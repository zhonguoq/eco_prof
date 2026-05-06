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
            fcf REAL,
            operating_cf REAL,
            capex REAL,
            cash REAL,
            total_liabilities REAL,
            revenue REAL,
            net_income REAL,
            pretax_income REAL,
            income_tax REAL,
            interest_expense REAL,
            equity REAL,
            data TEXT,
            PRIMARY KEY (code, report_date)
        )""",
        """CREATE TABLE IF NOT EXISTS scenarios (
            code TEXT,
            scenario_name TEXT,
            g1 REAL,
            N INTEGER,
            gt REAL,
            r REAL,
            wacc_l2_sanity REAL,
            base_fcf_method TEXT,
            updated_at TEXT,
            PRIMARY KEY (code, scenario_name)
        )""",
        """CREATE TABLE IF NOT EXISTS securities (
            code TEXT PRIMARY KEY,
            market TEXT,
            name TEXT,
            industry TEXT,
            shares_outstanding REAL,
            currency TEXT,
            current_price REAL,
            updated_at TEXT
        )""",
    ],
}


def _init_tables(conn, name):
    for stmt in _SCHEMAS.get(name, []):
        conn.execute(stmt)
    conn.commit()


_NEW_FINANCIAL_COLS = {
    "revenue": "REAL",
    "net_income": "REAL",
    "pretax_income": "REAL",
    "income_tax": "REAL",
    "interest_expense": "REAL",
    "equity": "REAL",
}

_NEW_SCENARIO_COLS = {
    "wacc_l2_sanity": "REAL",
}


def _migrate_db(conn, name):
    if name != "micro":
        return
    cursor = conn.execute("PRAGMA table_info(financial_statements)")
    existing = {row["name"] for row in cursor.fetchall()}

    # Old schema with statement_type → drop and recreate
    if "statement_type" in existing:
        conn.execute("DROP TABLE IF EXISTS financial_statements")
        for stmt in _SCHEMAS.get(name, []):
            if "financial_statements" in stmt:
                conn.execute(stmt)
        conn.commit()
        return

    # Add any missing Phase-4 columns via ALTER TABLE
    for col, col_type in _NEW_FINANCIAL_COLS.items():
        if col not in existing:
            conn.execute(
                f"ALTER TABLE financial_statements ADD COLUMN {col} {col_type}"
            )

    # Add Phase-5 wacc_l2_sanity to scenarios
    cursor2 = conn.execute("PRAGMA table_info(scenarios)")
    existing_sc = {row["name"] for row in cursor2.fetchall()}
    for col, col_type in _NEW_SCENARIO_COLS.items():
        if col not in existing_sc:
            conn.execute(f"ALTER TABLE scenarios ADD COLUMN {col} {col_type}")
    conn.commit()


def get_db(name):
    if name not in _connections:
        db_dir = _resolve_dir()
        os.makedirs(db_dir, exist_ok=True)
        path = os.path.join(db_dir, f"{name}.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        _init_tables(conn, name)
        _migrate_db(conn, name)
        _connections[name] = conn
    return _connections[name]
