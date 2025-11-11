# Panel 1 Blank Screen Diagnosis & Solutions

## The Problem: You See Only Black Background

### Why This Happens (Multiple Possible Causes)

#### **Issue 1: Plot Background is Transparent** 🔴 **LIKELY CULPRIT**
**Location:** `panels/panel1.py:426`
```python
self._plot.setBackground(None)  # ← TRANSPARENT BACKGROUND
self._plot.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
self._plot.setStyleSheet("background: transparent; border: none;")
```

**Problem:** The graph background is set to **transparent** and blends into the black panel background (which is also black):
- Plot background: `transparent`
- Panel background: `#000000` (pure black)
- Axes hidden: `plot_item.hideAxis("left")` + `hideAxis("bottom")`
- Result: **Invisible plot because there's nothing to see against the black background**

---

#### **Issue 2: Line Color Might Be Black/Dark** 🟡 **POSSIBLE**
**Location:** `panels/panel1.py:452`
```python
base_color = QtGui.QColor(ColorTheme.pnl_color_from_direction(getattr(self, "_pnl_up", None)))
main_pen = pg.mkPen(base_color, width=3, join="round", cap="round")
```

**Problem:**
- If `_pnl_up` is `None` (no P&L data), the color defaults to neutral:
  - `pnl_neu_color = "#C9CDD0"` (light gray) — should be visible
  - But if theme is wrong, could be dark

**In LIVE mode:**
- `ink = "#FFD700"` (gold) — line would be gold, should be visible
- But what if mode switching isn't working?

---

#### **Issue 3: No Data in Graph** 🟡 **VERY LIKELY**
**Location:** `panels/panel1.py:454-455`
```python
self._line = self._plot.plot([], [], pen=main_pen, antialias=True)  # ← EMPTY DATA!
```

**Problem:**
- Graph initialized with **empty data arrays** `[], []`
- Even if line is visible, there are no points to display
- Equity curve only appears when you call `update_equity_series_from_balance()`
- **If app never calls this function, the graph stays empty**

---

#### **Issue 4: Graph Not Getting Enough Screen Space** 🟡 **POSSIBLE**
**Location:** `panels/panel1.py:251-260`
```python
self.graph_container.setMinimumHeight(0)  # ← Can shrink to 0!
self.graph_container.setMinimumWidth(0)
```

**Problem:**
- Container might collapse if window is small or layout is broken
- Check your window size: must be at least 1100×720 (from `app_manager.py:74`)

---

#### **Issue 5: PyQtGraph Configuration Issue** 🟡 **LESS LIKELY**
**Location:** `panels/panel1.py:424`
```python
pg.setConfigOptions(antialias=True)
```

**Problem:**
- If PyQtGraph global settings are wrong, plot might not render
- But we tested this and it works

---

## Visual Diagnosis Checklist

### Option 1: Test if Graph is Actually Empty
```python
from panels.panel1 import Panel1
panel = Panel1()

# Check if data exists
print("Data in graph:", panel._equity_points)
print("Filtered data:", panel._filtered_points_for_current_tf())
print("Line has data:", panel._line.getData() if panel._line else "No line")
```

**Expected:** Lists should be empty `[]`

**What to do:** If empty, you need to ADD DATA:
```python
panel.update_equity_series_from_balance(50000.0, 'SIM')
panel.update_equity_series_from_balance(50100.0, 'SIM')
panel.update_equity_series_from_balance(50200.0, 'SIM')
```

---

### Option 2: Test if Colors Are Correct
```python
from config.theme import THEME
print("Panel background:", THEME.get("bg_panel"))
print("Graph secondary bg:", THEME.get("bg_secondary"))
print("Ink color:", THEME.get("ink"))
print("Neutral PnL color:", THEME.get("pnl_neu_color"))
```

**Expected in DEBUG mode:**
```
Panel background: #000000 (black)
Graph secondary bg: #000000 (black)
Ink color: #C0C0C0 (silver gray)
Neutral PnL color: #C9CDD0 (light gray)
```

**If all black:** Graph line will be invisible!

---

### Option 3: Test Graph Visibility
```python
from PyQt6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
from panels.panel1 import Panel1

panel = Panel1()

# Check sizes
print(f"Panel1 visible: {panel.isVisible()}")
print(f"Panel1 size: {panel.size()}")
print(f"Graph container visible: {panel.graph_container.isVisible()}")
print(f"Graph container size: {panel.graph_container.size()}")
print(f"Plot visible: {panel._plot.isVisible()}")
print(f"Plot size: {panel._plot.size()}")
```

**Expected:**
```
Panel1 visible: True
Panel1 size: PyQt6.QtCore.QSize(1100, 720)
Graph container visible: True
Graph container size: PyQt6.QtCore.QSize(some width > 0, some height > 0)
Plot visible: True
Plot size: (non-zero dimensions)
```

**If any is False or size is 0:** Layout issue!

---

## Solutions (In Order of Likelihood)

### **FIX #1: Add Test Data to Graph** ⭐ **TRY THIS FIRST**
The graph might be working but just empty!

Edit `panels/panel1.py` to add test data in `__init__`:

```python
# At end of __init__, after all initialization:
# Add test data to show the graph is working
import time
for i in range(20):
    self.update_equity_series_from_balance(50000.0 + (i * 50), 'SIM')
```

**Result:** You should see a diagonal line going up!

---

### **FIX #2: Change Plot Background to Visible** ⭐ **TRY THIS SECOND**

Edit `panels/panel1.py` line 426:

**Before:**
```python
self._plot.setBackground(None)
```

**After (Option A - Light background):**
```python
self._plot.setBackground('#1A1A2E')  # Very dark blue-gray, good contrast
```

**After (Option B - Auto background):**
```python
bg_color = THEME.get("bg_secondary", "#000000")
if bg_color == "#000000":
    self._plot.setBackground('#1A1A2E')  # Override pure black
else:
    self._plot.setBackground(bg_color)
```

---

### **FIX #3: Force Line Color to Be Visible**

Edit `panels/panel1.py` line 452:

**Before:**
```python
base_color = QtGui.QColor(ColorTheme.pnl_color_from_direction(getattr(self, "_pnl_up", None)))
```

**After (Force gray if neutral):**
```python
pnl_up = getattr(self, "_pnl_up", None)
if pnl_up is None:
    base_color = QtGui.QColor("#C9CDD0")  # Force light gray if no data
else:
    base_color = QtGui.QColor(ColorTheme.pnl_color_from_direction(pnl_up))
```

---

### **FIX #4: Increase Line Width for Visibility**

Edit `panels/panel1.py` line 453:

**Before:**
```python
main_pen = pg.mkPen(base_color, width=3, join="round", cap="round")
```

**After:**
```python
main_pen = pg.mkPen(base_color, width=5, join="round", cap="round")  # Thicker line
```

---

### **FIX #5: Force Graph Container to Be Visible**

Edit `panels/panel1.py` line 248-253:

**Add this debugging code:**
```python
# --- Graph container (MaskedFrame handles its own paint) ---
self.graph_container = MaskedFrame()
self.graph_container.setMinimumHeight(100)  # Force minimum height!
self.graph_container.setMinimumWidth(100)   # Force minimum width!
```

---

### **FIX #6: Show Grid Lines (Easy Debug)**

Edit `panels/panel1.py` after line 438:

```python
# plot item / viewbox
plot_item = self._plot.getPlotItem()
plot_item.showGrid(x=True, y=True, alpha=0.2)  # Add this line
plot_item.hideAxis("left")
plot_item.hideAxis("bottom")
```

**Result:** Grid lines will make it obvious if plot is rendering!

---

## The Most Likely Culprit & Quick Fix

**MOST LIKELY:** You need to add data to the graph + make the background visible.

### Quick 5-Line Fix:

```python
# In panels/panel1.py, in _init_graph() after line 532:

# Make graph background visible
self._plot.setBackground('#1A1A2E')

# Add test data so there's something to see
import time
now = time.time()
for i in range(20):
    balance = 50000.0 + (i * 100)
    self._equity_points_sim.append((now + i, balance))

# Redraw with test data
self._replot_from_cache()
```

---

## How to Debug Visually

1. **Run the app with `DEBUG_DTC=1` flag:**
   ```bash
   DEBUG_DTC=1 python main.py
   ```
   This will print initialization logs showing if graph is created.

2. **Add print statements to see what's happening:**
   ```python
   # In _init_graph() after plot creation:
   print(f"Plot background: {self._plot.getBackground()}")
   print(f"Plot size: {self._plot.size()}")
   print(f"Plot visible: {self._plot.isVisible()}")
   ```

3. **Check browser developer tools (if web-based):**
   - Not applicable here since it's Qt desktop app

4. **Use Qt Designer to inspect layout:**
   - Right-click on window → "Inspect"
   - Check if graph container has non-zero size

---

## Summary: What Likely Happened

| Symptom | Cause | Fix |
|---------|-------|-----|
| Black screen | Plot background is transparent, blending into black panel | Change background to `#1A1A2E` |
| No data visible | Graph initialized empty, no balance data added | Call `update_equity_series_from_balance()` |
| Graph too small | Container minimum height set to 0 | Set to `100+` |
| Line color wrong | P&L state is None, color might be dark | Force neutral color |
| Line too thin | Width set to 3px | Increase to 5-8px |

---

**Recommendation:** Try **FIX #1 + FIX #2** together—they'll almost certainly fix the issue!
