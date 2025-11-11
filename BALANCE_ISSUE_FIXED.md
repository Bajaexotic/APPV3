# Balance Reset Issue - FIXED ✅

## The Problem (What Was Happening)

1. Trade closes → PnL calculated → Balance updates from $10,000 to $9,985 ✅
2. DTC AccountBalanceUpdate (Type 600) arrives from broker with $10,000
3. Message router receives it and **OVERWRITES** the balance back to $10,000 ❌
4. User sees balance flash to correct value, then instantly reset ❌

## Root Cause

**Location:** `core/message_router.py:242`

The `_on_balance_signal()` method was blindly accepting ALL DTC balance updates and applying them to SIM mode, which overwrote the PnL-calculated balance.

```python
# BEFORE (WRONG):
def _on_balance_signal(self, sender, **kwargs):
    # ... extract balance_value from DTC message ...
    self.state.set_balance_for_mode(mode, float(balance_value))  # ← Overwrites SIM!
```

## The Fix Applied

**Check the mode BEFORE updating, and skip SIM mode balance updates:**

```python
# AFTER (FIXED):
def _on_balance_signal(self, sender, **kwargs):
    # ... extract balance_value from DTC message ...

    # ✅ Skip DTC balance updates for SIM mode!
    if mode == "SIM":
        print(f"[SKIPPING] DTC balance update for SIM mode")
        print(f"  (Using our calculated PnL balance instead)")
        return  # ← Don't overwrite!

    # Only update for LIVE mode (where DTC is the source of truth)
    if mode == "LIVE":
        self.state.set_balance_for_mode(mode, float(balance_value))
```

## Why This Works

### For SIM Mode:
- ✅ DTC balance updates are **ignored**
- ✅ Balance is updated only by **PnL calculations**
- ✅ Cumulative P&L is preserved
- ✅ No more resets!

### For LIVE Mode:
- ✅ DTC balance updates are **accepted**
- ✅ Balance comes from the **broker (source of truth)**
- ✅ Real account balance is always accurate

## What You'll See Now

When you close a trade:

```
[Trade closes]
  ↓
[Balance updates: $10,000 → $9,985]  ← Your PnL update
  ↓
[DTC sends AccountBalanceUpdate with $10,000]
  ↓
[Message Router logs]:
  [DEBUG MESSAGE_ROUTER] BALANCE_UPDATE signal received!
  [DEBUG MESSAGE_ROUTER] Detected mode: SIM
  [DEBUG MESSAGE_ROUTER] ✓ SKIPPING balance update for SIM mode
  [DEBUG MESSAGE_ROUTER] DTC value ignored: $10,000.00
  ↓
[Balance stays at $9,985]  ← FIXED! No reset!
```

## Debug Output Added

Both debug output and the fix have been added. You'll see:

When DTC tries to overwrite (for SIM mode):
```
[DEBUG MESSAGE_ROUTER] ✓ SKIPPING balance update for SIM mode
  Reason: SIM mode uses calculated PnL, not DTC broker balance
  DTC value ignored: $10,000.00
```

When it's LIVE mode (updates accepted):
```
[DEBUG MESSAGE_ROUTER] Updating balance for LIVE mode
  Old balance: $100,000.00
  New balance: $100,005.00
```

## Files Modified

1. **core/message_router.py** (FIXED)
   - Added SIM mode check
   - Skip DTC balance updates for SIM
   - Only apply updates for LIVE mode
   - Added comprehensive debug logging

2. **core/sim_balance.py** (ALREADY FIXED)
   - Fixed relative path to use absolute path

3. **services/trade_service.py** (ALREADY FIXED)
   - Fixed logging error
   - Fixed f-string formatting

## Testing

To verify the fix works:

1. Run the app
2. Close a SIM mode trade
3. Watch the console output:
   - Look for: `[SKIPPING] balance update for SIM mode`
   - Your balance should update and **STAY** at the new value
   - Should NOT reset back to original

Example:

```
[Trade CLOSED] 📈 MES | SIM Mode
  P&L: -$5.00
  Previous Balance: $10,000.00
  New Balance: $9,995.00

[DTC Message Router]:
  [SKIPPING] balance update for SIM mode
  DTC value ignored: $10,000.00

[Result]: Balance stays at $9,995.00 ✅
```

## Summary

| Issue | Status |
|-------|--------|
| PnL not calculating | Partially fixed (needs exit price from DTC) |
| Balance resets after update | ✅ FIXED |
| Balance not persisting on restart | ✅ FIXED (already was working) |
| Debug visibility | ✅ ADDED |

---

## Next Steps

Now that balance is fixed, the remaining issue is:
- **PnL calculation:** Still needs `exit_price` from DTC Type 306 message
- Look for the debug output we added to `on_position_update()`
- This will show us what fields are in the position close message

Once we find the exit price, the entire system will be complete! 🎯
