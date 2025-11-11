# Debug Mode & Theme Selection Guide

## Table of Contents

1. [Theme Mode Selection (Diagnostics)](#theme-mode-selection)
2. [How Advanced Programs Enter Debug Mode](#advanced-debug-patterns)
3. [APPSIERRA Debug Mode Implementation](#appsierra-implementation)

---

## Theme Mode Selection

### Overview

APPSIERRA has three visual themes corresponding to trading modes:

| Mode      | Theme | Badge Color | Cell Borders | Background | Use Case            |
| --------- | ----- | ----------- | ------------ | ---------- | ------------------- |
| **DEBUG** | Dark  | Blue        | None         | Dark gray  | Development/Testing |
| **LIVE**  | Dark  | Neon Gold   | None         | Black      | Real trading        |
| **SIM**   | Light | Neon Blue   | Neon Blue    | White      | Simulated trading   |

**Eventually**: Mode will be **auto-detected** from DTC `LogonResponse` message (account type field).
**For Now**: Manual selection for diagnostics and testing.

---

### Method 1: Environment Variable (Recommended)

**Best for**: Quick testing, CI/CD, Docker containers

```bash
# Set before launching application
export TRADING_MODE=DEBUG
export TRADING_MODE=LIVE
export TRADING_MODE=SIM

# Then launch
python main.py
```

**Advantages:**

- ✅ Simple and clean
- ✅ Works across all platforms
- ✅ Easy to script
- ✅ No code changes needed

---

### Method 2: Config File Override

**Best for**: Persistent settings, shared team configurations

```json
// config/config.json
{
  "TRADING_MODE": "DEBUG",
  "POSTGRES_DSN": "postgresql://...",
  "DTC_HOST": "127.0.0.1"
}
```

**Advantages:**

- ✅ Persists across sessions
- ✅ Team can share config files
- ✅ Can check into version control (with secrets excluded)

**Priority**: `config.json` > Environment Variable > Default (SIM)

---

### Method 3: Command-Line Argument

**Best for**: One-off testing, scripts

```bash
python main.py --mode=DEBUG
python main.py --mode=LIVE
python main.py --mode=SIM
```

**Implementation** (in your main.py):

```python
import argparse
from config import settings

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['DEBUG', 'LIVE', 'SIM'],
                    help='Trading mode (overrides env and config)')
args = parser.parse_args()

if args.mode:
    settings.TRADING_MODE = args.mode
```

---

### Method 4: Runtime Keyboard Shortcut

**Best for**: Rapid testing during development

Add to your main window:

```python
from PyQt6.QtGui import QShortcut, QKeySequence
from config import settings
from config import theme  # Your theme module

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Add Ctrl+Shift+M to cycle modes
        mode_shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        mode_shortcut.activated.connect(self.cycle_trading_mode)

    def cycle_trading_mode(self):
        """Cycle through DEBUG → SIM → LIVE → DEBUG"""
        modes = ["DEBUG", "SIM", "LIVE"]
        current_index = modes.index(settings.TRADING_MODE)
        next_index = (current_index + 1) % len(modes)
        settings.TRADING_MODE = modes[next_index]

        # Apply theme
        theme.apply_theme(settings.TRADING_MODE)

        # Log the change
        from core.diagnostics import info
        info("ui", f"Trading mode changed to {settings.TRADING_MODE}", context={
            "mode": settings.TRADING_MODE,
            "method": "keyboard_shortcut"
        })

        # Update UI indicator (e.g., status bar)
        self.statusBar().showMessage(f"MODE: {settings.TRADING_MODE}", 3000)
```

**Hotkey**: **`Ctrl+Shift+M`** (M for Mode)

---

### Method 5: Debug UI Toggle

**Best for**: Visual selection, non-technical users

Add a dropdown/buttons to debug console:

```python
from PyQt6.QtWidgets import QComboBox, QPushButton
from config import settings

class DebugConsole(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Debug Console", parent)

        # Add mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["DEBUG", "SIM", "LIVE"])
        self.mode_combo.setCurrentText(settings.TRADING_MODE)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)

        # Add to layout
        layout.addWidget(QLabel("Trading Mode:"))
        layout.addWidget(self.mode_combo)

    def on_mode_changed(self, new_mode: str):
        """Handle mode change from UI"""
        settings.TRADING_MODE = new_mode
        theme.apply_theme(new_mode)

        from core.diagnostics import info
        info("ui", f"Trading mode changed to {new_mode}", context={
            "mode": new_mode,
            "method": "ui_dropdown"
        })
```

---

### Auto-Detection (Future Implementation)

Once DTC integration is complete, mode will be detected automatically:

```python
# In services/dtc_json_client.py

def on_logon_response(self, msg: dict):
    """Handle LogonResponse and detect trading mode"""
    # DTC LogonResponse contains account info
    is_simulated = msg.get("IsSimulatedAccount", 0) == 1

    if is_simulated:
        detected_mode = "SIM"
    else:
        detected_mode = "LIVE"

    # Update global mode
    from config import settings
    settings.TRADING_MODE = detected_mode

    # Apply theme
    from config import theme
    theme.apply_theme(detected_mode)

    # Log the detection
    from core.diagnostics import info
    info("network", f"Trading mode auto-detected: {detected_mode}", context={
        "mode": detected_mode,
        "is_simulated": is_simulated,
        "method": "dtc_logon_response"
    })
```

---

## Advanced Debug Patterns

### How Leading Software Enables Debug Mode

#### 1. **Environment Variables** (Universal)

Most common across all advanced systems:

```bash
# Node.js / Express
DEBUG=* node app.js
DEBUG=app:* node app.js          # Namespace filtering
DEBUG=app:database,app:api       # Multiple namespaces

# Python
PYTHONVERBOSE=1 python app.py
LOG_LEVEL=DEBUG python app.py

# Go
GODEBUG=gctrace=1 ./app

# Docker
docker run -e DEBUG=1 myapp

# Kubernetes
env:
  - name: DEBUG
    value: "1"
```

**Why it works:**

- ✅ Works in production without code changes
- ✅ Can be set per-deployment
- ✅ No recompilation needed
- ✅ Easy to toggle in containerized environments

---

#### 2. **Command-Line Flags** (CLI Tools)

```bash
# Verbosity levels
program -v           # Verbose
program -vv          # More verbose
program -vvv         # Debug level

# Explicit debug flag
program --debug
program --log-level=debug

# Component-specific
program --debug-network --debug-sql

# Examples from real tools
kubectl --v=9 get pods              # Kubernetes (0-9 verbosity)
curl -v https://api.example.com     # Verbose
git --verbose fetch                 # Git verbose mode
docker build --progress=plain       # Docker plain output
```

---

#### 3. **Configuration Files** (Enterprise)

```yaml
# config/production.yml
logging:
  level: INFO
  handlers:
    - console
    - file

debug:
  enabled: false

# config/development.yml
logging:
  level: DEBUG
  handlers:
    - console
    - file
    - debug_console

debug:
  enabled: true
  network: true
  sql: true
  performance: true
```

**Patterns:**

- Separate config files per environment
- Hot-reload configuration
- Hierarchical config (base + environment overrides)

---

#### 4. **Runtime Toggles** (Production Systems)

##### HTTP Endpoints (Admin API)

```bash
# Enable debug mode via API
curl -X POST https://api.example.com/admin/debug/enable \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Enable specific category
curl -X POST https://api.example.com/admin/debug/enable/sql

# Check debug status
curl https://api.example.com/admin/debug/status
```

##### Signal Handlers (Unix)

```python
import signal

def toggle_debug(signum, frame):
    """Toggle debug mode with SIGUSR1"""
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    print(f"Debug mode: {'ON' if DEBUG_MODE else 'OFF'}")

signal.signal(signal.SIGUSR1, toggle_debug)

# Usage: kill -SIGUSR1 <pid>
```

##### Feature Flags (LaunchDarkly, Split.io)

```python
from launchdarkly import LDClient

client = LDClient("sdk-key")
user = {"key": "user-123"}

if client.variation("debug-mode", user, False):
    enable_debug()
```

---

#### 5. **Build Configurations** (Compiled Languages)

##### C/C++ Preprocessor

```c
#ifdef DEBUG
    printf("Debug: variable x = %d\n", x);
#endif

// Compile with: gcc -DDEBUG main.c
```

##### Rust

```rust
#[cfg(debug_assertions)]
println!("Debug build");

#[cfg(not(debug_assertions))]
println!("Release build");

// cargo build --release  (disables debug assertions)
```

##### Go Build Tags

```go
// +build debug

package main

func init() {
    EnableDebugMode()
}

// go build -tags debug
```

---

#### 6. **Dynamic/Runtime Control** (Modern Systems)

##### Admin UI Panels

```
https://app.example.com/admin/debug
┌─────────────────────────────────┐
│ Debug Configuration             │
├─────────────────────────────────┤
│ ☑ Enable Debug Mode             │
│ ☑ SQL Query Logging             │
│ ☑ Network Tracing               │
│ ☐ Performance Profiling         │
│                                 │
│ Debug Level: [DEBUG ▼]          │
│ Buffer Size: [1000 ▼]           │
│                                 │
│ [Apply] [Reset]                 │
└─────────────────────────────────┘
```

##### In-App Debug Menu

```python
# Accessible via Ctrl+Shift+D or hidden URL
class DebugPanel:
    def __init__(self):
        self.checkboxes = {
            "core": QCheckBox("Core Systems"),
            "network": QCheckBox("Network"),
            "database": QCheckBox("Database"),
            "ui": QCheckBox("UI Events")
        }

        for name, checkbox in self.checkboxes.items():
            checkbox.stateChanged.connect(
                lambda state, n=name: self.toggle_debug(n, state)
            )
```

---

#### 7. **Telemetry Integration** (Cloud-Native)

##### OpenTelemetry Sampling

```python
from opentelemetry import trace

# Increase sampling rate for specific users
sampler = TraceIdRatioBased(
    rate=1.0 if user.is_developer() else 0.01
)
```

##### Datadog / New Relic

```python
# Tag specific transactions for detailed tracing
tracer.current_span().set_tag("debug", "true")
tracer.current_span().set_tag("user_id", user_id)
```

---

## APPSIERRA Implementation

### Current State

APPSIERRA uses a **multi-layer approach** combining best practices:

#### Layer 1: Granular Debug Flags

```bash
export DEBUG_MODE=1          # Master switch
export DEBUG_CORE=1          # Core systems
export DEBUG_UI=1            # UI events
export DEBUG_DATA=1          # Data processing
export DEBUG_NETWORK=1       # Network operations
export DEBUG_ANALYTICS=1     # Calculations
export DEBUG_PERF=1          # Performance tracking
```

#### Layer 2: Trading Mode Selection

```bash
export TRADING_MODE=DEBUG    # Theme + behavior
export TRADING_MODE=LIVE
export TRADING_MODE=SIM
```

#### Layer 3: Runtime Tools

- Debug UI Console (`Ctrl+Shift+D`)
- Event filtering by category/level
- Live performance monitoring
- Session export and replay

---

### Recommended Workflow

#### Development

```bash
# Full debugging enabled
export DEBUG_MODE=1
export DEBUG_CORE=1
export DEBUG_UI=1
export DEBUG_DATA=1
export DEBUG_NETWORK=1
export TRADING_MODE=DEBUG

python main.py
```

#### Testing (Simulated Trading)

```bash
# Moderate debugging
export DEBUG_MODE=1
export DEBUG_NETWORK=1
export DEBUG_DATA=1
export TRADING_MODE=SIM

python main.py
```

#### Production (Live Trading)

```bash
# Minimal logging, errors only
export TRADING_MODE=LIVE

python main.py

# Enable debug remotely if needed:
# 1. Press Ctrl+Shift+D in UI
# 2. Enable specific categories
# 3. Export session when done
```

---

## Comparison: APPSIERRA vs Industry Standards

| Feature              | APPSIERRA        | Chrome DevTools    | VS Code          | Docker              | Kubernetes       |
| -------------------- | ---------------- | ------------------ | ---------------- | ------------------- | ---------------- |
| **Environment Vars** | ✅ DEBUG\_\*     | ✅ DEBUG           | ✅ VSCODE\_\*    | ✅ DEBUG            | ✅ LOG_LEVEL     |
| **Config Files**     | ✅ config.json   | ✅ settings.json   | ✅ settings.json | ✅ docker-compose   | ✅ ConfigMaps    |
| **Runtime Toggle**   | ✅ Ctrl+Shift+D  | ✅ F12             | ✅ Ctrl+Shift+P  | ❌ Requires restart | ✅ kubectl patch |
| **Granular Control** | ✅ 6 categories  | ✅ Per-domain      | ✅ Per-extension | ✅ Per-container    | ✅ Per-pod       |
| **UI Console**       | ✅ Debug Console | ✅ DevTools        | ✅ Debug Console | ✅ Logs panel       | ✅ kubectl logs  |
| **Session Replay**   | ✅ JSON export   | ✅ Performance tab | ✅ Debug logs    | ✅ Log export       | ✅ Audit logs    |
| **Performance**      | ✅ Auto markers  | ✅ Profiler        | ✅ Profiler      | ✅ Stats            | ✅ Metrics       |

**Conclusion**: APPSIERRA's debug system matches industry leaders! 🎉

---

## Best Practices

### DO ✅

- Use `DEBUG_MODE=1` during development
- Enable specific categories when investigating issues
- Export sessions before closing after bugs
- Use SIM mode for testing strategies
- Document debug flag usage in runbooks

### DON'T ❌

- Run `DEBUG_MODE=1` in production without reason
- Enable all debug flags simultaneously (performance impact)
- Forget to disable debug before live trading
- Ignore debug console warnings
- Mix LIVE mode with test data

---

## Quick Reference

```bash
# Quick Start - Development
export DEBUG_MODE=1 DEBUG_NETWORK=1 DEBUG_DATA=1 TRADING_MODE=DEBUG
python main.py

# Quick Start - Testing
export TRADING_MODE=SIM
python main.py

# Quick Start - Production
export TRADING_MODE=LIVE
python main.py

# Debug Console
Ctrl+Shift+D          # Toggle debug console
Ctrl+Shift+M          # Cycle trading modes (if implemented)

# Debug Specific Issue
export DEBUG_NETWORK=1  # Just network debugging
python main.py
```

---

**Summary**: APPSIERRA provides flexible debug mode selection matching industry best practices, with automatic mode detection coming via DTC integration. Use environment variables for quick testing, config files for persistence, and the debug console for runtime control.
