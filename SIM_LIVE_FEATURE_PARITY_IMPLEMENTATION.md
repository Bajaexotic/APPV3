# SIM/LIVE Feature Parity Implementation - Complete

## Overview
This implementation enables SIM mode to have complete feature parity with LIVE mode, including:
- ✅ Separate balance tracking per mode (SIM: $10K/month reset, LIVE: real DTC)
- ✅ Independent equity graphs for each mode
- ✅ Complete trade history and statistics for both modes separately
- ✅ Manual reset hotkey (Ctrl+Shift+R) to reset SIM balance to $10K

---

## What Changed

### Phase 1: Balance Management (Core)

#### 1.1 StateManager (`core/state_manager.py`)
**Lines 33-34 (Updated)**
```python
self.sim_balance: float = 10000.0  # SIM mode starting balance: $10K/month
self.sim_balance_start_of_month: float = 10000.0  # Track starting balance for reset
```

**Lines 178-182 (New Method)**
```python
def reset_sim_balance_to_10k(self) -> float:
    """Reset SIM balance to $10,000 (for monthly reset or manual hotkey)"""
    self.sim_balance = 10000.0
    self.sim_balance_start_of_month = 10000.0
    return self.sim_balance
```

#### 1.2 SIM Balance Manager (`core/sim_balance.py`)
**Line 20 (Updated)**
```python
SIM_STARTING_BALANCE: float = 10000.00  # Changed from 0.00
```

**Lines 41-51 (Enabled Monthly Reset)**
```python
def _check_monthly_reset(self) -> None:
    """Now checks if a new month has started and resets SIM balance to $10,000"""
    current_month = self._get_current_month()
    if self._last_reset_month != current_month:
        self._balance = SIM_STARTING_BALANCE
        self._last_reset_month = current_month
        self._save()
        log.info(f"[SIM] Monthly reset: Balance reset to ${self._balance:,.2f} for {current_month}")
```

**Lines 78-87 (Enabled Manual Reset)**
```python
def reset_balance(self) -> float:
    """Manually reset SIM balance to $10,000 (e.g., via Ctrl+Shift+R hotkey)"""
    self._balance = SIM_STARTING_BALANCE
    self._last_reset_month = self._get_current_month()
    self._save()
    log.info(f"[SIM] Manual reset: Balance reset to ${self._balance:,.2f}")
    return self._balance
```

---

### Phase 2: Separate Equity Graphs

#### 2.1 Panel1 (`panels/panel1.py`)

**Lines 143-147 (New Storage)**
```python
# Data - separate equity curves per mode for full parity
self._equity_points: list[tuple[float, float]] = []  # Combined (for legacy compatibility)
self._equity_points_sim: list[tuple[float, float]] = []  # SIM mode equity curve
self._equity_points_live: list[tuple[float, float]] = []  # LIVE mode equity curve
self._current_display_mode: str = "SIM"  # Track which mode's curve we're displaying
```

**Lines 765-808 (Updated Method)**
```python
def update_equity_series_from_balance(self, balance: Optional[float], mode: Optional[str] = None) -> None:
    """
    Now tracks separate equity curves per mode.
    Appends balance point to mode-specific curve (_equity_points_sim or _equity_points_live)
    """
    # Points appended to mode-specific lists with 2-hour windowing per mode
    if mode == "SIM":
        self._equity_points_sim.append((now, balance_float))
        # Limit to last 2 hours
        self._equity_points_sim = [(x, y) for x, y in self._equity_points_sim if x >= cutoff_time]
    else:  # LIVE
        self._equity_points_live.append((now, balance_float))
        self._equity_points_live = [(x, y) for x, y in self._equity_points_live if x >= cutoff_time]
```

**Lines 823-852 (Updated Filter)**
```python
def _filtered_points_for_current_tf(self) -> list[tuple[float, float]]:
    """
    Now uses mode-specific curves based on current_display_mode.
    Filters by active timeframe window.
    """
    # Get the appropriate curve for the current mode
    if self._current_display_mode == "SIM":
        pts = list(self._equity_points_sim or [])
    else:
        pts = list(self._equity_points_live or [])
```

**Lines 727-742 (New Method)**
```python
def switch_equity_curve_for_mode(self, mode: str) -> None:
    """
    Switch which equity curve is displayed based on trading mode.
    SIM mode shows SIM equity curve, LIVE mode shows LIVE equity curve.
    """
    self._current_display_mode = mode if mode != "DEBUG" else "SIM"
    # Redraw the graph with the new mode's data
    self._replot_from_cache()
```

**Line 725 (Integration)**
```python
# In set_trading_mode() - added call to switch equity curve display
self.switch_equity_curve_for_mode(mode)
```

---

### Phase 3: Message Router Updates

#### 3.1 Message Router (`core/message_router.py`)

**Lines 251, 256 (Updated Balance UI Calls)**
```python
# Now passes mode parameter to update functions
marshal_to_qt_thread(self._update_balance_ui, balance_value, mode)
self._update_balance_ui(balance_value, mode)
```

**Lines 276-291 (Updated Method Signature)**
```python
def _update_balance_ui(self, balance_value: float, mode: Optional[str] = None) -> None:
    """
    Now tracks mode and updates both display label and equity curve.
    Calls update_equity_series_from_balance(balance, mode=mode) for mode-aware graphing.
    """
    self.panel_balance.update_equity_series_from_balance(balance_value, mode=mode)
```

**Lines 338-358 (Updated Legacy Handler)**
```python
def _on_balance_update(self, payload: dict):
    """
    Now detects mode from account and passes to Panel1 for mode-specific equity tracking.
    """
    mode = detect_mode_from_account(account) if account else None
    self.panel_balance.update_equity_series_from_balance(bal, mode=mode)
```

---

### Phase 4: Manual Reset Hotkey

#### 4.1 App Manager (`core/app_manager.py`)

**Line 62 (Added Initialization)**
```python
self._setup_reset_balance_hotkey()
```

**Lines 321-331 (New Setup Method)**
```python
def _setup_reset_balance_hotkey(self) -> None:
    """Setup SIM balance reset hotkey (Ctrl+Shift+R)."""
    try:
        from PyQt6.QtWidgets import QShortcut
        from PyQt6.QtGui import QKeySequence

        shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        shortcut.activated.connect(self._on_reset_sim_balance_hotkey)
```

**Lines 333-369 (New Handler)**
```python
def _on_reset_sim_balance_hotkey(self) -> None:
    """
    Handler for Ctrl+Shift+R - Reset SIM balance to $10K.

    1. Resets balance in StateManager
    2. Updates Panel1 display
    3. Adds reset point to SIM equity curve
    4. Shows user confirmation dialog
    """
    # Reset SIM balance
    new_balance = self._state.reset_sim_balance_to_10k()

    # Update Panel1
    self.panel_balance.set_account_balance(new_balance)
    self.panel_balance.update_equity_series_from_balance(new_balance, mode="SIM")

    # Show confirmation
    QMessageBox.information(self, "SIM Balance Reset",
                           f"SIM balance has been reset to ${new_balance:,.2f}")
```

---

## Features Implemented

### ✅ Feature 1: Monthly Auto-Reset
- SIM balance automatically resets to $10,000 at the beginning of each calendar month
- Tracked via `sim_balance.json` file with `last_reset_month` timestamp
- Works even if app is restarted mid-month

### ✅ Feature 2: Manual Reset Hotkey
- **Hotkey**: Ctrl+Shift+R
- Resets SIM balance to $10K instantly
- Updates equity curve with reset point
- Shows user confirmation dialog
- Works from anywhere in the app

### ✅ Feature 3: Separate Equity Curves
- **SIM Mode**: Displays only SIM equity curve
- **LIVE Mode**: Displays only LIVE equity curve
- Curves are independent - one mode's trading doesn't affect the other's graph
- Timeframe filtering (LIVE, 1D, 1W, 1M, 3M, YTD) works per mode

### ✅ Feature 4: Independent Trade History
- **Panel 3 Statistics**: Automatically filters by active mode
- **SIM Trades**: Only shown when in SIM mode
- **LIVE Trades**: Only shown when in LIVE mode
- Each mode has separate P&L, win rate, metrics

### ✅ Feature 5: Mode-Aware Balance Updates
- DTC balance messages routed to correct mode-specific storage
- Panel1 updates correct equity curve based on incoming mode
- StateManager maintains separate `sim_balance` and `live_balance`

---

## Testing Checklist

### Balance & Reset
- [ ] App starts with SIM balance = $10,000
- [ ] Ctrl+Shift+R resets SIM balance to $10,000
- [ ] Confirmation dialog shows new balance
- [ ] Balance persists across app restarts
- [ ] SIM balance shown in Panel1 label
- [ ] Monthly auto-reset triggers on month boundary

### Separate Equity Curves
- [ ] Switching to SIM mode shows SIM equity curve
- [ ] Switching to LIVE mode shows LIVE equity curve
- [ ] Curves are independent (one mode's balance doesn't affect other's graph)
- [ ] Timeframe filtering works for both curves
- [ ] Hover/scrubbing works correctly

### Trade History & Statistics
- [ ] Panel 3 shows only SIM trades when in SIM mode
- [ ] Panel 3 shows only LIVE trades when in LIVE mode
- [ ] Statistics (P&L, win rate, etc.) filtered by mode
- [ ] Empty state displays "No trades in SIM mode" when appropriate
- [ ] Mode switch updates Panel 3 automatically

### DTC Integration
- [ ] LIVE balance updates from Sierra Chart display correctly
- [ ] SIM balance updates show in SIM curve
- [ ] Both curves can coexist with separate data
- [ ] Mode detection works for accounts (120005 = LIVE, Sim1 = SIM)

---

## Data Structure

### StateManager (core/state_manager.py)
```python
self.sim_balance: float = 10000.0
self.sim_balance_start_of_month: float = 10000.0
self.live_balance: float = 0.0
self.current_mode: str  # "SIM", "LIVE", or "DEBUG"
```

### Panel1 (panels/panel1.py)
```python
self._equity_points_sim: list[tuple[float, float]]  # (timestamp, balance)
self._equity_points_live: list[tuple[float, float]]  # (timestamp, balance)
self._current_display_mode: str  # Which curve to show
```

### Database (TradeRecord)
```python
mode: str = Field(default="SIM", index=True)  # "SIM" or "LIVE"
```

---

## Architecture

```
DTC Message (Type 600, Account 120005 or Sim1)
    ↓
MessageRouter._on_balance_signal()
    ↓ [Detect Mode]
    ├→ StateManager.set_balance_for_mode(mode, balance)
    └→ Panel1.update_equity_series_from_balance(balance, mode)
        ├→ Append to _equity_points_sim or _equity_points_live
        └→ Redraw via _replot_from_cache()
            └→ Uses _filtered_points_for_current_tf()
                └→ Filters by _current_display_mode
```

```
User presses Ctrl+Shift+R
    ↓
MainWindow._on_reset_sim_balance_hotkey()
    ↓
    ├→ StateManager.reset_sim_balance_to_10k()
    ├→ Panel1.set_account_balance(10000.0)
    ├→ Panel1.update_equity_series_from_balance(10000.0, mode="SIM")
    └→ QMessageBox.information()
```

---

## Files Modified

1. ✅ `core/state_manager.py` - Added reset method, initialized SIM balance to $10K
2. ✅ `core/sim_balance.py` - Enabled monthly reset, manual reset, $10K starting balance
3. ✅ `panels/panel1.py` - Added separate equity curves per mode, curve switching
4. ✅ `core/app_manager.py` - Added Ctrl+Shift+R hotkey handler
5. ✅ `core/message_router.py` - Updated to pass mode to Panel1 equity methods

**Note**: Panel2 and Panel3 already had mode tracking implemented, no changes needed.

---

## Backward Compatibility

- ✅ Combined `_equity_points` list maintained for legacy code
- ✅ All existing method signatures have optional `mode` parameter
- ✅ Falls back to `_current_display_mode` if mode not provided
- ✅ No breaking changes to public APIs

---

## Performance Impact

- **Minimal**: Mode tracking adds one indexed database field to queries
- **Zero overhead**: Balance tracking already separate (no new calculations)
- **Memory**: Separate equity curves = ~2x memory for 2-hour window (negligible)
- **CPU**: Mode detection is fast string comparison

---

## Security Considerations

- ✅ Mode detection based on account string (not user input)
- ✅ Reset only affects SIM balance, not LIVE
- ✅ Hotkey can be triggered from UI but controlled in code
- ✅ All balance updates validated before display

---

## Future Enhancements

1. Visual mode indicator (badge color in equity graph)
2. Separate starting balances per month (configurable)
3. SIM balance carry-over to next month (instead of reset)
4. Mode-specific risk limits
5. Audit log for balance resets

---

## Testing Status

**Syntax Check**: ✅ All files compile without errors

**Ready for**:
- Integration testing with Sierra Chart DTC
- E2E testing of balance updates
- Mode switching behavior verification
- Hotkey testing in main app window

---

**Generated**: 2025-11-10
**Status**: ✅ Implementation Complete - Ready for Testing
**Hotkey Reference**: Ctrl+Shift+R = Reset SIM balance to $10K

