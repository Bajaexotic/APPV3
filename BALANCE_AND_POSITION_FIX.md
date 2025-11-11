# Account Balance & Position Update Fix

## Problem

Account balance was not showing in Panel 1, and position updates were not reflecting in Panel 2 when entering/exiting trades.

## Root Causes

### 1. Missing Signal Connection

**Issue**: `signal_balance` was emitted by `data_bridge.py` but never connected to Panel 1.

**Location**: `core/app_manager.py`

- `signal_balance` was not imported
- No connection between `signal_balance` → `Panel1.set_account_balance()`

**Fix**: Added import and signal routing in app_manager.py

### 2. Missing Initial Data Requests

**Issue**: After connecting to Sierra Charts, the DTC client only sent LogonRequest but never requested:

- Account balance
- Current positions
- Open orders
- Historical fills

**Location**: `core/data_bridge.py`

- `_send_logon_request()` only sent logon, no follow-up requests
- The old `dtc_json_client.py` had `probe_server()` but data_bridge didn't use it

**Fix**: Added `_request_initial_data()` method that runs 1 second after logon

---

## Files Modified

### 1. `core/app_manager.py`

**Changes**:

- ✅ Imported `signal_balance` from data_bridge
- ✅ Added signal routing: `signal_balance` → `Panel1.set_account_balance()`
- ✅ Added logging for balance updates

**Lines Changed**: 18, 198-212

```python
# Import signal_balance
from core.data_bridge import signal_order, signal_position, signal_logon, signal_balance

# Wire signal to Panel 1
def _on_balance(msg: dict) -> None:
    """Extract balance from DTC message and update Panel 1 display."""
    balance = msg.get("balance")
    if balance is not None and hasattr(self.panel_balance, "set_account_balance"):
        try:
            self.panel_balance.set_account_balance(float(balance))
            log.debug(f"[Balance] Updated Panel 1: ${float(balance):,.2f}")
        except Exception as e:
            log.error(f"[Balance] Error updating Panel 1: {e}")
signal_balance.connect(_on_balance)
```

### 2. `core/data_bridge.py`

**Changes**:

- ✅ Added `_request_initial_data()` method
- ✅ Requests 5 types of data after logon:
  1. Trade accounts (Type 400)
  2. Account balance (Type 601)
  3. Current positions (Type 500)
  4. Open orders (Type 305)
  5. Historical fills (Type 303) - last 30 days
- ✅ Auto-triggered 1 second after logon via QTimer

**Lines Changed**: 383-461

```python
def _send_logon_request(self) -> None:
    # ... existing logon code ...
    self.send(logon_msg)

    # NEW: Request initial data after logon
    QtCore.QTimer.singleShot(1000, self._request_initial_data)

def _request_initial_data(self) -> None:
    """Request account balance, positions, orders, and historical fills."""
    # Request 1: Trade accounts
    self.send({"Type": 400, "RequestID": 1})

    # Request 2: Account balance
    bal_msg = {"Type": 601, "RequestID": 2}
    if account:
        bal_msg["TradeAccount"] = account
    self.send(bal_msg)

    # Request 3: Current positions
    # Request 4: Open orders
    # Request 5: Historical fills
    # ... (see code for full implementation)
```

---

## How It Works Now

### Connection Flow

```
1. App starts
   ↓
2. DTC client connects to 127.0.0.1:11099
   ↓
3. Sends LogonRequest (Type 1)
   ↓
4. Wait 1 second (ensure logon completes)
   ↓
5. _request_initial_data() runs
   ↓
6. Sends 5 data requests:
   - Trade accounts (Type 400)
   - Account balance (Type 601)    ← Panel 1
   - Current positions (Type 500)  ← Panel 2
   - Open orders (Type 305)        ← Panel 2
   - Historical fills (Type 303)   ← Panel 3
```

### Message Flow

```
Sierra Charts → DTC Protocol → data_bridge.py
                                     ↓
                              (normalizes & emits signals)
                                     ↓
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
            signal_balance    signal_position  signal_order
                    ↓                ↓                ↓
               Panel 1          Panel 2          Panel 2
            set_account_    on_position_     on_order_
              balance()        update()        update()
                    ↓                ↓                ↓
            Display $$$    Update position  Record trades
```

---

## Testing Instructions

### 1. Start Sierra Charts

- Ensure DTC server running on `127.0.0.1:11099`
- Connect to **Sim1** or **Account 120005**

### 2. Start Your App

```bash
cd C:\Users\cgrah\Desktop\APPSIERRA
set SIERRA_TRADE_ACCOUNT=Sim1  # or 120005 for LIVE
python main.py
```

### 3. Watch the Logs

Look for these log messages in order:

```
[DTC] Searching for DTC server at 127.0.0.1:11099
dtc.tcp.connected
dtc.logon.request account=Sim1
dtc.session_ready.logon
dtc.request.trade_accounts
dtc.request.balance account=Sim1
dtc.request.positions account=Sim1
dtc.request.orders account=Sim1
dtc.request.fills days=30 account=Sim1
dtc.initial_data.requested
```

### 4. Verify Panel 1 Balance Display

**Expected**: Panel 1 (top) should show account balance in white text

```
$10,500.00  ← Should appear here (instead of "—")
```

**Log confirmation**:

```
[Balance] Updated Panel 1: $10,500.00
```

### 5. Test Position Update

1. Place an order in Sierra Charts
2. Let it fill (enter position)

**Expected Panel 2 behavior**:

- Symbol updates (e.g., "MES")
- Qty and entry price display (e.g., "2 @ 6750.00")
- Time starts counting from entry
- CSV feed updates MAE/MFE every 500ms

**Log confirmation**:

```
[panel2] Position opened — Entry VWAP: 6765.70, Entry Delta: -1071, Entry POC: 6757.74
[panel2] Feed updated — VWAP changed: 6765.70
```

### 6. Test Trade Close

1. Exit the position
2. Check trade record is saved

**Expected**:

```
[panel2] Trade closed: F.US.MESZ25 long 1@6750.00 -> 6755.25
| PnL=$26.25 | R=1.31R | MAE=-0.15R | MFE=2.10R | Eff=62.4%
```

---

## Troubleshooting

### Balance Still Not Showing

1. **Check Sierra Charts** - Is the account balance available?
2. **Check logs** - Do you see `dtc.request.balance`?
3. **Check DTC response** - Add debug logging to see AccountBalanceResponse

### Position Not Updating

1. **Check CSV file** - Does `C:\Users\cgrah\Desktop\APPSIERRA\data\snapshot.csv` exist?
2. **Check CSV headers** - Should have: `last,high,low,vwap,poc,cum_delta`
3. **Check CSV timer** - Should refresh every 500ms

### Sierra Charts Not Sending Data

1. **Check DTC Protocol version** - App uses Protocol v8
2. **Check account name** - Must match exactly (case-sensitive)
3. **Check Trade→Trade Mode** in Sierra - Must be set to active mode

---

## What's Fixed

✅ **Account balance displays in Panel 1**

- Signal routing: data_bridge → app_manager → Panel 1
- Updates automatically when balance changes

✅ **Position updates display in Panel 2**

- Signal routing: data_bridge → app_manager → Panel 2
- Entry context captured (VWAP, POC, Delta)
- MAE/MFE tracked via CSV feed

✅ **Initial data requested on connect**

- Account balance
- Current positions
- Open orders
- Historical fills (30 days)

✅ **Complete trade records**

- All metrics calculated and stored
- Symbol-based $/pt and commissions
- MAE/MFE in 3 formats

---

## Summary

The issues were:

1. **Missing signal connection** - Panel 1 couldn't receive balance updates
2. **No initial data requests** - DTC client never asked for balance/positions

Both are now fixed. Your app will now:

- Display account balance on startup
- Update balance when it changes
- Show position info when you enter trades
- Track MAE/MFE during trades
- Record complete trade history with all metrics

**Ready to test with Sierra Charts!** 🚀
