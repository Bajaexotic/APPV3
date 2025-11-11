# APPSIERRA Test Suite

Comprehensive pytest-based diagnostic and self-healing suite for the APPSIERRA PyQt6 trading application.

## Overview

This test suite provides:

- **Functional Tests**: Panel1, Panel2, Panel3 functionality
- **Performance Tests**: DTC→Panel latency (<100ms), 500-event stress tests
- **Signal Introspection**: PyQt6 signal-slot connection validation
- **Self-Healing**: Automatic issue detection and patch generation
- **Coverage**: ≥90% target across panels and core modules

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or install individual components:
pip install pytest pytest-cov pytest-qt PyQt6
```

## Running Tests

### Quick Test Run

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_panel1_comprehensive.py

# Run specific test class
pytest tests/test_panel2_comprehensive.py::TestPanel2OrderUpdates

# Run specific test
pytest tests/test_panel3_comprehensive.py::TestPanel3MetricsLoading::test_load_metrics_for_timeframe_live
```

### With Coverage

```bash
# Run with coverage report
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings

# Generate HTML coverage report
pytest --cov=panels --cov=core --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Performance Tests

```bash
# Run only performance tests
pytest -m performance

# Run only signal introspection
pytest -m signals

# Run integration tests
pytest -m integration
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Test Structure

### conftest.py

Provides pytest fixtures:

- `qtbot` - PyQt6 widget testing
- `mock_panel1` - Panel1 (Balance/Investing)
- `mock_panel2` - Panel2 (Live Trade)
- `mock_panel3` - Panel3 (Statistics)
- `mock_app_manager` - MainWindow/AppManager
- `diagnostic_recorder` - Records test diagnostics
- `dtc_message_factory` - Creates DTC test messages
- `perf_timer` - High-resolution performance timer

### Test Files

#### test_panel1_comprehensive.py

Tests for Panel1 (Balance/Investing panel):

- Trading mode switching (LIVE/SIM/DEBUG)
- Account balance updates
- Panel linking (Panel1 ↔ Panel3)
- Theme refresh
- UI state integrity

**Key Tests:**

- `test_set_trading_mode_live()` - LIVE mode activation
- `test_set_account_balance_positive()` - Balance updates with latency measurement
- `test_balance_update_rapid_succession()` - Stress test with 5 rapid updates

#### test_panel2_comprehensive.py

Tests for Panel2 (Live Trade panel):

- Order updates (DTC ORDER_UPDATE messages)
- Position updates (DTC POSITION_UPDATE messages)
- Dirty-update guard (prevents duplicate updates)
- Trade signal emissions
- Timeframe pill interactions

**Key Tests:**

- `test_on_order_update_filled()` - Filled order handling with latency
- `test_duplicate_order_update_guard()` - Duplicate prevention
- `test_panel2_stress_500_events()` - 500 order updates stress test

#### test_panel3_comprehensive.py

Tests for Panel3 (Statistics panel):

- Statistical metrics loading and refresh
- Timeframe aggregation (LIVE, DAY, WEEK, MONTH, YEAR, ALL)
- Live trade data analysis
- Panel2 → Panel3 data flow
- Database storage and retrieval

**Key Tests:**

- `test_load_metrics_all_timeframes()` - All 6 timeframes
- `test_analyze_and_store_trade_snapshot()` - Live data analysis
- `test_aggregate_all_timeframes_sequential()` - Complete aggregation workflow

#### test_performance_and_signals.py

Performance and signal introspection:

**Performance Tests:**

- `test_dtc_to_panel1_balance_latency()` - DTC→Panel1 < 100ms
- `test_dtc_to_panel2_order_latency()` - DTC→Panel2 < 100ms
- `test_500_order_updates_stress()` - 500 events < 2 seconds
- `test_500_mixed_events_stress()` - Mixed orders/positions/balances

**Signal Tests:**

- `test_enumerate_all_signals()` - Introspect all PyQt6 signals
- `test_validate_critical_connections()` - Verify critical signal connections

**Database Tests:**

- `test_db_integrity_check()` - SQLite PRAGMA integrity_check

## Self-Healing System

### Automatic Execution

After running pytest, if any tests fail, automatically trigger self-healing:

```bash
# Run tests and auto-heal on failure
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings; \
if [ $? -ne 0 ]; then python selfheal.py; fi
```

### Manual Execution

```bash
# Run self-healing analysis
python selfheal.py

# Specify custom paths
python selfheal.py --diagnostics test_diagnostics.json --pytest-log pytest.log --output my_report.json
```

### What Self-Heal Detects

1. **Broken Signals** (HIGH severity, auto-fixable)
   - Disconnected PyQt6 signal-slot connections
   - Generates patch diffs for `core/app_manager.py`

2. **Timing Regressions** (MEDIUM severity)
   - Events exceeding latency thresholds
   - Provides performance optimization recommendations

3. **Schema Mismatches** (HIGH severity)
   - DTC message format inconsistencies
   - KeyError exceptions in message handling

4. **Database Issues** (CRITICAL severity)
   - SQLite integrity check failures
   - Recommends VACUUM or rebuild

### Output Files

- `test_diagnostics.json` - Complete diagnostic data (signals, timing, errors, memory, DB checks)
- `signal_connections.json` - All PyQt6 signal-slot connections
- `selfheal_report.json` - Self-healing analysis and patches

## Coverage Goals

Target ≥90% coverage across:

- `panels/panel1.py`
- `panels/panel2.py`
- `panels/panel3.py`
- `core/app_manager.py`
- `core/data_bridge.py`
- `core/state_manager.py`

## Example Command Set

```bash
# 1. Run full test suite with coverage
pytest -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings

# 2. If tests pass, generate HTML coverage report
pytest --cov=panels --cov=core --cov-report=html

# 3. If tests fail, run self-healing
python selfheal.py

# 4. Review self-healing report
cat selfheal_report.json

# 5. Re-run tests after applying fixes
pytest -q --cov=panels --cov=core --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: APPSIERRA Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements-test.txt
      - run: pytest --cov=panels --cov=core --cov-report=xml
      - run: python selfheal.py || true
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### PyQt6 Import Errors

If PyQt6 tests are skipped:

```bash
pip install PyQt6 pytest-qt
```

### Coverage Not Working

```bash
pip install pytest-cov coverage[toml]
```

### Tests Timeout

Increase timeout in pytest.ini or use:

```bash
pytest --timeout=600
```

### Memory Issues

Run with memory profiling:

```bash
pytest -m performance --memprof
```

## Advanced Usage

### Filter by Markers

```bash
# Run only integration tests
pytest -m integration

# Run everything except slow tests
pytest -m "not slow"

# Run performance AND signals tests
pytest -m "performance and signals"
```

### Verbose Output

```bash
# Very verbose
pytest -vv

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

### Custom Diagnostic Path

```bash
# Export diagnostics to custom location
pytest --junit-xml=results.xml
python selfheal.py --diagnostics test_diagnostics.json --output reports/selfheal_$(date +%Y%m%d).json
```

## Contributing

When adding new tests:

1. Follow existing test structure (SECTION markers, docstrings)
2. Use `diagnostic_recorder` to record events
3. Parametrize tests when testing multiple scenarios
4. Keep latency tests under threshold (100ms for DTC→Panel)
5. Add appropriate markers (@pytest.mark.integration, etc.)

## License

Part of the APPSIERRA project.
