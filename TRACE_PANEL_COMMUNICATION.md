# PANEL COMMUNICATION TRACE

## How Trade Close Should Flow

When a trade closes in Panel 2, this is what SHOULD happen:

```
1. DTC Message arrives (OrderUpdate Type 307 with Status=FILLED)
   └─ Contains: TradeAccount, Symbol, PnL, etc.

2. Panel 2.on_order_update(payload) called
   ├─ Detects: Trade is closed (qty went to 0)
   ├─ Calculates: PnL from entry/exit prices
   └─ Emits: tradesChanged signal with trade data

3. StateManager.set_balance_for_mode(mode, new_balance)
   ├─ Updates: sim_balance or live_balance
   └─ Emits: balanceChanged signal with new balance

4. Panel 1._on_balance_changed(balance) receives signal
   ├─ Updates: lbl_balance label text
   └─ Calls: lbl_balance.update() to redraw

5. Panel 3.on_trade_closed(trade_payload) receives signal
   ├─ Calls: _load_metrics_for_timeframe(current_tf)
   ├─ Queries: Database for trades in timeframe
   └─ Updates: metric_grid with new stats

6. Results visible:
   ✓ Panel 1: Balance changed
   ✓ Panel 2: Position flat (trade closed)
   ✓ Panel 3: Statistics updated with new trade
```

---

## What You're Seeing

Currently you see:
- ✗ Panel 1: Balance doesn't change
- ✗ Panel 2: Goes flat (this works)
- ✗ Panel 3: No data received

---

## How to Debug Each Connection

### Debug #1: Panel 2 → StateManager

**Add this to Panel 2.notify_trade_closed():**
```python
print(f"[DEBUG] notify_trade_closed called with trade: {trade}")
print(f"[DEBUG] About to call TradeManager.record_closed_trade()")
```

**Check output for**:
- Is "About to call" message printed?
- Does anything print after that?

---

### Debug #2: StateManager → Panel 1

**Add this to StateManager.set_balance_for_mode():**
```python
print(f"[DEBUG] set_balance_for_mode called: mode={mode}, balance={balance}")
print(f"[DEBUG] Emitting balanceChanged signal with {balance}")
self.balanceChanged.emit(balance)
print(f"[DEBUG] Signal emitted")
```

**Check output for**:
- All 3 messages printed?
- If not, where does it stop?

---

### Debug #3: Panel 1 Receives Balance Signal

**Add this to Panel1._on_balance_changed():**
```python
print(f"[DEBUG] _on_balance_changed called with balance={balance}")
print(f"[DEBUG] lbl_balance exists: {hasattr(self, 'lbl_balance')}")
if hasattr(self, 'lbl_balance'):
    print(f"[DEBUG] Setting text to: {_fmt_money(balance)}")
    self.lbl_balance.setText(_fmt_money(balance))
    print(f"[DEBUG] Text set, calling update()")
    self.lbl_balance.update()
    print(f"[DEBUG] update() called")
```

**Check output for**:
- Is callback called?
- Does lbl_balance exist?
- Does update() get called?

---

### Debug #4: Panel 2 → Panel 3

**Add this to Panel 3.on_trade_closed():**
```python
print(f"[DEBUG] Panel3.on_trade_closed called with: {trade_payload}")
print(f"[DEBUG] Current timeframe: {self._tf}")
print(f"[DEBUG] About to call _load_metrics_for_timeframe({self._tf})")
self._load_metrics_for_timeframe(self._tf)
print(f"[DEBUG] _load_metrics_for_timeframe completed")
```

**Check output for**:
- Is method called?
- What timeframe is active?
- Does _load_metrics complete?

---

### Debug #5: Panel 3 Loading Metrics

**Add this to Panel3._load_metrics_for_timeframe():**
```python
print(f"[DEBUG] _load_metrics_for_timeframe called with tf={tf}")
print(f"[DEBUG] Current mode: {mode}")
payload = compute_trading_stats_for_timeframe(tf, mode=mode)
print(f"[DEBUG] Stats computed. Keys: {list(payload.keys())}")
print(f"[DEBUG] Trade count: {payload.get('_trade_count', 0)}")
trades_count = payload.get("_trade_count", 0)
print(f"[DEBUG] About to call update_metrics with {len(payload)} items")
self.update_metrics(payload)
print(f"[DEBUG] update_metrics completed")
```

**Check output for**:
- Is method called?
- What stats are returned?
- How many trades found?
- Does update_metrics complete?

---

## How to Add These Debug Lines

1. Open the file in your editor
2. Find the method
3. Add print() statements at key points
4. Run the app
5. Close a trade
6. Watch the console output
7. Report back which prints appear and which don't

---

## What This Will Show Us

By tracing which debug statements print and which don't, we can identify:

1. **Data is being calculated but not displayed** → Visibility issue (my earlier fix)
2. **Signal isn't being emitted** → StateManager issue
3. **Signal emitted but not received** → Connection issue
4. **Method called but does nothing** → Logic issue
5. **Method never called** → Signal wiring broken

---

## Next Steps

1. Add these debug lines to the code
2. Run the app
3. Close a trade
4. Copy the console output
5. Share it with me
6. We'll know exactly where the problem is
