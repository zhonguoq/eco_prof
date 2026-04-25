#!/usr/bin/env python3
"""
fetch_cn_indicators.py
======================
Fetches China macroeconomic indicators for regime diagnosis and cycle analysis.

Sources:
  - World Bank API (free, no key): GDP growth, CPI, debt/GDP, population
  - FRED: USDCNY exchange rate, China GDP index
  - Output: one CSV per series to lab/data/

Usage:
    python3 lab/tools/fetch_cn_indicators.py

Requires:
    pip install pandas requests
    (if using FRED series) pip install fredapi && export FRED_API_KEY=...
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    print("Missing requests. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.today().strftime("%Y%m%d")

# ---- World Bank API ----
WB_BASE = "http://api.worldbank.org/v2/country/CN/indicator"

# World Bank indicators for China
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG":   "GDP Growth (annual %, real)",
    "FP.CPI.TOTL.ZG":      "CPI Inflation (annual %)",
    "GC.DOD.TOTL.GD.ZS":   "Central Government Debt/GDP (%)",
    "NY.GDP.MKTP.CD":      "GDP (current US$)",
    "NE.EXP.GNFS.KD.ZG":   "Exports Growth (annual %, real)",
    "GC.TAX.TOTL.GD.ZS":   "Tax Revenue/GDP (%)",
    "BN.CAB.XOKA.GD.ZS":   "Current Account Balance/GDP (%)",
    "SL.UEM.TOTL.ZS":      "Unemployment Rate (%)",
    "SP.POP.TOTL":         "Population, total",
}

SERIES = dict(WB_INDICATORS)

# Additional FRED China series
SERIES["DEXCHUS"] = "China / US Foreign Exchange Rate (CNY per USD)"

FRED_CHINA_SERIES: dict[str, str] = {
    "DEXCHUS": "China / US Foreign Exchange Rate (CNY per USD)",
}

# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


def fetch_wb(indicator: str, name: str) -> pd.DataFrame | None:
    """Fetch a World Bank indicator for China.

    Returns DataFrame with date index (year) and 'value' column, or None.
    """
    url = f"{WB_BASE}/{indicator}?format=json&per_page=1000"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[fetch_cn] WB error {indicator}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, list) or len(data) < 2 or data[1] is None:
        print(f"[fetch_cn] WB empty response for {indicator}", file=sys.stderr)
        return None

    records = []
    for entry in data[1]:
        year = entry.get("date", "")
        value = entry.get("value")
        if year and value is not None:
            try:
                records.append({
                    "date": f"{year}-01-01",
                    "value": float(value),
                })
            except (ValueError, TypeError):
                continue

    if not records:
        return None

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df.columns = ["value"]
    return df


def fetch_fred_china(series_id: str, name: str) -> pd.DataFrame | None:
    """Fetch a China-related FRED series (requires fredapi)."""
    try:
        from fredapi import Fred
    except ImportError:
        print("[fetch_cn] fredapi not installed—skipping FRED series", file=sys.stderr)
        return None

    api_key = os.environ.get("FRED_API_KEY", "570a0b9586e360ca11335b9f032e1e2d")
    if not api_key:
        print("[fetch_cn] FRED_API_KEY not set—skipping FRED series", file=sys.stderr)
        return None

    try:
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id, observation_start="1995-01-01")
        df = s.to_frame(name="value")
        df.index.name = "date"
        return df
    except Exception as e:
        print(f"[fetch_cn] FRED error {series_id}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Derived computations
# ---------------------------------------------------------------------------


def compute_cn_gdp_usd(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    """China GDP in current USD — pass-through of WB series."""
    return dfs.get("NY.GDP.MKTP.CD")


def compute_cn_m2_gdp(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    """Approximate China M2/GDP ratio (proxy for financial depth).

    Note: True M2 data would need PBOC/Haver. This is a placeholder
    using available WB indicators.
    """
    # Without actual M2 data, we compute nothing for now
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"[fetch_cn] Starting China indicator fetch ({TODAY})", file=sys.stderr)

    dfs: dict[str, pd.DataFrame] = {}

    # 1. World Bank indicators
    for indicator, name in WB_INDICATORS.items():
        df = fetch_wb(indicator, name)
        if df is not None:
            dfs[indicator] = df
            print(f"[fetch_cn] WB {indicator}: {len(df)} obs, "
                  f"{df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}",
                  file=sys.stderr)

    # 2. FRED China series
    for series_id, name in FRED_CHINA_SERIES.items():
        df = fetch_fred_china(series_id, name)
        if df is not None:
            dfs[series_id] = df
            print(f"[fetch_cn] FRED {series_id}: {len(df)} obs, "
                  f"{df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}",
                  file=sys.stderr)

    # 3. Save all series to CSV
    saved = 0
    for series_id, df in dfs.items():
        # Normalize: keep the value column name clean
        out = df.copy()
        out.columns = ["value"]

        # Use a clean slug
        slug = series_id.lower().replace(".", "_").replace("-", "_")
        path = DATA_DIR / f"cn_{slug}_{TODAY}.csv"
        out.to_csv(path)
        saved += 1

        # Print latest value to stderr for verification
        print(f"  → {series_id}: latest = {out['value'].iloc[-1]:.2f} "
              f"({out.index[-1].strftime('%Y-%m-%d')})",
              file=sys.stderr)

    # 4. Create snapshot
    snapshot_records = []
    for series_id, original_name in SERIES.items():
        slug = series_id.lower().replace(".", "_").replace("-", "_")
        if series_id in dfs:
            df = dfs[series_id]
            snapshot_records.append({
                "series_id": series_id,
                "name": original_name,
                "latest_date": df.index[-1].strftime("%Y-%m-%d"),
                "latest_value": float(df["value"].iloc[-1]),
            })

    if snapshot_records:
        snapshot_df = pd.DataFrame(snapshot_records)
        snapshot_path = DATA_DIR / f"cn_snapshot_{TODAY}.csv"
        snapshot_df.to_csv(snapshot_path, index=False)
        print(f"[fetch_cn] Snapshot saved: {snapshot_path}", file=sys.stderr)
        print(f"[fetch_cn] Total series saved: {saved}/{len(SERIES)}", file=sys.stderr)

    # 5. Output JSON summary to stdout
    output = {
        "fetched_at": datetime.now().isoformat(),
        "date": TODAY,
        "total_series": len(SERIES),
        "saved": saved,
        "series": [
            {"id": k, "name": v} for k, v in SERIES.items()
        ],
        "latest_values": {
            k: {
                "value": float(dfs[k]["value"].iloc[-1]),
                "date": dfs[k].index[-1].strftime("%Y-%m-%d"),
            }
            for k in dfs
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
