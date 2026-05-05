#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.meta.judgment import update_judgment


def main():
    parser = argparse.ArgumentParser(description="Update a judgment")
    parser.add_argument("--id", required=True)
    parser.add_argument("--outcome")
    parser.add_argument("--status", choices=["active", "confirmed", "disconfirmed"])
    args = parser.parse_args()

    conn = get_db("meta")
    update_judgment(conn, args.id, actual_outcome=args.outcome, status=args.status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
