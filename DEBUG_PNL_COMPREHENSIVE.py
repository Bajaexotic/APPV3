#!/usr/bin/env python3
"""
COMPREHENSIVE PNL DEBUGGING SCRIPT
Traces PnL calculations through the entire system
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.db_engine import get_session
from data.schema import TradeRecord
from services.stats_service import compute_trading_stats_for_timeframe
from core.state_manager import StateManager
from sqlalchemy import func

UTC = timezone.utc

def separator(title: str) -> None:
    print(f"\n{'='*100}")
    print(f" {title}")
    print(f"{'='*100}\n")

def debug_database() -> None:
    """Check what trades exist in the database"""
    separator("1. DATABASE STATE")

    try:
        with get_session() as session:
            total_count = session.query(TradeRecord).count()
            print(f" Total trades in database: {total_count}")

            if total_count > 0:
                # Get all trades
                trades = session.query(TradeRecord).order_by(TradeRecord.id.desc()).limit(10)
                print(f"\n Last 10 trades:")
                for trade in trades:
                    print(f"   ID={trade.id}: {trade.symbol} | Mode={trade.mode} | PnL=${trade.realized_pnl:+,.2f} | Exit={trade.exit_price} | Closed={trade.is_closed}")

                # Get total PnL by mode
                sim_pnl = session.query(func.sum(TradeRecord.realized_pnl)).filter(
                    TradeRecord.mode == "SIM",
                    TradeRecord.realized_pnl != None
                ).scalar() or 0.0

                live_pnl = session.query(func.sum(TradeRecord.realized_pnl)).filter(
                    TradeRecord.mode == "LIVE",
                    TradeRecord.realized_pnl != None
                ).scalar() or 0.0

                print(f"\n Total PnL by Mode:")
                print(f"   SIM:  ${sim_pnl:+,.2f}")
                print(f"   LIVE: ${live_pnl:+,.2f}")
            else:
                print(" No trades found in database!")

    except Exception as e:
        print(f" Database error: {e}")
        import traceback
        traceback.print_exc()

def debug_timeframe_pnl() -> None:
    """Check PnL calculation by timeframe"""
    separator("2. TIMEFRAME PNL CALCULATIONS")

    timeframes = ["1D", "1W", "1M", "3M", "YTD"]
    mode = "SIM"

    for tf in timeframes:
        print(f"\n Timeframe: {tf}")
        try:
            result = compute_trading_stats_for_timeframe(tf, mode)

            total_pnl = result.get("total_pnl", 0)
            trade_count = result.get("trade_count", 0)

            print(f"   Total PnL: ${total_pnl:+,.2f}")
            print(f"   Trade Count: {trade_count}")

            if trade_count > 0:
                print(f"   Hit Rate: {result.get('hit_rate', 0):.2f}%")
                print(f"   Max Drawdown: ${result.get('max_drawdown', 0):,.2f}")
                print(f"   Max Run-Up: ${result.get('max_runup', 0):,.2f}")
            else:
                print(f"    No trades in this timeframe")

        except Exception as e:
            print(f"    Error calculating {tf}: {e}")
            import traceback
            traceback.print_exc()

def debug_raw_queries() -> None:
    """Execute raw database queries to understand the data"""
    separator("3. RAW DATABASE QUERIES")

    now = datetime.now(UTC)

    ranges = {
        "LIVE (last 1 hour)": now - timedelta(hours=1),
        "1D (last day)": now - timedelta(days=1),
        "1W (last week)": now - timedelta(weeks=1),
        "1M (last month)": now - timedelta(days=30),
        "3M (last 3 months)": now - timedelta(days=90),
        "YTD (this year)": datetime(now.year, 1, 1, tzinfo=UTC),
    }

    try:
        with get_session() as session:
            for range_name, start_time in ranges.items():
                print(f"\n {range_name}")
                print(f"   Time range: {start_time.isoformat()}  {now.isoformat()}")

                trades = session.query(TradeRecord).filter(
                    TradeRecord.mode == "SIM",
                    TradeRecord.exit_time >= start_time,
                    TradeRecord.exit_time <= now,
                    TradeRecord.realized_pnl != None,
                    TradeRecord.is_closed == True
                ).order_by(TradeRecord.exit_time.desc()).all()

                if trades:
                    print(f"   Found: {len(trades)} trades")
                    total_pnl = sum(t.realized_pnl for t in trades)
                    print(f"   Total PnL: ${total_pnl:+,.2f}")

                    for trade in trades[:3]:  # Show first 3
                        print(f"       {trade.symbol}: ${trade.realized_pnl:+,.2f} @ {trade.exit_time}")
                else:
                    print(f"   Found: 0 trades")

    except Exception as e:
        print(f" Query error: {e}")
        import traceback
        traceback.print_exc()

def debug_state_manager() -> None:
    """Check state manager balance tracking"""
    separator("4. STATE MANAGER")

    try:
        state = StateManager()
        print(f" StateManager initialized")
        print(f"\n Current Balances:")
        print(f"   SIM:  ${state.sim_balance:,.2f}")
        print(f"   LIVE: ${state.live_balance:,.2f}")
        print(f"   Current Mode: {state.current_mode}")
        print(f"\n Position State:")
        print(f"   Positions: {state._positions}")

    except Exception as e:
        print(f" StateManager error: {e}")
        import traceback
        traceback.print_exc()

def debug_panel1_calculation() -> None:
    """Simulate what Panel1 should be doing"""
    separator("5. PANEL1 PNL CALCULATION SIMULATION")

    print("This simulates what Panel1._update_pnl_for_current_tf() should calculate:\n")

    now = datetime.now(UTC)

    # Simulate different timeframes
    timeframes = {
        "LIVE": (now - timedelta(hours=1), now),
        "1D": (datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=UTC), now),
        "1W": (now - timedelta(weeks=1), now),
        "1M": (now - timedelta(days=30), now),
        "YTD": (datetime(now.year, 1, 1, tzinfo=UTC), now),
    }

    try:
        with get_session() as session:
            for tf_name, (start_time, end_time) in timeframes.items():
                print(f"\n Timeframe: {tf_name}")

                trades = session.query(TradeRecord).filter(
                    TradeRecord.mode == "SIM",
                    TradeRecord.exit_time >= start_time,
                    TradeRecord.exit_time <= end_time,
                    TradeRecord.realized_pnl != None,
                    TradeRecord.is_closed == True
                ).all()

                if trades:
                    total_pnl = sum(t.realized_pnl for t in trades)
                    baseline = 10000.0  # Starting SIM balance
                    pnl_pct = (total_pnl / baseline) * 100.0

                    print(f"   Trades: {len(trades)}")
                    print(f"   Total PnL: ${total_pnl:+,.2f}")
                    print(f"   PnL %: {pnl_pct:+.2f}%")
                    print(f"   Direction: {' UP' if total_pnl > 0 else ' DOWN' if total_pnl < 0 else ' FLAT'}")
                    print(f"   Display: ${abs(total_pnl):,.2f} ({abs(pnl_pct):.2f}%)")
                else:
                    print(f"   Trades: 0")
                    print(f"   Total PnL: $0.00")
                    print(f"   PnL %: 0.00%")
                    print(f"   Display: $0.00 (0.00%)")

    except Exception as e:
        print(f" Panel1 simulation error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n[COMPREHENSIVE PNL DEBUGGING REPORT]")
    print(f"Generated: {datetime.now().isoformat()}\n")

    debug_database()
    debug_timeframe_pnl()
    debug_raw_queries()
    debug_state_manager()
    debug_panel1_calculation()

    separator("DEBUGGING COMPLETE")
    print(" Check output above for any  errors or  warnings\n")
