#!/usr/bin/env python3
"""
run_alerts.py
=============
Principle-driven alert engine.  Checks hard signals (data thresholds) and
soft signals (news keywords) against the rules defined in
.claude/skills/news-alert/SKILL.md.

Usage:
    python3 lab/tools/run_alerts.py [--date YYYY-MM-DD]
                                    [--news lab/news/YYYY-MM-DD.jsonl]

Output (stdout): JSON with triggered alerts.
Logs to stderr.
Exit code 0 = success, 1 = error.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "lab" / "data"
NEWS_DIR = ROOT / "lab" / "news"
ALERTS_FILE = DATA_DIR / "alerts.jsonl"

# ---------------------------------------------------------------------------
# Alert rule definitions  (mirrors news-alert/SKILL.md)
# ---------------------------------------------------------------------------

HARD_SIGNAL_RULES: list[dict[str, Any]] = [
    {
        "alert_id": "ALERT-YC",
        "severity": "P1",
        "principle_ids": ["P001", "P006"],
        "title": "收益率曲线正式倒挂",
        "condition": "t10y2y < 0",
        "sustained_days": 5,
        "suggested_action": "生成专题简报：收益率曲线倒挂分析",
    },
    {
        "alert_id": "ALERT-YC2",
        "severity": "P2",
        "principle_ids": ["P001"],
        "title": "收益率曲线从倒挂恢复正斜率",
        "condition": "t10y2y_recovery",
        "suggested_action": "关注衰退倒计时——最后绿灯信号",
    },
    {
        "alert_id": "ALERT-DEBT",
        "severity": "P1",
        "principle_ids": ["P003"],
        "title": "总债务/GDP 超过 350% 警戒线",
        "condition": "debt_gdp > 350",
        "suggested_action": "生成专题简报：债务风险分析",
    },
    {
        "alert_id": "ALERT-DEBT2",
        "severity": "P2",
        "principle_ids": ["P003"],
        "title": "总债务/GDP 进入警戒区（> 300%）",
        "condition": "debt_gdp > 300",
        "suggested_action": "在简报中标注债务风险",
    },
    {
        "alert_id": "ALERT-STAG",
        "severity": "P2",
        "principle_ids": ["P004"],
        "title": "Regime 进入 Stagflation",
        "condition": "regime == Stagflation",
        "suggested_action": "维持现金+商品/黄金配置，减少股票/长债敞口",
    },
    {
        "alert_id": "ALERT-REGIME-SHIFT",
        "severity": "P2",
        "principle_ids": ["P004"],
        "title": "Regime 象限切换",
        "condition": "regime_shift",
        "suggested_action": "审查资产配置是否需要调整",
    },
    {
        "alert_id": "ALERT-DIVERGE",
        "severity": "P1",
        "principle_ids": ["P005"],
        "title": "资产通胀背离超过 +15%",
        "condition": "divergence > 15",
        "suggested_action": "生成专题简报：泡沫风险评估",
    },
    {
        "alert_id": "ALERT-DIVERGE2",
        "severity": "P2",
        "principle_ids": ["P005"],
        "title": "资产通胀背离超过 +10%",
        "condition": "divergence > 10",
        "suggested_action": "关注泡沫风险",
    },
    {
        "alert_id": "ALERT-SENTIMENT",
        "severity": "P2",
        "principle_ids": [],
        "title": "消费者信心极低",
        "condition": "umcsent < 60",
        "suggested_action": "关注消费支出数据",
    },
    {
        "alert_id": "ALERT-SPREAD",
        "severity": "P1",
        "principle_ids": ["C2"],
        "title": "HY 信用利差超过 5%",
        "condition": "hy_spread > 5",
        "suggested_action": "信用市场恐慌——生成专题简报",
    },
    {
        "alert_id": "ALERT-SPREAD2",
        "severity": "P1",
        "principle_ids": ["C2"],
        "title": "HY 信用利差超过 8% — 危机级别",
        "condition": "hy_spread > 8",
        "suggested_action": "危机级别利差——全面风险排查",
    },
    {
        "alert_id": "ALERT-RATE0",
        "severity": "P2",
        "principle_ids": ["A6", "P007"],
        "title": "利率近零 — 货币政策空间耗尽",
        "condition": "fedfunds < 0.5",
        "suggested_action": "关注非常规货币政策",
    },
]

SOFT_SIGNAL_RULES: list[dict[str, Any]] = [
    {
        "alert_id": "ALERT-WAR",
        "severity": "P1",
        "principle_ids": [],
        "title": "地缘冲突推升不确定性",
        "keywords": ["战争", "军事冲突", "制裁", "核", "war", "sanctions", "military",
                     "missile", "strike", "冲突", "伊朗", "ukraine", "russia"],
        "suggested_action": "生成专题简报：地缘风险分析",
    },
    {
        "alert_id": "ALERT-FED",
        "severity": "P1",
        "principle_ids": ["P007", "P001"],
        "title": "央行非常规行动",
        "keywords": ["emergency", "紧急", "surprise", "意外", "加息", "降息",
                     "美联储", "federal reserve", "ECB", "央行"],
        "suggested_action": "生成专题简报：央行政策分析",
    },
    {
        "alert_id": "ALERT-BANK",
        "severity": "P1",
        "principle_ids": ["B5"],
        "title": "银行危机 / 信贷紧缩",
        "keywords": ["银行危机", "信贷紧缩", "挤兑", "bank run", "banking crisis",
                     "credit crunch", "silicon valley", "credit suisse"],
        "suggested_action": "生成专题简报：金融系统风险评估",
    },
    {
        "alert_id": "ALERT-CPI",
        "severity": "P2",
        "principle_ids": ["P004", "P005"],
        "title": "通胀 / 通缩信号",
        "keywords": ["CPI", "通胀", "通缩", "inflation", "deflation", "物价",
                     "能源", "oil", "原油", "higher for longer", "供给冲击"],
        "suggested_action": "关注通胀数据对 regime 的影响",
    },
    {
        "alert_id": "ALERT-DEFAULT",
        "severity": "P2",
        "principle_ids": ["C1", "C2"],
        "title": "信用事件",
        "keywords": ["违约", "default", "降级", "downgrade", "破产", "bankruptcy",
                     "债务危机", "debt crisis"],
        "suggested_action": "关注信用市场传染风险",
    },
    {
        "alert_id": "ALERT-RESERVE",
        "severity": "P2",
        "principle_ids": ["P003"],
        "title": "储备货币地位信号",
        "keywords": ["去美元化", "de-dollarization", "储备货币", "reserve currency",
                     "BRICS", "petrodollar", "石油美元"],
        "suggested_action": "关注美元储备货币地位变化",
    },
    {
        "alert_id": "ALERT-SHADOW",
        "severity": "P2",
        "principle_ids": ["C4"],
        "title": "金融创新 / 监管套利",
        "keywords": ["影子银行", "shadow banking", "crypto", "加密货币", "杠杆",
                     "leverage", "监管套利"],
        "suggested_action": "关注监管套利风险",
    },
]

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _read_series(series_id: str) -> pd.Series | None:
    """Read latest CSV for a raw FRED series (excludes derived)."""
    pattern = str(DATA_DIR / f"fred_{series_id.lower()}_*.csv")
    all_files = sorted(glob.glob(pattern))
    exact_files = [
        f for f in all_files
        if re.match(rf"fred_{series_id.lower()}_\d{{8}}\.csv$", Path(f).name)
    ]
    if not exact_files:
        return None
    df = pd.read_csv(exact_files[-1], index_col=0, parse_dates=True)
    df.columns = ["value"]
    return df["value"].dropna()


def _read_snapshot() -> dict[str, Any]:
    """Read the latest snapshot CSV and return a dict of series_id -> latest_value."""
    snapshots = sorted(glob.glob(str(DATA_DIR / "fred_snapshot_*.csv")))
    if not snapshots:
        return {}
    df = pd.read_csv(snapshots[-1])
    result: dict[str, Any] = {}
    for _, row in df.iterrows():
        sid = str(row["series_id"]).strip()
        try:
            result[sid] = float(row["latest_value"])
        except (ValueError, TypeError):
            result[sid] = row["latest_value"]
    return result


def _read_diagnosis_history() -> list[dict[str, Any]]:
    """Read diagnosis history and return entries sorted by date descending."""
    if not ALERTS_FILE.parent.exists():
        return []
    # Read from diagnosis_history.jsonl
    diag_file = DATA_DIR / "diagnosis_history.jsonl"
    if not diag_file.exists():
        return []
    entries = []
    with open(diag_file) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    return entries


def _check_sustained_inversion(days: int = 5) -> bool:
    """Check if T10Y2Y has been negative for N consecutive trading days."""
    t10y2y = _read_series("t10y2y")
    if t10y2y is None or len(t10y2y) < days:
        return False
    recent = t10y2y.tail(days)
    return bool((recent < 0).all())


def _check_recovery_from_inversion() -> bool:
    """Check if T10Y2Y has recently turned positive after being negative."""
    t10y2y = _read_series("t10y2y")
    if t10y2y is None or len(t10y2y) < 30:
        return False
    recent_30 = t10y2y.tail(30)
    # Was negative at some point in the last 30 days
    was_negative = (recent_30.iloc[:-5] < 0).any() if len(recent_30) > 5 else False
    # Is positive now
    is_positive = bool(t10y2y.iloc[-1] > 0)
    return was_negative and is_positive


# ---------------------------------------------------------------------------
# Hard signal checker
# ---------------------------------------------------------------------------


def _check_hard_signals(
    snapshot: dict[str, Any],
    diagnosis_entries: list[dict[str, Any]],
    check_date: str,
) -> list[dict[str, Any]]:
    triggered: list[dict[str, Any]] = []

    # Convenience values
    t10y2y = snapshot.get("T10Y2Y")
    debt_gdp = snapshot.get("TCMDO")
    gdp = snapshot.get("GDP")
    umcsent = snapshot.get("UMCSENT")
    hy_spread = snapshot.get("BAMLH0A0HYM2")
    fedfunds = snapshot.get("FEDFUNDS")
    divergence = snapshot.get("ASSET_INFLATION_DIVERGENCE")

    # Compute debt/GDP ratio if raw values available
    debt_gdp_ratio = None
    if debt_gdp is not None and gdp is not None and gdp != 0:
        # TCMDO is in $M, GDP is in $B
        if debt_gdp > 1e8:  # TCMDO is in raw dollars, need to convert
            # FRED returns raw values: TCMDO ~107,632,484 ($M), GDP ~31,422 ($B)
            # So debt_gdp / 1e6 for $T, gdp for $B... actually let's check
            # 107632484 $M = 107.6 $T, 31422 $B = 31.4 $T
            debt_gdp_ratio = (debt_gdp / 1000.0) / gdp * 100
        else:
            debt_gdp_ratio = debt_gdp / gdp * 100

    # 1. ALERT-YC: T10Y2Y < 0 sustained
    if t10y2y is not None and t10y2y < 0:
        if _check_sustained_inversion(5):
            triggered.append({
                "alert_id": "ALERT-YC",
                "severity": "P1",
                "principle_ids": ["P001", "P006"],
                "title": "收益率曲线正式倒挂（持续 > 5 个交易日）",
                "current_value": f"T10Y2Y = {t10y2y:.2f}%",
                "triggered_at": check_date,
                "note": "收益率曲线持续倒挂，衰退领先信号已触发",
                "suggested_action": "生成专题简报：收益率曲线倒挂分析",
            })
        else:
            # Single-day inversion, just P3
            triggered.append({
                "alert_id": "ALERT-YC",
                "severity": "P3",
                "principle_ids": ["P001", "P006"],
                "title": "收益率曲线单日倒挂",
                "current_value": f"T10Y2Y = {t10y2y:.2f}%",
                "triggered_at": check_date,
                "note": "单日倒挂，需观察是否持续",
                "suggested_action": "关注后续交易日是否持续倒挂",
            })

    # 2. ALERT-YC2: Recovery from inversion
    if t10y2y is not None and t10y2y > 0 and _check_recovery_from_inversion():
        triggered.append({
            "alert_id": "ALERT-YC2",
            "severity": "P2",
            "principle_ids": ["P001"],
            "title": "收益率曲线从倒挂恢复正斜率",
            "current_value": f"T10Y2Y = {t10y2y:.2f}%",
            "triggered_at": check_date,
            "note": "最后绿灯——衰退倒计时可能已经开始",
            "suggested_action": "关注衰退倒计时——最后绿灯信号",
        })

    # 3. ALERT-DEBT: debt/GDP > 350%
    if debt_gdp_ratio is not None and debt_gdp_ratio > 350:
        triggered.append({
            "alert_id": "ALERT-DEBT",
            "severity": "P1",
            "principle_ids": ["P003"],
            "title": "总债务/GDP 超过 350% 警戒线",
            "current_value": f"总债务/GDP = {debt_gdp_ratio:.1f}%",
            "triggered_at": check_date,
            "note": "债务超过泡沫顶部均值",
            "suggested_action": "生成专题简报：债务风险分析",
        })

    # 4. ALERT-DEBT2: debt/GDP > 300%
    if debt_gdp_ratio is not None and debt_gdp_ratio > 300:
        if debt_gdp_ratio <= 350:  # Don't double-alert if already P1
            triggered.append({
                "alert_id": "ALERT-DEBT2",
                "severity": "P2",
                "principle_ids": ["P003"],
                "title": "总债务/GDP 进入警戒区（> 300%）",
                "current_value": f"总债务/GDP = {debt_gdp_ratio:.1f}%",
                "triggered_at": check_date,
                "note": "债务超过 300% 警戒线",
                "suggested_action": "在简报中标注债务风险",
            })

    # 5. ALERT-STAG: Regime = Stagflation
    if diagnosis_entries:
        latest = diagnosis_entries[0]
        regime = latest.get("regime_quadrant", "")
        if regime == "Stagflation":
            triggered.append({
                "alert_id": "ALERT-STAG",
                "severity": "P2",
                "principle_ids": ["P004"],
                "title": "Regime 处于 Stagflation",
                "current_value": f"Stagflation (growth={latest.get('growth_value', '?')}%, "
                                 f"inflation={latest.get('inflation_value', '?')}%)",
                "triggered_at": check_date,
                "note": "增长低于 2% 阈值，通胀高于 3% 阈值，最差资产环境",
                "suggested_action": "维持现金+商品/黄金配置，减少股票/长债敞口",
            })

    # 6. ALERT-REGIME-SHIFT: quadrant change
    if len(diagnosis_entries) >= 2:
        current = diagnosis_entries[0].get("regime_quadrant", "")
        previous = diagnosis_entries[1].get("regime_quadrant", "")
        if current != previous:
            triggered.append({
                "alert_id": "ALERT-REGIME-SHIFT",
                "severity": "P2",
                "principle_ids": ["P004"],
                "title": f"Regime 象限切换: {previous} → {current}",
                "current_value": f"当前: {current}",
                "triggered_at": check_date,
                "note": "资产配置需要调整以适应新 regime",
                "suggested_action": "审查资产配置是否需要调整",
            })

    # 7/8. ALERT-DIVERGE / DIVERGE2
    if divergence is not None:
        if divergence > 15:
            triggered.append({
                "alert_id": "ALERT-DIVERGE",
                "severity": "P1",
                "principle_ids": ["P005"],
                "title": "资产通胀背离超过 +15% — 典型泡沫特征",
                "current_value": f"Divergence = {divergence:+.2f}%",
                "triggered_at": check_date,
                "note": "资产价格增速远高于商品通胀",
                "suggested_action": "生成专题简报：泡沫风险评估",
            })
        elif divergence > 10:
            triggered.append({
                "alert_id": "ALERT-DIVERGE2",
                "severity": "P2",
                "principle_ids": ["P005"],
                "title": "资产通胀背离超过 +10%",
                "current_value": f"Divergence = {divergence:+.2f}%",
                "triggered_at": check_date,
                "note": "关注泡沫风险",
                "suggested_action": "关注泡沫风险",
            })

    # 9. ALERT-SENTIMENT: UMCSENT < 60
    if umcsent is not None and umcsent < 60:
        triggered.append({
            "alert_id": "ALERT-SENTIMENT",
            "severity": "P2",
            "principle_ids": [],
            "title": "消费者信心极低",
            "current_value": f"UMCSENT = {umcsent:.1f}",
            "triggered_at": check_date,
            "note": f"消费者信心 {umcsent:.1f}，接近衰退读数",
            "suggested_action": "关注消费支出数据",
        })

    # 10. ALERT-SPREAD: HY > 5%
    if hy_spread is not None and hy_spread > 8:
        triggered.append({
            "alert_id": "ALERT-SPREAD2",
            "severity": "P1",
            "principle_ids": ["C2"],
            "title": "HY 信用利差超过 8% — 危机级别",
            "current_value": f"HY OAS = {hy_spread:.2f}%",
            "triggered_at": check_date,
            "note": "危机级别利差，信用市场恐慌",
            "suggested_action": "危机级别利差——全面风险排查",
        })
    elif hy_spread is not None and hy_spread > 5:
        triggered.append({
            "alert_id": "ALERT-SPREAD",
            "severity": "P1",
            "principle_ids": ["C2"],
            "title": "HY 信用利差超过 5%",
            "current_value": f"HY OAS = {hy_spread:.2f}%",
            "triggered_at": check_date,
            "note": "信用利差显著扩大，信用市场承压",
            "suggested_action": "信用市场恐慌——生成专题简报",
        })

    # 11. ALERT-RATE0: Fed < 0.5%
    if fedfunds is not None and fedfunds < 0.5:
        triggered.append({
            "alert_id": "ALERT-RATE0",
            "severity": "P2",
            "principle_ids": ["A6", "P007"],
            "title": "利率近零 — 货币政策空间耗尽",
            "current_value": f"Fed Funds = {fedfunds:.2f}%",
            "triggered_at": check_date,
            "note": "利率已近零，常规降息空间极有限",
            "suggested_action": "关注非常规货币政策",
        })

    return triggered


# ---------------------------------------------------------------------------
# Soft signal checker (news keyword matching)
# ---------------------------------------------------------------------------


def _check_soft_signals(news_file: str, check_date: str) -> list[dict[str, Any]]:
    """Scan news file for keywords matching soft signal rules."""
    triggered: list[dict[str, Any]] = []
    news_path = Path(news_file)

    if not news_path.exists():
        return triggered

    # Read all news headlines
    headlines: list[str] = []
    try:
        with open(news_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    title = item.get("title", "") or item.get("headline", "") or ""
                    if title:
                        headlines.append(title.lower())
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[run_alerts] Warning: error reading news file: {e}", file=sys.stderr)
        return triggered

    for rule in SOFT_SIGNAL_RULES:
        matched_keywords = []
        for kw in rule["keywords"]:
            kw_lower = kw.lower()
            for headline in headlines:
                if kw_lower in headline:
                    matched_keywords.append(kw)
                    break
            # Limit to first 3 matched keywords for display
            if len(matched_keywords) >= 3:
                break

        if matched_keywords:
            triggered.append({
                "alert_id": rule["alert_id"],
                "severity": rule["severity"],
                "principle_ids": rule["principle_ids"],
                "title": f"{rule['title']}（新闻关键词匹配）",
                "current_value": f"匹配关键词: {', '.join(matched_keywords)}",
                "triggered_at": check_date,
                "note": f"新闻扫描检测到 {len([h for h in headlines if any(k in h for k in matched_keywords)])} 条相关报道",
                "suggested_action": rule["suggested_action"],
            })

    return triggered


# ---------------------------------------------------------------------------
# Alert history management
# ---------------------------------------------------------------------------


def _load_alert_history() -> list[dict[str, Any]]:
    """Load existing alerts from alerts.jsonl."""
    if not ALERTS_FILE.exists():
        return []
    entries = []
    try:
        with open(ALERTS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        return []
    return entries


def _save_alerts(triggered: list[dict[str, Any]], check_date: str) -> None:
    """Append newly triggered alerts to alerts.jsonl."""
    if not triggered:
        return
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing to avoid duplicates within the same day
    existing = _load_alert_history()
    existing_ids_by_date = {
        (e.get("alert_id", ""), e.get("triggered_at", ""))
        for e in existing
    }

    with open(ALERTS_FILE, "a") as f:
        for alert in triggered:
            key = (alert["alert_id"], alert["triggered_at"])
            if key not in existing_ids_by_date:
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")
                existing_ids_by_date.add(key)


def _resolve_active_alerts(triggered: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge newly triggered alerts with history, marking resolved ones."""
    history = _load_alert_history()

    # Group history by alert_id, get latest entry per ID
    latest_per_id: dict[str, dict[str, Any]] = {}
    for entry in history:
        aid = entry.get("alert_id", "")
        latest_per_id[aid] = entry  # last write wins since append-only

    # Current triggered alert IDs
    current_ids = {a["alert_id"] for a in triggered}

    # Build active list
    active: list[dict[str, Any]] = list(triggered)

    # Add previously triggered but still active (not yet resolved)
    for aid, entry in latest_per_id.items():
        if aid not in current_ids and entry.get("resolved_at") is None:
            # Still active but not newly triggered — mark as "持续中"
            ongoing = dict(entry)
            ongoing["status"] = "持续中"
            active.append(ongoing)

    return active


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Principle-driven alert engine")
    parser.add_argument("--date", default="",
                        help="Check date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--news", default="",
                        help="Path to news JSONL file")
    args = parser.parse_args()

    check_date = args.date or Date.today().isoformat()

    # ---- Read data ----
    snapshot = _read_snapshot()
    if not snapshot:
        print(json.dumps({
            "checked_at": datetime.now().isoformat(),
            "check_date": check_date,
            "triggered_alerts": [],
            "total_alerts": 0,
            "p1_count": 0,
            "p2_count": 0,
            "error": "No snapshot data found",
        }, ensure_ascii=False))
        sys.exit(0)

    diagnosis_entries = _read_diagnosis_history()

    print(f"[run_alerts] Snapshot: {len(snapshot)} series, "
          f"Diagnosis entries: {len(diagnosis_entries)}",
          file=sys.stderr)

    # ---- Check hard signals ----
    hard_alerts = _check_hard_signals(snapshot, diagnosis_entries, check_date)
    print(f"[run_alerts] Hard signal alerts triggered: {len(hard_alerts)}",
          file=sys.stderr)
    for a in hard_alerts:
        print(f"  {a['severity']} {a['alert_id']}: {a['title']}", file=sys.stderr)

    # ---- Check soft signals ----
    soft_alerts: list[dict[str, Any]] = []
    if args.news:
        soft_alerts = _check_soft_signals(args.news, check_date)
        print(f"[run_alerts] Soft signal alerts triggered: {len(soft_alerts)}",
              file=sys.stderr)
        for a in soft_alerts:
            print(f"  {a['severity']} {a['alert_id']}: {a['title']}", file=sys.stderr)

    # ---- Combine ----
    all_alerts = hard_alerts + soft_alerts
    p1_count = sum(1 for a in all_alerts if a["severity"] == "P1")
    p2_count = sum(1 for a in all_alerts if a["severity"] == "P2")
    p3_count = sum(1 for a in all_alerts if a["severity"] == "P3")

    # ---- Persist ----
    _save_alerts(all_alerts, check_date)
    active_alerts = _resolve_active_alerts(all_alerts)
    print(f"[run_alerts] Active alerts total: {len(active_alerts)}, "
          f"Newly triggered: {len(all_alerts)}",
          file=sys.stderr)

    # ---- Output JSON ----
    output = {
        "checked_at": datetime.now().isoformat(),
        "check_date": check_date,
        "triggered_alerts": all_alerts,
        "active_alerts": active_alerts,
        "total_alerts": len(all_alerts),
        "p1_count": p1_count,
        "p2_count": p2_count,
        "p3_count": p3_count,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
