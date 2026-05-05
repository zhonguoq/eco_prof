from pyecharts.charts import Line
from pyecharts.options import TooltipOpts

from .base import CHART_THEME, default_title_opts


def yield_curve_chart(tenors=None, yields=None, title="收益率曲线"):
    tenors = tenors or ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]
    yields = yields or [4.5, 4.4, 4.3, 4.2, 4.0, 3.8, 3.5, 3.2]

    chart = (
        Line(init_opts={"theme": CHART_THEME, "width": "800px", "height": "400px"})
        .add_xaxis(tenors)
        .add_yaxis("收益率", yields,
                   is_smooth=True,
                   label_opts={"is_show": False},
                   linestyle_opts={"width": 3})
        .set_global_opts(
            title_opts=default_title_opts(title),
            tooltip_opts=TooltipOpts(trigger="axis"),
            yaxis_opts={"name": "%"},
        )
    )
    return chart


def signal_dashboard(signals=None, title="信号面板"):
    from pyecharts.charts import Grid
    from pyecharts.charts import Bar

    signals = signals or {"T10Y2Y": -0.15, "CPI": 3.2, "UNRATE": 4.0, "FEDFUNDS": 4.5, "UMCSENT": 72.0}
    names = list(signals.keys())
    values = list(signals.values())

    chart = (
        Bar(init_opts={"theme": CHART_THEME})
        .add_xaxis(names)
        .add_yaxis("值", values, label_opts={"position": "top"})
        .set_global_opts(
            title_opts=default_title_opts(title),
            yaxis_opts={"name": "值"},
        )
    )
    return chart


def stage_timeline(stages=None, title="阶段变化"):
    from pyecharts.charts import Timeline, Bar

    timeline = Timeline(init_opts={"theme": CHART_THEME, "width": "900px", "height": "400px"})
    stages = stages or [{"date": "2026Q1", "name": "泡沫期"}, {"date": "2026Q2", "name": "顶部"}]
    for s in stages:
        bar = Bar().add_xaxis(["阶段"]).add_yaxis("", [s["name"]])
        timeline.add(bar, s["date"])
    return timeline


def debt_gdp_chart(data=None, title="债务/GDP"):
    from pyecharts.charts import Line

    data = data or [("2000", 250), ("2005", 280), ("2010", 320), ("2015", 350), ("2020", 380), ("2025", 342)]
    years = [d[0] for d in data]
    values = [d[1] for d in data]

    chart = (
        Line(init_opts={"theme": CHART_THEME})
        .add_xaxis(years)
        .add_yaxis("债务/GDP %", values, is_smooth=True,
                   label_opts={"is_show": True},
                   markline_opts={"data": [{"yAxis": 350}]})
        .set_global_opts(
            title_opts=default_title_opts(title),
            yaxis_opts={"name": "%"},
        )
    )
    return chart
