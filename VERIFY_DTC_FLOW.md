# DTC Message Flow Verification Guide

## Step 1: Enable Debug Logging

Before running the app, enable DTC debug output:

```batch
set DEBUG_DTC=1
set DEBUG_DATA=1
python main.py
```

This will print **every DTC message** to console, showing:

- Message Type number
- Message Type name
- Raw JSON payload
- Timestamp

## Step 2: Watch the DTC Handshake

When app starts, you should see in logs:

```
[AppManager] [DTC] Searching for DTC server at 127.0.0.1:11099
[AppManager] [DTC] Client constructed; initiating TCP connect
[AppManager] DTC connected
```

**Expected next:**

```
[DTC-ALL-TYPES] Type: 2 (LogonResponse)
```

If you DON'T see "LogonResponse", the handshake failed.

---

## Step 3: Check Initial Data Requests

After logon, you should see requests being sent:

```
dtc.request.trade_accounts       # Type 400
dtc.request.positions            # Type 500
dtc.request.orders               # Type 305
dtc.request.fills                # Type 303
dtc.request.balance              # Type 601
```

**Expected responses:**

```
[DTC-ALL-TYPES] Type: 401 (TradeAccountResponse)
[DTC-ALL-TYPES] Type: 306 (PositionUpdate)
[DTC-ALL-TYPES] Type: 301 (OrderUpdate)
[DTC-ALL-TYPES] Type: 304 (HistoricalOrderFillResponse)
[BALANCE RESPONSE] DTC Message Type: 600 (AccountBalanceUpdate)
```

---

## Step 4: Look for Balance Messages Specifically

When balance updates arrive, you'll see:

```
[BALANCE RESPONSE] DTC Message Type: 600 (AccountBalanceUpdate)
   Raw JSON: {'Type': 600, 'balance': 50000.5, 'AccountValue': 50000.5, ...}
```

Or Type 602:

```
[DTC-ALL-TYPES] Type: 602 (AccountBalanceResponse)
```

---

## Step 5: Run the Handshake Capture Tool

For a clean, isolated test without the full app:

```bash
python capture_dtc_handshake.py --host 127.0.0.1 --port 11099 --timeout 10
```

This will:

1. Connect to Sierra Chart
2. Send logon
3. Capture first 20 messages
4. Show EXACTLY what Sierra Chart is sending

---

## What Each Message Type Tells You

| Type | Name                 | Direction | Expected | Indicates                           |
| ---- | -------------------- | --------- | -------- | ----------------------------------- |
| 1    | LogonRequest         | → Sent    | Yes      | App → Sierra Chart                  |
| 2    | LogonResponse        | ← Recv    | Yes      | Sierra Chart → App: Handshake OK    |
| 3    | Heartbeat            | ← Recv    | Maybe    | Keep-alive from server              |
| 400  | TradeAccountsRequest | → Sent    | Yes      | Requesting account list             |
| 401  | TradeAccountResponse | ← Recv    | Yes      | Server: Here are your accounts      |
| 306  | PositionUpdate       | ← Recv    | Maybe    | Position changed                    |
| 601  | BalanceRequest       | → Sent    | Yes      | Requesting balance                  |
| 600  | BalanceUpdate        | ← Recv    | Maybe    | Server: Here's your balance         |
| 602  | BalanceResponse      | ← Recv    | Maybe    | Server: Balance response to request |

---

## Verification Checklist

### Handshake Phase

- [ ] See "DTC connected" log
- [ ] See LogonResponse (Type 2)
- [ ] See TradeAccountResponse (Type 401)

### Data Phase

- [ ] See PositionUpdate (Type 306) messages
- [ ] See BalanceUpdate or BalanceResponse (Type 600 or 602)
- [ ] See OrderUpdate (Type 301) when you trade

### Data Flow

- [ ] Balance messages are being logged
- [ ] Position messages are being logged
- [ ] Graph updates when balance changes

---

## Common Issues & Solutions

### Issue: No LogonResponse

**Cause:** Connection failed or wrong credentials
**Check:**

```bash
# Verify port is correct
netstat -ano | findstr :11099

# Verify DTC server is running
# Check Sierra Chart > Server > DTCServer is enabled
```

### Issue: LogonResponse but no other messages

**Cause:** Request messages not being sent or not being recognized
**Check:**

```bash
# Look for "dtc.request" in logs
grep "dtc.request" logs/app.log

# If not there, check if _request_initial_data() is being called
grep "_request_initial_data\|request_account_balance" logs/app.log
```

### Issue: Balance not arriving

**Cause:** Balance type not being routed properly, or using SIM account
**Check:**

```bash
# Look for balance routing logs
grep "Routing balance\|BALANCE RESPONSE" logs/app.log

# Check your account type
# Type 600 = AccountBalanceUpdate
# Type 602 = AccountBalanceResponse
# Both should work now after our fixes
```

### Issue: Position messages have validation errors

**Cause:** Type field missing in normalized payload
**Status:** FIXED (Type field made optional in Pydantic models)
**Check:**

```bash
# Should NOT see these errors anymore:
grep "validation error for DTCMessage" logs/app.log
```

---

## Key File Locations

| What            | File                      | Line    |
| --------------- | ------------------------- | ------- |
| DTC Client      | `core/data_bridge.py`     | 162     |
| Message Types   | `core/data_bridge.py`     | 37-60   |
| Logon code      | `core/data_bridge.py`     | 235-244 |
| Message Receive | `core/data_bridge.py`     | 372-441 |
| Message Routing | `core/data_bridge.py`     | 118-159 |
| Message Parsing | `services/dtc_schemas.py` | 318-344 |

---

## Enabling Full Debug Mode

For complete diagnosis, set all debug flags:

```batch
set DEBUG_MODE=1
set DEBUG_DTC=1
set DEBUG_DATA=1
set DEBUG_NETWORK=1
set DEBUG_CORE=1
python main.py 2>&1 | tee debug_output.log
```

This captures everything to `debug_output.log` for analysis.

---

## Next Steps After Verification

1. **Run with DEBUG_DTC=1 and DEBUG_DATA=1**
2. **Capture the console output or tail the log file**
3. **Share the key messages** (LogonResponse, TradeAccountResponse, Balance messages)
4. **We can then see EXACTLY what Sierra Chart is sending**

This way we're not guessing - we're verifying with real data.
