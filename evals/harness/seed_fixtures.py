"""
harness/seed_fixtures.py — Fixture 种子脚本（ADR-003 决策 8）

跑 fetch_financials.py 拉三只股票数据，
然后复制 lab/db/micro.db 到 evals/fixtures/micro_seeded.db。

运行方式：
  python -m evals.harness.seed_fixtures
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent
_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_SCRIPTS_DIR = _REPO_ROOT / "lab" / "scripts"

STOCKS = [
    ("000725.SZ", "CN"),
    ("00700.HK", "HK"),
    ("AAPL", "US"),
]


def seed() -> int:
    """拉取三只股票数据并复制到 evals/fixtures/micro_seeded.db。"""
    _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Seeding fixtures ===")
    for code, country in STOCKS:
        print(f"Fetching {code} ({country})...")
        r = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS_DIR / "fetch_financials.py"),
                "--code",
                code,
                "--country",
                country,
            ],
            cwd=str(_REPO_ROOT),
        )
        if r.returncode != 0:
            print(f"  ERROR: fetch_financials.py failed for {code}", file=sys.stderr)
            return 1

    # 复制 micro.db → fixtures/micro_seeded.db
    src_db = _REPO_ROOT / "lab" / "db" / "micro.db"
    dst_db = _FIXTURES_DIR / "micro_seeded.db"
    if not src_db.exists():
        print(f"ERROR: {src_db} not found", file=sys.stderr)
        return 1

    shutil.copy2(str(src_db), str(dst_db))
    print(f"Fixture saved: {dst_db}")
    return 0


if __name__ == "__main__":
    sys.exit(seed())
