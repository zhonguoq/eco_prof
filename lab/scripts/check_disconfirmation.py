#!/usr/bin/env python3
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.macro.diagnose import read_signals
from lab.engine.meta.disconfirmation import check_disconfirmation


def main():
    conn_macro = get_db("macro")
    conn_meta = get_db("meta")

    results = check_disconfirmation(conn_meta, lambda: read_signals(conn_macro))
    if not results:
        print("未检测到背离")
        return 0

    print(f"检测到 {len(results)} 条背离:")
    for r in results:
        print(f"  {r['id']} ({r['stage']}, {r['timestamp'][:10]})")
        print(f"    {r['summary']}")
        for d in r["divergences"]:
            print(f"    {d['signal']}: {d['old']} → {d['current']} (Δ{d['change']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
