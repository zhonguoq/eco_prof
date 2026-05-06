"""Financial statements fetcher — router / dispatcher (Phase 4 #31).

Detects market from code and delegates to the appropriate sub-fetcher:
  A  → fetcher_a.fetch_a_statements
  HK → fetcher_hk.fetch_hk_statements
  US → fetcher_us.fetch_us_statements

Backward-compatible shim: the old fetch_financial_statements(code, conn,
  mock_cash_flow=..., mock_balance=...) signature is still accepted for A-shares.
"""

from __future__ import annotations

import re

import pandas as pd

from lab.engine.micro.fetcher_a import fetch_a_statements
from lab.engine.micro.fetcher_hk import fetch_hk_statements
from lab.engine.micro.fetcher_us import fetch_us_statements


# ── Market detection ───────────────────────────────────────────────────────


def _detect_market(code: str) -> str:
    """Return 'A', 'HK', or 'US' based on code suffix."""
    if re.search(r"\.(SH|SZ)$", code, re.IGNORECASE):
        return "A"
    if re.search(r"\.HK$", code, re.IGNORECASE):
        return "HK"
    return "US"


# ── Sub-fetcher wrappers (module-level names for monkeypatching) ──────────


def _fetch_a(code: str, conn, mock=None) -> int:
    return fetch_a_statements(code, conn, mock=mock)


def _fetch_hk(code: str, conn, mock=None) -> int:
    return fetch_hk_statements(code, conn, mock=mock)


def _fetch_us(code: str, conn, mock=None) -> int:
    return fetch_us_statements(code, conn, mock=mock)


# ── Router ─────────────────────────────────────────────────────────────────


def fetch_financial_statements(
    code: str,
    conn,
    market: str | None = None,
    # Legacy A-share kwargs for backward compatibility
    mock_cash_flow=None,
    mock_balance=None,
    mock=None,
) -> int:
    """
    Dispatch to the correct sub-fetcher based on code market.

    Legacy callers may still pass mock_cash_flow / mock_balance for A-shares.
    New callers pass mock={'cash_flow': df, 'balance': df, 'profit': df}.
    """
    detected = _detect_market(code)

    # ── A-share ──
    if detected == "A":
        # Convert legacy kwargs to new mock dict format
        if mock is None and (mock_cash_flow is not None or mock_balance is not None):
            mock = {
                "cash_flow": mock_cash_flow,
                "balance": mock_balance,
                "profit": None,
            }
        return _fetch_a(code, conn, mock=mock)

    # ── HK ──
    if detected == "HK":
        return _fetch_hk(code, conn, mock=mock)

    # ── US ──
    return _fetch_us(code, conn, mock=mock)


# ── Legacy helpers kept for backward compatibility ─────────────────────────


def _aksymbol(code: str) -> str:
    """Convert '000725.SZ' → 'SZ000725' for akshare API."""
    parts = code.split(".")
    return parts[1] + parts[0] if len(parts) == 2 else code


def fetch_stock_data(code, conn, market=None, mock=None):
    # Auto-detect market from code if not provided
    if market is None:
        market = _detect_market(code)
    if mock is not None:
        data = mock
    elif market == "A":
        import akshare as ak

        df = ak.stock_zh_a_hist(
            symbol=code.replace(".SH", "").replace(".SZ", ""), adjust="qfq"
        )
        data = df.set_index("日期")
    else:
        import yfinance as yf

        # Normalize HK codes: yfinance expects 4-digit prefix (e.g. 0700.HK not 00700.HK)
        yf_code = code
        if market == "HK" and re.search(r"^0+(\d{4})\.HK$", code, re.IGNORECASE):
            m = re.match(r"^0*(\d{4})\.HK$", code, re.IGNORECASE)
            if m:
                yf_code = m.group(1) + ".HK"
        ticker = yf.Ticker(yf_code)
        data = ticker.history(period="max")

    rows = 0
    for date_idx, row in data.iterrows():
        date_str = (
            date_idx.strftime("%Y-%m-%d")
            if hasattr(date_idx, "strftime")
            else str(date_idx)
        )
        conn.execute(
            """INSERT OR REPLACE INTO stock_prices
               (code, date, open, close, high, low, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                date_str,
                float(row.get("open", row.get("Open", 0))),
                float(row.get("close", row.get("Close", 0))),
                float(row.get("high", row.get("High", 0))),
                float(row.get("low", row.get("Low", 0))),
                float(row.get("volume", row.get("Volume", 0))),
            ),
        )
        rows += 1
    conn.commit()
    return rows
