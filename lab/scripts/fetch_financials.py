#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.fetcher import fetch_stock_data


def main():
    parser = argparse.ArgumentParser(description="Fetch financial data")
    parser.add_argument("--code", help="Stock code")
    args = parser.parse_args()

    if not args.code:
        print("--code is required", file=sys.stderr)
        return 1

    conn = get_db("micro")
    n = fetch_stock_data(args.code, conn)
    print(f"{args.code}: {n} price rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
