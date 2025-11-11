# Signal Trace Orders - Usage Guide

## Overview
`signal_trace_orders.py` is a live diagnostic tool that traces order propagation through your app:

```
DTC Server → Blinker (signal_order) → MessageRouter → marshal_to_qt_thread → Panel2.on_order_update
```

---

## Integration

### Option 1: Auto-enable with DEBUG_DTC flag (Recommended)

Add to **main.py** (near the top, after imports):

```python
import os

# Enable order signal tracing when DEBUG_DTC is set
if os.getenv("DEBUG_DTC", "1") == "1":
    from tools.signal_trace_orders import attach_order_trace
    attach_order_trace()
```

### Option 2: Manual activation

In any Python file:

```python
from tools.signal_trace_orders import attach_order_trace

# Attach tracer
attach_order_trace()
```

---

## What It Traces

When an order arrives from DTC, you'll see a sequence like:

```
[16:13:54.872] [TRACE] [TRACE] DTC->Blinker emitted (Symbol=F.US.MESZ25, Status=2)
[16:13:54.873] [TRACE] [TRACE] Router->Qt marshaling (on_order_update)
[16:13:54.874] [TRACE] [TRACE] Qt->Marshaled OK (on_order_update)
[16:13:54.875] [TRACE] [TRACE] Qt->Panel2 received (Symbol=F.US.MESZ25, Status=2)
[16:13:54.876] [TRACE] [TRACE] Panel2->Processed OK (Symbol=F.US.MESZ25)
```

**Order Status Codes:**
- `1` = Pending
- `2` = Open/Working
- `3` = Partially filled
- `4` = Filled
- `7` = Completely filled

---

## Output Locations

1. **Console** - Real-time trace to stdout
2. **Log file** - `logs/signal_trace_orders.log`

---

## Error Detection

The tracer will catch and log:

1. **Blinker signal failures** - Signal not emitted
2. **Qt marshaling failures** - Thread dispatch errors
3. **Panel2 processing failures** - Exceptions in on_order_update

Example error output:
```
[16:14:01.234] [TRACE] [ERROR] Qt marshal FAILED (on_order_update): RuntimeError: wrapped C/C++ object has been deleted
[Exception details:]
Traceback (most recent call last):
  ...
```

---

## Troubleshooting

### No trace output?
1. Check DEBUG_DTC is set: `echo %DEBUG_DTC%` (should be "1")
2. Verify imports are correct (no import errors)
3. Check if orders are actually being sent from DTC

### Trace shows Blinker emitted but not Panel2?
- **Router not wired**: MessageRouter may not be subscribed to signal_order
- **Qt marshal failure**: Check if Qt event loop is running

### Panel2 receives but fails to process?
- Check logs for exception details
- Verify Panel2.on_order_update() implementation

---

## Performance Impact

- **Minimal** - Only logs when orders arrive (not continuous)
- Adds ~0.5ms per order (negligible)
- Safe for production use with DEBUG_DTC=1

---

## Standalone Testing

Test without running the full app:

```bash
python tools/signal_trace_orders.py
```

This will verify all hooks install correctly.

---

## See Also

- `trace_order_flow.py` - Full order flow tracer with UI
- `tools/router_diagnostic.py` - MessageRouter validation
- `ORDER_FLOW_DIAGNOSTIC_REPORT.md` - Architecture overview
