"""Unit tests for fetcher_hk.py (Phase 4 #31).

Mock DataFrames use the real akshare STD_ITEM_NAME values for HK stocks
(verified against live 0700.HK data — HK GAAP terminology differs from A-share).
All tests use mock DataFrames — no real network calls.
"""

import pytest
import pandas as pd
import json


# ── helpers ────────────────────────────────────────────────────────────────


def _make_hk_df(items: dict, report_date="2024-12-31"):
    """
    Build a mock akshare-style HK long DataFrame.
    items: {STD_ITEM_NAME: AMOUNT}
    """
    rows = [
        {
            "REPORT_DATE": pd.Timestamp(report_date),
            "STD_ITEM_NAME": name,
            "AMOUNT": float(amount),
        }
        for name, amount in items.items()
    ]
    return pd.DataFrame(rows)


# ── _pivot_row: basic field extraction ────────────────────────────────────


def test_hk_pivot_extracts_operating_cf():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df(
        {
            "经营业务现金净额": 50000.0,
            "购建无形资产及其他资产": 5000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["operating_cf"] == 50000.0


def test_hk_pivot_extracts_capex():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df(
        {
            "经营业务现金净额": 50000.0,
            "购建无形资产及其他资产": 8000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["capex"] == 8000.0


def test_hk_pivot_extracts_balance_sheet_fields():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df(
        {
            "经营业务现金净额": 50000.0,
            "现金及等价物": 80000.0,
            "总负债": 120000.0,
            "股东权益": 200000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["cash"] == 80000.0
    assert result["total_liab"] == 120000.0
    assert result["equity"] == 200000.0


def test_hk_pivot_extracts_profit_fields():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df(
        {
            "经营业务现金净额": 50000.0,
            "营业额": 300000.0,
            "股东应占溢利": 60000.0,
            "除税前溢利": 75000.0,
            "税项": 15000.0,
            "融资成本": 3000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["revenue"] == 300000.0
    assert result["net_income"] == 60000.0
    assert result["pretax_income"] == 75000.0
    assert result["income_tax"] == 15000.0
    assert result["interest_expense"] == 3000.0


# ── alias fallback ─────────────────────────────────────────────────────────


def test_hk_pivot_operating_cf_alias_fallback():
    """Secondary alias 经营活动产生的现金流量净额 should work if primary absent."""
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df({"经营活动产生的现金流量净额": 30000.0})
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["operating_cf"] == 30000.0


def test_hk_pivot_capex_alias_fallback():
    """Secondary alias 购建固定资产及无形资产 used when primary absent."""
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df(
        {
            "经营业务现金净额": 30000.0,
            "购建固定资产及无形资产": 3000.0,
        }
    )
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result["capex"] == 3000.0


# ── missing field → NULL, no exception ────────────────────────────────────


def test_hk_pivot_missing_field_returns_none():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = _make_hk_df({"经营业务现金净额": 20000.0})
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    assert result.get("capex") is None


def test_hk_pivot_all_missing_returns_nones():
    from lab.engine.micro.fetcher_hk import _pivot_row

    df = pd.DataFrame(columns=["REPORT_DATE", "STD_ITEM_NAME", "AMOUNT"])
    result = _pivot_row(df, pd.Timestamp("2024-12-31"))
    for key in (
        "operating_cf",
        "capex",
        "cash",
        "total_liab",
        "revenue",
        "net_income",
        "equity",
    ):
        assert result.get(key) is None, f"{key} should be None when data absent"


# ── fetch_hk_statements writes to DB ──────────────────────────────────────


def test_fetch_hk_statements_writes_rows():
    from lab.engine.micro.fetcher_hk import fetch_hk_statements
    from lab.engine.db import get_db

    conn = get_db("micro")

    dates = [pd.Timestamp("2024-12-31"), pd.Timestamp("2023-12-31")]
    rows_cf, rows_bs, rows_pl = [], [], []

    for d in dates:
        rows_cf += [
            {"REPORT_DATE": d, "STD_ITEM_NAME": "经营业务现金净额", "AMOUNT": 50000.0},
            {
                "REPORT_DATE": d,
                "STD_ITEM_NAME": "购建无形资产及其他资产",
                "AMOUNT": 5000.0,
            },
        ]
        rows_bs += [
            {"REPORT_DATE": d, "STD_ITEM_NAME": "现金及等价物", "AMOUNT": 80000.0},
            {"REPORT_DATE": d, "STD_ITEM_NAME": "总负债", "AMOUNT": 120000.0},
        ]
        rows_pl += [
            {"REPORT_DATE": d, "STD_ITEM_NAME": "营业额", "AMOUNT": 200000.0},
            {"REPORT_DATE": d, "STD_ITEM_NAME": "股东应占溢利", "AMOUNT": 40000.0},
        ]

    n = fetch_hk_statements(
        "0700.HK",
        conn,
        mock={
            "cash_flow": pd.DataFrame(rows_cf),
            "balance": pd.DataFrame(rows_bs),
            "profit": pd.DataFrame(rows_pl),
        },
    )
    assert n == 2

    db_rows = conn.execute(
        "SELECT report_date, fcf, operating_cf, capex FROM financial_statements "
        "WHERE code='0700.HK' ORDER BY report_date"
    ).fetchall()
    assert len(db_rows) == 2
    # FCF = operating_cf - capex = 50000 - 5000 = 45000
    assert db_rows[1]["fcf"] == 45000.0


def test_fetch_hk_statements_is_idempotent():
    from lab.engine.micro.fetcher_hk import fetch_hk_statements
    from lab.engine.db import get_db

    conn = get_db("micro")

    mock_cf = pd.DataFrame(
        [
            {
                "REPORT_DATE": pd.Timestamp("2022-12-31"),
                "STD_ITEM_NAME": "经营业务现金净额",
                "AMOUNT": 10000.0,
            },
        ]
    )
    empty = pd.DataFrame(columns=["REPORT_DATE", "STD_ITEM_NAME", "AMOUNT"])

    fetch_hk_statements(
        "0001.HK", conn, mock={"cash_flow": mock_cf, "balance": empty, "profit": empty}
    )
    fetch_hk_statements(
        "0001.HK", conn, mock={"cash_flow": mock_cf, "balance": empty, "profit": empty}
    )

    row = conn.execute(
        "SELECT count(*) as c FROM financial_statements WHERE code='0001.HK'"
    ).fetchone()
    assert row["c"] == 1
