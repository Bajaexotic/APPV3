# APPSIERRA Mode Separation Architecture

**Version**: 2.0
**Last Updated**: 2025-11-11
**Status**: CRITICAL REFERENCE - Required reading before touching mode/account logic

---

## Executive Summary

APPSIERRA implements a sophisticated data separation system that allows the application to operate in three distinct modes: **LIVE** (real money trading), **SIM** (paper trading), and **DEBUG** (development/testing). The separation is achieved through:

1. **Mode Detection** - Automatic detection from DTC account identifiers
2. **Conditional Data Routing** - Different data paths for SIM vs. LIVE
3. **Separate State Storage** - Mode-specific equity curves, balance tracking, session state
4. **Theme Switching** - Visual mode indicators via theme system
5. **Account-Based Validation** - Configuration-driven LIVE_ACCOUNT matching

**CRITICAL PRINCIPLE**: Every read and write in the app **MUST** be scoped by `(mode, account)`. On `ModeChanged`, all panels swap to that scope, reload their data, and repaint **once**.

---

## 0. CRITICAL RULES (Read This First)

### 0.1 **Strict Namespacing by (mode, account)**

**MANDATE**: All reads/writes (state files, stats, caches, equity curves) are keyed by **both mode AND account**.

```python
# CORRECT - Scoped by (mode, account)
state_path = f"data/panel2_state_{mode}_{account}.json"
equity_curve = equity_curves[(mode, account)]

# WRONG - Shared singleton without scope
current_position = {}  # ❌ Will leak across modes!
```

**No shared singletons without (mode, account) keys.** A single "current position/stats" object for both modes guarantees data bleed; this is **forbidden**.

### 0.2 **Single ModeChanged Event Contract**

On manual or automatic mode switch, broadcast `ModeChanged(mode, account)`. Each panel **MUST**:

1. **Freeze** current state
2. **Swap** datasource to `(mode, account)` scope
3. **Reload** from persistent storage
4. **Single repaint** (coalesced UI update)

This contract prevents the "all panels show the same data" issue.

### 0.3 **Mode Inference Restrictions**

**DO NOT** infer mode from:
- Price feed metadata
- Server banners or status messages
- UI toggles or manual selectors
- Environment variables (except `LIVE_ACCOUNT` config)

**ONLY** infer mode from DTC `TradeAccount` field in messages (301, 306, etc).

### 0.4 **LIVE Arming Gate**

**LIVE trading is disarmed at boot** and on config changes. Requires explicit user arm action.

- Default state: `LIVE_ARMED = False`
- Manual arming: User clicks "Arm LIVE" button
- Auto-disarm: On disconnect, config reload, or mode drift

This prevents accidental real-money orders during development.

### 0.5 **No Local Timestamps**

**Mandate UTC everywhere.** DST will bite you.

```python
# CORRECT
timestamp = datetime.now(timezone.utc).isoformat()

# WRONG
timestamp = datetime.now()  # ❌ Local time, DST-sensitive
```

### 0.6 **SubmitNewSingleOrder is NOT Final**

Do **not** treat `SubmitNewSingleOrder` (Type 208) as truth. It's **intent**.

`OrderUpdate` (Type 301) is the **authoritative** record. Say this plainly:

> "Until you receive a 301 OrderUpdate, the order does not exist in the system of record."

---

## 1. MODE DETERMINATION SYSTEM

### 1.1 How the App Detects Mode

**Key Module**: `utils/trade_mode.py`

The application determines mode through account identifier matching:

**Detection Rules** (in order of precedence):
1. Empty/missing account → **DEBUG**
2. Account == LIVE_ACCOUNT config → **LIVE** (e.g., "120005")
3. Account starts with "Sim" → **SIM** (e.g., "Sim1", "Sim2")
4. Unknown account → **DEBUG** (fallback)

**Configuration**: `config/settings.py`
- `LIVE_ACCOUNT`: str = "120005" (configurable via `SIERRA_TRADE_ACCOUNT` env)
- `TRADING_MODE`: str = "SIM" (configurable via `TRADING_MODE` env or config.json)

### 1.2 Automatic Mode Detection Points

Mode switching occurs at **two trigger points** when DTC messages arrive:

**From Order Messages** (`utils/trade_mode.auto_detect_mode_from_order`):
- Always triggers mode switch when order received
- Extracts account from `msg.get("TradeAccount")`
- No quantity check needed (orders always matter)

**From Position Messages** (`utils/trade_mode.auto_detect_mode_from_position`):
- Only triggers when `qty != 0` (active position)
- Prevents mode flickering when flattening positions
- Extracts qty from message: `msg.get("PositionQuantity")`

### 1.3 **Debounce & Provisional Boot**

**Debounce Window**: ~750ms, requires 2 consecutive agreeing signals before switching SIM ↔ LIVE.

```python
# Pseudocode
mode_candidate_queue = []
DEBOUNCE_WINDOW_MS = 750
REQUIRED_CONSECUTIVE = 2

def should_switch_mode(new_mode):
    mode_candidate_queue.append((time.now(), new_mode))

    # Prune old candidates outside window
    cutoff = time.now() - DEBOUNCE_WINDOW_MS
    mode_candidate_queue = [c for c in mode_candidate_queue if c[0] > cutoff]

    # Check if last N candidates agree
    if len(mode_candidate_queue) >= REQUIRED_CONSECUTIVE:
        if all(c[1] == new_mode for c in mode_candidate_queue[-REQUIRED_CONSECUTIVE:]):
            return True
    return False
```

**Provisional Boot Mode**:
- Persist `last_known_mode` and `last_known_account` with 24h TTL
- UI boots in **provisional mode** (yellow banner: "Waiting for DTC confirmation...")
- After first confirming message (order or position), switch to authoritative mode
- Prevents stale mode if last session was 3 days ago

**Storage**: `data/last_known_mode.json`
```json
{
  "mode": "SIM",
  "account": "Sim1",
  "timestamp_utc": "2025-11-11T14:23:45.123456Z",
  "ttl_hours": 24
}
```

---

## 2. AUTHORITATIVE RECOVERY SEQUENCE

**When to trigger**: After any disconnect, network error, or app restart.

**The 3-step pull**:

1. **Positions Now** (DTC Type 500 - PositionRequest)
   - Request all current positions
   - Rebuild position state from scratch

2. **Open Orders Now** (DTC Type 300 - OpenOrdersRequest)
   - Request all open orders
   - Relink brackets (OCO, parent-child relationships)

3. **Fills Since Last Seen** (DTC Type 303 - HistoricalOrderFillRequest)
   - Request fills since `last_seen_timestamp_utc`
   - Replay fills to reconstruct balance, PnL, equity curve

**Guarantees**: Panel 2 and Panel 3 are correct even if no new trade occurs after reconnect.

**Implementation**: `core/message_router.py::_recovery_sequence()`

```python
async def _recovery_sequence(self):
    """3-step authoritative recovery."""
    logger.info("Recovery: Step 1 - Requesting positions now")
    await self._dtc_client.request_positions()

    logger.info("Recovery: Step 2 - Requesting open orders now")
    await self._dtc_client.request_open_orders()

    last_seen = self._get_last_seen_timestamp_utc()
    logger.info(f"Recovery: Step 3 - Requesting fills since {last_seen}")
    await self._dtc_client.request_historical_fills(since=last_seen)

    logger.info("Recovery sequence complete - relinking brackets")
    self._relink_brackets()
```

---

## 3. STATE MANAGER MODE TRACKING

**Key Class**: `core/state_manager.py::StateManager`

The state manager maintains mode awareness as a boolean flag:

**Key attributes**:
- `current_account`: Optional[str] - The active trading account ID
- `is_sim_mode`: bool - True if account starts with "Sim", False for LIVE/DEBUG
- `mode_history`: list[tuple[datetime, str, str]] - UTC timestamp, mode, account

**set_mode(account)** method:
- Detects if `account.lower().startswith("sim")`
- Updates `is_sim_mode` flag
- Logs mode change via logger
- Appends to `mode_history` with UTC timestamp

**Called from**: `core/message_router.py:329` (_on_trade_account handler)

---

## 4. DATA SOURCE SEPARATION

### 4.1 Market Data (Both Modes Use Same Source)

**Service**: `services/market_data_service.py::MarketDataService`

Market data comes from a **single CSV feed** (not mode-dependent):
- **Path**: `data/snapshot.csv`
- **Read Frequency**: Every 500ms (Panel2)
- **Fields**: last, high, low, vwap, cum_delta, poc
- **Mode Agnostic**: Both SIM and LIVE panels read from the same file

Returns **MarketSnapshot** namedtuple with fields:
- `last_price`, `session_high`, `session_low`, `vwap`, `cum_delta`, `poc`

### 4.2 Account Balance Data (Mode-Specific Sources)

**Live Account Balance**:
- **Source**: DTC protocol (real-time updates from Sierra Chart)
- **Message Type**: Type 600/602 (AccountBalanceUpdate)
- **Routing**: data_bridge normalization → MessageRouter → Panel1
- **Only in LIVE mode**: Balance requests sent after fills (core/message_router.py:176-179)

**Simulated Account Balance**:
- **Source**: `core/sim_balance.py::SimBalanceManager` (persistent JSON storage)
- **Storage**: `data/sim_balance_{account}.json` (scoped by account!)
- **Derivation**: Ledger-based (start balance + realized PnL - fees)
- **Updates**: Called explicitly when SIM trades execute
- **Do NOT depend on Sierra sending SIM balance** - it's unreliable

**SIM Balance Source of Truth**:
```python
# In SIM, derive balance from ledger
balance = starting_balance + sum(realized_pnl) - sum(fees)
# NOT from DTC balance updates
```

### 4.3 Order/Position Data

**Source**: DTC Protocol (unified for both modes)
- **Orders**: Type 301, 304, 307 (OrderUpdate, OrderFillResponse, etc)
- **Positions**: Type 306 (PositionUpdate)
- **Routing**: Normalized in data_bridge → MessageRouter → Panels
- **NOTE**: Sierra Chart only sends unsolicited position updates in LIVE mode, not SIM

---

## 5. CONDITIONAL LOGIC BRANCHES BY MODE

### 5.1 Panel1: Equity Curve Separation (panels/panel1.py)

Panel1 maintains **separate equity point lists** for each `(mode, account)`:

**Data structures**:
```python
# CORRECT - Scoped by (mode, account)
_equity_curves: dict[tuple[str, str], list[tuple[float, float]]] = {}
# Key: (mode, account), Value: [(timestamp_utc, balance), ...]

_current_balances: dict[tuple[str, str], float] = {}
# Key: (mode, account), Value: last_balance
```

**set_trading_mode(mode, account)** switches active curve:
```python
def set_trading_mode(self, mode: str, account: str) -> None:
    self._active_scope = (mode, account)

    # Initialize if first time seeing this scope
    if self._active_scope not in self._equity_curves:
        self._equity_curves[self._active_scope] = []
        self._current_balances[self._active_scope] = 0.0

    # Swap to scoped data
    self._equity_points = self._equity_curves[self._active_scope]
    self._current_balance = self._current_balances[self._active_scope]

    # Single repaint
    self.update()
```

**update_equity_series_from_balance()** appends to active curve:
```python
def update_equity_series_from_balance(self, balance: float) -> None:
    timestamp_utc = datetime.now(timezone.utc).timestamp()
    self._equity_points.append((timestamp_utc, balance))
    self._current_balance = balance
    # Update scoped storage
    self._current_balances[self._active_scope] = balance
```

### 5.2 Panel2: Session State Separation (panels/panel2.py)

Panel2 maintains **separate session state files** for each `(mode, account)`:

**Path Construction**:
```python
def _get_state_path(self) -> Path:
    mode = self.current_mode
    account = self.current_account or "unknown"
    return Path(f"data/runtime_state_panel2_{mode}_{account}.json")
```

**_load_state()** loads session timers based on current `(mode, account)`:
- Reads appropriate JSON file
- Restores `entry_time_epoch`, `heat_start_epoch`
- **Atomic read**: Read from temp file if main file is corrupt

**_save_state()** persists to mode-specific file:
- Writes trade duration, heat timer, position data
- **Atomic write**: Write to temp → rename (see §8)

**Separated Data**:
- Trade entry time (ephemeral timestamp)
- Heat warning start time
- Per-trade MAE/MFE extremes
- Session-scoped position data

### 5.3 Panel2: SIM-Only Position Seeding

Comment at `panels/panel2.py:148-152`:
> "Seeds position from fill data when in SIM mode (Sierra Chart doesn't send non-zero PositionUpdate for SIM)."

**Logic** when fill happens in SIM mode:
1. Extract symbol, qty, price from order fill
2. If fill is entry: Create position record
3. If fill is exit: Mark position closed

### 5.4 MessageRouter: Balance Update Behavior

**File**: `core/message_router.py:159-182`

**LIVE mode behavior**:
- After fill (status 3 or 7), requests fresh account balance from DTC
- Ensures UI always reflects current account equity

**SIM mode behavior**:
- Skips balance request after fills
- Uses ledger-derived balance from `sim_balance_{account}.json` instead

---

## 6. PANEL-LEVEL MODE TRACKING

Each panel maintains its own `(mode, account)` scope:

**Panel1** (Balance/Equity):
- `self.current_mode: str = "DEBUG"`
- `self.current_account: Optional[str] = None`
- `self._active_scope: tuple[str, str]` - Used to index scoped data

**Panel2** (Live Trading):
- `self.current_mode: str = "DEBUG"`
- `self.current_account: Optional[str] = None`
- Used to select state file path

**Panel3** (Statistics):
- `self.current_mode: str = "DEBUG"`
- `self.current_account: Optional[str] = None`
- Used to scope trade records in database

**Update Mechanism**: MessageRouter broadcasts mode change to all panels:

In `_on_order_signal()` and `_on_position_signal()`:
```python
new_mode = auto_detect_mode_from_order(msg)
new_account = msg.get("TradeAccount", "")

if should_switch_mode(new_mode, new_account):  # Debounce check
    # Broadcast ModeChanged event
    self._broadcast_mode_changed(new_mode, new_account)

def _broadcast_mode_changed(self, mode: str, account: str):
    """Single ModeChanged event to all panels."""
    marshal_to_qt_thread(lambda: panel_balance.set_trading_mode(mode, account))
    marshal_to_qt_thread(lambda: panel_live.set_trading_mode(mode, account))
    marshal_to_qt_thread(lambda: panel_stats.set_trading_mode(mode, account))
```

---

## 7. PROCESSING ORDER & HEARTBEAT

### 7.1 Single Funnel for DTC Messages

**One processing pipeline**:
```
DTC Raw Frame
  ↓
[data_bridge normalization]
  ↓
[MessageRouter dispatch]
  ↓
Process in order:
  1. Orders (301, 304, 307)
  2. Positions (306)
  3. Balance (600, 602)
  4. UI update (coalesced)
```

**Always apply**: Orders → Positions → Balance → UI

### 7.2 Coalesced UI Updates

UI paints on a **coalesced price heartbeat** (5–10 Hz), **not** on every message.

```python
# In MessageRouter
UI_REFRESH_INTERVAL_MS = 100  # 10 Hz

def _schedule_ui_refresh(self):
    """Coalesce UI updates to prevent flicker."""
    if not self._ui_refresh_pending:
        self._ui_refresh_pending = True
        QTimer.singleShot(UI_REFRESH_INTERVAL_MS, self._flush_ui_updates)

def _flush_ui_updates(self):
    """Single repaint for all accumulated updates."""
    self._ui_refresh_pending = False
    self.panel_balance.update()
    self.panel_live.update()
    self.panel_stats.update()
```

This prevents the UI from repainting 500 times/second when DTC floods messages.

---

## 8. ATOMIC PERSISTENCE

**All JSON/state writes** via **temp-file → rename**:

```python
def _save_state_atomic(self, data: dict, path: Path) -> None:
    """Atomic write to prevent corruption."""
    # Add schema version and UTC timestamp
    data["_schema_version"] = "2.0"
    data["_saved_at_utc"] = datetime.now(timezone.utc).isoformat()

    # Write to temp file
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Atomic rename (POSIX guarantees atomicity)
    temp_path.replace(path)
```

**Schema versioning**: Every file includes `_schema_version` to enable migrations.

**UTC timestamps only**: All saved timestamps use ISO 8601 with 'Z' suffix.

---

## 9. IDEMPOTENCY

**Handlers MUST be replay-safe**. Applying the same fill/order twice = no state change.

Example: Order fill handler
```python
def on_order_fill(self, order_id: str, fill_data: dict) -> None:
    """Idempotent fill handler."""
    # Check if already processed
    if order_id in self._processed_fills:
        logger.debug(f"Ignoring duplicate fill for order {order_id}")
        return

    # Process fill
    self._apply_fill(fill_data)

    # Mark as processed
    self._processed_fills.add(order_id)
    self._persist_processed_fills()
```

**Why**: Recovery sequence replays fills. Idempotency prevents double-counting PnL.

---

## 10. MODE DRIFT SENTINEL

**If any inbound message's `TradeAccount` disagrees with active `(mode, account)`, raise a yellow banner and log a structured event.**

```python
def _check_mode_drift(self, msg: dict) -> None:
    """Non-blocking mode drift detection."""
    incoming_account = msg.get("TradeAccount", "")
    incoming_mode = detect_mode_from_account(incoming_account)

    if (incoming_mode, incoming_account) != (self._current_mode, self._current_account):
        # Log structured event
        logger.warning(
            "MODE_DRIFT_DETECTED",
            extra={
                "expected_mode": self._current_mode,
                "expected_account": self._current_account,
                "incoming_mode": incoming_mode,
                "incoming_account": incoming_account,
                "message_type": msg.get("Type"),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Show yellow banner (non-blocking)
        self._show_mode_drift_banner(incoming_mode, incoming_account)
```

**Non-blocking**: Does not halt trading, but alerts user to investigate.

---

## 11. THEME SYSTEM & VISUAL MODE INDICATION

**File**: `config/theme.py`

Three complete theme definitions reflect operating mode visually:

**DEBUG Theme** (Grey/Silver - Development):
- Badge: Golden amber (#F5B342) with black text
- Background: Dark (#1E1E1E)
- Text: Silver (#C0C0C0)
- Purpose: Neutral appearance for development/testing

**SIM Theme** (White/Blue - Paper Trading):
- Badge: Gentle blue (#4DA7FF) with black text
- Background: White (#FFFFFF)
- Text: Black (#000000)
- Border: Neon cyan (#00D4FF) with glow effect
- Purpose: Safe, sandbox-like appearance

**LIVE Theme** (Black/Gold - Real Money):
- Badge: Vibrant green (#00C97A) with white text
- Background: Pure black (#000000)
- Text: Gold (#FFD700)
- **Red glow effect** on panels when LIVE_ARMED = True
- Purpose: High-attention appearance for real trading

**Arming Indicator**:
```python
if mode == "LIVE" and LIVE_ARMED:
    # Apply red glow effect
    panel_border_color = "#FF0000"
    panel_border_width = 3
    panel_box_shadow = "0 0 20px rgba(255, 0, 0, 0.8)"
```

---

## 12. CONFIGURATION & ENVIRONMENT VARIABLES

**Key environment variables** (set via OS or config.json):

**Trading account identification**:
- `SIERRA_TRADE_ACCOUNT=120005` (LIVE account ID, default: 120005)
- `TRADING_MODE=SIM` (Default mode, default: SIM)

**DTC connection**:
- `SIERRA_DTC_HOST=127.0.0.1` (DTC server, default: localhost)
- `SIERRA_DTC_PORT=11099` (DTC port, default: 11099)

**Config file override** (config/config.json):
```json
{
  "TRADING_MODE": "LIVE",
  "LIVE_ACCOUNT": "120005",
  "POSTGRES_DSN": "postgresql+psycopg://user:pass@host:5432/db"
}
```

---

## 13. KEY FILES & CLASSES SUMMARY

### Detection & Routing

**utils/trade_mode.py**
- `detect_mode_from_account(account: str)` -> Literal["LIVE", "SIM", "DEBUG"]
- `auto_detect_mode_from_order(order_msg: dict)` -> Optional[str]
- `auto_detect_mode_from_position(position_msg: dict)` -> Optional[str]
- `should_switch_mode(mode, account, qty=None)` -> bool (with debounce)
- `is_sim_mode(mode)`, `is_live_mode(mode)`, `is_debug_mode(mode)` - Predicates

**core/state_manager.py::StateManager**
- `current_account`: Optional[str]
- `is_sim_mode`: bool
- `mode_history`: list[tuple[datetime, str, str]]
- `set_mode(account: str)` -> None

**core/message_router.py::MessageRouter**
- `_subscribe_to_signals()` - Wire Blinker signal handlers
- `_on_order_signal(sender, **kwargs)` - Handle orders, auto-detect mode
- `_on_position_signal(sender, **kwargs)` - Handle positions, auto-detect mode
- `_on_balance_signal(sender, **kwargs)` - Handle balance updates
- `_on_trade_account_signal(sender, **kwargs)` - Handle account info
- `_recovery_sequence()` - 3-step authoritative recovery
- `_check_mode_drift(msg)` - Mode drift sentinel
- `_current_mode`, `_current_account` - Active scope

### Data Bridge & Normalization

**core/data_bridge.py::DTCClientJSON**
- Receives raw DTC frames
- Normalizes to AppMessage via `_dtc_to_app_event()`
- Emits Blinker signals: `signal_order`, `signal_position`, `signal_balance`, `signal_trade_account`

### Panels & UI

**panels/panel1.py::Panel1**
- `current_mode: str`, `current_account: Optional[str]` - Active scope
- `set_trading_mode(mode: str, account: str)` - Update scope
- `update_equity_series_from_balance(balance: float)` - Append to curve
- `_equity_curves: dict[tuple[str, str], list]` - Scoped curves
- `_current_balances: dict[tuple[str, str], float]` - Scoped balances

**panels/panel2.py::Panel2**
- `current_mode: str`, `current_account: Optional[str]` - Active scope
- `_load_state()`, `_save_state()` - Mode-specific persistence (atomic)
- `on_order_update()`, `on_position_update()` - Handle DTC updates
- `_get_state_path()` - Returns scoped path

**panels/panel3.py::Panel3**
- `current_mode: str`, `current_account: Optional[str]` - Active scope
- Scopes trade records in database by `(mode, account)`

### Services & Persistence

**core/sim_balance.py::SimBalanceManager**
- `get_balance(account: str)` -> float (scoped by account!)
- `set_balance(account: str, balance: float)` -> None
- `adjust_balance(account: str, delta: float)` -> float
- **Ledger-derived**: balance = start + realized_pnl - fees
- Storage: `data/sim_balance_{account}.json`

**services/market_data_service.py::MarketDataService**
- `read_snapshot()` -> Optional[MarketSnapshot]
- Reads from CSV (mode-agnostic)
- Caches results based on file modification time

### Theme System

**config/theme.py**
- `THEME` dict - Current active theme
- `DEBUG_THEME`, `SIM_THEME`, `LIVE_THEME` - Theme definitions
- `apply_trading_mode_theme(mode: str)` - Switch theme
- `switch_theme(mode_name: str)` - Helper to apply theme
- `apply_live_arming_effect(armed: bool)` - Red glow when armed

---

## 14. DATA FLOW DIAGRAM

```
DTC Connection (Sierra Chart)
        ↓
[DTCClientJSON] normalizes frames
        ↓
[Debounce Window] 750ms, 2 consecutive signals
        ↓
[Blinker Signals] four channels:
- signal_order → ORDER_UPDATE
- signal_position → POSITION_UPDATE
- signal_balance → BALANCE_UPDATE
- signal_trade_account → TRADE_ACCOUNT
        ↓
[MessageRouter] dispatches to panels
├─ Auto-detects mode from TradeAccount field
├─ Checks mode drift sentinel
├─ Broadcasts ModeChanged(mode, account) to all panels
├─ Routes data to appropriate panel
└─ Requests balance (LIVE only)
        ↓
[Panels] freeze → swap scope → reload → repaint
├─ Panel1: swap to (mode, account) equity curve
├─ Panel2: load (mode, account) session state
└─ Panel3: filter trade records by (mode, account)
        ↓
[Persistence] - Atomic writes with schema versioning
├─ data/runtime_state_panel2_{mode}_{account}.json
├─ data/sim_balance_{account}.json
├─ data/last_known_mode.json (24h TTL)
└─ data/snapshot.csv (both modes)
```

---

## 15. IMPLEMENTATION PATTERNS

### Pattern for Mode-Dependent Code

```python
from utils.trade_mode import is_sim_mode, is_live_mode

if is_sim_mode(current_mode):
    # SIM-specific behavior
    balance = sim_balance_manager.get_balance(account)
elif is_live_mode(current_mode):
    # LIVE-specific behavior
    balance = await dtc_client.request_account_balance()
else:
    # DEBUG mode fallback
    balance = 0.0
```

### Listening for Mode Changes in a Panel

```python
def set_trading_mode(self, mode: str, account: str) -> None:
    """Called by MessageRouter when mode changes."""
    old_scope = (self.current_mode, self.current_account)
    new_scope = (mode, account)

    # 1. Freeze current state
    self._save_state()

    # 2. Swap to new scope
    self.current_mode = mode
    self.current_account = account
    self._active_scope = new_scope

    # 3. Reload from persistent storage
    self._load_state()

    # 4. Single repaint
    self.update()
```

### Persisting Mode-Specific State (Atomic)

```python
def _save_state(self) -> None:
    """Atomic write to scoped state file."""
    path = self._get_state_path()  # Returns scoped path

    data = {
        "entry_time_epoch": self.entry_time_epoch,
        "heat_start_epoch": self.heat_start_epoch,
        "mae": self.mae,
        "mfe": self.mfe,
    }

    # Atomic write with schema version
    self._save_state_atomic(data, path)

def _load_state(self) -> None:
    """Load from scoped state file."""
    path = self._get_state_path()

    if not path.exists():
        return

    try:
        with open(path, 'r') as f:
            data = json.load(f)

        # Validate schema version
        if data.get("_schema_version") != "2.0":
            logger.warning(f"State file {path} has old schema, ignoring")
            return

        self.entry_time_epoch = data.get("entry_time_epoch")
        self.heat_start_epoch = data.get("heat_start_epoch")
        self.mae = data.get("mae", 0.0)
        self.mfe = data.get("mfe", 0.0)
    except Exception as e:
        logger.error(f"Failed to load state from {path}: {e}")
```

### Testing Mode Detection

Test utilities in `utils/trade_mode.py:271-303`:

```python
def _test_mode_detection():
    test_cases = [
        ("120005", None, "LIVE"),       # LIVE_ACCOUNT config
        ("Sim1", None, "SIM"),          # SIM account
        ("Sim2", None, "SIM"),          # Another SIM
        ("", None, "DEBUG"),            # Empty account
        ("Unknown123", None, "DEBUG"),  # Unknown account
    ]

    for account, qty, expected_mode in test_cases:
        detected = detect_mode_from_account(account)
        assert detected == expected_mode, f"Expected {expected_mode}, got {detected}"
```

---

## 16. CRITICAL IMPLEMENTATION DETAILS

### 16.1 Order Message Routing with Mode Auto-Detection

**core/message_router.py:107-130** - Order signal handler:

1. Receives DTC order message
2. Auto-detects mode from account: `mode = auto_detect_mode_from_order(msg)`
3. Checks debounce window (2 consecutive agreeing signals)
4. If mode changed, broadcasts to all panels: `set_trading_mode(mode, account)`
5. Routes to Panel2 for live trading updates
6. Routes to Panel3 for statistics collection
7. **LIVE only**: Requests balance after fill (not SIM)

### 16.2 Balance Request Gating by Mode

**core/message_router.py:174-181** - Balance request logic:

```python
detected_mode = auto_detect_mode_from_order(msg)
detected_account = msg.get("TradeAccount", "")

if detected_mode == "LIVE":
    debug_data("Order filled in LIVE mode - requesting updated balance")
    if self._dtc_client and hasattr(self._dtc_client, "request_account_balance"):
        self._dtc_client.request_account_balance()
else:
    debug_data(f"Order filled in {detected_mode} mode - deriving balance from ledger")
    # Use sim_balance_manager for SIM
    balance = sim_balance_manager.get_balance(detected_account)
```

This prevents unnecessary DTC round-trips in SIM mode.

### 16.3 Equity Curve Switching in Panel1

**panels/panel1.py:671-789** - Trading mode handler:

```python
def set_trading_mode(self, mode: str, account: str) -> None:
    prev_scope = (self.current_mode, self.current_account)
    self.current_mode = mode
    self.current_account = account
    self._active_scope = (mode, account)

    # Initialize scope if first time
    if self._active_scope not in self._equity_curves:
        self._equity_curves[self._active_scope] = []
        self._current_balances[self._active_scope] = 0.0

    # Switch active curve (single repaint)
    self._equity_points = self._equity_curves[self._active_scope]
    self._current_balance = self._current_balances[self._active_scope]

    # Apply theme
    switch_theme(self.current_mode.lower())

    # Single repaint
    self.update()
```

### 16.4 Session State Persistence in Panel2

**panels/panel2.py:670-712** - Session save/load with mode routing:

```python
def _get_state_path(self) -> Path:
    """Returns scoped state path."""
    mode = self.current_mode
    account = self.current_account or "unknown"
    return Path(f"data/runtime_state_panel2_{mode}_{account}.json")

def _load_state(self) -> None:
    state_path = self._get_state_path()
    try:
        with open(state_path, "r") as f:
            state = json.load(f)

        # Validate schema
        if state.get("_schema_version") != "2.0":
            logger.warning(f"Old schema in {state_path}, ignoring")
            return

        self.entry_time_epoch = state.get("entry_time_epoch")
        self.heat_start_epoch = state.get("heat_start_epoch")
    except FileNotFoundError:
        pass  # First time in this scope
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
```

---

## 17. SUMMARY: Data Separation Architecture

APPSIERRA implements **three-tier mode separation with strict namespacing**:

1. **Detection Tier**: Account identifier determines mode automatically from DTC `TradeAccount` field
2. **Routing Tier**: MessageRouter dispatches data to correct panels with `(mode, account)` scope
3. **Storage Tier**: Each panel maintains scoped state - separate curves, session files, database records

**Key Design Principle**:
> Every read and write is scoped by `(mode, account)`. On `ModeChanged`, all panels swap to that scope, reload their data, and repaint once.

**Benefits**:
- **Complete data isolation**: Prevents accidental mixing of SIM and LIVE statistics
- **Seamless switching**: No manual reconfiguration when switching modes
- **Visual safety**: Theme colors + LIVE arming gate prevent trading errors
- **Automatic recovery**: 3-step sequence rebuilds state after disconnect
- **Audit trail**: Mode history with UTC timestamps for debugging

---

## 18. TESTING THE MODE DETECTION SYSTEM

Run the built-in test:

```bash
cd /home/user/APPV3
python utils/trade_mode.py
```

Expected output shows:
- Account matching tests (LIVE_ACCOUNT, "Sim*", unknown)
- Mode switch decision tests (orders always switch, positions switch on qty != 0)
- Debounce window tests (2 consecutive agreeing signals)

---

## 19. FORBIDDEN PATTERNS (Anti-Patterns)

### ❌ Shared Singleton Without Scope

```python
# WRONG - Single position object for all modes
current_position = {"symbol": "ES", "qty": 10}
```

**Why forbidden**: SIM and LIVE positions will overwrite each other.

**Correct**:
```python
# RIGHT - Scoped by (mode, account)
positions: dict[tuple[str, str], dict] = {}
positions[("SIM", "Sim1")] = {"symbol": "ES", "qty": 10}
positions[("LIVE", "120005")] = {"symbol": "ES", "qty": 5}
```

### ❌ Local Timestamps

```python
# WRONG - DST-sensitive
timestamp = datetime.now()
```

**Why forbidden**: Daylight saving time will cause 1-hour jumps.

**Correct**:
```python
# RIGHT - Always UTC
timestamp = datetime.now(timezone.utc).isoformat()
```

### ❌ Treating SubmitNewSingleOrder as Truth

```python
# WRONG - Assuming order exists after submission
def on_order_submit(self, order_id: str):
    self.open_orders[order_id] = {"status": "open"}  # ❌ Not yet confirmed!
```

**Why forbidden**: Order may be rejected. Only `OrderUpdate` (301) is authoritative.

**Correct**:
```python
# RIGHT - Wait for OrderUpdate confirmation
def on_order_update(self, msg: dict):
    if msg["Type"] == 301:  # OrderUpdate
        order_id = msg["ServerOrderID"]
        self.open_orders[order_id] = msg  # ✓ Confirmed by server
```

### ❌ Inferring Mode from UI Toggle

```python
# WRONG - UI toggle is not authoritative
if self.mode_selector.currentText() == "LIVE":
    mode = "LIVE"
```

**Why forbidden**: UI can desync from DTC reality.

**Correct**:
```python
# RIGHT - Only DTC TradeAccount field is authoritative
mode = detect_mode_from_account(msg.get("TradeAccount"))
```

---

## 20. CHECKLIST FOR NEW CODE

Before committing code that touches mode/account logic:

- [ ] All state reads/writes scoped by `(mode, account)`
- [ ] No shared singletons without scope keys
- [ ] All timestamps use `datetime.now(timezone.utc)`
- [ ] All file writes use atomic temp → rename
- [ ] Schema version in all persistent files
- [ ] Idempotent handlers (replay-safe)
- [ ] Mode inferred only from DTC `TradeAccount` field
- [ ] LIVE arming gate checked before real orders
- [ ] ModeChanged broadcasts freeze → swap → reload → repaint
- [ ] UI updates coalesced (not per-message)
- [ ] Mode drift sentinel logs structured events
- [ ] Recovery sequence implemented for reconnects
- [ ] Debounce window applied to mode switches

---

**END OF DOCUMENT**

**Version**: 2.0
**Schema**: `DATA_SEPARATION_ARCHITECTURE_V2`
**Next Review**: Before any mode/account refactoring
