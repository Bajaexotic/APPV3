# Unit Tests

Fast unit tests that don't require external dependencies.

## Tests

### test_mode_logic.py

Tests trading mode switching logic (DEBUG/SIM/LIVE cycling).

### test_mode_switching.py

Tests mode switching with theme updates.

### test_balance_debug.py

Tests balance update logic and formatting.

### test_debug_subsystem.py

Tests debug subsystem functionality.

### test_terminal_output.py

Tests terminal output formatting and colors.

### test_dtc_messages.py

Tests DTC message creation and validation (mocked).

## Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run specific test
python tests/unit/test_mode_logic.py

# Run with coverage
pytest tests/unit/ --cov=core --cov=panels
```

## Characteristics

- Fast (no I/O, all in-memory)
- No external dependencies
- Can run offline
- Safe (no side effects)
