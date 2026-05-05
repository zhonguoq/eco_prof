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
