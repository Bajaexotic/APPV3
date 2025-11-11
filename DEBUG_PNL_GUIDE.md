# PnL Calculation Debug Guide

## Overview

This document explains how to trace and debug PnL (Profit and Loss) calculation throughout the APPSIERRA trading system.

---

## Debug Output Flow

When you close a trade, the following debug output flows through the system:

```
[DEBUG ENTRY] record_closed_trade() called
    ↓
[DEBUG STEP 1] Extract position info
    ↓
[DEBUG STEP 2A/2B] PnL calculation check
    ↓
[DEBUG STEP 3] Mode detection
    ↓
[DEBUG STEP 4] Balance update check
    ↓
[DEBUG STEP 5] Creating TradeRecord object
    ↓
[DEBUG STEP 6-8] Database write
    ↓
[DEBUG STATS] compute_trading_stats_for_timeframe()
    ↓
[DEBUG PANEL3] _load_metrics_for_timeframe()
    ↓
[DISPLAY] Metrics shown in Panel 3 grid
```

---

## Key Debug Points

### 1. **Trade Closure Detection** (`services/trade_service.py`)

When a position closes (qty → 0), `on_position_update()` triggers:

```python
# Look for this in console:
[DEBUG ENTRY] record_closed_trade() called
  symbol=MES
  realized_pnl=None (type: NoneType)
  exit_price=6850.0 (type: float)
  pos_info={'qty': 2, 'entry_price': 6844.5, ...}
```

**What to check:**
- ✓ Is `symbol` correct?
- ✓ Is `realized_pnl` being passed (should be None if calculated from exit_price)?
- ✓ Is `exit_price` provided?
- ✓ Is `pos_info` populated with entry details?

---

### 2. **PnL Calculation** (`services/trade_service.py`, Step 2)

The formula is: `PnL = (exit_price - entry_price) × qty`

```python
# Look for one of these outputs:

# Case A: PnL calculated from exit_price
[DEBUG STEP 2A] PnL calculated from exit_price:
  formula: (exit_price - entry_price) * qty
  = (6850.0 - 6844.5) * 2
  = 11.0

# Case B: PnL NOT calculated (already provided or missing data)
[DEBUG STEP 2B] PnL NOT calculated:
  realized_pnl provided: True (value=15.0)
  exit_price provided: False (value=None)
```

**If you see Case B with `realized_pnl=None`:**
- ❌ This means `exit_price` is missing
- 💡 Check: Is the position getting an `exit_price` from the DTC message?

---

### 3. **Balance Update** (`services/trade_service.py`, Step 4)

```python
[DEBUG STEP 4] Balance update check:
  state_manager exists: True
  realized_pnl is not None: True
  realized_pnl value: 11.0

[TRADE CLOSED] 📈 MES | SIM Mode
==================================================================
  Entry Price: $6,844.50 | Exit Price: $6,850.00
  Quantity: 2 contracts
  Calculation: (6850.0 - 6844.5) * 2 = 11.0
  P&L: +$11.00
  Previous Balance: $10,000.00
  New Balance: $10,011.00
==================================================================
```

**If balance doesn't update:**
- ❌ Check if `state_manager exists: False` → StateManager not initialized
- ❌ Check if `realized_pnl is not None: False` → PnL calculation failed

---

### 4. **Database Write** (`services/trade_service.py`, Step 5-8)

```python
[DEBUG STEP 5] Creating TradeRecord object:
  symbol=MES
  qty=2
  mode=SIM
  entry_price=6844.5
  entry_time=2025-11-11 08:13:19.123456
  exit_price=6850.0
  exit_time=2025-11-11 08:13:25.654321
  realized_pnl=11.0 (will be stored: 11.0)
  is_closed=True
  account=Sim1

[DEBUG STEP 6] ✓ TradeRecord created, now writing to database...
[DEBUG STEP 7] Trade added to session, committing to database...
[DEBUG STEP 8] ✓ Trade committed to database with ID=42
[DEBUG] Verifying trade was saved:
  - Trade ID: 42
  - Symbol: MES
  - Realized PnL in DB: 11.0
  - Mode in DB: SIM
  - Is Closed: True
```

**If database write fails:**
- Look for: `[DEBUG ERROR] Exception in record_closed_trade():`
- Check the traceback for database connection issues

---

### 5. **Stats Calculation** (`services/stats_service.py`)

```python
[DEBUG STATS] compute_trading_stats_for_timeframe() called:
  timeframe=1D, mode=SIM

[DEBUG STATS] Querying trades from 2025-11-11T00:00:00
[DEBUG STATS] Opening database session...
[DEBUG STATS] Found 5 trades in database for 1D / mode=SIM

[DEBUG STATS] Trade 1: MES | PnL=11.0 | Exit=2025-11-11 08:13:25.654321
  → Added to PnL list: 11.0
[DEBUG STATS] Trade 2: MES | PnL=-5.0 | Exit=2025-11-11 08:14:12.123456
  → Added to PnL list: -5.0
[DEBUG STATS] Trade 3: ES | PnL=20.0 | Exit=2025-11-11 08:15:00.654321
  → Added to PnL list: 20.0

[DEBUG STATS] ✓ Database query complete
  Total PnL values collected: 3
  PnL list: [11.0, -5.0, 20.0]

[DEBUG STATS] Calculation Summary:
  Total PnL: 26.0
  Wins: 2 trades = $31.00
  Losses: 1 trades = $5.00
  Hit Rate: 66.7%
  Max Drawdown: 5.00
  Max Run-Up: 31.00
  Expectancy: 19.33
  Profit Factor: 6.20

[DEBUG STATS] ✓ Stats calculation complete, returning 17 metrics
  Total PnL (formatted): 26.00
  Trade Count: 3
```

**If PnL is 0 but trades exist:**
- Check: "Found X trades in database" → Is it showing trades?
- Check: "PnL list: []" → Are trades missing realized_pnl values?

---

### 6. **Panel 3 Display** (`panels/panel3.py`)

```python
[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf=1D

[DEBUG panel3._load_metrics_for_timeframe] STEP 3: State manager obtained
[DEBUG panel3._load_metrics_for_timeframe] STEP 4: Mode detected as SIM

[DEBUG panel3._load_metrics_for_timeframe] STEP 5: Calling compute_trading_stats_for_timeframe with tf=1D, mode=SIM

[DEBUG panel3._load_metrics_for_timeframe] STEP 6: compute_trading_stats_for_timeframe returned payload with keys: ['Total PnL', 'Max Drawdown', ..., 'Sharpe Ratio']

[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 3

[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics
[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed

[DEBUG panel3._load_metrics_for_timeframe] STEP 10: Sharpe Ratio value: 0.95
[DEBUG panel3._load_metrics_for_timeframe] STEP 11: Sharpe bar updated

[DEBUG panel3._load_metrics_for_timeframe] STEP 12: Total PnL value: 26.0
```

**If metrics don't display:**
- Check: "Trades count for SIM mode in 1D: 0" → No trades found
- Check: "Step 8: No trades found, calling display_empty_metrics" → Empty state shown

---

## Common Issues & Solutions

### Issue 1: PnL Shows as None

```
[DEBUG STEP 2B] PnL NOT calculated:
  realized_pnl provided: False (value=None)
  exit_price provided: False (value=None)
```

**Cause:** Exit price not provided when closing position

**Solution:**
- Check that `on_position_update()` is being called with `qty=0`
- Verify the DTC position update message includes the exit information
- Ensure the position close handler is capturing the last fill price

---

### Issue 2: Database Shows 0 Trades

```
[DEBUG STATS] Found 0 trades in database for 1D / mode=SIM
```

**Cause:** Trades not being saved to database

**Solution:**
- Check Step 8 in trade_service: Is trade committed?
- Verify database connection is working: Check app.log for DB errors
- Check Mode detection: Is the mode "SIM" or "LIVE" matching?

```bash
# Query the database directly:
sqlite> SELECT COUNT(*) FROM trade_record WHERE mode='SIM' AND is_closed=1;
sqlite> SELECT symbol, realized_pnl, mode FROM trade_record LIMIT 10;
```

---

### Issue 3: Total PnL Calculations Wrong

```
[DEBUG STATS] Total PnL: 26.0  # But should be 31.5
  PnL list: [11.0, -5.0, 20.0]
```

**Cause:** Math error in calculation or trades have NULL realized_pnl

**Solution:**
- Check if trades in database have `realized_pnl IS NULL`
- Verify each trade's individual PnL calculation:
  - `(6850 - 6844.5) * 2 = 11.0` ✓
  - `(6839 - 6844) * 1 = -5.0` ✓

---

### Issue 4: Panel 3 Shows Empty Metrics

```
[DEBUG panel3._load_metrics_for_timeframe] STEP 8: No trades found, calling display_empty_metrics
```

**Cause:** No trades for the selected timeframe

**Solution:**
- Change the timeframe pill (1D → 1W → YTD)
- Check app startup: Does it load trades from database?
  - Look for: `[DATABASE LOAD] SIM Balance Restored from Trades`
  - Check: `Trades in Database: X`

---

## How to Enable Full Debug Output

### Option 1: Environment Variable

```bash
# Windows PowerShell
$env:DEBUG_MODE="1"
python main.py

# Windows Command Prompt
set DEBUG_MODE=1
python main.py
```

### Option 2: Edit settings.py

```python
# config/settings.py
DEBUG_MODE = True
```

---

## Reading the Console Output

### Critical Checkpoints

1. **Trade Closes Successfully?**
   ```
   [DEBUG ENTRY] record_closed_trade() called
   [DEBUG STEP 2A] PnL calculated from exit_price:  ← Should see this
   = (exit - entry) * qty
   = <number here>
   ```

2. **Balance Updated?**
   ```
   [DEBUG STEP 4] Balance update check:
     realized_pnl is not None: True  ← MUST be True
   [TRADE CLOSED] 📈 MES | SIM Mode
     P&L: +$11.00  ← Actual PnL value
     New Balance: $10,011.00  ← New balance
   ```

3. **Database Write Success?**
   ```
   [DEBUG STEP 8] ✓ Trade committed to database with ID=42
   [DEBUG] Verifying trade was saved:
     - Realized PnL in DB: 11.0  ← Must match calculated PnL
   ```

4. **Stats Retrieval Success?**
   ```
   [DEBUG STATS] Found 5 trades in database for 1D / mode=SIM
   [DEBUG STATS] PnL list: [11.0, -5.0, 20.0]  ← Should show values
   [DEBUG STATS] Total PnL: 26.0  ← Sum of all
   ```

5. **Panel Shows Metrics?**
   ```
   [DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed
   ```

---

## Debugging Workflow

When PnL isn't calculating:

1. **Check Step 2** - Is PnL being calculated or provided?
2. **Check Step 4** - Is balance being updated?
3. **Check Step 8** - Is trade being saved to database?
4. **Check STATS** - Are trades being queried from database?
5. **Check Panel 3** - Is the UI getting the data?

If you find a ❌ at any step, that's where the issue is!

---

## Example: Full Debug Trace of a Winning Trade

```
====================================================================================================
[DEBUG ENTRY] record_closed_trade() called
  symbol=MES
  realized_pnl=None (type: NoneType)
  exit_price=6850.0 (type: float)
  pos_info={'qty': 2, 'entry_price': 6844.5, 'entry_time': datetime.datetime(2025, 11, 11, 8, 13, 19, 123456), ...}
====================================================================================================

[DEBUG] ✓ Imports successful: get_session and TradeRecord

[DEBUG STEP 1] Extract position info:
  entry_price=6844.5, qty=2
  entry_time=2025-11-11 08:13:19.123456, exit_time=2025-11-11 08:13:25.654321
  account=Sim1

[DEBUG STEP 2A] PnL calculated from exit_price:
  formula: (exit_price - entry_price) * qty
  = (6850.0 - 6844.5) * 2
  = 11.0

[DEBUG STEP 3] Mode detection: mode=SIM

[DEBUG STEP 4] Balance update check:
  state_manager exists: True
  realized_pnl is not None: True
  realized_pnl value: 11.0

================================================================================
[TRADE CLOSED] 📈 MES | SIM Mode
================================================================================
  Entry Price: $6,844.50 | Exit Price: $6,850.00
  Quantity: 2 contracts
  Calculation: (6850.0 - 6844.5) * 2 = 11.0
  P&L: +$11.00
  Previous Balance: $10,000.00
  New Balance: $10,011.00
================================================================================

[DEBUG STEP 5] Creating TradeRecord object:
  symbol=MES
  qty=2
  mode=SIM
  entry_price=6844.5
  entry_time=2025-11-11 08:13:19.123456
  exit_price=6850.0
  exit_time=2025-11-11 08:13:25.654321
  realized_pnl=11.0 (will be stored: 11.0)
  is_closed=True
  account=Sim1

[DEBUG STEP 6] ✓ TradeRecord created, now writing to database...
[DEBUG STEP 7] Trade added to session, committing to database...
[DEBUG STEP 8] ✓ Trade committed to database with ID=1
[DEBUG] Verifying trade was saved:
  - Trade ID: 1
  - Symbol: MES
  - Realized PnL in DB: 11.0
  - Mode in DB: SIM
  - Is Closed: True

[DEBUG STEP 9] ✓ Trade recording completed successfully!

================================================================================
[TRADE SUMMARY] MES trade recorded to database
  - Trade ID: 1
  - Mode: SIM
  - Entry: $6,844.50 | Exit: $6,850.00
  - Quantity: 2 contracts
  - Realized P&L: +$11.00
  - New SIM Balance: $10,011.00
================================================================================

[DEBUG STATS] compute_trading_stats_for_timeframe() called:
  timeframe=1D, mode=SIM

[DEBUG STATS] Querying trades from 2025-11-11T00:00:00
[DEBUG STATS] Opening database session...
[DEBUG STATS] Found 1 trades in database for 1D / mode=SIM

[DEBUG STATS] Trade 1: MES | PnL=11.0 | Exit=2025-11-11 08:13:25.654321
  → Added to PnL list: 11.0

[DEBUG STATS] ✓ Database query complete
  Total PnL values collected: 1
  PnL list: [11.0]

[DEBUG STATS] Calculation Summary:
  Total PnL: 11.0
  Wins: 1 trades = $11.00
  Losses: 0 trades = $0.00
  Hit Rate: 100.0%
  Max Drawdown: 0.00
  Max Run-Up: 11.00
  Expectancy: 11.00
  Profit Factor: inf

[DEBUG STATS] ✓ Stats calculation complete, returning 17 metrics
  Total PnL (formatted): 11.00
  Trade Count: 1

================================================================================

[DEBUG panel3._load_metrics_for_timeframe] STEP 1: Called with tf=1D
[DEBUG panel3._load_metrics_for_timeframe] STEP 3: State manager obtained
[DEBUG panel3._load_metrics_for_timeframe] STEP 4: Mode detected as SIM
[DEBUG panel3._load_metrics_for_timeframe] STEP 5: Calling compute_trading_stats_for_timeframe with tf=1D, mode=SIM
[DEBUG panel3._load_metrics_for_timeframe] STEP 6: compute_trading_stats_for_timeframe returned payload with keys: ['Total PnL', 'Max Drawdown', 'Max Run-Up', 'Expectancy', 'Avg Time', 'Trades', 'Best', 'Worst', 'Hit Rate', 'Commissions', 'Avg R', 'Profit Factor', 'Streak', 'MAE', 'MFE', '_total_pnl_value', '_trade_count', 'Sharpe Ratio']
[DEBUG panel3._load_metrics_for_timeframe] STEP 7: Trades count for SIM mode in 1D: 1
[DEBUG panel3._load_metrics_for_timeframe] STEP 8: Trades found, calling update_metrics
[DEBUG panel3._load_metrics_for_timeframe] STEP 9: update_metrics completed
[DEBUG panel3._load_metrics_for_timeframe] STEP 10: Sharpe Ratio value: inf
[DEBUG panel3._load_metrics_for_timeframe] STEP 11: Sharpe bar updated
[DEBUG panel3._load_metrics_for_timeframe] STEP 12: Total PnL value: 11.0

Panel 3 displays:
  Total PnL: $11.00 ✓
  Trades: 1 ✓
  Hit Rate: 100.0% ✓
```

---

## Need More Help?

- Check `logs/app.log` for full error messages
- Run with `DEBUG_MODE=1` for verbose output
- Verify database integrity: Check for NULL values in `realized_pnl` column
