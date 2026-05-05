import pandas as pd

def test_fetch_prices_writes_to_micro_db():
    from lab.engine.micro.fetcher import fetch_stock_data
    from lab.engine.db import get_db

    conn = get_db("micro")
    dates = pd.date_range("2024-01-01", "2024-01-05")
    mock_data = pd.DataFrame({
        "open": [100.0]*5, "close": [101.0]*5,
        "high": [102.0]*5, "low": [99.0]*5,
        "volume": [1e6]*5,
    }, index=dates)

    n = fetch_stock_data("600519.SH", conn, market="A", mock=mock_data)
    assert n == 5
    rows = conn.execute("SELECT count(*) AS c FROM stock_prices WHERE code='600519.SH'").fetchone()
    assert rows["c"] == 5

def test_dcf_value_computation():
    from lab.engine.micro.dcf import dcf_value

    fcf_list = [100, 110, 120, 130, 140]
    result = dcf_value(
        fcf_list=fcf_list,
        growth_rate=0.10,
        growth_years=5,
        terminal_growth=0.03,
        discount_rate=0.08,
    )
    assert result > 0
    assert isinstance(result, float)

def test_dcf_sensitivity_matrix():
    from lab.engine.micro.dcf import sensitivity_matrix

    fcf_list = [100, 110, 120]
    matrix = sensitivity_matrix(fcf_list)
    assert isinstance(matrix, dict)
    for g_row in matrix.values():
        for val in g_row.values():
            assert isinstance(val, (int, float))

def test_dcf_cli_without_args_prints_usage():
    import subprocess, os
    r = subprocess.run(
        ["python3", "lab/scripts/dcf.py", "--help"],
        capture_output=True, text=True
    )
    assert r.returncode == 0
    assert "--code" in r.stdout
