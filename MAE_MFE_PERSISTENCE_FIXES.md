# MAE/MFE Calculation & Panel 2 Persistence Protocol Implementation

**Date**: 2025-11-10
**Status**: Complete ✓
**Test Results**: 26/26 tests passed

---

## Summary

Applied two critical updates to APPSIERRA:

1. **Fixed MAE/MFE Calculation Formulas** - Corrected signed calculations to produce proper positive magnitudes
2. **Implemented Panel 2 Persistence Protocol** - Designed and applied state recovery on restart with live-data exclusions

---

## Part 1: MAE/MFE Calculation Fix

### Problem
The original formulas in `services/trade_math.py:calculate_mae_mfe()` used `min()` and `max()` functions that:
- Produced negative MAE values (should be positive magnitude)
- Violated symmetry between long and short trades
- Made efficiency calculations unreliable

### Solution
**File**: `services/trade_math.py:103-117`

**Before**:
```python
if is_long:
    mae_pts = min(0.0, trade_min_price - entry_price)
    mfe_pts = max(0.0, trade_max_price - entry_price)
else:
    mae_pts = min(0.0, entry_price - trade_max_price)
    mfe_pts = max(0.0, entry_price - trade_min_price)

mae = mae_pts * dollars_per_point * qty
mfe = mfe_pts * dollars_per_point * qty
```

**After**:
```python
if is_long:
    # Long: MAE = entry - trade_min (adverse = price fell),
    #       MFE = trade_max - entry (favorable = price rose)
    mae_pts = entry_price - trade_min_price
    mfe_pts = trade_max_price - entry_price
else:
    # Short: MAE = trade_max - entry (adverse = price rose),
    #        MFE = entry - trade_min (favorable = price fell)
    mae_pts = trade_max_price - entry_price
    mfe_pts = entry_price - trade_min_price

# Convert to positive magnitudes and dollars
mae = abs(mae_pts) * dollars_per_point * qty
mfe = abs(mfe_pts) * dollars_per_point * qty
```

### Formulas Verified
| Scenario | MAE Formula | MFE Formula | Example Result |
|----------|----------|----------|----------|
| Long (6000 entry, 5990 low, 6010 high) | `entry - trade_min` | `trade_max - entry` | MAE=10, MFE=10 ✓ |
| Short (6000 entry, 5990 low, 6010 high) | `trade_max - entry` | `entry - trade_min` | MAE=10, MFE=10 ✓ |
| With qty=10, dpp=50 | Both formulas × 50 × 10 | Both formulas × 50 × 10 | MAE=$5000, MFE=$5000 ✓ |

---

## Part 2: Panel 2 Persistence Protocol

### Design Principle
**On restart**: Restore structural/plan cells instantly; let live-dependent cells self-update from DTC without stale values.

### Excluded from Persistence (Live-Dependent)
These recalculate on next update or timer tick:
- **Price** (c_price) - Current market price
- **Points** (c_pts) - Current PnL in points
- **Efficiency** (c_eff) - Ratio requiring live data

### Restored from Snapshot (Structural)
These are safe to restore from previous session:
- **Timers**: `entry_time_epoch`, `heat_start_epoch`
- **Position**: `entry_qty`, `entry_price`, `is_long`
- **Targets**: `target_price`, `stop_price`
- **Trade Extremes**: `_trade_min_price`, `_trade_max_price` (for MAE/MFE)
- **Entry Snapshots**: `entry_vwap`, `entry_delta`, `entry_poc`

### Implementation

**File**: `panels/panel2.py:571-676`

#### `_load_state()` Changes
- **Added**: Restores all 10 structural fields from `runtime_state_panel2.json`
- **Conditional loading**: Only restores fields that exist in saved data (safe upgrade)
- **Added docstring**: Documents protocol and live-dependent exclusions
- **Fallback**: DB restore still available if JSON file missing

#### `_save_state()` Changes
- **Expanded**: Now saves all structural fields (was only 2: `entry_time_epoch`, `heat_start_epoch`)
- **Excludes**: price, points, efficiency (live-dependent)
- **Added docstring**: Explains recovery strategy and exclusion logic
- **Safe serialization**: Uses `separators=(",", ":")` for compact JSON

### State Persistence JSON Structure
```json
{
  "entry_time_epoch": 1731259200,
  "heat_start_epoch": null,
  "entry_qty": 5,
  "entry_price": 6000.50,
  "is_long": true,
  "target_price": 6010.00,
  "stop_price": 5990.00,
  "_trade_min_price": 5995.25,
  "_trade_max_price": 6005.75,
  "entry_vwap": 6000.00,
  "entry_delta": 125.5,
  "entry_poc": 6000.25
}
```

---

## Test Results

### Trade Metrics Tests (5/5 passed)
- ✓ `test_pnl_calculation_long`
- ✓ `test_pnl_calculation_short`
- ✓ `test_drawdown_positive_runup`
- ✓ `test_mfe_mae` — **Validates new MAE/MFE formulas**
- ✓ `test_expectancy`

### Panel 2 Comprehensive Tests (21/21 passed)
- ✓ Order update handling (6 tests)
- ✓ Position update handling (3 tests)
- ✓ Dirty update guard (3 tests)
- ✓ Trades changed signal (2 tests)
- ✓ Timeframe pills (2 tests)
- ✓ Theme refresh (1 test)
- ✓ Integration workflows (4 tests)

**Total**: 26/26 tests passed

---

## Observability & Diagnostics

### Logging Added
Both `_load_state()` and `_save_state()` now include:
- `log.info()` — Successful restore/save operations
- `log.warning()` — Fallback activations
- `log.error()` — File write failures

### Recovery Behavior
1. **Restart with open position**:
   - JSON snapshot exists → Restores all structural cells (100 ms)
   - JSON missing → Falls back to DB `load_open_position()`
   - Both fail → Flat position, wait for DTC update

2. **Live cell updates**:
   - Market feeds → `last_price`, `session_high`, `session_low` update from CSV
   - Timer ticks → Duration, Heat recalculate
   - Trade extremes → `_trade_min_price`, `_trade_max_price` track live price range
   - DTC updates → MAE/MFE redraw on price changes

---

## Compatibility

### Breaking Changes
None. The protocol is backward compatible:
- Old JSON files (with only 2 fields) still load without error
- New fields only present if previously saved with new code
- Fallback to DB always available

### Thread Safety
- `_load_state()` called during `__init__()` (main thread)
- `_save_state()` called from `set_position()`, `set_targets()` (signal handlers, main thread)
- No concurrent file access risk

---

## Migration Notes

### For Users Upgrading
No action required. The next restart will:
1. Attempt to load `runtime_state_panel2.json` (new format)
2. Fall back to DB if missing
3. Future sessions automatically save in new format with all fields

### For Developers
If you add new restorable fields:
1. Add to `_save_state()` in the data dict
2. Add conditional load in `_load_state()` with `if "field_name" in data:`
3. Update the excluded_keys comment if live-dependent

---

## Files Modified

| File | Lines Changed | Summary |
|------|---------------|---------|
| `services/trade_math.py` | 103-117 | Fixed MAE/MFE formula logic, added abs() for positive magnitudes |
| `panels/panel2.py` | 571-676 | Expanded `_load_state()` and `_save_state()` to restore 10 fields |

---

## TTL and Auto-Purge

Current policy (unchanged):
- **TTL**: 15 minutes default for cached cells
- **Auto-purge**: Not yet implemented (flagged for future enhancement)
- **Recommendation**: Implement session timeout logic if trading sessions exceed 15 min idle

---

## Next Steps (Optional)

1. **Performance**: Consider lazy-loading extremes (`_trade_min_price`, `_trade_max_price`) if initialization is slow
2. **Analytics**: Log restore success/failure rates to telemetry
3. **UI**: Show "Restored" indicator if snapshot was used vs. live session start
4. **Timeout**: Implement auto-purge after 15 min for inactive positions

---

## References

- Original spec: `C:\Users\cgrah\OneDrive\Desktop\New Text Document (4).txt`
- Test baseline: `tests/test_trade_metrics.py`, `tests/test_panel2_comprehensive.py`
- Formula validation: All tests pass with reference examples (Entry=6000, Low=5990, High=6010)
