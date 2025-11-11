# Logger Bug Fixes - November 11, 2025

## Problem
The application was crashing when trying to record closed trades with logger errors:
```
[ERROR] [services.trade_service] trade_manager.db_write_failed for F.US.MESZ25:
  Logger._log() got an unexpected keyword argument 'balance'
```

This error repeated multiple times in the log, preventing trades from being properly saved to the database.

## Root Cause
The code was using structlog's logger incorrectly. The logger doesn't accept keyword arguments in the format:
```python
log.info("message", key=value)  # ❌ WRONG
```

Instead, it requires the message to be formatted as an f-string:
```python
log.info(f"message: key={value}")  # ✅ CORRECT
```

## Files Fixed

### 1. `core/message_router.py` (18 logger calls fixed)
Fixed incorrect logger calls with keyword arguments:

**Line 75:** `log.debug("router.signals.subscribed", msg="...")`
→ `log.debug(f"router.signals.subscribed: msg=...")`

**Line 100:** `log.error("router.signals.subscribe_failed", error=str(e))`
→ `log.error(f"router.signals.subscribe_failed: {str(e)}")`

**Line 123:** `log.warning(f"router.order.blocked", mode=..., reason=...)`
→ `log.warning(f"router.order.blocked: mode={mode}, reason=...")`

**Line 131:** `log.warning("router.order.mode_detect_failed", error=str(e))`
→ `log.warning(f"router.order.mode_detect_failed: {str(e)}")`

**Lines 139, 143:** Order handler marshal/direct call errors
→ Formatted as f-strings with error message

**Line 164:** `log.warning("router.order.balance_request_failed", error=str(e))`
→ `log.warning(f"router.order.balance_request_failed: {str(e)}")`

**Line 167:** `log.error("router.order.handler_failed", error=str(e))`
→ `log.error(f"router.order.handler_failed: {str(e)}")`

**Line 191:** Position blocked warning
→ Formatted as f-string with mode and reason

**Line 199:** Position mode detection failure
→ Formatted as f-string with error

**Lines 207, 211:** Position marshal/direct call errors
→ Formatted as f-strings

**Line 214:** Position handler failure
→ Formatted as f-string

**Line 264:** `log.debug(f"router.balance.updated", mode=mode, balance=balance_value)`
→ `log.debug(f"router.balance.updated: mode={mode}, balance={balance_value}")`

**Line 266:** `log.warning("router.balance.state_update_failed", error=str(e))`
→ `log.warning(f"router.balance.state_update_failed: {str(e)}")`

**Lines 275, 279:** Balance marshal/direct call errors
→ Formatted as f-strings

**Line 282:** Balance handler failure
→ Formatted as f-string

**Line 316:** `log.error("router.balance.ui_update_error", error=str(e))`
→ `log.error(f"router.balance.ui_update_error: {str(e)}")`

**Line 338:** `log.warning("router.handler.error", type=mtype, err=str(e))`
→ `log.warning(f"router.handler.error: type={mtype}, error={str(e)}")`

**Line 340:** `log.debug("router.unhandled", type=mtype)`
→ `log.debug(f"router.unhandled: type={mtype}")`

**Line 369:** `log.debug("router.balance", balance=bal)`
→ `log.debug(f"router.balance: balance={bal}")`

**Line 404:** `log.debug("router.position.closed", symbol=sym)`
→ `log.debug(f"router.position.closed: symbol={sym}")`

**Line 441:** `log.debug("router.position", symbol=sym, qty=qty, avg_entry=avg)`
→ `log.debug(f"router.position: symbol={sym}, qty={qty}, avg_entry={avg}")`

### 2. `services/trade_service.py` (1 variable fix)
Fixed undefined variable reference on line 304:

**Line 214:** Added initialization
```python
new_balance = None  # Initialize to None for later use
```

This prevents the NameError when trying to reference `new_balance` at line 304 if the balance update was skipped.

## Impact
These fixes will:
1. ✅ Allow trades to be recorded successfully when they close
2. ✅ Prevent logger errors from blocking the database write
3. ✅ Enable P&L calculations to persist to the database
4. ✅ Allow Panel 3 to retrieve and display historical trade statistics
5. ✅ Restore account balance tracking across sessions

## Testing
To verify the fixes work:
1. Run the application: `python main.py`
2. Place a trade and close it
3. Check that `[TRADE CLOSED]` shows in the console without logger errors
4. Verify Panel 3 displays the P&L for the closed trade
5. Close and reopen the app - balance should persist

## Log Messages Expected
After fixes, you should see clean trade closure messages like:
```
[TRADE CLOSED] 📈 MES | SIM Mode
================================================================================
  Entry Price: $6,844.50 | Exit Price: $6,850.00
  Quantity: 2 contracts
  P&L: +$11.00
  Previous Balance: $10,000.00
  New Balance: $10,011.00
================================================================================

[DEBUG STEP 8] ✓ Trade committed to database with ID=1
```

No logger errors or exceptions should appear.
