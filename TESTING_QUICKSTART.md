# APPSIERRA Testing Quick Start Guide

Complete pytest-based diagnostic and self-healing suite for APPSIERRA.

## Installation

```bash
# Install all testing dependencies
pip install -r requirements-test.txt
```

## Quick Start

### Windows

```cmd
REM Install dependencies and run tests with coverage
run_tests.bat --install --coverage
```

### Linux/Mac

```bash
# Install dependencies and run tests with coverage
./run_tests.sh --install --coverage
```

## Manual Test Execution

### Run Complete Test Suite

```bash
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings
```

### Run Specific Test Files

```bash
# Panel1 tests (balance, mode switching)
pytest tests/test_panel1_comprehensive.py -v

# Panel2 tests (orders, positions, dirty-update guard)
pytest tests/test_panel2_comprehensive.py -v

# Panel3 tests (statistics, aggregation)
pytest tests/test_panel3_comprehensive.py -v

# Performance tests (latency <100ms, 500-event stress)
pytest tests/test_performance_and_signals.py -v
```

### Run by Test Markers

```bash
# Performance tests only
pytest -m performance

# Signal introspection only
pytest -m signals

# Integration tests only
pytest -m integration
```

## Self-Healing

### Automatic (Run After Test Failures)

```bash
# Run tests, then auto-trigger self-healing if failures occur
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings; \
if [ $? -ne 0 ]; then python selfheal.py; fi
```

### Manual Execution

```bash
# Run self-healing analysis
python selfheal.py

# View results
cat selfheal_report.json
```

## Test Suite Components

### 1. Fixtures (tests/conftest.py)

- `qtbot` - PyQt6 widget testing
- `mock_panel1/2/3` - Panel fixtures
- `mock_app_manager` - MainWindow fixture
- `diagnostic_recorder` - Records diagnostics to JSON
- `dtc_message_factory` - Creates DTC test messages
- `perf_timer` - Performance timing

### 2. Panel Tests

**test_panel1_comprehensive.py** (Panel1 - Balance/Investing)

- Trading mode tests (LIVE/SIM/DEBUG)
- Balance update tests
- Panel linking tests
- Theme refresh tests
- Coverage target: ≥90%

**test_panel2_comprehensive.py** (Panel2 - Live Trade)

- Order update tests (all statuses)
- Position update tests (long/short/flat)
- Dirty-update guard tests
- 500-event stress test
- Coverage target: ≥90%

**test_panel3_comprehensive.py** (Panel3 - Statistics)

- Metrics loading tests (all timeframes)
- Live data analysis tests
- Panel2→Panel3 data flow tests
- Database storage tests
- Coverage target: ≥90%

### 3. Performance Tests (test_performance_and_signals.py)

**Latency Tests** (Threshold: <100ms)

- DTC → Panel1 balance update
- DTC → Panel2 order update
- DTC → Panel2 position update
- DTC → Panel3 metrics load

**Stress Tests**

- 500 order updates (<2 seconds)
- 500 position updates (<2 seconds)
- 500 balance updates (<2 seconds)
- 500 mixed events (<2.5 seconds)

**Signal Introspection**

- Enumerate all PyQt6 signals
- Validate critical connections
- Export to signal_connections.json

**Database Checks**

- SQLite integrity check
- Schema consistency validation

### 4. Self-Healing System (selfheal.py)

**Detects:**

1. Broken Signals (HIGH severity) - Auto-fixable
2. Timing Regressions (MEDIUM severity)
3. Schema Mismatches (HIGH severity)
4. Database Issues (CRITICAL severity)

**Outputs:**

- `test_diagnostics.json` - Complete diagnostic data
- `signal_connections.json` - Signal-slot connections
- `selfheal_report.json` - Issues + patches

## Expected Output

### Successful Test Run

```
======================================================================
test_panel1_comprehensive.py .........                         [ 25%]
test_panel2_comprehensive.py ...............                   [ 63%]
test_panel3_comprehensive.py .............                     [ 95%]
test_performance_and_signals.py ..                             [100%]

---------- coverage: platform linux, python 3.10.0 -----------
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
panels/panel1.py          234     18    92%   45-48, 201-205
panels/panel2.py          312     22    93%   78-82, 156-162
panels/panel3.py          289     25    91%   99-103, 234-241
core/app_manager.py       456     38    92%   123-128, 345-352
-----------------------------------------------------
TOTAL                    1291    103    92%
======================================================================
TESTS PASSED!
======================================================================
```

### Test Failure with Self-Healing

```
======================================================================
TESTS FAILED (Exit code: 1)
======================================================================

Triggering Self-Healing System...

[SELFHEAL] Initializing self-healing system...
[SELFHEAL] Loaded diagnostics from: test_diagnostics.json
[SELFHEAL] Detecting issues...
[SELFHEAL] Found 3 issues
[SELFHEAL] Generating patches...
[SELFHEAL] Generated 1 patches
[SELFHEAL] Report exported to: selfheal_report.json

SELF-HEALING REPORT SUMMARY
======================================================================
Generated: 2025-11-08T21:30:00
Total Issues: 3
Auto-Fixable: 1
Patches Generated: 1

Severity Breakdown:
  HIGH: 2
  MEDIUM: 1

Issues by Type:
  BrokenSignal: 1
  TimingRegression: 1
  SchemaMismatch: 1

Recommendations:
  1. Signals: 1 broken signal connections. Review AppManager._setup_cross_panel_linkage()
  2. Performance: 1 timing violations detected. Consider optimizing hot paths
  3. Schema: 1 schema mismatches. Verify DTC message schema
======================================================================
```

## File Structure

```
APPSIERRA/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # Pytest fixtures
│   ├── test_panel1_comprehensive.py         # Panel1 tests
│   ├── test_panel2_comprehensive.py         # Panel2 tests
│   ├── test_panel3_comprehensive.py         # Panel3 tests
│   ├── test_performance_and_signals.py      # Performance + signals
│   └── README_TEST_SUITE.md                 # Detailed documentation
├── selfheal.py                              # Self-healing system
├── pytest.ini                               # Pytest configuration
├── requirements-test.txt                    # Test dependencies
├── run_tests.sh                             # Linux/Mac test runner
├── run_tests.bat                            # Windows test runner
└── TESTING_QUICKSTART.md                    # This file
```

## Output Artifacts

After running tests:

```
test_diagnostics.json       # Diagnostic data (signals, timing, errors, memory, DB)
signal_connections.json     # PyQt6 signal-slot connections
selfheal_report.json        # Self-healing analysis and patches
pytest.log                  # Detailed pytest log
.coverage                   # Coverage data
htmlcov/                    # HTML coverage report
```

## Common Commands

```bash
# Install and run everything
pip install -r requirements-test.txt
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings
python selfheal.py  # If tests failed

# Run specific test with verbose output
pytest tests/test_panel2_comprehensive.py::TestPanel2OrderUpdates::test_on_order_update_filled -vv

# Run only fast tests (exclude slow/performance)
pytest -m "not slow and not performance"

# Generate HTML coverage report
pytest --cov=panels --cov=core --cov-report=html
# View: open htmlcov/index.html

# Run in parallel (faster)
pytest -n auto

# Run with timeout (prevent hanging)
pytest --timeout=300
```

## Troubleshooting

### PyQt6 Not Found

```bash
pip install PyQt6 pytest-qt
```

### Pytest Not Found

```bash
pip install pytest pytest-cov
```

### Tests Timeout

```bash
# Increase timeout
pytest --timeout=600
```

### Permission Denied (Linux/Mac)

```bash
chmod +x run_tests.sh selfheal.py
```

## Next Steps

1. **Run Tests**: `./run_tests.sh --install --coverage` (or `run_tests.bat` on Windows)
2. **Review Coverage**: Open `htmlcov/index.html`
3. **Check Diagnostics**: Review `test_diagnostics.json`
4. **Apply Fixes**: If failures, review `selfheal_report.json`
5. **Iterate**: Re-run tests after applying fixes

## Support

See `tests/README_TEST_SUITE.md` for comprehensive documentation including:

- Detailed test descriptions
- Fixture reference
- CI/CD integration examples
- Advanced usage patterns
