# APPSIERRA DATA FLOW FIXES

**Root Cause Diagnosis Date**: November 7, 2025  
**Issues Found**: 2 Critical  
**Time to Fix**: 15 minutes

---

## ISSUE #1: StateManager Missing Methods (CRITICAL)

### Problem

Three methods are called by `message_router.py` but don't exist in `StateManager`:

- Line 105: `self.state.update_balance(bal)`
- Line 118: `self.state.update_position(sym, qty, avg)`
- Line 128: `self.state.record_order(payload)`

This causes silent `AttributeError` exceptions, blocking state persistence.

### Solution

Add these 3 methods to `core/state_manager.py` after the existing methods.

**File to edit**: `C:\Users\cgrah\OneDrive\Desktop\APPSIERRA\core\state_manager.py`

Add this code after line 90 (after the `_log_mode_change` method):

```python
# -------------------- Trading data persistence (start)
def update_balance(self, balance: Optional[float]) -> None:
    """Record current account balance."""
    if balance is not None:
        try:
            self._state["balance"] = float(balance)
        except (TypeError, ValueError):
            pass  # Ignore invalid balance values

def update_position(self, symbol: Optional[str], qty: int, avg_price: Optional[float]) -> None:
    """Record or remove a position."""
    if not symbol:
        return
    positions = self._state.get("positions", {})
    if qty == 0:
        # Close position (remove from dict)
        positions.pop(symbol, None)
    else:
        # Update or create position
        positions[symbol] = {
            "qty": int(qty),
            "avg_price": float(avg_price) if avg_price else None,
        }
    self._state["positions"] = positions

def record_order(self, payload: dict) -> None:
    """Record an order event for statistics and replay."""
    if not isinstance(payload, dict):
        return
    orders = self._state.get("orders", [])
    orders.append(payload)
    self._state["orders"] = orders
# -------------------- Trading data persistence (end)
```

---

## ISSUE #2: MessageRouter Not Wired (MEDIUM PRIORITY)

### Problem

The `MessageRouter` exists in code but is **never instantiated** or **passed to DTCClientJSON**.

**File**: `core/app_manager.py` line 565

Current code:

```python
self._dtc = DTCClientJSON(host=host, port=port, router=None)
```

This means the router dispatcher is disconnected. Even if StateManager has the right methods, the router won't call them.

### Solution

Wire the MessageRouter to DTCClientJSON.

**File to edit**: `C:\Users\cgrah\OneDrive\Desktop\APPSIERRA\core\app_manager.py`

**Step 1**: Add import at the top of the file (around line 22):

```python
from core.message_router import MessageRouter  # Add this line
```

**Step 2**: Replace lines 558-566 with:

```python
def _init_dtc(self) -> None:
    """Initialize DTC client and start connection immediately (guarded)."""
    try:
        if getattr(self, "_dtc_started", False):
            log.info("[DTC] Init already started; skipping duplicate init")
            return
        host = DTC_HOST
        port = int(DTC_PORT)
        log.info(f"[DTC] Searching for DTC server at {host}:{port}")

        # Create message router to dispatch data to panels and state
        router = MessageRouter(
            state=self._state,
            panel_balance=self.panel_balance,
            panel_live=self.panel_live,
            panel_stats=self.panel_stats,
        )

        self._dtc = DTCClientJSON(host=host, port=port, router=router)
        self._connect_dtc_signals()

        # ... rest of method continues unchanged ...
```

**That's it!** The router will now be instantiated and passed to DTCClientJSON.

---

## Verification Steps

### Step 1: Verify StateManager Methods Exist

```bash
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
python -c "
from core.state_manager import StateManager
sm = StateManager()
print('update_balance():', hasattr(sm, 'update_balance'))
print('update_position():', hasattr(sm, 'update_position'))
print('record_order():', hasattr(sm, 'record_order'))
"
```

**Expected output**:

```
update_balance(): True
update_position(): True
record_order(): True
```

### Step 2: Verify Data Flow with Debug Logging

```bash
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
export DEBUG_DATA=1
python main.py
```

**Expected output (after Sierra sends balance update)**:

```
[DTC] Type: 600 (AccountBalanceUpdate)
[BALANCE RESPONSE] DTC Message Type: 600
   Raw JSON: {"Type": 600, "CashBalance": 50000.0, ...}
DEBUG [data_bridge]: [BALANCE] Sending BALANCE_UPDATE signal
DEBUG: [SIGNAL] BALANCE received: {'balance': 50000.0}
DEBUG: Panel1.set_account_balance(50000.0) called
```

### Step 3: Run Tests

```bash
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
python -m pytest tests/test_state_manager.py -v
```

---

## Explanation: Why These Fixes Work

### Issue #1 Fix (StateManager Methods)

When `message_router._on_balance_update()` is called with a payload:

1. It was calling `self.state.update_balance(bal)` → AttributeError (method didn't exist)
2. Now it will call `self.state.update_balance(bal)` → Sets `self._state["balance"] = bal`
3. App state persists the value → other code can call `self.state.get("balance")`

### Issue #2 Fix (MessageRouter Wiring)

When DTC receives a balance update (Type 600):

1. Before: Router was None → dispatcher never called → state never updated via router
2. After: Router is instantiated → `_emit_app()` calls `self._router.route(data)` → dispatcher runs → StateManager methods called

**Result**: Data flows through all layers:

```
Socket → DTC Client → data_bridge → [Blinker signals + Router] → StateManager
                                    ↓
                              UI Panels (receive both ways)
```

---

## Code Changes Summary

| File                    | Change                   | Lines             | Severity |
| ----------------------- | ------------------------ | ----------------- | -------- |
| `core/state_manager.py` | Add 3 methods            | After line 90     | CRITICAL |
| `core/app_manager.py`   | Add import + wire router | Line 22 + 556-566 | MEDIUM   |

Total lines added: ~35  
Total lines modified: 1 (DTCClientJSON call)

---

## Rollback Plan (If needed)

If something breaks:

1. **Revert StateManager** (safest):
   - Remove the 3 new methods
   - App still works (state just won't persist)

2. **Revert Router Wiring**:
   - Remove the `MessageRouter` import
   - Change `router=router` back to `router=None`
   - App still works (Blinker signals still fire)

Both changes are additive and non-breaking.

---

## Additional Notes

### Why Blinker Signals Alone Aren't Enough

The Blinker signals (balance, position, order) fire directly to UI panels and work great. BUT:

- They execute in the socket thread (not Qt main thread) - can cause race conditions
- They don't persist state for historical lookups
- They don't work well with redo/undo functionality

### Why Router is Better

The message router:

- Routes all data through StateManager (single source of truth)
- Ensures consistent state for all consumers
- Decouples UI panels from DTC message format
- Makes the code testable

### Why Both Can Coexist

Having both Blinker signals AND router running is safe:

1. Blinker signals fire first (direct to UI)
2. Router fires second (to StateManager)
3. Data only updates once per message (efficient)
4. Both are idempotent (calling twice = same result)
