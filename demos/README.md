# APPSIERRA Demonstration Scripts

This directory contains demonstration and validation scripts.

## Contents

### demo_test_run.py

Simulates successful test execution (39 tests, 92% coverage).
Shows expected pytest behavior when all tests pass.

### demo_test_failure.py

Simulates test failures and self-healing system response.
Demonstrates automatic issue detection and patch generation.

### demo_theme_switching.py

Demonstrates DEBUG/SIM/LIVE theme switching functionality.
Shows theme definitions and cycling behavior.

## Usage

Run any demo script directly:

```bash
python demos/demo_test_run.py
python demos/demo_test_failure.py
python demos/demo_theme_switching.py
```

These scripts are for validation and demonstration purposes only.
They do not require PyQt6 or external dependencies.
