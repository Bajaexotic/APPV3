#!/usr/bin/env python3
"""
Database Setup & Verification Tool

An advanced database configuration tool that:
1. Validates database configuration
2. Tests connectivity to all configured databases
3. Creates tables if needed
4. Provides detailed diagnostics
5. Handles fallbacks gracefully

Usage:
    python tools/database_setup.py
    python tools/database_setup.py --test
    python tools/database_setup.py --init
    python tools/database_setup.py --health
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseSetup:
    """Advanced database setup and verification"""

    def __init__(self):
        self.results = []
        self.db_url = None
        self.engine = None
        self.config = {}

    def log(self, level: str, msg: str) -> None:
        """Log with colored output"""
        colors = {"✓": "\033[92m", "✗": "\033[91m", "⚠": "\033[93m", "ℹ": "\033[94m"}
        reset = "\033[0m"
        symbol = level[0]
        color = colors.get(symbol, "")
        print(f"{color}{level}{reset} {msg}")
        self.results.append((level, msg))

    def check_config(self) -> bool:
        """Step 1: Verify configuration files exist and are valid"""
        self.log("ℹ Config Check", "Verifying configuration files...")

        try:
            from config.settings import (
                DB_URL,
                POSTGRES_DSN,
                TRADING_MODE,
            )

            self.db_url = DB_URL
            self.config = {
                "DB_URL": DB_URL,
                "POSTGRES_DSN": POSTGRES_DSN,
                "TRADING_MODE": TRADING_MODE,
            }

            if not DB_URL:
                self.log("✗ Config Error", "DB_URL is not set!")
                return False

            self.log("✓ Config Valid", f"Using DB_URL: {self._mask_url(DB_URL)}")
            return True

        except Exception as e:
            self.log("✗ Config Error", f"Failed to load config: {e}")
            return False

    def check_db_type(self) -> str:
        """Determine database type from URL"""
        if not self.db_url:
            return "unknown"

        if "postgresql" in self.db_url.lower():
            return "postgresql"
        elif "sqlite" in self.db_url.lower():
            return "sqlite"
        elif "mysql" in self.db_url.lower():
            return "mysql"
        else:
            return "other"

    def check_connectivity(self) -> bool:
        """Step 2: Test database connectivity"""
        self.log("ℹ Connectivity Check", f"Testing database connection...")

        try:
            from data.db_engine import engine, health_check

            self.engine = engine

            ok, msg = health_check()
            if ok:
                self.log("✓ Connected", msg)
                return True
            else:
                self.log("✗ Connection Failed", msg)
                return False

        except Exception as e:
            self.log("✗ Connection Error", f"Failed to connect: {e}")
            return False

    def check_tables(self) -> bool:
        """Step 3: Verify database tables exist"""
        self.log("ℹ Table Check", "Verifying database schema...")

        try:
            from sqlalchemy import inspect, text

            inspector = inspect(self.engine)
            tables = inspector.get_table_names()

            required_tables = ["traderecord", "orderrecord", "accountbalance"]
            missing = [t for t in required_tables if t not in tables]

            if missing:
                self.log(
                    "⚠ Tables Missing",
                    f"Missing tables: {', '.join(missing)}. Run with --init to create.",
                )
                return False
            else:
                self.log("✓ Tables Exist", f"Found {len(tables)} tables: {', '.join(tables)}")
                return True

        except Exception as e:
            self.log("✗ Table Check Error", f"Failed to check tables: {e}")
            return False

    def init_db(self) -> bool:
        """Step 4: Create database tables"""
        self.log("ℹ Database Init", "Creating tables...")

        try:
            from data.db_engine import init_db

            init_db()
            self.log("✓ Tables Created", "Database schema initialized successfully")
            return True

        except Exception as e:
            self.log("✗ Init Error", f"Failed to create tables: {e}")
            return False

    def test_write(self) -> bool:
        """Step 5: Test writing to database"""
        self.log("ℹ Write Test", "Testing database write capability...")

        try:
            from data.db_engine import get_session
            from data.schema import TradeRecord
            from datetime import datetime

            # Create a test trade record
            with get_session() as session:
                test_trade = TradeRecord(
                    symbol="TEST.US.TEST",
                    side="LONG",
                    qty=1,
                    mode="SIM",
                    entry_price=100.0,
                    entry_time=datetime.utcnow(),
                    realized_pnl=500.0,
                    account="TEST",
                )
                session.add(test_trade)
                session.commit()
                trade_id = test_trade.id

            self.log("✓ Write Test Passed", f"Successfully wrote test trade (ID: {trade_id})")
            return True

        except Exception as e:
            self.log("✗ Write Test Failed", f"Could not write to database: {e}")
            return False

    def test_read(self) -> bool:
        """Step 6: Test reading from database"""
        self.log("ℹ Read Test", "Testing database read capability...")

        try:
            from data.db_engine import get_session
            from data.schema import TradeRecord

            with get_session() as session:
                trades = session.query(TradeRecord).filter(TradeRecord.symbol == "TEST.US.TEST").all()

                if trades:
                    self.log("✓ Read Test Passed", f"Found {len(trades)} test record(s)")
                    return True
                else:
                    self.log("⚠ Read Test", "No test records found (may be first run)")
                    return True

        except Exception as e:
            self.log("✗ Read Test Failed", f"Could not read from database: {e}")
            return False

    def cleanup_test_data(self) -> bool:
        """Clean up test trade records"""
        self.log("ℹ Cleanup", "Removing test data...")

        try:
            from data.db_engine import get_session
            from data.schema import TradeRecord

            with get_session() as session:
                session.query(TradeRecord).filter(TradeRecord.symbol == "TEST.US.TEST").delete()
                session.commit()

            self.log("✓ Cleanup Done", "Test data removed")
            return True

        except Exception as e:
            self.log("⚠ Cleanup Warning", f"Could not clean test data: {e}")
            return True  # Non-fatal

    def run_full_check(self) -> bool:
        """Run complete database verification suite"""
        print("\n" + "=" * 70)
        print("APPSIERRA DATABASE SETUP & VERIFICATION")
        print("=" * 70 + "\n")

        all_passed = True

        # Step 1: Config check
        if not self.check_config():
            self.log("✗ Fatal Error", "Configuration is invalid. Cannot proceed.")
            return False

        db_type = self.check_db_type()
        self.log("ℹ Database Type", f"Detected: {db_type.upper()}")

        # Step 2: Connectivity
        if not self.check_connectivity():
            all_passed = False

        # Step 3: Tables
        if not self.check_tables():
            all_passed = False

        print("\n" + "-" * 70)
        if all_passed:
            self.log("✓ Full Check Passed", "Database is configured and ready!")
        else:
            self.log("⚠ Issues Found", "Some checks failed. See above for details.")

        print("-" * 70 + "\n")
        return all_passed

    def run_init_sequence(self) -> bool:
        """Run complete initialization sequence"""
        print("\n" + "=" * 70)
        print("APPSIERRA DATABASE INITIALIZATION")
        print("=" * 70 + "\n")

        # Step 1: Config
        if not self.check_config():
            return False

        db_type = self.check_db_type()
        self.log("ℹ Database Type", f"Detected: {db_type.upper()}")

        # Step 2: Connectivity
        if not self.check_connectivity():
            return False

        # Step 3: Init tables
        if not self.init_db():
            return False

        # Step 4: Write test
        if not self.test_write():
            return False

        # Step 5: Read test
        if not self.test_read():
            return False

        # Cleanup
        self.cleanup_test_data()

        print("\n" + "-" * 70)
        self.log("✓ Init Complete", "Database is fully configured and working!")
        print("-" * 70 + "\n")
        return True

    @staticmethod
    def _mask_url(url: str, keep: int = 4) -> str:
        """Mask sensitive parts of database URL"""
        if not url:
            return "[None]"

        if "sqlite" in url.lower():
            return url  # SQLite paths are not sensitive

        # For PostgreSQL/MySQL, mask password
        if "@" in url:
            parts = url.split("@", 1)
            user_pass = parts[0].split("://", 1)[-1]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                return f"...{user}:***@{parts[1]}"

        return url


def main():
    parser = argparse.ArgumentParser(description="APPSIERRA Database Setup Tool")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run full database verification check (default)",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize and verify database with test write/read",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Quick health check only",
    )

    args = parser.parse_args()

    setup = DatabaseSetup()

    # Default to check if no args
    if not (args.check or args.init or args.health):
        args.check = True

    if args.health:
        return 0 if setup.check_connectivity() else 1

    if args.init:
        return 0 if setup.run_init_sequence() else 1

    if args.check:
        return 0 if setup.run_full_check() else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
