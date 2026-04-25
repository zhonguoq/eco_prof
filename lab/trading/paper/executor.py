#!/usr/bin/env python3
"""
executor.py
===========
Convert eco-advise tilt signals to paper trading orders.

Mapping:
    tilt -2 →  0% allocation
    tilt -1 → 10%
    tilt  0 → 25%
    tilt +1 → 40%
    tilt +2 → 60%

These raw allocations are normalized to sum to 100% and converted
to ETF share counts based on current prices.

Usage:
    python3 lab/trading/paper/executor.py --tilts '{"stocks":-2,"long_bonds":-1,"commodities_gold":1,"cash":2}'
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from lab.trading.paper.account import PaperAccount, ETF_MAP  # noqa: E402

# ---------------------------------------------------------------------------
# Tilt → weight mapping
# ---------------------------------------------------------------------------

TILT_TO_RAW: dict[int, float] = {
    -2: 0.0,
    -1: 0.10,
    0: 0.25,
    1: 0.40,
    2: 0.60,
}


def tilts_to_weights(tilts: dict[str, int]) -> dict[str, float]:
    """Convert tilt dict to normalized allocation weights.

    Args:
        tilts: {"stocks": -2, "long_bonds": -1, ...}

    Returns:
        {"SPY": 0.0, "TLT": 0.09, "GLD": 0.36, "BIL": 0.55, ...}
    """
    raw = {}
    for asset_class, tilt in tilts.items():
        tilt = max(-2, min(2, tilt))  # clamp
        ticker = ETF_MAP.get(asset_class)
        if ticker:
            raw[ticker] = TILT_TO_RAW.get(tilt, 0.25)

    total = sum(raw.values())
    if total == 0:
        # All zero → equally split
        for k in raw:
            raw[k] = 1.0 / len(raw)
    else:
        for k in raw:
            raw[k] /= total

    return raw


def advise_to_allocation(
    advice_tilts: dict[str, int],
    prices: dict[str, float],
    portfolio_value: float,
) -> dict[str, dict[str, Any]]:
    """Convert advice tilts to target position sizes.

    Args:
        advice_tilts: {"stocks": -2, "long_bonds": -1, ...}
        prices: {"SPY": 450.0, ...}
        portfolio_value: total portfolio value to allocate

    Returns:
        {ticker: {"ticker": ..., "weight": ..., "target_value": ..., "target_shares": ...}}
    """
    weights = tilts_to_weights(advice_tilts)
    result = {}
    for ticker, weight in weights.items():
        target_value = portfolio_value * weight
        price = prices.get(ticker, 100.0)
        target_shares = int(target_value / price) if price > 0 else 0
        result[ticker] = {
            "ticker": ticker,
            "weight": round(weight, 4),
            "target_value": round(target_value, 2),
            "price": price,
            "target_shares": target_shares,
        }
    return result


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_advice(
    advice_tilts: dict[str, int],
    prices: dict[str, float],
    reason: str = "",
) -> dict[str, Any]:
    """Execute rebalance based on advice tilts.

    Steps:
    1. Calculate current positions and total equity
    2. Calculate target allocations from tilts
    3. Generate orders to rebalance
    4. Execute orders on the PaperAccount
    """
    acct = PaperAccount()
    total_value = acct.total_equity

    # Calculate target weights
    targets = advise_to_allocation(advice_tilts, prices, total_value)

    # Calculate current positions
    current_positions: dict[str, int] = {}
    current_values: dict[str, float] = {}
    for ticker, pos in acct.positions.items():
        current_positions[ticker] = pos.shares
        price = prices.get(ticker, pos.avg_cost)
        current_values[ticker] = pos.shares * price

    # Generate orders
    orders: list[dict[str, Any]] = []
    for ticker, target in targets.items():
        current_shares = current_positions.get(ticker, 0)
        target_shares = target["target_shares"]
        price = prices.get(ticker, 100.0)
        diff = target_shares - current_shares

        if abs(diff) < 1:
            continue

        side = "BUY" if diff > 0 else "SELL"
        shares = abs(diff)

        try:
            result = acct.execute_order(
                side=side,
                ticker=ticker,
                shares=shares,
                price=price,
                reason=reason,
            )
            orders.append(result)
        except ValueError as e:
            orders.append({
                "status": "rejected",
                "side": side,
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "reason": str(e),
            })

    return {
        "executed_at": datetime.now().isoformat(),
        "advice_reason": reason,
        "portfolio_value_before": round(total_value, 2),
        "portfolio_value_after": round(acct.total_equity, 2),
        "targets": targets,
        "orders": orders,
        "fills": len([o for o in orders if o.get("status") == "filled"]),
        "rejected": len([o for o in orders if o.get("status") == "rejected"]),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Execute eco-advise tilts")
    parser.add_argument("--tilts", required=True,
                        help='JSON: {"stocks":-2,"long_bonds":-1,...}')
    parser.add_argument("--prices", default="{}",
                        help='JSON: {"SPY":450.0,"TLT":90.0,...}')
    parser.add_argument("--reason", default="eco-advise",
                        help="Reason for the trade")
    args = parser.parse_args()

    try:
        tilts = json.loads(args.tilts)
        prices = json.loads(args.prices)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = execute_advice(tilts, prices, args.reason)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
