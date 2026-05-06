from __future__ import annotations

from typing import Optional

from pyecharts.charts import Bar, HeatMap, Line
from pyecharts.options import TooltipOpts

from .base import CHART_THEME, default_title_opts


# ── 估值分级 ──────────────────────────────────────────────────────────────────


def valuation_badge(ratio: float) -> str:
    """
    返回 HTML 片段，颜色分级：
      ratio < 0.7   → 🟢 低估
      0.7 <= r < 0.9 → 🟡 偏低
      0.9 <= r <= 1.1 → ⚪ 合理
      1.1 < r <= 1.3  → 🟠 偏高
      ratio > 1.3  → 🔴 高估
    边界按 issue 契约（0.7/0.9/1.1/1.3）：
      0.70 → 低估；0.90 → 合理；1.10 → 合理；1.30 → 高估
    """
    if ratio <= 0.70:
        color, label = "#4caf50", "🟢 低估"
    elif ratio < 0.90:
        color, label = "#ffeb3b", "🟡 偏低"
    elif ratio <= 1.10:
        color, label = "#9e9e9e", "⚪ 合理"
    elif ratio < 1.30:
        color, label = "#ff9800", "🟠 偏高"
    else:
        color, label = "#f44336", "🔴 高估"
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-weight:bold">{label}</span>'
    )


# ── 三场景对照表 ──────────────────────────────────────────────────────────────


def scenario_table(
    scenarios: list[dict],
    current_price: float,
    currency: str = "CNY",
) -> str:
    """
    返回 HTML <table> 字符串。
    每行：scenario | g₁ | N | gt | r | 每股内在价值 | vs 现价 | 安全边际 | 降级注释
    """
    header_cells = [
        "场景",
        "g₁",
        "N",
        "gt",
        "r (WACC)",
        f"内在价值({currency})",
        "vs 现价",
        "安全边际",
    ]
    rows_html = []
    degradation_notes = []

    for s in scenarios:
        iv = s.get("intrinsic_value")
        if iv and current_price and current_price > 0:
            ratio = iv / current_price
            diff_pct = (iv - current_price) / current_price
            diff_str = f"{diff_pct:+.1%}"
            margin = "✓" if diff_pct >= 0 else f"✗ {diff_pct:.1%}"
        else:
            ratio, diff_str, margin = None, "N/A", "N/A"

        iv_str = f"{iv:.0f}" if iv else "N/A"
        name = s.get("scenario_name", "")
        row = [
            f"<b>{name}</b>",
            f"{s.get('g1', 0):.1%}" if s.get("g1") is not None else "N/A",
            str(s.get("N", "N/A")),
            f"{s.get('gt', 0):.2%}" if s.get("gt") is not None else "N/A",
            f"{s.get('r', 0):.2%}" if s.get("r") is not None else "N/A",
            iv_str,
            diff_str,
            margin,
        ]
        rows_html.append(row)

        reason = s.get("degradation_reason")
        if reason:
            degradation_notes.append(f"[{name}] 降级: {reason}")

    # Build HTML
    th = "".join(
        f"<th style='padding:6px 10px;border:1px solid #ddd'>{h}</th>"
        for h in header_cells
    )
    tbody = ""
    for row in rows_html:
        td = "".join(
            f"<td style='padding:6px 10px;border:1px solid #ddd'>{c}</td>" for c in row
        )
        tbody += f"<tr>{td}</tr>\n"

    notes_html = ""
    if degradation_notes:
        notes_list = "".join(f"<li>{n}</li>" for n in degradation_notes)
        notes_html = (
            f'<p style="color:#888;font-size:0.85em;margin-top:8px">'
            f"<b>降级信息：</b><ul>{notes_list}</ul></p>"
        )

    table = (
        "<table style='border-collapse:collapse;width:100%;font-size:0.9em'>"
        f"<thead><tr style='background:#1a237e;color:#fff'>{th}</tr></thead>"
        f"<tbody>{tbody}</tbody>"
        "</table>"
        f"{notes_html}"
    )
    return table


# ── FCF 历史柱状图 ─────────────────────────────────────────────────────────────


def fcf_history_chart(
    fcf_list: list,
    base_fcf: float,
    years: Optional[list] = None,
    title: str = "历史 FCF",
) -> Bar:
    """
    FCF 柱状图 + base_fcf 红色横线（用第二 y 轴系列模拟）。
    """
    if years is None:
        years = [str(i + 1) for i in range(len(fcf_list))]

    baseline = [base_fcf] * len(fcf_list)

    chart = (
        Bar(init_opts={"theme": CHART_THEME, "width": "700px", "height": "400px"})
        .add_xaxis(years)
        .add_yaxis(
            "FCF",
            fcf_list,
            label_opts={"is_show": False},
            itemstyle_opts={"color": "#1565c0"},
        )
        .add_yaxis(
            "base FCF (均值)",
            baseline,
            label_opts={"is_show": False},
            itemstyle_opts={"color": "#e53935"},
        )
        .set_global_opts(
            title_opts=default_title_opts(title),
            yaxis_opts={"name": "亿元"},
            tooltip_opts=TooltipOpts(trigger="axis"),
        )
    )
    return chart


# ── 敏感性热力图 ───────────────────────────────────────────────────────────────


def sensitivity_heatmap(
    base_scenario: dict,
    base_fcf: float,
    shares: float,
    current_price: float = 1.0,
    g1_steps: int = 3,
    r_steps: int = 2,
    title: str = "敏感性分析（每股内在价值）",
) -> HeatMap:
    """
    base 场景附近 g₁ ± g1_steps% × r ± r_steps% 热力图。
    每格 = 每股内在价值（用简化 DCF）。
    """
    from lab.engine.micro.dcf import dcf_intrinsic_value

    g1_base = base_scenario.get("g1", 0.10)
    r_base = base_scenario.get("r", 0.10)
    N = base_scenario.get("N", 5)
    gt = base_scenario.get("gt", 0.025)

    g1_range = [round(g1_base + i * 0.01, 4) for i in range(-g1_steps, g1_steps + 1)]
    r_range = [round(r_base + i * 0.01, 4) for i in range(-r_steps, r_steps + 1)]

    data = []
    for ri, r in enumerate(r_range):
        for gi, g1 in enumerate(g1_range):
            try:
                ev = dcf_intrinsic_value(
                    base_fcf=base_fcf,
                    growth_rate=g1,
                    growth_years=N,
                    terminal_growth=gt,
                    discount_rate=r,
                )
                per_share = round(ev / shares, 2) if shares > 0 else 0
            except Exception:
                per_share = 0
            data.append([gi, ri, per_share])

    g1_labels = [f"{g:.1%}" for g in g1_range]
    r_labels = [f"{r:.1%}" for r in r_range]

    max_val = max(d[2] for d in data) if data else 1
    min_val = min(d[2] for d in data) if data else 0

    chart = (
        HeatMap(init_opts={"theme": CHART_THEME, "width": "700px", "height": "450px"})
        .add_xaxis(g1_labels)
        .add_yaxis(
            "每股价值",
            r_labels,
            data,
            label_opts={"is_show": True},
        )
        .set_global_opts(
            title_opts=default_title_opts(title),
            visualmap_opts={
                "min": min_val,
                "max": max_val,
                "orient": "horizontal",
            },
            xaxis_opts={"name": "g₁"},
            yaxis_opts={"name": "r (WACC)"},
        )
    )
    return chart


# ── 旧接口保持向后兼容 ──────────────────────────────────────────────────────────


def dcf_comparison(dcf_value, current_price, year_high, year_low, title="DCF 估值对比"):
    chart = (
        Bar(init_opts={"theme": CHART_THEME, "width": "600px", "height": "400px"})
        .add_xaxis(["DCF 估值", "当前价", "52周高", "52周低"])
        .add_yaxis(
            "价格",
            [dcf_value, current_price, year_high, year_low],
            label_opts={"position": "top"},
        )
        .set_global_opts(
            title_opts=default_title_opts(title),
            yaxis_opts={"name": "元"},
        )
    )
    return chart


def dcf_sensitivity_heatmap(matrix, title="DCF 敏感性分析"):
    if not matrix:
        return None
    rows = list(matrix.keys())
    cols = list(matrix[rows[0]].keys())
    data = []
    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            data.append([ci, ri, matrix[r][c]])

    chart = (
        HeatMap(init_opts={"theme": CHART_THEME})
        .add_xaxis(cols)
        .add_yaxis("", rows, data, label_opts={"is_show": True})
        .set_global_opts(
            title_opts=default_title_opts(title),
            visualmap_opts={"min": 0, "max": max(d[2] for d in data)},
        )
    )
    return chart


def industry_ranking(result, stocks, title="行业排名"):
    names = []
    scores = []
    for r in result:
        s = next((st for st in stocks if st["code"] == r["code"]), {})
        names.append(s.get("name", r["code"]))
        scores.append(r["score"])

    chart = (
        Bar(init_opts={"theme": CHART_THEME})
        .add_xaxis(names)
        .add_yaxis("综合得分", scores, label_opts={"position": "top"})
        .set_global_opts(
            title_opts=default_title_opts(title),
            yaxis_opts={"name": "综合得分"},
        )
    )
    return chart


def valuation_history(code, pe_list, pb_list, years, title="历史估值"):
    chart = (
        Line(init_opts={"theme": CHART_THEME, "width": "700px", "height": "400px"})
        .add_xaxis(years)
        .add_yaxis("PE", pe_list, is_smooth=True)
        .add_yaxis("PB", pb_list, is_smooth=True)
        .set_global_opts(
            title_opts=default_title_opts(title),
            tooltip_opts=TooltipOpts(trigger="axis"),
        )
    )
    return chart
