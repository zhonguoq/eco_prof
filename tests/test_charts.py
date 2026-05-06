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


# ── Slice 5: 无硬编码图表 ───────────────────────────────

def test_dcf_comparison_accepts_explicit_data():
    from lab.chart_lib.micro_charts import dcf_comparison
    from pyecharts.charts import Bar

    chart = dcf_comparison(dcf_value=300, current_price=250,
                           year_high=320, year_low=200,
                           title="测试 DCF")
    assert isinstance(chart, Bar)


def test_valuation_history_accepts_explicit_data():
    from lab.chart_lib.micro_charts import valuation_history
    from pyecharts.charts import Line

    chart = valuation_history(
        code="600519.SH",
        title="历史估值",
        pe_list=[35, 28, 30, 25, 22],
        pb_list=[10, 8, 9, 7, 6],
        years=["2021", "2022", "2023", "2024", "2025"],
    )
    assert isinstance(chart, Line)
