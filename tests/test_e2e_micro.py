"""
端到端 Benchmark 测试 — 微观引擎 v2
ADR-002 决策验收：三场景 / L3 WACC / Damodaran / 渲染报告

- 不依赖网络（mock DB 预填数据，跳过 fetch 和 WebSearch）
- 三市场各一只：000725.SZ（A股）/ 00700.HK（港股）/ AAPL（美股）
- 验证 ADR-002 规定的可观测行为，不测内部实现
"""

import os
import sqlite3
import subprocess
import sys

import pytest

# 脚本目录（相对于 repo root）
_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "lab", "scripts")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _run(script_name: str, args: list, db_dir: str):
    """Run a lab script with ECO_DB_DIR pointed at db_dir."""
    script = os.path.join(_SCRIPTS, script_name)
    env = os.environ.copy()
    env["ECO_DB_DIR"] = str(db_dir)
    return subprocess.run(
        [sys.executable, script] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=_REPO_ROOT,
    )


def _fresh_conn(db_dir: str, db_name: str):
    """Open a fresh sqlite3 connection (bypasses lab connection cache)."""
    path = os.path.join(str(db_dir), f"{db_name}.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
def seeded_micro(tmp_path):
    """三只股票 × 5年 FCF + securities（含 market/industry/shares/price）+ macro Rf。"""
    from lab.engine.db import get_db

    conn = get_db("micro")
    macro = get_db("macro")

    # (code, market, industry, shares, price, currency, fcf_list,
    #  interest_expense, pretax_income, income_tax, total_liabilities)
    STOCKS = [
        (
            "000725.SZ",
            "CN",
            "Semiconductor",
            36_710_000_000.0,
            5.0,
            "CNY",
            [8e9, 9e9, 10e9, 11e9, 12e9],
            1e9,
            5e9,
            1.25e9,
            50e9,
        ),
        (
            "00700.HK",
            "HK",
            "Technology",
            9_600_000_000.0,
            400.0,
            "HKD",
            [100e9, 120e9, 140e9, 160e9, 180e9],
            5e9,
            100e9,
            15e9,
            200e9,
        ),
        (
            "AAPL",
            "US",
            "Technology",
            15_600_000_000.0,
            180.0,
            "USD",
            [90e9, 95e9, 100e9, 105e9, 110e9],
            3e9,
            115e9,
            29e9,
            290e9,
        ),
    ]

    for (
        code,
        market,
        industry,
        shares,
        price,
        currency,
        fcf_list,
        ie,
        pi,
        it,
        tl,
    ) in STOCKS:
        for i, fcf in enumerate(fcf_list):
            year = 2019 + i
            conn.execute(
                """INSERT OR REPLACE INTO financial_statements
                   (code, report_date, fcf, operating_cf, capex,
                    interest_expense, pretax_income, income_tax, total_liabilities)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (code, f"{year}-12-31", fcf, fcf + 0.5e9, -0.5e9, ie, pi, it, tl),
            )
        conn.execute(
            """INSERT OR REPLACE INTO securities
               (code, market, name, industry, shares_outstanding,
                currency, current_price, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, market, code, industry, shares, currency, price, "2026-05-06"),
        )
    conn.commit()

    # macro: Rf 数据（CN10Y / DGS10 / HK10Y）
    for series_id, value in [("CN10Y", 0.025), ("DGS10", 0.045), ("HK10Y", 0.040)]:
        macro.execute(
            "INSERT OR REPLACE INTO series (series_id, date, value) VALUES (?, ?, ?)",
            (series_id, "2026-05-06", value),
        )
    macro.commit()

    return tmp_path


# ── ADR #3: estimate_params 输出含 L3 WACC ──────────────────────────────────


def test_estimate_params_shows_l3_wacc_cn(seeded_micro):
    """A股：estimate_params 输出含 WACC (L3) 分解（ADR-002 决策 #3）。"""
    r = _run(
        "estimate_params.py", ["--code", "000725.SZ", "--country", "CN"], seeded_micro
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "WACC (L3)" in out or "L3" in out


def test_estimate_params_shows_l3_wacc_hk(seeded_micro):
    """港股：estimate_params 输出含 WACC (L3) 分解（ADR-002 决策 #3）。"""
    r = _run(
        "estimate_params.py", ["--code", "00700.HK", "--country", "HK"], seeded_micro
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "WACC (L3)" in out or "L3" in out


def test_estimate_params_shows_l3_wacc_us(seeded_micro):
    """美股：estimate_params 输出含 WACC (L3) 分解（ADR-002 决策 #3）。"""
    r = _run("estimate_params.py", ["--code", "AAPL", "--country", "US"], seeded_micro)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "WACC (L3)" in out or "L3" in out


# ── ADR #2: build_scenarios 生成三场景 ──────────────────────────────────────


def test_build_scenarios_three_rows(seeded_micro):
    """build_scenarios.py 写入三条记录（base/bull/bear）到 scenarios 表（ADR-002 决策 #2/#13）。"""
    r = _run(
        "build_scenarios.py",
        ["--code", "000725.SZ", "--country", "CN", "--analyst-mid", "0.10"],
        seeded_micro,
    )
    assert r.returncode == 0, r.stderr
    conn = _fresh_conn(seeded_micro, "micro")
    rows = conn.execute(
        "SELECT scenario_name FROM scenarios WHERE code='000725.SZ'"
    ).fetchall()
    names = {r["scenario_name"] for r in rows}
    assert names == {"base", "bull", "bear"}


# ── ADR #3: r 字段来自 L3，wacc_l2_sanity 不为 NULL ─────────────────────────


def test_build_scenarios_wacc_l2_sanity_not_null(seeded_micro):
    """scenarios 表有 wacc_l2_sanity 字段且不为 NULL（ADR-002 决策 #3）。"""
    _run(
        "build_scenarios.py",
        ["--code", "000725.SZ", "--country", "CN", "--analyst-mid", "0.10"],
        seeded_micro,
    )
    conn = _fresh_conn(seeded_micro, "micro")
    row = conn.execute(
        "SELECT wacc_l2_sanity FROM scenarios WHERE code='000725.SZ' AND scenario_name='base'"
    ).fetchone()
    assert row is not None
    assert row["wacc_l2_sanity"] is not None


def test_build_scenarios_r_is_l3_not_l2(seeded_micro):
    """r（折现率）字段来自 L3 WACC，与 wacc_l2_sanity（纯 CAPM）不同（ADR-002 决策 #3）。
    数据已包含 interest_expense + liabilities，故 L3 可完整计算，≠ L2。"""
    _run(
        "build_scenarios.py",
        ["--code", "000725.SZ", "--country", "CN", "--analyst-mid", "0.10"],
        seeded_micro,
    )
    conn = _fresh_conn(seeded_micro, "micro")
    row = conn.execute(
        "SELECT r, wacc_l2_sanity FROM scenarios WHERE code='000725.SZ' AND scenario_name='base'"
    ).fetchone()
    assert row is not None
    # L3 与 L2 数值不同（D/V 权重引入 Rd 贡献，两者必然不等）
    assert abs(row["r"] - row["wacc_l2_sanity"]) > 1e-6


# ── ADR #15: render 生成含三场景的 HTML ──────────────────────────────────────


def _build_and_render(code: str, country: str, out_dir, db_dir):
    """辅助：先 build_scenarios，再 render_micro，返回 HTML 路径。"""
    _run(
        "build_scenarios.py",
        ["--code", code, "--country", country, "--analyst-mid", "0.10"],
        db_dir,
    )
    _run(
        "render_micro.py",
        ["--code", code, "--dcf", "--out-dir", str(out_dir)],
        db_dir,
    )
    # render_micro.py 在 out_dir/<code>_dcf.html 或 <code>_micro.html
    for fname in os.listdir(str(out_dir)):
        if fname.endswith(".html"):
            return os.path.join(str(out_dir), fname)
    return None


def test_render_micro_html_has_three_scenarios(seeded_micro, tmp_path):
    """render_micro.py 输出 HTML 含三场景标签（ADR-002 决策 #15）。"""
    html_path = _build_and_render("000725.SZ", "CN", tmp_path / "report", seeded_micro)
    assert html_path is not None, "HTML 文件未生成"
    html = open(html_path).read()
    assert "bear" in html.lower() or "bear" in html
    assert "base" in html.lower() or "base" in html
    assert "bull" in html.lower() or "bull" in html


def test_render_micro_html_has_valuation_badge(seeded_micro, tmp_path):
    """render_micro.py 输出 HTML 含 Buffett 30% 安全边际估值标签（ADR-002 决策 #15）。"""
    html_path = _build_and_render("000725.SZ", "CN", tmp_path / "report2", seeded_micro)
    assert html_path is not None, "HTML 文件未生成"
    html = open(html_path).read()
    # valuation_badge 输出低估/合理/高估
    assert any(kw in html for kw in ["低估", "合理", "高估"])


# ── ADR #15: 估值合理性（数量级检验）────────────────────────────────────────


def test_intrinsic_value_sane_range(seeded_micro):
    """base 场景的每股内在价值在 0.1×price ~ 100×price 范围内（ADR-002 决策 #15）。"""
    from lab.engine.db import get_db
    from lab.engine.micro.dcf import dcf_value

    # 先 build_scenarios
    _run(
        "build_scenarios.py",
        ["--code", "000725.SZ", "--country", "CN", "--analyst-mid", "0.10"],
        seeded_micro,
    )

    micro_conn = _fresh_conn(seeded_micro, "micro")
    row = micro_conn.execute(
        "SELECT g1, N, gt, r, base_fcf_method FROM scenarios "
        "WHERE code='000725.SZ' AND scenario_name='base'"
    ).fetchone()
    assert row is not None

    fcf_rows = micro_conn.execute(
        "SELECT fcf FROM financial_statements WHERE code='000725.SZ' "
        "AND fcf IS NOT NULL ORDER BY report_date ASC"
    ).fetchall()
    fcf_list = [r["fcf"] for r in fcf_rows]

    sec = micro_conn.execute(
        "SELECT shares_outstanding, current_price FROM securities WHERE code='000725.SZ'"
    ).fetchone()

    ev = dcf_value(
        fcf_list,
        growth_rate=row["g1"],
        growth_years=row["N"],
        terminal_growth=row["gt"],
        discount_rate=row["r"],
        base_fcf_method=row["base_fcf_method"] or "mean3",
    )
    per_share_iv = ev / sec["shares_outstanding"]
    price = sec["current_price"]

    assert per_share_iv > price * 0.1, f"内在价值过低: {per_share_iv:.4f} < 0.1×{price}"
    assert per_share_iv < price * 100, f"内在价值过高: {per_share_iv:.4f} > 100×{price}"


# ── Happy path: 完整流程无报错（无网络版）────────────────────────────────────


def _full_pipeline(code: str, country: str, db_dir, report_dir):
    """estimate_params → build_scenarios → render_micro，返回 (all_ok, html_path)。"""
    r1 = _run("estimate_params.py", ["--code", code, "--country", country], db_dir)
    if r1.returncode != 0:
        return False, r1.stderr
    r2 = _run(
        "build_scenarios.py",
        ["--code", code, "--country", country, "--analyst-mid", "0.10"],
        db_dir,
    )
    if r2.returncode != 0:
        return False, r2.stderr
    os.makedirs(str(report_dir), exist_ok=True)
    r3 = _run(
        "render_micro.py",
        ["--code", code, "--dcf", "--out-dir", str(report_dir)],
        db_dir,
    )
    if r3.returncode != 0:
        return False, r3.stderr
    html_files = [f for f in os.listdir(str(report_dir)) if f.endswith(".html")]
    return len(html_files) > 0, str(report_dir)


def test_full_pipeline_no_network_cn(seeded_micro, tmp_path):
    """A股完整流程：estimate → build_scenarios → render → HTML 存在。"""
    ok, info = _full_pipeline("000725.SZ", "CN", seeded_micro, tmp_path / "cn")
    assert ok, f"Pipeline 失败: {info}"


def test_full_pipeline_no_network_hk(seeded_micro, tmp_path):
    """港股完整流程：estimate → build_scenarios → render → HTML 存在。"""
    ok, info = _full_pipeline("00700.HK", "HK", seeded_micro, tmp_path / "hk")
    assert ok, f"Pipeline 失败: {info}"


def test_full_pipeline_no_network_us(seeded_micro, tmp_path):
    """美股完整流程：estimate → build_scenarios → render → HTML 存在。"""
    ok, info = _full_pipeline("AAPL", "US", seeded_micro, tmp_path / "us")
    assert ok, f"Pipeline 失败: {info}"
