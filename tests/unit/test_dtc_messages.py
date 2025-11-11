#!/usr/bin/env python3
"""
DTC Message Type Verification Test Suite

Usage:
    python test_dtc_messages.py [--timeout 30]

This script runs APPSIERRA and captures all incoming DTC message types,
verifying that the handshake, routing, and message handlers are working correctly.

Expected Output After Patches:
    - Type 2 (LogonResponse) ✓
    - Type 308/401 (Account) ✓
    - Type 306 (Positions) ✓
    - Type 600 (Balance) ✓
    - Type 301 (Orders) - only if active orders exist
"""

from collections import defaultdict
import os
import subprocess
import sys
import time


def run_test(timeout_sec=30):
    """Run the app and capture all message types"""

    print("=" * 80)
    print("DTC MESSAGE TYPE VERIFICATION TEST")
    print("=" * 80)
    print(f"\nRunning app for {timeout_sec} seconds with DEBUG_DTC=1...")
    print("(Place an order in Sierra Chart during this time to test Type 301)\n")

    # Set environment variable for detailed logging
    env = os.environ.copy()
    env["DEBUG_DTC"] = "1"

    try:
        # Run the app with timeout
        result = subprocess.run(["python", "main.py"], capture_output=True, text=True, timeout=timeout_sec, env=env)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        # Expected - we're timing out intentionally
        output = ""
    except Exception as e:
        print(f"ERROR: Failed to run app: {e}")
        return False

    # Parse message types from output
    message_types = defaultdict(int)
    router_events = []

    for line in output.split("\n"):
        # Look for [DTC-ALL-TYPES] lines
        if "[DTC-ALL-TYPES]" in line:
            # Extract Type number
            try:
                parts = line.split("Type: ")
                if len(parts) > 1:
                    type_num = int(parts[1].split()[0])
                    message_types[type_num] += 1
            except Exception:
                pass

        # Look for router events
        if "[debug    ] router." in line:
            if "balance" in line:
                router_events.append("BALANCE_UPDATE (Type 600)")
            elif "position" in line:
                router_events.append("POSITION_UPDATE (Type 306)")
            elif "order" in line:
                router_events.append("ORDER_UPDATE (Type 301)")
            elif "trade_account" in line:
                router_events.append("TRADE_ACCOUNT (Type 308/401)")

    # Display results
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    print("\n1. MESSAGE TYPES RECEIVED (via DEBUG_DTC):")
    print("-" * 80)

    if message_types:
        for msg_type in sorted(message_types.keys()):
            count = message_types[msg_type]
            type_names = {
                2: "LogonResponse",
                308: "TradeAccountResponse (variant)",
                401: "TradeAccountResponse",
                306: "PositionUpdate",
                600: "AccountBalanceUpdate",
                301: "OrderUpdate",
                501: "MktDataResponse",
            }
            type_name = type_names.get(msg_type, f"Type {msg_type}")
            print(f"  ✓ Type {msg_type:3d} ({type_name:30s}): {count:5d} messages")
    else:
        print("  ✗ NO MESSAGE TYPES FOUND - Check if app is running")

    print("\n2. ROUTED EVENTS (via message_router):")
    print("-" * 80)

    if router_events:
        unique_events = {}
        for event in router_events:
            unique_events[event] = unique_events.get(event, 0) + 1
        for event in sorted(unique_events.keys()):
            count = unique_events[event]
            print(f"  ✓ {event:40s}: {count:5d} events")
    else:
        print("  ✗ NO ROUTER EVENTS - Check message_router.py")

    # Verification checklist
    print("\n3. VERIFICATION CHECKLIST:")
    print("-" * 80)

    checks = {
        "LogonResponse received (Type 2)": 2 in message_types,
        "Account info received (Type 308/401)": (308 in message_types or 401 in message_types),
        "Positions received (Type 306)": 306 in message_types,
        "Balance received (Type 600)": 600 in message_types,
        "Order updates received (Type 301)": 301 in message_types,
        "Router processing TRADE_ACCOUNT": "TRADE_ACCOUNT" in router_events,
        "Router processing POSITION_UPDATE": "POSITION_UPDATE" in router_events,
        "Router processing BALANCE_UPDATE": "BALANCE_UPDATE" in router_events,
    }

    all_passed = True
    for check, passed in checks.items():
        status = "✅ PASS" if passed else "⚠️  FAIL"
        print(f"  [{status}] {check}")
        if not passed and "Type 301" not in check:  # Type 301 is optional (no active orders)
            all_passed = False

    # Special note for Type 301
    if 301 not in message_types:
        print("\n  ⓘ NOTE: Type 301 (OrderUpdate) not received - this is normal if:")
        print("    - You have no active orders placed")
        print("    - Place an order in Sierra Chart and run test again")
        print("    - After Patch 3, app now requests: OrderUpdatesAsConnectionDefault: 1")

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    critical_checks = [
        (2, "LogonResponse"),
        (306, "PositionUpdate"),
        (600, "AccountBalanceUpdate"),
    ]

    critical_passed = all(msg_type in message_types for msg_type, _ in critical_checks)

    if critical_passed:
        print("\n✅ ALL CRITICAL MESSAGE TYPES RECEIVED")
        print("\nApp is correctly:")
        print("  • Connecting to Sierra DTC server")
        print("  • Receiving account information")
        print("  • Receiving position updates")
        print("  • Receiving account balance")
        if 301 in message_types:
            print("  • Receiving order updates (Type 301)")
        else:
            print("  • Ready to receive order updates (Type 301) when orders are placed")
    else:
        print("\n⚠️  SOME CRITICAL MESSAGE TYPES MISSING")
        print("\nPlease verify:")
        print("  • Sierra Chart DTC server is running")
        print("  • DTC server is in JSON/Compact mode (not Binary)")
        print("  • Connection string is correct (127.0.0.1:11099)")
        all_passed = False

    print("\n" + "=" * 80 + "\n")
    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test DTC message reception in APPSIERRA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_dtc_messages.py              # Default 30 seconds
  python test_dtc_messages.py --timeout 60 # 60 second test
  DEBUG_DTC=1 python test_dtc_messages.py  # With debug output
        """,
    )

    parser.add_argument("--timeout", type=int, default=30, help="Test duration in seconds (default: 30)")

    args = parser.parse_args()

    try:
        success = run_test(args.timeout)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        sys.exit(1)
