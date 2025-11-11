# ROOT CAUSE FOUND: PnL Calculation Issue

## The Problem

PnL is being calculated as `0.00` instead of the actual profit/loss value, even though the balance IS being updated correctly!

Example from logs:
```
[INFO] balance.updated.SIM: 9,980.00 (pnl=-5.00)
[INFO] trade.recorded: F.US.MESZ25 | PnL=+0.00 | Mode=SIM | ID=14
[ERROR] Invalid format specifier (now FIXED)
```

Notice:
- Balance changed by `-5.00` (correct!)
- But recorded trade shows PnL as `+0.00` (wrong!)

---

## Root Cause Identified

### Issue Location: `services/trade_service.py:81`

When a position closes via DTC Type 306 (PositionUpdate), the code calls:

```python
self.record_closed_trade(symbol, current_pos)
```

**Problem:** This call provides NO `exit_price` parameter!

The function signature expects:
```python
def record_closed_trade(
    self,
    symbol: str,
    pos_info: dict[str, Any],
    exit_price: Optional[float] = None,  # ← THIS IS REQUIRED FOR PnL
    realized_pnl: Optional[float] = None,
    ...
)
```

### What Happens Without `exit_price`

When `exit_price=None` and `realized_pnl=None`:

1. Function tries to calculate PnL: `(exit_price - entry_price) * qty`
2. But `exit_price` is None, so it skips calculation
3. `realized_pnl` stays `None`
4. However, balance IS updated somewhere (line 186 shows balance changing!)

This is confusing because:
- ✓ Balance updates correctly
- ✗ But PnL shown as 0.00 in database

---

## Why Balance Updates But PnL Shows 0

Looking at the code flow:

1. **on_position_update()** receives DTC Type 306 message
   - Message contains: symbol, qty=0, avg_entry
   - Message DOES NOT contain: exit_price

2. **record_closed_trade()** is called with NO exit_price
   - PnL cannot be calculated
   - `realized_pnl = None`

3. **Balance update happens ANYWAY** (line 186)
   - But we don't see a `realized_pnl=+5.00` in the calculation
   - This suggests the balance is being updated from somewhere ELSE

4. **Panel 3 queries database**
   - Finds trade with `realized_pnl = NULL`
   - Returns `0.00` for PnL display

---

## The Solution

### We need to find the exit price!

The DTC Type 306 message (PositionUpdate) when `qty=0` should contain information about where the position closed. This might be:

1. **In the position update payload itself**
   - Check if there's a field like `last_price`, `exit_price`, `close_price`

2. **In the last order fill message**
   - The most recent OrderFillUpdate (Type 307) with matching symbol
   - This has the actual execution price

3. **In the last market data**
   - The last known market price for that symbol

---

## Debug Output Added

I added debug logging to see what's in the DTC payload:

```python
[DEBUG on_position_update] DTC Type 306 Message received:
  Payload keys: [list of all keys in the message]
  Full payload: {entire message dict}
  Extracted: symbol=MES, qty=0, avg_entry=6844.5
```

**Run the app now and close a trade.** Watch the console for this debug output!

---

## What to Look For

When a position closes, you should see:

```
[DEBUG on_position_update] DTC Type 306 Message received:
  Payload keys: ['symbol', 'qty', 'avg_entry', ...]
  Full payload: {...}
```

**Check the payload keys carefully:**
- Is there a `last_price` field?
- Is there a `close_price` field?
- Is there a `bid`/`ask` or any price field?
- Check for fields we haven't seen before

This will tell us where to get the exit price!

---

## Current Workaround

The balance IS being updated (we can see it), which means something DOES know the exit price. We need to find what that is and wire it into the trade recording.

**Hypothesis:** The balance update might be coming from Panel 2 directly (not from trade_service), and that's why the balance changes correctly but the PnL in the database is wrong.

---

## Next Steps

1. **Run app with new debug output**
2. **Close a trade and examine the payload**
3. **Find where the exit price is coming from**
4. **Update on_position_update() to extract and pass exit_price**

---

## Files Modified (Debug Instrumentation)

1. `services/trade_service.py`
   - Added payload inspection in `on_position_update()`
   - Added position close debug output
   - Fixed f-string formatting errors

2. Fixed logging error that was hiding the real issue

---

## Key Log Lines from Earlier Run

```
-156→[2025-11-11 08:17:34] [INFO] [panels.panel2] Seeded position from fill: qty=2, price=6844, long=True
-155→[2025-11-11 08:17:34] [INFO] [services.trade_service] balance.updated.SIM: 9,990.00 (pnl=+0.00)
```

This shows:
- Panel 2 knows the fill price (6844)
- Trade service updates balance with pnl=+0.00 (wrong!)
- But balance amount changed (9,990.00)

The balance change is probably coming from Panel 2 directly via StateManager!

---

## Summary

**THE ISSUE:** `on_position_update()` doesn't pass `exit_price` to `record_closed_trade()`, so PnL can't be calculated from the DTC position message alone.

**THE QUESTION:** Where should we get the exit price from?

**THE ANSWER:** Check the debug output from the new logging to see what's in the DTC Type 306 payload!
