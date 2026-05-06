"""
valuation.py — 每股估值与 Buffett 分级标签
ADR-002 决策 15：
- per_share_value(equity, shares) → float
- buffett_label(price, intrinsic) → str
- build_scenario_table(conn, code) → list[dict]
"""

from __future__ import annotations
from typing import List

from lab.engine.micro.dcf import dcf_value, equity_value as _deduct_debt


# ── 每股价值 ─────────────────────────────────────────────────────────────


def per_share_value(equity: float, shares: float) -> float:
    """equity / shares_outstanding。"""
    if not shares:
        raise ValueError("shares_outstanding 不能为 0")
    return equity / shares


# ── Buffett 分级标签 ──────────────────────────────────────────────────────


def buffett_label(price: float, intrinsic: float) -> str:
    """
    基于 price/intrinsic 比值分级（ADR-002 决策 15）：
    < 0.70  深度低估
    0.70–0.90  低估
    0.90–1.10  合理
    1.10–1.30  高估
    > 1.30  深度高估
    边界归上区间（左闭右开）。
    """
    ratio = price / intrinsic
    if ratio < 0.70:
        return "深度低估"
    elif ratio < 0.90:
        return "低估"
    elif ratio <= 1.10:
        return "合理"
    elif ratio <= 1.30:
        return "高估"
    else:
        return "深度高估"


# ── 三场景对照表 ─────────────────────────────────────────────────────────


def build_scenario_table(conn, code: str) -> List[dict]:
    """
    从 DB 读取 scenarios + securities + financial_statements，
    计算三场景每股内在价值，返回 list of dict（含 label）。
    """
    # ── 读取 securities ──
    sec = conn.execute(
        "SELECT shares_outstanding, current_price FROM securities WHERE code=?",
        (code,),
    ).fetchone()
    if not sec:
        raise ValueError(f"securities 中找不到 {code}，请先跑 fetch_financials.py")

    shares = sec["shares_outstanding"]
    current_price = sec["current_price"]

    # ── 读取历史 FCF ──
    fcf_rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code=? AND fcf IS NOT NULL
           ORDER BY report_date ASC""",
        (code,),
    ).fetchall()
    fcf_list = [r["fcf"] for r in fcf_rows]

    if not fcf_list:
        raise ValueError(f"financial_statements 中找不到 {code} 的 FCF 数据")

    # ── 读取三场景参数 ──
    scenario_rows = conn.execute(
        "SELECT * FROM scenarios WHERE code=? ORDER BY scenario_name",
        (code,),
    ).fetchall()
    if not scenario_rows:
        raise ValueError(f"scenarios 中找不到 {code}，请先跑 build_scenarios.py")

    rows_out = []
    for sr in scenario_rows:
        name = sr["scenario_name"]
        g1 = sr["g1"]
        N = sr["N"]
        gt = sr["gt"]
        r = sr["r"]
        method = sr["base_fcf_method"] or "mean3"

        # growth_rates = [g1]*N（两段式）
        ev = dcf_value(
            fcf_list,
            growth_rates=[g1] * N,
            terminal_growth=gt,
            discount_rate=r,
            base_fcf_method=method,
        )
        # 扣净债务
        eq = _deduct_debt(conn, code, ev)
        # 每股
        psv = per_share_value(equity=eq, shares=shares)
        # 对比
        if current_price and current_price > 0:
            vs_pct = (psv - current_price) / current_price * 100
            label = buffett_label(price=current_price, intrinsic=psv)
        else:
            vs_pct = None
            label = "N/A"

        rows_out.append(
            {
                "scenario": name,
                "per_share_value": round(psv, 2),
                "current_price": current_price,
                "vs_current_pct": round(vs_pct, 2) if vs_pct is not None else None,
                "label": label,
            }
        )

    return rows_out
