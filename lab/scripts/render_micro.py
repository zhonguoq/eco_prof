#!/usr/bin/env python3
"""
render_micro.py — 三场景估值报告 HTML（Phase 6）

用法:
  python lab/scripts/render_micro.py --code 000725.SZ --dcf
  python lab/scripts/render_micro.py --code 000725.SZ --dcf --out-dir /tmp
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.micro.dcf import dcf_value, _normalize_base
from lab.chart_lib.micro_charts import (
    valuation_badge,
    scenario_table,
    fcf_history_chart,
    sensitivity_heatmap,
    industry_ranking,
)


_REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def _read_scenarios(conn, code):
    rows = conn.execute(
        """SELECT scenario_name, g1, N, gt, r, wacc_l2_sanity, base_fcf_method
           FROM scenarios WHERE code=? ORDER BY scenario_name""",
        (code,),
    ).fetchall()
    return [dict(row) for row in rows]


def _read_security(conn, code):
    row = conn.execute("SELECT * FROM securities WHERE code=?", (code,)).fetchone()
    return dict(row) if row else {}


def _read_fcf_list(conn, code):
    rows = conn.execute(
        """SELECT report_date, fcf FROM financial_statements
           WHERE code=? AND fcf IS NOT NULL
           ORDER BY report_date ASC""",
        (code,),
    ).fetchall()
    return [r["fcf"] for r in rows], [r["report_date"][:4] for r in rows]


def _compute_intrinsic_values(scenarios, fcf_list):
    """为每个场景计算每股企业价值（EV，不除股数）。"""
    if len(fcf_list) < 1:
        for s in scenarios:
            s["intrinsic_value"] = None
        return scenarios

    for s in scenarios:
        try:
            ev = dcf_value(
                fcf_list,
                growth_rate=s["g1"],
                growth_years=s["N"],
                terminal_growth=s["gt"],
                discount_rate=s["r"],
                base_fcf_method=s.get("base_fcf_method", "mean3"),
            )
            s["intrinsic_value"] = ev
        except Exception:
            s["intrinsic_value"] = None
        s.setdefault("degradation_reason", None)
    return scenarios


def _build_header_card(sec, scenarios, current_price, currency):
    """返回头部卡片 HTML。"""
    base = next((s for s in scenarios if s["scenario_name"] == "base"), None)
    badge_html = ""
    rel_html = ""
    if base and base.get("intrinsic_value") and current_price:
        ratio = base["intrinsic_value"] / current_price
        diff = (base["intrinsic_value"] - current_price) / current_price
        badge_html = valuation_badge(ratio)
        rel_html = f"base 场景相对现价: <b>{diff:+.1%}</b>"

    name = sec.get("name", "")
    code = sec.get("code", "")
    market = sec.get("market", "")
    price_str = f"{current_price:.2f} {currency}" if current_price else "N/A"

    return f"""
<div style="background:#1a237e;color:#fff;padding:16px 24px;border-radius:8px;margin-bottom:16px">
  <h2 style="margin:0">{name} ({code}) &nbsp; <small style="font-size:0.7em">{market}</small></h2>
  <p style="margin:4px 0">当前价: <b>{price_str}</b> &nbsp; {badge_html}</p>
  <p style="margin:4px 0;font-size:0.9em;color:#ccc">{rel_html}</p>
</div>
"""


def _build_params_card(sec, fcf_list):
    """参数来源透明卡片 HTML。"""
    from lab.engine.micro.wacc import terminal_growth as tg_fn, LONG_TERM_GDP
    from lab.engine.micro.damodaran import load_erp

    country = sec.get("market", "CN")
    erp = load_erp(country)
    gt = tg_fn(country=country)
    gdp = LONG_TERM_GDP.get(country, 0.04)
    cagr_note = f"FCF 数据: {len(fcf_list)} 期" if fcf_list else "FCF: 无数据"

    return f"""
<div style="background:#263238;color:#eceff1;padding:12px 20px;border-radius:8px;
            margin-bottom:16px;font-size:0.88em">
  <b>参数来源透明</b>
  <ul style="margin:6px 0;padding-left:20px">
    <li>ERP ({country}): {erp:.2%}（Damodaran ctryprem.csv）</li>
    <li>gt = min(Rf, GDP) = {gt:.2%}（GDP={gdp:.1%}）</li>
    <li>{cagr_note}</li>
    <li>WACC: L3 完整公式（见 build_scenarios.py）</li>
  </ul>
</div>
"""


def main():
    parser = argparse.ArgumentParser(description="Render micro DCF report")
    parser.add_argument("--code", help="Stock code")
    parser.add_argument("--industry", help="Industry name")
    parser.add_argument(
        "--dcf",
        action="store_true",
        default=True,
        help="Include DCF valuation (default on)",
    )
    parser.add_argument("--out-dir", default=None, help="Output directory")
    args = parser.parse_args()

    if not args.code and not args.industry:
        parser.print_help()
        return 0

    conn = get_db("micro")
    out_dir = args.out_dir or _REPORT_DIR
    os.makedirs(out_dir, exist_ok=True)

    if args.industry:
        # 行业排名（原逻辑保留）
        from lab.chart_lib.composite import compose

        chart = industry_ranking(result=[], stocks=[], title=f"{args.industry} 排名")
        today = datetime.now().strftime("%Y%m%d")
        filename = os.path.join(out_dir, f"micro_{args.industry}_{today}.html")
        compose(f"{args.industry} 排名", [chart], filename=filename)
        print(f"报告已生成: {filename}")
        return 0

    code = args.code
    sec = _read_security(conn, code)
    fcf_list, years = _read_fcf_list(conn, code)
    current_price = sec.get("current_price") or 0
    currency = sec.get("currency", "CNY")
    shares = sec.get("shares_outstanding") or 1

    # ── 读取 / 计算场景 ──
    scenarios = _read_scenarios(conn, code)
    if scenarios:
        scenarios = _compute_intrinsic_values(scenarios, fcf_list)
    else:
        # 无 scenarios 表数据 → 生成最简报告
        scenarios = []

    # ── 区块 1: 头部 ──
    header_html = _build_header_card(sec, scenarios, current_price, currency)

    # ── 区块 2: 三场景表 ──
    table_html = ""
    if scenarios:
        table_html = f"<h3>三场景估值对照</h3>" + scenario_table(
            scenarios, current_price=current_price, currency=currency
        )

    # ── 区块 3: 参数来源 ──
    params_html = _build_params_card(sec, fcf_list)

    # ── 区块 4: FCF 历史图 ──
    fcf_chart_html = ""
    if len(fcf_list) >= 2:
        base_fcf = _normalize_base(fcf_list, "mean3")
        fcf_bar = fcf_history_chart(
            fcf_list=fcf_list, base_fcf=base_fcf, years=years, title=f"{code} 历史 FCF"
        )
        fcf_chart_html = fcf_bar.render_embed()

    # ── 区块 5: 敏感性热力图 ──
    heatmap_html = ""
    base_s = next((s for s in scenarios if s["scenario_name"] == "base"), None)
    if base_s and len(fcf_list) >= 1:
        base_fcf = _normalize_base(fcf_list, "mean3")
        hmap = sensitivity_heatmap(
            base_scenario=base_s,
            base_fcf=base_fcf,
            shares=shares,
            current_price=current_price,
            title=f"{code} 敏感性分析",
        )
        heatmap_html = hmap.render_embed()

    # ── 拼装 HTML ──
    today = datetime.now().strftime("%Y%m%d")
    filename = os.path.join(out_dir, f"micro_{code}_{today}.html")

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>{sec.get("name", code)} 微观报告</title>
<style>
  body {{ font-family: 'PingFang SC', sans-serif; background:#121212; color:#eceff1;
         max-width:1100px; margin:0 auto; padding:24px; }}
  h3 {{ color:#90caf9; }}
</style>
</head>
<body>
{header_html}
{table_html}
{params_html}
<h3>历史 FCF</h3>
{fcf_chart_html}
<h3>敏感性分析</h3>
{heatmap_html}
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"报告已生成: {filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
