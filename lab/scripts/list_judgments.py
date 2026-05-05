#!/usr/bin/env python3
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.meta.judgment import list_judgments


def main():
    parser = argparse.ArgumentParser(description="List judgments")
    parser.add_argument("--status")
    parser.add_argument("--type", choices=["macro", "micro"])
    parser.add_argument("--last", type=int)
    args = parser.parse_args()

    conn = get_db("meta")
    rows = list_judgments(conn, status=args.status, type=args.type, last_n=args.last)
    for r in rows:
        print(f"{r['id']} | {r['type']:5} | {r['stage']:10} | {r['confidence']:6} | {r['status']:10} | {r['timestamp'][:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
