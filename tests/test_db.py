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
