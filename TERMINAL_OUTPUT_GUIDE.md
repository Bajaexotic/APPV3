# Terminal Output Behavior by Trading Mode

## Summary

Terminal output is now **conditional based on TRADING_MODE**:

| Trading Mode | Terminal Output | File Logging | UI Console |
| ------------ | --------------- | ------------ | ---------- |
| **DEBUG**    | ✅ Verbose      | ✅ Enabled   | ✅ Enabled |
| **SIM**      | ❌ Clean/Silent | ✅ Enabled   | ✅ Enabled |
| **LIVE**     | ❌ Clean/Silent | ✅ Enabled   | ✅ Enabled |

---

## What Changed

### Before

```
# All modes showed terminal output
[2025-11-06 12:00:00] [INFO] [diagnostics] Event logged
[NETWORK] INFO: Connection established (dtc_client.connect:145)
[DATA] DEBUG: Processing message (dtc_client._rx_loop:356)
...endless debug messages...
```

### After

**DEBUG Mode:**

```
[Logger] Initialized (INFO) → logs/app.log
[Logger] Console output enabled (TRADING_MODE=DEBUG)
[SETTINGS] MODE=DEBUG | DTC=127.0.0.1:11099 | ...
[2025-11-06 12:00:00] [INFO] [diagnostics] Event logged
[NETWORK] INFO: Connection established
[DATA] DEBUG: Processing message
```

**SIM Mode:**

```
(clean terminal - no debug output)
```

**LIVE Mode:**

```
(clean terminal - no debug output)
```

---

## Modified Files

### 1. core/diagnostics.py

**Change:** Console handler only outputs in DEBUG mode

```python
def _console_handler(self, event: DiagnosticEvent):
    """
    Only outputs to terminal when TRADING_MODE == "DEBUG".
    In LIVE/SIM modes, terminal is kept clean and quiet.
    Events are still logged to file and UI console in all modes.
    """
    # Check if we should output to console
    if _SETTINGS_AVAILABLE and settings:
        if getattr(settings, 'TRADING_MODE', 'DEBUG') != 'DEBUG':
            return  # Silent in LIVE/SIM modes

    # ... console output code ...
```

### 2. utils/logger.py

**Change:** Console handler only added in DEBUG mode

```python
# Console handler - only in DEBUG trading mode
if TRADING_MODE == "DEBUG":
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

# File handler always added (all modes)
root_logger.addHandler(file_handler)
```

### 3. config/settings.py

**Change:** Boot banner only prints in DEBUG mode

```python
# Only show in DEBUG trading mode to keep LIVE/SIM terminal clean
if DEBUG_MODE and TRADING_MODE == "DEBUG":
    print("[SETTINGS] MODE=DEBUG | DTC=... | ...")
```

---

## Why This Matters

### Production/Trading Environments

**LIVE Mode** (Real Money):

- Clean terminal prevents information overload
- Focus on critical alerts only
- Professional appearance
- Reduces stress during trading

**SIM Mode** (Testing):

- Clean terminal for strategy observation
- Easier to spot important messages
- Less distraction during backtesting

### Development Environment

**DEBUG Mode** (Development):

- Verbose output for debugging
- Color-coded events
- Immediate feedback
- Full visibility into system behavior

---

## Where Events Still Go

Even in LIVE/SIM modes, all events are captured:

### 1. File Logs (Always)

```
logs/app.log  (rotating, 1MB max, 3 backups)
```

View with:

```bash
tail -f logs/app.log
```

### 2. Debug UI Console (Always)

```
Press Ctrl+Shift+D in the application
```

Features:

- Live event stream
- Filter by category/level
- Search and export
- System statistics

### 3. Session Export (Always)

```python
hub = DiagnosticsHub.get_instance()
hub.export_json("logs/session_dump.json")
```

---

## Testing

Run the test script:

```bash
python test_terminal_output.py
```

Expected output:

```
======================================================================
Testing TRADING_MODE = DEBUG
======================================================================

[Logger] Initialized (INFO) → logs/app.log
[Logger] Console output enabled (TRADING_MODE=DEBUG)
[NETWORK] INFO: Test info event in DEBUG mode
[DATA] DEBUG: Test debug event in DEBUG mode
✓ Console output shown above (expected in DEBUG mode)

======================================================================
Testing TRADING_MODE = SIM
======================================================================

✓ Terminal is clean (expected in SIM mode)
  Events logged to file: logs/app.log

======================================================================
Testing TRADING_MODE = LIVE
======================================================================

✓ Terminal is clean (expected in LIVE mode)
  Events logged to file: logs/app.log
```

---

## Manual Testing

### Test DEBUG Mode

```bash
export TRADING_MODE=DEBUG
python main.py

# Should see:
# - Boot banner
# - Logger initialization
# - Colored event output
# - Verbose debugging
```

### Test SIM Mode

```bash
export TRADING_MODE=SIM
python main.py

# Should see:
# - Clean terminal
# - No debug output
# - Application runs quietly
```

### Test LIVE Mode

```bash
export TRADING_MODE=LIVE
python main.py

# Should see:
# - Clean terminal
# - No debug output
# - Professional appearance
```

### Check File Logging (All Modes)

```bash
tail -f logs/app.log

# Should see events in all modes
```

### Check Debug Console (All Modes)

```
1. Start application
2. Press Ctrl+Shift+D
3. Should see live events in all modes
```

---

## Overriding Behavior

### Force Console Output in LIVE/SIM (Not Recommended)

If you absolutely need console output in LIVE/SIM for debugging:

```python
# Temporary workaround (remove after debugging)
import sys
import logging

# Add console handler manually
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)
```

**Warning:** This defeats the purpose of clean LIVE/SIM terminals.

---

## Best Practices

### DO ✅

- Use DEBUG mode during development
- Use SIM mode for strategy testing (clean terminal)
- Use LIVE mode for real trading (clean terminal)
- Check logs/app.log for historical events
- Use Debug Console (Ctrl+Shift+D) for live monitoring

### DON'T ❌

- Don't run DEBUG mode in production
- Don't manually add console handlers in LIVE/SIM
- Don't rely on terminal output in LIVE mode
- Don't disable file logging
- Don't forget to check the log file

---

## FAQ

**Q: I'm in SIM mode but want to see network events. How?**

A: Two options:

1. Press `Ctrl+Shift+D` to open Debug Console, filter by "network"
2. Run `tail -f logs/app.log | grep NETWORK`

**Q: How do I debug in LIVE mode?**

A: Don't change to DEBUG mode in production. Instead:

1. Press `Ctrl+Shift+D` for live events
2. Export session: Debug Console → "Export Snapshot"
3. Analyze offline with session replay tools

**Q: Can I have console output for errors only in LIVE mode?**

A: Yes, modify core/diagnostics.py:

```python
# In _console_handler, change the check to:
if getattr(settings, 'TRADING_MODE', 'DEBUG') == 'LIVE':
    # Only show errors/fatal in LIVE mode
    if event.level not in ['error', 'fatal']:
        return
```

**Q: Does this affect the Debug UI Console?**

A: No! Debug UI Console (`Ctrl+Shift+D`) works in all modes.

**Q: What about DTC protocol messages?**

A: All DTC messages logged to file and UI in all modes. Console only in DEBUG.

---

## Summary

**TRADING_MODE=DEBUG:**

- Verbose terminal output ✓
- Boot banner ✓
- Logger messages ✓
- Colored events ✓

**TRADING_MODE=SIM:**

- Clean terminal ✓
- File logging ✓
- UI Console ✓
- No console spam ✓

**TRADING_MODE=LIVE:**

- Clean terminal ✓
- File logging ✓
- UI Console ✓
- Professional appearance ✓

**Result:** Production-ready terminal behavior! 🎉
