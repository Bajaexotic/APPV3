# BUG FIX: Live Balance Showing in SIM Mode - COMPLETE SOLUTION

## The Problem You Experienced

When you switched to SIM mode, you still saw your **LIVE account balance** displayed, not the SIM balance.

Example:
```
Expected: SIM mode shows $10,000.00
Actual:   SIM mode shows $45,328.50 (your live account balance)
```

This happened because:
1. Sierra Chart sends balance updates for the LIVE account (120005)
2. MessageRouter received them but didn't check the current mode
3. It displayed the LIVE balance even when you were in SIM mode

---

## The Root Cause

There were **THREE bugs**:

### Bug #1: `_update_balance_ui()` (Line 284)
Did not check if incoming balance was for the current mode.

### Bug #2: `_on_balance_update()` (Line 351)
Detected the mode but ignored it when updating the UI.

### Bug #3: `switch_equity_curve_for_mode()` (Line 727)
When switching modes, updated the equity curve but NOT the balance label.

---

## The Complete Fix

### Fix #1: Add mode check to `_update_balance_ui()`

**File**: `core/message_router.py` (Lines 276-298)

```python
def _update_balance_ui(self, balance_value: float, mode: Optional[str] = None):
    try:
        if self.panel_balance and self.state:
            # ✅ NEW: Only update if balance is for the CURRENT mode!
            if mode and mode != self.state.current_mode:
                log.debug(f"balance for {mode}, current is {self.state.current_mode}")
                return  # SKIP if wrong mode

            self.panel_balance.set_account_balance(balance_value)
            self.panel_balance.update_equity_series_from_balance(balance_value, mode=mode)
```

### Fix #2: Add mode check to `_on_balance_update()`

**File**: `core/message_router.py` (Lines 345-373)

```python
def _on_balance_update(self, payload: dict):
    bal = payload.get("balance")
    mode = detect_mode_from_account(account)

    # Store balance in state manager (for all modes)
    if self.state:
        self.state.set_balance_for_mode(mode, float(bal))

    # ✅ NEW: Only update UI if balance is for the CURRENT mode!
    if self.panel_balance and self.state:
        if mode and mode != self.state.current_mode:
            log.debug(f"UI ignored - balance for {mode}")
            return  # SKIP if wrong mode

        self.panel_balance.set_account_balance(bal)
```

### Fix #3: Update balance label when switching modes

**File**: `panels/panel1.py` (Lines 727-758)

```python
def switch_equity_curve_for_mode(self, mode: str) -> None:
    """Switch equity curve AND update balance label for the new mode."""
    mode = mode.upper()
    self._current_display_mode = mode if mode != "DEBUG" else "SIM"

    # ✅ NEW: Update balance label to show correct mode's balance!
    try:
        state = get_state_manager()
        if state:
            if self._current_display_mode == "SIM":
                balance = state.sim_balance
            else:
                balance = state.live_balance
            self.set_account_balance(balance)  # Update label!
    except Exception as e:
        log.debug(f"Could not update balance on mode switch: {e}")

    # Redraw the graph
    self._replot_from_cache()
```

---

## How It Works Now

### Scenario 1: SIM Mode, LIVE Balance Arrives

```
Current state:
  ├─ Current mode: "SIM"
  ├─ Panel1 shows: $10,000.00 (SIM balance)
  └─ StateManager.sim_balance = $10,000.00

Sierra Chart sends:
  ├─ Account: 120005 (LIVE account)
  └─ Balance: $45,328.50

MessageRouter receives:
  ├─ Detect mode = "LIVE"
  ├─ Update StateManager.live_balance = $45,328.50 ✓
  ├─ Check: Is mode "LIVE" == current mode "SIM"? NO!
  └─ SKIP UI update ✓ (don't change what's shown)

Result:
  ├─ StateManager.sim_balance = $10,000.00
  ├─ StateManager.live_balance = $45,328.50 ✓ (stored)
  └─ Panel1 shows: $10,000.00 ✓ (unchanged)
```

### Scenario 2: User Switches to LIVE Mode

```
Current state:
  ├─ Current mode: "SIM"
  ├─ Panel1 shows: $10,000.00
  └─ StateManager.live_balance = $45,328.50 (waiting)

User presses: Ctrl+Shift+M (mode switcher)

Panel1.set_trading_mode("LIVE") called:
  ├─ Switch theme to LIVE
  └─ Call switch_equity_curve_for_mode("LIVE")

switch_equity_curve_for_mode("LIVE"):
  ├─ Set _current_display_mode = "LIVE"
  ├─ Get state.live_balance = $45,328.50
  ├─ Call set_account_balance($45,328.50) ✓ (UPDATE LABEL!)
  └─ Redraw equity curve for LIVE

Result:
  ├─ Current mode: "LIVE"
  ├─ Panel1 shows: $45,328.50 ✓ (updated!)
  └─ Equity curve: Switched to LIVE data ✓
```

---

## Testing the Fix

### Test 1: SIM Mode Doesn't Show LIVE Balance
1. Start app
2. Switch to SIM mode (badge shows "SIM")
3. Look at balance in Panel1
4. **Expected**: Shows $10,000.00 (SIM)
5. **NOT**: Your real LIVE balance (e.g., $45,328.50)

### Test 2: Mode Switch Updates Balance
1. Start app in SIM mode
2. Panel1 shows: $10,000.00
3. Press Ctrl+Shift+M to switch to LIVE
4. **Expected**: Panel1 updates to show $45,328.50
5. **Expected**: Equity curve switches to LIVE data

### Test 3: LIVE Mode Shows LIVE Balance
1. Switch to LIVE mode (badge shows "LIVE")
2. Look at balance in Panel1
3. **Expected**: Shows your real LIVE balance from Sierra
4. **Not**: The SIM balance ($10K)

### Test 4: Switching Back Updates Balance Again
1. In LIVE mode, Panel1 shows: $45,328.50
2. Press Ctrl+Shift+M to switch back to SIM
3. **Expected**: Panel1 updates to show $10,000.00
4. **Expected**: Equity curve switches to SIM data

### Test 5: Log Messages Show Mode Checking
```bash
set DEBUG_DTC=1
python main.py

# Look for messages like:
# [router] balance.ui_ignored - balance for LIVE, current is SIM
# [panel1] Updated balance for SIM mode: $10,000.00
```

---

## What Changed

### Files Modified
1. **core/message_router.py** (2 fixes)
   - Added mode check to `_update_balance_ui()`
   - Added mode check to `_on_balance_update()`

2. **panels/panel1.py** (1 fix)
   - Added balance label update to `switch_equity_curve_for_mode()`

### Key Changes
- Balance is **stored** for all modes in StateManager
- Balance is **displayed** only if it matches current mode
- Balance is **updated** when you switch modes

---

## StateManager Still Stores Everything

Important: StateManager stores **BOTH balances** at all times:

```python
StateManager.sim_balance = $10,000.00
StateManager.live_balance = $45,328.50
```

**But only one is displayed** based on current mode:

```python
if current_mode == "SIM":
    display = state.sim_balance  # Show SIM
else:
    display = state.live_balance  # Show LIVE
```

This way:
- ✅ No data is lost
- ✅ Switching modes instantly shows the right balance
- ✅ SIM and LIVE are completely separate

---

## Summary of the Fix

### Before (Broken)
```
SIM mode:  Shows LIVE balance ❌
LIVE mode: Shows LIVE balance ✓
Switch:    Equity curve changes, but balance label doesn't ❌
```

### After (Fixed)
```
SIM mode:  Shows SIM balance ✓
LIVE mode: Shows LIVE balance ✓
Switch:    Both equity curve AND balance label update ✓
```

---

## Syntax Verified

Both files compile successfully:
- ✅ `core/message_router.py` - OK
- ✅ `panels/panel1.py` - OK

---

## Ready to Test

Run your app:
```bash
python main.py
```

**Expected behavior**:
- SIM mode → Shows $10,000.00 (or persisted balance)
- LIVE mode → Shows your real Sierra Chart balance
- Switching modes → Both equity curve AND balance update

**You should NO LONGER see LIVE balance in SIM mode!**

