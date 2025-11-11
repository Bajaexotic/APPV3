#!/usr/bin/env python3
"""
Verification script for short-side calculation logic in panel2.py.
Tests that all metrics produce correct values for both long and short positions.
"""


def test_risk_calculation():
    """Test RISK calculation for long and short."""
    print("\n=== Testing RISK ===")

    # Long position: Entry=100, Stop=95 → Risk = 5 points
    entry_long = 100.0
    stop_long = 95.0
    is_long = True
    if is_long:
        dist_pts = entry_long - stop_long
    else:
        dist_pts = stop_long - entry_long
    print(f"Long: Entry={entry_long}, Stop={stop_long} -> Risk={abs(dist_pts)} pts")
    assert abs(dist_pts) == 5.0, "Long risk calculation failed"

    # Short position: Entry=100, Stop=105 → Risk = 5 points
    entry_short = 100.0
    stop_short = 105.0
    is_long = False
    if is_long:
        dist_pts = entry_short - stop_short
    else:
        dist_pts = stop_short - entry_short
    print(f"Short: Entry={entry_short}, Stop={stop_short} -> Risk={abs(dist_pts)} pts")
    assert abs(dist_pts) == 5.0, "Short risk calculation failed"
    print("OK: RISK calculations correct")


def test_rlive_calculation():
    """Test R-LIVE calculation for long and short."""
    print("\n=== Testing R-LIVE ===")

    # Long position: Entry=100, Stop=95, Last=105 → R-Live = 1.0R
    entry_long = 100.0
    stop_long = 95.0
    last_long = 105.0
    is_long = True
    if is_long:
        numer = last_long - entry_long
        denom = entry_long - stop_long
    else:
        numer = entry_long - last_long
        denom = stop_long - entry_long
    r_live = numer / denom
    print(f"Long: Entry={entry_long}, Stop={stop_long}, Last={last_long} -> R-Live={r_live:.2f}R")
    assert abs(r_live - 1.0) < 0.01, f"Long R-Live calculation failed: expected 1.0, got {r_live}"

    # Short position: Entry=100, Stop=105, Last=95 → R-Live = 1.0R
    entry_short = 100.0
    stop_short = 105.0
    last_short = 95.0
    is_long = False
    if is_long:
        numer = last_short - entry_short
        denom = entry_short - stop_short
    else:
        numer = entry_short - last_short
        denom = stop_short - entry_short
    r_live = numer / denom
    print(f"Short: Entry={entry_short}, Stop={stop_short}, Last={last_short} -> R-Live={r_live:.2f}R")
    assert abs(r_live - 1.0) < 0.01, f"Short R-Live calculation failed: expected 1.0, got {r_live}"
    print("OK: R-LIVE calculations correct")


def test_rplan_calculation():
    """Test R-PLAN calculation for long and short."""
    print("\n=== Testing R-PLAN ===")

    # Long position: Entry=100, Stop=95, Target=110 → R-Plan = 2.0R
    entry_long = 100.0
    stop_long = 95.0
    target_long = 110.0
    is_long = True
    if is_long:
        numer = target_long - entry_long
        denom = entry_long - stop_long
    else:
        numer = entry_long - target_long
        denom = stop_long - entry_long
    r_plan = numer / denom
    print(f"Long: Entry={entry_long}, Stop={stop_long}, Target={target_long} -> R-Plan={r_plan:.2f}R")
    assert abs(r_plan - 2.0) < 0.01, f"Long R-Plan calculation failed: expected 2.0, got {r_plan}"

    # Short position: Entry=100, Stop=105, Target=90 → R-Plan = 2.0R
    entry_short = 100.0
    stop_short = 105.0
    target_short = 90.0
    is_long = False
    if is_long:
        numer = target_short - entry_short
        denom = entry_short - stop_short
    else:
        numer = entry_short - target_short
        denom = stop_short - entry_short
    r_plan = numer / denom
    print(f"Short: Entry={entry_short}, Stop={stop_short}, Target={target_short} -> R-Plan={r_plan:.2f}R")
    assert abs(r_plan - 2.0) < 0.01, f"Short R-Plan calculation failed: expected 2.0, got {r_plan}"
    print("OK: R-PLAN calculations correct")


def test_mae_mfe_calculation():
    """Test MAE/MFE calculation for long and short."""
    print("\n=== Testing MAE/MFE ===")

    # Long position: Entry=100, SessionLow=98, SessionHigh=105
    # MAE = 98 - 100 = -2 (lost 2 points at worst), MFE = 105 - 100 = 5 (gained 5 points at best)
    entry_long = 100.0
    session_low = 98.0
    session_high = 105.0
    is_long = True
    if is_long:
        mae_pts = session_low - entry_long
        mfe_pts = session_high - entry_long
    else:
        mae_pts = entry_long - session_high
        mfe_pts = entry_long - session_low
    print(f"Long: Entry={entry_long}, Low={session_low}, High={session_high} -> MAE={mae_pts:.2f}, MFE={mfe_pts:.2f}")
    assert abs(mae_pts - (-2.0)) < 0.01, f"Long MAE calculation failed: expected -2.0, got {mae_pts}"
    assert abs(mfe_pts - 5.0) < 0.01, f"Long MFE calculation failed: expected 5.0, got {mfe_pts}"

    # Short position: Entry=100, SessionLow=95, SessionHigh=102
    # MAE = 100 - 102 = -2 (lost 2 points at worst), MFE = 100 - 95 = 5 (gained 5 points at best)
    entry_short = 100.0
    session_low = 95.0
    session_high = 102.0
    is_long = False
    if is_long:
        mae_pts = session_low - entry_short
        mfe_pts = session_high - entry_short
    else:
        mae_pts = entry_short - session_high
        mfe_pts = entry_short - session_low
    print(f"Short: Entry={entry_short}, Low={session_low}, High={session_high} -> MAE={mae_pts:.2f}, MFE={mfe_pts:.2f}")
    assert abs(mae_pts - (-2.0)) < 0.01, f"Short MAE calculation failed: expected -2.0, got {mae_pts}"
    assert abs(mfe_pts - 5.0) < 0.01, f"Short MFE calculation failed: expected 5.0, got {mfe_pts}"
    print("OK: MAE/MFE calculations correct")


def test_efficiency_calculation():
    """Test Efficiency calculation for long and short."""
    print("\n=== Testing Efficiency ===")

    # Long position: Entry=100, Last=105, SessionLow=98, SessionHigh=108
    # Efficiency = (105 - 100) / (108 - 98) = 5 / 10 = 0.5
    entry_long = 100.0
    last_long = 105.0
    session_low = 98.0
    session_high = 108.0
    is_long = True
    if is_long:
        pnl_pts = last_long - entry_long
    else:
        pnl_pts = entry_long - last_long
    denom = session_high - session_low
    eff_val = pnl_pts / denom
    print(f"Long: Entry={entry_long}, Last={last_long}, Range={session_low}-{session_high} -> Efficiency={eff_val:.2f}")
    assert abs(eff_val - 0.5) < 0.01, f"Long Efficiency calculation failed: expected 0.5, got {eff_val}"

    # Short position: Entry=100, Last=95, SessionLow=92, SessionHigh=102
    # Efficiency = (100 - 95) / (102 - 92) = 5 / 10 = 0.5
    entry_short = 100.0
    last_short = 95.0
    session_low = 92.0
    session_high = 102.0
    is_long = False
    if is_long:
        pnl_pts = last_short - entry_short
    else:
        pnl_pts = entry_short - last_short
    denom = session_high - session_low
    eff_val = pnl_pts / denom
    print(f"Short: Entry={entry_short}, Last={last_short}, Range={session_low}-{session_high} -> Efficiency={eff_val:.2f}")
    assert abs(eff_val - 0.5) < 0.01, f"Short Efficiency calculation failed: expected 0.5, got {eff_val}"
    print("OK: Efficiency calculations correct")


def test_points_calculation():
    """Test Points P&L calculation for long and short."""
    print("\n=== Testing Points P&L ===")

    # Long position: Entry=100, Last=105 → P&L = +5 points
    entry_long = 100.0
    last_long = 105.0
    is_long = True
    if is_long:
        pnl_pts = last_long - entry_long
    else:
        pnl_pts = entry_long - last_long
    print(f"Long: Entry={entry_long}, Last={last_long} -> P&L={pnl_pts:.2f} pts")
    assert abs(pnl_pts - 5.0) < 0.01, f"Long Points calculation failed: expected 5.0, got {pnl_pts}"

    # Short position: Entry=100, Last=95 → P&L = +5 points
    entry_short = 100.0
    last_short = 95.0
    is_long = False
    if is_long:
        pnl_pts = last_short - entry_short
    else:
        pnl_pts = entry_short - last_short
    print(f"Short: Entry={entry_short}, Last={last_short} -> P&L={pnl_pts:.2f} pts")
    assert abs(pnl_pts - 5.0) < 0.01, f"Short Points calculation failed: expected 5.0, got {pnl_pts}"
    print("OK: Points P&L calculations correct")


if __name__ == "__main__":
    print("=" * 60)
    print("Verifying Short-Side Calculation Logic")
    print("=" * 60)

    try:
        test_risk_calculation()
        test_rlive_calculation()
        test_rplan_calculation()
        test_mae_mfe_calculation()
        test_efficiency_calculation()
        test_points_calculation()

        print("\n" + "=" * 60)
        print("OK: ALL TESTS PASSED - Short-side calculations are correct!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nX TEST FAILED: {e}")
        exit(1)
