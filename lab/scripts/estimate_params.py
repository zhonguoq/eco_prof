#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.growth import cagr, linear_trend
from lab.engine.micro.beta import calc_beta
from lab.engine.micro.wacc import capm, default_industry


def main():
    parser = argparse.ArgumentParser(description="Estimate DCF parameters from historical data")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--industry", default="",
                        help="Industry name for WACC default")
    parser.add_argument("--benchmark", default="000300.SH",
                        help="Benchmark index for beta calculation")
    parser.add_argument("--rf", type=float, default=None,
                        help="Risk-free rate (10Y bond yield)")
    args = parser.parse_args()

    if not args.code:
        parser.print_help()
        return 0

    conn = get_db("micro")

    # ── FCF growth rates ──
    fcf_rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code=? AND fcf IS NOT NULL
           ORDER BY report_date ASC""",
        (args.code,)
    ).fetchall()
    fcf_list = [r["fcf"] for r in fcf_rows]

    print(f"=== {args.code} 参数估计 ===")
    print()

    if len(fcf_list) >= 2:
        cagr_rate = cagr(fcf_list)
        trend_rate = linear_trend(fcf_list)
        print(f"FCF 历史数据: {len(fcf_list)} 期")
        print(f"  CAGR (年复合增长率): {cagr_rate:.2%}" if cagr_rate else "  CAGR: 无法计算")
        print(f"  线性趋势增长率:      {trend_rate:.2%}" if trend_rate else "  线性趋势增长率: 无法计算")
    else:
        print("FCF 数据不足 (需 ≥2 期)")
    print()

    # ── Beta ──
    beta = calc_beta(conn, args.code, benchmark=args.benchmark)
    if beta is not None:
        print(f"Beta (vs {args.benchmark}): {beta:.4f}")
    else:
        print(f"Beta: 无法计算 (需价格数据)")
    print()

    # ── WACC ──
    rf = args.rf
    if rf is None:
        macro = get_db("macro")
        row = macro.execute(
            "SELECT value FROM series WHERE series_id='DGS10' ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if row:
            rf = row["value"] / 100.0
        else:
            rf = 0.04  # default
    print(f"无风险利率 (Rf): {rf:.2%}")
    print()

    if beta is not None:
        wacc_capm = capm(rf=rf, beta=beta)
        print(f"CAPM WACC (Rf={rf:.2%}, Beta={beta:.4f}, ERP=6%): {wacc_capm:.2%}")

    wacc_ind = default_industry(args.industry or None)
    print(f"行业默认 WACC ({args.industry or '通用'}): {wacc_ind:.2%}")
    print(f"通用默认 WACC: 10.00%")
    print()

    print("提示: 以上为自动估计值，请与用户讨论后确认最终参数。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
