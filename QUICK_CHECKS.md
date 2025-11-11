# Quick Checks - Panel Update Flow

## TL;DR Quick Diagnosis

When you **close a trade**, watch the **console** for these exact lines in order:

### ✓ PASS (All these should appear):

```
====================================================================================================
[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
  Entry: $6844.5  Exit: $6850.0  Qty: 1
  → About to emit tradesChanged signal to all listeners
====================================================================================================

[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully

[SIGNAL RECEIVED] _on_trade_changed called!
[SIGNAL RECEIVED] STEP 1: Check panel_stats=<panels.panel3.Panel3 object>
[SIGNAL RECEIVED] STEP 2: Calling panel_stats.on_trade_closed()
[SIGNAL RECEIVED] STEP 3: ✓ on_trade_closed completed

[DEBUG panel3.on_trade_closed] STEP 1: Trade closed notification received
[DEBUG panel3.on_trade_closed] STEP 3: Calling _load_metrics_for_timeframe
[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf=1D
[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics
[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed

Panel 3 metric cells update with new values ✓
```

---

## If You Don't See Them:

### Missing: `[TRADE CLOSE EVENT]`
- Trade never closed or didn't trigger notify_trade_closed()
- Check: Did position qty actually go to 0?

### Missing: `[SIGNAL RECEIVED] _on_trade_changed called!`
- Signal was emitted but not received
- Wiring failed at startup
- Check console for: `[DEBUG APP_MANAGER] ✓ tradesChanged.connect() succeeded`

### Missing: `[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found`
- Database has no trades for selected timeframe
- Check: Is the trade actually in the database?
- Run SQL: `SELECT COUNT(*) FROM trade_record WHERE is_closed=1;`

### Missing: `update_metrics completed` OR Panel 3 doesn't update visually
- Metrics loaded but cells not updating
- Possible Qt rendering issue
- Check if cell widgets are visible and have correct size

---

## Database Quick Check

Open `data/trading.db` and run:

```sql
-- How many trades total?
SELECT COUNT(*) as total FROM trade_record;

-- Do we have today's trades? (1D timeframe)
SELECT COUNT(*) as today FROM trade_record
WHERE DATE(exit_time) = DATE('now');

-- What are the latest 3 trades?
SELECT symbol, realized_pnl, exit_time, is_closed
FROM trade_record
ORDER BY exit_time DESC
LIMIT 3;
```

If these queries return 0 trades, the issue is in **trade_service.py**, not Panel 3.

---

## Panel 3 Current Values Check

Look at Panel 3 in the GUI and note:

- **Total PnL**: $______ (what does it show?)
- **Trades**: _____ (how many?)
- **Active Tab**: (LIVE / 1D / 1W / 1M / 3M / YTD?)

Then run the SQL above with correct timeframe:

```sql
-- For LIVE tab (last 1 hour):
SELECT SUM(realized_pnl) as total_pnl, COUNT(*) as trades
FROM trade_record
WHERE exit_time >= datetime('now', '-1 hour')
AND is_closed = 1;

-- For 1D tab (today):
SELECT SUM(realized_pnl) as total_pnl, COUNT(*) as trades
FROM trade_record
WHERE DATE(exit_time) = DATE('now')
AND is_closed = 1;
```

**Do the numbers match?**
- YES = Panel 3 is correct, just not updating on new trades
- NO = Panel 3 is showing wrong/stale data

---

## One-Line Diagnostic

Close a trade and search console for:

```
grep -i "SIGNAL RECEIVED\|Trades found\|update_metrics" console_output.txt
```

If you see:
- `SIGNAL RECEIVED` → Signal wiring works
- `Trades found` → Database has trades
- `update_metrics` → Panel 3 loaded metrics

But Panel 3 still doesn't update → It's a Qt rendering issue

---

## Summary Table

| Symptom | Check For | Fix |
|---------|-----------|-----|
| Panel 3 shows wrong values | SQL query vs Panel 3 values | Rebuild cache or reload |
| Panel 3 doesn't update on new trade | `SIGNAL RECEIVED` in console | Check wiring |
| Signal not received | `tradesChanged.connect()` at startup | Restart app |
| Trades not in database | SQL `COUNT(*)` query | Check trade_service STEP 8 |
| Panel 3 loads metrics but cells don't update | Qt rendering issue | Possible widget visibility bug |

---

## Next: Run This Now

1. **Close a trade**
2. **Search console for**: `SIGNAL RECEIVED`
3. **Report**: "I see it" or "I don't see it"

That one line tells us everything!
