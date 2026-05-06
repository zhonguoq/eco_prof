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


# ── Slice 2: batch_dcf + equity_value + edge cases ──────

def test_batch_dcf_reads_from_db():
    from lab.engine.micro.dcf import batch_dcf
    from lab.engine.db import get_db

    conn = get_db("micro")
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf, operating_cf, capex)
        VALUES (?, ?, ?, ?, ?)""",
        ("600519.SH", "2020-12-31", 800, 1000, 200))
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf, operating_cf, capex)
        VALUES (?, ?, ?, ?, ?)""",
        ("600519.SH", "2021-12-31", 900, 1100, 200))
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf, operating_cf, capex)
        VALUES (?, ?, ?, ?, ?)""",
        ("600519.SH", "2022-12-31", 1000, 1200, 200))
    conn.commit()

    ev = batch_dcf(conn, "600519.SH", growth_rate=0.10, growth_years=3,
                   terminal_growth=0.03, discount_rate=0.08)
    assert ev is not None
    assert ev > 0

    # With no data, return None
    ev2 = batch_dcf(conn, "NONEXIST", growth_rate=0.10)
    assert ev2 is None


def test_equity_value_deducts_net_debt():
    from lab.engine.micro.dcf import equity_value
    from lab.engine.db import get_db

    conn = get_db("micro")
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf, cash, total_liabilities)
        VALUES (?, ?, ?, ?, ?)""",
        ("600519.SH", "2024-12-31", 1000, 5000, 2000))
    conn.commit()

    # EV=10000, net_debt=2000-5000= -3000 (net cash), equity = 10000 - (-3000) = 13000
    eq = equity_value(conn, "600519.SH", 10000)
    assert eq == 13000.0

    # No data → return EV as-is
    eq2 = equity_value(conn, "NONEXIST", 5000)
    assert eq2 == 5000.0


def test_dcf_value_raises_on_bad_params():
    from lab.engine.micro.dcf import dcf_value
    import pytest

    with pytest.raises(ValueError, match="must be >"):
        dcf_value([100, 200], growth_rate=0.10, discount_rate=0.02, terminal_growth=0.03)


def test_dcf_cli_reads_from_db(tmp_path):
    import subprocess, os, sys
    from lab.engine.db import get_db, _connections

    _connections.clear()
    db_dir = str(tmp_path)
    os.environ["ECO_DB_DIR"] = db_dir

    conn = get_db("micro")
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf) VALUES (?, ?, ?)""",
        ("600519.SH", "2024-12-31", 1000))
    conn.commit()
    _connections.clear()

    r = subprocess.run(
        [sys.executable, "lab/scripts/dcf.py", "--code", "600519.SH",
         "--growth", "0.10", "--growth-years", "1",
         "--terminal-growth", "0.03", "--discount", "0.08"],
        capture_output=True, text=True,
        env={**os.environ, "ECO_DB_DIR": db_dir}
    )
    assert r.returncode == 0
    assert "DCF" in r.stdout


def test_dcf_cli_no_data_returns_error():
    import subprocess, os, sys
    env = {**os.environ, "ECO_DB_DIR": "/tmp/test_dcf_no_data"}
    r = subprocess.run(
        [sys.executable, "lab/scripts/dcf.py", "--code", "NONEXIST",
         "--growth", "0.10"],
        capture_output=True, text=True, env=env
    )
    assert r.returncode == 1
    assert "未找到" in r.stderr
