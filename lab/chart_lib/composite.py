from pyecharts.charts import Page
from .base import CHART_THEME


def compose(title, charts, filename="diagnosis_report.html"):
    page = Page(page_title=title)
    for chart in charts:
        page.add(chart)
    page.render(filename)
    return filename
