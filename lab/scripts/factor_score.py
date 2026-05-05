#!/usr/bin/env python3
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.micro.factors import compute_scores


def main():
    parser = argparse.ArgumentParser(description="Factor score ranking")
    parser.add_argument("--industry", help="Industry name")
    parser.add_argument("--factors", default="pe,roe,peg",
                        help="Comma-separated factor names")
    parser.add_argument("--weights", help="Comma-separated factor:weight pairs")
    parser.add_argument("--output", choices=["table", "chart"], default="table")
    parser.add_argument("--show-data", action="store_true")
    args = parser.parse_args()

    if not args.industry:
        parser.print_help()
        return 0

    factor_list = [f.strip() for f in args.factors.split(",")]
    weights = None
    if args.weights:
        pairs = [w.split(":") for w in args.weights.split(",")]
        weights = {p[0]: float(p[1]) for p in pairs}

    stocks = [
        {"code": "600519.SH", "name": "茅台", "pe": 25, "roe": 0.32, "peg": 1.2, "pb": 8},
        {"code": "000858.SZ", "name": "五粮液", "pe": 18, "roe": 0.28, "peg": 0.9, "pb": 5},
        {"code": "000568.SZ", "name": "泸州老窖", "pe": 22, "roe": 0.30, "peg": 1.1, "pb": 7},
    ]

    result = compute_scores(stocks, factors=factor_list, weights=weights)

    if args.output == "table":
        print(f"{'排名':>4} {'代码':<12} {'名称':<10} {'综合分':>8}")
        for r in result:
            s = next(s for s in stocks if s["code"] == r["code"])
            print(f"{r['rank']:>4} {r['code']:<12} {s.get('name', ''):<10} {r['score']:>8.3f}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
