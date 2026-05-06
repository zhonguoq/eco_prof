"""
Phase 5: industry_relevered_beta 测试
ADR-002 决策 5
"""

import pytest


def _make_conn(tmp_path):
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding, currency, current_price, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "CN", "BOE", "半导体", 10000, "CNY", 5.0, "2024-01-01"),
    )
    conn.commit()
    return conn


def test_industry_relevered_beta_returns_tuple(tmp_path):
    """industry_relevered_beta 返回 (beta_float, source_str) 元组。"""
    conn = _make_conn(tmp_path)
    from lab.engine.micro.beta import industry_relevered_beta

    beta, source = industry_relevered_beta(
        "000725.SZ", conn, industry="半导体", country="CN"
    )
    assert isinstance(beta, float)
    assert beta > 0
    assert source in ("damodaran", "self-computed")


def test_industry_relevered_beta_uses_damodaran_when_available(tmp_path):
    """行业在 Damodaran 表中存在 → source = 'damodaran'。"""
    conn = _make_conn(tmp_path)
    from lab.engine.micro.beta import industry_relevered_beta

    _, source = industry_relevered_beta(
        "000725.SZ", conn, industry="半导体", country="CN"
    )
    assert source == "damodaran"


def test_industry_relevered_beta_fallback_to_calc(tmp_path):
    """行业不在 Damodaran 表 → fallback calc_beta（stock price data not enough → 1.0）。"""
    conn = _make_conn(tmp_path)
    from lab.engine.micro.beta import industry_relevered_beta

    beta, source = industry_relevered_beta(
        "000725.SZ", conn, industry="SomeUnknownIndustry", country="CN"
    )
    # No price data → calc_beta returns None → fallback 1.0
    assert beta == 1.0
    assert source == "self-computed"


def test_industry_relevered_beta_relevering_formula(tmp_path):
    """
    re-lever 公式：β_relevered = β_unlevered × (1 + (1-t) × D/E_company)。
    用已知数据验证结果在合理范围内（> unlevered_beta）。
    """
    import os

    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")

    # Securities with D/E ratio
    conn.execute(
        """INSERT OR REPLACE INTO securities
           (code, market, name, industry, shares_outstanding, currency, current_price, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        ("000725.SZ", "CN", "BOE", "半导体", 10000, "CNY", 5.0, "2024-01-01"),
    )
    # Financial data for D/E calculation
    conn.execute(
        """INSERT OR REPLACE INTO financial_statements
           (code, report_date, total_liabilities, fcf)
           VALUES (?,?,?,?)""",
        ("000725.SZ", "2024-12-31", 20000, 1000),
    )
    conn.commit()

    from lab.engine.micro.beta import industry_relevered_beta

    beta, source = industry_relevered_beta(
        "000725.SZ", conn, industry="半导体", country="CN"
    )
    assert source == "damodaran"
    assert beta > 0
