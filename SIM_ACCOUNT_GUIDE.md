# SIM Account Logic - Quick Reference

## How SIM Mode Works

### Automatic Detection

The app automatically detects if you're in SIM or LIVE mode by checking the account name:

```python
# core/state_manager.py
new_mode = account.lower().startswith("sim") if account else False
```

**Examples:**

- `account = "sim1"` → SIM mode ✅
- `account = "SIM2"` → SIM mode ✅
- `account = "120005"` → LIVE mode ✅

---

## Mode Indicators

### Visual Indicators

- **SIM Mode:** Badge shows "SIM" (cyan border)
- **LIVE Mode:** Badge shows "LIVE" (red border)
- **No Mode:** Badge shows "DEBUG"

### Mode Detection Points

1. **Order Arrival** (Type 401)

   ```python
   if trade_account and "sim" in trade_account.lower():
       self.panel_balance.set_trading_mode("SIM")
   ```

2. **Position Update** (Type 427)

   ```python
   if trade_account and "sim" in trade_account.lower():
       self.panel_balance.set_trading_mode("SIM")
   ```

---

## Balance Behavior

### LIVE Mode Balance

- ✅ Comes from Sierra Chart DTC connection
- ✅ Updates in real-time with trades
- ✅ Account 120005 → Real balance

### SIM Mode Balance

- ❌ Sierra Chart SIM mode does NOT send balance
- ❌ Will show "—" (no data)
- ⚠️ **DO NOT rely on hardcoded $10,000** (now disabled)

### Balance Update Flow

```
Sierra Chart DTC
    ↓ (Type 602: AccountBalanceResponse)
core/data_bridge.py [signal_balance]
    ↓
core/app_manager.py [_on_balance handler]
    ↓
panels/panel1.py [set_account_balance()]
    ↓
Display: "$10,500.00"
```

---

## What Was Fixed

### ❌ REMOVED: Auto-Reset to $10,000

**Problem:** SIM balance manager was resetting balance to $10k every month

```python
# DELETED from core/sim_balance.py:39-50
def _check_monthly_reset(self) -> None:
    if self._last_reset_month != current_month:
        self._balance = 10000.00  # ← NO LONGER HAPPENS
```

### ❌ REMOVED: Hardcoded Test Data

**Problem:** Panel1 was injecting $10,500 test balance on startup

```python
# DELETED from panels/panel1.py:176-188
test_data = [(now - 3600 + i*30, 10000 + i*5 + ...)]
self.set_account_balance(10500.0)  # ← NO LONGER HAPPENS
```

### ✅ FIXED: Graph Display Position

**Before:** Graph had 10% bottom padding (pushed down)

```python
# BEFORE
self._plot.setYRange(y_min, y_max, padding=0.10)
```

**After:** Graph has 5% padding (raised up, more visible)

```python
# AFTER
self._plot.setYRange(y_min, y_max, padding=0.05)
```

---

## Potential Issues Still Present

### Issue 1: SIM Mode Has No Balance Data

**Why:** Sierra Chart SIM mode doesn't send balance updates
**Workaround:** Use test_balance_debug.py to manually set balance
**Fix:** Document in UI that SIM mode balance is "N/A"

### Issue 2: No Balance Validation

**Current:** Any balance value is accepted without validation
**Risk:** Negative balances could cause issues
**Recommendation:** Add validation in `set_account_balance()`

### Issue 3: SimBalanceManager Is Unused

**Current:** Module exists but is disabled
**Recommendation:** Either remove it or use only for explicit testing

---

## How to Test

### Test 1: Verify Live Balance Updates

```
1. Open APPSIERRA
2. Connect to Sierra Chart (Account 120005 or your LIVE account)
3. Watch Panel1 balance update in real-time
4. Make a trade
5. Verify balance updates correctly
```

### Test 2: Verify SIM Mode Detection

```
1. Create a SIM account in Sierra Chart (named "SIM1" or "sim2")
2. Switch to SIM account
3. Verify badge changes to "SIM"
4. Balance should show "—" (Sierra Chart SIM doesn't send balance)
```

### Test 3: Verify Graph Display

```
1. Check that line graph fills ~75% of the panel height
2. Verify it's not pushed down too far
3. Hover over graph to see tooltip
```

### Test 4: Verify No 10k Reset

```
1. Set balance to $25,000 in live account
2. Wait for next month (or check logs)
3. Verify balance stays at $25,000 (not reset to $10k)
```

---

## Debug Logging

### To Enable Debug Output

Set environment variable:

```bash
DEBUG=1 python main.py
```

### Key Log Messages to Watch For

```
[Mode] StateManager: Application now in SIM mode
[Mode] StateManager: Application now in LIVE mode
[Startup] ✓ Wired DTC signal_balance -> Panel1.set_account_balance
[SIM] Balance updated to ${amount}
[Balance] ✅ Successfully updated Panel 1: ${amount}
```

### What Should NOT Appear

```
❌ "test data added"
❌ "Monthly reset triggered"
❌ "Balance manually reset to $10000"
```

---

## Key Code Locations

| Component              | File                    | Lines   |
| ---------------------- | ----------------------- | ------- |
| Mode Detection         | `core/state_manager.py` | 70-78   |
| Balance Routing        | `core/app_manager.py`   | 290-305 |
| Graph Display          | `panels/panel1.py`      | 877     |
| SIM Balance (Disabled) | `core/sim_balance.py`   | 18-76   |

---

## Summary

✅ SIM account detection works correctly
✅ Live account balance updates work correctly
✅ Mock data ($10,000) completely removed
✅ Graph display now properly positioned
⚠️ SIM mode balance is "N/A" (Sierra Chart limitation)
