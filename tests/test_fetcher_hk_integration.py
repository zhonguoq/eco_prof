"""Integration smoke tests for akshare HK financial data API.

Calls the REAL akshare API (no mocks) to verify:
1. stock_financial_hk_report_em exists and accepts the expected parameters
2. Returns long-table DataFrame with correct column names (STD_ITEM_NAME / AMOUNT)
3. Key STD_ITEM_NAME values for 0700.HK (Tencent) match our FIELD_MAP_HK

Marked pytest.mark.slow — excluded from fast CI:
    pytest tests/test_fetcher_hk_integration.py -v -m slow
"""

import pytest

pytestmark = pytest.mark.slow

HK_CODE = "0700.HK"
HK_AK_CODE = "00700"  # zero-padded, no .HK suffix


# ── API surface ────────────────────────────────────────────────────────────


def test_akshare_hk_function_exists():
    import akshare as ak

    assert hasattr(ak, "stock_financial_hk_report_em")
    assert callable(ak.stock_financial_hk_report_em)


def test_akshare_hk_cash_flow_columns():
    """现金流量表 returns DataFrame with STD_ITEM_NAME and AMOUNT columns."""
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="现金流量表", indicator="年度"
    )
    assert not df.empty, "HK cash flow DataFrame should not be empty"
    assert "REPORT_DATE" in df.columns, f"Missing REPORT_DATE, got {list(df.columns)}"
    assert "STD_ITEM_NAME" in df.columns, (
        f"Missing STD_ITEM_NAME, got {list(df.columns)}"
    )
    assert "AMOUNT" in df.columns, f"Missing AMOUNT, got {list(df.columns)}"


def test_akshare_hk_balance_sheet_columns():
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="资产负债表", indicator="年度"
    )
    assert not df.empty
    assert "STD_ITEM_NAME" in df.columns
    assert "AMOUNT" in df.columns


def test_akshare_hk_profit_columns():
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="利润表", indicator="年度"
    )
    assert not df.empty
    assert "STD_ITEM_NAME" in df.columns
    assert "AMOUNT" in df.columns


# ── Key field names present in real data ──────────────────────────────────


def test_hk_operating_cf_field_present():
    """经营业务现金净额 (primary alias) exists in real 0700.HK cash flow data."""
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="现金流量表", indicator="年度"
    )
    all_items = set(df["STD_ITEM_NAME"].unique())
    assert "经营业务现金净额" in all_items, (
        f"经营业务现金净额 not found in HK cash flow. Available: {sorted(all_items)}"
    )


def test_hk_balance_sheet_key_fields_present():
    """现金及等价物 and 总负债 exist in real 0700.HK balance sheet data."""
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="资产负债表", indicator="年度"
    )
    all_items = set(df["STD_ITEM_NAME"].unique())
    for expected in ("现金及等价物", "总负债"):
        assert expected in all_items, (
            f"{expected!r} not found in HK balance sheet. Available: {sorted(all_items)}"
        )


def test_hk_profit_key_fields_present():
    """除税前溢利 and 股东应占溢利 exist in real 0700.HK profit data."""
    import akshare as ak

    df = ak.stock_financial_hk_report_em(
        stock=HK_AK_CODE, symbol="利润表", indicator="年度"
    )
    all_items = set(df["STD_ITEM_NAME"].unique())
    for expected in ("除税前溢利", "股东应占溢利"):
        assert expected in all_items, (
            f"{expected!r} not found in HK profit sheet. Available: {sorted(all_items)}"
        )


# ── fetch_hk_statements end-to-end (real network) ────────────────────────


def test_fetch_hk_statements_end_to_end():
    """fetch_hk_statements('0700.HK') writes ≥1 row to DB, fcf is non-zero."""
    from lab.engine.micro.fetcher_hk import fetch_hk_statements
    from lab.engine.db import get_db

    conn = get_db("micro")
    n = fetch_hk_statements(HK_CODE, conn)
    assert n > 0, "Should have written at least one year of data"

    rows = conn.execute(
        "SELECT operating_cf, capex, fcf FROM financial_statements "
        "WHERE code=? ORDER BY report_date DESC LIMIT 3",
        (HK_CODE,),
    ).fetchall()
    assert len(rows) > 0
    # operating_cf should be a real number (Tencent has large positive CF)
    assert rows[0]["operating_cf"] is not None
    assert rows[0]["operating_cf"] > 0, "Tencent operating CF should be positive"
