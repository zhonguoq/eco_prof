#!/usr/bin/env python3
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.growth import cagr, linear_trend
from lab.engine.micro.beta import calc_beta, industry_relevered_beta
from lab.engine.micro.wacc import (
    capm,
    default_industry,
    wacc_l3,
    wacc_l2,
    terminal_growth,
    LONG_TERM_GDP,
)
from lab.engine.micro.damodaran import load_erp


def main():
    parser = argparse.ArgumentParser(
        description="Estimate DCF parameters from historical data"
    )
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--industry", default="", help="Industry name for WACC default")
    parser.add_argument("--country", default="CN", help="CN/HK/US")
    parser.add_argument(
        "--benchmark", default="000300.SH", help="Benchmark index for beta calculation"
    )
    parser.add_argument(
        "--rf", type=float, default=None, help="Risk-free rate (10Y bond yield)"
    )
    args = parser.parse_args()

    if not args.code:
        parser.print_help()
        return 0

    conn = get_db("micro")
    macro = get_db("macro")

    # ── FCF growth rates ──
    fcf_rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code=? AND fcf IS NOT NULL
           ORDER BY report_date ASC""",
        (args.code,),
    ).fetchall()
    fcf_list = [r["fcf"] for r in fcf_rows]

    print(f"=== {args.code} 参数估计 ===")
    print()

    if len(fcf_list) >= 2:
        cagr_rate = cagr(fcf_list)
        trend_rate = linear_trend(fcf_list)
        print(f"FCF 历史数据: {len(fcf_list)} 期")
        print(
            f"  CAGR (年复合增长率): {cagr_rate:.2%}"
            if cagr_rate
            else "  CAGR: 无法计算"
        )
        print(
            f"  线性趋势增长率:      {trend_rate:.2%}"
            if trend_rate
            else "  线性趋势增长率: 无法计算"
        )
    else:
        print("FCF 数据不足 (需 ≥2 期)")
    print()

    # ── 无风险利率 ──
    rf = args.rf
    if rf is None:
        series_id = {"CN": "CN10Y", "US": "DGS10", "HK": "HK10Y"}.get(
            args.country, "DGS10"
        )
        row = macro.execute(
            "SELECT value FROM series WHERE series_id=? ORDER BY date DESC LIMIT 1",
            (series_id,),
        ).fetchone()
        if row:
            rf = float(row["value"])
        else:
            rf = {"CN": 0.025, "US": 0.045, "HK": 0.04}.get(args.country, 0.04)

    # ── Beta ──
    self_beta = calc_beta(conn, args.code, benchmark=args.benchmark)
    industry = args.industry or None
    dam_beta, dam_source = industry_relevered_beta(
        args.code, conn, industry=industry, country=args.country
    )

    # ── WACC L3 ──
    l3 = wacc_l3(args.code, conn, rf=rf, industry=industry, country=args.country)
    erp = load_erp(args.country)
    beta_for_l2 = self_beta or 1.0
    r_l2 = wacc_l2(rf=rf, beta=beta_for_l2, erp=erp)

    # ── terminal growth ──
    gt = terminal_growth(country=args.country, macro_conn=macro)
    gdp = LONG_TERM_GDP.get(args.country, 0.04)

    print(f"无风险利率 (Rf):                    {rf:.2%}")
    print(f"Re (CAPM):                          {l3['re']:.2%}")
    print(f"Rd (cost of debt):                  {l3['rd']:.2%}")
    print(f"effective tax rate:                 {l3['tax']:.2%}")
    print(f"D/V: {l3['dv']:.2%}   E/V: {l3['ev']:.2%}")
    print(f"WACC (L3):                          {l3['wacc']:.2%}   ← 完整公式")
    print(f"WACC (L2 sanity):                   {r_l2:.2%}   ← 原 CAPM")
    print(
        f"Industry β (Damodaran, re-levered):  {dam_beta:.4f}   "
        f"vs   Self β: {f'{self_beta:.4f}' if self_beta else 'N/A'}"
    )
    print(
        f"gt = min(Rf, GDP):                   {gt:.2%}  "
        f"(country={args.country}, Rf={rf:.1%}, GDP={gdp:.1%})"
    )
    if l3["degradation_reason"]:
        print(f"\n[降级信息] {l3['degradation_reason']}")
    print()
    print("提示: 以上为自动估计值，请与用户讨论后确认最终参数。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
