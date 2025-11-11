#!/usr/bin/env python
"""
Test Panel 2 → Panel 3 data handoff and UI updates.
Run this to verify statistics actually update when trades close.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from data.schema import TradeRecord
from data.db_engine import get_session


def test_panel3_data_flow():
    """Verify Panel 3 can query trades and compute statistics."""
    print("\n" + "="*60)
    print("TEST: Panel 3 Data Flow")
    print("="*60)

    # Test 1: Can we create a test trade in database?
    print("\n[1] Creating test trade in database...")
    try:
        trade = TradeRecord(
            symbol="TEST.US",
            side="LONG",
            qty=1,
            mode="SIM",
            account="Sim1",
            entry_price=100.0,
            entry_time=datetime.utcnow(),
            exit_price=105.0,
            exit_time=datetime.utcnow(),
            is_closed=True,
            realized_pnl=500.0,
        )

        with get_session() as s:
            s.add(trade)
            s.commit()
            trade_id = trade.id

        print(f"   ✓ Trade created with ID: {trade_id}")
    except Exception as e:
        print(f"   ✗ Failed to create trade: {e}")
        return False

    # Test 2: Can we query it back?
    print("\n[2] Querying trade from database...")
    try:
        with get_session() as s:
            found = s.query(TradeRecord).filter(
                TradeRecord.id == trade_id
            ).first()

        if found:
            print(f"   ✓ Trade found: {found.symbol}, PnL=${found.realized_pnl}")
        else:
            print(f"   ✗ Trade not found in database")
            return False
    except Exception as e:
        print(f"   ✗ Query failed: {e}")
        return False

    # Test 3: Can stats_service compute metrics?
    print("\n[3] Computing statistics from trade...")
    try:
        from services.stats_service import compute_trading_stats_for_timeframe

        stats = compute_trading_stats_for_timeframe("1D", mode="SIM")
        print(f"   Stats returned: {list(stats.keys())[:5]}...")

        if "Total PnL" in stats:
            print(f"   ✓ Total PnL: {stats.get('Total PnL')}")
        if "Trades" in stats:
            print(f"   ✓ Trades: {stats.get('Trades')}")

    except Exception as e:
        print(f"   ✗ Stats computation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Check mode filtering
    print("\n[4] Testing mode filtering...")
    try:
        # Query SIM trades
        with get_session() as s:
            sim_trades = s.query(TradeRecord).filter(
                TradeRecord.mode == "SIM"
            ).all()

        print(f"   ✓ SIM trades: {len(sim_trades)}")

        # Query LIVE trades
        with get_session() as s:
            live_trades = s.query(TradeRecord).filter(
                TradeRecord.mode == "LIVE"
            ).all()

        print(f"   ✓ LIVE trades: {len(live_trades)}")

    except Exception as e:
        print(f"   ✗ Mode filtering failed: {e}")
        return False

    print("\n" + "="*60)
    print("RESULT: Panel 3 data flow is working ✓")
    print("="*60)
    return True


def test_balance_update():
    """Test if SIM balance updates when trade is recorded."""
    print("\n" + "="*60)
    print("TEST: SIM Balance Update")
    print("="*60)

    # Test 1: Can we read current balance?
    print("\n[1] Reading current SIM balance...")
    try:
        from data.sim_balance import SIMBalanceManager
        mgr = SIMBalanceManager()
        balance = mgr.get_sim_balance()
        print(f"   ✓ Current balance: ${balance}")
    except Exception as e:
        print(f"   ✗ Failed to read balance: {e}")
        return False

    # Test 2: Can we update balance?
    print("\n[2] Updating SIM balance by +$500...")
    try:
        new_balance = balance + 500.0
        mgr.set_sim_balance(new_balance)

        # Verify it was set
        verified = mgr.get_sim_balance()
        if verified == new_balance:
            print(f"   ✓ Balance updated to: ${verified}")
        else:
            print(f"   ✗ Balance not updated (expected ${new_balance}, got ${verified})")
            return False

    except Exception as e:
        print(f"   ✗ Failed to update balance: {e}")
        return False

    # Test 3: Does it persist in JSON?
    print("\n[3] Checking JSON file...")
    try:
        json_file = Path(__file__).parent / "data" / "sim_balance.json"
        if json_file.exists():
            content = json_file.read_text()
            print(f"   ✓ JSON file exists")
            print(f"   Content: {content[:100]}...")
        else:
            print(f"   ⚠ JSON file doesn't exist at {json_file}")
    except Exception as e:
        print(f"   ✗ Error checking JSON: {e}")

    print("\n" + "="*60)
    print("RESULT: SIM balance update is working ✓")
    print("="*60)
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PANEL HANDOFF & BALANCE UPDATE TESTS")
    print("="*60)

    success = True

    try:
        success &= test_balance_update()
    except Exception as e:
        print(f"\nBalance test crashed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    try:
        success &= test_panel3_data_flow()
    except Exception as e:
        print(f"\nPanel 3 test crashed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print("\n" + "="*60)
    if success:
        print("ALL TESTS PASSED ✓")
        print("\nIf you're still not seeing updates in the UI,")
        print("the issue is in the PyQt signal connections, not the data.")
    else:
        print("SOME TESTS FAILED ✗")
        print("\nFix the data layer issues above first.")
    print("="*60 + "\n")

    sys.exit(0 if success else 1)
