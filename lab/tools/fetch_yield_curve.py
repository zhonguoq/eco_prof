"""
fetch_yield_curve.py
====================
Fetches all US Treasury constant-maturity yield series from FRED and saves
a single wide-format CSV suitable for yield-curve snapshot queries.

Output:
  lab/data/fred_yield_curve_YYYYMMDD.csv
  Columns: date (index), DGS1MO, DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5,
           DGS7, DGS10, DGS20, DGS30

Usage:
  python fetch_yield_curve.py
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY  = os.environ.get("FRED_API_KEY", "570a0b9586e360ca11335b9f032e1e2d")
SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY      = datetime.today().strftime("%Y%m%d")
START_DATE = "1990-01-01"   # enough history to capture multiple full cycles

# (series_id, human label, months)
MATURITIES = [
    ("DGS1MO", "1-Month",  1),
    ("DGS3MO", "3-Month",  3),
    ("DGS6MO", "6-Month",  6),
    ("DGS1",   "1-Year",  12),
    ("DGS2",   "2-Year",  24),
    ("DGS3",   "3-Year",  36),
    ("DGS5",   "5-Year",  60),
    ("DGS7",   "7-Year",  84),
    ("DGS10",  "10-Year", 120),
    ("DGS20",  "20-Year", 240),
    ("DGS30",  "30-Year", 360),
]

# ---------------------------------------------------------------------------

def main():
    print("Connecting to FRED API...")
    fred = Fred(api_key=API_KEY)

    frames = {}
    for series_id, label, _ in MATURITIES:
        print(f"  Fetching {series_id} ({label})...")
        try:
            s = fred.get_series(series_id, observation_start=START_DATE)
            frames[series_id] = s
        except Exception as e:
            print(f"  [WARN] {series_id}: {e}")

    if not frames:
        print("No data fetched. Exiting.")
        sys.exit(1)

    # Merge into wide-format, daily index
    df = pd.DataFrame(frames)
    df.index.name = "date"
    df = df.sort_index()

    # Forward-fill short gaps (weekends / holidays), max 5 calendar days
    df = df.ffill(limit=5)

    out_path = DATA_DIR / f"fred_yield_curve_{TODAY}.csv"
    df.to_csv(out_path)
    print(f"\nSaved {len(df)} rows × {len(df.columns)} maturities → {out_path.name}")
    print(f"Date range: {df.dropna(how='all').index.min().date()} → {df.dropna(how='all').index.max().date()}")


if __name__ == "__main__":
    main()
