#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.fetcher import fetch_stock_data, fetch_financial_statements


def main():
    parser = argparse.ArgumentParser(description="Fetch financial data")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--no-prices", action="store_true",
                        help="Skip price data, fetch financial statements only")
    parser.add_argument("--no-statements", action="store_true",
                        help="Skip financial statements, fetch prices only")
    args = parser.parse_args()

    if not args.code:
        print("--code is required", file=sys.stderr)
        return 1

    conn = get_db("micro")
    n_prices = 0
    n_stmt = 0

    if not args.no_prices:
        n_prices = fetch_stock_data(args.code, conn)

    if not args.no_statements:
        n_stmt = fetch_financial_statements(args.code, conn)

    print(f"{args.code}: {n_prices} price rows, {n_stmt} statement rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
