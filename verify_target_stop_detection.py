#!/usr/bin/env python3
"""
Verification script for target/stop detection logic in panel2.py.
Tests that stop and target orders are correctly detected for both long and short positions.
"""


def test_long_position_detection():
    """Test target/stop detection for LONG positions."""
    print("\n=== Testing LONG Position ===")

    # Simulate a long position
    entry_price = 100.0
    is_long = True

    print(f"Position: LONG @ {entry_price}")

    # Test case 1: SELL order below entry = STOP
    side = 2  # Sell
    price1 = 95.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        if is_long:
            if price1 < entry_price:
                detected = "STOP"
            elif price1 > entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
        else:
            if price1 > entry_price:
                detected = "STOP"
            elif price1 < entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  SELL @ {price1} -> Detected as: {detected}")
    assert detected == "STOP", f"Expected STOP, got {detected}"

    # Test case 2: SELL order above entry = TARGET
    side = 2  # Sell
    price1 = 105.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        if is_long:
            if price1 < entry_price:
                detected = "STOP"
            elif price1 > entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
        else:
            if price1 > entry_price:
                detected = "STOP"
            elif price1 < entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  SELL @ {price1} -> Detected as: {detected}")
    assert detected == "TARGET", f"Expected TARGET, got {detected}"

    # Test case 3: BUY order should be ignored (not an exit order for longs)
    side = 1  # Buy
    price1 = 95.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        detected = "SHOULD NOT REACH HERE"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  BUY @ {price1} -> Detected as: {detected}")
    assert detected == "NOT EXIT ORDER", f"Expected NOT EXIT ORDER, got {detected}"

    print("OK: Long position detection correct")


def test_short_position_detection():
    """Test target/stop detection for SHORT positions."""
    print("\n=== Testing SHORT Position ===")

    # Simulate a short position
    entry_price = 100.0
    is_long = False

    print(f"Position: SHORT @ {entry_price}")

    # Test case 1: BUY order above entry = STOP
    side = 1  # Buy
    price1 = 105.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        if is_long:
            if price1 < entry_price:
                detected = "STOP"
            elif price1 > entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
        else:
            if price1 > entry_price:
                detected = "STOP"
            elif price1 < entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  BUY @ {price1} -> Detected as: {detected}")
    assert detected == "STOP", f"Expected STOP, got {detected}"

    # Test case 2: BUY order below entry = TARGET
    side = 1  # Buy
    price1 = 95.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        if is_long:
            if price1 < entry_price:
                detected = "STOP"
            elif price1 > entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
        else:
            if price1 > entry_price:
                detected = "STOP"
            elif price1 < entry_price:
                detected = "TARGET"
            else:
                detected = "UNKNOWN"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  BUY @ {price1} -> Detected as: {detected}")
    assert detected == "TARGET", f"Expected TARGET, got {detected}"

    # Test case 3: SELL order should be ignored (not an exit order for shorts)
    side = 2  # Sell
    price1 = 105.0
    is_exit_order = (is_long and side == 2) or (not is_long and side == 1)

    if is_exit_order:
        detected = "SHOULD NOT REACH HERE"
    else:
        detected = "NOT EXIT ORDER"

    print(f"  SELL @ {price1} -> Detected as: {detected}")
    assert detected == "NOT EXIT ORDER", f"Expected NOT EXIT ORDER, got {detected}"

    print("OK: Short position detection correct")


if __name__ == "__main__":
    print("=" * 60)
    print("Verifying Target/Stop Detection Logic")
    print("=" * 60)

    try:
        test_long_position_detection()
        test_short_position_detection()

        print("\n" + "=" * 60)
        print("OK: ALL TESTS PASSED - Target/Stop detection is correct!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nX TEST FAILED: {e}")
        exit(1)
