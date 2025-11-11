# Current State Diagnostic

## What You're Seeing
- Panel 3 cells are NOT stuck at $0.00
- Panel 3 cells DO show some values
- But something "might have gotten fixed then broken"
- Unclear if updates are working when NEW trades close

## What to Test Now

### Test 1: Do Panel 3 values CHANGE when you close a trade?

1. **Before closing trade**: Take a screenshot or note Panel 3 values
   - What does "Total PnL" show?
   - What does "Trades" count show?

2. **Close a trade** and watch for:
   - `[TRADE CLOSE EVENT]` in console
   - `[SIGNAL RECEIVED]` in console
   - Panel 3 cells updating

3. **After trade closes**: Check if values changed
   - Did "Total PnL" change?
   - Did "Trades" count increase?
   - Or did they stay the same?

### Test 2: Are the current values CORRECT?

Check if the values showing in Panel 3 match the database:

```sql
SELECT
  COUNT(*) as trades,
  SUM(realized_pnl) as total_pnl,
  COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as wins,
  COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losses
FROM trade_record
WHERE mode = 'SIM'
  AND is_closed = 1
  AND exit_time >= datetime('now', '-1 day');
```

**Match?** If the Panel 3 values match this query result, then:
- Panel 3 is showing correct historical data
- But may not be UPDATING when new trades close

**Don't match?** If they don't match, then:
- Panel 3 is showing stale/cached data
- Need to force refresh

### Test 3: Is the Signal Actually Flowing?

When you close a trade, watch console for:

```
[DEBUG APP_MANAGER] ==== WIRING tradesChanged SIGNAL ====
↑ This should appear ONCE at app startup

[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
↑ This should appear when you close a trade

[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully
↑ This confirms Panel 2 emitted the signal

[SIGNAL RECEIVED] _on_trade_changed called!
↑ THIS IS THE KEY LINE - if you see this, signal IS flowing

[SIGNAL RECEIVED] STEP 3: ✓ on_trade_closed completed
↑ This confirms Panel 3 was called

[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed
↑ This confirms metrics were reloaded
```

**Do you see all these lines?** Or do some steps appear and others don't?

---

## What Probably Happened

Given that:
1. Panel 3 shows VALUES (not $0.00)
2. You don't know if they update

Most likely scenario:
- **Initial load works**: Panel 3 loads historical trades and displays them correctly
- **Updates may not work**: When NEW trades close, Panel 3 might not refresh

### Possible Causes:

1. **Signal not being emitted** from Panel 2
   - Check: Do you see `[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully`?

2. **Signal not being received** by signal handler
   - Check: Do you see `[SIGNAL RECEIVED] _on_trade_changed called!`?

3. **Signal received but handler fails**
   - Check: Do you see `[SIGNAL RECEIVED] STEP X: ✗` errors?

4. **Signal handled but Panel 3 refresh fails**
   - Check: Do you see `[DEBUG panel3._load_metrics_for_timeframe]` errors?

5. **Panel 3 refreshes but cells don't update visually**
   - This is a Qt rendering issue, not a data issue

---

## How to Know Which It Is

**Run these tests in order:**

### Quick Test A: Panel 3 Initial Data
```
1. Close app
2. Open database browser
3. Check total trades and total PnL in database
4. Open app
5. Check Panel 3 - do values match database?
6. Result: YES = initial load works, NO = data loading broken
```

### Quick Test B: Panel 3 Update Flow
```
1. Note current Panel 3 "Trades" count
2. Close one trade
3. Watch console for [SIGNAL RECEIVED] or [TRADE CLOSE EVENT]
4. Check if Panel 3 "Trades" count increased by 1
5. Result: YES = updates work, NO = updates broken
```

### Quick Test C: Console Output
```
1. Close a trade
2. Search console for these keywords:
   - "TRADE CLOSE EVENT" - Panel 2 closed the trade
   - "Signal emitted" - Panel 2 emitted signal
   - "SIGNAL RECEIVED" - Signal arrived at handler
   - "update_metrics completed" - Panel 3 refreshed
3. Which ones do you see?
```

---

## If Updates Are NOT Working

Here's the debug sequence to fix it:

1. **Turn ON maximum debugging**:
   - The code already has all debug prints added
   - Just watch the console output

2. **Close a trade and capture**:
   - Take a screenshot of console output
   - Share it here
   - I'll trace where it breaks

3. **Database check**:
   - Run the SQL query above
   - Check if trade was actually saved
   - If not saved, the issue is in trade_service, not Panel 3

---

## What I Need From You

To diagnose the exact issue, tell me:

1. **What values are currently in Panel 3?**
   - Total PnL: $____
   - Trades: ____
   - Which timeframe tab is active?

2. **Do they change when you close a trade?**
   - Screenshot before/after would be helpful

3. **What do you see in the console when you close a trade?**
   - Just the keywords: TRADE CLOSE EVENT, SIGNAL RECEIVED, etc.
   - Or full output if possible

4. **When was the last time it worked correctly?**
   - What changed since then?
   - Was any code edited?

---

## Summary

The fact that Panel 3 shows VALUES means the initial load is working. The question is: **do they update when new trades close?**

Once you run Test B above and report whether the "Trades" count increases, we'll know exactly where to focus the debugging.
