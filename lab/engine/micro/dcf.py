"""
DCF 估值内核 v2
ADR-002 决策 1、2、14：
- growth_rates: List[float] 驱动逐年增长（两段式等价 [g]*N）
- _normalize_base 支持 latest/mean3/mean5/median5
- base_fcf ≤ 0 抛 ValueError
- 保留旧 kwargs（growth_rate/growth_years）供向后兼容
"""

from __future__ import annotations
from typing import List, Optional


# ── 归一化基础 FCF ────────────────────────────────────────────────────────


def _normalize_base(fcf_list: list, method: str = "mean3") -> float:
    """从历史 FCF 列表中提取基础 FCF，支持 latest/mean3/mean5/median5。"""
    if not fcf_list:
        raise ValueError("fcf_list 不能为空")
    if method == "latest":
        return float(fcf_list[-1])
    elif method == "mean3":
        tail = fcf_list[-3:]
        return sum(tail) / len(tail)
    elif method == "mean5":
        tail = fcf_list[-5:]
        return sum(tail) / len(tail)
    elif method == "median5":
        tail = sorted(fcf_list[-5:])
        n = len(tail)
        return float(tail[n // 2])
    else:
        raise ValueError(f"未知 base_fcf_method: {method}")


# ── DCF 内核 ──────────────────────────────────────────────────────────────


def dcf_value(
    fcf_list: list,
    growth_rates: Optional[List[float]] = None,
    terminal_growth: float = 0.03,
    discount_rate: float = 0.08,
    base_fcf_method: str = "mean3",
    # ── 向后兼容旧 kwargs ──
    growth_rate: Optional[float] = None,
    growth_years: int = 5,
) -> float:
    """
    计算 DCF 企业价值（PV of FCFs + terminal value）。

    新接口：growth_rates=[0.10, 0.12, ...]  列表长度决定 N
    旧接口：growth_rate=0.10, growth_years=5  向后兼容保留
    """
    if discount_rate <= terminal_growth:
        raise ValueError(
            f"discount_rate ({discount_rate}) must be > terminal_growth ({terminal_growth})"
        )

    # ── 解析 growth_rates ──
    if growth_rates is None:
        g = growth_rate if growth_rate is not None else 0.10
        growth_rates = [g] * growth_years

    N = len(growth_rates)

    # ── 归一化基础 FCF ──
    base_fcf = _normalize_base(fcf_list, base_fcf_method)
    if base_fcf <= 0:
        raise ValueError("DCF 不适用：归一化 FCF 为非正值")

    # ── 逐年现金流折现（复利增长） ──
    pv_total = 0.0
    projected = base_fcf
    for y, g in enumerate(growth_rates, start=1):
        projected = projected * (1 + g)
        pv_total += projected / (1 + discount_rate) ** y

    # ── 终值折现 ──
    terminal = projected * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_total += terminal / (1 + discount_rate) ** N

    return round(pv_total, 2)


# ── 批量读 DB 计算 DCF ─────────────────────────────────────────────────────


def batch_dcf(
    conn,
    code,
    growth_rate=0.10,
    growth_years=5,
    terminal_growth=0.03,
    discount_rate=0.08,
    years_back=5,
):
    rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code = ? AND fcf IS NOT NULL
           AND report_date LIKE '%-12-31'
           ORDER BY report_date DESC
           LIMIT ?""",
        (code, years_back),
    ).fetchall()

    if not rows:
        return None

    fcf_list = [r["fcf"] for r in rows]
    fcf_list.reverse()
    return dcf_value(
        fcf_list,
        growth_rate=growth_rate,
        growth_years=growth_years,
        terminal_growth=terminal_growth,
        discount_rate=discount_rate,
    )


# ── 股权价值 ──────────────────────────────────────────────────────────────


def equity_value(conn, code, ev):
    row = conn.execute(
        """SELECT cash, total_liabilities FROM financial_statements
           WHERE code = ? AND cash IS NOT NULL AND total_liabilities IS NOT NULL
           ORDER BY report_date DESC LIMIT 1""",
        (code,),
    ).fetchone()
    if not row:
        return ev
    net_debt = row["total_liabilities"] - row["cash"]
    return round(ev - net_debt, 2)


# ── 敏感性矩阵 ────────────────────────────────────────────────────────────


def sensitivity_matrix(
    fcf_list,
    growth_range=(0.05, 0.15, 3),
    discount_range=(0.06, 0.10, 3),
    growth_years=5,
    terminal_growth=0.03,
):
    matrix = {}
    g_lo, g_hi, g_steps = growth_range
    d_lo, d_hi, d_steps = discount_range
    for g in [g_lo + i * (g_hi - g_lo) / (g_steps - 1) for i in range(g_steps)]:
        row_key = f"g={g:.0%}"
        matrix[row_key] = {}
        for d in [d_lo + i * (d_hi - d_lo) / (d_steps - 1) for i in range(d_steps)]:
            matrix[row_key][f"r={d:.0%}"] = dcf_value(
                fcf_list,
                growth_rate=g,
                growth_years=growth_years,
                terminal_growth=terminal_growth,
                discount_rate=d,
            )
    return matrix


def dcf_intrinsic_value(
    base_fcf: float,
    growth_rate: float = 0.10,
    growth_years: int = 5,
    terminal_growth: float = 0.025,
    discount_rate: float = 0.10,
) -> float:
    """
    单次 DCF 估值，直接传入 base_fcf（不需要历史列表）。
    供热力图等批量计算场景使用。
    """
    if discount_rate <= terminal_growth:
        raise ValueError(
            f"discount_rate ({discount_rate}) must be > terminal_growth ({terminal_growth})"
        )
    growth_rates = [growth_rate] * growth_years
    pv_total = 0.0
    projected = base_fcf
    for y, g in enumerate(growth_rates, start=1):
        projected = projected * (1 + g)
        pv_total += projected / (1 + discount_rate) ** y
    terminal = projected * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_total += terminal / (1 + discount_rate) ** growth_years
    return round(pv_total, 2)
