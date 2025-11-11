#!/usr/bin/env python3
"""
Advanced Persistence Monitoring & Diagnostics Tool

Monitors and verifies all three persistence layers:
1. SIM Balance (JSON file: data/sim_balance.json)
2. Trade Records (Database: SQLite or PostgreSQL)
3. Statistics (Computed from trade records)

Provides real-time diagnostics and validation.

Usage:
    python tools/persistence_monitor.py --watch
    python tools/persistence_monitor.py --verify
    python tools/persistence_monitor.py --report
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PersistenceMonitor:
    """Monitor and verify all persistence layers"""

    def __init__(self):
        self.reports = []
        self.last_sim_balance = None
        self.last_trade_count = 0

    def log(self, level: str, msg: str) -> None:
        """Log with timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {level:8} {msg}")

    # ========== LAYER 1: SIM BALANCE JSON ==========

    def check_sim_balance_file(self) -> Dict[str, Any]:
        """Verify SIM balance file persistence"""
        result = {
            "layer": "SIM Balance (JSON)",
            "file": "data/sim_balance.json",
            "status": "unknown",
            "details": {},
            "errors": [],
        }

        try:
            sim_file = Path("data/sim_balance.json")

            if not sim_file.exists():
                result["status"] = "missing"
                result["errors"].append("File does not exist")
                return result

            with open(sim_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            result["details"] = {
                "balance": data.get("balance"),
                "last_reset_month": data.get("last_reset_month"),
                "last_updated": data.get("last_updated"),
            }

            result["status"] = "ok"

            # Check if balance is valid
            balance = data.get("balance")
            if balance is not None and isinstance(balance, (int, float)):
                if balance > 0:
                    result["details"]["balance_valid"] = True
                    result["details"]["balance_usd"] = f"${balance:,.2f}"
                else:
                    result["errors"].append(f"Balance is {balance} (should be > 0)")
            else:
                result["errors"].append("Balance is missing or not a number")

        except json.JSONDecodeError as e:
            result["status"] = "corrupted"
            result["errors"].append(f"JSON decode error: {e}")

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Error reading file: {e}")

        return result

    # ========== LAYER 2: TRADE RECORDS DATABASE ==========

    def check_trade_records_db(self) -> Dict[str, Any]:
        """Verify trade records in database"""
        result = {
            "layer": "Trade Records (Database)",
            "status": "unknown",
            "details": {},
            "errors": [],
        }

        try:
            from data.db_engine import get_session, health_check
            from data.schema import TradeRecord
            from sqlalchemy import func

            # Check connectivity
            ok, msg = health_check()
            if not ok:
                result["status"] = "disconnected"
                result["errors"].append(f"Database connection failed: {msg}")
                return result

            # Query trade counts
            with get_session() as session:
                total_trades = session.query(func.count(TradeRecord.id)).scalar() or 0
                sim_trades = session.query(func.count(TradeRecord.id)).filter(TradeRecord.mode == "SIM").scalar() or 0
                live_trades = session.query(func.count(TradeRecord.id)).filter(TradeRecord.mode == "LIVE").scalar() or 0

                total_pnl = session.query(func.sum(TradeRecord.realized_pnl)).scalar() or 0.0

                result["details"] = {
                    "total_trades": total_trades,
                    "sim_trades": sim_trades,
                    "live_trades": live_trades,
                    "total_pnl": f"${float(total_pnl):,.2f}",
                    "connection": "ok",
                }

                result["status"] = "ok"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Database query error: {e}")

        return result

    # ========== LAYER 3: STATISTICS ==========

    def check_statistics_computation(self) -> Dict[str, Any]:
        """Verify statistics can be computed"""
        result = {
            "layer": "Statistics (Computed)",
            "status": "unknown",
            "details": {},
            "errors": [],
        }

        try:
            from services.stats_service import compute_trading_stats_for_timeframe

            # Try to compute stats for today
            stats = compute_trading_stats_for_timeframe("1D", mode="SIM")

            if not stats or stats == {}:
                result["status"] = "no_data"
                result["details"]["message"] = "No trades in timeframe (expected for new accounts)"
                return result

            result["details"] = {
                "total_pnl": stats.get("Total PnL"),
                "trades": stats.get("Trades"),
                "hit_rate": stats.get("Hit Rate"),
                "max_drawdown": stats.get("Max Drawdown"),
                "expectancy": stats.get("Expectancy"),
            }

            result["status"] = "ok"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Statistics computation error: {e}")

        return result

    # ========== INTEGRATION CHECKS ==========

    def check_data_consistency(self) -> Dict[str, Any]:
        """Verify all layers are consistent"""
        result = {
            "check": "Data Consistency",
            "status": "unknown",
            "issues": [],
        }

        try:
            # Get SIM balance from file
            with open("data/sim_balance.json") as f:
                sim_data = json.load(f)
                file_balance = sim_data.get("balance", 0)

            # Get SIM balance from state manager
            from core.sim_balance import get_sim_balance

            state_balance = get_sim_balance()

            # Check if they match
            if abs(file_balance - state_balance) < 0.01:  # Allow for float precision
                result["status"] = "consistent"
                result["balance_match"] = True
            else:
                result["status"] = "inconsistent"
                result["balance_match"] = False
                result["issues"].append(
                    f"Balance mismatch: file={file_balance}, state={state_balance}"
                )

        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"Consistency check error: {e}")

        return result

    # ========== REPORTING ==========

    def generate_full_report(self) -> None:
        """Generate comprehensive persistence report"""
        print("\n" + "=" * 70)
        print("APPSIERRA PERSISTENCE MONITORING REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")

        # Check each layer
        print("LAYER 1: SIM BALANCE (JSON FILE)")
        print("-" * 70)
        sim_result = self.check_sim_balance_file()
        self._print_result(sim_result)

        print("\nLAYER 2: TRADE RECORDS (DATABASE)")
        print("-" * 70)
        db_result = self.check_trade_records_db()
        self._print_result(db_result)

        print("\nLAYER 3: STATISTICS (COMPUTED)")
        print("-" * 70)
        stats_result = self.check_statistics_computation()
        self._print_result(stats_result)

        print("\nINTEGRATION CHECK")
        print("-" * 70)
        consistency = self.check_data_consistency()
        self._print_result(consistency)

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print("\nAll persistence layers are being monitored.")
        print("✓ SIM Balance: Persists to JSON file (fast, reliable)")
        print("✓ Trade Records: Persists to database (comprehensive, queryable)")
        print("✓ Statistics: Computed on-demand from trade records")
        print("\nFor any issues, check the error messages above.")
        print("=" * 70 + "\n")

    @staticmethod
    def _print_result(result: Dict[str, Any]) -> None:
        """Pretty print a result"""
        status = result.get("status", "unknown")
        status_symbol = {
            "ok": "✓",
            "error": "✗",
            "missing": "⚠",
            "disconnected": "✗",
            "corrupted": "✗",
            "consistent": "✓",
            "inconsistent": "⚠",
            "no_data": "ℹ",
        }.get(status, "?")

        print(f"{status_symbol} Status: {status.upper()}")

        if "details" in result and result["details"]:
            print(f"  Details:")
            for key, value in result["details"].items():
                print(f"    {key}: {value}")

        if "errors" in result and result["errors"]:
            print(f"  Errors:")
            for error in result["errors"]:
                print(f"    ✗ {error}")

    def watch_changes(self, interval: int = 5) -> None:
        """Watch for changes in persistence layers"""
        print("\n" + "=" * 70)
        print("APPSIERRA PERSISTENCE MONITOR (WATCH MODE)")
        print("Monitoring for changes every {} seconds... (Ctrl+C to stop)".format(interval))
        print("=" * 70 + "\n")

        try:
            while True:
                # Check SIM balance
                sim_result = self.check_sim_balance_file()
                if sim_result["status"] == "ok":
                    current_balance = sim_result["details"].get("balance")
                    if current_balance != self.last_sim_balance:
                        self.log("CHANGE", f"SIM balance changed: ${current_balance:,.2f}")
                        self.last_sim_balance = current_balance

                # Check trade count
                db_result = self.check_trade_records_db()
                if db_result["status"] == "ok":
                    current_trade_count = db_result["details"].get("total_trades", 0)
                    if current_trade_count != self.last_trade_count:
                        self.log(
                            "CHANGE",
                            f"Trade count changed: {current_trade_count} (was {self.last_trade_count})",
                        )
                        self.last_trade_count = current_trade_count

                time.sleep(interval)

        except KeyboardInterrupt:
            self.log("STOP", "Monitor stopped by user")


def main():
    parser = argparse.ArgumentParser(description="APPSIERRA Persistence Monitor")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate full persistence report (default)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for changes in persistence (live monitoring)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Watch interval in seconds (default: 5)",
    )

    args = parser.parse_args()

    monitor = PersistenceMonitor()

    if args.watch:
        monitor.watch_changes(interval=args.interval)
    else:
        # Default to report
        monitor.generate_full_report()

    return 0


if __name__ == "__main__":
    sys.exit(main())
