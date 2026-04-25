#!/usr/bin/env python3
"""
tracker.py
==========
Performance tracking & benchmark comparison for the paper trading account.

Records NAV snapshots over time, compares against benchmarks (SPY, 60/40),
and generates performance reports.

Usage:
    python3 lab/trading/paper/tracker.py                     # latest report
    python3 lab/trading/paper/tracker.py --history           # all snapshots
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from lab.trading.paper.account import PaperAccount, ETF_MAP  # noqa: E402

DATA_DIR = ROOT / "lab" / "data"
SNAPSHOTS_FILE = DATA_DIR / "paper_snapshots.jsonl"

# Benchmark tickers and their weights for 60/40
BENCHMARK_60_40 = {"SPY": 0.60, "TLT": 0.40}


def _record_snapshot() -> dict[str, Any]:
    """Record current NAV snapshot to paper_snapshots.jsonl."""
    acct = PaperAccount()
    snap = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_equity": round(acct.total_equity, 2),
        "cash": round(acct.cash, 2),
        "pnl": round(acct.total_pnl, 2),
        "pnl_pct": round(acct.total_pnl_pct, 2),
        "num_positions": len(acct.positions),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOTS_FILE, "a") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")
    return snap


def _load_snapshots() -> list[dict[str, Any]]:
    """Load all historical NAV snapshots."""
    if not SNAPSHOTS_FILE.exists():
        return []
    snaps = []
    with open(SNAPSHOTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                snaps.append(json.loads(line))
    return snaps


def benchmark_return(
    benchmark: dict[str, float],
    start_date: str | None = None,
) -> dict[str, Any]:
    """Calculate benchmark return over the tracking period.

    Uses FRED data (SP500, T10Y2Y proxy for bond returns).

    This is a simplified benchmark — real benchmark tracking would
    need daily ETF price data.
    """
    # For now, return a placeholder
    return {
        "benchmark": "60/40 (SPY/TLT)",
        "note": "Full benchmark tracking requires daily price data feed",
        "estimated_return": None,
    }


def generate_report() -> dict[str, Any]:
    """Generate a performance report comparing account vs benchmark."""
    acct = PaperAccount()
    snaps = _load_snapshots()

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "account": acct.summary(),
        "snapshots": {
            "count": len(snaps),
            "first": snaps[0] if snaps else None,
            "latest": snaps[-1] if snaps else None,
        },
        "benchmark": benchmark_return(BENCHMARK_60_40),
    }

    # If we have enough snapshots, calculate return metrics
    if len(snaps) >= 2:
        first_equity = snaps[0]["total_equity"]
        last_equity = snaps[-1]["total_equity"]
        total_return = ((last_equity - first_equity) / first_equity) * 100

        # Simple annualized return (approximate)
        try:
            first_dt = datetime.fromisoformat(snaps[0]["timestamp"])
            last_dt = datetime.fromisoformat(snaps[-1]["timestamp"])
            days = (last_dt - first_dt).days
            if days > 0:
                annualized = ((1 + total_return / 100) ** (365 / days) - 1) * 100
            else:
                annualized = 0.0
        except Exception:
            annualized = None

        report["performance"] = {
            "total_return_pct": round(total_return, 2),
            "annualized_return_pct": round(annualized, 2) if annualized else None,
            "tracking_days": days if days else 0,
        }

    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Paper trading performance tracker")
    parser.add_argument("--snapshot", action="store_true",
                        help="Record a NAV snapshot now")
    parser.add_argument("--history", action="store_true",
                        help="Show all historical snapshots")
    args = parser.parse_args()

    if args.snapshot:
        snap = _record_snapshot()
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return

    if args.history:
        snaps = _load_snapshots()
        print(json.dumps(snaps, indent=2, ensure_ascii=False))
        return

    # Default: generate report
    report = generate_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
