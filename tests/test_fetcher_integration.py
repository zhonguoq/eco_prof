"""Integration smoke tests for akshare API.

These tests call the REAL akshare API (no mocks) to verify:
1. The expected function names exist and are callable
2. The returned DataFrames have the expected column names

Marked with pytest.mark.slow so they can be excluded in fast CI runs.
"""
import pytest

pytestmark = pytest.mark.slow


def test_akshare_cash_flow_function_exists():
    """Verify stock_cash_flow_sheet_by_report_em is available."""
    import akshare as ak
    assert hasattr(ak, "stock_cash_flow_sheet_by_report_em")
    assert callable(ak.stock_cash_flow_sheet_by_report_em)


def test_akshare_balance_sheet_function_exists():
    """Verify stock_balance_sheet_by_report_em is available."""
    import akshare as ak
    assert hasattr(ak, "stock_balance_sheet_by_report_em")
    assert callable(ak.stock_balance_sheet_by_report_em)


def test_akshare_cash_flow_returns_expected_columns():
    """Fetch real data for 600519 and check column names."""
    import akshare as ak
    df = ak.stock_cash_flow_sheet_by_report_em(symbol="SH600519")
    assert "REPORT_DATE" in df.columns, f"Missing REPORT_DATE in {list(df.columns)}"
    assert "NETCASH_OPERATE" in df.columns
    assert "CONSTRUCT_LONG_ASSET" in df.columns


def test_akshare_balance_sheet_returns_expected_columns():
    """Fetch real data for 600519 and check column names."""
    import akshare as ak
    df = ak.stock_balance_sheet_by_report_em(symbol="SH600519")
    assert "REPORT_DATE" in df.columns
    assert "MONETARYFUNDS" in df.columns
    assert "TOTAL_LIABILITIES" in df.columns


def test_aksymbol_conversion():
    """Verify the _aksymbol helper produces correct format."""
    from lab.engine.micro.fetcher import _aksymbol
    assert _aksymbol("000725.SZ") == "SZ000725"
    assert _aksymbol("600519.SH") == "SH600519"
    assert _aksymbol("AAPL") == "AAPL"
