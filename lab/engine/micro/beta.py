from __future__ import annotations
from typing import Optional, Tuple

import pandas as pd


def industry_relevered_beta(
    code: str,
    conn,
    industry: Optional[str] = None,
    country: str = "CN",
) -> Tuple[float, str]:
    """
    返回 (beta_relevered, source)。
    source = 'damodaran' | 'self-computed'

    流程：
    1. 从 securities 表读取 industry（若参数未给）
    2. 用 Damodaran 表查 β_unlevered
    3. 读公司 D/E = total_liabilities / market_cap
    4. re-lever: β_l = β_u × (1 + (1-t) × D/E_company)
    5. 若 Damodaran 未命中 → fallback calc_beta；再未命中 → 1.0
    """
    from lab.engine.micro.damodaran import load_industry_beta, load_country_tax

    # ── 读取行业 ──
    _industry = industry
    if not _industry:
        sec = conn.execute(
            "SELECT industry FROM securities WHERE code=?", (code,)
        ).fetchone()
        if sec:
            _industry = sec["industry"]

    # ── 读取 Damodaran β_unlevered ──
    dam = load_industry_beta(_industry, country) if _industry else None

    if dam is not None:
        b_unlevered = dam["unlevered_beta"]
        t = load_country_tax(country)

        # 公司 D/E = total_liabilities / market_cap
        fin = conn.execute(
            """SELECT total_liabilities FROM financial_statements
               WHERE code=? ORDER BY report_date DESC LIMIT 1""",
            (code,),
        ).fetchone()
        sec = conn.execute(
            "SELECT shares_outstanding, current_price FROM securities WHERE code=?",
            (code,),
        ).fetchone()
        market_cap = 0.0
        if sec and sec["shares_outstanding"] and sec["current_price"]:
            market_cap = sec["shares_outstanding"] * sec["current_price"]
        total_liab = (fin["total_liabilities"] or 0) if fin else 0
        de_company = (total_liab / market_cap) if market_cap > 0 else 0.0

        b_relevered = round(b_unlevered * (1 + (1 - t) * de_company), 6)
        return b_relevered, "damodaran"

    # ── Fallback: calc_beta ──
    b = calc_beta(conn, code)
    if b is not None:
        return b, "self-computed"
    return 1.0, "self-computed"


def calc_beta(conn, code, benchmark="000300.SH", periods=252):
    stock = pd.read_sql_query(
        "SELECT date, close FROM stock_prices WHERE code=? ORDER BY date",
        conn,
        params=(code,),
    )
    bench = pd.read_sql_query(
        "SELECT date, close FROM stock_prices WHERE code=? ORDER BY date",
        conn,
        params=(benchmark,),
    )
    if len(stock) < 2 or len(bench) < 2:
        return None

    merged = stock.merge(bench, on="date", suffixes=("_stock", "_bench"))
    if len(merged) < 2:
        return None

    returns = merged["close_stock"].pct_change().dropna()
    bench_returns = merged["close_bench"].pct_change().dropna()

    if len(returns) < 2 or len(bench_returns) < 2:
        return None

    cov = returns.cov(bench_returns)
    var = bench_returns.var()
    if var == 0:
        return None

    return round(cov / var, 4)
