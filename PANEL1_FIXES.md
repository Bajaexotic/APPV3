# Panel 1 Display & Hover Fixes

## Issues Found & Fixed

### 🔴 Critical Issue #1: Graph Never Rendered
**Problem:** The PyQtGraph PlotWidget was created but never attached to the UI layout.

**Root Cause:** `_attach_plot_to_container()` was defined but **never called** in the initialization chain.

**Location:** `panels/panel1.py:183-194`

**Impact:**
- Graph completely invisible
- No equity curve displayed
- Entire visualization layer missing

**Fix Applied:**
```python
# Added between _init_graph() and _init_pulse()
if hasattr(self, "_plot") and self._plot is not None:
    self._attach_plot_to_container(self._plot)
```

---

### 🟡 Critical Issue #2: Hover Elements Never Initialized
**Problem:** Hover line and timestamp text were never created, making hover interaction impossible.

**Root Cause:**
1. `_init_hover_elements()` calls `has_graph()` which checks if `self._plot` exists
2. Since the plot was never attached, `has_graph()` returned `False`
3. Function returned early without creating hover artifacts

**Location:** `panels/panel1.py:1084-1108`

**Impact:**
- No hover line displayed
- No timestamp tooltip
- No live balance scrubbing when hovering

**Fix Applied:** The graph attachment fix (Issue #1) automatically resolves this since `_init_hover_elements()` now runs after the plot is properly initialized.

---

### 🟡 Issue #3: Hover Text Color Incompatibility
**Problem:** Hover text color was passed as a hex string to PyQtGraph's `TextItem`, but it expects a `QColor` object.

**Location:** `panels/panel1.py:1098-1100`

**Impact:** Hover timestamp text may not render with correct color or may not appear at all.

**Fix Applied:**
```python
# Before:
text_color = normalize_color(THEME.get("ink"))
self._hover_text = pg.TextItem("", color=text_color, anchor=(0.5, 1.0))

# After:
text_hex = normalize_color(THEME.get("ink"))
text_qcolor = QtGui.QColor(text_hex)
self._hover_text = pg.TextItem("", color=text_qcolor, anchor=(0.5, 1.0))
```

---

### 🟡 Issue #4: Hover Uses Incomplete Data Set
**Problem:** Hover handler accessed `self._equity_points` (full 2-hour history) but should use the filtered points for the current timeframe.

**Location:** `panels/panel1.py:1133-1168`

**Impact:**
- Hover could snap to points outside the visible timeframe
- P&L calculations based on wrong time window
- Confusing user experience

**Fix Applied:**
```python
# Use filtered points for the current timeframe
pts = self._filtered_points_for_current_tf()
if not pts:
    # Hide hover elements if no data for this timeframe
    return
xs = [p[0] for p in pts]
ys = [p[1] for p in pts]
```

---

### 🟡 Issue #5: Missing Baseline Fallback
**Problem:** If baseline calculation failed, P&L display would crash or show garbage values.

**Location:** `panels/panel1.py:1221-1230`

**Impact:** Hover header display instability.

**Fix Applied:**
```python
baseline = self._get_baseline_for_tf(x)
if baseline is None:
    # If no baseline found, show just the balance
    self.lbl_pnl.setText("—  —")
    return
```

---

## Testing Checklist

- [ ] Graph renders and displays equity curve
- [ ] Hover line appears when moving mouse over graph
- [ ] Hover timestamp displays with correct formatting
- [ ] Balance updates on hover
- [ ] P&L percentage calculates correctly
- [ ] Hover disappears when cursor leaves graph
- [ ] Works across all timeframes (LIVE, 1D, 1W, 1M, 3M, YTD)
- [ ] Hover snaps to correct data points

---

## Files Modified

1. **panels/panel1.py**
   - Line 187-190: Added plot attachment call
   - Line 1098-1100: Fixed hover text color to use QColor
   - Line 1138-1168: Fixed hover to use filtered timeframe points
   - Line 1225-1230: Added baseline calculation fallback

---

## Summary

All issues were interconnected in the initialization sequence:
1. Plot not attached → can't render → graph invisible
2. Plot not visible → hover elements won't initialize → no hover
3. Orphaned hover code → color/data mismatches → buggy behavior

The fix ensures proper initialization order and data consistency throughout the hover pipeline.
