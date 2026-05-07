"""Integration tests for the full fetch_financials pipeline.

Calls the REAL network (akshare + yfinance) to verify:
1. fetch_stock_data writes rows to stock_prices (with fallback)
2. fetch_financial_statements writes rows to financial_statements
3. upsert_securities populates the securities table
4. All three tables are non-empty after a complete fetch

Marked pytest.mark.slow — excluded from fast CI.
Run explicitly:
    pytest tests/test_fetch_financials_integration.py -v -m slow
"""

import pytest

pytestmark = pytest.mark.slow

A_CODE = "000725.SZ"  # 京东方 A — 深交所，流动性好


# ── 逐表验证 ───────────────────────────────────────────────────────────────


def test_fetch_stock_data_a_share_populates_stock_prices():
    """fetch_stock_data 为 A 股写入 stock_prices，收盘价为正数。

    akshare 可用时从 EastMoney 拉取；不可用时经 yfinance 降级后仍应通过。
    若两条路径都失败则测试失败，表明价格数据无法获取。
    """
    from lab.engine.micro.fetcher import fetch_stock_data
    from lab.engine.db import get_db

    conn = get_db("micro")
    n = fetch_stock_data(A_CODE, conn)

    assert n > 0, f"stock_prices 应有 >0 行，实际 {n} 行"
    row = conn.execute(
        "SELECT date, close FROM stock_prices WHERE code=? ORDER BY date DESC LIMIT 1",
        (A_CODE,),
    ).fetchone()
    assert row is not None
    assert row["close"] > 0, f"最新收盘价应为正数，得到 {row['close']}"


def test_fetch_financial_statements_a_share_populates_statements():
    """fetch_financial_statements 为 A 股写入 financial_statements，FCF 字段存在。"""
    from lab.engine.micro.fetcher import fetch_financial_statements
    from lab.engine.db import get_db

    conn = get_db("micro")
    n = fetch_financial_statements(A_CODE, conn)

    assert n > 0, f"financial_statements 应有 >0 行，实际 {n} 行"
    row = conn.execute(
        "SELECT fcf, operating_cf FROM financial_statements"
        " WHERE code=? AND fcf IS NOT NULL ORDER BY report_date DESC LIMIT 1",
        (A_CODE,),
    ).fetchone()
    assert row is not None, "financial_statements 中没有非空 FCF 行"


def test_upsert_securities_a_share_populates_securities():
    """upsert_securities 写入 securities，current_price / shares_outstanding 非零。"""
    from lab.engine.micro.yf_fetcher import upsert_securities
    from lab.engine.db import get_db

    conn = get_db("micro")
    upsert_securities(conn, A_CODE)

    row = conn.execute(
        "SELECT current_price, shares_outstanding, market FROM securities WHERE code=?",
        (A_CODE,),
    ).fetchone()
    assert row is not None, "securities 表中未找到该股票"
    assert row["current_price"] > 0, (
        f"current_price 应为正数，得到 {row['current_price']}"
    )
    assert row["shares_outstanding"] > 0, (
        f"shares_outstanding 应为正数，得到 {row['shares_outstanding']}"
    )
    assert row["market"] == "A"


# ── 全流程验证（对应 fetch_financials.py 默认行为）──────────────────────


def test_full_fetch_financials_populates_all_three_tables():
    """模拟 fetch_financials.py 默认调用，验证三表均有数据。

    这是防止「应用层才暴露问题」的关键回归测试：
    任何一张表为空都意味着下游 DCF / estimate_params 会失败。
    """
    from lab.engine.micro.fetcher import fetch_stock_data, fetch_financial_statements
    from lab.engine.micro.yf_fetcher import upsert_securities
    from lab.engine.db import get_db

    conn = get_db("micro")

    n_prices = fetch_stock_data(A_CODE, conn)
    n_stmt = fetch_financial_statements(A_CODE, conn)
    upsert_securities(conn, A_CODE)

    # stock_prices
    assert n_prices > 0, f"stock_prices 为空（{n_prices} 行）"

    # financial_statements
    assert n_stmt > 0, f"financial_statements 为空（{n_stmt} 行）"

    # securities — DCF 需要 current_price + shares_outstanding
    sec = conn.execute(
        "SELECT current_price, shares_outstanding FROM securities WHERE code=?",
        (A_CODE,),
    ).fetchone()
    assert sec is not None, (
        "securities 表中无记录；dcf.py 将报 '找不到 securities' 并退出"
    )
    assert sec["current_price"] > 0
    assert sec["shares_outstanding"] > 0
