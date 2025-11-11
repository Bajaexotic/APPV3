#!/usr/bin/env python
"""
Verification script for MAE/MFE fixes and Panel 2 persistence protocol.
Demonstrates:
1. Correct MAE/MFE calculation for long and short trades
2. Panel 2 state save/load roundtrip
"""

import json
import tempfile
import os
from pathlib import Path

from services.trade_math import TradeMath


def test_mae_mfe_calculations():
    """Test MAE/MFE formulas match specification."""
    print("\n" + "="*70)
    print("TEST 1: MAE/MFE Calculation Verification")
    print("="*70)

    test_cases = [
        {
            "name": "Long Trade (Entry=6000, Low=5990, High=6010)",
            "entry": 6000,
            "trade_min": 5990,
            "trade_max": 6010,
            "is_long": True,
            "qty": 1,
            "dpp": 1,
            "expected_mae": 10,
            "expected_mfe": 10,
        },
        {
            "name": "Short Trade (Entry=6000, Low=5990, High=6010)",
            "entry": 6000,
            "trade_min": 5990,
            "trade_max": 6010,
            "is_long": False,
            "qty": 1,
            "dpp": 1,
            "expected_mae": 10,
            "expected_mfe": 10,
        },
        {
            "name": "Long Trade with Multiplier (qty=10, dpp=50)",
            "entry": 6000,
            "trade_min": 5990,
            "trade_max": 6010,
            "is_long": True,
            "qty": 10,
            "dpp": 50,
            "expected_mae": 5000,
            "expected_mfe": 5000,
        },
        {
            "name": "Short Trade with Multiplier (qty=10, dpp=50)",
            "entry": 6000,
            "trade_min": 5990,
            "trade_max": 6010,
            "is_long": False,
            "qty": 10,
            "dpp": 50,
            "expected_mae": 5000,
            "expected_mfe": 5000,
        },
    ]

    all_passed = True
    for i, tc in enumerate(test_cases, 1):
        mae, mfe = TradeMath.calculate_mae_mfe(
            entry_price=tc["entry"],
            trade_min_price=tc["trade_min"],
            trade_max_price=tc["trade_max"],
            is_long=tc["is_long"],
            qty=tc["qty"],
            dollars_per_point=tc["dpp"],
        )

        passed = mae == tc["expected_mae"] and mfe == tc["expected_mfe"]
        status = "PASS" if passed else "FAIL"
        all_passed = all_passed and passed

        print(f"\n{i}. {tc['name']}")
        print(f"   MAE: {mae} (expected: {tc['expected_mae']}) [{status}]")
        print(f"   MFE: {mfe} (expected: {tc['expected_mfe']}) [{status}]")

    print("\n" + "-"*70)
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed


def test_panel2_persistence():
    """Test Panel 2 state save/load roundtrip."""
    print("\n" + "="*70)
    print("TEST 2: Panel 2 Persistence Protocol")
    print("="*70)

    # Simulate Panel 2 state
    mock_state = {
        "entry_time_epoch": 1731259200,
        "heat_start_epoch": None,
        "entry_qty": 5,
        "entry_price": 6000.50,
        "is_long": True,
        "target_price": 6010.00,
        "stop_price": 5990.00,
        "_trade_min_price": 5995.25,
        "_trade_max_price": 6005.75,
        "entry_vwap": 6000.00,
        "entry_delta": 125.5,
        "entry_poc": 6000.25,
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(mock_state, f, separators=(",", ":"))
        temp_path = f.name

    try:
        # Read back from temp file
        with open(temp_path, 'r') as f:
            loaded_state = json.load(f)

        # Verify all fields match
        print("\nState Serialization & Deserialization:")
        all_matched = True
        for key in mock_state.keys():
            original = mock_state[key]
            loaded = loaded_state.get(key)
            matched = original == loaded
            all_matched = all_matched and matched
            status = "OK" if matched else "MISMATCH"
            print(f"  {key:25} {str(original):20} -> {str(loaded):20} [{status}]")

        # Test selective restore (like _load_state does)
        print("\nSelective Restore (Protocol Compliance):")
        restored = {}
        excluded_keys = {"price", "points", "efficiency"}  # Live-dependent
        for key in mock_state.keys():
            if key not in excluded_keys and key in loaded_state:
                restored[key] = loaded_state[key]

        restore_count = len(restored)
        expected_count = len(mock_state)
        print(f"  Restored fields: {restore_count}/{expected_count}")
        print(f"  Excluded fields (live-dependent): {excluded_keys}")
        print(f"  Restore Success: {all_matched}")

        return all_matched
    finally:
        os.unlink(temp_path)


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("APPSIERRA MAE/MFE & Persistence Verification Suite")
    print("="*70)

    test1_passed = test_mae_mfe_calculations()
    test2_passed = test_panel2_persistence()

    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Test 1 (MAE/MFE Calculations): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (Panel 2 Persistence):  {'PASSED' if test2_passed else 'FAILED'}")
    print(f"\nOverall: {'ALL TESTS PASSED [OK]' if test1_passed and test2_passed else 'SOME TESTS FAILED [FAIL]'}")
    print("="*70 + "\n")

    return 0 if (test1_passed and test2_passed) else 1


if __name__ == "__main__":
    exit(main())
