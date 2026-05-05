from pyecharts.globals import ThemeType

BRAND_COLORS = {
    "primary": "#1a237e",
    "secondary": "#0d47a1",
    "warning": "#e65100",
    "danger": "#b71c1c",
    "safe": "#1b5e20",
    "neutral": "#546e7a",
}

CHART_THEME = ThemeType.DARK


def default_title_opts(text):
    from pyecharts.options import TitleOpts
    return TitleOpts(title=text, title_textstyle_opts={"color": BRAND_COLORS["primary"]})


def render_chart(chart):
    return chart.render_notebook() if hasattr(chart, "render_notebook") else chart.render_embed()
