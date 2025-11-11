# Startup Log Cleanup - Implementation Summary

## Overview
Cleaned up noisy startup logs to provide a cleaner, more professional startup experience. Unnecessary debug chatter has been suppressed or gated behind environment flags.

## Changes Made

### 1. main.py
**Suppressed cosmetic UI feature flag logs:**
- `ENABLE_GLOW`
- `ENABLE_HOVER_ANIMATIONS`
- `TOOLTIP_AUTO_HIDE_MS`

These are now only visible when `DEBUG_DTC=1`.

**Before:**
```
ENABLE_GLOW: True
ENABLE_HOVER_ANIMATIONS: True
TOOLTIP_AUTO_HIDE_MS: 3000
```

**After (normal startup):**
```
(silent)
```

**After (with DEBUG_DTC=1):**
```
ENABLE_GLOW: True
ENABLE_HOVER_ANIMATIONS: True
TOOLTIP_AUTO_HIDE_MS: 3000
```

---

### 2. core/app_manager.py
**Gated all debug prints and logs behind DEBUG_DTC=1:**

| Log Message | Type | Before | After |
|------------|------|---------|--------|
| "DEBUG: app_manager.py module loaded" | print | Always | Only if DEBUG_DTC=1 |
| "[Startup] app_manager module loaded" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "DEBUG: MainWindow.__init__ STARTING" | print | Always | Only if DEBUG_DTC=1 |
| "[Startup] MainWindow __init__ begin" | log.info | Always | Changed to "[startup] Initializing MainWindow" |
| "DEBUG: Panel1/2/3 created" | print | Always | Only if DEBUG_DTC=1 |
| "[Startup] Panels created" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[Startup] Direct DTC init..." | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[DTC] Searching for DTC server..." | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[DTC] MessageRouter instantiated" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[Startup] Wired Panel3 -> Panel2" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[Theme] Reapplied LIVE after panel init" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |
| "[Startup] Mode selector hotkey enabled" | log.info | Always | Only if DEBUG_DTC=1 (demoted to debug) |

**High-level lifecycle logs (always visible):**
- `[startup] Initializing MainWindow` - INFO
- `[startup] MainWindow initialized` - INFO
- `[startup] DTC session ready` - INFO
- `[info] DTC connected` - INFO
- `[info] DTC disconnected` - INFO
- `[error] DTC error: ...` - ERROR

---

### 3. core/message_router.py
**Suppressed trade account enumeration:**

**Before:**
```
router.trade_account.Sim1
router.trade_account.Sim2
router.trade_account.Live1
```

**After (normal startup):**
```
(silent)
```

**After (with DEBUG_DTC=1):**
```
router.trade_account.Sim1
router.trade_account.Sim2
router.trade_account.Live1
```

**Other changes:**
- `router.signals.subscribed` demoted from INFO to DEBUG (only visible with DEBUG_DTC=1)

---

### 4. utils/logger.py
**Added QUIET_STARTUP environment variable support:**

| Mode | DEBUG Logs | INFO Logs | Console Output |
|------|-----------|-----------|----------------|
| Normal | Visible (if DEBUG_MODE=True) | Visible | Visible (if TRADING_MODE=DEBUG) |
| QUIET_STARTUP=1 | **Suppressed** | Visible | Suppressed (file only) |
| QUIET_STARTUP=1 + DEBUG_DTC=1 | Still suppressed by logger level | Visible | Suppressed (file only) |

**Key behaviors:**
- `QUIET_STARTUP=1` forces log level to INFO regardless of DEBUG_MODE
- All DEBUG logs are suppressed in QUIET_STARTUP mode
- Console output is disabled in QUIET_STARTUP mode
- File logging always works (logs/app.log)

---

## Environment Variables

### DEBUG_DTC (default: 0)
Controls debug-level logging and print statements.

**Usage:**
```bash
# Enable debug logs
export DEBUG_DTC=1
python main.py

# Windows
set DEBUG_DTC=1
python main.py
```

**When enabled:**
- Shows all debug prints (panel creation, signal wiring, etc.)
- Shows account enumeration logs
- Shows cosmetic UI feature flags
- Shows detailed DTC connection logs

---

### QUIET_STARTUP (default: 0)
Forces minimal logging during startup.

**Usage:**
```bash
# Enable quiet startup
export QUIET_STARTUP=1
python main.py

# Windows
set QUIET_STARTUP=1
python main.py
```

**When enabled:**
- Suppresses ALL DEBUG logs
- Only shows critical INFO/WARNING/ERROR logs
- No console output (logs to file only)
- Clean, minimal startup experience

---

## Example Startup Outputs

### Normal Startup (default)
```
[startup] Initializing MainWindow
[startup] MainWindow initialized
[startup] DTC session ready
[info] DTC connected
[info] router.balance 21.66
```

### With DEBUG_DTC=1
```
DEBUG: app_manager.py module loaded, logger initialized
ENABLE_GLOW: True
ENABLE_HOVER_ANIMATIONS: True
TOOLTIP_AUTO_HIDE_MS: 3000
DEBUG: MainWindow.__init__ STARTING
[startup] Initializing MainWindow
DEBUG: About to create panels (Panel1, Panel2, Panel3)...
DEBUG: Panel1 created
DEBUG: Panel2 created
DEBUG: Panel3 created
[Startup] Panels created: Panel1/Panel2/Panel3
DEBUG: About to initialize DTC and run diagnostics...
[DTC] Searching for DTC server at 127.0.0.1:11099
[DTC] MessageRouter instantiated and wired to panels/state
DEBUG: Session ready - sending AccountBalanceRequest
[startup] DTC session ready
[info] DTC connected
router.trade_account.Sim1
router.trade_account.Sim2
[info] router.balance 21.66
```

### With QUIET_STARTUP=1
```
[Logger] QUIET_STARTUP mode enabled → C:\Users\...\logs\app.log
[startup] Initializing MainWindow
[startup] MainWindow initialized
[startup] DTC session ready
[info] DTC connected
```

---

## Implementation Notes

### Code Patterns

**Guard pattern for debug prints:**
```python
if os.getenv("DEBUG_DTC", "0") == "1":
    print("DEBUG: ...")
```

**Guard pattern for debug logs:**
```python
if os.getenv("DEBUG_DTC", "0") == "1":
    log.debug("[Startup] ...")
```

**High-level lifecycle logs (always visible):**
```python
log.info("[startup] Initializing MainWindow")
log.info("[info] DTC connected")
```

### Log Prefixes

Consistent prefixes for easy filtering:
- `[startup]` - Application initialization
- `[info]` - Critical lifecycle events
- `[error]` - Error conditions
- `[DTC]` - DTC-specific operations (debug only)
- `[Startup]` - Panel wiring (debug only)
- `[Theme]` - Theme operations (debug only)

---

## Testing

### Test Normal Startup
```bash
python main.py
```
Expected: Clean startup with only high-level lifecycle logs.

### Test Debug Mode
```bash
set DEBUG_DTC=1
python main.py
```
Expected: Verbose debug output with all details.

### Test Quiet Mode
```bash
set QUIET_STARTUP=1
python main.py
```
Expected: Minimal output, INFO logs only.

### Test Combination
```bash
set DEBUG_DTC=1
set QUIET_STARTUP=1
python main.py
```
Expected: QUIET_STARTUP takes precedence, minimal output.

---

## Benefits

✅ **Cleaner Startup Experience**
- No more cosmetic UI feature flag spam
- No more duplicate Sim1/Sim2 account enumeration
- Only essential lifecycle events visible

✅ **Flexible Debugging**
- Enable DEBUG_DTC=1 for full verbosity when troubleshooting
- Disable for production-ready clean output

✅ **Production Ready**
- Use QUIET_STARTUP=1 for minimal logging
- All logs still captured to file for diagnostics

✅ **Maintainable**
- Consistent guard patterns across codebase
- Easy to add new debug logs with same pattern
- Clear separation of debug vs production logs

---

## Future Improvements

1. **Structured Logging**: Consider migrating all logging to structlog for better filtering and analysis
2. **Log Levels**: Fine-tune log levels (TRACE, DEBUG, INFO, WARNING, ERROR)
3. **Performance**: Add timing metrics for startup stages (only visible with DEBUG_DTC=1)
4. **Documentation**: Add log level documentation to developer guide

---

## Related Files

- `main.py` - Entry point, cosmetic feature flag logs
- `core/app_manager.py` - Main startup orchestration
- `core/message_router.py` - Account enumeration, signal routing
- `utils/logger.py` - Logger configuration, QUIET_STARTUP support
