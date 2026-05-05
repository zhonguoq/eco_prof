#!/usr/bin/env python3
import argparse
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.micro.dcf import dcf_value, sensitivity_matrix
from lab.engine.db import get_db


def main():
    parser = argparse.ArgumentParser(description="DCF valuation")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--growth", type=float, default=0.10)
    parser.add_argument("--growth-years", type=int, default=5)
    parser.add_argument("--terminal-growth", type=float, default=0.03)
    parser.add_argument("--discount", type=float, default=0.08)
    parser.add_argument("--sensitivity", help="Comma-separated factors")
    parser.add_argument("--output", choices=["table", "chart"], default="table")
    args = parser.parse_args()

    if not args.code:
        parser.print_help()
        return 0

    fcf_list = [100, 110, 120, 130, 140]

    if args.sensitivity:
        matrix = sensitivity_matrix(fcf_list)
        print(json.dumps(matrix, indent=2))
    else:
        val = dcf_value(fcf_list, growth_rate=args.growth,
                        growth_years=args.growth_years,
                        terminal_growth=args.terminal_growth,
                        discount_rate=args.discount)
        print(f"DCF 估值: {val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
