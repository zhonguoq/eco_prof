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
# Data paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent.parent / "data"


# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

GROWTH_THRESHOLD = 2.0   # Real GDP YoY %: above = high growth
INFLATION_THRESHOLD = 3.0  # CPI YoY %: above = high inflation

DEBT_GDP_WARNING = 300   # Total debt/GDP % warning line
DEBT_GDP_DANGER = 350    # Total debt/GDP % danger line

# B4 — Yield curve shape thresholds
YC_SHAPE_THRESHOLDS = {
    "inversion_max": 0.0,          # spread <= 0 = inverted
    "flattening_max": 0.5,         # spread <= 0.5, trend negative = flattening
    "short_end_low": 0.5,          # DGS2 < 0.5% = ultra-flat (QE regime)
}

# A6 — Rate phase thresholds
RATE_PHASE_THRESHOLDS = {
    "high_rate": 3.0,              # FEDFUNDS > 3% = high
    "low_rate": 0.5,               # FEDFUNDS < 0.5% = near zero
    "trend_window_days": 63,       # ~3 months for trend calculation
    "trend_threshold": 0.25,       # > 0.25% change = meaningful trend
}

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


# ---------------------------------------------------------------------------
# B4 — Yield Curve Shape Classification (6-phase classifier)
# ---------------------------------------------------------------------------

YC_SHAPES = {
    "normal":       {"cn": "正常正斜率",  "phase": "早期健康 / 正常化"},
    "flattening":   {"cn": "趋平",        "phase": "泡沫中后期"},
    "inverted":     {"cn": "倒挂",        "phase": "顶部 / 收缩期"},
    "bull_steep":   {"cn": "牛陡",        "phase": "衰退 / 萧条开始"},
    "ultra_flat":   {"cn": "超平近零",    "phase": "去杠杆 / QE"},
    "recovery":     {"cn": "恢复正斜率",  "phase": "正常化"},
}


def _read_latest_series_df(data_dir: Path, series_id: str) -> pd.DataFrame | None:
    """Read the most recent CSV file for a FRED series."""
    import glob
    pattern = str(data_dir / f"fred_{series_id.lower()}_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    df = pd.read_csv(files[-1], index_col=0, parse_dates=True)
    df.columns = ["value"]
    return df.dropna()


def _get_trend(series: pd.DataFrame, window: int = 63) -> float | None:
    """Compute approximate trend over the trailing window (in units/second)."""
    recent = series.dropna().iloc[-window:] if len(series) > window else series.dropna()
    if len(recent) < 2:
        return None
    return float(recent["value"].iloc[-1] - recent["value"].iloc[0])


# P001/B4 — Yield Curve Shape Classification
def classify_yield_curve_shape(
    spread: float | None,
    dgs2: float | None,
) -> dict[str, Any] | None:
    """
    Classify yield curve into 6 shapes based on spread level + short-end trend.

    Returns: {id, label, shape_cn, phase, note} or None if data insufficient.
    """
    if spread is None:
        return None

    # Default classification
    result = {
        "id": "yield_curve_shape",
        "label": "收益率曲线形态",
        "spread": f"{spread:+.2f}%",
    }

    # Spread-only classification (when trend data unavailable)
    if spread <= YC_SHAPE_THRESHOLDS["inversion_max"]:
        if dgs2 is not None and dgs2 < YC_SHAPE_THRESHOLDS["short_end_low"]:
            result.update(YC_SHAPES["ultra_flat"])
            result["note"] = "短端近零 + 曲线倒挂 — QE 压制下的去杠杆阶段"
        else:
            result.update(YC_SHAPES["inverted"])
            result["note"] = f"曲线倒挂（{spread:+.2f}%）— 衰退预警，领先约 12-18 个月"
    elif spread <= YC_SHAPE_THRESHOLDS["flattening_max"]:
        result.update(YC_SHAPES["flattening"])
        result["note"] = f"曲线趋平（{spread:+.2f}%）— 泡沫中后期特征"
    elif dgs2 is not None and dgs2 < YC_SHAPE_THRESHOLDS["short_end_low"]:
        result.update(YC_SHAPES["ultra_flat"])
        result["note"] = "短端近零 — 货币政策极度宽松，收益率曲线受 QE 压制"
    else:
        result.update(YC_SHAPES["normal"])
        result["note"] = f"曲线正常正斜率（{spread:+.2f}%）— 经济扩张/正常化"

    # Try to refine with trend data
    try:
        t10y2y_series = _read_latest_series_df(DATA_DIR, "T10Y2Y")
        dgs2_series = _read_latest_series_df(DATA_DIR, "DGS2")
        if t10y2y_series is not None:
            spread_trend = _get_trend(t10y2y_series, RATE_PHASE_THRESHOLDS["trend_window_days"])
            if spread_trend is not None:
                # Refine classification with trend info
                if spread > 0 and spread_trend < -RATE_PHASE_THRESHOLDS["trend_threshold"]:
                    # Curve positive but narrowing = flattening
                    if spread <= YC_SHAPE_THRESHOLDS["flattening_max"]:
                        result.update(YC_SHAPES["flattening"])
                        result["note"] = f"曲线趋平（{spread:+.2f}%，趋势 {spread_trend:+.2f}%）— 泡沫中后期"
                    else:
                        result["note"] += f" 但趋势趋平（{spread_trend:+.2f}%），关注倒挂风险"
                elif spread <= 0 and dgs2_series is not None:
                    dgs2_trend = _get_trend(dgs2_series, RATE_PHASE_THRESHOLDS["trend_window_days"])
                    if dgs2_trend is not None and dgs2_trend < -RATE_PHASE_THRESHOLDS["trend_threshold"]:
                        # Short end collapsing while still inverted
                        result.update(YC_SHAPES["bull_steep"])
                        result["note"] = f"牛陡 — 短端快速下行（{dgs2_trend:+.2f}%），衰退/萧条确认"
                    elif spread_trend > RATE_PHASE_THRESHOLDS["trend_threshold"]:
                        # Inversion narrowing
                        result["note"] += "，倒挂深度在收窄"
    except (IndexError, FileNotFoundError, OSError):
        pass  # Fall back to spread-only classification

    return result


# ---------------------------------------------------------------------------
# A6 — Rate Phase Classification (level + direction)
# ---------------------------------------------------------------------------


def classify_rate_phase(fedfunds: float | None) -> dict[str, Any] | None:
    """
    Classify monetary policy phase based on fed funds rate level + trend.

    Returns: {id, label, phase, phase_cn, note} or None if data insufficient.
    """
    if fedfunds is None:
        return None

    result = {
        "id": "rate_phase",
        "label": "利率阶段",
        "value": f"{fedfunds:.2f}%",
    }

    # Level-based with trend refinement
    if fedfunds < RATE_PHASE_THRESHOLDS["low_rate"]:
        result["phase"] = "depression_deleveraging"
        result["phase_cn"] = "萧条/去杠杆期"
        result["note"] = f"利率近零（{fedfunds:.2f}%）— 常规工具耗尽，靠非常规货币政策"
        result["status"] = "danger"
    elif fedfunds < RATE_PHASE_THRESHOLDS["high_rate"]:
        # Low to moderate — try to infer trend
        try:
            fed_series = _read_latest_series_df(DATA_DIR, "FEDFUNDS")
            if fed_series is not None:
                trend = _get_trend(fed_series, RATE_PHASE_THRESHOLDS["trend_window_days"])
            else:
                trend = None
        except (IndexError, FileNotFoundError, OSError):
            trend = None

        if trend is not None:
            if fedfunds < 1.0 and trend > RATE_PHASE_THRESHOLDS["trend_threshold"]:
                result["phase"] = "early_normalization"
                result["phase_cn"] = "早期正常化"
                result["note"] = f"利率从低位缓慢回升（{fedfunds:.2f}% → 趋势 {trend:+.2f}%）— 正常化初期"
                result["status"] = "ok"
            elif trend > RATE_PHASE_THRESHOLDS["trend_threshold"]:
                result["phase"] = "tightening"
                result["phase_cn"] = "收紧阶段"
                result["note"] = f"利率中等且上升（{fedfunds:.2f}%，趋势 {trend:+.2f}%）— 收紧中"
                result["status"] = "warning" if fedfunds > 2.0 else "ok"
            elif trend < -RATE_PHASE_THRESHOLDS["trend_threshold"]:
                result["phase"] = "easing"
                result["phase_cn"] = "放松阶段"
                result["note"] = f"利率中等且下降（{fedfunds:.2f}%，趋势 {trend:+.2f}%）— 宽松中"
                result["status"] = "warning"
            else:
                result["phase"] = "neutral"
                result["phase_cn"] = "中性阶段"
                result["note"] = f"利率中等且稳定（{fedfunds:.2f}%）— 观察期"
                result["status"] = "ok"
        else:
            result["phase"] = "moderate"
            result["phase_cn"] = "中等利率"
            result["note"] = f"利率中等（{fedfunds:.2f}%）— 有一定政策空间"
            result["status"] = "ok"
    else:
        # High rate — try trend
        try:
            fed_series = _read_latest_series_df(DATA_DIR, "FEDFUNDS")
            if fed_series is not None:
                trend = _get_trend(fed_series, RATE_PHASE_THRESHOLDS["trend_window_days"])
            else:
                trend = None
        except (IndexError, FileNotFoundError, OSError):
            trend = None

        if trend is not None and trend < -RATE_PHASE_THRESHOLDS["trend_threshold"]:
            result["phase"] = "peak_reversal"
            result["phase_cn"] = "顶部反转"
            result["note"] = f"利率触顶快速回落（{fedfunds:.2f}%，趋势 {trend:+.2f}%）— 衰退确认，政策急转弯"
            result["status"] = "danger"
        else:
            result["phase"] = "high_plateau"
            result["phase_cn"] = "高位僵持"
            result["note"] = f"利率高位（{fedfunds:.2f}%）— 压制通胀，但经济可能承压"
            result["status"] = "warning"

    return result


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
    t10y2y = get("T10Y2Y")
    dgs2 = get("DGS2")
    fedfunds = get("FEDFUNDS")

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

    # P005 — Asset-Inflation Divergence (SP500 YoY - CPI YoY)
    divergence = get("ASSET_INFLATION_DIVERGENCE")
    if divergence is not None:
        if divergence > 20:
            div_status = "danger"
            div_note = f"资产通胀远超商品通胀（+{divergence:.0f}%）— 典型泡沫特征，警惕均值回归"
        elif divergence > 10:
            div_status = "warning"
            div_note = f"资产通胀显著高于商品通胀（+{divergence:.0f}%）— 关注资金流向和杠杆积累"
        elif divergence < -10:
            div_status = "warning"
            div_note = f"资产价格跑输通胀（{divergence:.0f}%）— 可能反映了经济悲观预期"
        else:
            div_status = "ok"
            div_note = f"资产通胀与商品通胀基本同步（{divergence:+.0f}%）"
        aux_signals.append({
            "id": "asset_inflation_divergence", "label": "资产通胀背离",
            "value": f"{divergence:+.1f}%", "status": div_status, "note": div_note,
        })

    # B4 — Yield Curve Shape Classification
    yc = classify_yield_curve_shape(t10y2y, dgs2)
    if yc:
        aux_signals.append({
            "id": "yield_curve_shape", "label": "收益率曲线形态",
            "value": yc.get("spread", ""), "status": yc.get("phase", ""),
            "shape": yc.get("cn", ""), "note": yc.get("note", ""),
        })

    # A6 — Rate Phase Classification
    rp = classify_rate_phase(fedfunds)
    if rp:
        aux_signals.append({
            "id": "rate_phase", "label": "利率阶段",
            "value": rp.get("value", ""), "status": rp.get("status", "ok"),
            "phase": rp.get("phase_cn", ""), "note": rp.get("note", ""),
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
