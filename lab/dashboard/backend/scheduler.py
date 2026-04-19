"""
Data Scheduler
==============
APScheduler-based auto-fetch for FRED data.
Integrated into FastAPI via lifespan context manager.

Schedule: daily at 06:00 UTC (roughly 18:00 ET, after FRED updates).
On startup: runs immediately if no data for today.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
FETCHER_SCRIPT = TOOLS_DIR / "fetch_us_indicators.py"
YIELD_CURVE_SCRIPT = TOOLS_DIR / "fetch_yield_curve.py"


def _today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def _has_today_data() -> bool:
    """Check if snapshot for today already exists."""
    return (DATA_DIR / f"fred_snapshot_{_today_str()}.csv").exists()


def run_fetch() -> bool:
    """Run the FRED fetcher scripts. Returns True on success."""
    logger.info("Starting FRED data fetch...")
    success = True

    for script in [FETCHER_SCRIPT, YIELD_CURVE_SCRIPT]:
        if not script.exists():
            logger.warning(f"Script not found: {script}")
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                logger.info(f"Fetch OK: {script.name}")
            else:
                logger.error(f"Fetch FAILED: {script.name}\n{result.stderr}")
                success = False
        except subprocess.TimeoutExpired:
            logger.error(f"Fetch TIMEOUT: {script.name}")
            success = False
        except Exception as e:
            logger.error(f"Fetch ERROR: {script.name}: {e}")
            success = False

    return success


def run_fetch_and_log() -> None:
    """Fetch data, compute diagnosis + regime, append to history log."""
    from .main import read_snapshot, compute_diagnosis
    from .regime import compute_regime, append_history

    success = run_fetch()
    if not success:
        logger.warning("Fetch had errors — attempting diagnosis with available data")

    snapshot = read_snapshot()
    if snapshot is None:
        logger.error("No snapshot available after fetch — skipping diagnosis")
        return

    diagnosis = compute_diagnosis(snapshot)
    regime = compute_regime(snapshot)
    append_history(diagnosis, regime)
    logger.info(
        f"Diagnosis logged: stage={diagnosis['stage']}, "
        f"regime={regime.get('quadrant', 'N/A')}"
    )


# ---------------------------------------------------------------------------
# APScheduler setup
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()


def _has_today_history() -> bool:
    """Check if history already has a record for today."""
    from .regime import HISTORY_FILE
    if not HISTORY_FILE.exists():
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    with open(HISTORY_FILE) as f:
        for line in f:
            if f'"date": "{today}"' in line:
                return True
    return False


def log_diagnosis_only() -> None:
    """Compute diagnosis from existing data and log to history (no fetch)."""
    from .main import read_snapshot, compute_diagnosis
    from .regime import compute_regime, append_history

    snapshot = read_snapshot()
    if snapshot is None:
        logger.error("No snapshot available — cannot log diagnosis")
        return
    diagnosis = compute_diagnosis(snapshot)
    regime = compute_regime(snapshot)
    append_history(diagnosis, regime)
    logger.info(
        f"Diagnosis logged: stage={diagnosis['stage']}, "
        f"regime={regime.get('quadrant', 'N/A')}"
    )


def start_scheduler() -> None:
    """Start the background scheduler. Call once at app startup."""
    # Daily job at 06:00 UTC
    scheduler.add_job(
        run_fetch_and_log,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily fetch at 06:00 UTC")

    # Run immediately if no data for today
    if not _has_today_data():
        logger.info("No data for today — running initial fetch")
        run_fetch_and_log()
    elif not _has_today_history():
        logger.info("Today's data exists but no history entry — logging diagnosis")
        log_diagnosis_only()
    else:
        logger.info("Today's data and history already exist — skipping")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


@asynccontextmanager
async def scheduler_lifespan(app):
    """FastAPI lifespan context manager for scheduler."""
    start_scheduler()
    yield
    stop_scheduler()
