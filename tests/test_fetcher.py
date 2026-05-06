import sys
import pandas as pd

def test_fetch_one_writes_series_to_db():
    from lab.engine.macro.fetcher import fetch_one
    from lab.engine.db import get_db

    conn = get_db("macro")

    dates = pd.date_range("2020-01-01", "2020-01-10")
    values = [1.0 + i * 0.1 for i in range(10)]
    mock_series = pd.Series(values, index=dates)

    class MockFred:
        def get_series(self, series_id):
            return mock_series

    n = fetch_one("FEDFUNDS", conn, api_key="fake", fred=MockFred())
    assert n == 10
    row = conn.execute(
        "SELECT count(*) AS cnt FROM series WHERE series_id='FEDFUNDS'"
    ).fetchone()
    assert row["cnt"] == 10

def test_fetch_one_is_idempotent():
    from lab.engine.macro.fetcher import fetch_one
    from lab.engine.db import get_db

    conn = get_db("macro")
    dates = pd.date_range("2020-01-01", "2020-01-05")
    mock_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)

    class MockFred:
        def get_series(self, series_id):
            return mock_series

    fetch_one("GDPC1", conn, api_key="fake", fred=MockFred())
    fetch_one("GDPC1", conn, api_key="fake", fred=MockFred())

    row = conn.execute(
        "SELECT count(*) AS cnt FROM series WHERE series_id='GDPC1'"
    ).fetchone()
    assert row["cnt"] == 5

def test_get_latest_date_returns_max():
    from lab.engine.macro.fetcher import get_latest_date
    from lab.engine.db import get_db

    conn = get_db("macro")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('TEST', '2020-01-01', 1.0)")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('TEST', '2020-06-15', 2.0)")
    conn.commit()

    assert get_latest_date(conn, "TEST") == "2020-06-15"
    assert get_latest_date(conn, "NONEXIST") is None

def test_cli_requires_api_key():
    import subprocess, os
    env = {**os.environ, "ECO_DB_DIR": "/tmp/test_cli_fred", "FRED_API_KEY": ""}
    r = subprocess.run(
        [sys.executable, "lab/scripts/fetch_macro.py"],
        capture_output=True, text=True, env=env
    )
    assert r.returncode == 1
    assert "FRED_API_KEY" in r.stderr

def test_fetch_financial_statements_is_idempotent():
    from lab.engine.micro.fetcher import fetch_financial_statements
    from lab.engine.db import get_db

    conn = get_db("micro")
    df = pd.DataFrame({
        "REPORT_DATE": pd.to_datetime(["2024-12-31"]),
        "NETCASH_OPERATE": [20000.0],
        "CONSTRUCT_LONG_ASSET": [2000.0],
    })

    fetch_financial_statements("000001.SZ", conn, mock_cash_flow=df, mock_balance=None)
    fetch_financial_statements("000001.SZ", conn, mock_cash_flow=df, mock_balance=None)

    rows = conn.execute(
        "SELECT count(*) AS c FROM financial_statements WHERE code='000001.SZ'"
    ).fetchone()
    assert rows["c"] == 1


def test_fetch_financials_cli_accepts_code():
    import subprocess, os, sys
    env = {**os.environ, "ECO_DB_DIR": "/tmp/test_cli_fin"}
    r = subprocess.run(
        [sys.executable, "lab/scripts/fetch_financials.py", "--code", "600519.SH",
         "--no-prices", "--no-statements"],
        capture_output=True, text=True, env=env
    )
    assert r.returncode == 0
    assert "600519.SH" in r.stdout


def test_fetch_financials_cli_requires_code():
    import subprocess, os, sys
    r = subprocess.run(
        [sys.executable, "lab/scripts/fetch_financials.py"],
        capture_output=True, text=True
    )
    assert r.returncode == 1
    assert "--code" in r.stderr


def test_fetch_all_calls_all_series():
    from lab.engine.macro.fetcher import fetch_all, FRED_SERIES
    from lab.engine.db import get_db

    conn = get_db("macro")

    class MockFred:
        def get_series(self, series_id):
            dates = pd.date_range("2020-01-01", "2020-01-03")
            return pd.Series([1.0, 2.0, 3.0], index=dates)

    results = fetch_all(conn, api_key="fake", fred=MockFred())
    assert set(results.keys()) == set(FRED_SERIES)
    for series_id, count in results.items():
        assert count == 3, f"{series_id} got {count} rows"


# ── Slice 1: 财报数据管道 ─────────────────────────────────

def test_fetch_financial_statements_writes_structured_fields():
    from lab.engine.micro.fetcher import fetch_financial_statements
    from lab.engine.db import get_db

    conn = get_db("micro")

    cf_df = pd.DataFrame({
        "REPORT_DATE": pd.to_datetime(["2024-12-31", "2023-12-31"]),
        "NETCASH_OPERATE": [20000.0, 18000.0],
        "CONSTRUCT_LONG_ASSET": [2000.0, 1500.0],
    })
    bs_df = pd.DataFrame({
        "REPORT_DATE": pd.to_datetime(["2024-12-31", "2023-12-31"]),
        "MONETARYFUNDS": [50000.0, 45000.0],
        "TOTAL_LIABILITIES": [30000.0, 28000.0],
    })

    n = fetch_financial_statements("600519.SH", conn,
                                   mock_cash_flow=cf_df,
                                   mock_balance=bs_df)
    assert n == 2

    rows = conn.execute(
        "SELECT report_date, fcf, operating_cf, capex, cash, total_liabilities "
        "FROM financial_statements WHERE code='600519.SH' ORDER BY report_date"
    ).fetchall()
    assert len(rows) == 2

    # 2023: FCF = 18000 - 1500 = 16500
    assert rows[0]["report_date"] == "2023-12-31"
    assert rows[0]["fcf"] == 16500.0
    assert rows[0]["operating_cf"] == 18000.0
    assert rows[0]["capex"] == 1500.0
    assert rows[0]["cash"] == 45000.0
    assert rows[0]["total_liabilities"] == 28000.0

    # 2024: FCF = 20000 - 2000 = 18000
    assert rows[1]["report_date"] == "2024-12-31"
    assert rows[1]["fcf"] == 18000.0
    assert rows[1]["operating_cf"] == 20000.0
    assert rows[1]["capex"] == 2000.0
    assert rows[1]["cash"] == 50000.0
    assert rows[1]["total_liabilities"] == 30000.0
