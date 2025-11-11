# REAL ISSUES FOUND - NOT GUESSING

Based on actual code analysis, here are the REAL problems:

---

## ISSUE #1: Panel 1 Balance Doesn't Update

**Problem**: When you close a trade, balance doesn't change in Panel 1

**Root Cause**: `StateManager` doesn't emit a `balanceChanged` signal

**Evidence**:
```bash
$ grep -r "balanceChanged" core/state_manager.py
No matches found
```

**How it should work**:
```python
# In StateManager:
balanceChanged = QtCore.pyqtSignal(float)  # Missing!

def set_balance_for_mode(self, mode: str, new_balance: float):
    if mode == "SIM":
        self.sim_balance = new_balance
        self.balanceChanged.emit(new_balance)  # Missing!
```

**How to fix**:
1. Add `balanceChanged` signal to StateManager
2. Emit it in `set_balance_for_mode()`
3. Connect it in Panel 1 to update display

**Impact**: HIGH - This is why balance never changes

---

## ISSUE #2: Panel 3 Doesn't Update When Trades Close

**Problem**: Statistics panel doesn't refresh when a trade closes

**Root Cause**: Panel 3 needs to respond to `tradesChanged` signal AND actually update its UI elements

**Evidence**:
```bash
$ grep -r "tradesChanged" panels/panel3.py
No matches found
```

App manager tries to wire it on line 241:
```python
self.panel_live.tradesChanged.connect(_on_trade_changed)
```

But Panel 3 doesn't have a way to UPDATE its displayed metrics.

**How it should work**:
```python
# In Panel 3:
def on_trade_closed(self, trade_data):
    """Called when Panel 2 closes a trade."""
    # Refresh the metrics grid with new data
    self._load_metrics_for_timeframe(self._tf)

    # Update grid display
    self.metric_grid.update()
    self.update()
```

**How to fix**:
1. Add method to Panel 3 that refreshes metrics
2. Connect Panel 2's `tradesChanged` signal to this method
3. Make sure metric_grid actually displays the data

**Impact**: HIGH - This is why Panel 3 never shows statistics

---

## ISSUE #3: Graph Not Visible in Panel 1

**Problem**: Price chart/graph doesn't display in Panel 1

**Probable Causes** (need to verify):
1. PlotWidget created but not added to layout
2. PlotWidget created but set to hidden
3. PlotWidget created but no data fed to it
4. PlotWidget created but sizing issue (0px width/height)

**How to debug**:
1. Check if `plot_widget.show()` is called
2. Check if `plot_widget` is added to a visible layout
3. Check if data is being plotted to the widget
4. Check if parent widget is visible

**How to fix**:
Depends on what's causing it - need to run actual app and inspect:
```python
# Add to Panel 1.__init__:
print(f"Plot widget visible: {self.plot_widget.isVisible()}")
print(f"Plot widget size: {self.plot_widget.width()} x {self.plot_widget.height()}")
print(f"Plot widget parent: {self.plot_widget.parent()}")
```

**Impact**: MEDIUM - Graph is nice-to-have but not critical for trading

---

## QUICK FIXES PRIORITY

### HIGH PRIORITY (Stop losing data, show stats):
1. Add `balanceChanged` signal to StateManager → Panel 1 displays balance
2. Wire Panel 3 to update on trades → Stats panel refreshes

### MEDIUM PRIORITY (Nice to have):
3. Fix graph visibility → Chart displays

---

## Next Steps

1. **Fix balance signal** - 5 minute fix
2. **Fix Panel 3 refresh** - 10 minute fix
3. **Test in app** - 5 minutes
4. Then we can debug the graph issue if needed

Would you like me to make these fixes?
