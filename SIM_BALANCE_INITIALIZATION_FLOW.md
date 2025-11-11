# SIM Balance Initialization - Complete Flow

## The Complete Initialization Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Runs: python main.py                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
        ┌──────────────────────────────────────┐
        │         main.py (Line 18-30)         │
        │                                      │
        │  def main():                         │
        │    app = QApplication(sys.argv)      │
        │    win = MainWindow()  ← HERE!       │
        │    win.show()                        │
        │    sys.exit(app.exec())              │
        └──────────────────────┬───────────────┘
                               │
                               ↓
        ┌──────────────────────────────────────────────────┐
        │  MainWindow.__init__() (app_manager.py, Line 44) │
        │                                                  │
        │  def __init__(self):                            │
        │    ...                                          │
        │    self._setup_state_manager()  ← Step 1        │
        │    self._setup_theme()                          │
        │    self._build_ui()                             │
        │    self._setup_reset_balance_hotkey()           │
        │    ...                                          │
        └──────────────────────┬──────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ↓                             ↓
    ┌─────────────────────────┐   ┌──────────────────────┐
    │ STEP 1: Setup State     │   │ STEP 2: Build UI     │
    │ (app_manager.py:76-85)  │   │ (app_manager.py:98)  │
    └────────────┬────────────┘   └──────────┬───────────┘
                 │                           │
                 ↓                           ↓
    ┌──────────────────────────────────┐   Panel1.__init__()
    │  _setup_state_manager()          │   └─ _equity_points_sim = []
    │                                  │   └─ _equity_points_live = []
    │  from core.state_manager import  │   └─ _current_display_mode = "SIM"
    │      StateManager                │   └─ Creates UI elements
    │  from core.app_state import      │
    │      set_state_manager           │   Panel2.__init__()
    │                                  │   └─ Ready to process orders
    │  self._state = StateManager() ←│
    │  set_state_manager(self._state)  │
    └──────────────────┬───────────────┘
                       │
                       ↓
        ┌───────────────────────────────────────────────────┐
        │  StateManager.__init__() (state_manager.py:21-52) │
        │                                                   │
        │  self.sim_balance = 10000.0  ← INITIALIZED HERE! │
        │  self.live_balance = 0.0                         │
        │  self.current_mode = "SIM"                       │
        │  self.position_mode = None                       │
        │  ...                                             │
        │                                                   │
        │  [INITIALIZATION COMPLETE]                        │
        │  SIM Balance is now $10,000.00                   │
        │                                                   │
        └─────────────────────────────────────────────────────┘
```

---

## Step-by-Step Breakdown

### Step 1: Python Runs main.py

**File**: `main.py` (Lines 18-30)

```python
def main():
    app = QtWidgets.QApplication(sys.argv)

    # This creates MainWindow which triggers everything
    win = MainWindow()  # ← STARTS THE CHAIN

    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

**What happens**: Creates a `QApplication` then immediately creates `MainWindow()`.

---

### Step 2: MainWindow Initialization Starts

**File**: `core/app_manager.py` (Lines 44-68)

```python
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # These are the setup calls in order:
        self._setup_window()              # Line 56
        self._setup_state_manager()       # Line 57 ← CRITICAL!
        self._setup_theme()               # Line 58
        self._build_ui()                  # Line 59
        self._setup_theme_toolbar()       # Line 60
        self._setup_mode_selector()       # Line 61
        self._setup_reset_balance_hotkey()# Line 62
```

**Key Point**: `_setup_state_manager()` is called at **Line 57**, before anything else that needs it.

---

### Step 3: StateManager is Created (The Initialization!)

**File**: `core/app_manager.py` (Lines 76-85)

```python
def _setup_state_manager(self) -> None:
    """Setup app-wide state manager."""
    try:
        from core.state_manager import StateManager
        from core.app_state import set_state_manager

        # CREATE THE STATE MANAGER
        self._state = StateManager()  # ← CALLS StateManager.__init__()

        # Register it globally so other modules can access it
        set_state_manager(self._state)

    except Exception as e:
        log.error(f"Failed to setup state manager: {e}")
```

**What it does**:
1. Imports `StateManager` class
2. Creates an instance: `StateManager()`
3. Registers it globally via `set_state_manager()`

---

### Step 4: StateManager.__init__() - Where SIM Balance Gets Set

**File**: `core/state_manager.py` (Lines 21-52)

```python
class StateManager:
    def __init__(self):
        # Core dynamic store
        self._state: dict[str, Any] = {}

        # Mode awareness
        self.current_account: Optional[str] = None
        self.is_sim_mode: bool = False
        self.current_mode: str = "SIM"

        # ===== MODE-SPECIFIC BALANCE =====
        self.sim_balance: float = 10000.0  # ← SIM BALANCE INITIALIZED TO $10K!
        self.sim_balance_start_of_month: float = 10000.0
        self.live_balance: float = 0.0

        # Position tracking
        self.position_symbol: Optional[str] = None
        self.position_qty: float = 0
        self.position_entry_price: float = 0
        # ... etc
```

**THIS IS WHERE IT HAPPENS:**
- Line 33: `self.sim_balance: float = 10000.0`
- This is a hardcoded default value
- Set when StateManager is instantiated
- **Happens automatically on app startup**

---

### Step 5: SimBalanceManager Checks for Persistence

**File**: `core/sim_balance.py` (Lines 31-35)

```python
class SimBalanceManager:
    def __init__(self):
        self._balance: float = SIM_STARTING_BALANCE  # 10000.0
        self._last_reset_month: Optional[str] = None

        self._load()  # ← TRY TO LOAD FROM FILE
        self._check_monthly_reset()  # ← CHECK IF NEW MONTH
```

**What `_load()` does** (Lines 89-101):

```python
def _load(self) -> None:
    try:
        if not SIM_BALANCE_FILE.exists():
            # FILE DOESN'T EXIST YET (first run)
            log.debug("[SIM] No persisted balance file found, using defaults")
            self._last_reset_month = self._get_current_month()
            return  # ← USE DEFAULT (10000.0)

        # FILE EXISTS - LOAD IT
        with open(SIM_BALANCE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        self._balance = float(data.get("balance", SIM_STARTING_BALANCE))
        self._last_reset_month = data.get("last_reset_month", ...)

        log.debug(f"[SIM] Loaded balance: ${self._balance:,.2f}")

    except Exception as e:
        log.warning(f"[SIM] Error loading balance file: {e}")
        self._balance = SIM_STARTING_BALANCE  # ← FALLBACK TO 10000.0
```

**What `_check_monthly_reset()` does** (Lines 41-51):

```python
def _check_monthly_reset(self) -> None:
    """Check if new month - reset if needed."""
    current_month = self._get_current_month()  # e.g., "2025-11"

    if self._last_reset_month != current_month:
        # MONTH HAS CHANGED - RESET!
        self._balance = SIM_STARTING_BALANCE  # 10000.0
        self._last_reset_month = current_month
        self._save()
        log.info(f"[SIM] Monthly reset: Balance reset to $10,000.00")
```

---

## The Complete Initialization Timeline

```
Time    Event                                    SIM Balance State
──────────────────────────────────────────────────────────────────────
 T0     python main.py executed                 (not created yet)

 T1     MainWindow.__init__() called            (not created yet)

 T2     _setup_state_manager() called           (not created yet)

 T3     StateManager() instantiated             $10,000.00 ← CREATED!
        (state_manager.py:33)

 T4     set_state_manager(state) called         $10,000.00 (registered globally)

 T5     MainWindow._build_ui() called           $10,000.00 (Panel1 ready)

 T6     Panel1 created & displayed              $10,000.00 (shown on screen!)

 T7     App ready, waiting for user input       $10,000.00 (ready for trading)
```

---

## THREE Possible Initial Balance Values

### Scenario 1: First App Run (Most Common)

```
File: data/sim_balance.json        Does NOT exist
│
StateManager created               sim_balance = 10000.0 ✓
│
SimBalanceManager._load()          File not found
│
Uses default                       sim_balance = 10000.0 ✓
│
_check_monthly_reset()             First run, set month
│
Result                             Balance = $10,000.00 ✓
```

### Scenario 2: App Reopened Same Month

```
File: data/sim_balance.json        EXISTS with balance=10500.00
│
StateManager created               sim_balance = 10000.0 (default)
│
SimBalanceManager._load()          File found!
│
Load from file                     sim_balance = 10500.00 ✓
│
_check_monthly_reset()             Month hasn't changed
│
Result                             Balance = $10,500.00 ✓ (persisted!)
```

### Scenario 3: App Reopened Next Month

```
File: data/sim_balance.json        EXISTS with balance=10500.00
                                   AND last_reset_month="2025-10"
│
StateManager created               sim_balance = 10000.0 (default)
│
SimBalanceManager._load()          File found, load 10500.00
│
sim_balance = 10500.00
last_reset_month = "2025-10"
│
_check_monthly_reset()             Current month is "2025-11"
│                                  Month changed!
│
Reset!                             sim_balance = 10000.0 ✓
Save to file                       {"balance": 10000.0,
                                    "last_reset_month": "2025-11"}
│
Result                             Balance = $10,000.00 ✓ (auto-reset!)
```

---

## Code Path Diagram

```
main.py:main()
  │
  └──> MainWindow.__init__()                     [app_manager.py:44]
         │
         └──> _setup_state_manager()             [app_manager.py:76]
                │
                ├──> StateManager()              [state_manager.py:21]
                │     └──> self.sim_balance = 10000.0  [state_manager.py:33]
                │
                └──> set_state_manager(state)    [app_state.py:29]
                      └──> _state_manager = state (global registration)

ALSO (in parallel):

main.py:main()
  │
  └──> MainWindow.__init__()                     [app_manager.py:44]
         │
         └──> _build_ui()                        [app_manager.py:98]
                │
                └──> Panel1.__init__()           [panel1.py:129]
                      ├──> self._equity_points_sim = []
                      ├──> self._current_display_mode = "SIM"
                      └──> GUI elements created
```

---

## Where The Value 10000.0 Comes From

The `10000.0` is **hardcoded** in the source code:

**File**: `core/state_manager.py` (Line 33)
```python
self.sim_balance: float = 10000.0  # ← HARDCODED DEFAULT
```

**File**: `core/sim_balance.py` (Line 20)
```python
SIM_STARTING_BALANCE: float = 10000.00  # ← HARDCODED DEFAULT
```

Both files have the same value, so:
- Initial balance = `10000.0`
- Reset balance = `10000.0`
- Fallback balance = `10000.0`

---

## When Each Component Gets Initialized

| Order | Component | File | Line | Status |
|-------|-----------|------|------|--------|
| 1 | StateManager created | state_manager.py | 21 | **SIM balance = $10K** |
| 2 | Registered globally | app_state.py | 29 | Accessible everywhere |
| 3 | Panel1 created | panel1.py | 129 | Equity curves initialized |
| 4 | Panel2 created | panel2.py | 46 | Ready for trades |
| 5 | SimBalanceManager created | sim_balance.py | 31 | Loads persisted balance |
| 6 | UI displayed | app_manager.py | 100+ | Shows $10,000 |

---

## The Key Point

**SIM balance is initialized in TWO places:**

### Primary: StateManager (Always Happens)
```python
StateManager.__init__()
  └─ self.sim_balance = 10000.0  [Line 33]
```
**This always runs, always sets to $10K initially**

### Secondary: SimBalanceManager (Overrides if File Exists)
```python
SimBalanceManager.__load()
  └─ self._balance = load from JSON  [if file exists]
```
**This can override the default if persistence file exists**

---

## Summary

### How SIM Balance Gets Set

1. **App starts** → `main.py` creates `MainWindow()`

2. **MainWindow init** → calls `_setup_state_manager()`

3. **StateManager created** → `self.sim_balance = 10000.0` ← **INITIAL VALUE SET HERE**

4. **SimBalanceManager init** → tries to load from `data/sim_balance.json`
   - If file exists: uses saved balance
   - If file doesn't exist: uses default 10000.0
   - If month changed: resets to 10000.0

5. **Panel1 created** → displays the balance

### Result
- **First run**: Shows $10,000.00
- **Reopen same month**: Shows saved balance from JSON
- **New month**: Shows $10,000.00 (auto-reset)

**Everything is automatic - no user interaction needed!**

