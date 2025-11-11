# Development Setup Guide for APPSIERRA

This guide covers the complete modern Python development workflow for APPSIERRA, including all tools and their usage.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Development Tools](#development-tools)
3. [Tool Verification](#tool-verification)
4. [Daily Workflow](#daily-workflow)
5. [Troubleshooting](#troubleshooting)

---

## Initial Setup

### 1. Install Dependencies

```bash
# Install all dependencies (including dev tools)
poetry install

# Activate the virtual environment
poetry shell
```

### 2. Install Pre-commit Hooks

```bash
# Install git hooks
poetry run pre-commit install

# (Optional) Run on all files to test
poetry run pre-commit run --all-files
```

### 3. Configure Database (Optional)

If using PostgreSQL with Alembic:

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/appsierra"

# Verify Alembic configuration
poetry run alembic current
```

---

## Development Tools

### 🔍 Tool 1: Ruff (Linting & Formatting)

**Purpose**: Fast Python linter and formatter (replaces black, isort, flake8)

**Configuration**: `ruff.toml`, `pyproject.toml` (tool.ruff)

**Usage**:

```bash
# Check for linting issues
poetry run ruff check .

# Auto-fix linting issues
poetry run ruff check --fix .

# Format code
poetry run ruff format .

# Check specific file
poetry run ruff check path/to/file.py
```

**Integrated**: ✅ Pre-commit hook, ✅ Watchdog

---

### 🔎 Tool 2: Mypy (Type Checking)

**Purpose**: Static type checker for Python

**Configuration**: `pyproject.toml` ([tool.mypy])

**Usage**:

```bash
# Type check entire project
poetry run mypy .

# Type check specific directory
poetry run mypy config/ core/

# Type check with verbose output
poetry run mypy --verbose .

# Generate HTML report
poetry run mypy --html-report ./mypy-report .
```

**Integrated**: ✅ Pre-commit hook, ✅ Watchdog

---

### 🧪 Tool 3: Pytest (Testing)

**Purpose**: Testing framework with coverage

**Configuration**: `pyproject.toml` ([tool.pytest.ini_options], [tool.coverage])

**Usage**:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_trade_metrics.py

# Run tests matching pattern
poetry run pytest -k "test_connection"

# Run with verbose output
poetry run pytest -v --tb=short

# Generate HTML coverage report
poetry run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

**Test Markers**:

```bash
# Run only unit tests
poetry run pytest -m unit

# Skip slow tests
poetry run pytest -m "not slow"

# Run only UI tests
poetry run pytest -m ui
```

**Integrated**: ✅ Watchdog

---

### 🔒 Tool 4: Bandit (Security)

**Purpose**: Security vulnerability scanner

**Configuration**: `pyproject.toml` ([tool.bandit])

**Usage**:

```bash
# Security scan
poetry run bandit -r .

# Scan with config file
poetry run bandit -r . -c pyproject.toml

# Only high severity issues
poetry run bandit -r . -ll

# Generate JSON report
poetry run bandit -r . -f json -o bandit-report.json
```

**Integrated**: ✅ Pre-commit hook

---

### 🗃️ Tool 5: Alembic (Database Migrations)

**Purpose**: Database migration tool for PostgreSQL

**Configuration**: `alembic.ini`, `alembic/env.py`

**Usage**:

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add users table"

# Apply migrations
poetry run alembic upgrade head

# Revert one migration
poetry run alembic downgrade -1

# Show current version
poetry run alembic current

# Show migration history
poetry run alembic history --verbose

# Downgrade to specific revision
poetry run alembic downgrade <revision_id>
```

**Setup Required**:

1. Set `DATABASE_URL` environment variable
2. Update `alembic/env.py` to import your SQLAlchemy models
3. Update `alembic.ini` with your database connection

See `alembic/README` for detailed instructions.

---

### 👀 Tool 6: Watchdog (File Monitoring)

**Purpose**: Auto-run tasks on file changes

**Configuration**: `dev_watcher.py`

**Usage**:

```bash
# Watch and lint on changes
poetry run python dev_watcher.py --mode lint

# Watch and test on changes
poetry run python dev_watcher.py --mode test

# Watch and run full checks (lint + mypy + test)
poetry run python dev_watcher.py --mode full

# Custom debounce time
poetry run python dev_watcher.py --mode lint --debounce 2.0

# Watch specific directory
poetry run python dev_watcher.py --mode lint --path ./services
```

**Modes**:

- `lint`: Run ruff on file changes
- `test`: Run pytest on file changes
- `full`: Run ruff + mypy + pytest
- `restart`: Restart application (requires custom implementation)

---

### 📦 Tool 7: PyInstaller (Packaging)

**Purpose**: Create standalone executable

**Configuration**: `appsierra.spec`, `build.py`

**Usage**:

```bash
# Build with spec file (recommended)
poetry run pyinstaller appsierra.spec

# Or use helper script
poetry run python build.py

# Clean build
poetry run python build.py --clean

# Build as single file
poetry run python build.py --onefile

# Debug build (with console)
poetry run python build.py --debug
```

**Output**: `dist/APPSIERRA/` directory with executable

**Notes**:

- Update `appsierra.spec` to include data files (images, configs)
- Set `console=False` for GUI-only mode
- Add missing imports to `hiddenimports` list

---

### 📊 Tool 8: Memory Profiler (Performance)

**Purpose**: Profile memory usage

**Usage**:

```bash
# Profile specific function
# Add @profile decorator to function first
poetry run python -m memory_profiler main.py

# Line-by-line memory usage
poetry run mprof run main.py
poetry run mprof plot

# Profile with time intervals
poetry run mprof run --interval 0.1 main.py
```

**Example**:

```python
from memory_profiler import profile

@profile
def my_function():
    # Your code here
    pass
```

---

### 🔥 Tool 9: py-spy (Performance Profiling)

**Purpose**: Sampling profiler (no code changes needed)

**Usage**:

```bash
# Profile running application (by PID)
poetry run py-spy top --pid <PID>

# Record flamegraph
poetry run py-spy record -o profile.svg -- python main.py

# Live top view
poetry run py-spy top -- python main.py

# Dump current stack traces
poetry run py-spy dump --pid <PID>
```

**Output**: Generates SVG flamegraphs for performance analysis

---

## Tool Verification

Run these commands to verify all tools are working:

```bash
# 1. Ruff
poetry run ruff check . && echo "✅ Ruff OK"

# 2. Mypy
poetry run mypy --version && echo "✅ Mypy OK"

# 3. Pytest
poetry run pytest --version && echo "✅ Pytest OK"

# 4. Bandit
poetry run bandit --version && echo "✅ Bandit OK"

# 5. Alembic
poetry run alembic --version && echo "✅ Alembic OK"

# 6. Watchdog
poetry run python dev_watcher.py --help && echo "✅ Watchdog OK"

# 7. PyInstaller
poetry run pyinstaller --version && echo "✅ PyInstaller OK"

# 8. Memory Profiler
poetry run python -m memory_profiler --version && echo "✅ Memory Profiler OK"

# 9. py-spy
poetry run py-spy --version && echo "✅ py-spy OK"

# Pre-commit
poetry run pre-commit --version && echo "✅ Pre-commit OK"
```

---

## Daily Workflow

### Morning Setup

```bash
# 1. Activate environment
poetry shell

# 2. Update dependencies (if needed)
poetry install

# 3. Pull latest changes
git pull

# 4. Run pre-commit on all files
poetry run pre-commit run --all-files
```

### During Development

**Option A: Manual checks**

```bash
# Format and lint
poetry run ruff format .
poetry run ruff check --fix .

# Type check
poetry run mypy .

# Run tests
poetry run pytest -v
```

**Option B: Auto-watch (recommended)**

```bash
# Terminal 1: Run development watcher
poetry run python dev_watcher.py --mode full

# Terminal 2: Run your application
python main.py

# Edit files - watcher will auto-run checks
```

### Before Committing

```bash
# 1. Run all checks
poetry run ruff check .
poetry run mypy .
poetry run pytest
poetry run bandit -r .

# 2. Or use pre-commit
poetry run pre-commit run --all-files

# 3. Commit (hooks will run automatically)
git add .
git commit -m "Your message"
```

### Before Releasing

```bash
# 1. Run full test suite with coverage
poetry run pytest --cov --cov-report=html

# 2. Security scan
poetry run bandit -r . -ll

# 3. Type check
poetry run mypy .

# 4. Build executable
poetry run python build.py --clean

# 5. Test executable
cd dist/APPSIERRA
./APPSIERRA  # or APPSIERRA.exe on Windows
```

---

## Troubleshooting

### Poetry install fails

```bash
# Clear cache
poetry cache clear pypi --all

# Reinstall
rm poetry.lock
poetry install
```

### Pre-commit hooks fail

```bash
# Update hooks
poetry run pre-commit autoupdate

# Clean and reinstall
poetry run pre-commit clean
poetry run pre-commit install
```

### Mypy errors

```bash
# Install missing type stubs
poetry add --group dev types-requests

# Clear cache
poetry run mypy --cache-clear .
```

### PyInstaller build fails

```bash
# Clean build
poetry run python build.py --clean

# Debug mode to see errors
poetry run python build.py --debug

# Check missing imports in appsierra.spec
```

### Database migrations fail

```bash
# Check database connection
psql $DATABASE_URL

# Reset migrations (DANGER: loses data)
poetry run alembic downgrade base
poetry run alembic upgrade head
```

---

## Additional Resources

- **Ruff**: <https://docs.astral.sh/ruff/>
- **Mypy**: <https://mypy.readthedocs.io/>
- **Pytest**: <https://docs.pytest.org/>
- **Bandit**: <https://bandit.readthedocs.io/>
- **Alembic**: <https://alembic.sqlalchemy.org/>
- **Watchdog**: <https://python-watchdog.readthedocs.io/>
- **PyInstaller**: <https://pyinstaller.org/>
- **py-spy**: <https://github.com/benfred/py-spy>
- **Pre-commit**: <https://pre-commit.com/>

---

## Quick Reference

| Tool        | Command                                 | Purpose          |
| ----------- | --------------------------------------- | ---------------- |
| Ruff        | `poetry run ruff check .`               | Lint code        |
| Ruff        | `poetry run ruff format .`              | Format code      |
| Mypy        | `poetry run mypy .`                     | Type check       |
| Pytest      | `poetry run pytest`                     | Run tests        |
| Bandit      | `poetry run bandit -r .`                | Security scan    |
| Alembic     | `poetry run alembic upgrade head`       | Apply migrations |
| Watchdog    | `poetry run python dev_watcher.py`      | Watch files      |
| PyInstaller | `poetry run python build.py`            | Build executable |
| Pre-commit  | `poetry run pre-commit run --all-files` | Run all hooks    |

---

**Last Updated**: 2025-11-06
**APPSIERRA Version**: 0.1.0
