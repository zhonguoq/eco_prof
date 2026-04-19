"""
FastAPI backend for the Macro Regime Dashboard.
Reads CSV files from lab/data/ and exposes REST endpoints.

Endpoints:
  GET  /api/snapshot            — latest value for every indicator
  GET  /api/series/{id}         — full historical time series
  GET  /api/diagnosis           — debt cycle stage signals
  GET  /api/regime              — growth-inflation regime + asset tilts
  GET  /api/diagnosis/history   — historical diagnosis records
  POST /api/refresh             — manually trigger data refresh
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .scheduler import scheduler_lifespan

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).parent
DATA_DIR = BACKEND_DIR.parent.parent / "data"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Macro Regime Dashboard API", lifespan=scheduler_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SERIES_META = {
    # Group 1 — Debt Health
    "TCMDO":         {"name": "Total Credit Market Debt ($B)",       "group": 1, "unit": "$B"},
    "GDP":           {"name": "Nominal GDP ($B, quarterly)",          "group": 1, "unit": "$B"},
    "GFDEGDQ188S":   {"name": "Federal Debt / GDP",                   "group": 1, "unit": "%"},
    "DPSACBW027SBOG":{"name": "Household Debt Service Ratio",         "group": 1, "unit": "$B"},
    # Group 2 — Monetary Policy Space
    "FEDFUNDS":      {"name": "Fed Funds Rate",                       "group": 2, "unit": "%"},
    "DGS2":          {"name": "2Y Treasury Yield",                    "group": 2, "unit": "%"},
    "DGS10":         {"name": "10Y Treasury Yield",                   "group": 2, "unit": "%"},
    "T10Y2Y":        {"name": "10Y-2Y Spread",                        "group": 2, "unit": "%"},
    # Group 3 — Nominal Growth vs Rates
    "CPIAUCSL":      {"name": "CPI (index, SA)",                      "group": 3, "unit": "index"},
    "GDP_YOY":       {"name": "Nominal GDP YoY Growth",               "group": 3, "unit": "%"},
    # Group 4 — Growth-Inflation Regime
    "GDPC1":         {"name": "Real GDP ($B, quarterly)",              "group": 5, "unit": "$B"},
    "RGDP_YOY":      {"name": "Real GDP YoY Growth",                  "group": 5, "unit": "%"},
    "CPI_YOY":       {"name": "CPI YoY Inflation",                    "group": 5, "unit": "%"},
    "UNRATE":        {"name": "Unemployment Rate",                     "group": 5, "unit": "%"},
    "UMCSENT":       {"name": "Consumer Sentiment (Michigan)",         "group": 5, "unit": "index"},
    "DTWEXBGS":      {"name": "USD Trade-Weighted Index",              "group": 5, "unit": "index"},
    # Early-warning
    "BAMLH0A0HYM2":  {"name": "HY Credit Spread (OAS)",               "group": 4, "unit": "%"},
    "DRCCLACBS":     {"name": "Credit Card Delinquency Rate",          "group": 4, "unit": "%"},
}


def latest_file(pattern: str) -> Path | None:
    files = sorted(glob.glob(str(DATA_DIR / pattern)))
    return Path(files[-1]) if files else None


def read_series(series_id: str) -> pd.DataFrame | None:
    path = latest_file(f"fred_{series_id.lower()}_*.csv")
    if path is None:
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index.name = "date"
    df.columns = ["value"]
    df = df.dropna()
    return df


def read_snapshot() -> pd.DataFrame | None:
    path = latest_file("fred_snapshot_*.csv")
    if path is None:
        return None
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Diagnosis logic
# ---------------------------------------------------------------------------

def compute_diagnosis(snapshot: pd.DataFrame) -> dict[str, Any]:
    """
    Apply the 快速检查清单 from 债务周期阶段判断框架.
    Returns a dict of signals and an overall stage label.
    """
    row = lambda sid: snapshot[snapshot["series_id"] == sid]["latest_value"].values
    get = lambda sid: float(row(sid)[0]) if len(row(sid)) else None

    spread   = get("T10Y2Y")
    fedfunds = get("FEDFUNDS")
    dgs10    = get("DGS10")
    gdp_yoy  = get("GDP_YOY")
    hy_oas   = get("BAMLH0A0HYM2")
    delinq   = get("DRCCLACBS")
    fed_debt_gdp = get("GFDEGDQ188S")

    signals = []

    # ① Yield curve
    if spread is not None:
        if spread < 0:
            signals.append({"id": "yield_curve", "label": "收益率曲线", "value": f"{spread:+.2f}%",
                             "status": "danger", "note": "倒挂 — 衰退信号，顶部约 12-18 个月内"})
        elif spread < 0.5:
            signals.append({"id": "yield_curve", "label": "收益率曲线", "value": f"{spread:+.2f}%",
                             "status": "warning", "note": "趋平 — 泡沫中后期特征"})
        else:
            signals.append({"id": "yield_curve", "label": "收益率曲线", "value": f"{spread:+.2f}%",
                             "status": "ok", "note": "正斜率 — 曲线健康"})

    # ② Policy rate space
    if fedfunds is not None:
        if fedfunds < 0.5:
            signals.append({"id": "rate_space", "label": "货币政策空间", "value": f"{fedfunds:.2f}%",
                             "status": "danger", "note": "利率接近 0% — 常规工具耗尽"})
        elif fedfunds < 2.0:
            signals.append({"id": "rate_space", "label": "货币政策空间", "value": f"{fedfunds:.2f}%",
                             "status": "warning", "note": "利率偏低 — 空间有限"})
        else:
            signals.append({"id": "rate_space", "label": "货币政策空间", "value": f"{fedfunds:.2f}%",
                             "status": "ok", "note": f"仍有约 {fedfunds * 100:.0f}bps 空间"})

    # ③ Nominal growth vs nominal rate
    if gdp_yoy is not None and dgs10 is not None:
        diff = gdp_yoy - dgs10
        if diff > 0:
            signals.append({"id": "growth_vs_rate", "label": "名义增速 vs 名义利率",
                             "value": f"{gdp_yoy:.1f}% vs {dgs10:.1f}%",
                             "status": "ok", "note": f"增速领先 {diff:+.1f}% — 债务负担自然减轻"})
        else:
            signals.append({"id": "growth_vs_rate", "label": "名义增速 vs 名义利率",
                             "value": f"{gdp_yoy:.1f}% vs {dgs10:.1f}%",
                             "status": "warning" if diff > -1 else "danger",
                             "note": f"利率领先 {-diff:+.1f}% — 债务负担积累"})

    # ④ HY credit spread
    if hy_oas is not None:
        if hy_oas > 8:
            signals.append({"id": "hy_spread", "label": "HY 信用利差", "value": f"{hy_oas:.2f}%",
                             "status": "danger", "note": "危机级别利差扩大"})
        elif hy_oas > 5:
            signals.append({"id": "hy_spread", "label": "HY 信用利差", "value": f"{hy_oas:.2f}%",
                             "status": "warning", "note": "利差偏高，风险情绪恶化"})
        else:
            signals.append({"id": "hy_spread", "label": "HY 信用利差", "value": f"{hy_oas:.2f}%",
                             "status": "ok", "note": "利差处于历史低位，市场情绪尚可"})

    # ⑤ Delinquency
    if delinq is not None:
        if delinq > 4.0:
            signals.append({"id": "delinquency", "label": "信用卡违约率", "value": f"{delinq:.2f}%",
                             "status": "danger", "note": "超过危机前预警水平"})
        elif delinq > 3.0:
            signals.append({"id": "delinquency", "label": "信用卡违约率", "value": f"{delinq:.2f}%",
                             "status": "warning", "note": "接近历史预警区间"})
        else:
            signals.append({"id": "delinquency", "label": "信用卡违约率", "value": f"{delinq:.2f}%",
                             "status": "ok", "note": "尚在正常范围"})

    # Overall stage
    danger_count  = sum(1 for s in signals if s["status"] == "danger")
    warning_count = sum(1 for s in signals if s["status"] == "warning")

    if danger_count >= 2:
        stage = "萧条 / 去杠杆期"
        stage_color = "danger"
    elif danger_count == 1 or warning_count >= 3:
        stage = "顶部 / 调整期"
        stage_color = "warning"
    elif warning_count >= 1:
        stage = "泡沫中后期 / 过渡"
        stage_color = "warning"
    else:
        stage = "早期健康 / 正常化"
        stage_color = "ok"

    return {"stage": stage, "stage_color": stage_color, "signals": signals}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/snapshot")
def get_snapshot():
    df = read_snapshot()
    if df is None:
        raise HTTPException(status_code=404, detail="No snapshot file found")
    records = df.to_dict(orient="records")
    # Attach metadata
    for r in records:
        meta = SERIES_META.get(r["series_id"], {})
        r.update(meta)
    return records


@app.get("/api/series/{series_id}")
def get_series(series_id: str, years: int = 20):
    df = read_series(series_id)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Series {series_id} not found")
    # Limit to requested years
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    df = df[df.index >= cutoff]
    return {
        "series_id": series_id,
        "meta": SERIES_META.get(series_id, {}),
        "data": [
            {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 4)}
            for d, v in zip(df.index, df["value"])
        ],
    }


@app.get("/api/diagnosis")
def get_diagnosis():
    df = read_snapshot()
    if df is None:
        raise HTTPException(status_code=404, detail="No snapshot file found")
    return compute_diagnosis(df)


@app.get("/api/series")
def list_series():
    return SERIES_META


# ---------------------------------------------------------------------------
# Yield Curve
# ---------------------------------------------------------------------------

YIELD_CURVE_MATURITIES = [
    ("DGS1MO", "1M",   1),
    ("DGS3MO", "3M",   3),
    ("DGS6MO", "6M",   6),
    ("DGS1",   "1Y",  12),
    ("DGS2",   "2Y",  24),
    ("DGS3",   "3Y",  36),
    ("DGS5",   "5Y",  60),
    ("DGS7",   "7Y",  84),
    ("DGS10",  "10Y", 120),
    ("DGS20",  "20Y", 240),
    ("DGS30",  "30Y", 360),
]


def _load_yield_curve_df() -> pd.DataFrame | None:
    path = latest_file("fred_yield_curve_*.csv")
    if path is None:
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index.name = "date"
    return df


@app.get("/api/yield-curve/info")
def get_yield_curve_info():
    """Return available date range and maturity labels."""
    df = _load_yield_curve_df()
    if df is None:
        raise HTTPException(status_code=404, detail="No yield curve data file found")
    valid = df.dropna(how="all")
    return {
        "min_date": valid.index.min().strftime("%Y-%m-%d"),
        "max_date": valid.index.max().strftime("%Y-%m-%d"),
        "maturities": [m for _, m, _ in YIELD_CURVE_MATURITIES],
    }


@app.get("/api/yield-curve")
def get_yield_curve(dates: str = ""):
    """
    Return yield curve snapshot(s) for requested dates.
    dates: comma-separated YYYY-MM-DD strings.
    Each date is resolved to the nearest trading day with available data.
    """
    df = _load_yield_curve_df()
    if df is None:
        raise HTTPException(status_code=404, detail="No yield curve data file found")

    if not dates.strip():
        raise HTTPException(status_code=422, detail="dates parameter is required")

    valid = df.dropna(how="all")
    results = []

    for raw in dates.split(","):
        date_str = raw.strip()
        if not date_str:
            continue
        try:
            target = pd.Timestamp(date_str)
        except Exception:
            continue

        # Nearest trading day
        idx = valid.index.get_indexer([target], method="nearest")[0]
        row = valid.iloc[idx]
        actual_date = valid.index[idx].strftime("%Y-%m-%d")

        points = []
        for series_id, maturity, months in YIELD_CURVE_MATURITIES:
            val = row.get(series_id, None)
            if val is not None and pd.notna(val):
                points.append({"maturity": maturity, "months": months, "value": round(float(val), 4)})

        results.append({
            "requested_date": date_str,
            "actual_date": actual_date,
            "points": points,
        })

    return results


# ---------------------------------------------------------------------------
# Regime & History Routes
# ---------------------------------------------------------------------------

@app.get("/api/regime")
def get_regime():
    """Return current growth-inflation regime, asset tilts, and long-term risk."""
    from .regime import compute_regime

    df = read_snapshot()
    if df is None:
        raise HTTPException(status_code=404, detail="No snapshot file found")
    return compute_regime(df)


@app.get("/api/diagnosis/history")
def get_diagnosis_history(limit: int = 365):
    """Return historical diagnosis records (most recent first)."""
    from .regime import read_history

    return read_history(limit=limit)


@app.post("/api/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a data refresh (runs in background)."""
    from .scheduler import run_fetch_and_log

    background_tasks.add_task(run_fetch_and_log)
    return {"status": "refresh_started", "message": "数据刷新已启动，请稍后刷新页面"}
