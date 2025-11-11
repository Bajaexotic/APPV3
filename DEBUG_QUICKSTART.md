# Debug Subsystem Quick Start

## 🚀 Quick Start (30 seconds)

### 1. Enable Debug Mode

```bash
export DEBUG_MODE=1
export DEBUG_NETWORK=1
export DEBUG_DATA=1
```

### 2. Use in Your Code

```python
from core.diagnostics import info, debug, error

# Log events
info("network", "Connection established", context={"host": "127.0.0.1"})
debug("data", "Processing trade", context={"symbol": "ES", "price": 4500})
error("core", "Config error", context={"missing": "API_KEY"})
```

### 3. Run Example

```bash
python examples/debug_integration_example.py
```

### 4. Enable Debug UI (PyQt6 apps)

Press **`Ctrl+Shift+D`** to toggle the debug console.

---

## 📚 Key Features

| Feature                  | Usage                                                  |
| ------------------------ | ------------------------------------------------------ |
| **Structured Logging**   | `log_event(category, level, message, context={...})`   |
| **Performance Tracking** | `with PerformanceMarker("operation"):`                 |
| **Error Policies**       | `handle_error("error_type", "category", operation=fn)` |
| **Health Monitoring**    | `register_component("name")` + `heartbeat("name")`     |
| **Session Replay**       | `SessionReplay.from_file("dump.json")`                 |
| **Debug Console**        | Press `Ctrl+Shift+D` in PyQt6 app                      |

---

## 📖 Components

### 1. DiagnosticsHub

Central event management and storage.

```python
from core.diagnostics import DiagnosticsHub

hub = DiagnosticsHub.get_instance()
snapshot = hub.snapshot(max_events=100)
hub.export_json("logs/session.json")
```

### 2. Error Policy Manager

Automatic error recovery with policies.

```python
from core.error_policy import handle_error

success = handle_error(
    error_type="dtc_connection_drop",
    category="network",
    operation=connect_function
)
```

### 3. Health Watchdog

Component health monitoring.

```python
from core.health_watchdog import register_component, heartbeat

register_component("my_service", heartbeat_timeout=30.0)
heartbeat("my_service")  # Call periodically
```

### 4. Session Replay

Forensic analysis of event timelines.

```python
from core.session_replay import SessionReplay

replay = SessionReplay.from_file("logs/debug_dump.json")
analysis = replay.analyze()
report = replay.generate_report("logs/report.md")
```

---

## 🎯 Common Patterns

### Pattern 1: Network Component

```python
from core.diagnostics import info, debug, PerformanceMarker
from core.health_watchdog import register_component, heartbeat

class NetworkClient:
    def __init__(self):
        register_component("network_client", heartbeat_timeout=30.0)

    def connect(self):
        with PerformanceMarker("connection", category="network"):
            # Connection logic
            info("network", "Connected", context={"host": self.host})

    def _heartbeat_loop(self):
        while self.running:
            heartbeat("network_client")
            time.sleep(10)
```

### Pattern 2: Data Processing

```python
from core.diagnostics import PerformanceMarker, debug

def process_market_data(data):
    with PerformanceMarker("data_processing", category="data"):
        debug("data", "Processing", context={"records": len(data)})
        # Process data
```

### Pattern 3: Error Handling

```python
from core.error_policy import handle_error

def risky_operation():
    success = handle_error(
        error_type="database_query_timeout",
        category="data",
        operation=lambda: db.execute(query)
    )
    return success
```

---

## 🔧 Environment Variables

| Variable          | Purpose                                   | Default |
| ----------------- | ----------------------------------------- | ------- |
| `DEBUG_MODE`      | Master debug switch                       | `0`     |
| `DEBUG_CORE`      | Core systems (app_manager, state_manager) | `0`     |
| `DEBUG_UI`        | UI events, signals, widgets               | `0`     |
| `DEBUG_DATA`      | DTC/JSON payloads, schema, cache          | `0`     |
| `DEBUG_NETWORK`   | Socket connectivity, heartbeats           | `0`     |
| `DEBUG_ANALYTICS` | Metrics, calculations                     | `0`     |
| `DEBUG_PERF`      | Performance measurements                  | `0`     |

---

## 📁 Files Created

```
APPSIERRA/
├── config/
│   ├── settings.py              # Updated with debug flags
│   └── debug_policies.yml       # Error recovery policies
├── core/
│   ├── diagnostics.py           # Core event system
│   ├── error_policy.py          # Policy enforcement
│   ├── health_watchdog.py       # Health monitoring
│   └── session_replay.py        # Forensic analysis
├── ui/
│   └── debug_console.py         # PyQt6 debug console
├── examples/
│   └── debug_integration_example.py  # Full example
└── docs/
    └── DEBUG_SUBSYSTEM.md       # Full documentation
```

---

## 🎨 Event Categories

| Category    | Usage                                |
| ----------- | ------------------------------------ |
| `core`      | App initialization, state management |
| `ui`        | Widget creation, signal emissions    |
| `data`      | DTC messages, JSON parsing, cache    |
| `network`   | Connections, heartbeats, timeouts    |
| `analytics` | Calculations, metrics, formulas      |
| `perf`      | Performance timing, resource usage   |
| `system`    | Health checks, diagnostics           |

---

## 📊 Event Levels

| Level   | Auto Stack Trace | Auto Dump |
| ------- | ---------------- | --------- |
| `debug` | No               | No        |
| `info`  | No               | No        |
| `warn`  | No               | No        |
| `error` | Yes              | No        |
| `fatal` | Yes              | Yes       |

---

## 💡 Tips

1. **Start simple**: Enable `DEBUG_MODE=1` and add `info()` calls
2. **Use categories**: Helps filter events in debug console
3. **Add context**: Rich context makes debugging easier
4. **Performance markers**: Wrap expensive operations
5. **Error policies**: Let the system handle retries
6. **Export sessions**: Save dumps for offline analysis
7. **Health monitoring**: Register long-running components

---

## 🐛 Troubleshooting

**No events showing?**

- Check `DEBUG_MODE=1` is set
- Press `Ctrl+Shift+D` to show debug console
- Check category/level filters in UI

**High memory usage?**

- Reduce buffer size: `DiagnosticsHub.get_instance(max_events=500)`
- Enable only needed categories

**Missing dependencies?**

```bash
pip install psutil pyyaml
```

---

## 📚 Full Documentation

See [`docs/DEBUG_SUBSYSTEM.md`](docs/DEBUG_SUBSYSTEM.md) for complete documentation.

---

## 🚦 Next Steps

1. ✅ Run the example: `python examples/debug_integration_example.py`
2. ✅ Review exported files in `logs/`
3. ✅ Add `log_event()` to your components
4. ✅ Configure error policies in `config/debug_policies.yml`
5. ✅ Enable debug console in your PyQt6 app
6. ✅ Read full docs: [`docs/DEBUG_SUBSYSTEM.md`](docs/DEBUG_SUBSYSTEM.md)
