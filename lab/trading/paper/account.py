#!/usr/bin/env python3
"""
account.py
==========
Paper trading account — holds cash + positions, tracks NAV/P&L/trade history.

State is persisted to lab/data/paper_state.json.

Usage:
    from lab.trading.paper.account import PaperAccount
    acct = PaperAccount()
    acct.initial_deposit(100000)
    acct.execute_order("BUY", "SPY", 10, 450.0)
    print(acct.summary())
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = ROOT / "lab" / "data" / "paper_state.json"

# ETF proxies for asset classes
ETF_MAP = {
    "stocks": "SPY",         # S&P 500 ETF
    "long_bonds": "TLT",     # 20+ Year Treasury ETF
    "commodities_gold": "GLD",  # Gold ETF
    "cash": "BIL",           # 1-3 Month T-Bill ETF
}

ETF_NAMES = {
    "SPY": "S&P 500 ETF (stocks)",
    "TLT": "20+ Year Treasury ETF (long bonds)",
    "GLD": "Gold ETF (commodities/gold)",
    "BIL": "1-3 Month T-Bill ETF (cash)",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TradeRecord:
    timestamp: str
    side: str          # "BUY" or "SELL"
    ticker: str
    shares: int
    price: float
    value: float       # shares * price
    reason: str = ""   # e.g., "rebalance: eco-advise 2026-04-25"


@dataclass
class Position:
    ticker: str
    shares: int = 0
    avg_cost: float = 0.0

    def market_value(self, current_price: float | None = None) -> float:
        return self.shares * (current_price if current_price is not None else self.avg_cost)


# ---------------------------------------------------------------------------
# Paper Account
# ---------------------------------------------------------------------------


class PaperAccount:
    """Simple paper trading account with persistent state."""

    def __init__(self, initial_cash: float = 100_000.0):
        self.initial_cash: float = initial_cash
        self.cash: float = initial_cash
        self.positions: dict[str, Position] = {}
        self.trades: list[TradeRecord] = []
        self.prices: dict[str, float] = {}  # latest known prices
        self._load()

    # ---- Persistence ----

    def _load(self) -> None:
        """Load state from disk if exists."""
        if not STATE_FILE.exists():
            self.cash = self.initial_cash
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            self.cash = data.get("cash", self.initial_cash)
            self.initial_cash = data.get("initial_cash", self.initial_cash)
            self.prices = data.get("prices", {})
            for p_data in data.get("positions", []):
                pos = Position(**p_data)
                self.positions[pos.ticker] = pos
            for t_data in data.get("trades", []):
                self.trades.append(TradeRecord(**t_data))
        except Exception:
            pass

    def save(self) -> None:
        """Persist current state to disk."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "prices": self.prices,
            "positions": [asdict(p) for p in self.positions.values()],
            "trades": [asdict(t) for t in self.trades],
            "updated_at": datetime.now().isoformat(),
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ---- Account operations ----

    def initial_deposit(self, amount: float) -> None:
        """Set initial cash balance."""
        self.cash = amount
        self.initial_cash = amount
        self.save()

    @property
    def total_equity(self) -> float:
        """Cash + market value of all positions (using latest known prices)."""
        pos_value = sum(
            pos.market_value(self.prices.get(pos.ticker))
            for pos in self.positions.values()
        )
        return self.cash + pos_value

    @property
    def total_pnl(self) -> float:
        """Total P&L since inception."""
        return self.total_equity - self.initial_cash

    @property
    def total_pnl_pct(self) -> float:
        """Total return as percentage."""
        if self.initial_cash == 0:
            return 0.0
        return (self.total_pnl / self.initial_cash) * 100

    # ---- Trading ----

    def update_price(self, ticker: str, price: float) -> None:
        """Update latest known price for a ticker."""
        self.prices[ticker] = price

    def execute_order(
        self,
        side: str,
        ticker: str,
        shares: int,
        price: float,
        reason: str = "",
    ) -> dict[str, Any]:
        """Execute a paper trade.

        Args:
            side: "BUY" or "SELL"
            ticker: ETF ticker
            shares: number of shares
            price: execution price
            reason: reason for the trade

        Returns:
            dict with execution result.

        Raises:
            ValueError: if insufficient cash (BUY) or shares (SELL).
        """
        if side.upper() not in ("BUY", "SELL"):
            raise ValueError(f"Invalid side: {side}. Use BUY or SELL.")

        value = shares * price

        if side.upper() == "BUY":
            if value > self.cash:
                raise ValueError(
                    f"Insufficient cash: need ${value:,.2f}, have ${self.cash:,.2f}"
                )
            self.cash -= value
            if ticker not in self.positions:
                self.positions[ticker] = Position(ticker=ticker)
            pos = self.positions[ticker]
            # Weighted average cost
            total_cost = pos.avg_cost * pos.shares + value
            pos.shares += shares
            pos.avg_cost = total_cost / pos.shares if pos.shares > 0 else 0
        else:
            if ticker not in self.positions or self.positions[ticker].shares < shares:
                raise ValueError(
                    f"Insufficient shares: have "
                    f"{self.positions.get(ticker, Position(ticker)).shares}, want {shares}"
                )
            self.cash += value
            pos = self.positions[ticker]
            pos.shares -= shares
            if pos.shares == 0:
                del self.positions[ticker]

        trade = TradeRecord(
            timestamp=datetime.now().isoformat(),
            side=side.upper(),
            ticker=ticker,
            shares=shares,
            price=price,
            value=value,
            reason=reason,
        )
        self.trades.append(trade)
        self.prices[ticker] = price
        self.save()

        return {
            "status": "filled",
            "side": side.upper(),
            "ticker": ticker,
            "shares": shares,
            "price": price,
            "value": value,
            "cash_remaining": self.cash,
            "reason": reason,
        }

    def close_all(self, reason: str = "closeout") -> list[dict[str, Any]]:
        """Liquidate all positions at latest known prices."""
        results = []
        for ticker, pos in list(self.positions.items()):
            price = self.prices.get(ticker, pos.avg_cost)
            result = self.execute_order("SELL", ticker, pos.shares, price, reason)
            results.append(result)
        return results

    # ---- Reporting ----

    def summary(self) -> dict[str, Any]:
        """Return a snapshot of account state."""
        pos_details = {}
        for ticker, pos in self.positions.items():
            current_price = self.prices.get(ticker, pos.avg_cost)
            pos_details[ticker] = {
                "ticker": ticker,
                "shares": pos.shares,
                "avg_cost": round(pos.avg_cost, 2),
                "current_price": round(current_price, 2),
                "market_value": round(pos.market_value(current_price), 2),
                "unrealized_pnl": round(
                    (current_price - pos.avg_cost) * pos.shares, 2
                ),
            }

        return {
            "initial_cash": self.initial_cash,
            "cash": round(self.cash, 2),
            "total_equity": round(self.total_equity, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "positions": pos_details,
            "num_positions": len(self.positions),
            "num_trades": len(self.trades),
            "last_trade": asdict(self.trades[-1]) if self.trades else None,
        }

    def trade_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent trade history."""
        recent = self.trades[-limit:] if limit else self.trades
        return [asdict(t) for t in recent]


def main() -> None:
    """CLI entry point for manual account inspection."""
    import argparse
    parser = argparse.ArgumentParser(description="Paper trading account")
    parser.add_argument("action", choices=["summary", "trades", "reset"],
                        default="summary", nargs="?")
    parser.add_argument("--deposit", type=float, default=100000,
                        help="Initial deposit (for reset)")
    args = parser.parse_args()

    acct = PaperAccount()

    if args.action == "reset":
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        acct = PaperAccount(args.deposit)
        acct.initial_deposit(args.deposit)
        print(json.dumps({"status": "reset", "deposit": args.deposit}))
        return

    if args.action == "trades":
        print(json.dumps(acct.trade_history(limit=50), indent=2))
        return

    # Default: summary
    print(json.dumps(acct.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
