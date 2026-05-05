def test_yield_curve_chart_returns_line_chart():
    from lab.chart_lib.macro_charts import yield_curve_chart
    from pyecharts.charts import Line

    chart = yield_curve_chart()
    assert isinstance(chart, Line)

def test_signal_dashboard_returns_bar():
    from lab.chart_lib.macro_charts import signal_dashboard
    from pyecharts.charts import Bar
    chart = signal_dashboard()
    assert isinstance(chart, Bar)

def test_compose_writes_html(tmp_path):
    from lab.chart_lib.macro_charts import yield_curve_chart
    from lab.chart_lib.composite import compose

    chart = yield_curve_chart()
    out = compose("Test", [chart], filename=str(tmp_path / "test.html"))
    assert out
    assert (tmp_path / "test.html").exists()
    assert (tmp_path / "test.html").stat().st_size > 100
