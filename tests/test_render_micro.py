"""
Phase 6: render_micro.py 三场景 HTML 报告测试
ADR-002 决策 15
"""

import os
import pytest


# ── valuation_badge ──────────────────────────────────────────────────────────


def test_valuation_badge_undervalued():
    """ratio < 0.7 → 低估（绿色）。"""
    from lab.chart_lib.micro_charts import valuation_badge

    badge = valuation_badge(0.60)
    assert "低估" in badge
    assert "green" in badge.lower() or "#" in badge


def test_valuation_badge_fair():
    """0.9 <= ratio <= 1.1 → 合理。"""
    from lab.chart_lib.micro_charts import valuation_badge

    badge = valuation_badge(1.0)
    assert "合理" in badge


def test_valuation_badge_overvalued():
    """ratio > 1.3 → 高估（红色）。"""
    from lab.chart_lib.micro_charts import valuation_badge

    badge = valuation_badge(1.5)
    assert "高估" in badge


def test_valuation_badge_thresholds():
    """边界值：0.7/0.9/1.1/1.3。"""
    from lab.chart_lib.micro_charts import valuation_badge

    assert "低估" in valuation_badge(0.70)  # edge: 0.70 → 低估
    assert "合理" in valuation_badge(0.90)  # edge: 0.90 → 合理
    assert "合理" in valuation_badge(1.10)  # edge: 1.10 → 合理
    assert "高估" in valuation_badge(1.30)  # edge: 1.30 → 高估


# ── scenario_table ───────────────────────────────────────────────────────────


def test_scenario_table_returns_html_string():
    """scenario_table 返回 HTML 字符串，包含三场景行。"""
    from lab.chart_lib.micro_charts import scenario_table

    scenarios = [
        {
            "scenario_name": "bear",
            "g1": 0.05,
            "N": 3,
            "gt": 0.025,
            "r": 0.12,
            "intrinsic_value": 380,
            "degradation_reason": None,
        },
        {
            "scenario_name": "base",
            "g1": 0.10,
            "N": 5,
            "gt": 0.025,
            "r": 0.10,
            "intrinsic_value": 521,
            "degradation_reason": None,
        },
        {
            "scenario_name": "bull",
            "g1": 0.15,
            "N": 7,
            "gt": 0.025,
            "r": 0.10,
            "intrinsic_value": 680,
            "degradation_reason": None,
        },
    ]
    html = scenario_table(scenarios, current_price=460, currency="CNY")
    assert isinstance(html, str)
    assert "bear" in html.lower() or "Bear" in html
    assert "base" in html.lower() or "Base" in html
    assert "bull" in html.lower() or "Bull" in html


def test_scenario_table_shows_safety_margin():
    """HTML 包含安全边际符号（% 或 vs 现价列）。"""
    from lab.chart_lib.micro_charts import scenario_table

    scenarios = [
        {
            "scenario_name": "base",
            "g1": 0.10,
            "N": 5,
            "gt": 0.025,
            "r": 0.10,
            "intrinsic_value": 600,
            "degradation_reason": None,
        },
    ]
    html = scenario_table(scenarios, current_price=460, currency="CNY")
    assert "%" in html or "安全边际" in html


def test_scenario_table_shows_degradation_reason():
    """若 degradation_reason 非空，出现在表格注释中。"""
    from lab.chart_lib.micro_charts import scenario_table

    scenarios = [
        {
            "scenario_name": "base",
            "g1": 0.10,
            "N": 5,
            "gt": 0.025,
            "r": 0.10,
            "intrinsic_value": 521,
            "degradation_reason": "rd degraded: interest_expense missing",
        },
    ]
    html = scenario_table(scenarios, current_price=460, currency="CNY")
    assert "rd degraded" in html or "interest_expense" in html or "降级" in html


# ── fcf_history_chart ────────────────────────────────────────────────────────


def test_fcf_history_chart_returns_bar():
    """fcf_history_chart 返回 pyecharts Bar 对象。"""
    from lab.chart_lib.micro_charts import fcf_history_chart
    from pyecharts.charts import Bar

    fcf_list = [800, 900, 1000, 1100, 1200]
    chart = fcf_history_chart(fcf_list=fcf_list, base_fcf=1000)
    assert isinstance(chart, Bar)


def test_fcf_history_chart_accepts_labels():
    """fcf_history_chart 接受 years 参数。"""
    from lab.chart_lib.micro_charts import fcf_history_chart
    from pyecharts.charts import Bar

    chart = fcf_history_chart(
        fcf_list=[800, 900, 1000],
        base_fcf=900,
        years=["2022", "2023", "2024"],
    )
    assert isinstance(chart, Bar)


# ── sensitivity_heatmap ──────────────────────────────────────────────────────


def test_sensitivity_heatmap_returns_heatmap():
    """sensitivity_heatmap 返回 pyecharts HeatMap。"""
    from lab.chart_lib.micro_charts import sensitivity_heatmap
    from pyecharts.charts import HeatMap

    base_scenario = {"g1": 0.10, "N": 5, "gt": 0.025, "r": 0.10}
    chart = sensitivity_heatmap(
        base_scenario=base_scenario,
        base_fcf=1000,
        shares=1000,
        current_price=5.0,
    )
    assert isinstance(chart, HeatMap)


# ── render_micro.py CLI smoke test ───────────────────────────────────────────


def test_render_micro_generates_html(tmp_path):
    """render_micro.py --code X --dcf → 生成 HTML 文件，不报错。"""
    import subprocess

    env = {**os.environ, "ECO_DB_DIR": str(tmp_path)}

    # Seed minimal data
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")
    for i, year in enumerate(["2022-12-31", "2023-12-31", "2024-12-31"]):
        conn.execute(
            """INSERT OR REPLACE INTO financial_statements
               (code, report_date, fcf, pretax_income, income_tax,
                interest_expense, total_liabilities)
               VALUES (?,?,?,?,?,?,?)""",
            ("000725.SZ", year, 1000 * (1 + i * 0.1), 2000, 500, 100, 5000),
        )
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding, currency, current_price, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "CN", "BOE", "半导体", 100000, "CNY", 5.0, "2024-01-01"),
    )
    conn.execute(
        """INSERT OR REPLACE INTO scenarios
           (code, scenario_name, g1, N, gt, r, wacc_l2_sanity, base_fcf_method, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "bear", 0.05, 3, 0.025, 0.12, 0.10, "mean3", "2024-01-01"),
    )
    conn.execute(
        """INSERT OR REPLACE INTO scenarios
           (code, scenario_name, g1, N, gt, r, wacc_l2_sanity, base_fcf_method, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "base", 0.10, 5, 0.025, 0.10, 0.10, "mean3", "2024-01-01"),
    )
    conn.execute(
        """INSERT OR REPLACE INTO scenarios
           (code, scenario_name, g1, N, gt, r, wacc_l2_sanity, base_fcf_method, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "bull", 0.15, 7, 0.025, 0.10, 0.10, "mean3", "2024-01-01"),
    )
    conn.commit()
    _connections.clear()

    out_dir = str(tmp_path / "reports")
    os.makedirs(out_dir, exist_ok=True)

    r = subprocess.run(
        [
            "python",
            "lab/scripts/render_micro.py",
            "--code",
            "000725.SZ",
            "--dcf",
            "--out-dir",
            out_dir,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr

    html_files = [f for f in os.listdir(out_dir) if f.endswith(".html")]
    assert len(html_files) >= 1
