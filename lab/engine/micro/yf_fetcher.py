"""
yf_fetcher.py — yfinance 数据获取与 securities 表写入
ADR-002 决策 9、10：
- fetch_securities(code) → dict  从 yfinance 取 8 字段
- upsert_securities(conn, code, mock=None) 覆写 securities 表
- market 从代码后缀正则推断
- _to_yf_code：内部代码格式 → yfinance 格式（.SH → .SS）
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Optional


# ── 市场推断 ──────────────────────────────────────────────────────────────


def _infer_market(code: str) -> str:
    """从内部代码后缀推断市场：A / HK / US。"""
    c = code.upper()
    if re.search(r"\.(SH|SZ|BJ|SS)$", c):
        return "A"
    if re.search(r"\.HK$", c):
        return "HK"
    if re.match(r"^[A-Z]{1,5}$", c):
        return "US"
    return "US"


def _to_yf_code(code: str) -> str:
    """
    把内部股票代码转换为 yfinance 接受的格式。
    上交所：内部 .SH → yfinance .SS（Yahoo Finance 用 .SS 表示上交所）
    深交所 .SZ、港股 .HK、美股 纯字母：保持不变。
    """
    return re.sub(r"\.SH$", ".SS", code, flags=re.IGNORECASE)


# ── yfinance 数据拉取 ─────────────────────────────────────────────────────


def fetch_securities(code: str) -> dict:
    """
    调 yfinance.Ticker(code).info，提取关键字段，返回 dict。
    内部代码（如 600519.SH）会先经 _to_yf_code 转换再传给 yfinance。
    测试时可通过 mock patch yfinance.Ticker。
    """
    import yfinance as yf

    yf_code = _to_yf_code(code)
    ticker = yf.Ticker(yf_code)
    info = ticker.info

    market = _infer_market(code)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "code": code,
        "market": market,
        "name": info.get("shortName") or info.get("longName") or "",
        "industry": info.get("industry") or "",
        "shares_outstanding": info.get("sharesOutstanding") or 0,
        "currency": info.get("currency") or "",
        "current_price": info.get("currentPrice")
        or info.get("regularMarketPrice")
        or 0.0,
        "updated_at": now,
    }


# ── DB upsert ─────────────────────────────────────────────────────────────


def upsert_securities(conn, code: str, mock: Optional[dict] = None) -> None:
    """
    把 securities 信息写入 DB（INSERT OR REPLACE → 每次覆写）。
    mock: 直接传 dict 时跳过 yfinance 调用（用于测试/离线）。
    """
    if mock is not None:
        data = dict(mock)
        data.setdefault("code", code)
        data.setdefault("market", _infer_market(code))
        data.setdefault(
            "updated_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    else:
        data = fetch_securities(code)

    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding,
            currency, current_price, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            code,
            data.get("market", ""),
            data.get("name", ""),
            data.get("industry", ""),
            data.get("shares_outstanding", 0),
            data.get("currency", ""),
            data.get("current_price", 0.0),
            data.get("updated_at", ""),
        ),
    )
    conn.commit()
