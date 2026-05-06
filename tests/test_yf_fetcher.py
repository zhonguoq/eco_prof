"""
Phase 3: yfinance fetcher + securities 表测试
ADR-002 决策 3、9、10
- fetch_securities mock yfinance.Ticker
- upsert_securities 写入 securities 表
"""

import os
import pytest
from unittest.mock import MagicMock, patch


def _make_mock_ticker(info: dict):
    """构造一个 mock yfinance.Ticker。"""
    ticker = MagicMock()
    ticker.info = info
    return ticker


MOCK_INFO_ASTOCK = {
    "shortName": "BOE Technology",
    "industry": "Electronic Components",
    "sharesOutstanding": 38_700_000_000,
    "currency": "CNY",
    "currentPrice": 4.85,
    "marketCap": 187_695_000_000,
    "quoteType": "EQUITY",
}

MOCK_INFO_US = {
    "shortName": "Apple Inc.",
    "industry": "Consumer Electronics",
    "sharesOutstanding": 15_441_000_000,
    "currency": "USD",
    "currentPrice": 211.45,
    "marketCap": 3_200_000_000_000,
    "quoteType": "EQUITY",
}


def test_fetch_securities_returns_required_fields(tmp_path):
    """fetch_securities 返回包含 8 个关键字段的 dict。"""
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import _connections

    _connections.clear()

    with patch("yfinance.Ticker", return_value=_make_mock_ticker(MOCK_INFO_ASTOCK)):
        from lab.engine.micro.yf_fetcher import fetch_securities

        result = fetch_securities("000725.SZ")

    assert result["name"] == "BOE Technology"
    assert result["industry"] == "Electronic Components"
    assert result["shares_outstanding"] == 38_700_000_000
    assert result["currency"] == "CNY"
    assert result["current_price"] == pytest.approx(4.85)
    assert "market" in result
    assert "updated_at" in result
    _connections.clear()


def test_fetch_securities_market_inference():
    """market 从代码后缀推断。"""
    with patch("yfinance.Ticker", return_value=_make_mock_ticker(MOCK_INFO_ASTOCK)):
        from lab.engine.micro.yf_fetcher import fetch_securities

        result = fetch_securities("000725.SZ")
    assert result["market"] == "A"

    with patch("yfinance.Ticker", return_value=_make_mock_ticker(MOCK_INFO_US)):
        result = fetch_securities("AAPL")
    assert result["market"] == "US"


def test_upsert_securities_writes_to_db(tmp_path):
    """upsert_securities 写入 securities 表。"""
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()

    conn = get_db("micro")

    with patch("yfinance.Ticker", return_value=_make_mock_ticker(MOCK_INFO_ASTOCK)):
        from lab.engine.micro.yf_fetcher import upsert_securities

        upsert_securities(conn, "000725.SZ")

    row = conn.execute("SELECT * FROM securities WHERE code='000725.SZ'").fetchone()
    assert row is not None
    assert row["name"] == "BOE Technology"
    assert row["shares_outstanding"] == 38_700_000_000
    _connections.clear()


def test_upsert_securities_with_mock_dict(tmp_path):
    """upsert_securities 支持直接传 mock dict（不调 yfinance）。"""
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()

    conn = get_db("micro")
    mock_data = {
        "name": "Test Corp",
        "industry": "Tech",
        "shares_outstanding": 1_000_000,
        "currency": "CNY",
        "current_price": 10.0,
        "market": "A",
    }

    from lab.engine.micro.yf_fetcher import upsert_securities

    upsert_securities(conn, "TEST.SZ", mock=mock_data)

    row = conn.execute("SELECT * FROM securities WHERE code='TEST.SZ'").fetchone()
    assert row["current_price"] == pytest.approx(10.0)
    _connections.clear()


def test_upsert_securities_overwrites_on_second_call(tmp_path):
    """每次调用覆写 shares_outstanding（ADR-002 决策 10）。"""
    os.environ["ECO_DB_DIR"] = str(tmp_path)
    from lab.engine.db import get_db, _connections

    _connections.clear()
    conn = get_db("micro")

    from lab.engine.micro.yf_fetcher import upsert_securities

    upsert_securities(
        conn,
        "000725.SZ",
        mock={
            "name": "BOE",
            "industry": "Tech",
            "shares_outstanding": 1_000,
            "currency": "CNY",
            "current_price": 5.0,
            "market": "A",
        },
    )
    upsert_securities(
        conn,
        "000725.SZ",
        mock={
            "name": "BOE",
            "industry": "Tech",
            "shares_outstanding": 2_000,
            "currency": "CNY",
            "current_price": 5.5,
            "market": "A",
        },
    )
    row = conn.execute(
        "SELECT shares_outstanding FROM securities WHERE code='000725.SZ'"
    ).fetchone()
    assert row["shares_outstanding"] == 2_000
    _connections.clear()
