# APPSIERRA Theme System Update

**Date:** 2025-11-09
**Status:** Complete
**Branch:** claude/upload-entire-file-011CUvy9JC1QTE42F7nntMSa
**Commit:** 93114db

---

## Summary

Updated the theme system from generic dark/light themes to custom DEBUG/SIM/LIVE themes that match the application's trading mode system.

---

## Changes Made

### 1. core/app_manager.py

**Purpose:** Main application window orchestration

**Updates:**

- `themeChanged` signal now emits `"DEBUG" | "SIM" | "LIVE"`
- Default theme changed from `"dark"` to `"LIVE"`
- `_setup_theme()` now uses `switch_theme()` instead of `set_theme()`
- `_setup_theme_toolbar()` creates DEBUG/SIM/LIVE buttons (instead of Dark/Light)
- `_set_theme_mode(mode)` accepts `"DEBUG"`, `"SIM"`, or `"LIVE"`
- `on_theme_changed(mode)` handles DEBUG/SIM/LIVE modes

**Lines Changed:** 75-434

### 2. widgets/dev_toolbar.py

**Purpose:** Developer toolbar with theme toggle

**Updates:**

- `_toggle_theme()` now cycles: DEBUG -> SIM -> LIVE -> DEBUG
- Uses `current_theme_mode` instead of `_theme_mode`
- Calls `_set_theme_mode()` if available

**Lines Changed:** 45-57

### 3. tools/theme_sandbox.py

**Purpose:** Theme testing sandbox

**Updates:**

- Replaced two buttons (Dark/Light) with three (DEBUG/SIM/LIVE)
- Changed import from `set_theme` to `switch_theme`
- `apply_mode()` uses `switch_theme(mode.lower())`
- Default theme changed from "dark" to "LIVE"

**Lines Changed:** 7-95

### 4. core/message_router.py

**Purpose:** DTC message routing

**Updates:**

- Updated comment from "LIVE=dark, SIM=light" to "DEBUG/SIM/LIVE themes"

**Lines Changed:** 99

### 5. demo_theme_switching.py (NEW)

**Purpose:** Demonstration script for theme switching

**Features:**

- Shows all three theme definitions
- Demonstrates theme cycling behavior
- Validates hotkey support
- Provides visual confirmation of theme switching

---

## Theme Definitions

### DEBUG Theme

- **Purpose:** Grey/silver monochrome for development
- **Background:** #2A2A2A (Dark charcoal)
- **Foreground:** #E0E0E0 (Light silver)
- **Accent:** #A0A0A0 (Medium grey)
- **Use Case:** Development and debugging

### SIM Theme

- **Purpose:** White/neon blue for simulation trading
- **Background:** #FFFFFF (White)
- **Foreground:** #1A1A1A (Near black)
- **Accent:** #00D9FF (Bright cyan)
- **Use Case:** Simulation/paper trading

### LIVE Theme

- **Purpose:** Black/gold for real trading
- **Background:** #0A0A0A (Near black)
- **Foreground:** #E8E8E8 (Off-white)
- **Accent:** #FFD700 (Gold)
- **Use Case:** Live/real trading

---

## Theme Switching Methods

### Method 1: Hotkey (Ctrl+Shift+M)

Already implemented in `utils/mode_selector.py`:

- Cycles: DEBUG -> SIM -> LIVE -> DEBUG
- Updates Panel 1 badge, theme, and pill colors
- Calls `apply_trading_mode_theme(mode)`

### Method 2: Theme Toolbar (ENV-gated)

Implemented in `core/app_manager.py`:

- Shows three buttons: DEBUG, SIM, LIVE
- Calls `_set_theme_mode(mode)` when clicked
- Emits `themeChanged` signal

### Method 3: DevToolbar Button

Implemented in `widgets/dev_toolbar.py`:

- Single "Theme" button cycles through modes
- Calls `_set_theme_mode(mode)` on main window

### Method 4: Theme Sandbox

Implemented in `tools/theme_sandbox.py`:

- Three separate buttons for each theme
- Useful for testing theme visuals

---

## Testing the Theme System

### On Windows (Your Platform)

1. **Run the application:**

   ```cmd
   cd C:\Users\cgrah\Desktop\APPSIERRA
   python main.py
   ```

2. **Test hotkey:**
   - Press `Ctrl+Shift+M` to cycle through themes
   - Observe visual changes in background, text colors, and badges

3. **Test toolbar buttons:**
   - Click DEBUG/SIM/LIVE buttons (if toolbar visible)
   - Verify theme switches correctly

4. **Test theme sandbox:**

   ```cmd
   python -m tools.theme_sandbox
   ```

   - Click DEBUG/SIM/LIVE buttons
   - Observe theme changes in sample cards

5. **Run demonstration:**

   ```cmd
   python demo_theme_switching.py
   ```

   - Shows theme definitions and cycling behavior

---

## Validation

### Syntax Check

All files compile successfully:

```bash
python -m py_compile core/app_manager.py
python -m py_compile widgets/dev_toolbar.py
python -m py_compile tools/theme_sandbox.py
python -m py_compile core/message_router.py
```

### No Errors

All Python syntax is valid with no compilation errors.

### Backward Compatibility

The `set_theme()` function in `config/theme.py` remains for backward compatibility:

- Maps "dark" -> "live"
- Maps "light" -> "sim"

---

## Integration Points

### Existing Code

These components already support DEBUG/SIM/LIVE themes:

- `config/theme.py`: Defines DEBUG_THEME, SIM_THEME, LIVE_THEME
- `config/theme.py`: `switch_theme(mode)` function
- `config/theme.py`: `apply_trading_mode_theme(mode)` wrapper
- `utils/mode_selector.py`: Ctrl+Shift+M hotkey
- `panels/panel1.py`: Uses ThemeAwareMixin
- `panels/panel2.py`: Uses ThemeAwareMixin
- `panels/panel3.py`: Uses ThemeAwareMixin

### Updated Code

These components now use DEBUG/SIM/LIVE instead of dark/light:

- `core/app_manager.py`: Theme switching orchestration
- `widgets/dev_toolbar.py`: Theme toggle button
- `tools/theme_sandbox.py`: Theme testing sandbox

---

## What This Fixes

### Before

- Generic dark/light themes that didn't match trading modes
- Confusion between theme modes and trading modes
- Inconsistent theme switching behavior

### After

- Custom DEBUG/SIM/LIVE themes that match trading modes
- Clear distinction between development, simulation, and live trading
- Consistent theme switching across all UI components

---

## Next Steps

1. Test theme switching on Windows with PyQt6
2. Verify visual appearance of all three themes
3. Confirm hotkey (Ctrl+Shift+M) works correctly
4. Test theme persistence across sessions (if implemented)
5. Update tests to verify theme switching (optional)

---

## Files Changed

| File                    | Lines Changed | Type     |
| ----------------------- | ------------- | -------- |
| core/app_manager.py     | ~180          | Modified |
| widgets/dev_toolbar.py  | 13            | Modified |
| tools/theme_sandbox.py  | 28            | Modified |
| core/message_router.py  | 1             | Modified |
| demo_theme_switching.py | 93            | New      |

**Total:** 5 files, ~315 lines

---

## Commit Details

```
commit 93114db
Author: Claude
Date: 2025-11-09

refactor: Update theme system from dark/light to DEBUG/SIM/LIVE

Replace generic dark/light theme switching with custom DEBUG/SIM/LIVE themes
to match the application's trading mode theming system.
```

---

**Status:** Ready for testing on Windows with PyQt6
**Branch:** claude/upload-entire-file-011CUvy9JC1QTE42F7nntMSa
**Remote:** Pushed successfully
