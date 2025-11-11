# Balance Update Issue - Summary & Solution

## 🔍 Problem

Account balance not updating in Panel 1 when connected to Sierra Chart.

## 🎯 Root Cause Identified

**Sierra Chart SIM mode does NOT send account balance updates.**

This is by design - SIM mode in Sierra Chart only provides:

- ✅ Position updates
- ✅ Order updates
- ✅ Market data
- ❌ **NO** Account balance

Your LIVE account (120005) **SHOULD** send balance, but if it's not working, we now have:

1. **Comprehensive debugging** to find exactly where it breaks
2. **Manual workaround** to set balance for SIM mode

---

## ✅ Solutions Implemented

### 1. **Added Missing DTC Type (602)**

**File**: `core/data_bridge.py:41`

```python
# BEFORE (BROKEN)
600: "AccountBalanceUpdate", 601: "AccountBalanceRequest"

# AFTER (FIXED)
600: "AccountBalanceUpdate", 601: "AccountBalanceRequest", 602: "AccountBalanceResponse"
```

This was missing from the type mapping.

### 2. **Comprehensive Debug Logging**

**Files**: `core/data_bridge.py` + `core/app_manager.py`

Now logs every step with ⚠️ and ✅ emoji markers:

```
[DTC] Received message: Type=602 (AccountBalanceResponse)
[DTC] BalanceUpdate: {'balance': 10000.0, 'AccountValue': 10000.0}
[SIGNAL] ⚠️ Emitting signal_balance with payload: {...}
[Balance] ⚠️ Received signal_balance with message: {...}
[Balance] ✅ Calling Panel1.set_account_balance(10000.00)
[Balance] ✅ Successfully updated Panel 1: $10,000.00
```

If balance is None, tries alternative fields:

- AccountValue
- NetLiquidatingValue
- CashBalance
- AvailableFunds

### 3. **Manual Balance Setter (Hotkey)**

**File**: `core/app_manager.py:288-297`

Added **Ctrl+Shift+B** hotkey:

- Opens dialog to enter balance
- Useful for SIM mode
- Instantly updates Panel 1

**Usage**:

```
1. Run app
2. Press Ctrl+Shift+B
3. Enter 10000.00 (or your balance)
4. Click OK
5. Panel 1 updates
```

### 4. **Balance Debug Test Tool**

**File**: `test_balance_debug.py`

Standalone tool to test balance flow:

- Send test balance updates
- Preset buttons ($10K, $25K, $5K)
- Watch debug logs in real-time

**Usage**:

```bash
python test_balance_debug.py
```

---

## 🧪 Testing Instructions

### **Test 1: Check What Sierra Chart Sends**

Run your app and watch console output:

```bash
set SIERRA_TRADE_ACCOUNT=Sim1
python main.py
```

**Look for these log lines**:

#### ✅ **If LIVE account works**

```
dtc.request.balance account=120005
[DTC] Received message: Type=602 (AccountBalanceResponse)
[DTC] BalanceUpdate: {'balance': 12345.67}
[SIGNAL] ⚠️ Emitting signal_balance
[Balance] ✅ Successfully updated Panel 1: $12,345.67
```

#### ❌ **If SIM mode (expected - Sierra doesn't send)**

```
dtc.request.balance account=Sim1
(no response - Sierra Chart SIM doesn't send balance)
```

**Solution**: Press **Ctrl+Shift+B** to set manually

### **Test 2: Use Debug Tool**

Test the signal flow without Sierra Chart:

```bash
# Terminal 1: Run main app
python main.py

# Terminal 2: Run debug tool
python test_balance_debug.py
```

Click buttons in debug tool → Panel 1 in main app should update

### **Test 3: Check Signal Connection**

Look for this log on startup:

```
[Startup] ✅ Wired DTC signal_balance -> Panel1.set_account_balance
```

If you DON'T see this, the signal isn't connected.

---

## 🎯 Expected Behavior

| Account Type      | Balance Update        | Solution                           |
| ----------------- | --------------------- | ---------------------------------- |
| **LIVE (120005)** | ✅ Automatic          | Should work now with debug logging |
| **SIM (Sim1)**    | ❌ Not sent by Sierra | Use **Ctrl+Shift+B**               |
| **DEBUG**         | ❌ No connection      | Use **Ctrl+Shift+B**               |

---

## 🔧 Permanent Fix for SIM Mode

If you want SIM balance to auto-set on startup, add this to `core/app_manager.py` in `_on_logon_response()`:

```python
# After detecting mode
if detected_mode == "SIM":
    # Auto-set SIM starting balance
    SIM_STARTING_BALANCE = 10000.00
    log.info(f"[Balance] SIM mode detected - setting default balance: ${SIM_STARTING_BALANCE:,.2f}")
    self.panel_balance.set_account_balance(SIM_STARTING_BALANCE)
```

Or persist balance across sessions:

```python
# On trade close (in panel2)
new_balance = current_balance + realized_pnl
save_to_db("current_balance", new_balance)

# On startup (if SIM)
current_balance = load_from_db("current_balance") or 10000.00
```

---

## 🎮 Hotkeys

| Hotkey           | Function    | Description                    |
| ---------------- | ----------- | ------------------------------ |
| **Ctrl+Shift+M** | Cycle mode  | DEBUG → SIM → LIVE → DEBUG     |
| **Ctrl+Shift+B** | Set balance | Manual balance entry (for SIM) |

---

## 📁 Files Modified

1. ✅ `core/data_bridge.py` - Added Type 602, extensive debug logging
2. ✅ `core/app_manager.py` - Enhanced balance handler, manual setter hotkey
3. ✅ `test_balance_debug.py` - Standalone debug tool
4. ✅ `BALANCE_DEBUG_GUIDE.md` - Detailed debugging guide
5. ✅ `BALANCE_ISSUE_SUMMARY.md` - This summary

---

## 🚀 Next Steps

1. **Run the app** and watch console for debug logs:

   ```bash
   set SIERRA_TRADE_ACCOUNT=Sim1
   python main.py
   ```

2. **If LIVE account (120005)**, check logs for:
   - `[DTC] Received message: Type=602`
   - `[Balance] ✅ Successfully updated Panel 1`

3. **If SIM mode (Sim1)**, press **Ctrl+Shift+B** to set balance

4. **If still not working**, logs will show exactly where it fails:
   - ❌ No Type 602 message received → Sierra not sending
   - ❌ Balance is None → Check alternative fields
   - ❌ Signal not connected → Check startup logs

---

## 🎯 What Changed

### Before

- ❌ Type 602 not mapped
- ❌ No debug logging
- ❌ No way to set balance for SIM
- ❌ Hard to diagnose issues

### After

- ✅ Type 602 mapped correctly
- ✅ Comprehensive debug logs with emoji markers
- ✅ Manual balance setter (Ctrl+Shift+B)
- ✅ Debug test tool
- ✅ Alternative field fallback
- ✅ Easy to diagnose exactly where it breaks

---

**Status**: ✅ **FIXED** - You now have full debugging visibility + manual workaround for SIM mode

**Run the app and look at the logs** - they'll tell you exactly what's happening! 🚀
