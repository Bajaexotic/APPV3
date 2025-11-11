# Mode Selector Integration Guide

## Quick Integration (2 minutes)

### Step 1: Add to MainWindow

In your `core/app_manager.py` or wherever `MainWindow` is defined:

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # ... your existing code ...

        # ADD THIS LINE (temporary, remove when DTC auto-detection works)
        from utils.mode_selector import setup_mode_hotkey
        setup_mode_hotkey(self)

        # ... rest of your code ...
```

### Step 2: Use the Hotkey

Press **`Ctrl+Shift+M`** to cycle through modes:

```
DEBUG → SIM → LIVE → DEBUG → ...
```

The status bar will show: `"Trading Mode: DEBUG (Ctrl+Shift+M to cycle)"`

---

## Modes & Themes

### DEBUG Mode (Grey/Silver)

**Use**: Development, testing, debugging
**Theme**: Monochrome grey/silver tones

```
Background:    #1E1E1E (Dark charcoal)
Text:          #C0C0C0 (Silver)
Badge:         #6B6B6B (Medium grey)
Borders:       #404040 (Dark grey) or none
```

### SIM Mode (White/Neon Blue)

**Use**: Simulated trading, strategy testing
**Theme**: Light background with neon blue accents

```
Background:    #FFFFFF (White)
Text:          #000000 (Black)
Badge:         #00D4FF (Neon blue)
Borders:       #00D4FF 2px (Neon blue)
```

### LIVE Mode (Black/Gold)

**Use**: Real money trading (HIGH ATTENTION)
**Theme**: Black background with gold accents

```
Background:    #000000 (Pure black)
Text:          #FFD700 (Gold)
Badge:         #FFD700 (Gold, bold)
Borders:       None
```

---

## Alternative Methods

### Method 1: Environment Variable (Persistent)

```bash
export TRADING_MODE=DEBUG
python main.py
```

### Method 2: Config File (Team Settings)

```json
// config/config.json
{
  "TRADING_MODE": "DEBUG"
}
```

### Method 3: Command-Line (One-off)

```bash
python main.py --mode=DEBUG
```

---

## When to Remove

**Remove this integration** once DTC auto-detection is working:

1. Delete the import line:

   ```python
   # DELETE THIS
   from utils.mode_selector import setup_mode_hotkey
   setup_mode_hotkey(self)
   ```

2. Delete the file:

   ```bash
   rm utils/mode_selector.py
   ```

3. Mode will be set automatically from DTC `LogonResponse`:

   ```python
   # In dtc_json_client.py (will be implemented)
   def on_logon_response(self, msg):
       is_sim = msg.get("IsSimulatedAccount", 0) == 1
       settings.TRADING_MODE = "SIM" if is_sim else "LIVE"
   ```

---

## Testing the Integration

```python
# Test file
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from utils.mode_selector import setup_mode_hotkey

    app = QApplication([])
    window = QMainWindow()
    window.setWindowTitle("Mode Selector Test")

    # Setup hotkey
    setup_mode_hotkey(window)

    window.statusBar().showMessage("Press Ctrl+Shift+M to cycle modes")
    window.show()

    app.exec()
```

---

## Debug Subsystem Integration

Mode changes are automatically logged:

```json
{
  "timestamp": "2025-11-06T12:00:00.000Z",
  "category": "ui",
  "level": "info",
  "message": "Trading mode switched: DEBUG → SIM",
  "context": {
    "new_mode": "SIM",
    "previous_mode": "DEBUG",
    "method": "hotkey",
    "hotkey": "Ctrl+Shift+M"
  }
}
```

View logs in the Debug Console (`Ctrl+Shift+D`).

---

## FAQ

**Q: Can I have both hotkey and command-line?**
A: Yes, command-line overrides the hotkey's starting value.

**Q: Does it persist between restarts?**
A: No, use environment variable or config file for persistence.

**Q: What happens in LIVE mode?**
A: Same functionality, but visual theme changes to gold/black for high visibility.

**Q: Can I customize the hotkey?**
A: Yes, edit `utils/mode_selector.py` line 81:

```python
shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), window)  # Change here
```

---

## Summary

1. ✅ Add one line to `MainWindow.__init__`
2. ✅ Use `Ctrl+Shift+M` to cycle modes
3. ✅ Status bar shows current mode
4. ✅ All changes logged to debug subsystem
5. ✅ Easy to remove when DTC auto-detection is ready

**That's it!** 🎉
