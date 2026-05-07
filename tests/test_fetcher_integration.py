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


# ── A 股价格历史 API 契约 (stock_zh_a_hist) ────────────────────────────────


def test_akshare_a_hist_function_exists():
    """stock_zh_a_hist 函数存在且可调用。"""
    import akshare as ak

    assert hasattr(ak, "stock_zh_a_hist")
    assert callable(ak.stock_zh_a_hist)


def test_akshare_a_hist_returns_price_data():
    """stock_zh_a_hist 返回含预期列的非空 DataFrame。

    此测试直接访问 EastMoney 端点；若 akshare 端点不可用则测试失败，
    表明价格数据将依赖 yfinance 降级路径。
    """
    import akshare as ak

    df = ak.stock_zh_a_hist(symbol="000725", adjust="qfq")
    assert not df.empty, "stock_zh_a_hist 返回空 DataFrame，EastMoney 端点可能已故障"
    for col in ("日期", "收盘", "开盘", "最高", "最低", "成交量"):
        assert col in df.columns, (
            f"缺少列 {col!r}，API 列名可能已变更: {list(df.columns)}"
        )
    assert (df["收盘"] > 0).any(), "收盘价全为 0，数据异常"


# ── fetch_stock_data 端到端（真实网络，A 股）─────────────────────────────


def test_fetch_stock_data_a_share_writes_rows():
    """fetch_stock_data A 股写入 stock_prices，收盘价为正数。

    akshare 可用时直接读取；不可用时经 yfinance 降级后仍应通过。
    """
    from lab.engine.micro.fetcher import fetch_stock_data
    from lab.engine.db import get_db

    conn = get_db("micro")
    n = fetch_stock_data("000725.SZ", conn)
    assert n > 0, f"应写入 >0 行价格数据，实际写入 {n} 行"

    row = conn.execute(
        "SELECT close FROM stock_prices WHERE code='000725.SZ'"
        " ORDER BY date DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row["close"] > 0, f"收盘价应为正数，实际值: {row['close']}"
