#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.macro.fetcher import fetch_all


def main():
    parser = argparse.ArgumentParser(description="Fetch macro data from FRED")
    parser.add_argument("--full", action="store_true", help="Fetch full history")
    args = parser.parse_args()

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set", file=sys.stderr)
        return 1

    conn = get_db("macro")
    results = fetch_all(conn, api_key)
    for series_id, count in results.items():
        print(f"{series_id}: {count} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
