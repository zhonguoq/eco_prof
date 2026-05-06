"""
Phase 5: terminal_growth 测试
ADR-002 决策 6：gt = min(Rf, GDP[country])
"""

import pytest


def test_terminal_growth_cn_rf_below_gdp():
    """CN: Rf=2.5% < GDP=4.5% → gt=2.5%。"""
    from lab.engine.micro.wacc import terminal_growth

    gt = terminal_growth(country="CN", macro_conn=None)
    # CN 默认 Rf = 2.5%, GDP = 4.5%
    assert abs(gt - 0.025) < 1e-6


def test_terminal_growth_us_rf_above_gdp(tmp_path):
    """US: Rf=4.5% > GDP=4.0% → gt=4.0%（US 默认 Rf=4.5%）。"""
    from lab.engine.micro.wacc import terminal_growth

    gt = terminal_growth(country="US", macro_conn=None)
    # US 默认 Rf = 4.5%, GDP = 4.0%
    assert abs(gt - 0.040) < 1e-6


def test_terminal_growth_uses_macro_db_rf(tmp_path):
    """macro_conn 提供 CN10Y=3.5% > GDP=4.5% → gt=3.5%。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    macro_conn = get_db("macro")
    macro_conn.execute(
        "INSERT OR REPLACE INTO series (series_id, date, value) VALUES (?,?,?)",
        ("CN10Y", "2024-01-01", 0.035),
    )
    macro_conn.commit()

    from lab.engine.micro.wacc import terminal_growth

    gt = terminal_growth(country="CN", macro_conn=macro_conn)
    assert abs(gt - 0.035) < 1e-6


def test_terminal_growth_macro_db_rf_below_gdp(tmp_path):
    """macro_conn 提供 CN10Y=2.0% < GDP=4.5% → gt=2.0%。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    macro_conn = get_db("macro")
    macro_conn.execute(
        "INSERT OR REPLACE INTO series (series_id, date, value) VALUES (?,?,?)",
        ("CN10Y", "2024-01-01", 0.02),
    )
    macro_conn.commit()

    from lab.engine.micro.wacc import terminal_growth

    gt = terminal_growth(country="CN", macro_conn=macro_conn)
    assert abs(gt - 0.02) < 1e-6
