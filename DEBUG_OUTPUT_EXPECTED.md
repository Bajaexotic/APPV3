# Expected Debug Output When Trade Closes

## What You'll Now See

When you close a trade, the console will show:

### Panel 2 - Trade Close Event
```
====================================================================================================
[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
  Entry: $6844.5  Exit: $6850.0  Qty: 2
  Balance BEFORE: $10,000.00
  Balance AFTER:  $10,011.00 (+$11.00)
  Mode: SIM
  → About to emit tradesChanged signal to all listeners
====================================================================================================
[DEBUG panel2.notify_trade_closed] STEP 1: Trade closed notification received: {...}
[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully
```

**What This Tells You:**
- ✓ Trade detected: MES
- ✓ P&L calculated: +$11.00 gained
- ✓ Balance updated: $10,000 → $10,011
- ✓ Mode detected: SIM
- ✓ Signal emitted: Ready to trigger Panel 3 updates

---

### Signal Handler - Route to Panel 3
```
====================================================================================================
[SIGNAL RECEIVED] _on_trade_changed called!
[SIGNAL RECEIVED] Trade: MES P&L: +$11.00
[SIGNAL RECEIVED] Payload keys: ['symbol', 'qty', 'entry_price', 'exit_price', 'realized_pnl', ...]
[SIGNAL RECEIVED] STEP 1: Check panel_stats=<panels.panel3.Panel3 object at 0x...>
[SIGNAL RECEIVED] STEP 2: Calling panel_stats.on_trade_closed()
[SIGNAL RECEIVED] STEP 3: ✓ on_trade_closed completed
[SIGNAL RECEIVED] STEP 4: Check panel_stats._load_metrics_for_timeframe
[SIGNAL RECEIVED] STEP 5: Calling _load_metrics_for_timeframe with tf=1D
[SIGNAL RECEIVED] STEP 6: ✓ _load_metrics_for_timeframe completed
[SIGNAL RECEIVED] STEP 7: Check panel_stats.analyze_and_store_trade_snapshot
[SIGNAL RECEIVED] STEP 8: Calling analyze_and_store_trade_snapshot()
[SIGNAL RECEIVED] STEP 9: ✓ analyze_and_store_trade_snapshot completed
[SIGNAL RECEIVED] ==== SIGNAL HANDLING COMPLETE ====
====================================================================================================
```

**What This Tells You:**
- ✓ Signal received by handler
- ✓ Panel 3 on_trade_closed() called
- ✓ Metrics reloaded from database
- ✓ Snapshot analysis completed
- ✓ All steps successful

---

### Panel 3 - Metrics Refresh
```
[DEBUG panel3.on_trade_closed] STEP 1: Trade closed notification received: {...}
[DEBUG panel3.on_trade_closed] STEP 3: Calling _load_metrics_for_timeframe
[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf=1D
[DEBUG panel3._load_metrics_for_timeframe] STEP 6: compute_trading_stats_for_timeframe returned payload
[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 1
[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics
[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed
```

**What This Tells You:**
- ✓ Panel 3 received notification
- ✓ Metrics function loaded
- ✓ 1 trade found in database
- ✓ Update metrics called
- ✓ Panel 3 cells should now show updated values

---

## Real-World Example: Multiple Trades

If you close 3 trades in a row:

### Trade 1: Win +$500
```
====================================================================================================
[TRADE CLOSE EVENT] ES closed with +$500.00 P&L
  Entry: $5000  Exit: $5100  Qty: 1
  Balance BEFORE: $10,000.00
  Balance AFTER:  $10,500.00 (+$500.00)
  Mode: SIM
====================================================================================================
[SIGNAL RECEIVED] Trade: ES P&L: +$500.00
[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 1
```

### Trade 2: Loss -$200
```
====================================================================================================
[TRADE CLOSE EVENT] NQ closed with -$200.00 P&L
  Entry: $16000  Exit: $15980  Qty: 1
  Balance BEFORE: $10,500.00
  Balance AFTER:  $10,300.00 (-$200.00)
  Mode: SIM
====================================================================================================
[SIGNAL RECEIVED] Trade: NQ P&L: -$200.00
[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 2
```

### Trade 3: Win +$1,000
```
====================================================================================================
[TRADE CLOSE EVENT] MES closed with +$1,000.00 P&L
  Entry: $6800  Exit: $6850  Qty: 2
  Balance BEFORE: $10,300.00
  Balance AFTER:  $11,300.00 (+$1,000.00)
  Mode: SIM
====================================================================================================
[SIGNAL RECEIVED] Trade: MES P&L: +$1,000.00
[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 3
```

**Summary:**
- Trade 1: $10,000 + $500 = $10,500 (1 win)
- Trade 2: $10,500 - $200 = $10,300 (1 win, 1 loss)
- Trade 3: $10,300 + $1,000 = $11,300 (2 wins, 1 loss)

**Panel 3 Should Show:**
- Total PnL: $1,300.00 (sum of all P&L)
- Trades: 3 (count of closed trades)
- Wins: 2
- Losses: 1
- Hit Rate: 66.7%

---

## Error Cases

### If Balance Update Fails
```
[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
  Entry: $6844.5  Exit: $6850.0  Qty: 2
  Balance BEFORE: (Could not read)  ← Balance couldn't be fetched
  Mode: UNKNOWN                      ← Mode detection failed
```

**Action:** Check if StateManager is initialized

### If Signal Not Emitted
```
[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully  ← Says success
(But then nothing else appears)

(No [SIGNAL RECEIVED] appears)  ← Signal wiring failed
```

**Action:** Check app_manager startup messages for wiring errors

### If Panel 3 Metrics Load Fails
```
[SIGNAL RECEIVED] STEP 5: Calling _load_metrics_for_timeframe with tf=1D
[SIGNAL RECEIVED] STEP 6: ✗ _load_metrics_for_timeframe FAILED: DatabaseError...
```

**Action:** Check database query in stats_service.py

---

## How to Use This

1. **Run the app**
2. **Close a trade**
3. **Watch the console** for the output above
4. **Compare what you see** to the examples
5. **Report where it differs**

The debug output now includes:
- ✓ P&L gained/lost amount
- ✓ Balance before/after
- ✓ Trade count updates
- ✓ All signal flow steps

This gives you **complete visibility** into the entire trade close → Panel 3 update chain!
