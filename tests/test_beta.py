def test_estimate_params_cli(tmp_path):
    import subprocess, os, sys
    from lab.engine.db import get_db, _connections

    _connections.clear()
    db_dir = str(tmp_path)
    os.environ["ECO_DB_DIR"] = db_dir

    conn = get_db("micro")
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf) VALUES (?, ?, ?)""",
        ("600519.SH", "2024-12-31", 1000))
    conn.execute("""INSERT OR REPLACE INTO financial_statements
        (code, report_date, fcf) VALUES (?, ?, ?)""",
        ("600519.SH", "2023-12-31", 900))
    conn.execute("""INSERT OR REPLACE INTO stock_prices
        (code, date, close) VALUES (?, ?, ?)""",
        ("600519.SH", "2024-01-01", 100))
    conn.execute("""INSERT OR REPLACE INTO stock_prices
        (code, date, close) VALUES (?, ?, ?)""",
        ("600519.SH", "2024-01-02", 102))
    conn.execute("""INSERT OR REPLACE INTO stock_prices
        (code, date, close) VALUES (?, ?, ?)""",
        ("000300.SH", "2024-01-01", 3000))
    conn.execute("""INSERT OR REPLACE INTO stock_prices
        (code, date, close) VALUES (?, ?, ?)""",
        ("000300.SH", "2024-01-02", 3010))
    conn.commit()
    _connections.clear()

    r = subprocess.run(
        [sys.executable, "lab/scripts/estimate_params.py",
         "--code", "600519.SH"],
        capture_output=True, text=True,
        env={**os.environ, "ECO_DB_DIR": db_dir}
    )
    assert r.returncode == 0
    assert "CAGR" in r.stdout or "增长" in r.stdout


def test_calc_beta_from_db():
    from lab.engine.micro.beta import calc_beta
    from lab.engine.db import get_db

    conn = get_db("micro")

    # Stock prices (rising) and benchmark (rising more)
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    for i, d in enumerate(dates):
        close_stock = 100.0 + i * 2.0   # 100, 102, 104, 106, 108
        close_bm = 3000.0 + i * 10.0     # 3000, 3010, 3020, 3030, 3040
        conn.execute("INSERT OR REPLACE INTO stock_prices (code, date, close) VALUES (?, ?, ?)",
                     ("600519.SH", d, close_stock))
        conn.execute("INSERT OR REPLACE INTO stock_prices (code, date, close) VALUES (?, ?, ?)",
                     ("000300.SH", d, close_bm))
    conn.commit()

    # Stock returns: ~2%, benchmark returns: ~0.33%
    # Beta should be positive (>0)
    beta = calc_beta(conn, "600519.SH", benchmark="000300.SH")
    assert beta is not None
    assert beta > 0

    # Insufficient data → None
    beta2 = calc_beta(conn, "NONEXIST")
    assert beta2 is None
