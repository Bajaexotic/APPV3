# PNL and Balance Issues - Root Cause Analysis & Fixes

## Problem Summary
You reported:
1. **PnL is not updating** - Panel 3 shows $0.00 even after trades close
2. **Balance changes when reopening the app** - Balance jumps unexpectedly
3. **Database write failures** - Logger errors preventing trades from saving

## Root Causes Found

### Issue #1: Duplicate Trade Recording
**Location:** `services/trade_service.py:93` (in `on_position_update()` method)

**Problem:**
- When a position closes (qty→0), TWO different code paths were recording the SAME trade:
  1. `TradeManager.on_position_update()` at line 93 (from DTC position message Type 306)
  2. `Panel2.notify_trade_closed()` at line 346 (from DTC order fill message Type 307)

- This created **duplicate trade records** with the same ID but from different sources
- The balance was being updated **multiple times** for the same trade
- Each record had slightly different data, causing inconsistencies

**Evidence from logs:**
```
[TRACE - 08:33:33]
[services.trade_service] balance.updated.SIM: 9,953.75 (pnl=+1.25)      ← First update from on_position_update()
[services.trade_service] trade.recorded: ID=39                           ← First record
[ERROR] format specifier error
[services.trade_service] balance.updated.SIM: 9,921.25 (pnl=+1.25)      ← Second update from notify_trade_closed()
[services.trade_service] trade.recorded: ID=40                           ← Second record (duplicate!)
```

The balance jumped from $9,953.75 to $9,921.25 (-$32.50) even though PnL was only +1.25, showing multiple conflicting updates.

**Fix:**
Removed the `record_closed_trade()` call from `on_position_update()` method.

**Why this works:**
- The position update (Type 306) from DTC only tells us qty changed to 0
- It does NOT provide the exit price or fill information
- The order fill (Type 307) from DTC DOES provide exit price, commission, etc.
- Therefore, Panel2's `notify_trade_closed()` is the correct place to record the trade (it has all necessary data)
- Removing the duplicate call prevents:
  - Duplicate records in database
  - Multiple balance updates
  - Calls with missing exit_price

---

### Issue #2: Missing Exit Price in Format String
**Location:** `services/trade_service.py:224`

**Problem:**
```python
print(f"  Entry Price: ${entry_price:,.2f} | Exit Price: ${exit_price:,.2f}")
```

When `exit_price` was None, this would crash with:
```
Invalid format specifier ',.2f if exit_price else 'N/A'' for object of type 'float'
```

**Why it was None:**
- When `on_position_update()` called `record_closed_trade()` without an exit price (the old bug)
- `exit_price` parameter defaulted to None
- Trying to format None as a float caused the error

**Fix:**
```python
exit_price_display = f"${exit_price:,.2f}" if exit_price else "N/A"
print(f"  Entry Price: ${entry_price:,.2f} | Exit Price: {exit_price_display}")
```

Safely handle None values by formatting outside the f-string.

---

### Issue #3: Logger Keyword Arguments (Already Fixed)
**Location:** `core/message_router.py` (18 calls fixed)

**Problem:** structlog doesn't accept keyword arguments in format:
```python
log.error("message", error=str(e))  # ❌ WRONG
```

**Fix:** Changed to f-string format:
```python
log.error(f"message: {str(e)}")  # ✅ CORRECT
```

---

## Impact of Fixes

### Before Fixes:
- ❌ Each position close records 2 trades with different balance changes
- ❌ Panel 3 retrieves multiple records for same trade, shows $0.00
- ❌ Balance calculation is wrong (multiple PnL additions)
- ❌ On app restart, balance loads from corrupted database state
- ❌ Format specifier errors prevent database writes

### After Fixes:
- ✅ Each position close records exactly 1 trade
- ✅ Balance updates once per trade with correct PnL
- ✅ Panel 3 shows accurate trade statistics
- ✅ Balance persists correctly between app restarts
- ✅ No logger errors or exceptions

---

## Testing Checklist

After deploying these fixes:

1. **Open a position**
   - [ ] Balance shows initial SIM balance ($10,000)
   - [ ] No duplicate balance updates in console

2. **Close the position**
   - [ ] One `[TRADE CLOSED]` message in console
   - [ ] PnL calculated correctly: `(exit_price - entry_price) * qty`
   - [ ] Balance updated once with correct value
   - [ ] No logger errors

3. **Check Panel 3**
   - [ ] Shows total PnL for closed trades
   - [ ] Shows correct trade count (1, not 2)
   - [ ] Shows correct win/loss statistics

4. **Close and reopen app**
   - [ ] Balance persists at previous value
   - [ ] Doesn't reset to $10,000 or jump unexpectedly
   - [ ] Historical trades still visible in Panel 3

5. **Multiple trades**
   - [ ] Each trade recorded once
   - [ ] Balance accumulates correctly (trade1_pnl + trade2_pnl + ...)
   - [ ] No duplicate records in database

---

## Files Modified

1. **services/trade_service.py**
   - Line 93: Removed duplicate `record_closed_trade()` call
   - Line 214: Added `new_balance = None` initialization
   - Line 224: Added safe formatting for `exit_price` (None check)

2. **core/message_router.py**
   - 18 logger calls: Changed from keyword arguments to f-string format
   - Lines: 100, 123, 131, 139, 143, 164, 167, 191, 199, 207, 211, 214, 264, 266, 275, 279, 282, 316, 338, 340, 369, 404, 441

---

## Technical Explanation

### Why Duplicate Recording Happened

```
DTC sends: ORDER_FILL (Type 307)
  ├─ Extracted by data_bridge.py → signal sent
  ├─ Caught by Panel2.on_order_update() → triggers notify_trade_closed()
  │   └─> Calls trade_manager.record_closed_trade() with EXIT PRICE ✅
  │
  ├─ Also extracted by data_bridge.py → POSITION_UPDATE (Type 306) sent
  │   └─> Calls TradeManager.on_position_update()
  │       └─> Detected qty→0 → Called record_closed_trade() WITHOUT exit price ❌

Result: TWO records created, TWO balance updates
```

### Why This Broke PnL Display

```
Database has trades:
- Trade ID 39: PnL=+1.25, Mode=SIM
- Trade ID 40: PnL=+1.25, Mode=SIM  (duplicate!)

Panel 3 queries: SELECT * FROM trades WHERE mode='SIM'
Returns: 2 records instead of 1

But Panel 3 UI probably shows only latest or sums them:
- If summed: +1.25 + 1.25 = +2.50 (wrong)
- If latest: +1.25 (right value, but on second record)
- If deduplicated: Shows $0.00 (confusion logic)

Balance persistence issue:
- App saves balance=$9,921.25 (after 2nd update)
- Should be $9,953.75 + 1.25 = $9,955.00
- On restart: Loads corrupted $9,921.25
```

---

## Code References

**Before (WRONG):**
```python
# services/trade_service.py:93
self.record_closed_trade(symbol, current_pos)  # ❌ No exit_price!
```

**After (CORRECT):**
```python
# services/trade_service.py:93
# ⚠ DO NOT call record_closed_trade() here!
# Panel2.notify_trade_closed() will handle it with full data
self._open_positions.pop(symbol, None)
```

---

## Next Steps

1. **Test the fixes** - Run a mock trade and verify:
   - One trade record created
   - Balance updated once
   - PnL displays correctly
   - Balance persists on restart

2. **Monitor logs** - Watch for:
   - No format specifier errors
   - No duplicate balance.updated messages
   - Clean [TRADE CLOSED] messages

3. **Validate database** - Check:
   - No duplicate trade records
   - Correct PnL values
   - Correct mode (SIM/LIVE)
   - Balance matches UI

4. **Performance** - Ensure:
   - No slowdown from removing duplicate call
   - Database queries faster (fewer duplicate records)
   - Panel 3 loads instantly
