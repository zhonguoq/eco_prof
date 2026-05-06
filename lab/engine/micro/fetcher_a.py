"""A-share financial statements fetcher.

Extracted from fetcher.py (Phase 4 #31).
Fetches 10 structured fields from akshare wide-table API.
"""

from __future__ import annotations

import json
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _aksymbol(code: str) -> str:
    """Convert '000725.SZ' → 'SZ000725' for akshare API."""
    parts = code.split(".")
    return parts[1] + parts[0] if len(parts) == 2 else code


# ── Field maps for A-share wide tables ────────────────────────────────────

# Cash flow statement (stock_cash_flow_sheet_by_report_em)
_CF_FIELDS = {
    "operating_cf": "NETCASH_OPERATE",
    "capex": "CONSTRUCT_LONG_ASSET",
}

# Balance sheet (stock_balance_sheet_by_report_em)
_BS_FIELDS = {
    "cash": "MONETARYFUNDS",
    "total_liab": "TOTAL_LIABILITIES",
    "equity": "TOTAL_EQUITY",
}

# Profit sheet (stock_profit_sheet_by_report_em)
_PL_FIELDS = {
    "revenue": "TOTAL_OPERATE_INCOME",
    "net_income": "NETPROFIT",
    "pretax_income": "TOTAL_PROFIT",
    "income_tax": "INCOME_TAX",
    "interest_expense": "FINANCE_EXPENSE",
}


def _safe_float(df: pd.DataFrame, col: str, date_val) -> float | None:
    if df is None or col not in df.columns:
        return None
    row = df[df["REPORT_DATE"] == date_val]
    if row.empty:
        return None
    val = row[col].iloc[0]
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def fetch_a_statements(code: str, conn, mock: dict | None = None) -> int:
    """
    Fetch A-share financial statements and write to financial_statements table.

    mock: optional dict with keys 'cash_flow', 'balance', 'profit' → DataFrames
          (for unit tests without network)
    Returns: number of rows written.
    """
    symbol = _aksymbol(code)

    if mock is not None:
        cf_df = mock.get("cash_flow")
        bs_df = mock.get("balance")
        pl_df = mock.get("profit")
    else:
        import akshare as ak

        cf_df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        bs_df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        try:
            pl_df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        except Exception as exc:
            logger.warning("profit sheet unavailable for %s: %s", code, exc)
            pl_df = None

    if cf_df is None or cf_df.empty:
        return 0

    rows = 0
    for date_val in cf_df["REPORT_DATE"]:
        date_str = (
            date_val.strftime("%Y-%m-%d")
            if hasattr(date_val, "strftime")
            else str(date_val)[:10]
        )

        operating_cf = _safe_float(cf_df, "NETCASH_OPERATE", date_val)
        capex_raw = _safe_float(cf_df, "CONSTRUCT_LONG_ASSET", date_val)
        capex = abs(capex_raw) if capex_raw is not None else None

        if operating_cf is None:
            continue

        fcf = round(operating_cf - (capex or 0.0), 2)

        cash = _safe_float(bs_df, "MONETARYFUNDS", date_val)
        total_liab = _safe_float(bs_df, "TOTAL_LIABILITIES", date_val)
        equity = _safe_float(bs_df, "TOTAL_EQUITY", date_val)

        revenue = _safe_float(pl_df, "TOTAL_OPERATE_INCOME", date_val)
        net_income = _safe_float(pl_df, "NETPROFIT", date_val)
        pretax_income = _safe_float(pl_df, "TOTAL_PROFIT", date_val)
        income_tax = _safe_float(pl_df, "INCOME_TAX", date_val)
        interest_expense = _safe_float(pl_df, "FINANCE_EXPENSE", date_val)

        raw_data = json.dumps(
            {
                "operating_cf": operating_cf,
                "capex": capex,
                "cash": cash,
                "total_liab": total_liab,
                "revenue": revenue,
                "net_income": net_income,
                "pretax_income": pretax_income,
                "income_tax": income_tax,
                "interest_expense": interest_expense,
            },
            ensure_ascii=False,
        )

        conn.execute(
            """INSERT OR REPLACE INTO financial_statements
               (code, report_date, fcf, operating_cf, capex, cash, total_liabilities,
                revenue, net_income, pretax_income, income_tax, interest_expense,
                equity, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                date_str,
                fcf,
                operating_cf,
                capex,
                cash,
                total_liab,
                revenue,
                net_income,
                pretax_income,
                income_tax,
                interest_expense,
                equity,
                raw_data,
            ),
        )
        rows += 1
    conn.commit()
    return rows
