# SIM/LIVE Mode Separation - Testing Guide

## Quick Test Checklist

### Setup
1. Ensure database has `mode` column in TradeRecord, OrderRecord, AccountBalance
2. Verify LIVE_ACCOUNT is configured in `config/settings.py` (e.g., "120005")
3. Start application connected to Sierra Chart

### Test Scenario 1: SIM Mode Trading
**Objective**: Verify SIM trades are tracked separately

1. Connect to Sierra Chart with SIM account (e.g., "Sim1")
2. Verify badge shows "SIM" mode
3. Open a position (long or short)
4. Check Panel 2: Position should display with mode="SIM" in logs
5. Close position
6. Check Panel 3: Trade appears in statistics
7. Switch to 1D timeframe: Verify trade count shows 1

**Expected Results:**
- Badge: "SIM" (cyan color)
- Panel 2 logs: `mode=SIM`
- Panel 3: Trade count = 1
- Database: `TradeRecord.mode = "SIM"`

### Test Scenario 2: LIVE Mode Trading
**Objective**: Verify LIVE trades are tracked separately

1. Connect to Sierra Chart with LIVE account (e.g., "120005")
2. Verify badge shows "LIVE" mode
3. Open a position
4. Check Panel 2: Position should display with mode="LIVE" in logs
5. Close position
6. Check Panel 3: Trade appears in statistics

**Expected Results:**
- Badge: "LIVE" (red color)
- Panel 2 logs: `mode=LIVE`
- Panel 3: Shows LIVE trades only (not SIM trades from Test 1)
- Database: `TradeRecord.mode = "LIVE"`

### Test Scenario 3: Mode Precedence (LIVE over SIM)
**Objective**: Verify LIVE mode takes precedence

1. Connect with SIM account
2. Open a SIM position (e.g., 2 contracts long)
3. Verify position is open in Panel 2
4. Without closing, connect with LIVE account
5. Attempt to open a LIVE position

**Expected Results:**
- SIM position auto-closes when LIVE account connects
- Panel 2 logs: `Auto-closed SIM position due to mode switch to LIVE`
- LIVE position opens successfully
- No dialog warnings (LIVE always allowed)

### Test Scenario 4: Mode Blocking (SIM Blocked by LIVE)
**Objective**: Verify SIM trades are blocked when LIVE position is open

1. Connect with LIVE account
2. Open a LIVE position
3. Without closing, attempt to switch to SIM account
4. Try to open a SIM position

**Expected Results:**
- Dialog warning: "Cannot switch to SIM mode - LIVE position open"
- SIM order rejected
- Panel 2 logs: `Order rejected - SIM mode blocked by open LIVE position`
- LIVE position remains open

### Test Scenario 5: Balance Separation
**Objective**: Verify SIM and LIVE balances are tracked separately

1. Connect with SIM account
2. Note starting balance (e.g., $5,000)
3. Make a winning trade (+$100)
4. Verify Panel 1 shows $5,100
5. Switch to LIVE account
6. Verify Panel 1 shows LIVE balance (not $5,100)
7. Make a trade in LIVE
8. Switch back to SIM account
9. Verify Panel 1 still shows $5,100

**Expected Results:**
- SIM balance persists across mode switches
- LIVE balance persists across mode switches
- No cross-contamination between modes

### Test Scenario 6: Statistics Filtering
**Objective**: Verify Panel 3 filters by mode

1. Make 3 SIM trades (mix of wins/losses)
2. Make 2 LIVE trades (different P&L than SIM)
3. View Panel 3 in SIM mode:
   - Verify "Trades" shows 3
   - Verify "Total PnL" reflects SIM trades only
4. Switch to LIVE mode
5. View Panel 3:
   - Verify "Trades" shows 2
   - Verify "Total PnL" reflects LIVE trades only

**Expected Results:**
- Panel 3 statistics completely separate per mode
- No mixing of SIM and LIVE trade data
- Empty state displayed if no trades for current mode

### Test Scenario 7: Empty State Display
**Objective**: Verify empty state when no trades exist for mode

1. Clear database or use fresh account
2. Connect with SIM account
3. View Panel 3 → 1D timeframe

**Expected Results:**
- All metrics show zero or "--"
- "Trades" shows "0"
- No errors or crashes
- Neutral pill color

### Test Scenario 8: Mode Detection Edge Cases
**Objective**: Verify mode detection handles edge cases

1. Connect with account "Sim1" → Should be SIM
2. Connect with account "Sim" → Should be SIM
3. Connect with account "sim1" (lowercase) → Should be SIM
4. Connect with account "" (empty) → Should be DEBUG
5. Connect with account "Unknown123" → Should be DEBUG
6. Connect with LIVE_ACCOUNT value → Should be LIVE

**Expected Results:**
- All detection logic works correctly
- No crashes on edge cases
- Default to DEBUG for unknown accounts

## Database Verification Queries

### Check Trade Modes
```sql
SELECT mode, COUNT(*) as count, SUM(realized_pnl) as total_pnl
FROM traderecord
WHERE realized_pnl IS NOT NULL
GROUP BY mode;
```

**Expected Output:**
```
mode  | count | total_pnl
------|-------|----------
SIM   | 3     | 150.00
LIVE  | 2     | -50.00
```

### Check Order Modes
```sql
SELECT mode, COUNT(*) as count
FROM orderrecord
GROUP BY mode;
```

### Check Balance History
```sql
SELECT mode, balance, timestamp
FROM accountbalance
ORDER BY timestamp DESC
LIMIT 10;
```

## Debugging Tips

### Enable Debug Logging
```python
# In config/settings.py or environment
DEBUG_DTC = "1"  # Enables mode detection logs
```

### Check Logs for Mode Detection
Look for these patterns:
```
[AUTO-DETECT] Mode switch: SIM → LIVE (account: 120005)
[panel2] Position opened — Mode: SIM
[panel2] Order rejected - SIM mode blocked by open LIVE position
[router.balance.updated] mode=LIVE balance=50000.00
```

### State Manager Inspection
```python
from core.app_state import get_state_manager

state = get_state_manager()
print(f"Current mode: {state.current_mode}")
print(f"Position mode: {state.position_mode}")
print(f"SIM balance: {state.sim_balance}")
print(f"LIVE balance: {state.live_balance}")
print(f"Has position: {state.has_active_position()}")
```

## Common Issues & Solutions

### Issue: Mode not detected
**Symptoms**: Badge stays on DEBUG, trades not filtered
**Solution**: Check account string format in DTC messages, verify LIVE_ACCOUNT config

### Issue: Statistics show mixed data
**Symptoms**: Panel 3 shows both SIM and LIVE trades
**Solution**: Verify `mode` column exists in database, check query filtering in stats_service.py

### Issue: Balance not updating
**Symptoms**: Panel 1 shows stale balance after mode switch
**Solution**: Check message_router balance signal handling, verify mode detection in _on_balance_signal

### Issue: SIM trades not blocked in LIVE mode
**Symptoms**: Can open SIM position while LIVE position is open
**Solution**: Check state.is_mode_blocked() logic, verify _check_mode_precedence() in message_router

### Issue: Dialogs not showing
**Symptoms**: No warning when trying to open blocked trade
**Solution**: Check Qt thread marshaling, verify show_mode_blocked_warning() is called

## Performance Testing

### Load Test: 1000 Trades
1. Import 1000 historical trades (500 SIM, 500 LIVE)
2. Switch between modes rapidly
3. Query Panel 3 statistics

**Expected Performance:**
- Mode switch < 100ms
- Statistics query < 500ms (with indexes)
- No memory leaks
- UI remains responsive

### Stress Test: Rapid Mode Switching
1. Script to switch modes every 100ms for 1 minute
2. Monitor memory usage
3. Check for race conditions

**Expected Behavior:**
- No crashes
- State remains consistent
- No orphaned positions

## Acceptance Criteria

- [ ] All 8 test scenarios pass
- [ ] Database queries show correct mode filtering
- [ ] No cross-contamination between SIM/LIVE data
- [ ] LIVE mode precedence enforced 100% of the time
- [ ] Dialogs show for blocked trades
- [ ] Statistics empty state works correctly
- [ ] Balance tracking separate per mode
- [ ] Mode detection handles all edge cases
- [ ] Performance acceptable under load
- [ ] No memory leaks or race conditions

## Test Environment Requirements

1. **Sierra Chart**: Running with DTC enabled
2. **Accounts**: At least one SIM account and one LIVE account
3. **Database**: Clean test database with schema migrations applied
4. **Config**: LIVE_ACCOUNT properly configured
5. **Data**: Some historical trades for each mode (optional)

## Automated Testing (Future)

Potential automated tests to add:
```python
# tests/test_mode_separation.py

def test_sim_trades_blocked_in_live_mode():
    state = StateManager()
    state.open_position("ES", 2, 5800.0, datetime.now(), mode="LIVE")
    assert state.is_mode_blocked("SIM") == True

def test_live_trades_always_allowed():
    state = StateManager()
    state.open_position("ES", 2, 5800.0, datetime.now(), mode="SIM")
    assert state.is_mode_blocked("LIVE") == False

def test_balance_separation():
    state = StateManager()
    state.set_balance_for_mode("SIM", 5000.0)
    state.set_balance_for_mode("LIVE", 50000.0)
    assert state.get_balance_for_mode("SIM") == 5000.0
    assert state.get_balance_for_mode("LIVE") == 50000.0
```

## Sign-off

After completing all tests:

**Tester**: _______________  **Date**: ___________

**Verified By**: _______________  **Date**: ___________

**Production Ready**: [ ] Yes [ ] No

**Notes**:
