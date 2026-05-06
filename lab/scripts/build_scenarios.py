#!/usr/bin/env python3
"""
build_scenarios.py — 生成三场景参数并写入 scenarios 表
用法:
  python lab/scripts/build_scenarios.py --code 000725.SZ --analyst-mid 0.10
  python lab/scripts/build_scenarios.py --code 000725.SZ \
      --analyst-high 0.12 --analyst-mid 0.10 --analyst-low 0.08
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.scenarios import build_all_scenarios, save_scenarios
from lab.engine.micro.wacc import wacc_l3, wacc_l2, terminal_growth


def main():
    parser = argparse.ArgumentParser(description="Build DCF scenarios for a stock")
    parser.add_argument("--code", required=True, help="Stock code, e.g. 000725.SZ")
    parser.add_argument("--analyst-high", type=float, default=None)
    parser.add_argument("--analyst-mid", type=float, default=None)
    parser.add_argument("--analyst-low", type=float, default=None)
    parser.add_argument("--country", default="CN", help="CN/HK/US")
    parser.add_argument("--industry", default=None, help="行业（用于 Damodaran β）")
    parser.add_argument(
        "--rf",
        type=float,
        default=None,
        help="Risk-free rate; auto-read from macro.db if omitted",
    )
    args = parser.parse_args()

    conn = get_db("micro")

    # ── 读取历史 FCF ──
    rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code=? AND fcf IS NOT NULL
           ORDER BY report_date ASC""",
        (args.code,),
    ).fetchall()
    fcf_list = [r["fcf"] for r in rows]

    if len(fcf_list) < 2:
        print(f"错误: {args.code} FCF 数据不足 (需 ≥2 期)", file=sys.stderr)
        return 1

    # ── 无风险利率 ──
    rf = args.rf
    macro = get_db("macro")
    if rf is None:
        series_id = {"CN": "CN10Y", "US": "DGS10", "HK": "HK10Y"}.get(
            args.country, "DGS10"
        )
        row = macro.execute(
            f"SELECT value FROM series WHERE series_id=? ORDER BY date DESC LIMIT 1",
            (series_id,),
        ).fetchone()
        if row:
            rf = float(row["value"])
        else:
            rf = {"CN": 0.025, "US": 0.045, "HK": 0.04}.get(args.country, 0.04)

    # ── wacc_l3 (L3 完整公式) ──
    l3 = wacc_l3(args.code, conn, rf=rf, industry=args.industry, country=args.country)
    r_l3 = l3["wacc"]
    beta_l3 = l3["beta"]

    # ── wacc_l2 sanity ──
    from lab.engine.micro.damodaran import load_erp

    erp = load_erp(args.country)
    r_l2 = wacc_l2(rf=rf, beta=beta_l3, erp=erp)

    # ── 终端增长率 ──
    gt_base = terminal_growth(country=args.country, macro_conn=macro)

    # ── 分析师共识 ──
    analyst = None
    if args.analyst_mid is not None:
        analyst = {"mid": args.analyst_mid}
        analyst["high"] = (
            args.analyst_high if args.analyst_high else args.analyst_mid + 0.03
        )
        analyst["low"] = (
            args.analyst_low if args.analyst_low else args.analyst_mid - 0.03
        )

    # ── 构建场景（用 L3 wacc 覆写 r） ──
    scenarios = build_all_scenarios(
        fcf_list=fcf_list,
        rf=rf,
        beta=beta_l3,
        country=args.country,
        analyst=analyst,
    )
    # 将 L3 结果注入每个场景的 r 字段，并写入 wacc_l2_sanity
    for name in scenarios:
        offset = 0.01 if name == "bear" else 0.0
        scenarios[name]["r"] = round(r_l3 + offset, 6)
        scenarios[name]["wacc_l2_sanity"] = r_l2

    save_scenarios(conn, args.code, scenarios)

    # ── 打印 ──
    print(f"=== {args.code} 三场景参数 ===\n")
    print(f"  WACC (L3): {r_l3:.2%}")
    print(f"  WACC (L2 sanity): {r_l2:.2%}")
    print(f"  beta ({l3['beta_source']}): {beta_l3:.4f}")
    print(f"  degradation: {l3['degradation_reason'] or 'none'}")
    print()
    header = f"{'场景':<8} {'g1':>8} {'N':>4} {'gt':>8} {'r':>8} {'method':<10}"
    print(header)
    print("-" * len(header))
    for name in ("bear", "base", "bull"):
        p = scenarios[name]
        print(
            f"{name:<8} {p['g1']:>8.2%} {p['N']:>4} "
            f"{p['gt']:>8.2%} {p['r']:>8.2%} {p['base_fcf_method']:<10}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
