"""
fetch_us_indicators.py
======================
Fetches key US macroeconomic indicators for the Big Debt Cycle diagnostic framework.

Indicators (mapped to 债务周期阶段判断框架):
  Group 1 — Debt Health
    - Total credit / GDP (TCMDO / GDP)
    - Household Debt Service Ratio (DSR)
    - Federal debt / GDP (GFDEGDQ188S)

  Group 2 — Monetary Policy Space
    - Fed Funds Rate (FEDFUNDS)
    - 2-Year Treasury (DGS2)
    - 10-Year Treasury (DGS10)
    - Yield curve spread: 10Y - 2Y (T10Y2Y, or computed)

  Group 3 — Nominal Growth vs Rates
    - Nominal GDP YoY growth (GDP, quarterly)
    - CPI YoY (CPIAUCSL)

  Early-warning signals
    - ICE BofA US High Yield Option-Adjusted Spread (BAMLH0A0HYM2)
    - Delinquency rate on credit cards (DRCCLACBS)

Output: saves one CSV per series to lab/data/ with naming convention:
    fred_<series_id_lower>_<YYYYMMDD>.csv
"""

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    from fredapi import Fred
except ImportError:
    print("Missing dependencies. Run:\n  pip install fredapi pandas")
    sys.exit(1)

from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("FRED_API_KEY", "570a0b9586e360ca11335b9f032e1e2d")

# Output directory relative to this script's location (lab/tools/ → lab/data/)
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.today().strftime("%Y%m%d")

# Observation window — 30 years of history is enough for cycle analysis
START_DATE = "1995-01-01"

# Series to fetch: {series_id: human_readable_name}
SERIES = {
    # Group 1 — Debt Health
    "TCMDO":         "Total Credit Market Debt Outstanding ($ billions)",
    "GDP":           "Nominal GDP ($ billions, quarterly, SAAR)",
    "GFDEGDQ188S":   "Federal Debt / GDP (%)",
    "DPSACBW027SBOG":"Household Debt Service Ratio (DSR, %)",

    # Group 2 — Monetary Policy Space
    "FEDFUNDS":      "Federal Funds Effective Rate (%)",
    "DGS2":          "2-Year Treasury Constant Maturity Rate (%)",
    "DGS10":         "10-Year Treasury Constant Maturity Rate (%)",
    "T10Y2Y":        "10Y-2Y Treasury Spread (%, daily) — FRED computed",

    # Group 3 — Nominal Growth vs Rates
    "CPIAUCSL":      "CPI All Urban Consumers (index, SA)",

    # Group 4 — Growth-Inflation Regime
    "GDPC1":         "Real GDP ($ billions, quarterly, SAAR)",
    "UNRATE":        "Unemployment Rate (%)",
    "UMCSENT":       "U of Michigan Consumer Sentiment Index",
    "DTWEXBGS":      "Trade Weighted US Dollar Index (Broad, Goods & Services)",

    # Early-warning
    "BAMLH0A0HYM2":  "ICE BofA US HY OAS (credit spread, %)",
    "DRCCLACBS":     "Credit Card Delinquency Rate (%, quarterly)",

    # Group 5 — Asset-Inflation Divergence (P005)
    "SP500":         "S&P 500 Index (monthly, SA)",
}


def fetch_series(fred: Fred, series_id: str, name: str) -> Optional[pd.DataFrame]:
    """Fetch a single FRED series and return as a DataFrame."""
    try:
        s = fred.get_series(series_id, observation_start=START_DATE)
        df = s.to_frame(name=name)
        df.index.name = "date"
        return df
    except Exception as e:
        print(f"  [WARN] {series_id}: {e}")
        return None


def compute_yield_spread(dfs: "dict[str, pd.DataFrame]") -> Optional[pd.DataFrame]:
    """Compute 10Y-2Y spread from raw series if T10Y2Y is unavailable."""
    if "DGS10" in dfs and "DGS2" in dfs:
        spread = dfs["DGS10"].iloc[:, 0] - dfs["DGS2"].iloc[:, 0]
        df = spread.to_frame(name="10Y-2Y Spread (computed, %)")
        df.index.name = "date"
        return df
    return None


def compute_nominal_gdp_growth(dfs: "dict[str, pd.DataFrame]") -> Optional[pd.DataFrame]:
    """Compute nominal GDP YoY growth rate from quarterly GDP series."""
    if "GDP" in dfs:
        gdp = dfs["GDP"].iloc[:, 0].dropna()
        yoy = gdp.pct_change(4) * 100  # 4 quarters back
        df = yoy.to_frame(name="Nominal GDP YoY Growth (%)")
        df.index.name = "date"
        return df
    return None


def compute_real_gdp_growth(dfs: "dict[str, pd.DataFrame]") -> Optional[pd.DataFrame]:
    """Compute real GDP YoY growth rate from quarterly real GDP series."""
    if "GDPC1" in dfs:
        rgdp = dfs["GDPC1"].iloc[:, 0].dropna()
        yoy = rgdp.pct_change(4) * 100
        df = yoy.to_frame(name="Real GDP YoY Growth (%)")
        df.index.name = "date"
        return df
    return None


def compute_cpi_yoy(dfs: "dict[str, pd.DataFrame]") -> Optional[pd.DataFrame]:
    """Compute CPI YoY inflation rate from monthly CPI index."""
    if "CPIAUCSL" in dfs:
        cpi = dfs["CPIAUCSL"].iloc[:, 0].dropna()
        yoy = cpi.pct_change(12) * 100  # 12 months back
        df = yoy.to_frame(name="CPI YoY Inflation (%)")
        df.index.name = "date"
        return df
    return None


def compute_sp500_yoy(dfs: "dict[str, pd.DataFrame]") -> Optional[pd.DataFrame]:
    """Compute S&P 500 YoY % change from monthly SP500 index."""
    if "SP500" in dfs:
        sp500 = dfs["SP500"].iloc[:, 0].dropna()
        yoy = sp500.pct_change(12) * 100  # 12 months back
        df = yoy.to_frame(name="S&P 500 YoY Change (%)")
        df.index.name = "date"
        return df
    return None


def compute_asset_inflation_divergence(
    dfs: "dict[str, pd.DataFrame]",
) -> Optional[pd.DataFrame]:
    """
    Compute asset price vs goods price divergence (P005).

    divergence = SP500 YoY (%) - CPI YoY (%)

    A large positive value means asset prices are inflating much faster than
    consumer goods — a signal of potential asset bubble / credit-fueled speculation.
    """
    sp500_yoy = None
    cpi_yoy = None
    if "SP500" in dfs:
        sp500 = dfs["SP500"].iloc[:, 0].dropna()
        sp500_yoy = sp500.pct_change(12) * 100
    if "CPIAUCSL" in dfs:
        cpi = dfs["CPIAUCSL"].iloc[:, 0].dropna()
        cpi_yoy = cpi.pct_change(12) * 100

    if sp500_yoy is not None and cpi_yoy is not None:
        # Align by joining on date index
        combined = sp500_yoy.to_frame("sp500_yoy").join(cpi_yoy.to_frame("cpi_yoy"), how="inner")
        divergence = (combined["sp500_yoy"] - combined["cpi_yoy"]).to_frame(
            name="Asset Inflation Divergence (SP500 YoY - CPI YoY, %)"
        )
        divergence.index.name = "date"
        return divergence
    return None


def save(df: pd.DataFrame, label: str) -> Path:
    """Save DataFrame to CSV, return path."""
    filename = f"fred_{label.lower()}_{TODAY}.csv"
    path = DATA_DIR / filename
    df.to_csv(path)
    return path


def main():
    print(f"Connecting to FRED API...")
    fred = Fred(api_key=API_KEY)

    dfs = {}  # type: dict[str, pd.DataFrame]

    print(f"\nFetching {len(SERIES)} series (start={START_DATE})...")
    for series_id, name in SERIES.items():
        print(f"  {series_id}: {name[:60]}")
        df = fetch_series(fred, series_id, name)
        if df is not None:
            dfs[series_id] = df

    # Derived series
    spread_computed = compute_yield_spread(dfs)
    if "T10Y2Y" not in dfs and spread_computed is not None:
        print("  T10Y2Y not available — using computed 10Y-2Y spread instead")
        dfs["T10Y2Y_computed"] = spread_computed

    gdp_growth = compute_nominal_gdp_growth(dfs)
    if gdp_growth is not None:
        dfs["GDP_YOY"] = gdp_growth

    rgdp_growth = compute_real_gdp_growth(dfs)
    if rgdp_growth is not None:
        dfs["RGDP_YOY"] = rgdp_growth

    cpi_yoy = compute_cpi_yoy(dfs)
    if cpi_yoy is not None:
        dfs["CPI_YOY"] = cpi_yoy

    # P005 — Asset price YoY and divergence from inflation
    sp500_yoy = compute_sp500_yoy(dfs)
    if sp500_yoy is not None:
        dfs["SP500_YOY"] = sp500_yoy

    divergence = compute_asset_inflation_divergence(dfs)
    if divergence is not None:
        dfs["ASSET_INFLATION_DIVERGENCE"] = divergence

    # Save each series
    print(f"\nSaving to {DATA_DIR}/")
    saved_paths = []
    for series_id, df in dfs.items():
        path = save(df, series_id)
        saved_paths.append(path)
        print(f"  -> {path.name}  ({len(df)} rows)")

    # Build a merged snapshot (latest value per series)
    print("\nBuilding latest-values snapshot...")
    rows = []
    for series_id, df in dfs.items():
        latest = df.dropna().iloc[-1] if not df.dropna().empty else None
        if latest is not None:
            rows.append({
                "series_id": series_id,
                "name": df.columns[0],
                "latest_date": df.dropna().index[-1].strftime("%Y-%m-%d"),
                "latest_value": round(float(latest.iloc[0]), 4),
            })

    snapshot = pd.DataFrame(rows)
    snapshot_path = DATA_DIR / f"fred_snapshot_{TODAY}.csv"
    snapshot.to_csv(snapshot_path, index=False)
    print(f"  -> {snapshot_path.name}")

    # Print snapshot to console
    print("\n" + "=" * 70)
    print("US DEBT CYCLE INDICATORS — LATEST VALUES")
    print("=" * 70)
    print(snapshot.to_string(index=False))
    print("=" * 70)
    print(f"\nDone. {len(saved_paths) + 1} files written to {DATA_DIR}")


if __name__ == "__main__":
    main()
