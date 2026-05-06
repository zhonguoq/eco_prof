#!/usr/bin/env python3
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.micro.dcf import dcf_value, sensitivity_matrix, batch_dcf, equity_value
from lab.engine.db import get_db


def main():
    parser = argparse.ArgumentParser(description="DCF valuation")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--growth", type=float, default=0.10)
    parser.add_argument("--growth-years", type=int, default=5)
    parser.add_argument("--terminal-growth", type=float, default=0.03)
    parser.add_argument("--discount", type=float, default=0.08)
    parser.add_argument("--sensitivity", action="store_true",
                        help="Show sensitivity matrix")
    parser.add_argument("--equity", action="store_true",
                        help="Deduct net debt to get equity value")
    parser.add_argument("--years-back", type=int, default=5,
                        help="Years of FCF history to read from DB")
    parser.add_argument("--output", choices=["table", "chart"], default="table")
    args = parser.parse_args()

    if not args.code:
        parser.print_help()
        return 0

    conn = get_db("micro")
    ev = batch_dcf(conn, args.code,
                   growth_rate=args.growth,
                   growth_years=args.growth_years,
                   terminal_growth=args.terminal_growth,
                   discount_rate=args.discount,
                   years_back=args.years_back)

    if ev is None:
        print(f"错误: 未找到 {args.code} 的 FCF 数据", file=sys.stderr)
        return 1

    if args.sensitivity:
        fcf_rows = conn.execute(
            """SELECT fcf FROM financial_statements
               WHERE code=? AND fcf IS NOT NULL
               AND report_date LIKE '%-12-31'
               ORDER BY report_date DESC LIMIT ?""",
            (args.code, args.years_back)
        ).fetchall()
        fcf_list = [r["fcf"] for r in fcf_rows]
        fcf_list.reverse()
        matrix = sensitivity_matrix(fcf_list)
        print(json.dumps(matrix, indent=2, ensure_ascii=False))
    elif args.equity:
        eq = equity_value(conn, args.code, ev)
        print(f"DCF 企业价值: {ev}")
        print(f"股权价值 (扣除净债务): {eq}")
    else:
        print(f"DCF 估值: {ev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
