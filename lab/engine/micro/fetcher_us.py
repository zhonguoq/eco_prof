"""US-share financial statements fetcher.

Uses akshare stock_financial_us_report_em long-table API.
Each row: REPORT_DATE / STD_ITEM_NAME / AMOUNT.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ── Field map: logical name → STD_ITEM_NAME alias(es) ────────────────────

FIELD_MAP_US: dict[str, str | list[str]] = {
    # 现金流量表 (column=ITEM_NAME)
    "operating_cf": "经营活动产生的现金流量净额",
    "capex": ["购买固定资产", "资本支出", "购建固定资产支付的现金"],
    # 资产负债表
    "cash": ["现金及现金等价物", "货币资金"],
    "total_liab": "总负债",
    "equity": ["股东权益合计", "归属于母公司股东权益"],
    # 综合损益表
    "revenue": ["营业收入", "主营收入"],
    "net_income": ["净利润", "持续经营净利润"],
    "pretax_income": ["持续经营税前利润", "税前利润"],
    "income_tax": "所得税",
    "interest_expense": None,  # not available in eastmoney US data; will degrade in WACC L3
}


# ── Long-table pivot helper ───────────────────────────────────────────────


_US_ITEM_COL = "ITEM_NAME"  # US long-table uses ITEM_NAME (not STD_ITEM_NAME)


def _lookup(
    df: pd.DataFrame,
    date_val: pd.Timestamp,
    aliases: str | list | None,
    item_col: str = _US_ITEM_COL,
) -> float | None:
    """Return AMOUNT for the first matching alias at the given report date."""
    if aliases is None:
        return None
    if isinstance(aliases, str):
        aliases = [aliases]
    if df.empty or item_col not in df.columns:
        return None
    sub = df[df["REPORT_DATE"] == date_val]
    for alias in aliases:
        match = sub[sub[item_col] == alias]
        if not match.empty:
            try:
                return float(match["AMOUNT"].iloc[0])
            except (TypeError, ValueError):
                continue
    return None


def _pivot_row(df: pd.DataFrame, date_val: pd.Timestamp) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, aliases in FIELD_MAP_US.items():
        result[field] = _lookup(df, date_val, aliases)
    return result


# ── Main fetcher ──────────────────────────────────────────────────────────


def fetch_us_statements(code: str, conn, mock: dict | None = None) -> int:
    """
    Fetch US-share financials and write to financial_statements table.

    mock: dict with keys 'cash_flow', 'balance', 'profit' → DataFrames
    Returns: number of rows written.
    """
    if mock is not None:
        cf_df = mock.get("cash_flow", pd.DataFrame())
        bs_df = mock.get("balance", pd.DataFrame())
        pl_df = mock.get("profit", pd.DataFrame())
    else:
        import akshare as ak

        # akshare US: symbol = statement type name, valid values:
        #   "资产负债表" / "综合损益表" / "现金流量表"
        try:
            cf_df = ak.stock_financial_us_report_em(
                stock=code, symbol="现金流量表", indicator="年报"
            )
        except Exception as exc:
            logger.error("US cash_flow fetch failed for %s: %s", code, exc)
            cf_df = pd.DataFrame()
        try:
            bs_df = ak.stock_financial_us_report_em(
                stock=code, symbol="资产负债表", indicator="年报"
            )
        except Exception as exc:
            logger.warning("US balance fetch failed for %s: %s", code, exc)
            bs_df = pd.DataFrame()
        try:
            pl_df = ak.stock_financial_us_report_em(
                stock=code, symbol="综合损益表", indicator="年报"
            )
        except Exception as exc:
            logger.warning("US profit fetch failed for %s: %s", code, exc)
            pl_df = pd.DataFrame()

    all_df = _concat_long(cf_df, bs_df, pl_df)

    if all_df.empty or "REPORT_DATE" not in all_df.columns:
        return 0

    dates = sorted(all_df["REPORT_DATE"].unique())
    rows = 0
    for date_val in dates:
        date_str = (
            date_val.strftime("%Y-%m-%d")
            if hasattr(date_val, "strftime")
            else str(date_val)[:10]
        )

        fields = _pivot_row(all_df, date_val)

        operating_cf = fields.get("operating_cf")
        if operating_cf is None:
            continue

        capex = fields.get("capex")
        capex_abs = abs(capex) if capex is not None else None
        fcf = round(operating_cf - (capex_abs or 0.0), 2)

        raw_data = json.dumps(fields, ensure_ascii=False)

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
                capex_abs,
                fields.get("cash"),
                fields.get("total_liab"),
                fields.get("revenue"),
                fields.get("net_income"),
                fields.get("pretax_income"),
                fields.get("income_tax"),
                fields.get("interest_expense"),
                fields.get("equity"),
                raw_data,
            ),
        )
        rows += 1
    conn.commit()
    return rows


def _concat_long(*dfs: pd.DataFrame) -> pd.DataFrame:
    non_empty = [d for d in dfs if not d.empty and "REPORT_DATE" in d.columns]
    if not non_empty:
        return pd.DataFrame()
    combined = pd.concat(non_empty, ignore_index=True)
    # US tables use ITEM_NAME; deduplicate on (REPORT_DATE, ITEM_NAME)
    if _US_ITEM_COL in combined.columns:
        combined = combined.drop_duplicates(
            subset=["REPORT_DATE", _US_ITEM_COL], keep="first"
        )
    return combined
