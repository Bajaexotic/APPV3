# Core Module Audit: data_bridge.py & app_manager.py

## Date: 2025-11-09

## Scope: Identify redundancies and overlaps between `core/data_bridge.py` and `core/app_manager.py`

---

## Executive Summary

**Finding:** Moderate overlap with **dual-dispatch pattern** creating redundancy.

**Impact:** ~150 LOC of duplicate message routing logic, scattered balance refresh triggers, and embedded mode detection.

**Recommendation:** Consolidate to single dispatch path and extract mode detection service.

---

## Module Responsibilities

### `data_bridge.py` (DTCClientJSON - 623 LOC)

**Primary Role:** Low-level DTC protocol handling

| Responsibility                                   | Lines   | Status                             |
| ------------------------------------------------ | ------- | ---------------------------------- |
| Socket management (connect/disconnect/reconnect) | 205-357 | ✓ Unique                           |
| Heartbeat + watchdog system                      | 300-340 | ✓ Unique                           |
| Null-terminated frame parsing                    | 360-388 | ✓ Unique                           |
| Message normalization helpers                    | 54-113  | ✓ Unique                           |
| **Blinker signal emission**                      | 540-586 | ⚠️ **Overlaps with MessageRouter** |
| **MessageRouter dispatch**                       | 572-576 | ⚠️ **Overlaps with signals**       |
| Initial data requests                            | 480-509 | ✓ Unique                           |
| Binary/JSON protocol detection                   | 512-537 | ✓ Unique                           |
| Balance request API                              | 601-619 | ✓ Unique                           |

### `app_manager.py` (MainWindow - 672 LOC)

**Primary Role:** UI orchestration and panel coordination

| Responsibility                     | Lines            | Status                      |
| ---------------------------------- | ---------------- | --------------------------- |
| Window setup and theme management  | 62-434           | ✓ Unique                    |
| Panel instantiation (Panel1/2/3)   | 99-141           | ✓ Unique                    |
| Cross-panel signal wiring          | 157-332          | ✓ Unique                    |
| **Blinker signal subscription**    | 224-323          | ⚠️ **Overlaps with router** |
| **Auto-mode detection (SIM/LIVE)** | 232-287          | ⚠️ **Should be service**    |
| **Balance refresh triggers**       | 249-256, 594-599 | ⚠️ **Scattered logic**      |
| DTC client instantiation           | 570-607          | ✓ Unique                    |
| Connection status UI updates       | 638-667          | ✓ Unique                    |
| Timeframe synchronization          | 454-530          | ✓ Unique                    |

---

## Critical Redundancy #1: Dual Message Dispatch

### Problem

`data_bridge.py` dispatches messages via **TWO parallel paths**:

```python
# Path 1: Blinker signals (data_bridge.py:540-586)
def _emit_app(self, app_msg: AppMessage) -> None:
    if app_msg.type == "BALANCE_UPDATE":
        signal_balance.send(app_msg.payload)  # ← Blinker signal
    elif app_msg.type == "POSITION_UPDATE":
        signal_position.send(app_msg.payload)  # ← Blinker signal
    elif app_msg.type == "ORDER_UPDATE":
        signal_order.send(app_msg.payload)  # ← Blinker signal

    # Path 2: MessageRouter (data_bridge.py:573-576)
    if self._router:
        self._router.route(data)  # ← Router dispatch
```

**Then `app_manager.py` subscribes to Blinker signals:**

```python
# app_manager.py:224-323
signal_order.connect(_on_order, weak=False)
signal_position.connect(_on_position, weak=False)
signal_balance.connect(_on_balance, weak=False)
```

### Impact

- **Duplicate dispatch logic** (~30 LOC)
- Potential for **message ordering issues** (signals vs router may execute in different order)
- **Harder to debug** (two code paths for same data)
- **Maintenance burden** (changes must be made in both paths)

### Recommendation

**Option A: Keep Blinker signals only** (Simpler)

- Remove MessageRouter entirely
- All subscribers use Blinker
- Pro: Less coupling, easier testing
- Con: Loses structured routing benefits

**Option B: Keep MessageRouter only** (More structured)

- Remove Blinker signal emissions from data_bridge
- MessageRouter handles all dispatch
- Pro: Single source of truth, better logging
- Con: More coupling to router

**Recommended:** **Option A** - Remove MessageRouter, keep Blinker signals for loose coupling.

---

## Critical Redundancy #2: Auto-Mode Detection Embedded in App Manager

### Problem

`app_manager.py` embeds SIM/LIVE mode detection logic in signal handlers:

```python
# app_manager.py:232-242 (ORDER handler)
trade_account = msg.get("TradeAccount", "")
if trade_account:
    if trade_account == LIVE_ACCOUNT:
        self.panel_balance.set_trading_mode("LIVE")
        log.info(f"[AUTO-DETECT] Switched to LIVE mode")
    elif trade_account.startswith("Sim"):
        self.panel_balance.set_trading_mode("SIM")
        log.info(f"[AUTO-DETECT] Switched to SIM mode")

# app_manager.py:276-287 (POSITION handler)
# ... DUPLICATE of above logic
```

**Duplicated in 2 places:** ORDER and POSITION handlers

### Impact

- **60 LOC of duplicate logic**
- Mode detection **scattered** across multiple signal handlers
- Hard to modify detection rules (must update 2+ places)
- **Testing difficulty** (can't unit test mode detection in isolation)

### Recommendation

**Extract to service:**

```python
# core/mode_detector.py
class ModeDetector:
    def __init__(self, live_account: str):
        self._live_account = live_account

    def detect_mode(self, trade_account: str) -> str:
        """
        Returns "SIM" or "LIVE" based on account.

        Rules:
        - Starts with "Sim" (case-insensitive) → SIM
        - Matches LIVE_ACCOUNT → LIVE
        - Default → LIVE
        """
        if not trade_account:
            return "LIVE"

        if trade_account.upper().startswith("SIM"):
            return "SIM"
        elif trade_account == self._live_account:
            return "LIVE"
        else:
            return "LIVE"  # Default to LIVE for numeric accounts
```

**Usage in app_manager:**

```python
# app_manager.py: Single call in each handler
def _on_order(sender, **kwargs):
    msg = sender if isinstance(sender, dict) else kwargs
    trade_account = msg.get("TradeAccount", "")

    if trade_account:
        mode = self._mode_detector.detect_mode(trade_account)
        self.panel_balance.set_trading_mode(mode)
        log.info(f"[AUTO-DETECT] Switched to {mode} mode (account: {trade_account})")
```

---

## Critical Redundancy #3: Scattered Balance Refresh Logic

### Problem

Balance refresh requests triggered from **3 different locations:**

1. **data_bridge.py:503** - Initial data seeding

   ```python
   def send_balance():
       self.request_account_balance(None)
   QtCore.QTimer.singleShot(400, send_balance)
   ```

2. **app_manager.py:598** - After session ready

   ```python
   def _on_session_ready():
       self._dtc.request_account_balance()
   ```

3. **app_manager.py:256** - After order filled

   ```python
   if status in (3, 7):  # Filled
       self._dtc.request_account_balance()
   ```

### Impact

- **Logic scattered** across 2 modules
- **Duplicate initial request** (both data_bridge and app_manager request on session ready)
- Hard to track when/why balance updates happen

### Recommendation

**Consolidate to app_manager:**

```python
# app_manager.py
def _setup_balance_refresh_triggers(self):
    """
    Centralize all balance refresh triggers:
    1. On session ready (initial)
    2. After filled orders (update)
    3. Manual refresh (user action)
    """
    # Initial balance on session ready
    self._dtc.session_ready.connect(self._refresh_balance)

    # Refresh after filled orders
    signal_order.connect(self._on_order_for_balance_refresh)

def _on_order_for_balance_refresh(self, sender, **kwargs):
    msg = sender if isinstance(sender, dict) else kwargs
    status = msg.get("OrderStatus")
    if status in (3, 7):  # Filled
        self._refresh_balance()

def _refresh_balance(self):
    """Single point of balance refresh."""
    self._dtc.request_account_balance()
```

**Remove from data_bridge:**

- Delete `send_balance()` from `_request_initial_data()`

---

## Minor Issue: Request/Response Routing Diagnostics in data_bridge

### Observation

`data_bridge.py:404-425` has extensive logging for request/response correlation:

```python
REQUEST_ID_MAP = {
    1: "Type 400 (TradeAccountsRequest)",
    2: "Type 500 (PositionsRequest) - SKIPPED",
    3: "Type 305 (OpenOrdersRequest)",
    4: "Type 303 (HistoricalOrderFillRequest)",
    5: "Type 601 (AccountBalanceRequest)",
}

if req_id is not None:
    expected_request = REQUEST_ID_MAP.get(req_id, f"Unknown RequestID {req_id}")
    log.info("dtc.response.routing", type=msg_type, name=msg_name,
             request_id=req_id, expected_request=expected_request)
```

### Assessment

**Status:** ✓ **Keep as-is** - This is valuable debugging/tracing infrastructure

---

## Summary of Redundancies

| Issue                            | LOC Impact | Severity | Recommendation                     |
| -------------------------------- | ---------- | -------- | ---------------------------------- |
| Dual dispatch (Blinker + Router) | ~30        | Medium   | Remove MessageRouter, keep signals |
| Embedded mode detection          | ~60        | High     | Extract to `ModeDetector` service  |
| Scattered balance refresh        | ~15        | Low      | Consolidate to app_manager         |
| **Total**                        | **~105**   |          |                                    |

---

## Refactor Plan

### Phase 1: Extract Mode Detection (High Priority)

**Files to create:**

- `core/mode_detector.py` (~30 LOC)

**Files to modify:**

- `app_manager.py` - Replace duplicate logic with single ModeDetector call

**Test impact:**

- Update `tests/test_mode_routing.py` to test ModeDetector service
- Remove redundant inline tests

**Estimated effort:** 30 minutes

---

### Phase 2: Consolidate Balance Refresh (Medium Priority)

**Files to modify:**

- `app_manager.py` - Add `_setup_balance_refresh_triggers()`
- `data_bridge.py` - Remove balance request from `_request_initial_data()`

**Test impact:**

- Add test for consolidated balance refresh logic

**Estimated effort:** 15 minutes

---

### Phase 3: Simplify Dispatch (Low Priority)

**Decision required:** Keep Blinker or MessageRouter?

**Option A (Recommended): Remove MessageRouter**

- `data_bridge.py` - Remove router parameter and `router.route()` call
- `message_router.py` - Can be deleted or repurposed
- All dispatch via Blinker signals

**Option B: Remove Blinker signals**

- `data_bridge.py` - Remove signal emissions, keep only `router.route()`
- `app_manager.py` - Subscribe to router instead of signals
- More coupled but more structured

**Estimated effort:** 45 minutes (either option)

---

## Metrics

| Metric                   | Current | After Refactor | Improvement   |
| ------------------------ | ------- | -------------- | ------------- |
| Total LOC (both files)   | 1,295   | ~1,190         | -105 LOC (8%) |
| Duplicate logic blocks   | 3       | 0              | -100%         |
| Signal dispatch paths    | 2       | 1              | -50%          |
| Balance refresh triggers | 3       | 1              | -67%          |
| Testability score        | Medium  | High           | +2 levels     |

---

## Next Steps

1. **Review this audit** with team
2. **Decide on dispatch approach** (Blinker vs MessageRouter)
3. **Implement Phase 1** (mode detection) - highest value
4. **Implement Phase 2** (balance refresh) - quick win
5. **Implement Phase 3** (dispatch simplification) - architectural decision

---

## Notes

- **No breaking changes** to external API
- All changes are **internal refactoring**
- Tests will need updates but **no new test scenarios required**
- **Backward compatible** - old code paths can coexist during migration

---

**End of Audit**
