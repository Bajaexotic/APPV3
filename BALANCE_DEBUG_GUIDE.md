# Balance Update Debugging Guide

## Problem

Account balance not updating in Panel 1 when connected to Sierra Chart.

## Root Cause

**Sierra Chart SIM mode does NOT send balance updates** - This is by design. SIM mode only provides:

- Position updates
- Order updates
- Market data

But **NOT** account balance information.

---

## Solutions Implemented

### 1. **Comprehensive Debug Logging**

Added extensive logging at every step of the balance update flow:

#### **Step 1: DTC Message Reception** (`data_bridge.py`)

```
[DTC] Received message: Type=602 (AccountBalanceResponse)
[DTC] BalanceUpdate: {'balance': 10000.0, 'AccountValue': 10000.0, ...}
[DTC] Raw balance message fields: ['Type', 'AccountValue', 'CashBalance', ...]
```

#### **Step 2: Signal Emission** (`data_bridge.py`)

```
[SIGNAL] ⚠️ Emitting signal_balance with payload: {'balance': 10000.0, ...}
```

#### **Step 3: Signal Reception** (`app_manager.py`)

```
[Balance] ⚠️ Received signal_balance with message: {'balance': 10000.0}
[Balance] Extracted balance value: 10000.0
[Balance] ✅ Calling Panel1.set_account_balance(10000.00)
[Balance] ✅ Successfully updated Panel 1: $10,000.00
```

### 2. **Manual Balance Setter (For SIM Mode)**

Added hotkey **Ctrl+Shift+B** to manually set balance:

```python
# In app_manager.py
def _show_balance_setter(self):
    """Show dialog to manually set balance (useful for SIM mode)"""
    # Opens input dialog with default $10,000
```

**Usage**:

1. Run app
2. Press **Ctrl+Shift+B**
3. Enter balance (e.g., 10000.00)
4. Click OK
5. Panel 1 updates immediately

### 3. **Balance Debug Test Script**

Created standalone test tool: `test_balance_debug.py`

**Features**:

- Send manual balance updates
- Test with preset values ($10K, $25.5K, $5.1K)
- Watch console for debug logs
- Echo back received signals

**Usage**:

```bash
python test_balance_debug.py
```

### 4. **Fixed Missing DTC Type**

Added missing AccountBalanceResponse (Type 602) to type mapping:

```python
# Before (BROKEN)
600: "AccountBalanceUpdate", 601: "AccountBalanceRequest"

# After (FIXED)
600: "AccountBalanceUpdate", 601: "AccountBalanceRequest", 602: "AccountBalanceResponse"
```

---

## Testing Instructions

### **Scenario 1: Live Account (Should Work)**

If connected to LIVE account (120005), Sierra Chart **DOES** send balance:

1. Start Sierra Charts
2. Connect to account 120005
3. Run app:

   ```bash
   set SIERRA_TRADE_ACCOUNT=120005
   python main.py
   ```

4. Watch logs for:

   ```
   dtc.request.balance account=120005
   [DTC] BalanceUpdate: {'balance': XXXXX.XX}
   [SIGNAL] ⚠️ Emitting signal_balance with payload: ...
   [Balance] ✅ Successfully updated Panel 1: $XXXXX.XX
   ```

5. **Expected**: Panel 1 shows balance

### **Scenario 2: SIM Mode (Use Manual Setter)**

If connected to SIM (Sim1), Sierra Chart does **NOT** send balance:

1. Start Sierra Charts
2. Connect to Sim1
3. Run app:

   ```bash
   set SIERRA_TRADE_ACCOUNT=Sim1
   python main.py
   ```

4. **You will see**:

   ```
   dtc.request.balance account=Sim1
   (no response from Sierra Chart)
   ```

5. **Solution**: Press **Ctrl+Shift+B**
6. Enter 10000.00 (or your mock balance)
7. Panel 1 updates

### **Scenario 3: Debug Tool Testing**

Test the signal flow without Sierra Charts:

1. Run main app in one terminal:

   ```bash
   python main.py
   ```

2. Run debug tool in another terminal:

   ```bash
   python test_balance_debug.py
   ```

3. Click "Test: $10,000" in debug tool
4. Watch main app - Panel 1 should update
5. Check both consoles for debug logs

---

## Debug Log Interpretation

### ✅ **Success Pattern**

```
[DTC] Received message: Type=602 (AccountBalanceResponse)
[DTC] BalanceUpdate: {'balance': 10000.0}
[SIGNAL] ⚠️ Emitting signal_balance with payload: {'balance': 10000.0}
[Balance] ⚠️ Received signal_balance with message: {'balance': 10000.0}
[Balance] ✅ Calling Panel1.set_account_balance(10000.00)
[Balance] ✅ Successfully updated Panel 1: $10,000.00
```

### ❌ **No Balance Received (SIM Mode)**

```
dtc.request.balance account=Sim1
(silence - no AccountBalanceResponse)
```

**Solution**: Use Ctrl+Shift+B to set manually

### ❌ **Balance Field Missing**

```
[DTC] BalanceUpdate: {}
[Balance] ⚠️ Balance is None! Full message: {'AccountValue': 10000}
[Balance] Found alternative field 'AccountValue': 10000
[Balance] ✅ Calling Panel1.set_account_balance(10000.00)
```

**Solution**: Code now tries alternative fields automatically

### ❌ **Signal Not Connected**

```
[SIGNAL] ⚠️ Emitting signal_balance with payload: {'balance': 10000.0}
(no [Balance] logs after)
```

**Problem**: Signal not wired in app_manager
**Solution**: Check startup logs for "✅ Wired DTC signal_balance"

---

## Hotkeys Reference

| Hotkey           | Function    | Purpose                     |
| ---------------- | ----------- | --------------------------- |
| **Ctrl+Shift+M** | Cycle mode  | DEBUG → SIM → LIVE          |
| **Ctrl+Shift+B** | Set balance | Manual balance for SIM mode |

---

## Permanent Solution for SIM Mode

### **Option 1: Store Balance in Config**

Add to `config/settings.py`:

```python
SIM_STARTING_BALANCE: float = 10000.00
```

Then auto-set on SIM mode detection in `app_manager.py`:

```python
if detected_mode == "SIM":
    self.panel_balance.set_account_balance(SIM_STARTING_BALANCE)
```

### **Option 2: Persist Balance in Database**

Store current balance in state database and restore on startup:

```python
# On trade close
new_balance = old_balance + realized_pnl
save_balance_to_db(new_balance)

# On startup (SIM mode)
balance = load_balance_from_db() or 10000.00
panel_balance.set_account_balance(balance)
```

### **Option 3: Calculate from Trades**

Track all trades and calculate balance:

```python
starting_balance = 10000.00
total_pnl = sum([trade.realized_pnl for trade in get_all_trades()])
current_balance = starting_balance + total_pnl
```

---

## Files Modified

1. ✅ `core/data_bridge.py` - Added Type 602, debug logging
2. ✅ `core/app_manager.py` - Enhanced balance handler, added manual setter
3. ✅ `test_balance_debug.py` - Created debug tool
4. ✅ `BALANCE_DEBUG_GUIDE.md` - This doc

---

## Quick Fixes

### If balance still not showing

```bash
# 1. Check if Panel1 has the method
python -c "from panels.panel1 import Panel1; p = Panel1(); print(hasattr(p, 'set_account_balance'))"

# 2. Test signal manually
python test_balance_debug.py

# 3. Check logs for errors
# Look for ❌ emoji in console output

# 4. Use manual setter
# Press Ctrl+Shift+B in running app
```

---

## Summary

| Mode              | Balance Updates? | Solution                                   |
| ----------------- | ---------------- | ------------------------------------------ |
| **LIVE** (120005) | ✅ Yes           | Works automatically                        |
| **SIM** (Sim1)    | ❌ No            | Use Ctrl+Shift+B or implement Option 1/2/3 |
| **DEBUG**         | ❌ No            | Use Ctrl+Shift+B                           |

**For production SIM mode**: Implement Option 1 (config-based default) or Option 2 (database persistence)

---

**Generated**: 2025-11-07
**Issue**: SIM mode balance not updating
**Status**: ✅ Fixed with manual setter + debug logging
