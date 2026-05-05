import json
import os
from datetime import date

SIGNAL_SERIES = [
    "T10Y2Y", "DGS2", "DGS10",
    "CPIAUCSL",
    "UNRATE",
    "UMCSENT",
    "GDPC1", "FEDFUNDS",
    "TCMDO", "GFDEGDQ188S", "DTWEXBGS",
]

STAGES = [
    {"id": 3, "name": "顶部", "name_en": "Top"},
    {"id": 2, "name": "泡沫期", "name_en": "Bubble"},
    {"id": 5, "name": "美丽去杠杆", "name_en": "Beautiful Deleveraging"},
    {"id": 1, "name": "早期", "name_en": "Early"},
    {"id": 6, "name": "推绳子", "name_en": "Pushing on a String"},
    {"id": 7, "name": "正常化", "name_en": "Normalization"},
    {"id": 4, "name": "萧条", "name_en": "Depression"},
]


def _latest(conn, series_id):
    row = conn.execute(
        "SELECT value FROM series WHERE series_id=? ORDER BY date DESC LIMIT 1",
        (series_id,),
    ).fetchone()
    return row["value"] if row else None


def _latest_date(conn, series_id):
    row = conn.execute(
        "SELECT date FROM series WHERE series_id=? ORDER BY date DESC LIMIT 1",
        (series_id,),
    ).fetchone()
    return row[0] if row else None


def _compute_cpi_yoy(conn):
    latest = _latest_date(conn, "CPIAUCSL")
    if not latest:
        return None
    current_val = _latest(conn, "CPIAUCSL")
    y = latest[:4]
    m = latest[5:7]
    prev = f"{int(y) - 1}-{m}-01"
    row = conn.execute(
        "SELECT value FROM series WHERE series_id='CPIAUCSL' AND date <= ? ORDER BY date DESC LIMIT 1",
        (prev,),
    ).fetchone()
    if row and row["value"]:
        return round((current_val - row["value"]) / row["value"] * 100, 2)
    return None


def read_signals(conn):
    signals = {}
    for series_id in SIGNAL_SERIES:
        val = _latest(conn, series_id)
        if val is not None:
            signals[series_id] = val

    cpi_yoy = _compute_cpi_yoy(conn)
    if cpi_yoy is not None:
        signals["CPI_YOY"] = cpi_yoy

    return signals


def _check_stage_3(signals):
    t = signals.get("T10Y2Y")
    if t is None or t >= 0:
        return False
    cpi = signals.get("CPI_YOY", 0)
    return cpi > 3 or signals.get("UNRATE", 0) > 4


def _check_stage_2(signals):
    t = signals.get("T10Y2Y")
    if t is None or t < 0 or t > 0.5:
        return False
    r = signals.get("FEDFUNDS", 0)
    cpi = signals.get("CPI_YOY", 0)
    sent = signals.get("UMCSENT", 0)
    return r > 3 and cpi > 3 and sent > 80


def _check_stage_5(signals):
    r = signals.get("FEDFUNDS")
    if r is None or r >= 0.5:
        return False
    t = signals.get("T10Y2Y", 0)
    return t < 0.5


def _check_stage_1(signals):
    r = signals.get("FEDFUNDS")
    if r is None or r >= 2.5:
        return False
    t = signals.get("T10Y2Y", 0)
    cpi = signals.get("CPI_YOY", 0)
    u = signals.get("UNRATE", 0)
    return t > 1.0 and cpi < 3 and u > 4


def _check_stage_6(signals):
    r = signals.get("FEDFUNDS")
    if r is None or r >= 1.5:
        return False
    t = signals.get("T10Y2Y", 0)
    return t > 0.5


def _check_stage_7(signals):
    t = signals.get("T10Y2Y", 0)
    cpi = signals.get("CPI_YOY", 0)
    u = signals.get("UNRATE", 0)
    return t > 1.0 and cpi > 1.5 and 3.5 < u < 5.5


def _check_stage_4(signals):
    t = signals.get("T10Y2Y")
    if t is None or t >= 1.0:
        return False
    sent = signals.get("UMCSENT", 100)
    return sent < 60


_RULE_CHECKS = [
    (3, _check_stage_3),
    (2, _check_stage_2),
    (5, _check_stage_5),
    (1, _check_stage_1),
    (6, _check_stage_6),
    (7, _check_stage_7),
    (4, _check_stage_4),
]


RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")


def load_rules(path=None):
    path = path or RULES_PATH
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def classify_stage(signals):
    for stage_id, check in _RULE_CHECKS:
        if check(signals):
            return next(s for s in STAGES if s["id"] == stage_id)
    return {"id": 0, "name": "未明确", "name_en": "Unclear"}


def _compute_confidence(signals, stage_id):
    n_signals = sum(1 for s in ("T10Y2Y", "FEDFUNDS", "CPI_YOY", "UNRATE", "UMCSENT") if s in signals)
    if stage_id == 0:
        return "low"
    if n_signals >= 4:
        return "high"
    if n_signals >= 2:
        return "medium"
    return "low"


def diagnose(conn):
    signals = read_signals(conn)
    stage = classify_stage(signals)
    today = date.today().isoformat()

    signal_list = [
        {"id": k, "value": v, "status": "ok"}
        for k, v in signals.items()
    ]

    return {
        "date": today,
        "stage": stage,
        "signals": signal_list,
        "confidence": _compute_confidence(signals, stage["id"]),
    }
