"""Unit tests for fetcher.py router (Phase 4 #31).

Tests _detect_market() and fetch_financial_statements() dispatcher.
All tests use mocks — no real network calls.
"""

import pytest
import pandas as pd


# ── _detect_market ─────────────────────────────────────────────────────────


def test_detect_market_a_sh():
    from lab.engine.micro.fetcher import _detect_market

    assert _detect_market("600519.SH") == "A"


def test_detect_market_a_sz():
    from lab.engine.micro.fetcher import _detect_market

    assert _detect_market("000725.SZ") == "A"


def test_detect_market_hk():
    from lab.engine.micro.fetcher import _detect_market

    assert _detect_market("0700.HK") == "HK"


def test_detect_market_us_plain():
    from lab.engine.micro.fetcher import _detect_market

    assert _detect_market("AAPL") == "US"


def test_detect_market_us_nasdaq():
    from lab.engine.micro.fetcher import _detect_market

    assert _detect_market("MSFT") == "US"


# ── dispatcher routes correctly ────────────────────────────────────────────


def test_dispatcher_calls_fetcher_a_for_a_share(monkeypatch):
    """fetch_financial_statements with A-share code must delegate to fetcher_a."""
    called = {}

    def mock_fetch_a(code, conn, mock=None):
        called["market"] = "A"
        called["code"] = code
        return 3

    import lab.engine.micro.fetcher as router_mod

    monkeypatch.setattr(router_mod, "_fetch_a", mock_fetch_a)

    from lab.engine.db import get_db

    conn = get_db("micro")
    n = router_mod.fetch_financial_statements("000725.SZ", conn)
    assert called["market"] == "A"
    assert called["code"] == "000725.SZ"
    assert n == 3


def test_dispatcher_calls_fetcher_hk_for_hk_share(monkeypatch):
    """fetch_financial_statements with HK code must delegate to fetcher_hk."""
    called = {}

    def mock_fetch_hk(code, conn, mock=None):
        called["market"] = "HK"
        return 2

    import lab.engine.micro.fetcher as router_mod

    monkeypatch.setattr(router_mod, "_fetch_hk", mock_fetch_hk)

    from lab.engine.db import get_db

    conn = get_db("micro")
    n = router_mod.fetch_financial_statements("0700.HK", conn)
    assert called["market"] == "HK"
    assert n == 2


def test_dispatcher_calls_fetcher_us_for_us_share(monkeypatch):
    """fetch_financial_statements with US code must delegate to fetcher_us."""
    called = {}

    def mock_fetch_us(code, conn, mock=None):
        called["market"] = "US"
        return 5

    import lab.engine.micro.fetcher as router_mod

    monkeypatch.setattr(router_mod, "_fetch_us", mock_fetch_us)

    from lab.engine.db import get_db

    conn = get_db("micro")
    n = router_mod.fetch_financial_statements("AAPL", conn)
    assert called["market"] == "US"
    assert n == 5
