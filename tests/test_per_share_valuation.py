"""
Phase 3: 每股估值 + Buffett 分级标签测试
ADR-002 决策 15
"""

import pytest
import os


def test_per_share_value_divides_by_shares():
    """equity_value 除以 shares_outstanding 得到每股价值。"""
    from lab.engine.micro.valuation import per_share_value

    assert per_share_value(equity=100_000, shares=10_000) == pytest.approx(10.0)


def test_per_share_value_large_numbers():
    from lab.engine.micro.valuation import per_share_value

    # 1万亿 / 400亿股 = 25元
    assert per_share_value(
        equity=1_000_000_000_000, shares=40_000_000_000
    ) == pytest.approx(25.0)


def test_per_share_value_zero_shares_raises():
    from lab.engine.micro.valuation import per_share_value

    with pytest.raises(ValueError, match="shares_outstanding"):
        per_share_value(equity=100_000, shares=0)


# ── Buffett 分级标签 ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "price,intrinsic,expected_label",
    [
        (60, 100, "深度低估"),  # 0.60 < 0.70
        (75, 100, "低估"),  # 0.70 ≤ 0.75 < 0.90
        (89, 100, "低估"),  # 0.89 < 0.90
        (95, 100, "合理"),  # 0.90 ≤ 0.95 < 1.10
        (110, 100, "合理"),  # exactly 1.10 → 合理 boundary (< 1.10 is 合理)
        (115, 100, "高估"),  # 1.10 ≤ 1.15 < 1.30
        (130, 100, "高估"),  # exactly 1.30 → boundary
        (131, 100, "深度高估"),  # > 1.30
    ],
)
def test_buffett_label(price, intrinsic, expected_label):
    from lab.engine.micro.valuation import buffett_label

    assert buffett_label(price=price, intrinsic=intrinsic) == expected_label


def test_buffett_label_exact_boundaries():
    """边界值：0.70 / 0.90 / 1.10 / 1.30 的归属。"""
    from lab.engine.micro.valuation import buffett_label

    assert buffett_label(70, 100) == "低估"  # 0.70 ≥ 0.70 → 低估
    assert buffett_label(90, 100) == "合理"  # 0.90 ≥ 0.90 → 合理
    assert (
        buffett_label(110, 100) == "合理"
    )  # ratio=1.10, < 1.10 is False → 高估? No, ratio=1.10/100=1.10
    # ADR说 0.9-1.1 ⚪ 合理，1.1-1.3 🔴 高估
    # ratio=1.10 → on boundary. Let's say [1.10, 1.30) is 高估
    assert buffett_label(111, 100) == "高估"
    assert buffett_label(130, 100) == "高估"  # [1.10, 1.30] — 1.30 ≤ 1.30 → 高估
    assert buffett_label(131, 100) == "深度高估"


def test_scenario_table_output(tmp_path):
    """三场景对照表正确计算每股内在价值与现价对比。"""
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")

    # 写入 securities
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, shares_outstanding, current_price, currency, market, updated_at)
           VALUES ('TEST.SZ', 1000, 8.0, 'CNY', 'A', '2026-01-01')"""
    )
    # 写入 scenarios
    for name, g1 in [("base", 0.10), ("bull", 0.15), ("bear", 0.06)]:
        conn.execute(
            """INSERT OR REPLACE INTO scenarios
               (code, scenario_name, g1, N, gt, r, base_fcf_method, updated_at)
               VALUES ('TEST.SZ', ?, ?, 5, 0.03, 0.08, 'mean3', '2026-01-01')""",
            (name, g1),
        )
    # 写入 FCF
    for i, fcf in enumerate([700, 800, 900], start=1):
        conn.execute(
            "INSERT OR REPLACE INTO financial_statements (code, report_date, fcf) VALUES (?,?,?)",
            ("TEST.SZ", f"202{i}-12-31", fcf),
        )
    conn.commit()

    from lab.engine.micro.valuation import build_scenario_table

    table = build_scenario_table(conn, "TEST.SZ")

    assert len(table) == 3
    scenarios_present = {row["scenario"] for row in table}
    assert scenarios_present == {"base", "bull", "bear"}

    for row in table:
        assert "per_share_value" in row
        assert "vs_current_pct" in row
        assert "label" in row
        assert row["per_share_value"] > 0

    _connections.clear()
