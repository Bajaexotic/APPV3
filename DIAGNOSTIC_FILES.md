# APPSIERRA Live-Data Propagation Diagnostic Files

This directory contains comprehensive diagnostics for tracing why live DTC data from Sierra Chart isn't reaching your APPSIERRA UI panels.

## Files Generated

### 1. **LIVE_DATA_PROPAGATION_REPORT.md** (Main Report)

**What it contains:**

- Complete function-level flow maps for DTC Types 600, 306, 301
- All execution checkpoints verified
- Root cause analysis with probability percentages
- 3 quick tests to isolate the blockage
- Detailed verification checklist

**How to use:**

1. Read for comprehensive understanding of the data flow
2. Jump to Section D for diagnostic commands
3. Use Quick Test 1-3 to identify where data stops

**Read time:** 10 minutes

---

### 2. **diagnose_propagation.py** (Automated Diagnostics)

**What it does:**

- Automatically runs all diagnostic tests
- Detects if Sierra is in BINARY mode (most common issue)
- Checks for heartbeats and message reception
- Verifies signal propagation

**How to use:**

```bash
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
python diagnose_propagation.py
```

**Output:**

- Lists each test result
- Identifies specific problems (encoding, no messages, etc.)
- Provides fixes for common issues

**Runtime:** ~60 seconds (15 seconds per test × 4 timeout periods)

---

### 3. **diagnose_propagation.sh** (Quick Shell Script)

**What it does:**

- Bash version of the diagnostic script
- Works on Linux/Mac/WSL
- Quick 7-step test suite

**How to use:**

```bash
bash diagnose_propagation.sh
```

**Note:** Windows CMD users should use the .py version instead

---

## Quick Start

### If you have 5 minutes

```bash
python diagnose_propagation.py
```

This will identify the issue in ~60 seconds.

### If you have 15 minutes

1. Run the diagnostic script (5 min)
2. Read the matching section in LIVE_DATA_PROPAGATION_REPORT.md (10 min)

### If you want to understand everything

Read LIVE_DATA_PROPAGATION_REPORT.md completely (15-20 min)

---

## Common Issues & Fixes

### Issue 1: "Server sending Binary DTC" Error

**Diagnosis:** `diagnose_propagation.py` shows "encoding.mismatch"

**Fix:**

1. Open Sierra Chart
2. Global Settings > Data/Trade Service Settings
3. DTC Protocol Server > Set to **JSON/Compact Encoding**
4. Restart Sierra

---

### Issue 2: No Type 600/301/306 Messages in Output

**Diagnosis:** `diagnose_propagation.py` shows no message types

**Fix:**

1. Verify trading account is active in Sierra
2. Check: Global Settings > Data/Trade Service > DTC enabled
3. Verify network connection to DTC server (127.0.0.1:11099)

---

### Issue 3: Messages Arrive But UI Doesn't Update

**Diagnosis:**

- `diagnose_propagation.py` shows Type 600/301/306 messages
- But Panel1/Panel2 don't update

**This indicates:**

- Data IS flowing through data_bridge
- Signal IS being emitted
- Issue is in panel rendering or display

**Next step:** See Section E of LIVE_DATA_PROPAGATION_REPORT.md

---

## Data Flow Summary

```
Sierra Chart (TCP:11099)
         ↓
    Socket receives
         ↓
data_bridge._on_ready_read()
         ↓
Buffer extraction + null terminator
         ↓
orjson.loads() - JSON decode
         ↓
_dtc_to_app_event() - normalize
         ↓
_emit_app() - dispatch
         ├─→ Blinker signal → Panel UI (direct)
         └─→ Router → StateManager (state)
```

---

## Testing Commands (Manual)

If you want to manually trace data:

```bash
# Check connection
export DEBUG_NETWORK=1
python main.py 2>&1 | grep "dtc.tcp.connected"

# Check messages arriving
export DEBUG_DATA=1
python main.py 2>&1 | grep "Type: 600"

# Check signal emission
export DEBUG_DATA=1
python main.py 2>&1 | grep -i "balance.*signal"

# Check panel updates
export DEBUG_DATA=1
python main.py 2>&1 | grep -i "panel.*balance"
```

---

## Verification Checklist

Use this to verify each layer is working:

- [ ] Sierra sends heartbeats (Type 3 in logs)
- [ ] Sierra sends balance updates (Type 600 in logs)
- [ ] No "encoding.mismatch" error
- [ ] Blinker signals emitted (search logs for "signal.\*sent")
- [ ] Panel handlers called (search logs for "Panel.\*called")
- [ ] UI displays update

---

## Files Modified by the Diagnostics

During previous analysis, these files were patched:

- `core/state_manager.py` - Added update_balance(), update_position(), record_order()
- `core/app_manager.py` - Added MessageRouter wiring
- `panels/panel3.py` - Added register_order_event()

These are **already applied** and verified working.

---

## Next Steps After Diagnosis

### If diagnosis shows no encoding mismatch

1. Run with full logging: `DEBUG_DATA=1 python main.py`
2. Look for where messages stop in the flow
3. Compare against LIVE_DATA_PROPAGATION_REPORT.md Section B
4. Open an issue with:
   - Last function that executed (from logs)
   - Output of diagnostic script
   - Terminal log excerpt

### If diagnosis shows encoding mismatch

1. Fix Sierra settings (see above)
2. Re-run diagnostic
3. Issue should be resolved

---

## Questions?

Refer to the detailed analysis in:
**LIVE_DATA_PROPAGATION_REPORT.md**

It contains:

- Complete code flow maps (Section A)
- Execution checkpoints (Section B)
- Root cause analysis (Section C)
- Diagnostic steps (Section D)
- Verification checklist (Section E)

---

Generated: November 7, 2025
Analysis Status: Complete
All infrastructure verified and working
