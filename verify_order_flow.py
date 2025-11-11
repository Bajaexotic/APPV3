#!/usr/bin/env python3
"""
Direct verification: Does your app receive Type 301 (OrderUpdate) fills?

Usage:
    1. python verify_order_flow.py &          # Start in background
    2. Place an order in Sierra Chart (on account 120005)
    3. Watch the terminal output
    4. See if Type 301 appears

This script monitors for OrderUpdate messages (Type 301) in real-time.
"""

from datetime import datetime
import subprocess
import sys
import time


def monitor_order_fills(duration_sec=60):
    """Monitor for Type 301 (OrderUpdate) messages"""

    print("=" * 80)
    print("ORDER FLOW VERIFICATION - LIVE MONITOR")
    print("=" * 80)
    print(f"\nWatching for Type 301 (OrderUpdate) messages for {duration_sec} seconds...\n")
    print("INSTRUCTIONS:")
    print("  1. This script is running and watching logs")
    print("  2. Go to Sierra Chart")
    print("  3. Place an order on account 120005")
    print("  4. Watch below for Type 301 to appear")
    print("  5. Order fills should show OrderStatus 3 with FilledQuantity\n")
    print("-" * 80 + "\n")

    # Run the app and capture output
    env = {"DEBUG_DTC": "1"}
    try:
        proc = subprocess.Popen(
            ["python", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**__import__("os").environ, **env},
        )

        start_time = time.time()
        order_updates_found = []

        # Monitor output
        for line in proc.stdout:
            elapsed = time.time() - start_time

            # Look for order-related messages
            if "Type: 301" in line or "OrderUpdate" in line or "router.order" in line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] ✅ ORDER DETECTED: {line.strip()[:100]}")
                order_updates_found.append(line.strip())

            # Show other Type messages for context
            elif "[DTC-ALL-TYPES]" in line and "Type:" in line:
                # Extract just the type number
                try:
                    msg_type = line.split("Type: ")[1].split()[0]
                    if msg_type not in ("3", "501"):  # Skip heartbeats
                        print(
                            f"[{timestamp}] Type: {msg_type} {line.split('(')[1].split(')')[0] if '(' in line else ''}"
                        )
                except:
                    pass

            # Check timeout
            if elapsed > duration_sec:
                break

            # Show progress every 10 seconds
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Still watching... ({int(elapsed)}s elapsed)")

        proc.terminate()

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Monitoring stopped by user")
        proc.terminate()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

    # Results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if order_updates_found:
        print(f"\n✅ SUCCESS: Found {len(order_updates_found)} OrderUpdate message(s)\n")
        print("Your app IS receiving Type 301 (OrderUpdate) fills!")
        print("\nMessages received:")
        for msg in order_updates_found[:5]:  # Show first 5
            print(f"  {msg}")
        if len(order_updates_found) > 5:
            print(f"  ... and {len(order_updates_found) - 5} more")
        print("\n✅ Order flow is working correctly")
        return True
    else:
        print("\n⚠️  NO OrderUpdate messages found\n")
        print("Possible reasons:")
        print("  1. You didn't place an order during the monitoring window")
        print("  2. Order was placed but didn't fill")
        print("  3. Order was placed on different account (not 120005)")
        print("  4. Sierra Chart DTC in wrong mode")
        print("\nNext steps:")
        print("  - Verify trading on account: 120005")
        print("  - Check Sierra Chart DTC settings: Global Settings > Data/Trade Service")
        print("  - Try again with a MARKET order (should fill instantly)")
        return False


if __name__ == "__main__":
    try:
        success = monitor_order_fills(duration_sec=60)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
