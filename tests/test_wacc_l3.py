"""
Phase 5: wacc_l3 测试
ADR-002 决策 3、4、5
"""

import pytest


def _make_conn(
    tmp_path,
    interest_expense=500,
    total_debt=10000,
    pretax_income=2000,
    income_tax=400,
    total_liabilities=15000,
    market_cap=50000,
):
    """辅助：创建带财务数据的 micro.db 连接。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")

    # 写入 financial_statements（最近 3 年）
    for i, year in enumerate(["2022-12-31", "2023-12-31", "2024-12-31"]):
        conn.execute(
            """INSERT OR REPLACE INTO financial_statements
               (code, report_date, interest_expense, pretax_income, income_tax,
                total_liabilities, fcf)
               VALUES (?,?,?,?,?,?,?)""",
            (
                "000725.SZ",
                year,
                interest_expense * (1 + i * 0.05),
                pretax_income,
                income_tax,
                total_liabilities,
                1000,
            ),
        )
    # 写入 securities（market_cap 模拟：用 shares * price）
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding, currency, current_price, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            "000725.SZ",
            "CN",
            "BOE",
            "半导体",
            10000,  # shares
            "CNY",
            market_cap / 10000,  # price such that market_cap = shares * price
            "2024-01-01",
        ),
    )
    conn.commit()
    return conn


# ── 正常场景 ─────────────────────────────────────────────────────────────────


def test_wacc_l3_normal(tmp_path):
    """正常财务数据 → wacc_l3 返回合理结果，所有关键字段存在。"""
    conn = _make_conn(tmp_path)
    from lab.engine.micro.wacc import wacc_l3

    result = wacc_l3("000725.SZ", conn, rf=0.025, industry="半导体")
    assert "wacc" in result
    assert "re" in result
    assert "rd" in result
    assert "tax" in result
    assert "de_ratio" in result
    assert "method" in result
    assert "degradation_reason" in result
    assert 0.05 < result["wacc"] < 0.25


def test_wacc_l3_method_is_l3(tmp_path):
    """正常路径下 method == 'L3'。"""
    conn = _make_conn(tmp_path)
    from lab.engine.micro.wacc import wacc_l3

    result = wacc_l3("000725.SZ", conn, rf=0.025, industry="半导体")
    assert result["method"] == "L3"


# ── 降级：interest_expense 缺失 ──────────────────────────────────────────────


def test_wacc_l3_rd_degradation_when_no_interest(tmp_path):
    """interest_expense 缺失 → rd 降级为 Rf+2%，degradation_reason 非空。"""
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")

    # 写入不含 interest_expense 的数据
    conn.execute(
        """INSERT OR REPLACE INTO financial_statements
           (code, report_date, pretax_income, income_tax, total_liabilities, fcf)
           VALUES (?,?,?,?,?,?)""",
        ("000725.SZ", "2024-12-31", 2000, 400, 15000, 1000),
    )
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding, currency, current_price, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "CN", "BOE", "半导体", 10000, "CNY", 5.0, "2024-01-01"),
    )
    conn.commit()

    from lab.engine.micro.wacc import wacc_l3

    result = wacc_l3("000725.SZ", conn, rf=0.025)
    assert abs(result["rd"] - 0.045) < 1e-6  # Rf + 2% = 2.5% + 2% = 4.5%
    assert result["degradation_reason"] != ""


# ── 降级：pretax_income <= 0 → 国家税率 ──────────────────────────────────────


def test_wacc_l3_tax_degradation_when_pretax_nonpositive(tmp_path):
    """pretax_income <= 0 → 降级到 Damodaran 国家税率，degradation_reason 非空。"""
    conn = _make_conn(tmp_path, pretax_income=0, income_tax=0)
    from lab.engine.micro.wacc import wacc_l3

    result = wacc_l3("000725.SZ", conn, rf=0.025)
    # CN 国家税率 = 25%
    assert abs(result["tax"] - 0.25) < 0.01
    assert "tax" in result["degradation_reason"]


# ── 零负债 → WACC ≈ Re ───────────────────────────────────────────────────────


def test_wacc_l3_zero_debt_wacc_equals_re(tmp_path):
    """D=0 时 WACC 应退化为 Re（权益成本）。"""
    conn = _make_conn(tmp_path, total_liabilities=0, total_debt=0)
    from lab.engine.micro.wacc import wacc_l3

    result = wacc_l3("000725.SZ", conn, rf=0.025)
    assert abs(result["wacc"] - result["re"]) < 1e-4


# ── wacc_l2 保留作 sanity ────────────────────────────────────────────────────


def test_wacc_l2_is_capm():
    """wacc_l2 等价于旧 capm 函数。"""
    from lab.engine.micro.wacc import wacc_l2, capm

    assert wacc_l2(rf=0.03, beta=1.2, erp=0.06) == capm(rf=0.03, beta=1.2, erp=0.06)
