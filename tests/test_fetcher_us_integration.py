"""Integration smoke tests for akshare US financial data API.

Calls the REAL akshare API (no mocks) to verify:
1. stock_financial_us_report_em exists and accepts the expected parameters
2. Returns long-table DataFrame with correct column name (ITEM_NAME, not STD_ITEM_NAME)
3. Valid symbol values: "资产负债表" / "综合损益表" / "现金流量表"
4. Key ITEM_NAME values for AAPL match our FIELD_MAP_US

Marked pytest.mark.slow — excluded from fast CI:
    pytest tests/test_fetcher_us_integration.py -v -m slow
"""

import pytest

pytestmark = pytest.mark.slow

US_CODE = "AAPL"


# ── API surface ────────────────────────────────────────────────────────────


def test_akshare_us_function_exists():
    import akshare as ak

    assert hasattr(ak, "stock_financial_us_report_em")
    assert callable(ak.stock_financial_us_report_em)


def test_akshare_us_cash_flow_columns():
    """现金流量表 returns DataFrame with ITEM_NAME (not STD_ITEM_NAME) and AMOUNT."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="现金流量表", indicator="年报"
    )
    assert not df.empty, "US cash flow DataFrame should not be empty"
    assert "REPORT_DATE" in df.columns, f"Missing REPORT_DATE, got {list(df.columns)}"
    assert "ITEM_NAME" in df.columns, (
        f"US tables must use ITEM_NAME column, got {list(df.columns)}"
    )
    assert "AMOUNT" in df.columns


def test_akshare_us_balance_sheet_columns():
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="资产负债表", indicator="年报"
    )
    assert not df.empty
    assert "ITEM_NAME" in df.columns
    assert "AMOUNT" in df.columns


def test_akshare_us_income_statement_columns():
    """综合损益表 (NOT 利润表) is the valid income symbol for US."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="综合损益表", indicator="年报"
    )
    assert not df.empty
    assert "ITEM_NAME" in df.columns
    assert "AMOUNT" in df.columns


def test_akshare_us_invalid_symbol_raises():
    """利润表 is NOT a valid symbol for US — should raise ValueError."""
    import akshare as ak

    with pytest.raises(ValueError):
        ak.stock_financial_us_report_em(
            stock=US_CODE, symbol="利润表", indicator="年报"
        )


# ── Key field names present in real data ──────────────────────────────────


def test_us_operating_cf_field_present():
    """经营活动产生的现金流量净额 exists in real AAPL cash flow."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="现金流量表", indicator="年报"
    )
    all_items = set(df["ITEM_NAME"].unique())
    assert "经营活动产生的现金流量净额" in all_items, (
        f"经营活动产生的现金流量净额 not found. Available: {sorted(all_items)}"
    )


def test_us_capex_field_present():
    """购买固定资产 (primary capex alias) exists in real AAPL cash flow."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="现金流量表", indicator="年报"
    )
    all_items = set(df["ITEM_NAME"].unique())
    assert "购买固定资产" in all_items, (
        f"购买固定资产 not found. Available: {sorted(all_items)}"
    )


def test_us_balance_key_fields_present():
    """现金及现金等价物 and 总负债 exist in real AAPL balance sheet."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="资产负债表", indicator="年报"
    )
    all_items = set(df["ITEM_NAME"].unique())
    for expected in ("现金及现金等价物", "总负债"):
        assert expected in all_items, (
            f"{expected!r} not found in US balance sheet. Available: {sorted(all_items)}"
        )


def test_us_income_key_fields_present():
    """营业收入 and 净利润 and 持续经营税前利润 exist in real AAPL income."""
    import akshare as ak

    df = ak.stock_financial_us_report_em(
        stock=US_CODE, symbol="综合损益表", indicator="年报"
    )
    all_items = set(df["ITEM_NAME"].unique())
    for expected in ("营业收入", "净利润", "持续经营税前利润", "所得税"):
        assert expected in all_items, (
            f"{expected!r} not found in US income statement. Available: {sorted(all_items)}"
        )


# ── fetch_us_statements end-to-end (real network) ────────────────────────


def test_fetch_us_statements_end_to_end():
    """fetch_us_statements('AAPL') writes ≥1 row to DB with positive operating_cf."""
    from lab.engine.micro.fetcher_us import fetch_us_statements
    from lab.engine.db import get_db

    conn = get_db("micro")
    n = fetch_us_statements(US_CODE, conn)
    assert n > 0, "Should have written at least one year of AAPL data"

    rows = conn.execute(
        "SELECT operating_cf, capex, fcf, revenue, net_income FROM financial_statements "
        "WHERE code=? ORDER BY report_date DESC LIMIT 3",
        (US_CODE,),
    ).fetchall()
    assert len(rows) > 0
    assert rows[0]["operating_cf"] is not None
    assert rows[0]["operating_cf"] > 0, "AAPL operating CF should be positive"
    assert rows[0]["revenue"] is not None
    assert rows[0]["net_income"] is not None
