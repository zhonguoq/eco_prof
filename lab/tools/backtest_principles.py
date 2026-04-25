#!/usr/bin/env python3
"""
backtest_principles.py
=====================
Backtest investment principles against historical FRED data.

Outputs structured JSON to stdout, logs to stderr.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
DATA_DIR = ROOT / "lab" / "data"

# ---------------------------------------------------------------------------
# NBER U.S. Recession Dates (monthly resolution)
# ---------------------------------------------------------------------------

NBER_RECESSIONS: list[tuple[str, str]] = [
    ("1990-07", "1991-03"),
    ("2001-03", "2001-11"),
    ("2007-12", "2009-06"),
    ("2020-02", "2020-04"),
]


def _read_series(series_id: str) -> pd.DataFrame | None:
    """Read latest CSV file for a raw FRED series (excludes derived series)."""
    import re
    pattern = str(DATA_DIR / f"fred_{series_id.lower()}_*.csv")
    all_files = sorted(glob.glob(pattern))
    # Filter: only match exact series_id (fred_{id}_YYYYMMDD.csv, not fred_{id}_extra_YYYYMMDD.csv)
    exact_files = [
        f for f in all_files
        if re.match(rf"fred_{series_id.lower()}_\d{{8}}\.csv$", Path(f).name)
    ]
    if not exact_files:
        return None
    df = pd.read_csv(exact_files[-1], index_col=0, parse_dates=True)
    df.columns = ["value"]
    return df.dropna()


def _is_in_recession(dt: datetime, recessions: list[tuple[str, str]]) -> bool:
    """Check if a given date falls within any NBER recession window."""
    for start, end in recessions:
        if start <= dt.strftime("%Y-%m") <= end:
            return True
    return False


def _compute_continuous_signals(
    series: pd.Series, condition: pd.Series
) -> list[tuple[str, str]]:
    """
    Find continuous periods where condition is True.
    Returns list of (start_date, end_date) strings.
    """
    signals: list[tuple[str, str]] = []
    in_signal = False
    signal_start = None

    for idx in series.index:
        if condition.loc[idx]:
            if not in_signal:
                signal_start = idx
                in_signal = True
        else:
            if in_signal and signal_start is not None:
                signals.append((signal_start.strftime("%Y-%m-%d"), idx.strftime("%Y-%m-%d")))
                in_signal = False
                signal_start = None

    if in_signal and signal_start is not None:
        signals.append((signal_start.strftime("%Y-%m-%d"), series.index[-1].strftime("%Y-%m-%d")))

    return signals


def _min_gap_months(start1: str, end1: str, start2: str, end2: str) -> int:
    """Minimum gap in months between two date ranges."""
    s1 = datetime.strptime(start1, "%Y-%m-%d")
    e1 = datetime.strptime(end1, "%Y-%m-%d")
    s2 = datetime.strptime(start2, "%Y-%m-%d")
    e2 = datetime.strptime(end2, "%Y-%m-%d")
    # Gap from end of first to start of second
    if e1 < s2:
        return (s2.year - e1.year) * 12 + (s2.month - e1.month)
    elif e2 < s1:
        return (s1.year - e2.year) * 12 + (s1.month - e2.month)
    else:
        return 0  # overlapping


def backtest_p001(verbose: bool = False) -> dict[str, Any]:
    """
    P001: 10Y-2Y yield curve inversion → recession within 24 months.

    Hypothesis: Continuous inversion (T10Y2Y < 0 for >= 30 trading days)
    is followed by an NBER recession within 24 months.
    """
    t10y2y = _read_series("T10Y2Y")
    if t10y2y is None:
        return {"error": "T10Y2Y data not found"}

    inverted = t10y2y["value"] < 0
    inversion_periods = _compute_continuous_signals(t10y2y["value"], inverted)

    if verbose:
        print(f"[P001] Found {len(inversion_periods)} inversion period(s)", file=sys.stderr)

    results: list[dict[str, Any]] = []
    for start_str, end_str in inversion_periods:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        duration_days = (end - start).days

        # Only count inversions lasting >= 30 trading days
        if duration_days < 30:
            if verbose:
                print(f"  Skipping brief inversion: {start_str} to {end_str} ({duration_days}d)", file=sys.stderr)
            continue

        # Check if a recession started within 24 months after the INVERSION START
        found_recession = None
        lead_months = None
        for r_start, r_end in NBER_RECESSIONS:
            r_dt = datetime.strptime(r_start, "%Y-%m")
            gap_months = (r_dt.year - start.year) * 12 + (r_dt.month - start.month)
            if 0 <= gap_months <= 24:
                found_recession = f"{r_start} to {r_end}"
                lead_months = gap_months
                break

        results.append({
            "inversion_start": start_str,
            "inversion_end": end_str,
            "duration_days": duration_days,
            "max_spread": round(float(t10y2y["value"].loc[start:end].min()), 2),
            "recession_followed": found_recession is not None,
            "recession_period": found_recession,
            "lead_months": lead_months,
        })

    # Summary stats
    total_signals = len(results)
    correct = sum(1 for r in results if r["recession_followed"])
    false_alarms = total_signals - correct
    lead_times = [r["lead_months"] for r in results if r["lead_months"] is not None]

    # Check for missed recessions (recession without prior inversion)
    missed = 0
    for r_start, _ in NBER_RECESSIONS:
        r_dt = datetime.strptime(r_start, "%Y-%m")
        # Check if any inversion signal preceded this recession
        preceded = False
        for r in results:
            inv_start = datetime.strptime(r["inversion_start"], "%Y-%m-%d")
            gap = (r_dt.year - inv_start.year) * 12 + (r_dt.month - inv_start.month)
            if 0 <= gap <= 24:
                preceded = True
                break
        if not preceded:
            missed += 1
            if verbose:
                print(f"  Missed recession: {r_start} (no prior inversion)", file=sys.stderr)

    summary = {
        "principle": "P001",
        "hypothesis": "T10Y2Y continuous inversion >= 30 days → NBER recession within 24 months",
        "period": f"{t10y2y.index[0].strftime('%Y-%m-%d')} to {t10y2y.index[-1].strftime('%Y-%m-%d')}",
        "total_signals": total_signals,
        "correct_predictions": correct,
        "false_alarms": false_alarms,
        "missed_recessions": missed,
        "total_recessions": len(NBER_RECESSIONS),
        "precision": round(correct / total_signals, 3) if total_signals else 0,
        "recall": round(correct / (correct + missed), 3) if (correct + missed) else 0,
        "avg_lead_months": round(sum(lead_times) / len(lead_times), 1) if lead_times else None,
        "min_lead_months": min(lead_times) if lead_times else None,
        "max_lead_months": max(lead_times) if lead_times else None,
        "details": results,
    }
    return summary


def backtest_p002(verbose: bool = False) -> dict[str, Any]:
    """
    P002: Nominal GDP growth > nominal interest rate → debt/GDP decreases.

    Hypothesis: When Nominal GDP YoY > DGS10 (10Y yield), the total debt/GDP
    ratio declines in the following 12 months.
    """
    gdp_raw = _read_series("GDP")       # $B quarterly
    tcmdo = _read_series("TCMDO")        # $M quarterly
    dgs10 = _read_series("DGS10")        # % daily

    if any(x is None for x in [gdp_raw, tcmdo, dgs10]):
        missing = [k for k, v in [("GDP", gdp_raw), ("TCMDO", tcmdo), ("DGS10", dgs10)] if v is None]
        return {"error": f"Data missing: {missing}"}

    # Compute nominal GDP YoY % (4-quarter change)
    gdp_yoy = gdp_raw["value"].pct_change(4) * 100

    # Compute debt/GDP ratio: TCMDO ($M) / 1000 = $B, then / GDP ($B) * 100 = %
    debt_gdp_pct = (tcmdo["value"] / 1000.0) / gdp_raw["value"] * 100

    # Quarterly average of DGS10 to match GDP frequency (GDP uses QS dates)
    dgs10_q = dgs10["value"].resample("QS").mean()

    # Align all series on quarterly index
    combined = pd.DataFrame({
        "gdp_yoy": gdp_yoy,
        "dgs10": dgs10_q,
        "debt_gdp_pct": debt_gdp_pct,
    }).dropna()

    if len(combined) < 8:
        return {"error": f"Insufficient aligned data: {len(combined)} quarters"}

    # P002 check: GDP YoY > DGS10?
    combined["growth_beats_rate"] = combined["gdp_yoy"] > combined["dgs10"]

    # 4-quarter-ahead change in debt/GDP (in percentage points, not % change)
    combined["debt_change_4q"] = combined["debt_gdp_pct"].diff(4)

    # Look 4 quarters ahead: after a favorable quarter, does debt/GDP drop?
    combined["debt_down_4q"] = combined["debt_change_4q"].shift(-4) < -1.0  # at least 1pp decline
    combined["debt_up_4q"] = combined["debt_change_4q"].shift(-4) > 1.0    # at least 1pp rise

    favorable = combined[combined["growth_beats_rate"]]
    unfavorable = combined[~combined["growth_beats_rate"]]

    debt_down_after_good = int(favorable["debt_down_4q"].sum())
    debt_up_after_bad = int(unfavorable["debt_up_4q"].sum())

    # Correlation: GDP YoY vs 4Q-ahead debt/GDP change
    corr = combined["gdp_yoy"].corr(combined["debt_change_4q"].shift(-4))

    if verbose:
        n_good = len(favorable)
        n_bad = len(unfavorable)
        print(f"[P002] Quarters with growth > rate: {n_good}", file=sys.stderr)
        print(f"[P002]   Debt/GDP ↓ 1yr later: {debt_down_after_good} ({debt_down_after_good/n_good*100:.0f}%)", file=sys.stderr)
        print(f"[P002] Quarters with rate > growth: {n_bad}", file=sys.stderr)
        print(f"[P002]   Debt/GDP ↑ 1yr later: {debt_up_after_bad} ({debt_up_after_bad/n_bad*100:.0f}%)", file=sys.stderr)
        print(f"[P002] Correlation(gdp_yoy, 4Q-ahead debt_change): {corr:.3f}", file=sys.stderr)

    return {
        "principle": "P002",
        "hypothesis": "Nominal GDP YoY > 10Y yield → debt/GDP decreases in following year",
        "period": f"{combined.index[0].strftime('%Y-%m-%d')} to {combined.index[-1].strftime('%Y-%m-%d')}",
        "total_quarters": len(combined),
        "favorable_quarters": int(combined["growth_beats_rate"].sum()),
        "unfavorable_quarters": int((~combined["growth_beats_rate"]).sum()),
        "debt_decreased_after_favorable": debt_down_after_good,
        "favorable_debt_decrease_rate": round(debt_down_after_good / int(combined["growth_beats_rate"].sum()), 3) if combined["growth_beats_rate"].sum() else None,
        "debt_increased_after_unfavorable": debt_up_after_bad,
        "unfavorable_debt_increase_rate": round(debt_up_after_bad / int((~combined["growth_beats_rate"]).sum()), 3) if (~combined["growth_beats_rate"]).sum() else None,
        "correlation_gdp_vs_debt_change": round(corr, 3),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def backtest_p005(verbose: bool = False) -> dict[str, Any]:
    """
    P005: Asset-inflation divergence → market correction.

    Hypothesis: When SP500 YoY - CPI YoY > 15% (elevated divergence),
    the S&P 500 corrects > 10% within 12 months (mean reversion).
    """
    sp500 = _read_series("SP500")
    cpiaucsl = _read_series("CPIAUCSL")

    if sp500 is None or cpiaucsl is None:
        missing = [k for k, v in [("SP500", sp500), ("CPIAUCSL", cpiaucsl)] if v is None]
        return {"error": f"Data missing: {missing}"}

    # Monthly data: compute YoY changes (12-month pct_change)
    sp500_yoy = sp500["value"].pct_change(12) * 100
    cpi_yoy = cpiaucsl["value"].pct_change(12) * 100

    # SP500 forward returns: 12-month ahead pct change from current month's close
    # This tells us: if we signal today, what does SP500 do in the next year?
    sp500_fwd_1y = sp500["value"].pct_change(12).shift(-12) * 100

    # Align
    combined = pd.DataFrame({
        "sp500_yoy": sp500_yoy,
        "cpi_yoy": cpi_yoy,
        "divergence": sp500_yoy - cpi_yoy,
        "sp500_fwd_1y": sp500_fwd_1y,
    }).dropna()

    if len(combined) < 12:
        return {"error": f"Insufficient aligned data: {len(combined)} months"}

    # Test: divergence thresholds
    thresholds = [15, 20, 25]
    results_by_threshold = {}

    for threshold in thresholds:
        signals = combined[combined["divergence"] > threshold].copy()
        n_signals = len(signals)

        if n_signals == 0:
            results_by_threshold[str(threshold)] = {
                "n_signals": 0,
                "note": f"No divergence events > {threshold}% in this dataset"
            }
            continue

        corrected = signals[signals["sp500_fwd_1y"] < -10]
        n_corrected = len(corrected)
        avg_fwd_return = signals["sp500_fwd_1y"].mean()

        if verbose:
            print(f"[P005] Threshold >{threshold}%: {n_signals} signals", file=sys.stderr)
            print(f"[P005]   Corrected >10% within 12mo: {n_corrected} ({n_corrected/n_signals*100:.0f}%)", file=sys.stderr)
            print(f"[P005]   Avg 12mo fwd return: {avg_fwd_return:.1f}%", file=sys.stderr)

        results_by_threshold[str(threshold)] = {
            "n_signals": int(n_signals),
            "corrected_10pct": int(n_corrected),
            "correction_rate": round(n_corrected / n_signals, 3),
            "avg_fwd_1y_return": round(float(avg_fwd_return), 1),
            "max_fwd_return": round(float(signals["sp500_fwd_1y"].max()), 1),
            "min_fwd_return": round(float(signals["sp500_fwd_1y"].min()), 1),
        }

    # Asymmetry check: what happens when divergence is very negative?
    extreme_neg = combined[combined["divergence"] < -15]
    neg_avg_fwd = extreme_neg["sp500_fwd_1y"].mean() if len(extreme_neg) else None

    # Correlation
    corr = combined["divergence"].corr(combined["sp500_fwd_1y"])

    if verbose:
        print(f"[P005] Extreme negative divergence (<-15%): {len(extreme_neg)} months, avg fwd: {neg_avg_fwd:.1f}%", file=sys.stderr)
        print(f"[P005] Correlation(divergence, 12mo fwd): {corr:.3f}", file=sys.stderr)

    return {
        "principle": "P005",
        "hypothesis": "SP500 YoY - CPI YoY > 15% → market correction >10% within 12 months",
        "period": f"{combined.index[0].strftime('%Y-%m-%d')} to {combined.index[-1].strftime('%Y-%m-%d')}",
        "total_months": len(combined),
        "mean_divergence": round(float(combined["divergence"].mean()), 2),
        "std_divergence": round(float(combined["divergence"].std()), 2),
        "max_divergence": round(float(combined["divergence"].max()), 2),
        "by_threshold": results_by_threshold,
        "extreme_negative_avg_fwd_return": round(float(neg_avg_fwd), 1) if neg_avg_fwd is not None else None,
        "correlation_divergence_fwd_return": round(corr, 3),
    }


BACKTEST_FUNCTIONS = {
    "P001": backtest_p001,
    "P002": backtest_p002,
    "P005": backtest_p005,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest investment principles")
    parser.add_argument("--principle", choices=list(BACKTEST_FUNCTIONS.keys()) + ["all"],
                        default="all", help="Principle to backtest")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    results = {}
    principles = list(BACKTEST_FUNCTIONS.keys()) if args.principle == "all" else [args.principle]

    for pid in principles:
        if args.verbose:
            print(f"Backtesting {pid}...", file=sys.stderr)
        result = BACKTEST_FUNCTIONS[pid](verbose=args.verbose)
        results[pid] = result

    # Stdout: JSON only
    json.dump(results, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
