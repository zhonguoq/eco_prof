import os
import sqlite3

_DB_DIR = None

def _resolve_dir():
    if _DB_DIR is not None:
        return _DB_DIR
    env = os.environ.get("ECO_DB_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(__file__), "..", "db")

_connections = {}

_SCHEMAS = {
    "macro": [
        """CREATE TABLE IF NOT EXISTS series (
            series_id TEXT,
            date TEXT,
            value REAL,
            PRIMARY KEY (series_id, date)
        )""",
        """CREATE TABLE IF NOT EXISTS series_meta (
            series_id TEXT PRIMARY KEY,
            name TEXT,
            unit TEXT,
            freq TEXT,
            source TEXT,
            last_updated TEXT
        )""",
    ],
    "meta": [
        """CREATE TABLE IF NOT EXISTS judgments (
            id TEXT PRIMARY KEY,
            type TEXT,
            timestamp TEXT,
            stage TEXT,
            signals TEXT,
            confidence TEXT,
            key_question TEXT,
            prediction TEXT,
            verification_window TEXT,
            context TEXT,
            actual_outcome TEXT,
            status TEXT DEFAULT 'active'
        )""",
        """CREATE TABLE IF NOT EXISTS iterations (
            id TEXT PRIMARY KEY,
            judgment_id TEXT,
            timestamp TEXT,
            trigger TEXT,
            old_principle TEXT,
            new_principle TEXT,
            FOREIGN KEY (judgment_id) REFERENCES judgments(id)
        )""",
    ],
    "micro": [
        """CREATE TABLE IF NOT EXISTS stock_prices (
            code TEXT,
            date TEXT,
            open REAL,
            close REAL,
            high REAL,
            low REAL,
            volume REAL,
            PRIMARY KEY (code, date)
        )""",
        """CREATE TABLE IF NOT EXISTS financial_statements (
            code TEXT,
            report_date TEXT,
            statement_type TEXT,
            data TEXT,
            PRIMARY KEY (code, report_date, statement_type)
        )""",
    ],
}

def _init_tables(conn, name):
    for stmt in _SCHEMAS.get(name, []):
        conn.execute(stmt)
    conn.commit()

def get_db(name):
    if name not in _connections:
        db_dir = _resolve_dir()
        os.makedirs(db_dir, exist_ok=True)
        path = os.path.join(db_dir, f"{name}.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        _init_tables(conn, name)
        _connections[name] = conn
    return _connections[name]
