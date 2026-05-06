"""HK-share financial statements fetcher.

Uses akshare stock_financial_hk_report_em long-table API.
Each row: REPORT_DATE / STD_ITEM_NAME / AMOUNT.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ── Field map: logical name → STD_ITEM_NAME alias(es) ────────────────────
# Value is str (primary) or list[str] (primary + fallbacks tried in order).

FIELD_MAP_HK: dict[str, str | list[str]] = {
    # 现金流量表 (indirect method, HK GAAP)
    "operating_cf": ["经营业务现金净额", "经营活动产生的现金流量净额"],
    "capex": [
        "购建无形资产及其他资产",  # primary (seen in Tencent/HK stocks)
        "购建固定资产及无形资产",  # alias variant
        "购建固定资产、无形资产和其他资产",
    ],
    # 资产负债表
    "cash": ["现金及等价物", "货币资金", "现金及现金等价物"],
    "total_liab": ["总负债", "负债合计"],
    "equity": ["股东权益", "总权益", "股东权益合计"],
    # 利润表
    "revenue": ["营业额", "营运收入", "营业收入"],
    "net_income": ["股东应占溢利", "净利润", "本期净利润"],
    "pretax_income": ["除税前溢利", "税前溢利", "税前利润"],
    "income_tax": ["税项", "所得税费用", "所得税"],
    "interest_expense": ["融资成本", "利息支出", "财务费用"],
}


# ── Long-table pivot helper ───────────────────────────────────────────────


def _lookup(
    df: pd.DataFrame, date_val: pd.Timestamp, aliases: str | list
) -> float | None:
    """Find first matching alias in long-table df for the given date."""
    if isinstance(aliases, str):
        aliases = [aliases]
    sub = df[df["REPORT_DATE"] == date_val]
    for alias in aliases:
        match = sub[sub["STD_ITEM_NAME"] == alias]
        if not match.empty:
            try:
                return float(match["AMOUNT"].iloc[0])
            except (TypeError, ValueError):
                continue
    return None


def _pivot_row(df: pd.DataFrame, date_val: pd.Timestamp) -> dict[str, Any]:
    """Extract all FIELD_MAP_HK fields for one report date."""
    result: dict[str, Any] = {}
    for field, aliases in FIELD_MAP_HK.items():
        result[field] = _lookup(df, date_val, aliases)
    return result


# ── Main fetcher ──────────────────────────────────────────────────────────


def fetch_hk_statements(code: str, conn, mock: dict | None = None) -> int:
    """
    Fetch HK-share financials and write to financial_statements table.

    mock: dict with keys 'cash_flow', 'balance', 'profit' → DataFrames
    Returns: number of rows written.
    """
    # Strip .HK suffix to get numeric code for akshare
    ak_code = code.split(".")[0]

    if mock is not None:
        cf_df = mock.get("cash_flow", pd.DataFrame())
        bs_df = mock.get("balance", pd.DataFrame())
        pl_df = mock.get("profit", pd.DataFrame())
    else:
        import akshare as ak

        # akshare HK: symbol = statement type name, indicator = '年度'
        # ak_code must be zero-padded 5-digit (e.g. '00700')
        ak_code_padded = ak_code.zfill(5)
        try:
            cf_df = ak.stock_financial_hk_report_em(
                stock=ak_code_padded, symbol="现金流量表", indicator="年度"
            )
        except Exception as exc:
            logger.error("HK cash_flow fetch failed for %s: %s", code, exc)
            cf_df = pd.DataFrame()
        try:
            bs_df = ak.stock_financial_hk_report_em(
                stock=ak_code_padded, symbol="资产负债表", indicator="年度"
            )
        except Exception as exc:
            logger.warning("HK balance fetch failed for %s: %s", code, exc)
            bs_df = pd.DataFrame()
        try:
            pl_df = ak.stock_financial_hk_report_em(
                stock=ak_code_padded, symbol="利润表", indicator="年度"
            )
        except Exception as exc:
            logger.warning("HK profit fetch failed for %s: %s", code, exc)
            pl_df = pd.DataFrame()

    # Merge all three long tables on (REPORT_DATE, STD_ITEM_NAME)
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
    """Concatenate long-table DataFrames, deduplicate by (REPORT_DATE, STD_ITEM_NAME)."""
    non_empty = [d for d in dfs if not d.empty and "REPORT_DATE" in d.columns]
    if not non_empty:
        return pd.DataFrame()
    combined = pd.concat(non_empty, ignore_index=True)
    # Keep first occurrence (cash_flow has priority)
    combined = combined.drop_duplicates(
        subset=["REPORT_DATE", "STD_ITEM_NAME"], keep="first"
    )
    return combined
