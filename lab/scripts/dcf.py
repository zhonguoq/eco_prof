#!/usr/bin/env python3
"""
dcf.py — DCF 估值入口
v2 新增：--scenario base|bull|bear|all  从 scenarios 表读参数，输出三场景对照表
v1 旧 flags 保留（--growth/--growth-years/--terminal-growth/--discount）供兼容
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.micro.dcf import dcf_value, sensitivity_matrix, batch_dcf, equity_value
from lab.engine.db import get_db


def _print_scenario_table(table: list) -> None:
    """打印三场景对照表。"""
    header = f"{'场景':<6} {'每股内在价值':>12} {'现价':>8} {'vs现价':>8} {'安全边际':<6} 判读"
    print(header)
    print("-" * len(header))
    for row in table:
        vs = (
            f"{row['vs_current_pct']:+.1f}%"
            if row["vs_current_pct"] is not None
            else "N/A"
        )
        print(
            f"{row['scenario']:<6} {row['per_share_value']:>12.2f} "
            f"{row['current_price']:>8.2f} {vs:>8}  {row['label']}"
        )


def main():
    parser = argparse.ArgumentParser(description="DCF valuation")
    parser.add_argument("--code", help="Stock code")
    # v2 新增
    parser.add_argument(
        "--scenario",
        choices=["base", "bull", "bear", "all"],
        default=None,
        help="从 scenarios 表读参数（v2）",
    )
    # v1 兼容 flags
    parser.add_argument("--growth", type=float, default=0.10)
    parser.add_argument("--growth-years", type=int, default=5)
    parser.add_argument("--terminal-growth", type=float, default=0.03)
    parser.add_argument("--discount", type=float, default=0.08)
    parser.add_argument(
        "--sensitivity", action="store_true", help="Show sensitivity matrix"
    )
    parser.add_argument(
        "--equity", action="store_true", help="Deduct net debt to get equity value"
    )
    parser.add_argument(
        "--years-back", type=int, default=5, help="Years of FCF history to read from DB"
    )
    parser.add_argument("--output", choices=["table", "chart"], default="table")
    args = parser.parse_args()

    if not args.code:
        parser.print_help()
        return 0

    conn = get_db("micro")

    # ── v2 路径：从 scenarios 表读参数 ──
    if args.scenario is not None:
        from lab.engine.micro.valuation import build_scenario_table

        try:
            table = build_scenario_table(conn, args.code)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        if args.scenario != "all":
            table = [r for r in table if r["scenario"] == args.scenario]

        if not table:
            print(f"错误: 未找到场景 {args.scenario}", file=sys.stderr)
            return 1

        print(f"\n=== {args.code} DCF 三场景估值 ===\n")
        _print_scenario_table(table)

        # Buffett 总判读（基于 base 场景）
        base_rows = [r for r in table if r["scenario"] == "base"]
        if base_rows:
            print(f"\n[总判读] {base_rows[0]['label']}（基于 base 场景）")
        return 0

    # ── v1 兼容路径 ──
    ev = batch_dcf(
        conn,
        args.code,
        growth_rate=args.growth,
        growth_years=args.growth_years,
        terminal_growth=args.terminal_growth,
        discount_rate=args.discount,
        years_back=args.years_back,
    )

    if ev is None:
        print(f"错误: 未找到 {args.code} 的 FCF 数据", file=sys.stderr)
        return 1

    if args.sensitivity:
        fcf_rows = conn.execute(
            """SELECT fcf FROM financial_statements
               WHERE code=? AND fcf IS NOT NULL
               AND report_date LIKE '%-12-31'
               ORDER BY report_date DESC LIMIT ?""",
            (args.code, args.years_back),
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
