# Theme Architecture Proposal

## Concept: DEBUG as Skeleton Base

### Current Issues

- Each mode (DEBUG/SIM/LIVE) redefines ALL colors
- Stylesheet generation code duplicated 3x
- Hard to maintain consistency
- Structural values (spacing, fonts) mixed with colors

### Proposed Structure

```
┌─────────────────────────────────────────────┐
│   BASE THEME (Never Changes)               │
│   ─────────────────────────────────────    │
│   ✅ Font family, weights, sizes           │
│   ✅ Spacing (gap_sm, gap_md, gap_lg)      │
│   ✅ Widget dimensions (chip_height, etc)  │
│   ✅ Border radius                          │
│   ✅ Animation flags                        │
│   ✅ Layout constants                       │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│   COLOR PALETTES (Mode-Specific)           │
│   ─────────────────────────────────────    │
│   DEBUG:  Grey/Silver (muted development)  │
│   SIM:    White/Neon Blue (testing)        │
│   LIVE:   Black/Gold (production)          │
└─────────────────────────────────────────────┘
```

## Implementation

### Step 1: Separate Structure from Colors

```python
# BASE THEME - The skeleton (never changes across modes)
BASE_STRUCTURE = {
    # Typography - SAME for all modes
    "font_family": "Inter, Segoe UI, Arial, Helvetica, sans-serif",
    "title_font_weight": 700,
    "title_font_size": 16,
    "balance_font_weight": 800,
    "balance_font_size": 16,
    "ui_font_weight": 500,
    "ui_font_size": 16,

    # Dimensions - SAME for all modes
    "metric_cell_width": 140,
    "metric_cell_height": 52,
    "chip_height": 34,
    "pill_radius": 12,
    "pill_font_weight": 600,
    "pill_font_size": 16,

    # Spacing - SAME for all modes
    "gap_sm": 6,
    "gap_md": 10,
    "gap_lg": 16,

    # Border radius - SAME for all modes
    "card_radius": 8,

    # Visual behavior - SAME for all modes
    "ENABLE_GLOW": True,
    "ENABLE_HOVER_ANIMATIONS": True,
    "ENABLE_TOOLTIP_FADE": True,
    "TOOLTIP_AUTO_HIDE_MS": 3000,
}

# COLOR PALETTES - Only colors change per mode
MODE_COLORS = {
    "DEBUG": {
        "bg_primary": "#1E1E1E",
        "bg_secondary": "#2D2D2D",
        "bg_panel": "#1E1E1E",
        "bg_elevated": "#2D2D2D",
        "card_bg": "#2D2D2D",
        "ink": "#C0C0C0",
        "fg_primary": "#C0C0C0",
        "fg_muted": "#808080",
        "subtle_ink": "#808080",
        "border": "#404040",
        "accent": "#B0B0B0",
        "pnl_pos_color": "#A0A0A0",
        "pnl_neg_color": "#707070",
        "pnl_neu_color": "#909090",
        "pnl_pos_color_weak": "rgba(160, 160, 160, 0.35)",
        "pnl_neg_color_weak": "rgba(112, 112, 112, 0.35)",
        "pnl_neu_color_weak": "rgba(144, 144, 144, 0.35)",
    },
    "SIM": {
        "bg_primary": "#FFFFFF",
        "bg_secondary": "#F7F8FA",
        "bg_panel": "#FFFFFF",
        "bg_elevated": "#F7F8FA",
        "card_bg": "#FFFFFF",
        "ink": "#000000",
        "fg_primary": "#000000",
        "fg_muted": "#6B7280",
        "subtle_ink": "#9CA3AF",
        "border": "#00D4FF",
        "accent": "#00D4FF",
        "pnl_pos_color": "#22C55E",
        "pnl_neg_color": "#EF4444",
        "pnl_neu_color": "#6B7280",
        "pnl_pos_color_weak": "rgba(34, 197, 94, 0.35)",
        "pnl_neg_color_weak": "rgba(239, 68, 68, 0.35)",
        "pnl_neu_color_weak": "rgba(107, 114, 128, 0.35)",
    },
    "LIVE": {
        "bg_primary": "#000000",
        "bg_secondary": "#0A0A0A",
        "bg_panel": "#000000",
        "bg_elevated": "#0A0A0A",
        "card_bg": "#0A0A0A",
        "ink": "#FFD700",
        "fg_primary": "#FFD700",
        "fg_muted": "#B8860B",
        "subtle_ink": "#DAA520",
        "border": "#FFD700",
        "accent": "#FFD700",
        "pnl_pos_color": "#FFD700",
        "pnl_neg_color": "#FF4444",
        "pnl_neu_color": "#B8860B",
        "pnl_pos_color_weak": "rgba(255, 215, 0, 0.35)",
        "pnl_neg_color_weak": "rgba(255, 68, 68, 0.35)",
        "pnl_neu_color_weak": "rgba(184, 134, 11, 0.35)",
    },
}

# Active theme - merges base + colors
THEME = {**BASE_STRUCTURE, **MODE_COLORS["DEBUG"]}  # Default to DEBUG
```

### Step 2: Simplified Mode Switching

```python
def apply_trading_mode_theme(mode: str) -> None:
    """
    Apply theme based on trading mode.
    Only changes colors, structure stays the same.
    """
    global THEME
    mode = mode.upper()

    if mode not in MODE_COLORS:
        mode = "DEBUG"  # Fallback

    # Merge: base structure + mode colors
    THEME.update(MODE_COLORS[mode])

    # Apply to Qt app (single implementation, not duplicated!)
    _apply_qt_stylesheet()


def _apply_qt_stylesheet() -> None:
    """Apply theme to Qt application (shared code, no duplication!)"""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            return

        fam = THEME.get("font_family", "Segoe UI")
        w = THEME.get("ui_font_weight", 500)
        sz = THEME.get("ui_font_size", 14)

        stylesheet = f"""
            QWidget {{
                font: {w} {sz}px '{fam}';
                background-color: {THEME['bg_primary']};
                color: {THEME['ink']};
            }}
            QMainWindow {{
                background-color: {THEME['bg_primary']};
            }}
        """
        app.setStyleSheet(stylesheet)
    except Exception as e:
        print(f"Failed to apply stylesheet: {e}")
```

## Benefits

### ✅ Advantages of This Approach

1. **DRY (Don't Repeat Yourself)**
   - Stylesheet code written once, not 3 times
   - Structural values defined once

2. **Easy to Maintain**
   - Change spacing? Edit one place
   - Add new color? Update MODE_COLORS only
   - Change font size? Edit BASE_STRUCTURE once

3. **Clear Separation**
   - Structure = What doesn't change (skeleton)
   - Colors = What changes per mode (skin)

4. **Debug Mode as Foundation**
   - Develop with DEBUG mode (muted colors don't distract)
   - SIM and LIVE inherit same layout/spacing
   - Color swap is instant and clean

5. **Easier to Add New Modes**

   ```python
   MODE_COLORS["PAPER"] = {
       "bg_primary": "#F0F0F0",
       "accent": "#4CAF50",
       # ... just colors!
   }
   ```

## Usage in Your Workflow

### Development

1. Build all UI in **DEBUG mode** (grey/muted)
2. Test layouts, spacing, fonts
3. Colors are neutral, won't distract

### Testing

```python
# Switch to SIM mode
apply_trading_mode_theme("SIM")
# Same layout, just neon blue accents
```

### Production

```python
# Switch to LIVE mode
apply_trading_mode_theme("LIVE")
# Same layout, gold accents (high visibility)
```

### Hotkey Cycling

```python
# Ctrl+Shift+M cycles: DEBUG → SIM → LIVE → DEBUG
# Only colors change, layout stays consistent!
```

## Recommendations

### 1. Default to DEBUG

```python
THEME = {**BASE_STRUCTURE, **MODE_COLORS["DEBUG"]}
```

- Start app in DEBUG mode
- Development-friendly
- Neutral colors

### 2. Lock Structural Values

```python
# In BASE_STRUCTURE - these NEVER change
"gap_sm": 6,      # Don't override this in modes!
"chip_height": 34, # Don't override this in modes!
```

### 3. Document Color Roles

```python
MODE_COLORS = {
    "DEBUG": {
        # Primary surfaces
        "bg_primary": "#1E1E1E",     # Main background
        "card_bg": "#2D2D2D",         # Card surfaces

        # Text colors
        "ink": "#C0C0C0",             # Primary text
        "fg_muted": "#808080",        # Secondary text

        # Interactive
        "accent": "#B0B0B0",          # Buttons, links
        "border": "#404040",          # Dividers

        # PnL indicators
        "pnl_pos_color": "#A0A0A0",   # Positive PnL
        "pnl_neg_color": "#707070",   # Negative PnL
    },
    # ... SIM and LIVE follow same structure
}
```

## Migration Checklist

- [ ] Extract BASE_STRUCTURE from current THEME
- [ ] Create MODE_COLORS dictionary
- [ ] Refactor apply_trading_mode_theme() to merge base + colors
- [ ] Extract stylesheet generation to \_apply_qt_stylesheet()
- [ ] Test each mode transition
- [ ] Update Panel1 badge to reflect mode
- [ ] Verify all widgets use THEME values correctly

## Visual Example

```
DEBUG Mode (Development):
┌────────────────────┐
│ [DEBUG Badge]      │  ← Grey badge
│ Balance: $5,000    │  ← Silver text
│ ┌────────────────┐ │
│ │  Metric Card   │ │  ← Dark grey card
│ │  +$120         │ │  ← Light grey (muted)
│ └────────────────┘ │
└────────────────────┘

SIM Mode (Testing):
┌────────────────────┐
│ [SIM Badge]        │  ← Neon blue badge
│ Balance: $5,000    │  ← Black text
│ ┌────────────────┐ │
│ │  Metric Card   │ │  ← White card, blue border
│ │  +$120         │ │  ← Green (positive)
│ └────────────────┘ │
└────────────────────┘

LIVE Mode (Production):
┌────────────────────┐
│ [LIVE Badge]       │  ← Gold badge
│ Balance: $5,000    │  ← Gold text
│ ┌────────────────┐ │
│ │  Metric Card   │ │  ← Black card, gold border
│ │  +$120         │ │  ← Gold (positive)
│ └────────────────┘ │
└────────────────────┘
```

**Same layout, same spacing, same fonts - only colors change!**
