# DTC Verification Plan - No Guessing, Just Data

## You're Right: We Should Verify, Not Guess

Instead of making assumptions about what Sierra Chart is sending, we'll capture the actual messages and verify the handshake properly.

---

## Quick Start: Run This Now

### Option 1: Simplest - Visual Console Debug

```batch
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
RUN_DTC_VERIFICATION.bat
```

This will:

1. Set `DEBUG_DTC=1` and `DEBUG_DATA=1` environment variables
2. Start the app
3. Print EVERY DTC message to console in real-time
4. Show exactly what Sierra Chart is sending

**What to look for:**

```
[DTC-ALL-TYPES] Type: 2 (LogonResponse)        ← Handshake OK
[DTC-ALL-TYPES] Type: 401 (TradeAccountResponse)  ← Got accounts
[BALANCE RESPONSE] Type: 600 (AccountBalanceUpdate) ← Got balance
[DTC-ALL-TYPES] Type: 306 (PositionUpdate)    ← Got positions
```

---

### Option 2: Raw Socket Capture - No App Interference

For an isolated test that connects directly to Sierra Chart:

```batch
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
python capture_dtc_handshake.py --host 127.0.0.1 --port 11099 --timeout 10
```

This will:

1. Connect to Sierra Chart DTC directly (not through your app)
2. Send logon
3. Capture raw JSON messages
4. Show structure of what's being sent
5. Print all message types received

**Output format:**

```
→ [SEND] LOGON_REQUEST
─────────────────────────────────
{
  "Type": 1,
  "ProtocolVersion": 12,
  ...
}

← [RECV] LOGON_RESPONSE
─────────────────────────────────
{
  "Type": 2,
  "LogonStatus": 1,
  ...
}
```

---

## What We'll Learn From Verification

### From the actual handshake, we'll see

1. **Does logon work?**
   - Yes: We see Type 2 (LogonResponse)
   - No: We see connection error or timeout

2. **Does Sierra Chart send our account info?**
   - Yes: We see Type 401 (TradeAccountResponse)
   - No: We never see it

3. **Does Sierra Chart send balance?**
   - Yes: We see Type 600 or 602
   - No: We never see it
   - **If not:** Balance is probably only available for LIVE accounts, not SIM

4. **What fields are in the balance message?**
   - We'll see the exact JSON structure
   - Can see which field contains the balance value
   - Can see if Type field is present or stripped

5. **Do positions come through?**
   - Yes: We see Type 306 (PositionUpdate)
   - No: We never see it

---

## How to Capture and Share Results

### Step 1: Run verification with debug enabled

```batch
REM Set these environment variables
set DEBUG_DTC=1
set DEBUG_DATA=1

REM Start the app
python main.py 2>&1 | tee dtc_capture.txt
```

Or use the batch file:

```batch
RUN_DTC_VERIFICATION.bat
```

### Step 2: Let it run for 30 seconds

- Let the app connect
- Let it send initial data requests
- Let it receive responses

### Step 3: Copy the console output

Look for these key sections:

**Handshake (first message):**

```
[DTC-ALL-TYPES] Type: 2 (LogonResponse)
```

**Account info:**

```
[DTC-ALL-TYPES] Type: 401 (TradeAccountResponse)
```

**Balance (might see these):**

```
[BALANCE RESPONSE] DTC Message Type: 600
   Raw JSON: {...}

[BALANCE RESPONSE] DTC Message Type: 602
   Raw JSON: {...}
```

**Positions:**

```
[DTC-ALL-TYPES] Type: 306 (PositionUpdate)
```

### Step 4: Share the captured lines

Once you run it, you'll have concrete data showing:

- ✓ What messages arrive
- ✓ In what order
- ✓ What fields they contain
- ✓ Whether Type field is present

Then we can fix any actual issues instead of guessing.

---

## What Each Tool Shows

| Tool                       | Use When              | Shows                               |
| -------------------------- | --------------------- | ----------------------------------- |
| `RUN_DTC_VERIFICATION.bat` | Want to test full app | Real handshake + data from app      |
| `capture_dtc_handshake.py` | Want isolated test    | Raw JSON from Sierra Chart directly |
| App logs with DEBUG_DTC    | Troubleshooting       | Filtered DTC messages only          |

---

## Expected vs Actual

### Best Case (Everything Works)

```
[AppManager] DTC connected
[DTC-ALL-TYPES] Type: 2 (LogonResponse)              ✓ Handshake OK
[DTC-ALL-TYPES] Type: 401 (TradeAccountResponse)   ✓ Accounts received
[DTC-ALL-TYPES] Type: 306 (PositionUpdate)         ✓ Positions received
[BALANCE RESPONSE] DTC Message Type: 600           ✓ Balance received
Raw JSON: {'Type': 600, 'balance': 50000, ...}
```

### Partial (Some Data Missing)

```
[AppManager] DTC connected
[DTC-ALL-TYPES] Type: 2 (LogonResponse)             ✓ Handshake OK
[DTC-ALL-TYPES] Type: 401 (TradeAccountResponse)   ✓ Accounts received
[DTC-ALL-TYPES] Type: 306 (PositionUpdate)         ✓ Positions received
(No balance messages)                              ✗ Balance NOT received
```

**Likely cause:** SIM account doesn't send balance (Sierra Chart design)

### Broken (Handshake Failed)

```
[AppManager] DTC connected
(Nothing else arrives)                             ✗ No response to handshake
```

**Likely cause:** Wrong credentials, DTC server not enabled, firewall

---

## After Verification: What We'll Do

Once we see the actual messages:

1. **If balance arrives:**
   - ✓ Data flow is working
   - Fix any remaining validation/routing issues

2. **If balance doesn't arrive (SIM account):**
   - Document this as a Sierra Chart limitation
   - Build equity curve from fills instead

3. **If handshake fails:**
   - Fix connection credentials
   - Verify DTC server is running

4. **If messages have unexpected format:**
   - Update message type mapping
   - Fix validation schemas

---

## Commands Quick Reference

```bash
# Run with debug enabled
set DEBUG_DTC=1 && set DEBUG_DATA=1 && python main.py

# Run capture tool directly
python capture_dtc_handshake.py

# Run verification batch file
RUN_DTC_VERIFICATION.bat

# Check for balance messages in logs
grep -i "balance" logs/app.log | head -20

# Check all DTC types that arrived
grep "DTC-ALL-TYPES" logs/app.log | sort | uniq
```

---

## Summary

**Instead of guessing, we will:**

1. ✅ Capture real handshake messages
2. ✅ See exactly what Sierra Chart sends
3. ✅ Verify field names and types
4. ✅ Fix issues based on actual data, not assumptions

**This way we know exactly what's working and what's not.**

Ready to verify? Run `RUN_DTC_VERIFICATION.bat` and share the output.
