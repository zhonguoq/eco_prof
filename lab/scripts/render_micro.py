#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.chart_lib.micro_charts import dcf_comparison, industry_ranking, valuation_history
from lab.chart_lib.composite import compose


def main():
    parser = argparse.ArgumentParser(description="Render micro reports")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--industry", help="Industry name")
    args = parser.parse_args()

    if not args.code and not args.industry:
        parser.print_help()
        return 0

    charts = []

    if args.code:
        charts.append(dcf_comparison(title=f"{args.code} DCF 估值"))
        charts.append(valuation_history(code=args.code, title=f"{args.code} 历史估值"))

    if args.industry:
        result = [
            {"code": "600519.SH", "score": 1.82, "rank": 1},
            {"code": "000858.SZ", "score": 1.21, "rank": 2},
        ]
        stocks = [
            {"code": "600519.SH", "name": "茅台"},
            {"code": "000858.SZ", "name": "五粮液"},
        ]
        charts.append(industry_ranking(result, stocks, title=f"{args.industry} 排名"))

    filename = f"micro_report_{args.code or args.industry}.html"
    path = compose("微观报告", charts, filename=filename)
    print(f"报告已生成: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
