"""
Macro Regime Engine
===================
Multi-layer macro environment diagnosis + asset allocation mapping.

Layers:
  1. Short-term debt cycle (reuses compute_diagnosis from main.py)
  2. Growth-Inflation regime (4-quadrant model)
  3. Long-term structural risk (debt level + USD trend)

References:
  - wiki/analyses/债务周期阶段判断框架.md
  - wiki/concepts/世界秩序大周期-big-cycle-of-world-order.md
  - wiki/concepts/储备货币周期-reserve-currency-cycle.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

GROWTH_THRESHOLD = 2.0   # Real GDP YoY %: above = high growth
INFLATION_THRESHOLD = 3.0  # CPI YoY %: above = high inflation

DEBT_GDP_WARNING = 300   # Total debt/GDP % warning line
DEBT_GDP_DANGER = 350    # Total debt/GDP % danger line

# ---------------------------------------------------------------------------
# Growth-Inflation 4-Quadrant Model
# ---------------------------------------------------------------------------

REGIME_LABELS = {
    ("high", "low"):  "Goldilocks",
    ("high", "high"): "Overheating",
    ("low",  "high"): "Stagflation",
    ("low",  "low"):  "Deflation",
}

REGIME_LABELS_CN = {
    "Goldilocks":  "金发姑娘（高增长低通胀）",
    "Overheating": "过热（高增长高通胀）",
    "Stagflation": "滞胀（低增长高通胀）",
    "Deflation":   "通缩/衰退（低增长低通胀）",
}

# Asset tilt per regime: scale from -2 to +2
ASSET_TILTS = {
    "Goldilocks":  {"stocks": 2, "long_bonds": 1,  "commodities_gold": -1, "cash": -1},
    "Overheating": {"stocks": 1, "long_bonds": -2, "commodities_gold": 2,  "cash": -1},
    "Stagflation": {"stocks": -2, "long_bonds": -1, "commodities_gold": 1, "cash": 2},
    "Deflation":   {"stocks": -1, "long_bonds": 2,  "commodities_gold": -2, "cash": 1},
}

ASSET_NAMES_CN = {
    "stocks": "股票",
    "long_bonds": "长期国债",
    "commodities_gold": "商品/黄金",
    "cash": "现金",
}


def _get_snapshot_value(snapshot: pd.DataFrame, series_id: str) -> float | None:
    rows = snapshot[snapshot["series_id"] == series_id]["latest_value"].values
    return float(rows[0]) if len(rows) else None


def compute_regime(snapshot: pd.DataFrame) -> dict[str, Any]:
    """
    Compute the full multi-layer macro regime diagnosis.
    """
    get = lambda sid: _get_snapshot_value(snapshot, sid)

    rgdp_yoy = get("RGDP_YOY")
    cpi_yoy = get("CPI_YOY")
    unrate = get("UNRATE")
    umcsent = get("UMCSENT")
    dtwexbgs = get("DTWEXBGS")
    tcmdo = get("TCMDO")
    gdp = get("GDP")
    fed_debt_gdp = get("GFDEGDQ188S")

    # --- Layer 2: Growth-Inflation Regime ---
    regime_quadrant = None
    growth_level = None
    inflation_level = None

    if rgdp_yoy is not None:
        growth_level = "high" if rgdp_yoy > GROWTH_THRESHOLD else "low"
    if cpi_yoy is not None:
        inflation_level = "high" if cpi_yoy > INFLATION_THRESHOLD else "low"

    if growth_level and inflation_level:
        regime_quadrant = REGIME_LABELS[(growth_level, inflation_level)]

    regime = {
        "quadrant": regime_quadrant,
        "quadrant_cn": REGIME_LABELS_CN.get(regime_quadrant, "数据不足"),
        "growth": {
            "value": round(rgdp_yoy, 2) if rgdp_yoy is not None else None,
            "level": growth_level,
            "threshold": GROWTH_THRESHOLD,
            "label": "实际GDP同比",
        },
        "inflation": {
            "value": round(cpi_yoy, 2) if cpi_yoy is not None else None,
            "level": inflation_level,
            "threshold": INFLATION_THRESHOLD,
            "label": "CPI同比",
        },
    }

    # Auxiliary signals
    aux_signals = []
    if unrate is not None:
        status = "ok" if unrate < 4.0 else ("warning" if unrate < 6.0 else "danger")
        aux_signals.append({
            "id": "unemployment", "label": "失业率",
            "value": f"{unrate:.1f}%", "status": status,
        })
    if umcsent is not None:
        status = "ok" if umcsent > 80 else ("warning" if umcsent > 60 else "danger")
        aux_signals.append({
            "id": "consumer_sentiment", "label": "消费者信心",
            "value": f"{umcsent:.1f}", "status": status,
        })
    if dtwexbgs is not None:
        aux_signals.append({
            "id": "usd_index", "label": "美元指数",
            "value": f"{dtwexbgs:.1f}", "status": "neutral",
        })

    regime["aux_signals"] = aux_signals

    # Asset tilts
    asset_tilts = None
    if regime_quadrant:
        raw_tilts = ASSET_TILTS[regime_quadrant]
        asset_tilts = [
            {"asset": k, "asset_cn": ASSET_NAMES_CN[k], "tilt": v}
            for k, v in raw_tilts.items()
        ]
    regime["asset_tilts"] = asset_tilts

    # --- Layer 3: Long-term Structural Risk ---
    total_debt_gdp = None
    if tcmdo is not None and gdp is not None and gdp > 0:
        # TCMDO is in $M, GDP is in $B quarterly SAAR
        total_debt_gdp = round((tcmdo / 1000) / gdp * 100, 1)

    long_term = {}
    if total_debt_gdp is not None:
        if total_debt_gdp > DEBT_GDP_DANGER:
            lt_status = "danger"
            lt_note = f"总债务/GDP {total_debt_gdp}% — 超过历史泡沫顶部均值"
        elif total_debt_gdp > DEBT_GDP_WARNING:
            lt_status = "warning"
            lt_note = f"总债务/GDP {total_debt_gdp}% — 接近历史警戒线"
        else:
            lt_status = "ok"
            lt_note = f"总债务/GDP {total_debt_gdp}% — 历史正常区间"
        long_term["debt_gdp"] = {
            "value": total_debt_gdp, "status": lt_status, "note": lt_note,
        }

    if fed_debt_gdp is not None:
        if fed_debt_gdp > 100:
            lt_status = "warning" if fed_debt_gdp < 130 else "danger"
        else:
            lt_status = "ok"
        long_term["fed_debt_gdp"] = {
            "value": round(fed_debt_gdp, 1), "status": lt_status,
            "note": f"联邦政府债务/GDP {fed_debt_gdp:.1f}%",
        }

    if dtwexbgs is not None:
        long_term["usd_trend"] = {
            "value": round(dtwexbgs, 1),
            "note": "美元贸易加权指数 — 关注长期趋势方向",
        }

    regime["long_term"] = long_term

    return regime


# ---------------------------------------------------------------------------
# History logging
# ---------------------------------------------------------------------------

HISTORY_FILE = Path(__file__).parent.parent.parent / "data" / "diagnosis_history.jsonl"


def append_history(diagnosis: dict, regime: dict) -> None:
    """Append a combined diagnosis+regime record to the JSONL history file."""
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "debt_cycle_stage": diagnosis.get("stage"),
        "regime_quadrant": regime.get("quadrant"),
        "regime_quadrant_cn": regime.get("quadrant_cn"),
        "growth_value": regime.get("growth", {}).get("value"),
        "inflation_value": regime.get("inflation", {}).get("value"),
        "asset_tilts": regime.get("asset_tilts"),
        "long_term_risk": regime.get("long_term"),
        "signals": diagnosis.get("signals"),
    }
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_history(limit: int = 365) -> list[dict]:
    """Read diagnosis history, most recent first."""
    if not HISTORY_FILE.exists():
        return []
    records = []
    with open(HISTORY_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    # Deduplicate by date (keep latest per day)
    seen = {}
    for r in records:
        seen[r["date"]] = r
    result = sorted(seen.values(), key=lambda x: x["date"], reverse=True)
    return result[:limit]
