# Integration Tests

Integration tests that require external services (Sierra Chart DTC server, database, etc.)

## Requirements

- Sierra Chart running with DTC server enabled
- DTC server listening on 127.0.0.1:11099 (configurable in config/settings.py)
- Live or SIM account configured

## Tests

### test_dtc_connection.py

Tests DTC server connectivity, handshake, and account balance request.

**Usage:**

```bash
python tests/integration/test_dtc_connection.py
```

## Running Integration Tests

Integration tests can be run individually or via pytest:

```bash
# Run all integration tests
pytest tests/integration/

# Run specific test
python tests/integration/test_dtc_connection.py
```

## Notes

- Integration tests are slower than unit tests (network I/O)
- Requires Sierra Chart DTC server to be running
- May produce side effects (actual orders, positions if misconfigured)
- Use SIM account for safety
