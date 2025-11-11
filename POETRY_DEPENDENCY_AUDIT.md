# Poetry Dependency Audit Results

## Summary

Analyzed the codebase to ensure all imported packages are declared in `pyproject.toml` for Poetry management.

## Changes Made

Added four missing dependencies to `pyproject.toml`:

1. **sqlmodel** ^0.0.14
   - Used in: `data/db_engine.py`, `data/schema.py`, `data/schema_clean.py`
   - Purpose: ORM combining SQLAlchemy and Pydantic

2. **psutil** ^7.0.0
   - Used in: `ui/debug_console.py`
   - Purpose: Process and system monitoring utilities

3. **numpy** ^2.0.0
   - Used in: `utils/color_utils.py`
   - Purpose: Array computing and numerical operations

4. **pyyaml** ^6.0.0
   - Used in: `core/error_policy.py`, `validate_config.py`
   - Purpose: YAML configuration file parsing

## Version Selection

All version constraints were matched to existing versions in `poetry.lock`:

- sqlmodel: Not in lock (will be added on next `poetry install`)
- psutil: 7.1.3 in lock -> using ^7.0.0 constraint
- numpy: 2.3.4 in lock -> using ^2.0.0 constraint
- pyyaml: 6.0.3 in lock -> using ^6.0.0 constraint

## Next Steps

**REQUIRED ON WINDOWS:**

1. Update Poetry lock file:

   ```cmd
   poetry lock --no-update
   ```

2. Install all dependencies:

   ```cmd
   poetry install
   ```

3. Verify all dependencies are resolved:

   ```cmd
   poetry show --with dev
   ```

4. Run the audit tool to confirm:

   ```cmd
   python tools/poetry_audit.py
   ```

## Current Dependency Status

### Production Dependencies (12)

- PyQt6 ^6.0.0
- pyqtgraph ^0.13.0
- pydantic ^2.0.0
- sqlmodel ^0.0.14 (NEW)
- structlog ^24.0.0
- blinker ^1.7.0
- orjson ^3.9.0
- colorio ^0.12.18
- colorspacious ^1.1.2
- psutil ^7.0.0 (NEW)
- numpy ^2.0.0 (NEW)
- pyyaml ^6.0.0 (NEW)

### Dev Dependencies (12)

- ruff ^0.1.0
- pre-commit ^3.0.0
- pytest ^7.0.0
- pytest-cov ^4.0.0
- pytest-qt ^4.0.0
- bandit ^1.7.0
- mypy ^1.0.0
- alembic ^1.13.0
- watchdog ^3.0.0
- pyinstaller ^6.0.0
- memory-profiler ^0.61.0
- py-spy ^0.3.14

## Files Reference

### Requirements Files Status

- `requirements.txt`: Contains 154 packages (likely conda/global export) - can be deprecated
- `requirements-test.txt`: Focused test requirements - can be deprecated once Poetry is confirmed working

**Recommendation**: Once Poetry is fully operational and verified, these requirements\*.txt files can be removed as pyproject.toml becomes the single source of truth.

## Audit Tool

The `tools/poetry_audit.py` script:

- Scans all Python files for imports
- Compares against Poetry-managed packages
- Identifies missing and unused dependencies
- Filters out stdlib, local modules, and known sub-dependencies

Run it anytime to verify dependency hygiene.
