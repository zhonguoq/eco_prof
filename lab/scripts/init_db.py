#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db


def main():
    for name in ("macro", "meta", "micro"):
        conn = get_db(name)
        table_count = conn.execute(
            "SELECT count(*) AS cnt FROM sqlite_master WHERE type='table'"
        ).fetchone()["cnt"]
        print(f"{name}.db: {table_count} tables created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
