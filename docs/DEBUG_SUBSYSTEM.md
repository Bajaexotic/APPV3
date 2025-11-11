# APPSIERRA Advanced Debug Subsystem

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Core Components](#core-components)
6. [Integration Guide](#integration-guide)
7. [Debug UI Console](#debug-ui-console)
8. [Error Policy System](#error-policy-system)
9. [Health Monitoring](#health-monitoring)
10. [Session Replay & Forensics](#session-replay--forensics)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The APPSIERRA Advanced Debug Subsystem is a comprehensive observability and diagnostics framework designed for production-grade debugging. It provides:

- **Structured Event Logging** with rich context
- **Ring Buffer** for in-memory event storage
- **Event Routing** to console, file, UI, and telemetry
- **Error Policy Matrix** for automated recovery
- **Health Watchdog** for component monitoring
- **Debug UI Console** for real-time event viewing
- **Session Replay** for post-mortem analysis
- **Performance Markers** for timing critical paths

### Philosophy

The debug subsystem acts as a **distributed nervous system** where every event answers:

1. **Where** did this happen? (file, module, line, thread)
2. **Why** did it happen? (causal event, trigger)
3. **What** should be done? (policy, reaction)

---

## Architecture

### Layered Design

```
┌─────────────────────────────────────────────────────────┐
│                  Application Code                        │
└──────────────┬────────────────────────────────┬─────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   Diagnostic Events       │    │   Health Watchdog        │
│   (log_event API)        │    │   (heartbeat API)        │
└──────────────┬───────────┘    └──────────────┬───────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────────────────────────────────┐
│              DiagnosticsHub (Singleton)                  │
│  - Ring Buffer (1000 events)                             │
│  - Event Router                                          │
│  - Statistics Tracking                                   │
│  - Performance Markers                                   │
└──────────────┬───────────────────────────────────────────┘
               │
    ┌──────────┴───────────┬────────────┬─────────────┐
    ▼                      ▼            ▼             ▼
┌─────────┐      ┌──────────────┐  ┌─────────┐  ┌──────────┐
│ Console │      │  Debug UI    │  │  File   │  │ Telemetry│
│ Handler │      │  Console     │  │ Logger  │  │ (future) │
└─────────┘      └──────────────┘  └─────────┘  └──────────┘
```

### Event Flow

1. **Emit**: `log_event()` called from application code
2. **Capture**: Caller information extracted automatically
3. **Route**: Event sent to all registered handlers
4. **Store**: Event added to ring buffer
5. **Display**: Handlers output to console/UI/file
6. **Analyze**: Events available for replay and forensics

---

## Quick Start

### 1. Basic Usage

```python
from core.diagnostics import log_event, info, debug, warn, error

# Simple logging
info("network", "Connection established", context={"host": "127.0.0.1"})

# Debug with context
debug("data", "Processing market data", context={
    "symbol": "ES",
    "price": 4500.25,
    "volume": 1000
})

# Error with automatic stack trace
error("core", "Configuration error", context={"missing_key": "API_KEY"})
```

### 2. Performance Measurement

```python
from core.diagnostics import PerformanceMarker

# Measure code block execution time
with PerformanceMarker("database_query", category="data"):
    result = database.execute(query)
```

### 3. Error Handling with Policy

```python
from core.error_policy import handle_error

def connect_to_server():
    # Connection logic
    pass

# Automatic retry with exponential backoff
success = handle_error(
    error_type="dtc_connection_drop",
    category="network",
    context={"host": "127.0.0.1"},
    operation=connect_to_server
)
```

### 4. Health Monitoring

```python
from core.health_watchdog import register_component, heartbeat

# Register component
register_component("dtc_client", heartbeat_timeout=30.0)

# Send periodic heartbeats
while running:
    heartbeat("dtc_client")
    time.sleep(10)
```

---

## Configuration

### Environment Variables

Enable debug subsystems via environment variables:

```bash
# Core debug flags
export DEBUG_MODE=1           # Master debug switch
export DEBUG_CORE=1           # Core systems (app_manager, state_manager)
export DEBUG_UI=1             # UI events, signals, widgets
export DEBUG_DATA=1           # DTC/JSON payloads, schema, cache
export DEBUG_NETWORK=1        # Socket connectivity, heartbeats
export DEBUG_ANALYTICS=1      # Metrics, calculations
export DEBUG_PERF=1           # Performance measurements

# Legacy flags (still supported)
export DEBUG_DTC=1            # DTC protocol debugging
```

### Runtime Configuration

Debug flags are loaded from `config/settings.py`:

```python
from config import settings

if settings.DEBUG_CORE:
    log_event("core", "debug", "Core debugging enabled")
```

---

## Core Components

### 1. DiagnosticsHub

The central hub for all diagnostic events.

```python
from core.diagnostics import DiagnosticsHub

hub = DiagnosticsHub.get_instance()

# Get recent events
snapshot = hub.snapshot(max_events=100)

# Export session
hub.export_json("logs/debug_session.json")

# Clear buffer
hub.clear()

# Get statistics
stats = hub.get_statistics()
```

### 2. Event Schema

All events follow a consistent structure:

```json
{
  "timestamp": "2025-01-06T12:00:00.000Z",
  "category": "network",
  "level": "info",
  "module": "services.dtc_client",
  "event_type": "ConnectionSuccess",
  "message": "DTC connection established",
  "context": {
    "host": "127.0.0.1",
    "port": 11099
  },
  "file_path": "/app/services/dtc_client.py",
  "line_number": 145,
  "function_name": "connect",
  "thread_id": 12345,
  "thread_name": "MainThread",
  "event_id": "evt_000123"
}
```

### 3. Event Categories

| Category    | Purpose            | Examples                             |
| ----------- | ------------------ | ------------------------------------ |
| `core`      | Core systems       | App initialization, state management |
| `ui`        | UI events          | Widget creation, signal emissions    |
| `data`      | Data processing    | DTC messages, JSON parsing, cache    |
| `network`   | Network operations | Connections, heartbeats, timeouts    |
| `analytics` | Calculations       | Metrics, aggregations, formulas      |
| `perf`      | Performance        | Timing, memory, CPU usage            |
| `system`    | System-level       | Health checks, diagnostics           |

### 4. Event Levels

| Level   | Usage                | Auto Stack Trace |
| ------- | -------------------- | ---------------- |
| `debug` | Detailed tracing     | No               |
| `info`  | Normal operations    | No               |
| `warn`  | Potential issues     | No               |
| `error` | Errors (recoverable) | Yes              |
| `fatal` | Fatal errors         | Yes + Auto-dump  |

---

## Integration Guide

### Integrating into Existing Modules

#### Example: DTC Client Integration

```python
# services/dtc_json_client.py

from config import settings
from core.diagnostics import log_event, PerformanceMarker
from core.error_policy import handle_error
from core.health_watchdog import register_component, heartbeat

class DTCJSONClient:
    def __init__(self):
        # Register for health monitoring
        if settings.DEBUG_NETWORK:
            register_component(
                "dtc_client",
                heartbeat_timeout=30.0,
                metadata={"component_type": "network"}
            )

    def connect(self):
        if settings.DEBUG_NETWORK:
            log_event(
                category="network",
                level="info",
                message="Attempting DTC connection",
                event_type="ConnectionAttempt",
                context={"host": self.host, "port": self.port}
            )

        # Measure connection time
        with PerformanceMarker("dtc_connection", category="network"):
            try:
                self._establish_connection()

                if settings.DEBUG_NETWORK:
                    log_event(
                        category="network",
                        level="info",
                        message="DTC connection established",
                        event_type="ConnectionSuccess"
                    )

            except Exception as e:
                # Use error policy for auto-retry
                success = handle_error(
                    error_type="dtc_connection_drop",
                    category="network",
                    exception=e,
                    operation=self._establish_connection
                )

                if not success:
                    raise

    def _heartbeat_loop(self):
        """Background heartbeat thread"""
        while self.running:
            if settings.DEBUG_NETWORK:
                heartbeat("dtc_client", metadata={
                    "connected": self.is_connected,
                    "messages_received": self.message_count
                })
            time.sleep(10)
```

#### Example: UI Panel Integration

```python
# panels/panel1.py

from config import settings
from core.diagnostics import log_event, PerformanceMarker

class Panel1(QWidget):
    def update_display(self):
        if settings.DEBUG_UI:
            log_event(
                category="ui",
                level="debug",
                message="Updating Panel1 display",
                event_type="PanelUpdate",
                context={"panel": "Panel1"}
            )

        with PerformanceMarker("panel1_render", category="ui"):
            self._render_content()

    def _render_content(self):
        # Rendering logic
        pass
```

---

## Debug UI Console

The Debug Console provides real-time event viewing with filtering and statistics.

### Features

- **Live Event Stream** with color-coding by level
- **Category/Level Filtering**
- **System Statistics** (CPU, memory, event counts)
- **Export Controls** for creating snapshots
- **Pause/Resume** capability
- **Configurable Buffer Size**

### Integration

```python
# In main application window

from ui.debug_console import DebugConsole
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create debug console
        self.debug_console = DebugConsole(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debug_console)

        # Hide by default
        self.debug_console.setVisible(False)

        # Add Ctrl+Shift+D hotkey
        debug_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        debug_shortcut.activated.connect(self.debug_console.toggle_visibility)
```

### Keyboard Shortcuts

| Shortcut       | Action                          |
| -------------- | ------------------------------- |
| `Ctrl+Shift+D` | Toggle debug console visibility |

---

## Error Policy System

Error policies define automated responses to errors.

### Policy Configuration

Policies are defined in `config/debug_policies.yml`:

```yaml
network:
  dtc_connection_drop:
    recovery: "auto_retry"
    max_retries: 3
    backoff_ms: 2000
    escalation: true
    dump_snapshot: false
    severity: "warn"
    message: "DTC connection dropped, attempting reconnection"
```

### Available Recovery Actions

| Action         | Description                    |
| -------------- | ------------------------------ |
| `auto_retry`   | Retry with exponential backoff |
| `skip_message` | Skip current message, continue |
| `log_continue` | Log and continue execution     |
| `use_default`  | Use default/fallback value     |
| `abort`        | Abort operation                |
| `reconnect`    | Attempt reconnection           |
| `clear_cache`  | Clear affected cache           |
| `reset_state`  | Reset to known good state      |

### Custom Policies

Add custom error policies by editing `config/debug_policies.yml`:

```yaml
custom_category:
  my_error_type:
    recovery: "auto_retry"
    max_retries: 5
    backoff_ms: 1000
    escalation: true
    dump_snapshot: true
    severity: "error"
    message: "Custom error occurred"
```

---

## Health Monitoring

The Health Watchdog monitors component health via heartbeats.

### Component Registration

```python
from core.health_watchdog import register_component, heartbeat

# Register once during initialization
register_component(
    name="my_component",
    heartbeat_timeout=30.0,  # Seconds before marked unresponsive
    metadata={"type": "service"}
)

# Send heartbeats periodically
while running:
    heartbeat("my_component", metadata={
        "status": "active",
        "queue_size": queue.size()
    })
    time.sleep(10)
```

### Starting the Watchdog

```python
from core.health_watchdog import HealthWatchdog

# In application startup
watchdog = HealthWatchdog.get_instance()
watchdog.start()

# In application shutdown
watchdog.stop()
```

### Health Callbacks

Register callbacks for health updates:

```python
def on_health_update(metrics):
    print(f"Healthy components: {metrics.healthy_components}/{metrics.total_components}")
    print(f"CPU: {metrics.cpu_percent:.1f}%")
    print(f"Memory: {metrics.memory_mb:.1f} MB")

watchdog.register_health_callback(on_health_update)
```

---

## Session Replay & Forensics

Replay and analyze diagnostic sessions for debugging.

### Loading a Session

```python
from core.session_replay import SessionReplay

# Load from dump file
replay = SessionReplay.from_file("logs/debug_snapshot_20250106_123045.json")

# Analyze session
analysis = replay.analyze()
print(f"Total events: {analysis.total_events}")
print(f"Error rate: {analysis.error_rate:.2%}")
print(f"Duration: {analysis.duration_sec:.2f}s")
```

### Playback

```python
# Real-time playback
replay.playback(speed=1.0)

# 10x speed playback
replay.playback(speed=10.0)

# Filtered playback
replay.playback(
    speed=5.0,
    filter_category="network",
    filter_level="error"
)

# Custom callback
def my_handler(event):
    print(f"[{event.category}] {event.message}")

replay.playback(callback=my_handler)
```

### Searching Events

```python
# Search by pattern
errors = replay.search(pattern="connection.*failed", category="network")

# Search by context
db_errors = replay.search(
    category="data",
    context_key="operation",
    context_value="database_query"
)
```

### Forensic Reports

```python
# Generate markdown report
report = replay.generate_report("logs/forensic_report.md")
print(report)
```

---

## Best Practices

### 1. Use Appropriate Event Levels

```python
# ✅ Good
debug("data", "Cache hit for key: user_123")
info("network", "Connection established")
warn("perf", "Slow query detected", context={"elapsed_ms": 1500})
error("core", "Failed to load config", context={"file": "config.json"})

# ❌ Bad
info("data", "Error occurred")  # Should be error level
error("network", "Connecting...")  # Should be debug/info level
```

### 2. Provide Rich Context

```python
# ✅ Good
log_event(
    category="data",
    level="info",
    message="Market data received",
    event_type="MarketDataUpdate",
    context={
        "symbol": "ES",
        "price": 4500.25,
        "volume": 1000,
        "timestamp": "2025-01-06T12:00:00Z"
    }
)

# ❌ Bad
log_event("data", "info", "Got data")  # Missing context
```

### 3. Use Performance Markers for Critical Paths

```python
# ✅ Good
with PerformanceMarker("database_query", category="data"):
    result = expensive_operation()

# Alternative with manual markers
hub = DiagnosticsHub.get_instance()
hub.mark_performance("query_start")
result = expensive_operation()
hub.mark_performance("query_end")
elapsed = hub.measure_elapsed("query_start", "query_end")
```

### 4. Conditional Debug Logging

```python
from config import settings

# ✅ Good - Only log when needed
if settings.DEBUG_NETWORK:
    debug("network", "Packet details", context={"size": len(packet)})

# For frequently called code
if settings.DEBUG_PERF:
    with PerformanceMarker("tight_loop"):
        for item in large_list:
            process(item)
```

### 5. Use Error Policies for Transient Failures

```python
# ✅ Good - Automatic retry with policy
success = handle_error(
    error_type="dtc_connection_drop",
    category="network",
    operation=connect_function
)

# ❌ Bad - Manual retry logic everywhere
for attempt in range(3):
    try:
        connect_function()
        break
    except Exception:
        time.sleep(2 ** attempt)
```

---

## Troubleshooting

### Debug Console Not Showing Events

**Problem**: Debug console is empty despite application activity.

**Solutions**:

1. Check if DEBUG_MODE is enabled: `export DEBUG_MODE=1`
2. Ensure console is visible: Press `Ctrl+Shift+D`
3. Check filters (category/level dropdown)
4. Verify event categories match enabled filters

### High Memory Usage

**Problem**: Application memory grows over time.

**Solutions**:

1. Reduce ring buffer size in DiagnosticsHub initialization
2. Adjust max_events in debug console
3. Enable periodic buffer clearing:

   ```python
   hub = DiagnosticsHub.get_instance(max_events=500)  # Smaller buffer
   ```

### Slow Performance When Debugging

**Problem**: Application slower with debug flags enabled.

**Solutions**:

1. Enable only needed subsystems:

   ```bash
   export DEBUG_NETWORK=1  # Only network debugging
   ```

2. Use conditional logging:

   ```python
   if settings.DEBUG_DATA and settings.DEBUG_MODE:
       log_event(...)
   ```

3. Disable console handler for high-frequency events

### Missing Dependencies

**Problem**: Import errors for `psutil` or `yaml`.

**Solutions**:

```bash
pip install psutil pyyaml
```

---

## Summary

The APPSIERRA Advanced Debug Subsystem provides:

✅ **Structured Events** with automatic context capture
✅ **Error Policies** for automated recovery
✅ **Health Monitoring** for component oversight
✅ **Debug UI** for real-time event viewing
✅ **Session Replay** for post-mortem analysis
✅ **Performance Markers** for timing critical paths

### Next Steps

1. Enable debug flags in your environment
2. Integrate `log_event()` into critical code paths
3. Add health monitoring for key components
4. Configure error policies for common failures
5. Use the Debug Console (`Ctrl+Shift+D`) during development
6. Export sessions for offline analysis

For questions or issues, see the troubleshooting section or check the implementation code in `core/diagnostics.py`.
