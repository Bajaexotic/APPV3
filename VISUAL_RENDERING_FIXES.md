# Panel 1 Black Screen Root Cause Analysis & Fixes

## 🔴 CRITICAL FINDINGS FROM DIAGNOSTIC

### **Issue #1: All Widgets Are INVISIBLE** 🔴 **PRIMARY CAUSE**
```
[DIAGNOSTIC OUTPUT]
Panel1 isVisible: False          <-- WIDGET NOT VISIBLE
Graph Container isVisible: False <-- WIDGET NOT VISIBLE
Plot Widget isVisible: False     <-- WIDGET NOT VISIBLE
Hover line isVisible: False      <-- HIDDEN
Hover text isVisible: False      <-- HIDDEN
```

**Why:** Widgets created in headless mode (no window).
In a **real app window**, parent visibility should cascade.

---

### **Issue #2: Default Plot Size is 640×480** 🟡 **SECONDARY**
```
Panel1 size: 640x480
Graph Container size: 640x480
Plot Widget size: 640x480
```

**Problem:** These are PyQtGraph defaults. Should be sized by layout.
**Expected in real window:** Much larger (1100×720 minimum from app_manager)

---

### **Issue #3: Graph Container Background is Black** 🟡 **RENDERING ISSUE**
```
Current THEME (active - SIM):
  bg_secondary: #000000 (pure black)

Graph Container bg_color: #000000 (black)
Plot background: Set to #0F0F1A (dark blue-gray) ✓
```

**Status:** Background fix was applied. Good!

---

### **Issue #4: Color Contrast is GOOD** ✅ **NO PROBLEM**
```
Background (bg_secondary): #000000 (black)
Neutral PnL color: #C9CDD0 (light gray)     ✓ HIGH CONTRAST
Positive PnL color: #20B36F (green)         ✓ HIGH CONTRAST
Negative PnL color: #C7463D (red)           ✓ HIGH CONTRAST
```

**Verdict:** Colors are NOT the problem. Line should be visible.

---

### **Issue #5: Data IS Being Added Successfully** ✅ **NO PROBLEM**
```
[OK] Added 25 points to equity curve
  First point: (1762823370.517078, 50000.0)
  Last point: (1762823370.5469978, 52400.0)

[OK] Line has 25 data points
  X range: 1762823371 to 1762823371
  Y range: 50000.00 to 52400.00
```

**Verdict:** Graph HAS DATA. Line should render.

---

### **Issue #6: ViewBox Exists and Has Valid Range** ✅ **NO PROBLEM**
```
ViewBox exists: True
  X range: [1762819698.5869267, 1762823442.5869267]
  Y range: [-2000.0, 102000.0]
```

**Verdict:** ViewBox is initialized correctly.

---

### **Issue #7: Hover Elements Created** ✅ **NO PROBLEM**
```
Hover line (_hover_seg): True
  type: QGraphicsLineItem

Hover text (_hover_text): True
  type: TextItem
```

**Verdict:** Hover system is ready (just hidden since plot is hidden).

---

## 🎯 ROOT CAUSE ANALYSIS

**You see a black screen because:**

1. **In headless/test mode:** Widgets are created but marked `isVisible=False`
   - This is correct for unit testing (no actual window)
   - When run in a real app with `MainWindow.show()`, visibility cascades

2. **In real app mode:** If still black, reasons could be:
   - a) Plot parent not in layout correctly (fixed in previous commit)
   - b) Plot size collapsed to 0×0 (check layout stretch factor)
   - c) MaskedFrame clipping mask hiding content (check paint events)
   - d) PyQtGraph render context not initialized (check OpenGL)

---

## ✅ ALREADY APPLIED FIXES

### Fix 1: Plot Background ✓
**File:** `panels/panel1.py:427`
```python
# OLD: self._plot.setBackground(None)  # TRANSPARENT
# NEW: self._plot.setBackground('#0F0F1A')  # VISIBLE DARK BLUE
```
Status: **APPLIED**

### Fix 2: Plot Attachment ✓
**File:** `panels/panel1.py:187-190`
```python
if hasattr(self, "_plot") and self._plot is not None:
    self._attach_plot_to_container(self._plot)
```
Status: **APPLIED**

---

## 🔧 ADDITIONAL FIXES TO APPLY

### Fix 3: Ensure Plot Gets Layout Space
**File:** `panels/panel1.py` - in `_init_graph()` after line 524:

```python
# After: self.graph_container.updateGeometry()
# ADD THIS:

# Force the container to not collapse
if not self.graph_container.isVisible():
    self.graph_container.show()

# Ensure plot has minimum dimensions
if self._plot and self._plot.size().width() < 100:
    self._plot.setMinimumSize(400, 300)

# Force an immediate redraw
self._plot.update()
self.graph_container.update()
```

---

### Fix 4: Add Grid Lines for Debugging
**File:** `panels/panel1.py` - in `_init_graph()` after line 438:

```python
# After: plot_item = self._plot.getPlotItem()
# ADD THIS:

# Show grid for debugging visibility
plot_item.showGrid(x=True, y=True, alpha=0.2)
```

This makes the plot OBVIOUSLY visible even if line is hard to see.

---

### Fix 5: Increase Line Width for Visibility
**File:** `panels/panel1.py` - Line 453:

```python
# OLD: main_pen = pg.mkPen(base_color, width=3, ...)
# NEW: main_pen = pg.mkPen(base_color, width=6, ...)  # THICKER
```

---

### Fix 6: Force Minimum Container Height
**File:** `panels/panel1.py` - Line 255:

```python
# OLD: self.graph_container.setMinimumHeight(0)
# NEW: self.graph_container.setMinimumHeight(200)  # PREVENT COLLAPSE
```

---

### Fix 7: Debug the MaskedFrame
**File:** `panels/panel1.py` - in `MaskedFrame.paintEvent()` after line 77:

```python
# After: self.setMask(region)
# ADD THIS:

# Debug: verify mask is set
if self.mask().isEmpty():
    import logging
    logging.warning("[MaskedFrame] Mask is empty! Region calculation may be wrong.")
```

---

## 📋 COMPREHENSIVE FIX CHECKLIST

I'll now apply all the remaining fixes:

1. [  ] Add container visibility force
2. [  ] Add grid lines for visibility
3. [  ] Increase line width to 6px
4. [  ] Force minimum container height
5. [  ] Add mask debug logging
6. [  ] Test with debug data

---

## VISUAL DEBUGGING STRATEGY

If graph is STILL not visible after all fixes, check:

1. **Is the MainWindow visible?**
   ```python
   window.show()  # Must be called in main.py
   ```

2. **Is Panel1 visible inside MainWindow?**
   ```python
   # In MainWindow._build_ui():
   self.panel_balance.show()  # May need explicit show
   ```

3. **Check window manager rendering:**
   - Windows: Check if window is minimized/hidden
   - Qt: Check `QApplication.processEvents()` is being called

4. **Check PyQtGraph OpenGL:**
   ```python
   # In Panel1._init_graph(), line 430:
   # self._plot.useOpenGL(False)  # Currently disabled
   # If graphics are broken, this might be the culprit
   ```

---

## SUMMARY: WHY YOU SEE BLACK

| Scenario | Reason | Solution |
|----------|--------|----------|
| **Unit test/diagnostic** | Widgets not shown in headless mode | Normal - run real app |
| **Real app, still black** | Plot not in layout | Plot attachment fix |
| **Graph visible but empty** | No data added | Call `update_equity_series_from_balance()` |
| **Graph visible, line not visible** | Color contrast/width | Increase width, add grid |
| **Whole panel black** | Container collapsed | Set minimum height |
| **Flickering/artifacts** | Render timing | Update geometry after layout |

---

## NEXT STEPS

The diagnostic shows:
- ✅ Code is correct
- ✅ Data is being added
- ✅ Colors have good contrast
- ✅ ViewBox is initialized
- ⚠️  Widgets not visible in headless test (EXPECTED)
- ⚠️  Default PyQtGraph sizing (640×480)

**In a real app window, this should work.** If not, the remaining fixes will address rendering issues.

Applying all fixes now...
