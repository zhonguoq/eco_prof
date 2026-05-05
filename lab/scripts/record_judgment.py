#!/usr/bin/env python3
import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.engine.db import get_db
from lab.engine.meta.judgment import record_judgment


def main():
    parser = argparse.ArgumentParser(description="Record a judgment")
    parser.add_argument("--type", required=True, choices=["macro", "micro"])
    parser.add_argument("--stage", required=True)
    parser.add_argument("--confidence", required=True, choices=["high", "medium", "low"])
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--verification-window", required=True)
    parser.add_argument("--context")
    args = parser.parse_args()

    conn = get_db("meta")
    jid = record_judgment(conn, type=args.type, stage=args.stage,
                          confidence=args.confidence, prediction=args.prediction,
                          verification_window=args.verification_window,
                          context=args.context)
    print(jid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
