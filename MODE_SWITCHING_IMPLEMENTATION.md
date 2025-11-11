# Trading Mode Switching Implementation

## Overview

The trading mode switching system allows you to cycle between DEBUG, SIM, and LIVE modes using **Ctrl+Shift+M**. Each mode has distinct visual themes and the badge in Panel 1 updates accordingly.

---

## ✅ Implementation Complete

### Files Modified

1. **panels/panel1.py**
   - Added `set_trading_mode(mode)` method (lines 609-655)
   - Updates badge text and neon glow for DEBUG/SIM/LIVE
   - Badge colors:
     - DEBUG: Grey (#808080)
     - SIM: Neon Blue (#00D4FF)
     - LIVE: Gold (#FFD700)

2. **config/theme.py**
   - Added `apply_trading_mode_theme(mode)` function (lines 184-304)
   - Three complete theme definitions:
     - **DEBUG**: Grey/silver monochrome
     - **SIM**: White with neon blue accents
     - **LIVE**: Black with gold accents

3. **utils/mode_selector.py**
   - Updated `cycle_mode()` function (lines 46-110)
   - Now calls `panel1.set_trading_mode(new_mode)`
   - Applies theme via `apply_trading_mode_theme(new_mode)`
   - Forces UI refresh after mode change
   - Shows descriptive status bar messages

4. **core/app_manager.py**
   - Integrated `setup_mode_hotkey(self)` (lines 238-245)
   - Hotkey is now automatically enabled on app startup

---

## Usage

### In the Application

```bash
python main.py
```

Then press **Ctrl+Shift+M** to cycle modes:

```
DEBUG → SIM → LIVE → DEBUG → ...
```

### What Happens

1. **Badge Updates**: The badge in Panel 1 changes:
   - Text changes: "DEBUG" / "SIM" / "LIVE"
   - Neon glow color changes
   - Border color changes

2. **Theme Changes**: The entire application theme updates:
   - Background colors change
   - Text colors change
   - Border colors change
   - Accent colors change

3. **Status Bar**: Shows current mode with description:
   - "Development Mode (Grey/Silver)"
   - "Simulation Mode (White/Neon Blue)"
   - "Live Trading Mode (Black/Gold)"

---

## Theme Specifications

### DEBUG Mode (Grey/Silver Monochrome)

**Purpose**: Development and testing environment

**Colors**:

- Background: `#1E1E1E` (Dark charcoal)
- Secondary Background: `#2D2D2D` (Medium grey)
- Text: `#C0C0C0` (Silver)
- Borders: `#404040` (Dark grey)
- Accent: `#B0B0B0` (Light grey)
- Badge Neon: `#808080` (Grey)

**Characteristics**:

- All grey and silver tones
- No bright colors
- Clean, minimal look
- Suitable for long development sessions

---

### SIM Mode (White/Neon Blue)

**Purpose**: Simulated trading environment

**Colors**:

- Background: `#FFFFFF` (Pure white)
- Secondary Background: `#F7F8FA` (Light grey)
- Text: `#000000` (Black)
- Borders: `#00D4FF` (Neon blue)
- Accent: `#00D4FF` (Neon blue)
- Badge Neon: `#00D4FF` (Neon blue)

**Characteristics**:

- High contrast white background
- Neon blue accents for visibility
- 2px neon blue borders on cells
- PnL colors: Green/Red (standard)

---

### LIVE Mode (Black/Gold)

**Purpose**: Real money trading (high attention)

**Colors**:

- Background: `#000000` (Pure black)
- Secondary Background: `#0A0A0A` (Near black)
- Text: `#FFD700` (Gold)
- Borders: `#FFD700` (Gold)
- Accent: `#FFD700` (Gold)
- Badge Neon: `#FFD700` (Gold)

**Characteristics**:

- Pure black background for focus
- Gold text and accents for luxury/importance feel
- Positive PnL: Gold
- Negative PnL: Red

---

## Code Architecture

### Panel 1 Badge Update

```python
# panels/panel1.py (line 609)
def set_trading_mode(self, mode: str) -> None:
    """Update badge display for DEBUG/SIM/LIVE modes"""
    mode = mode.upper()

    # Set badge text
    self.mode_badge.setText(mode)

    # Set colors based on mode
    if mode == "DEBUG":
        neon_color = "#808080"  # Grey
        text_color = "#FFFFFF"
    elif mode == "SIM":
        neon_color = "#00D4FF"  # Neon blue
        text_color = "#000000"
    else:  # LIVE
        neon_color = "#FFD700"  # Gold
        text_color = "#000000"

    # Apply styles and glow effect
    # ... (full implementation in file)
```

### Theme Application

```python
# config/theme.py (line 184)
def apply_trading_mode_theme(mode: str) -> None:
    """Apply theme based on trading mode"""
    global THEME

    if mode == "DEBUG":
        THEME.update({
            "bg_primary": "#1E1E1E",
            "ink": "#C0C0C0",
            # ... full theme
        })
    elif mode == "SIM":
        THEME.update({
            "bg_primary": "#FFFFFF",
            "ink": "#000000",
            "border": "#00D4FF",
            # ... full theme
        })
    else:  # LIVE
        THEME.update({
            "bg_primary": "#000000",
            "ink": "#FFD700",
            # ... full theme
        })

    # Apply stylesheet to QApplication
    # ... (full implementation in file)
```

### Mode Cycling Hotkey

```python
# utils/mode_selector.py (line 46)
def cycle_mode():
    """Cycle through modes and update UI"""
    MODE_ORDER = ["DEBUG", "SIM", "LIVE"]

    # Calculate next mode
    next_index = (current_index + 1) % len(MODE_ORDER)
    new_mode = MODE_ORDER[next_index]

    # Update settings
    settings.TRADING_MODE = new_mode

    # Update badge
    panel1.set_trading_mode(new_mode)

    # Apply theme
    apply_trading_mode_theme(new_mode)

    # Refresh UI
    window.update()
```

---

## Testing Instructions

### Manual Testing Steps

1. **Start the application**:

   ```bash
   python main.py
   ```

2. **Verify initial state**:
   - Check the badge in Panel 1 (top panel)
   - Should show current mode (likely SIM by default)
   - Note the neon glow around the badge

3. **Test mode cycling**:
   - Press **Ctrl+Shift+M**
   - Badge should change: SIM → LIVE
   - Entire app theme should change to black/gold
   - Status bar should show: "Live Trading Mode (Black/Gold)"

4. **Continue cycling**:
   - Press **Ctrl+Shift+M** again
   - Badge should change: LIVE → DEBUG
   - Theme should change to grey/silver
   - Status bar should show: "Development Mode (Grey/Silver)"

5. **Complete the cycle**:
   - Press **Ctrl+Shift+M** again
   - Badge should change: DEBUG → SIM
   - Theme should change to white/neon blue
   - Status bar should show: "Simulation Mode (White/Neon Blue)"

### Expected Behavior

✅ **Badge updates**:

- Text changes immediately
- Neon glow color changes
- Border color matches neon

✅ **Theme changes**:

- Background color changes throughout app
- Text color changes (silver/black/gold)
- Border colors change
- All panels update simultaneously

✅ **Status bar**:

- Shows descriptive mode name
- Message persists for 5 seconds

✅ **Terminal output** (DEBUG mode only):

- In DEBUG mode: Terminal shows diagnostic output
- In SIM/LIVE modes: Terminal is clean (no debug output)

---

## Terminal Output Behavior

The terminal output behavior is controlled by the TRADING_MODE setting:

### DEBUG Mode

```
[Logger] Initialized (INFO) → logs/app.log
[Logger] Console output enabled (TRADING_MODE=DEBUG)
[SETTINGS] MODE=DEBUG | DTC=127.0.0.1:11099 | ...
[NETWORK] INFO: Connection established
[DATA] DEBUG: Processing message
```

### SIM/LIVE Modes

```
(clean terminal - no debug output)
```

All events are still logged to `logs/app.log` in all modes. Only console output is conditional.

---

## Environment Variable Override

You can set the initial mode via environment variable:

```bash
# Windows Command Prompt
set TRADING_MODE=DEBUG
python main.py

# Windows PowerShell
$env:TRADING_MODE="DEBUG"
python main.py

# Linux/Mac
export TRADING_MODE=DEBUG
python main.py
```

---

## Config File Override

Edit `config/config.json`:

```json
{
  "TRADING_MODE": "DEBUG"
}
```

---

## Future: DTC Auto-Detection

**Note**: The hotkey method is temporary. Once DTC auto-detection is implemented, the mode will be automatically set based on the `LogonResponse` message from Sierra Chart.

When that's ready:

1. Remove `setup_mode_hotkey()` call from `app_manager.py`
2. Delete `utils/mode_selector.py`
3. Implement DTC message handler to call `set_trading_mode()` and `apply_trading_mode_theme()`

---

## Implementation Checklist

✅ Badge colors defined (grey/neon blue/gold)
✅ Theme definitions created (3 complete themes)
✅ Badge update method added to Panel1
✅ Theme application function added
✅ Mode cycling hotkey implemented
✅ Integrated into MainWindow startup
✅ Status bar notifications added
✅ UI refresh logic added
✅ Documentation created

---

## Summary

The trading mode switching system is **fully implemented and ready to test**. The badge in Panel 1 will update with appropriate colors and neon glows, the entire application theme will change, and terminal output will be conditional on DEBUG mode.

Press **Ctrl+Shift+M** in the running application to cycle through modes and watch the magic happen! ✨
