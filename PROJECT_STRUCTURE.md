# APPSIERRA Project Structure

**Last Updated:** 2025-11-09
**Status:** Reorganized for clarity

---

## Directory Structure

```
APPSIERRA/
├── core/                   # Core application logic
│   ├── app_manager.py     # Main window (MainWindow class)
│   ├── data_bridge.py     # DTC client (DTCClientJSON)
│   ├── state_manager.py   # Application state
│   └── message_router.py  # Message routing
│
├── panels/                 # UI panels
│   ├── panel1.py          # Balance/Investing panel
│   ├── panel2.py          # Live Trade panel
│   └── panel3.py          # Statistics panel
│
├── widgets/                # Reusable UI widgets
│   ├── connection_icon.py # Connection status indicator
│   ├── dev_toolbar.py     # Developer toolbar (theme/font controls)
│   └── timeframe_pills.py # Timeframe selector widget
│
├── services/               # Business logic layer
│   ├── dtc_constants.py   # DTC message type constants
│   ├── dtc_protocol.py    # DTC protocol utilities
│   └── dtc_schemas.py     # Pydantic schemas for DTC messages
│
├── config/                 # Configuration
│   ├── settings.py        # Application settings
│   └── theme.py           # Theme definitions (DEBUG/SIM/LIVE)
│
├── utils/                  # Utilities
│   ├── theme_mixin.py     # ThemeAwareMixin for panels
│   ├── theme_helpers.py   # Theme utility functions
│   └── mode_selector.py   # Mode cycling (Ctrl+Shift+M hotkey)
│
├── tests/                  # Test suite
│   ├── conftest.py        # Pytest fixtures (mocked panels, DTC messages)
│   ├── integration/       # Integration tests (require Sierra Chart)
│   │   ├── test_dtc_connection.py
│   │   └── README.md
│   ├── unit/              # Unit tests (standalone, fast)
│   │   ├── test_mode_logic.py
│   │   ├── test_mode_switching.py
│   │   ├── test_balance_debug.py
│   │   ├── test_debug_subsystem.py
│   │   ├── test_terminal_output.py
│   │   ├── test_dtc_messages.py
│   │   └── README.md
│   ├── test_panel1_comprehensive.py  # Panel 1 pytest tests
│   ├── test_panel2_comprehensive.py  # Panel 2 pytest tests
│   ├── test_panel3_comprehensive.py  # Panel 3 pytest tests
│   ├── test_performance_and_signals.py  # Performance tests
│   └── README_TEST_SUITE.md
│
├── tools/                  # Diagnostic and debugging utilities
│   ├── dtc_test_framework.py      # DTC testing framework (live connection)
│   ├── dtc_probe.py              # DTC protocol debugging
│   ├── dtc_diagnostic.py         # DTC diagnostics
│   ├── discover_all_dtc_messages.py
│   ├── theme_sandbox.py          # Theme testing sandbox
│   └── debug_phantom_position.py
│
├── demos/                  # Demonstration scripts
│   ├── demo_test_run.py          # Simulated test execution (success)
│   ├── demo_test_failure.py      # Simulated test failures + self-healing
│   ├── demo_theme_switching.py   # Theme switching demonstration
│   └── README.md
│
├── ui/                     # UI utilities
│   └── debug_console.py   # Debug console widget
│
├── main.py                 # Application entry point
├── selfheal.py            # Self-healing system
├── pytest.ini             # Pytest configuration
├── run_tests.bat          # Windows test runner
├── run_tests.sh           # Linux/Mac test runner
└── requirements-test.txt  # Test dependencies
```

---

## Key Distinctions

### tests/ vs tools/

| Aspect       | tests/                 | tools/                       |
| ------------ | ---------------------- | ---------------------------- |
| Purpose      | Automated testing      | Manual debugging/diagnostics |
| Execution    | Via pytest             | Run directly                 |
| Speed        | Fast (mocked)          | Slower (live connections)    |
| Dependencies | None (mocked fixtures) | Requires Sierra Chart (some) |
| CI/CD        | Yes                    | No                           |

### tests/integration/ vs tests/unit/

| Aspect        | integration/           | unit/            |
| ------------- | ---------------------- | ---------------- |
| External deps | Yes (Sierra Chart DTC) | No               |
| Speed         | Slow (network I/O)     | Fast (in-memory) |
| Isolation     | Low                    | High             |
| Safety        | Use SIM account        | Always safe      |

### demos/ vs tools/

| Aspect       | demos/             | tools/                     |
| ------------ | ------------------ | -------------------------- |
| Purpose      | Show functionality | Debug/diagnose             |
| Audience     | Users/docs         | Developers                 |
| Requirements | Minimal            | May need external services |

---

## Running Tests

### All Tests (Pytest Suite)

```bash
# Run all pytest tests
pytest

# Run with coverage
pytest --cov=core --cov=panels --cov=services

# Run specific test category
pytest tests/test_panel1_comprehensive.py
pytest tests/test_performance_and_signals.py
```

### Unit Tests Only

```bash
pytest tests/unit/
```

### Integration Tests

```bash
# Requires Sierra Chart DTC server running
pytest tests/integration/
```

### Individual Tests

```bash
python tests/unit/test_mode_logic.py
python tests/integration/test_dtc_connection.py
```

---

## Theme System

The application uses three custom themes matching trading modes:

- **DEBUG**: Grey/silver monochrome (#2A2A2A) - for development
- **SIM**: White/neon blue (#FFFFFF) - for simulation trading
- **LIVE**: Black/gold (#0A0A0A) - for real trading

**Switch themes:**

- Hotkey: `Ctrl+Shift+M` (cycles DEBUG → SIM → LIVE)
- Toolbar buttons (if enabled)
- `DevToolbar` "Theme" button

**Theme files:**

- `config/theme.py` - Theme definitions and `switch_theme()` function
- `utils/theme_mixin.py` - `ThemeAwareMixin` for panels
- `utils/mode_selector.py` - Hotkey implementation

---

## Self-Healing System

The self-healing system automatically detects and fixes test failures:

**Files:**

- `selfheal.py` - Main self-healing system
- `tests/conftest.py` - DiagnosticRecorder for capturing test diagnostics

**Issue types detected:**

- BrokenSignal (HIGH) - Disconnected PyQt signals
- TimingRegression (MEDIUM) - Performance degradation
- SchemaMismatch (HIGH) - DTC message format errors
- DatabaseIssue (CRITICAL) - SQLite corruption

**Usage:**

```bash
# Runs automatically after test failures
pytest  # If tests fail, selfheal.py triggers

# Manual trigger
python selfheal.py

# View report
cat selfheal_report.json
```

---

## Development Workflow

### 1. Code Changes

Make changes to core/, panels/, services/, etc.

### 2. Run Tests

```bash
pytest  # Run all tests
```

### 3. Check Coverage

```bash
pytest --cov=. --cov-report=html
start htmlcov/index.html  # Windows
```

### 4. Debug Issues

```bash
# Use diagnostic tools
python tools/dtc_probe.py
python tools/dtc_diagnostic.py

# Test theme changes
python tools/theme_sandbox.py
```

### 5. Validate Integration

```bash
# Test with real Sierra Chart
python tests/integration/test_dtc_connection.py
```

---

## Documentation

- `STARTUP_VALIDATION.md` - Startup validation report
- `TEST_SUITE_SUMMARY.md` - Test execution summary
- `THEME_SYSTEM_UPDATE.md` - Theme system documentation
- `tests/README_TEST_SUITE.md` - Comprehensive test suite docs
- `tests/integration/README.md` - Integration test guide
- `tests/unit/README.md` - Unit test guide
- `demos/README.md` - Demo script guide

---

## Quick Reference

### Start Application

```bash
python main.py
```

### Run All Tests

```bash
pytest
```

### Test Theme Switching

```bash
python demos/demo_theme_switching.py
```

### Debug DTC Connection

```bash
python tests/integration/test_dtc_connection.py
```

### View Test Coverage

```bash
pytest --cov=. --cov-report=term-missing
```

---

**Status:** Production Ready
**Branch:** claude/upload-entire-file-011CUvy9JC1QTE42F7nntMSa
**Python Version:** 3.10+
**PyQt Version:** PyQt6
