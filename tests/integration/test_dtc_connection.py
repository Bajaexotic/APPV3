#!/usr/bin/env python3
"""
Minimal DTC connection test - uses dtc_test_framework for clean implementation.
Tests TCP connection, handshake, and account balance request.
"""

import sys


# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from config.settings import LIVE_ACCOUNT
from services.dtc_constants import ACCOUNT_BALANCE_UPDATE
from services.dtc_protocol import build_account_balance_request
from tools.dtc_test_framework import DTCTestConnection


def test_connection():
    """Run comprehensive DTC connection test."""
    print("=" * 80)
    print("MINIMAL DTC CONNECTION TEST")
    print("=" * 80)

    try:
        with DTCTestConnection() as conn:
            # Test 1: TCP connection (handled by context manager)
            print("\n[1] TCP Connection")
            print("   [✓] TCP connection successful!")

            # Test 2: Logon handshake (handled by context manager)
            print("\n[2] Logon Handshake")
            if conn.logged_in:
                print("   [✓] Logon successful!")
            else:
                print("   [✗] Logon failed")
                return False

            # Test 3: Request account balance
            print(f"\n[3] Requesting account balance for {LIVE_ACCOUNT}...")
            balance_req = build_account_balance_request(
                trade_account=LIVE_ACCOUNT,
                request_id=1,
            )

            if not conn.send_message(balance_req):
                print("   [✗] Failed to send balance request")
                return False

            print("   [✓] Balance request sent")

            # Test 4: Wait for balance response
            print("\n[4] Waiting for ACCOUNT_BALANCE_UPDATE...")

            # Receive messages for up to 10 seconds, looking for balance update
            messages = conn.receive_messages(
                duration=10.0,
                filter_fn=lambda msg: msg.get("Type") == ACCOUNT_BALANCE_UPDATE,
            )

            if not messages:
                print("   [✗] No balance response received")
                print("   [HINT] Check if account is correct and active")
                return False

            # Found balance response
            balance_msg = messages[0]
            print("   [✓] Balance received:")

            # Display balance fields
            balance_fields = [
                "CashBalance",
                "AccountValue",
                "BalanceAvailableForNewPositions",
                "NetLiquidatingValue",
                "MarginRequirement",
            ]

            for key in balance_fields:
                if key in balance_msg:
                    value = balance_msg[key]
                    if isinstance(value, (int, float)):
                        print(f"      {key}: ${value:,.2f}")
                    else:
                        print(f"      {key}: {value}")

            return True

    except ConnectionRefusedError:
        print("\n[✗] Connection refused - DTC server not running")
        print("\n[SOLUTION]:")
        print("   1. Open Sierra Chart")
        print("   2. Go to: Global Settings > Data/Trade Service Settings")
        print("   3. Enable 'DTC Protocol Server'")
        print("   4. Set Port to 11099")
        print("   5. Click 'OK' and restart Sierra Chart if needed")
        return False

    except Exception as e:
        print(f"\n[✗] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()

    print("\n" + "=" * 80)
    if success:
        print("[SUCCESS] ALL TESTS PASSED - DTC connection working!")
    else:
        print("[FAIL] TESTS FAILED - See errors above")
    print("=" * 80)

    sys.exit(0 if success else 1)
