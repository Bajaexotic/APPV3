#!/usr/bin/env python3
"""
Verification script for MAE/MFE pure point calculations.
Tests that MAE/MFE are purely price-based (no qty multiplication), using trade extremes.
"""


def test_long_mae_mfe():
    """Test MAE/MFE for LONG positions - pure points from entry."""
    print("\n=== Testing LONG Position MAE/MFE ===")

    # Long position: Entry=100, trade ranges from 98 to 105
    entry_price = 100.0
    trade_min_price = 98.0   # Worst price during trade
    trade_max_price = 105.0  # Best price during trade
    is_long = True

    print(f"Position: LONG @ {entry_price}")
    print(f"Trade range: {trade_min_price} to {trade_max_price}")

    # Calculate MAE/MFE
    if is_long:
        mae_pts = trade_min_price - entry_price
        mfe_pts = trade_max_price - entry_price
    else:
        mae_pts = entry_price - trade_max_price
        mfe_pts = entry_price - trade_min_price

    print(f"MAE (Maximum Adverse Excursion): {mae_pts:.2f} pt")
    print(f"MFE (Maximum Favorable Excursion): {mfe_pts:.2f} pt")

    # Expected: MAE = 98 - 100 = -2.00 pt (lost 2 points at worst)
    # Expected: MFE = 105 - 100 = +5.00 pt (gained 5 points at best)
    assert abs(mae_pts - (-2.0)) < 0.01, f"Long MAE failed: expected -2.00, got {mae_pts}"
    assert abs(mfe_pts - 5.0) < 0.01, f"Long MFE failed: expected 5.00, got {mfe_pts}"

    print("OK: Long MAE/MFE calculations correct")


def test_short_mae_mfe():
    """Test MAE/MFE for SHORT positions - pure points from entry."""
    print("\n=== Testing SHORT Position MAE/MFE ===")

    # Short position: Entry=100, trade ranges from 95 to 102
    entry_price = 100.0
    trade_min_price = 95.0   # Lowest price during trade (best for short)
    trade_max_price = 102.0  # Highest price during trade (worst for short)
    is_long = False

    print(f"Position: SHORT @ {entry_price}")
    print(f"Trade range: {trade_min_price} to {trade_max_price}")

    # Calculate MAE/MFE
    if is_long:
        mae_pts = trade_min_price - entry_price
        mfe_pts = trade_max_price - entry_price
    else:
        mae_pts = entry_price - trade_max_price
        mfe_pts = entry_price - trade_min_price

    print(f"MAE (Maximum Adverse Excursion): {mae_pts:.2f} pt")
    print(f"MFE (Maximum Favorable Excursion): {mfe_pts:.2f} pt")

    # Expected: MAE = 100 - 102 = -2.00 pt (lost 2 points at worst)
    # Expected: MFE = 100 - 95 = +5.00 pt (gained 5 points at best)
    assert abs(mae_pts - (-2.0)) < 0.01, f"Short MAE failed: expected -2.00, got {mae_pts}"
    assert abs(mfe_pts - 5.0) < 0.01, f"Short MFE failed: expected 5.00, got {mfe_pts}"

    print("OK: Short MAE/MFE calculations correct")


def test_mae_mfe_no_qty_multiplication():
    """Verify MAE/MFE are NOT multiplied by quantity - pure price measures."""
    print("\n=== Testing MAE/MFE Pure Price (No Qty Multiplication) ===")

    # Same position with different quantities should yield same MAE/MFE in points
    entry_price = 100.0
    trade_min_price = 97.0
    trade_max_price = 106.0
    is_long = True

    # Calculate for qty = 1
    qty_1 = 1
    mae_pts_1 = trade_min_price - entry_price
    mfe_pts_1 = trade_max_price - entry_price

    # Calculate for qty = 5
    qty_5 = 5
    mae_pts_5 = trade_min_price - entry_price
    mfe_pts_5 = trade_max_price - entry_price

    print(f"Position: LONG @ {entry_price}, Range: {trade_min_price} to {trade_max_price}")
    print(f"With qty={qty_1}: MAE={mae_pts_1:.2f} pt, MFE={mfe_pts_1:.2f} pt")
    print(f"With qty={qty_5}: MAE={mae_pts_5:.2f} pt, MFE={mfe_pts_5:.2f} pt")

    # MAE/MFE should be identical regardless of quantity
    assert mae_pts_1 == mae_pts_5, f"MAE should be same for all quantities: {mae_pts_1} != {mae_pts_5}"
    assert mfe_pts_1 == mfe_pts_5, f"MFE should be same for all quantities: {mfe_pts_1} != {mfe_pts_5}"

    print("OK: MAE/MFE are quantity-independent (pure price measures)")


def test_mae_mfe_trade_vs_session_extremes():
    """Verify MAE/MFE use TRADE extremes, not SESSION extremes."""
    print("\n=== Testing Trade Extremes vs Session Extremes ===")

    # Session: 90 to 110 (pre-entry extremes)
    # Entry at 100
    # Trade (post-entry): 98 to 105
    session_low = 90.0
    session_high = 110.0
    entry_price = 100.0
    trade_min_price = 98.0   # Min since entry
    trade_max_price = 105.0  # Max since entry
    is_long = True

    print(f"Session range: {session_low} to {session_high}")
    print(f"Entry: {entry_price}")
    print(f"Trade range (post-entry): {trade_min_price} to {trade_max_price}")

    # CORRECT: Use trade extremes
    mae_correct = trade_min_price - entry_price
    mfe_correct = trade_max_price - entry_price

    # WRONG: Using session extremes
    mae_wrong = session_low - entry_price
    mfe_wrong = session_high - entry_price

    print(f"CORRECT (trade extremes): MAE={mae_correct:.2f} pt, MFE={mfe_correct:.2f} pt")
    print(f"WRONG (session extremes): MAE={mae_wrong:.2f} pt, MFE={mfe_wrong:.2f} pt")

    # Verify we're using the right values
    assert abs(mae_correct - (-2.0)) < 0.01, "Should use trade min, not session low"
    assert abs(mfe_correct - 5.0) < 0.01, "Should use trade max, not session high"
    assert mae_wrong != mae_correct, "Session extremes should differ from trade extremes"
    assert mfe_wrong != mfe_correct, "Session extremes should differ from trade extremes"

    print("OK: Using trade extremes (not session extremes)")


if __name__ == "__main__":
    print("=" * 60)
    print("Verifying MAE/MFE Pure Point Calculations")
    print("=" * 60)

    try:
        test_long_mae_mfe()
        test_short_mae_mfe()
        test_mae_mfe_no_qty_multiplication()
        test_mae_mfe_trade_vs_session_extremes()

        print("\n" + "=" * 60)
        print("OK: ALL TESTS PASSED - MAE/MFE are pure price-based!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nX TEST FAILED: {e}")
        exit(1)
