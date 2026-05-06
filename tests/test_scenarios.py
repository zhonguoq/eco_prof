"""
Phase 2: scenarios 表 + resolver 测试
ADR-002 决策 11、12、13
"""

import pytest
import os
import sys


# ── resolver 单元测试 ──────────────────────────────────────────────────────


def test_resolver_translates_cagr():
    """'CAGR' 被翻译为 FCF 列表的复合增长率。"""
    from lab.engine.micro.scenarios import resolve_scenario

    # fcf=[100,121,146.41] → CAGR ≈ 21% (100*(1.21)^2=146.41... actually 1.21^2=1.4641, yes)
    # Wait: CAGR = (146.41/100)^(1/2) - 1 = 1.21 - 1 = 0.21
    result = resolve_scenario(
        "g1_cagr_ref",
        fcf_list=[100, 121, 146.41],
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst=None,
    )
    assert abs(result["g1"] - 0.21) < 0.001


def test_resolver_analyst_mid_used_as_base_g1():
    """analyst={'mid': 0.10} → base 场景 g1=0.10。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    scenarios = build_all_scenarios(
        fcf_list=[100, 110, 120, 130, 140],
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst={"high": 0.15, "mid": 0.10, "low": 0.06},
    )
    assert abs(scenarios["base"]["g1"] - 0.10) < 1e-6


def test_resolver_analyst_high_used_as_bull_g1():
    """analyst={'high': 0.15} → bull 场景 g1=0.15。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    scenarios = build_all_scenarios(
        fcf_list=[100, 110, 120, 130, 140],
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst={"high": 0.15, "mid": 0.10, "low": 0.06},
    )
    assert abs(scenarios["bull"]["g1"] - 0.15) < 1e-6


def test_resolver_no_analyst_fallback_cagr_plus_minus_3pct():
    """analyst=None → base=CAGR, bull=CAGR+3%, bear=CAGR-3%。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    # fcf list with ~10% CAGR: [100,110,121,133,146]
    fcf_list = [100, 110, 121, 133.1, 146.41]
    scenarios = build_all_scenarios(
        fcf_list=fcf_list,
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst=None,
    )
    cagr_val = scenarios["base"]["g1"]
    assert abs(scenarios["bull"]["g1"] - (cagr_val + 0.03)) < 1e-5
    assert abs(scenarios["bear"]["g1"] - (cagr_val - 0.03)) < 1e-5


def test_resolver_rf_translates_correctly():
    """r 字段使用 CAPM = rf + beta*ERP。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    rf, beta = 0.04, 1.0
    scenarios = build_all_scenarios(
        fcf_list=[100, 110, 120],
        rf=rf,
        beta=beta,
        country="CN",
        analyst={"high": 0.15, "mid": 0.10, "low": 0.06},
    )
    # CAPM = 0.04 + 1.0 * 0.06 = 0.10
    assert abs(scenarios["base"]["r"] - 0.10) < 1e-5


def test_resolver_min_rf_gdp_terminal_growth():
    """gt = min(Rf, LONG_TERM_GDP[country])。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    # CN GDP=4.5%, Rf=4% → gt=4%
    scenarios = build_all_scenarios(
        fcf_list=[100, 110, 120],
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst={"high": 0.15, "mid": 0.10, "low": 0.06},
    )
    assert abs(scenarios["base"]["gt"] - 0.04) < 1e-5


def test_resolver_bear_gt_lower_by_half_percent():
    """bear gt = base gt - 0.5%。"""
    from lab.engine.micro.scenarios import build_all_scenarios

    scenarios = build_all_scenarios(
        fcf_list=[100, 110, 120],
        rf=0.04,
        beta=1.0,
        country="CN",
        analyst={"high": 0.15, "mid": 0.10, "low": 0.06},
    )
    assert abs(scenarios["bear"]["gt"] - (scenarios["base"]["gt"] - 0.005)) < 1e-6


# ── DB 写入 / 读取 ─────────────────────────────────────────────────────────


def test_build_scenarios_writes_three_rows(tmp_path):
    """build_all_scenarios_to_db 写入 scenarios 表三行。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()

    from lab.engine.micro.scenarios import save_scenarios

    conn = get_db("micro")

    scenarios = {
        "base": {"g1": 0.10, "N": 5, "gt": 0.04, "r": 0.10, "base_fcf_method": "mean3"},
        "bull": {"g1": 0.15, "N": 7, "gt": 0.04, "r": 0.10, "base_fcf_method": "mean3"},
        "bear": {
            "g1": 0.06,
            "N": 5,
            "gt": 0.035,
            "r": 0.11,
            "base_fcf_method": "mean3",
        },
    }
    save_scenarios(conn, "000725.SZ", scenarios)

    rows = conn.execute(
        "SELECT scenario_name FROM scenarios WHERE code='000725.SZ' ORDER BY scenario_name"
    ).fetchall()
    names = [r["scenario_name"] for r in rows]
    assert names == ["base", "bear", "bull"]

    _connections.clear()


def test_update_scenario_partial_fields(tmp_path):
    """update_scenario 只修改指定字段，其余保持原值。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()

    from lab.engine.micro.scenarios import save_scenarios, update_scenario

    conn = get_db("micro")

    initial = {
        "base": {"g1": 0.10, "N": 5, "gt": 0.04, "r": 0.10, "base_fcf_method": "mean3"},
    }
    save_scenarios(conn, "000725.SZ", initial)

    update_scenario(conn, "000725.SZ", "base", N=7)

    row = conn.execute(
        "SELECT * FROM scenarios WHERE code='000725.SZ' AND scenario_name='base'"
    ).fetchone()
    assert row["N"] == 7
    assert abs(row["g1"] - 0.10) < 1e-6  # unchanged

    _connections.clear()


# ── CLI smoke tests ───────────────────────────────────────────────────────


def test_build_scenarios_cli_writes_db(tmp_path):
    """build_scenarios.py --code X --analyst-mid 0.10 → 写入 scenarios 三行。"""
    import subprocess

    env = {**os.environ, "ECO_DB_DIR": str(tmp_path)}

    # First seed some FCF data
    from lab.engine.db import get_db, _connections

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    _connections.clear()
    conn = get_db("micro")
    for year, fcf in [("2020-12-31", 800), ("2021-12-31", 900), ("2022-12-31", 1000)]:
        conn.execute(
            "INSERT OR REPLACE INTO financial_statements (code, report_date, fcf) VALUES (?,?,?)",
            ("000725.SZ", year, fcf),
        )
    conn.commit()
    _connections.clear()

    r = subprocess.run(
        [
            sys.executable,
            "lab/scripts/build_scenarios.py",
            "--code",
            "000725.SZ",
            "--analyst-mid",
            "0.10",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr

    _connections.clear()
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    conn2 = get_db("micro")
    rows = conn2.execute(
        "SELECT scenario_name FROM scenarios WHERE code='000725.SZ'"
    ).fetchall()
    assert len(rows) == 3
    _connections.clear()


def test_update_scenario_cli(tmp_path):
    """update_scenario.py --code X --scenario base --N 7 只改 N。"""
    import subprocess

    env = {**os.environ, "ECO_DB_DIR": str(tmp_path)}

    from lab.engine.db import get_db, _connections

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    _connections.clear()
    conn = get_db("micro")
    conn.execute(
        """INSERT OR REPLACE INTO scenarios
           (code, scenario_name, g1, N, gt, r, base_fcf_method, updated_at)
           VALUES ('000725.SZ','base',0.10,5,0.04,0.10,'mean3','2026-01-01')"""
    )
    conn.commit()
    _connections.clear()

    r = subprocess.run(
        [
            sys.executable,
            "lab/scripts/update_scenario.py",
            "--code",
            "000725.SZ",
            "--scenario",
            "base",
            "--N",
            "7",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr

    _connections.clear()
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    conn2 = get_db("micro")
    row = conn2.execute(
        "SELECT N, g1 FROM scenarios WHERE code='000725.SZ' AND scenario_name='base'"
    ).fetchone()
    assert row["N"] == 7
    assert abs(row["g1"] - 0.10) < 1e-6
    _connections.clear()
