"""
WACC 计算模块
ADR-002 决策 3、4、5

- capm / wacc_l2: L2 简化公式（Rf + β×ERP）
- wacc_l3: L3 完整公式（Re CAPM + Rd + D/V 权重）
- default_industry: 行业默认 WACC 兜底
- terminal_growth: 终端增长率 min(Rf, GDP)
"""

from __future__ import annotations

from typing import Optional

# ── 行业默认值 ────────────────────────────────────────────────────────────────

_INDUSTRY_DEFAULTS = {
    "白酒": 0.10,
    "消费": 0.09,
    "科技": 0.12,
    "医药": 0.10,
    "金融": 0.10,
    "能源": 0.11,
    "制造": 0.10,
}

_GENERAL_DEFAULT = 0.10

# ── 国家长期 GDP 增速 ─────────────────────────────────────────────────────────

LONG_TERM_GDP = {
    "CN": 0.045,
    "HK": 0.040,
    "US": 0.040,
}


# ── L2 公式（简化，向后兼容） ─────────────────────────────────────────────────


def capm(rf: float, beta: float, erp: float = 0.06) -> float:
    """Re = Rf + β × ERP（L2 简化 WACC）。"""
    return round(rf + beta * erp, 4)


def wacc_l2(rf: float, beta: float, erp: float = 0.06) -> float:
    """wacc_l2 = capm（别名，供 sanity 对比）。"""
    return capm(rf=rf, beta=beta, erp=erp)


def default_industry(industry: str) -> float:
    """行业默认 WACC，未命中返回通用默认值。"""
    return _INDUSTRY_DEFAULTS.get(industry, _GENERAL_DEFAULT)


# ── terminal growth ───────────────────────────────────────────────────────────


def terminal_growth(country: str = "CN", macro_conn=None) -> float:
    """
    终端增长率 = min(Rf_from_macro_db, LONG_TERM_GDP[country])。
    若 macro_conn 为 None 或 Rf 查不到，使用默认 Rf = 2.5%（CN）。
    """
    rf = _fetch_rf(country, macro_conn)
    gdp = LONG_TERM_GDP.get(country, 0.04)
    return min(rf, gdp)


def _fetch_rf(country: str, macro_conn) -> float:
    """从 macro.db 查 Rf；查不到时返回国家默认值。"""
    _RF_DEFAULTS = {"CN": 0.025, "US": 0.045, "HK": 0.040}
    default_rf = _RF_DEFAULTS.get(country, 0.03)
    if macro_conn is None:
        return default_rf
    series_id = {"CN": "CN10Y", "US": "DGS10", "HK": "HK10Y"}.get(country, "")
    if not series_id:
        return default_rf
    try:
        row = macro_conn.execute(
            "SELECT value FROM series WHERE series_id=? ORDER BY date DESC LIMIT 1",
            (series_id,),
        ).fetchone()
        if row:
            return float(row[0])
    except Exception:
        pass
    return default_rf


# ── L3 完整公式 ───────────────────────────────────────────────────────────────


def wacc_l3(
    code: str,
    conn,
    rf: float = 0.025,
    industry: Optional[str] = None,
    country: str = "CN",
    erp: Optional[float] = None,
) -> dict:
    """
    L3 WACC 完整公式：
      Re = CAPM(Rf, β_relevered, ERP_by_country)
      Rd = interest_expense / total_debt；缺失 → Rf+2%
      t  = income_tax / pretax_income；<=0 → Damodaran 国家税率
      D/V = total_liab / (total_liab + market_cap)

    返回 dict{wacc, re, rd, tax, de_ratio, method, degradation_reason}
    """
    from lab.engine.micro.damodaran import load_erp, load_country_tax
    from lab.engine.micro.beta import industry_relevered_beta

    reasons: list[str] = []

    # ── ERP ──
    _erp = erp if erp is not None else load_erp(country)

    # ── β ──
    beta_val, beta_source = industry_relevered_beta(
        code, conn, industry=industry, country=country
    )
    if beta_val is None:
        beta_val = 1.0
        reasons.append("beta fallback: 1.0")

    # ── Re (CAPM) ──
    re = round(rf + beta_val * _erp, 6)

    # ── 从 DB 读取最近一期财务数据 ──
    row = conn.execute(
        """SELECT interest_expense, pretax_income, income_tax, total_liabilities
           FROM financial_statements
           WHERE code=? AND interest_expense IS NOT NULL
           ORDER BY report_date DESC LIMIT 1""",
        (code,),
    ).fetchone()

    row_any = conn.execute(
        """SELECT pretax_income, income_tax, total_liabilities
           FROM financial_statements
           WHERE code=?
           ORDER BY report_date DESC LIMIT 1""",
        (code,),
    ).fetchone()

    # ── Rd ──
    rd: float
    if row and row["interest_expense"] and row["interest_expense"] > 0:
        # 估算 total_debt（使用 total_liabilities 近似）
        total_debt = row["total_liabilities"] or 1
        rd = round(row["interest_expense"] / total_debt, 6)
        if rd <= 0 or rd > 0.30:
            rd = rf + 0.02
            reasons.append("rd out-of-range: fallback Rf+2%")
    else:
        rd = rf + 0.02
        reasons.append("rd degraded: interest_expense missing → Rf+2%")

    # ── tax ──
    fin = row if row else row_any
    tax: float
    if (
        fin
        and fin["pretax_income"]
        and fin["pretax_income"] > 0
        and fin["income_tax"] is not None
    ):
        tax = round(fin["income_tax"] / fin["pretax_income"], 6)
        if not (0 < tax < 1):
            tax = load_country_tax(country)
            reasons.append("tax out-of-range: fallback to country rate")
    else:
        tax = load_country_tax(country)
        reasons.append("tax degraded: pretax_income<=0 → country tax rate")

    # ── D/V ──
    total_liab = (fin["total_liabilities"] or 0) if fin else 0
    sec = conn.execute(
        "SELECT shares_outstanding, current_price FROM securities WHERE code=?",
        (code,),
    ).fetchone()
    market_cap = 0.0
    if sec and sec["shares_outstanding"] and sec["current_price"]:
        market_cap = sec["shares_outstanding"] * sec["current_price"]

    total_value = total_liab + market_cap
    dv = (total_liab / total_value) if total_value > 0 else 0.0
    ev = 1.0 - dv
    de_ratio = (total_liab / market_cap) if market_cap > 0 else 0.0

    # ── WACC ──
    wacc = round(re * ev + rd * (1 - tax) * dv, 6)

    return {
        "wacc": wacc,
        "re": re,
        "rd": rd,
        "tax": tax,
        "de_ratio": de_ratio,
        "dv": dv,
        "ev": ev,
        "beta": beta_val,
        "beta_source": beta_source,
        "erp": _erp,
        "method": "L3",
        "degradation_reason": "; ".join(reasons),
    }
