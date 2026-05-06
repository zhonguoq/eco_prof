import sqlite3

def test_get_db_returns_connection():
    from lab.engine.db import get_db
    conn = get_db("macro")
    assert isinstance(conn, sqlite3.Connection)

def test_macro_db_has_expected_tables():
    from lab.engine.db import get_db
    conn = get_db("macro")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "series" in tables
    assert "series_meta" in tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(series)").fetchall()}
    assert cols == {"series_id", "date", "value"}

def test_meta_db_has_expected_tables():
    from lab.engine.db import get_db
    conn = get_db("meta")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "judgments" in tables
    assert "iterations" in tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(judgments)").fetchall()}
    assert "id" in cols and "type" in cols and "confidence" in cols

def test_micro_db_has_expected_tables():
    from lab.engine.db import get_db
    conn = get_db("micro")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "stock_prices" in tables
    assert "financial_statements" in tables
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(stock_prices)").fetchall()}
    assert "code" in cols and "date" in cols

def test_init_db_creates_all_databases():
    from lab.engine.db import get_db
    for name in ("macro", "meta", "micro"):
        conn = get_db(name)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert len(tables) >= 1, f"{name}.db has no tables"

def test_get_db_is_idempotent():
    from lab.engine.db import get_db
    c1 = get_db("macro")
    c2 = get_db("macro")
    assert c1 is c2


def test_migrate_old_financial_statements_schema(tmp_path):
    """Old schema with statement_type should be auto-migrated to new schema."""
    from lab.engine.db import get_db, _connections
    import os

    _connections.clear()
    db_dir = str(tmp_path)
    os.environ["ECO_DB_DIR"] = db_dir

    old_conn = sqlite3.connect(os.path.join(db_dir, "micro.db"))
    old_conn.execute("""CREATE TABLE IF NOT EXISTS financial_statements (
        code TEXT, report_date TEXT, statement_type TEXT, data TEXT,
        PRIMARY KEY (code, report_date, statement_type)
    )""")
    old_conn.commit()
    old_conn.close()

    _connections.clear()
    conn = get_db("micro")
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(financial_statements)"
    ).fetchall()}

    assert "fcf" in cols, f"fcf missing, got {cols}"
    assert "operating_cf" in cols
    assert "capex" in cols
    assert "cash" in cols
    assert "total_liabilities" in cols
    assert "statement_type" not in cols
