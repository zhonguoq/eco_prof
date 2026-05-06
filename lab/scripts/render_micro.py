#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.chart_lib.micro_charts import dcf_comparison, industry_ranking, valuation_history
from lab.chart_lib.composite import compose
from lab.engine.db import get_db
from lab.engine.micro.dcf import batch_dcf


def _read_price_data(conn, code):
    rows = conn.execute(
        """SELECT date, close FROM stock_prices
           WHERE code=? ORDER BY date DESC LIMIT 260""",
        (code,)
    ).fetchall()
    closes = [r["close"] for r in rows]
    dates = [r["date"] for r in rows]
    return closes, dates


def main():
    parser = argparse.ArgumentParser(description="Render micro reports")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--industry", help="Industry name")
    parser.add_argument("--dcf", action="store_true",
                        help="Include DCF valuation chart")
    args = parser.parse_args()

    if not args.code and not args.industry:
        parser.print_help()
        return 0

    conn = get_db("micro")
    charts = []

    if args.code:
        closes, dates = _read_price_data(conn, args.code)

        if args.dcf:
            ev = batch_dcf(conn, args.code,
                           growth_rate=0.10, growth_years=5,
                           terminal_growth=0.03, discount_rate=0.08)
            dcf_val = ev if ev else 0
        else:
            dcf_val = 0

        current_price = closes[0] if closes else 0
        year_high = max(closes) if closes else 0
        year_low = min(closes) if closes else 0

        if dcf_val > 0:
            charts.append(dcf_comparison(
                dcf_value=dcf_val,
                current_price=current_price,
                year_high=year_high,
                year_low=year_low,
                title=f"{args.code} DCF 估值",
            ))

        if len(closes) >= 2:
            year_labels = [d[:4] for d in dates if len(d) >= 4]
            unique_years = []
            unique_closes = []
            seen = set()
            for y, c in zip(year_labels, closes):
                if y not in seen:
                    seen.add(y)
                    unique_years.append(y)
                    unique_closes.append(c)
            if len(unique_years) >= 2:
                charts.append(valuation_history(
                    code=args.code,
                    pe_list=unique_closes,
                    pb_list=[c * 0.3 for c in unique_closes],
                    years=unique_years,
                    title=f"{args.code} 历史价格",
                ))

    if args.industry:
        charts.append(industry_ranking(
            result=[],
            stocks=[],
            title=f"{args.industry} 排名",
        ))

    if not charts:
        print("数据不足以生成图表", file=sys.stderr)
        return 1

    filename = f"micro_report_{args.code or args.industry}.html"
    path = compose("微观报告", charts, filename=filename)
    print(f"报告已生成: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
