"""
Damodaran 数据加载模块
ADR-002 决策 3、4、5、6

加载 lab/data/damodaran/ 目录下的 CSV 文件，提供：
  - load_erp(country) → float
  - load_industry_beta(industry, market) → dict | None
  - load_country_tax(country) → float
所有 CSV 解析结果都缓存在 _CACHE 中。
"""

from __future__ import annotations

import csv
import os
from typing import Optional

# ── 常量 ─────────────────────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "damodaran")

_MARKET_TO_FILE = {
    "CN": "betas_china.csv",
    "HK": "betas_em.csv",
    "US": "betas_us.csv",
    "JP": "betas_japan.csv",
}

# 行业别名：中文 / yfinance 英文 → Damodaran 行业 key
INDUSTRY_ALIASES: dict[str, str] = {
    "白酒": "Beverage (Alcoholic)",
    "饮料": "Beverage (Soft)",
    "Beverages—Wineries & Distilleries": "Beverage (Alcoholic)",
    "Beverages—Non-Alcoholic": "Beverage (Soft)",
    "半导体": "Semiconductor",
    "科技": "Technology",
    "医药": "Pharmaceutical",
    "Drugs": "Pharmaceutical",
    "金融": "Financial Services",
    "Banks": "Financial Services",
    "房地产": "Real Estate",
    "汽车": "Auto",
    "消费": "Consumer Goods",
    "Consumer Defensive": "Consumer Goods",
    "Consumer Cyclical": "Consumer Goods",
    "能源": "Energy",
    "Oil & Gas": "Energy",
    "Technology": "Technology",
    "Semiconductors": "Semiconductor",
}

_COUNTRY_CODE_MAP = {
    "CN": "China",
    "US": "United States",
    "HK": "Hong Kong",
    "JP": "Japan",
}

_FALLBACK_ERP = 0.055
_FALLBACK_TAX = 0.25

# ── 缓存 ─────────────────────────────────────────────────────────────────────

_CACHE: dict = {}


# ── 内部加载器 ────────────────────────────────────────────────────────────────


def _load_csv(filename: str) -> list[dict]:
    """读取 lab/data/damodaran/<filename>，返回 list[dict]，带缓存。"""
    if filename in _CACHE:
        return _CACHE[filename]
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        _CACHE[filename] = []
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
    _CACHE[filename] = rows
    return rows


def _resolve_industry(industry: str) -> str:
    """将别名或原名统一为 Damodaran 行业 key。"""
    return INDUSTRY_ALIASES.get(industry, industry)


# ── 公开 API ──────────────────────────────────────────────────────────────────


def load_erp(country: str = "CN") -> float:
    """
    加载 ERP（Equity Risk Premium）by country。
    country: ISO-2 代码（CN / US / HK / JP）或国家全称
    返回 float；未命中时返回 _FALLBACK_ERP。
    """
    rows = _load_csv("ctryprem.csv")
    country_name = _COUNTRY_CODE_MAP.get(country, country)
    for row in rows:
        if row.get("Country", "").strip().lower() == country_name.lower():
            try:
                return float(row["Equity Risk Premium"])
            except (KeyError, ValueError):
                pass
    return _FALLBACK_ERP


def load_industry_beta(industry: str, market: str = "CN") -> Optional[dict]:
    """
    加载行业 β 数据。
    industry: Damodaran 行业名或别名
    market: CN / US / HK / JP
    返回 dict{unlevered_beta, levered_beta, de_ratio, tax_rate}；
    未命中时返回 None。
    """
    filename = _MARKET_TO_FILE.get(market, "betas_em.csv")
    rows = _load_csv(filename)
    canonical = _resolve_industry(industry)
    for row in rows:
        name = row.get("Industry Name", "").strip()
        if name.lower() == canonical.lower():
            try:
                return {
                    "unlevered_beta": float(row["Unlevered Beta"]),
                    "levered_beta": float(row["Beta"]),
                    "de_ratio": float(row["D/E Ratio"]),
                    "tax_rate": float(row["Tax Rate"]),
                }
            except (KeyError, ValueError):
                return None
    return None


def load_country_tax(country: str = "CN") -> float:
    """
    加载国家法定税率。
    country: ISO-2 代码
    返回 float；未命中时返回 _FALLBACK_TAX。
    """
    rows = _load_csv("taxrate.csv")
    country_name = _COUNTRY_CODE_MAP.get(country, country)
    for row in rows:
        if row.get("Country", "").strip().lower() == country_name.lower():
            try:
                return float(row["Tax Rate"])
            except (KeyError, ValueError):
                pass
    return _FALLBACK_TAX
