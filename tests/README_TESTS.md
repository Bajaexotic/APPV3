# APPSIERRA Test Suite Documentation

## Overview

Comprehensive test suite validating the two most critical aspects of APPSIERRA:

1. **UI Data Flow** - Terminal data reaches and updates UI panels correctly
2. **Mode Routing** - SIM/LIVE order segregation prevents catastrophic trading errors

---

## Test Files

### `test_integration.py`

**Purpose:** Validate complete data pipeline from Sierra Chart → DTC → UI

**Test Classes:**

1. `TestUIDataPipeline` - Message flow and UI updates
2. `TestSignalConnections` - PyQt signal/slot validation
3. `TestPanelStateSynchronization` - Panel state consistency
4. `TestEndToEndPerformance` - Latency measurements
5. `TestErrorHandling` - Graceful error recovery

**Coverage:**

- ✅ Position updates reach all panels
- ✅ Order updates trigger UI refresh (<30ms)
- ✅ Balance updates propagate to Panel1
- ✅ Signals exist and are connected
- ✅ Panels share same state instance
- ✅ High-frequency updates maintain performance
- ✅ Malformed messages don't crash UI

---

### `test_mode_routing.py`

**Purpose:** Validate SIM/LIVE segregation and theme switching

**Test Classes:**

1. `TestAccountDetection` - Account → mode mapping
2. `TestOrderRouting` - Order acceptance/rejection logic
3. `TestPositionSegregation` - Position filtering
4. `TestThemeSwitching` - Theme loading on mode change
5. `TestEnvironmentConfiguration` - Config validation
6. `TestModeSwitchEdgeCases` - Error conditions
7. `TestFullModeScenario` - End-to-end workflow

**Coverage:**

- ✅ SIM accounts trigger SIM mode
- ✅ LIVE accounts trigger LIVE mode
- ✅ SIM orders rejected in LIVE mode ⚠️ **CRITICAL**
- ✅ LIVE orders rejected in SIM mode ⚠️ **CRITICAL**
- ✅ SIM positions invisible in LIVE mode
- ✅ LIVE positions invisible in SIM mode
- ✅ Theme switches on mode change
- ✅ Mode pill/badge updates correctly
- ✅ Rapid mode switches maintain consistency

---

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
# Integration tests only
pytest tests/test_integration.py

# Mode routing tests only
pytest tests/test_mode_routing.py
```

### Run by Marker

```bash
# Integration tests (both files)
pytest -m integration

# Performance tests only
pytest -m performance

# Signal introspection tests
pytest -m signals
```

### Run Specific Test Class

```bash
pytest tests/test_mode_routing.py::TestOrderRouting
```

### Run Specific Test

```bash
pytest tests/test_mode_routing.py::TestOrderRouting::test_sim_orders_ignored_in_live_mode
```

### Verbose Output

```bash
pytest tests/ -v
```

### Show Print Statements

```bash
pytest tests/ -s
```

### Stop on First Failure

```bash
pytest tests/ -x
```

### Run with Coverage

```bash
pytest tests/ --cov=core --cov=panels --cov=services
```

---

## Test Markers

Tests are tagged with markers for selective execution:

| Marker                     | Purpose                      | Example          |
| -------------------------- | ---------------------------- | ---------------- |
| `@pytest.mark.integration` | End-to-end integration tests | Most tests       |
| `@pytest.mark.performance` | Latency/throughput tests     | UI timing tests  |
| `@pytest.mark.signals`     | PyQt signal validation       | Connection tests |

**Usage:**

```bash
# Run only performance tests
pytest -m performance

# Skip performance tests (faster)
pytest -m "not performance"
```

---

## Fixtures (conftest.py)

### Core Fixtures

| Fixture               | Purpose                        | Scope    |
| --------------------- | ------------------------------ | -------- |
| `qapp`                | QApplication instance          | session  |
| `qtbot`               | PyQt widget tester             | function |
| `diagnostic_recorder` | Test metrics recorder          | session  |
| `state_manager`       | Real StateManager with mock DB | function |
| `mock_state_manager`  | Fully mocked StateManager      | function |

### Panel Fixtures

| Fixture       | Returns                | Notes                                           |
| ------------- | ---------------------- | ----------------------------------------------- |
| `mock_panel1` | Real Panel1 or mock    | Balance/stats panel                             |
| `mock_panel2` | Real Panel2 or mock    | Orders/positions panel                          |
| `mock_panel3` | Real Panel3 or mock    | Analytics panel                                 |
| `all_panels`  | Dict with all 3 panels | `{"panel1": ..., "panel2": ..., "panel3": ...}` |

### DTC Message Factory

| Method                                     | Returns         | Example  |
| ------------------------------------------ | --------------- | -------- |
| `logon_response(success=True)`             | Logon message   | Type 2   |
| `order_update(symbol, qty, price, status)` | Order update    | Type 300 |
| `position_update(symbol, qty, avg_price)`  | Position update | Type 306 |
| `balance_update(balance)`                  | Balance update  | Type 600 |

**Usage:**

```python
def test_example(dtc_message_factory):
    msg = dtc_message_factory["order_update"](
        symbol="MESZ25",
        qty=1,
        price=6000.0,
        status=3  # Filled
    )
```

### Mode Routing Fixtures (New)

| Fixture              | Purpose                | Returns              |
| -------------------- | ---------------------- | -------------------- |
| `mock_trading_modes` | SIM/LIVE/DEBUG configs | Dict                 |
| `mode_detector`      | Account→mode mapper    | Function             |
| `order_filter`       | Order acceptance logic | Function             |
| `theme_loader`       | Mock theme switcher    | ThemeLoader instance |

**Usage:**

```python
def test_mode_detection(mode_detector):
    assert mode_detector("SIM1") == "SIM"
    assert mode_detector("120005") == "LIVE"

def test_order_filtering(order_filter):
    # SIM mode + SIM order = accept
    assert order_filter("SIM", "SIM1") == True

    # SIM mode + LIVE order = reject
    assert order_filter("SIM", "120005") == False
```

### Performance Fixtures

| Fixture      | Purpose        | Methods                             |
| ------------ | -------------- | ----------------------------------- |
| `perf_timer` | High-res timer | `start()`, `stop()`, `elapsed_ms()` |

**Usage:**

```python
def test_performance(perf_timer):
    perf_timer.start()
    # ... code to measure ...
    elapsed = perf_timer.stop()
    assert elapsed < 30.0  # ms
```

### Database Fixtures

| Fixture                  | Purpose                    |
| ------------------------ | -------------------------- |
| `temp_db_path`           | Temporary DB file path     |
| `db_consistency_checker` | SQLite integrity validator |

---

## Diagnostic Recording

All tests automatically record diagnostic data to `test_diagnostics.json`:

**Recorded Metrics:**

- Signal connections (name, sender, receiver, connected)
- Timing events (event, duration, threshold, passed)
- Errors (test name, type, message, stack trace)
- Memory snapshots (component, bytes)
- Database checks (check name, passed, message)

**Accessing in Tests:**

```python
def test_example(diagnostic_recorder):
    diagnostic_recorder.record_signal(
        signal_name="pnlChanged",
        sender="state_manager",
        receiver="panel1",
        connected=True
    )

    diagnostic_recorder.record_timing(
        event_name="ui_update",
        duration_ms=15.5,
        threshold_ms=30.0
    )
```

**Output Location:** `test_diagnostics.json` (generated after test run)

---

## Critical Test Scenarios

### ⚠️ MUST PASS - Trading Safety

These tests prevent financial disasters:

| Test                                      | File                 | What It Prevents            |
| ----------------------------------------- | -------------------- | --------------------------- |
| `test_sim_orders_ignored_in_live_mode`    | test_mode_routing.py | SIM orders on LIVE account  |
| `test_live_orders_ignored_in_sim_mode`    | test_mode_routing.py | LIVE orders on SIM account  |
| `test_sim_positions_ignored_in_live_mode` | test_mode_routing.py | False position data in LIVE |
| `test_live_positions_ignored_in_sim_mode` | test_mode_routing.py | False position data in SIM  |
| `test_account_detection_case_insensitive` | test_mode_routing.py | Mode detection failures     |

**Run critical tests only:**

```bash
pytest tests/test_mode_routing.py::TestOrderRouting -v
```

---

## Performance Thresholds

| Metric                 | Threshold | Test                                               |
| ---------------------- | --------- | -------------------------------------------------- |
| Order update → UI      | < 30ms    | `test_order_update_triggers_ui_refresh`            |
| DTC → UI total latency | < 50ms    | `test_message_to_ui_latency_under_threshold`       |
| High-frequency updates | < 5ms avg | `test_high_frequency_updates_maintain_performance` |

**Run performance tests:**

```bash
pytest -m performance -v
```

---

## Expected Test Output

### Success (All Pass)

```
tests/test_integration.py ............................ [ 55%]
tests/test_mode_routing.py ............................ [100%]

=============== 42 passed in 12.34s ===============

[DIAGNOSTICS] Exported to: test_diagnostics.json
```

### Failure (Critical)

```
FAILED tests/test_mode_routing.py::TestOrderRouting::test_sim_orders_ignored_in_live_mode

AssertionError: SIM order was processed in LIVE mode (CRITICAL BUG)
```

**Action:** Fix immediately - this is a trading safety violation.

---

## Integration with Tools

Tests complement the diagnostic tools:

### Tools vs Tests

| Tool                    | Tests                |
| ----------------------- | -------------------- |
| **Run during trading**  | **Run in CI/dev**    |
| Live session monitoring | Controlled scenarios |
| Actual data             | Mock data            |
| Continuous              | On-demand            |

### Combined Workflow

**Pre-Trading Validation:**

```bash
# 1. Run tests (prove correctness)
pytest tests/

# 2. Run tools (verify live system)
python tools/run_code_audit.py --preset ui

# 3. If both pass → safe to trade
```

**Continuous Integration:**

```yaml
# .github/workflows/ci.yml
- name: Run Test Suite
  run: pytest tests/ -v --cov

- name: Run Tool Audit
  run: python tools/run_code_audit.py --preset full
```

---

## Debugging Failed Tests

### Use pytest's built-in debugger

```bash
pytest tests/test_mode_routing.py --pdb
```

### Capture full output

```bash
pytest tests/ -vv -s --tb=long
```

### Run single test with max detail

```bash
pytest tests/test_mode_routing.py::TestOrderRouting::test_sim_orders_ignored_in_live_mode -vv -s --tb=long
```

### Check diagnostic output

```bash
cat test_diagnostics.json | jq '.errors'
cat test_diagnostics.json | jq '.timing'
```

---

## Common Issues

### PyQt6 Import Errors

```
ImportError: No module named 'PyQt6'
```

**Solution:**

```bash
poetry add pytest-qt PyQt6 --dev
# or
pip install pytest-qt PyQt6
```

### Tests Hang on Qt Signals

**Issue:** QtBot waiting forever for signal

**Solution:** Increase timeout or use `qtbot.waitUntil()` with condition:

```python
# Instead of:
qtbot.wait(5000)

# Use:
qtbot.waitUntil(lambda: panel.value == expected, timeout=5000)
```

### Mock vs Real Fixtures

**Issue:** Test behavior differs from production

**Solution:** Use real fixtures when testing integration:

```python
# Use real panel
def test_real_behavior(mock_panel1):  # Returns real Panel1 if available
    pass

# Force mock
def test_mock_behavior(mock_state_manager):  # Always returns mock
    pass
```

---

## Extending Tests

### Add New Test

```python
@pytest.mark.integration
class TestNewFeature:
    def test_new_behavior(self, qtbot, all_panels):
        """Describe what this validates"""
        # Arrange
        panel1 = all_panels["panel1"]

        # Act
        panel1.new_method()
        qtbot.wait(100)

        # Assert
        assert panel1.state == expected
```

### Add New Fixture

Edit `tests/conftest.py`:

```python
@pytest.fixture
def my_fixture():
    """Description"""
    obj = MyObject()
    yield obj
    obj.cleanup()
```

### Add New Marker

Edit `tests/conftest.py`:

```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "mymarker: description of marker"
    )
```

---

## Best Practices

1. **Test Isolation** - Each test should run independently
2. **Clear Assertions** - Use descriptive error messages
3. **Minimal Mocking** - Use real objects when possible
4. **Fast Tests** - Keep total runtime under 30 seconds
5. **Meaningful Names** - Test name should explain what it validates
6. **One Concept** - Each test validates one specific behavior
7. **Diagnostic Recording** - Record metrics for analysis

---

## Coverage Goals

| Module             | Target | Critical |
| ------------------ | ------ | -------- |
| core.state_manager | 80%    | Yes ⚠️   |
| core.data_bridge   | 75%    | Yes ⚠️   |
| panels.panel1      | 70%    | Medium   |
| panels.panel2      | 70%    | Medium   |
| panels.panel3      | 60%    | Low      |
| services.\*        | 65%    | Medium   |

**Check coverage:**

```bash
pytest tests/ --cov=core --cov=panels --cov-report=html
open htmlcov/index.html
```

---

## Quick Reference

### Run Everything

```bash
pytest tests/ -v
```

### Fast (Skip Performance)

```bash
pytest tests/ -m "not performance"
```

### Critical Only

```bash
pytest tests/test_mode_routing.py::TestOrderRouting -v
```

### With Coverage

```bash
pytest tests/ --cov --cov-report=term-missing
```

### Debug Mode

```bash
pytest tests/test_mode_routing.py::test_name --pdb -vv -s
```

---

## See Also

- `tools/AUDIT_GUIDE.md` - Tool audit system documentation
- `REFACTOR_COMPLETE.md` - Tools refactor summary
- PyTest documentation: <https://docs.pytest.org/>
- pytest-qt documentation: <https://pytest-qt.readthedocs.io/>
