#!/usr/bin/env python
"""
APPSIERRA Live-Data Propagation Diagnostic
Identifies where DTC messages stop flowing through the pipeline
"""

import os
import subprocess
import sys
import time


def run_test(test_name, command, timeout=10, expected_patterns=None):
    """Run a diagnostic test and report results"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr

        if expected_patterns:
            found = []
            for pattern in expected_patterns:
                if pattern.lower() in output.lower():
                    found.append(pattern)

            if found:
                print(f"[FOUND] {', '.join(found)}")
                for line in output.split("\n"):
                    if any(p.lower() in line.lower() for p in expected_patterns):
                        print(f"  {line[:100]}")
            else:
                print(f"[NOT FOUND] Expected: {expected_patterns}")
        else:
            print(output[:500])

        return output

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Test timed out after {timeout} seconds")
        return ""
    except Exception as e:
        print(f"[ERROR] {e}")
        return ""


def main():
    print("\n" + "=" * 80)
    print("APPSIERRA LIVE-DATA PROPAGATION DIAGNOSTIC")
    print("=" * 80)

    # Test 1: Connection
    print("\n[STEP 1] Checking TCP connection to DTC server...")
    run_test(
        "DTC Connection",
        "export DEBUG_NETWORK=1 && timeout 5 python main.py",
        timeout=6,
        expected_patterns=["dtc.tcp.connected", "Connected"],
    )

    # Test 2: Heartbeats
    print("\n[STEP 2] Checking for DTC heartbeats (Type 3)...")
    run_test(
        "DTC Heartbeats", "export DEBUG_NETWORK=1 && timeout 5 python main.py", timeout=6, expected_patterns=["Type: 3"]
    )

    # Test 3: Encoding check
    print("\n[STEP 3] Checking for encoding issues...")
    output = run_test(
        "Encoding Verification",
        "export DEBUG_DATA=1 && timeout 5 python main.py",
        timeout=6,
        expected_patterns=["encoding.mismatch"],
    )

    if "encoding.mismatch" in output.lower():
        print("\n" + "!" * 80)
        print("PROBLEM IDENTIFIED: Sierra is in BINARY mode, not JSON")
        print("!" * 80)
        print("\nFIX:")
        print("  1. Open Sierra Chart")
        print("  2. Global Settings > Data/Trade Service Settings")
        print("  3. DTC Protocol Server > Set to JSON/Compact Encoding")
        print("  4. Restart Sierra")
        print("  5. Run this diagnostic again")
        return

    # Test 4: Balance messages
    print("\n[STEP 4] Checking for balance updates (Type 600)...")
    output = run_test(
        "Balance Messages",
        "export DEBUG_DATA=1 && timeout 10 python main.py",
        timeout=11,
        expected_patterns=["Type: 600", "BALANCE"],
    )

    if "Type: 600" not in output:
        print("\n" + "!" * 80)
        print("PROBLEM: Sierra not sending balance updates (Type 600)")
        print("!" * 80)
        print("\nPossible causes:")
        print("  1. DTC server not enabled in Sierra")
        print("  2. Trading account not active")
        print("  3. No subscriptions to balance updates")
        print("\nFIX:")
        print("  1. Verify trading account in Sierra")
        print("  2. Check Global Settings > Data/Trade Service")
        print("  3. Ensure DTC Protocol Server is enabled")
        return

    # Test 5: Order messages
    print("\n[STEP 5] Checking for order updates (Type 301)...")
    run_test(
        "Order Messages",
        "export DEBUG_DATA=1 && timeout 10 python main.py",
        timeout=11,
        expected_patterns=["Type: 301", "OrderUpdate"],
    )

    # Test 6: Position messages
    print("\n[STEP 6] Checking for position updates (Type 306)...")
    run_test(
        "Position Messages",
        "export DEBUG_DATA=1 && timeout 10 python main.py",
        timeout=11,
        expected_patterns=["Type: 306", "Position"],
    )

    # Test 7: Signal emission
    print("\n[STEP 7] Checking signal propagation...")
    output = run_test(
        "Signal Emission",
        "export DEBUG_DATA=1 && timeout 10 python main.py",
        timeout=11,
        expected_patterns=["signal", "SENDING", "RECEIVED"],
    )

    # Final summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)

    if "Type: 600" in output:
        print("\n✓ Sierra is sending balance messages")
        print("✓ Data is arriving at socket layer")

        if "signal" in output.lower():
            print("✓ Signals are being emitted")
            print("\n→ Data flow is working through app_manager layer")
            print("→ Check panel implementation if UI still not updating")
        else:
            print("✗ Signals not being emitted")
            print("\n→ Issue is in data_bridge or app_manager")
    else:
        print("\n✗ Sierra not sending messages")
        print("→ Check Sierra DTC server configuration")

    print("\nFor detailed analysis, see: LIVE_DATA_PROPAGATION_REPORT.md")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
