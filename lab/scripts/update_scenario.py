#!/usr/bin/env python3
"""
update_scenario.py — 更新 scenarios 表中指定字段
用法:
  python lab/scripts/update_scenario.py --code 000725.SZ --scenario bull --N 7
  python lab/scripts/update_scenario.py --code 000725.SZ --scenario base --g1 0.08 --r 0.10
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.scenarios import update_scenario


def main():
    parser = argparse.ArgumentParser(description="Update a single DCF scenario")
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--scenario", required=True, help="base | bull | bear")
    parser.add_argument("--g1", type=float, default=None)
    parser.add_argument("--N", type=int, default=None)
    parser.add_argument("--gt", type=float, default=None)
    parser.add_argument("--r", type=float, default=None)
    parser.add_argument("--base-fcf-method", dest="base_fcf_method", default=None)
    args = parser.parse_args()

    conn = get_db("micro")

    # 收集非 None 字段
    updates = {}
    if args.g1 is not None:
        updates["g1"] = args.g1
    if args.N is not None:
        updates["N"] = args.N
    if args.gt is not None:
        updates["gt"] = args.gt
    if args.r is not None:
        updates["r"] = args.r
    if args.base_fcf_method is not None:
        updates["base_fcf_method"] = args.base_fcf_method

    if not updates:
        print("没有指定要更新的字段", file=sys.stderr)
        return 1

    update_scenario(conn, args.code, args.scenario, **updates)
    print(f"已更新 {args.code} / {args.scenario}: {updates}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
