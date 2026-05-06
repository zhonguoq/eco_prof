"""Unit tests for fetcher_us.py (Phase 4 #31).

Mock DataFrames use the real akshare ITEM_NAME values for US stocks
(verified against live AAPL data from eastmoney).
All tests use mock DataFrames — no real network calls.
"""

import pytest
import pandas as pd


# ── helpers ────────────────────────────────────────────────────────────────


def _make_us_df(items: dict, report_date="2024-09-30"):
    """
    Build a mock akshare-style US long DataFrame.
    US tables use column ITEM_NAME (not STD_ITEM_NAME).
    items: {ITEM_NAME: AMOUNT}
    """
    rows = [
        {
            "REPORT_DATE": pd.Timestamp(report_date),
            "ITEM_NAME": name,
            "AMOUNT": float(amount),
        }
        for name, amount in items.items()
    ]
    return pd.DataFrame(rows)


# ── _pivot_row: basic field extraction ───────────────────────────────────


def test_us_pivot_extracts_operating_cf():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 120000.0,
            "购买固定资产": 15000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["operating_cf"] == 120000.0


def test_us_pivot_extracts_capex():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 100000.0,
            "购买固定资产": 12000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["capex"] == 12000.0


def test_us_pivot_extracts_balance_fields():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 100000.0,
            "现金及现金等价物": 200000.0,
            "总负债": 300000.0,
            "股东权益合计": 150000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["cash"] == 200000.0
    assert result["total_liab"] == 300000.0
    assert result["equity"] == 150000.0


def test_us_pivot_extracts_income_fields():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 100000.0,
            "营业收入": 400000.0,
            "净利润": 90000.0,
            "持续经营税前利润": 110000.0,
            "所得税": 20000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["revenue"] == 400000.0
    assert result["net_income"] == 90000.0
    assert result["pretax_income"] == 110000.0
    assert result["income_tax"] == 20000.0


def test_us_pivot_interest_expense_is_none():
    """interest_expense not available in eastmoney US data → always None."""
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df({"经营活动产生的现金流量净额": 100000.0})
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result.get("interest_expense") is None


# ── alias fallback ─────────────────────────────────────────────────────────


def test_us_pivot_capex_alias_fallback():
    """Secondary capex alias 资本支出 should be used if primary absent."""
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 80000.0,
            "资本支出": 9000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["capex"] == 9000.0


def test_us_pivot_revenue_alias_fallback():
    """主营收入 is a valid alias for revenue."""
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df(
        {
            "经营活动产生的现金流量净额": 80000.0,
            "主营收入": 500000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result["revenue"] == 500000.0


# ── missing field → NULL, no exception ────────────────────────────────────


def test_us_pivot_missing_field_returns_none():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = _make_us_df({"经营活动产生的现金流量净额": 60000.0})
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    assert result.get("capex") is None


def test_us_pivot_all_missing_no_exception():
    from lab.engine.micro.fetcher_us import _pivot_row

    df = pd.DataFrame(columns=["REPORT_DATE", "ITEM_NAME", "AMOUNT"])
    result = _pivot_row(df, pd.Timestamp("2024-09-30"))
    for key in (
        "operating_cf",
        "capex",
        "cash",
        "total_liab",
        "revenue",
        "net_income",
        "equity",
    ):
        assert result.get(key) is None


# ── fetch_us_statements writes to DB ──────────────────────────────────────


def test_fetch_us_statements_writes_rows():
    from lab.engine.micro.fetcher_us import fetch_us_statements
    from lab.engine.db import get_db

    conn = get_db("micro")

    dates = [pd.Timestamp("2024-09-30"), pd.Timestamp("2023-09-30")]
    rows_cf, rows_bs, rows_pl = [], [], []

    for d in dates:
        rows_cf += [
            {
                "REPORT_DATE": d,
                "ITEM_NAME": "经营活动产生的现金流量净额",
                "AMOUNT": 100000.0,
            },
            {"REPORT_DATE": d, "ITEM_NAME": "购买固定资产", "AMOUNT": 10000.0},
        ]
        rows_bs += [
            {"REPORT_DATE": d, "ITEM_NAME": "现金及现金等价物", "AMOUNT": 200000.0},
            {"REPORT_DATE": d, "ITEM_NAME": "总负债", "AMOUNT": 300000.0},
        ]
        rows_pl += [
            {"REPORT_DATE": d, "ITEM_NAME": "营业收入", "AMOUNT": 400000.0},
            {"REPORT_DATE": d, "ITEM_NAME": "净利润", "AMOUNT": 90000.0},
        ]

    n = fetch_us_statements(
        "AAPL",
        conn,
        mock={
            "cash_flow": pd.DataFrame(rows_cf),
            "balance": pd.DataFrame(rows_bs),
            "profit": pd.DataFrame(rows_pl),
        },
    )
    assert n == 2

    db_rows = conn.execute(
        "SELECT report_date, fcf FROM financial_statements "
        "WHERE code='AAPL' ORDER BY report_date"
    ).fetchall()
    assert len(db_rows) == 2
    # FCF = 100000 - 10000 = 90000
    assert db_rows[1]["fcf"] == 90000.0


def test_fetch_us_statements_is_idempotent():
    from lab.engine.micro.fetcher_us import fetch_us_statements
    from lab.engine.db import get_db

    conn = get_db("micro")

    cf = pd.DataFrame(
        [
            {
                "REPORT_DATE": pd.Timestamp("2024-09-30"),
                "ITEM_NAME": "经营活动产生的现金流量净额",
                "AMOUNT": 50000.0,
            }
        ]
    )
    empty = pd.DataFrame(columns=["REPORT_DATE", "ITEM_NAME", "AMOUNT"])

    fetch_us_statements(
        "MSFT", conn, mock={"cash_flow": cf, "balance": empty, "profit": empty}
    )
    fetch_us_statements(
        "MSFT", conn, mock={"cash_flow": cf, "balance": empty, "profit": empty}
    )

    row = conn.execute(
        "SELECT count(*) as c FROM financial_statements WHERE code='MSFT'"
    ).fetchone()
    assert row["c"] == 1
