# DEBUGGING Panel 3 & Panel 1 PnL Updates

## Problem Statement

**Panel 3 Cells Not Updating**: When a trade closes, Panel 3 metric cells should show updated PnL/stats but they remain at $0.00

**Panel 1 PnL Not Updating**: Panel 1's PnL label should update to show profit/loss for the current timeframe but remains at 0.00%

---

## Signal Flow (How It Should Work)

```
┌─────────────────────────────────────────────────────────────┐
│ DTC sends ORDER_UPDATE (Type 307) when position closes     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
        ┌────────────────────────────────────┐
        │ data_bridge.py receives message   │
        │ Extracts OrderUpdate               │
        └────────────────────┬───────────────┘
                             │
                             ↓
             ┌───────────────────────────────┐
             │ Panel2.on_order_update()      │
             │ • Detects qty→0 (close)       │
             │ • Creates trade dict          │
             │ • Calls notify_trade_closed() │
             └────────────────┬──────────────┘
                              │
                              ↓
                ┌──────────────────────────────────┐
                │ Panel2.notify_trade_closed()     │
                │ • Records trade to database      │
                │ • Emits tradesChanged signal     │
                └────────────────┬─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ↓                         ↓
      ┌─────────────────────────┐  ┌───────────────────────┐
      │ app_manager receives    │  │ MessageRouter receives│
      │ tradesChanged signal    │  │ through Blinker       │
      │ → calls Panel3.         │  │ (parallel path)       │
      │   on_trade_closed()     │  │                       │
      │   _load_metrics_for_tf()│  │ Updates balance via   │
      └────────────┬────────────┘  │ Panel1.update_equity_ │
                   │               │ series_from_balance() │
                   ↓               └───────────────────────┘
        ┌──────────────────────┐
        │ Panel3.on_trade_    │
        │ closed()             │
        │ • Refreshes metrics  │
        │ • Updates cells      │
        └──────────────────────┘
```

---

## Debug Output Locations

### 1. **App Manager Signal Wiring** (NOW WITH DEBUG OUTPUT)
   - **File**: `core/app_manager.py:263-324`
   - **Look For**:
     - `[DEBUG APP_MANAGER] ==== WIRING tradesChanged SIGNAL ====`
     - `[DEBUG APP_MANAGER] ✓ tradesChanged.connect() succeeded`
     - `[DEBUG APP_MANAGER] ==== SIGNAL WIRING COMPLETE ====`

### 2. **Signal Received Handler** (NOW WITH DEBUG OUTPUT)
   - **File**: `core/app_manager.py:273-313`
   - **Look For**:
     - `[SIGNAL RECEIVED] _on_trade_changed called!`
     - `[SIGNAL RECEIVED] STEP 1-9` (traces through all callbacks)
     - `[SIGNAL RECEIVED] ==== SIGNAL HANDLING COMPLETE ====`

### 3. **Panel 2 Trade Close** (EXISTING DEBUG)
   - **File**: `panels/panel2.py:144-216`
   - **Look For**:
     - `[DEBUG panel2.notify_trade_closed] STEP 1-7`
     - `[TRADE CLOSE EVENT]`

### 4. **Trade Service Record** (EXISTING DEBUG)
   - **File**: `services/trade_service.py:160-315`
   - **Look For**:
     - `[DEBUG ENTRY] record_closed_trade() called`
     - `[TRADE CLOSED]` (emoji box with results)
     - `[TRADE SUMMARY]`

### 5. **Panel 3 On Trade Closed** (EXISTING DEBUG)
   - **File**: `panels/panel3.py:389-421`
   - **Look For**:
     - `[DEBUG panel3.on_trade_closed] STEP 1-7`
     - Calls to `_load_metrics_for_timeframe()`

### 6. **Panel 3 Load Metrics** (EXISTING DEBUG)
   - **File**: `panels/panel3.py:283-345`
   - **Look For**:
     - `[DEBUG panel3._load_metrics_for_timeframe] STEP 1-13`
     - Calls to `update_metrics()`

### 7. **Panel 1 PnL Update** (EXISTING DEBUG)
   - **File**: `panels/panel1.py:696-767`
   - **Look For**:
     - `[DEBUG panel1._update_pnl_for_current_tf] ENTRY`
     - Database query results
     - `[DEBUG panel1._update_pnl_for_current_tf] Calling set_pnl_for_timeframe`

---

## How to Debug

### Step 1: Run the App and Check Signal Wiring
```
[DEBUG APP_MANAGER] ==== WIRING tradesChanged SIGNAL ====
[DEBUG APP_MANAGER] panel_live=<Panel2 object>
[DEBUG APP_MANAGER] panel_stats=<Panel3 object>
[DEBUG APP_MANAGER] ✓ panel_live.tradesChanged exists
[DEBUG APP_MANAGER] ✓ tradesChanged.connect() succeeded
[DEBUG APP_MANAGER] ==== SIGNAL WIRING COMPLETE ====
```

**✓ PASS**: If you see all these lines, signal wiring is OK
**✗ FAIL**: If you don't see them, check app_manager startup

### Step 2: Close a Trade and Look for Signal Received

```
[TRADE CLOSE EVENT] MES closed with +$11.00 P&L
[DEBUG panel2.notify_trade_closed] STEP 1: Trade closed notification received: {...}
[DEBUG panel2.notify_trade_closed] STEP 7: Signal emitted successfully
[SIGNAL RECEIVED] _on_trade_changed called!
[SIGNAL RECEIVED] STEP 1-9: ...
[DEBUG panel3.on_trade_closed] STEP 1: Trade closed notification received: {...}
```

**✓ PASS**: If you see `[SIGNAL RECEIVED] _on_trade_changed called!`, signal is flowing
**✗ FAIL**: If you don't see this, signal is NOT being emitted or received

### Step 3: Check Panel 3 Metrics Load

```
[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf=1D
[DEBUG panel3._load_metrics_for_timeframe] STEP 2: stats_service imported successfully
[DEBUG panel3._load_metrics_for_timeframe] STEP 5: Calling compute_trading_stats_for_timeframe
[DEBUG panel3._load_metrics_for_timeframe] STEP 6: compute_trading_stats_for_timeframe returned payload
[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics
[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed
```

**✓ PASS**: If you see "Trades found" and "update_metrics completed"
**✗ FAIL**: If you see "No trades found", the database query failed

### Step 4: Check Panel 1 PnL Update

```
[DEBUG panel1._update_pnl_for_current_tf] ENTRY: timeframe=1D, mode=SIM
[DEBUG] Timeframe 1D: 2025-11-11T00:00:00+00:00 → 2025-11-11T14:32:15.123456+00:00
[DEBUG] Found 1 closed trades in timeframe
[DEBUG] Total PnL: $+11.00
[DEBUG] PnL %: +0.11%
[DEBUG] Calling set_pnl_for_timeframe: value=+11.00, pct=+0.11%, up=True
[DEBUG panel1.set_pnl_for_timeframe] ENTRY: pnl_value=11.0, pnl_pct=0.11, up=True
[DEBUG panel1._apply_pnl_to_header] EXIT: label text set to '▲ $11.00 (0.11%)'
```

**✓ PASS**: If you see "Found X closed trades" and label text updated
**✗ FAIL**: If you see "No trades found" or "Calling set_pnl_for_timeframe" but label doesn't update

---

## Common Issues & Solutions

### Issue 1: Signal Never Received
**Symptom**: No `[SIGNAL RECEIVED]` in console
**Causes**:
1. Signal not emitted from Panel 2 (check notify_trade_closed STEP 7)
2. Signal wiring failed (check APP_MANAGER output)
3. Signal handler not connected properly

**Fix**:
- Check if `[SIGNAL RECEIVED]` appears after trade close
- If not, check `[DEBUG panel2.notify_trade_closed]` STEP 7 for signal emission
- Verify app_manager shows `tradesChanged.connect() succeeded`

### Issue 2: Metrics Not Updating in Panel 3
**Symptom**: Panel 3 cells stay at $0.00
**Causes**:
1. No trades found in database for current timeframe
2. Trades have NULL realized_pnl
3. update_metrics() not actually refreshing cells

**Fix**:
- Check `[DEBUG panel3._load_metrics_for_timeframe] STEP 7` for trade count
- If 0 trades, check trade_service for why trades aren't being saved
- If trades exist, check `STEP 9` to see if update_metrics is called
- Check MetricGrid.update_metric() implementation

### Issue 3: Panel 1 PnL Not Updating
**Symptom**: Panel 1 shows "○ $0.00 (0.00%)" always
**Causes**:
1. No trades in database for timeframe range
2. Trades have NULL realized_pnl
3. set_pnl_for_timeframe() not updating label

**Fix**:
- Check `[DEBUG panel1._update_pnl_for_current_tf]` for found trade count
- If 0 found, check database directly:
  ```sql
  SELECT COUNT(*) FROM trade_record WHERE mode='SIM' AND is_closed=1;
  SELECT * FROM trade_record LIMIT 5;
  ```
- If trades exist but PnL shows 0, check realized_pnl column for NULL values

### Issue 4: Database Queries Return 0 Trades
**Symptom**: `[DEBUG] Found 0 trades in timeframe`
**Causes**:
1. Exit time is NULL or outside queried range
2. Mode doesn't match (SIM vs LIVE)
3. is_closed=False
4. Trades are in database but query parameters are wrong

**Fix**:
- Check trade_service.py STEP 8 for what was saved
- Verify trade.is_closed = True
- Verify trade.mode = current_mode
- Check exit_time is set correctly

---

## Quick Checklist to Run Through

- [ ] App starts and shows "[DEBUG APP_MANAGER] ==== WIRING tradesChanged SIGNAL ===="
- [ ] Signal wiring completes with "✓ tradesChanged.connect() succeeded"
- [ ] Close a trade and see "[TRADE CLOSE EVENT]" in console
- [ ] Trade records to database with "[DEBUG STEP 8] ✓ Trade committed..."
- [ ] Signal received with "[SIGNAL RECEIVED] _on_trade_changed called!"
- [ ] Panel 3 gets called with "[DEBUG panel3.on_trade_closed] STEP 1"
- [ ] Panel 3 loads metrics with "[DEBUG panel3._load_metrics_for_timeframe] STEP 1"
- [ ] Metrics load finds trades with "[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count ... 1"
- [ ] Metrics update with "[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed"
- [ ] Panel 3 cells show updated values
- [ ] Panel 1 updates PnL with "[DEBUG panel1._update_pnl_for_current_tf] ENTRY"
- [ ] Panel 1 label shows trade result like "▲ $11.00 (0.11%)"

---

## Database Validation Queries

Run these in `data/trading.db` to validate data:

```sql
-- Check if trades exist
SELECT COUNT(*) as total_trades FROM trade_record;

-- Check for NULL PnL trades
SELECT COUNT(*) as null_pnl FROM trade_record WHERE realized_pnl IS NULL;

-- List recent trades
SELECT id, symbol, mode, entry_price, exit_price, realized_pnl, is_closed, exit_time
FROM trade_record
ORDER BY exit_time DESC
LIMIT 10;

-- Check mode distribution
SELECT mode, COUNT(*) as count FROM trade_record GROUP BY mode;

-- Check today's trades (1D timeframe)
SELECT id, symbol, realized_pnl, exit_time
FROM trade_record
WHERE DATE(exit_time) = DATE('now')
ORDER BY exit_time DESC;
```

---

## If All Debug Output Looks Good But Panels Still Don't Update

There may be a UI rendering issue. Check:

1. **MetricGrid cell visibility**: Are cells even being redrawn?
   - Add breakpoint in `widgets/metric_grid.py::update_metric()`
   - Check if `set_value()` is called
   - Check if `update()` is called on the cell

2. **Qt Signal/Slot Thread Issues**: Is the update running on the wrong thread?
   - Look for Qt thread warnings in console
   - Check if `marshal_to_qt_thread()` is needed

3. **Widget Geometry**: Are cells hidden off-screen?
   - Check if MetricGrid widget is visible: `self.metric_grid.isVisible()`
   - Check size: `self.metric_grid.size()`

4. **CSS/Theme Conflicts**: Is the text color the same as background?
   - Check THEME colors for metric text color
   - Try forcing a different color to test visibility

---

## Running with Full Debug Output

To see all debug output, ensure you're running the app from terminal:

```bash
# Windows PowerShell
python main.py 2>&1 | Tee-Object -FilePath debug.log

# Windows CMD
python main.py > debug.log 2>&1

# Then search in the log file:
findstr /I "SIGNAL RECEIVED\|DEBUG panel3\|DEBUG panel1\|TRADE CLOSE" debug.log
```

This will show you the complete signal flow.

---

## Next Steps

1. **Run the app** and close a trade
2. **Watch the console** for the debug output above
3. **Report which steps are missing** from the checklist
4. **Share the relevant console output** for your trade close

That will pinpoint exactly where the update chain breaks!
