from pyecharts.charts import Bar, HeatMap, Line
from pyecharts.options import TooltipOpts

from .base import CHART_THEME, default_title_opts


def dcf_comparison(dcf_value=245, current_price=180, year_high=250,
                   year_low=150, title="DCF 估值对比"):
    chart = (
        Bar(init_opts={"theme": CHART_THEME, "width": "600px", "height": "400px"})
        .add_xaxis(["DCF 估值", "当前价", "52周高", "52周低"])
        .add_yaxis("价格", [dcf_value, current_price, year_high, year_low],
                   label_opts={"position": "top"})
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


def valuation_history(code, title="历史估值"):
    chart = (
        Line(init_opts={"theme": CHART_THEME, "width": "700px", "height": "400px"})
        .add_xaxis(["2021", "2022", "2023", "2024", "2025"])
        .add_yaxis("PE", [35, 28, 30, 25, 22], is_smooth=True)
        .add_yaxis("PB", [10, 8, 9, 7, 6], is_smooth=True)
        .set_global_opts(
            title_opts=default_title_opts(title),
            tooltip_opts=TooltipOpts(trigger="axis"),
        )
    )
    return chart
