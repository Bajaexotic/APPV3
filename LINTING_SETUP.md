# Code Quality & Linting Setup Guide

This document explains how to set up and use the code quality tools for APPSIERRA.

---

## Overview

The project uses the following tools:

1. **Ruff** - Fast Python linter and formatter (replaces black, isort, flake8, etc.)
2. **Pre-commit** - Framework for managing git hooks
3. **Pytest** - Testing framework with coverage
4. **Bandit** - Security vulnerability scanner

---

## Quick Start

### 1. Install Development Dependencies

```bash
# Windows PowerShell
pip install ruff pre-commit pytest pytest-cov bandit[toml]

# Or install all dev dependencies from pyproject.toml
pip install -e ".[dev]"
```

### 2. Install Pre-commit Hooks

```bash
pre-commit install
```

This will automatically run checks before each commit.

### 3. Run Linting Manually

```bash
# Run ruff linter with auto-fix
ruff check . --fix

# Run ruff formatter
ruff format .

# Run both
ruff check . --fix && ruff format .
```

---

## Tool Details

### Ruff

**Ruff** is an extremely fast Python linter and formatter written in Rust. It replaces multiple tools:

- Black (code formatter)
- isort (import sorter)
- Flake8 (linter)
- pyupgrade (syntax upgrader)
- And many more...

#### Configuration

Main configuration: `ruff.toml`

#### Usage

```bash
# Lint all files
ruff check .

# Lint with auto-fix
ruff check . --fix

# Format all files
ruff format .

# Check specific file
ruff check path/to/file.py

# Show what would be changed without applying
ruff check . --diff
```

#### VSCode Integration

Install the Ruff extension:

1. Open VSCode
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Ruff"
4. Install "Ruff" by Astral Software

Add to `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  "ruff.enable": true,
  "ruff.lint.enable": true,
  "ruff.format.enable": true
}
```

#### PyCharm Integration

1. Go to Settings → Tools → External Tools
2. Add New Tool:
   - Name: Ruff Check
   - Program: `ruff`
   - Arguments: `check $FilePath$ --fix`
   - Working directory: `$ProjectFileDir$`

---

### Pre-commit

**Pre-commit** manages git hooks to automatically check code before commits.

#### Configuration

Main configuration: `.pre-commit-config.yaml`

#### Usage

```bash
# Install hooks
pre-commit install

# Run on all files manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update hooks to latest versions
pre-commit autoupdate

# Uninstall hooks
pre-commit uninstall
```

#### Hooks Included

1. **File checks**: YAML/JSON/TOML syntax, large files, merge conflicts, private keys
2. **Python checks**: AST validation, debug statements, test naming
3. **Ruff**: Linting and formatting
4. **Codespell**: Spelling checker
5. **Bandit**: Security scanner
6. **Markdown linting**: Format markdown files
7. **Prettier**: Format JSON/YAML/TOML files

#### Skip Hooks

```bash
# Skip all pre-commit hooks
git commit --no-verify -m "message"

# Skip specific hook
SKIP=ruff git commit -m "message"
```

---

### Pytest

**Pytest** is the testing framework with coverage reporting.

#### Configuration

Main configuration: `pyproject.toml` under `[tool.pytest.ini_options]`

#### Usage

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_panels.py

# Run tests matching pattern
pytest -k "test_mode"

# Run with verbose output
pytest -v

# Run only unit tests (skip slow tests)
pytest -m "not slow"

# Generate HTML coverage report
pytest --cov --cov-report=html
# View at htmlcov/index.html
```

#### Test Markers

Mark tests with decorators:

```python
import pytest

@pytest.mark.slow
def test_expensive_operation():
    """This test takes a long time"""
    pass

@pytest.mark.integration
def test_dtc_connection():
    """This is an integration test"""
    pass

@pytest.mark.ui
def test_panel_rendering():
    """This test requires Qt/GUI"""
    pass
```

Run marked tests:

```bash
# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

---

### Bandit

**Bandit** scans Python code for common security issues.

#### Configuration

Main configuration: `pyproject.toml` under `[tool.bandit]`

#### Usage

```bash
# Scan all Python files
bandit -r . -c pyproject.toml

# Scan specific directory
bandit -r core/

# Show only high severity issues
bandit -r . -ll

# Generate report
bandit -r . -f json -o bandit-report.json
```

---

## Common Workflows

### Before Committing

```bash
# 1. Format code
ruff format .

# 2. Fix linting issues
ruff check . --fix

# 3. Run tests
pytest

# 4. Commit (pre-commit will run automatically)
git add .
git commit -m "Your message"
```

### Full Code Quality Check

```bash
# Run everything
ruff check . --fix && \
ruff format . && \
pytest --cov && \
bandit -r . -c pyproject.toml && \
pre-commit run --all-files
```

### Fix All Auto-fixable Issues

```bash
# Fix imports, formatting, and common issues
ruff check . --fix && ruff format .
```

### Check Without Changing Files

```bash
# Show what would change
ruff check . --diff
ruff format . --diff
```

---

## Ignoring Specific Violations

### In Code

```python
# Ignore specific rule for one line
result = eval(user_input)  # noqa: S307

# Ignore multiple rules
x = 1  # noqa: E501, W291

# Ignore all rules for one line
dangerous_code()  # noqa

# Ignore rule for entire file (at top of file)
# ruff: noqa: E501

# Type ignore for mypy
x = None  # type: ignore[assignment]
```

### In Configuration

Edit `ruff.toml`:

```toml
[lint]
ignore = [
    "E501",  # Line too long
]

[lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",  # Allow assert in tests
]
```

---

## Ruff Rule Categories

Ruff includes rules from many tools. Here are the main categories:

| Code | Tool/Category           | Description                     |
| ---- | ----------------------- | ------------------------------- |
| F    | Pyflakes                | Undefined names, unused imports |
| E/W  | pycodestyle             | Style violations                |
| I    | isort                   | Import sorting                  |
| D    | pydocstyle              | Docstring conventions           |
| UP   | pyupgrade               | Upgrade syntax for newer Python |
| N    | pep8-naming             | Naming conventions              |
| B    | flake8-bugbear          | Likely bugs                     |
| C4   | flake8-comprehensions   | Better comprehensions           |
| T10  | flake8-debugger         | Debugger imports                |
| SIM  | flake8-simplify         | Simplify code                   |
| TCH  | flake8-type-checking    | Type checking imports           |
| ARG  | flake8-unused-arguments | Unused arguments                |
| PTH  | flake8-use-pathlib      | Use pathlib                     |
| PL   | Pylint                  | Various checks                  |
| RUF  | Ruff                    | Ruff-specific rules             |

View all rules: <https://docs.astral.sh/ruff/rules/>

---

## Troubleshooting

### Pre-commit Hook Fails

```bash
# See what failed
git commit -m "message"

# Fix issues manually
ruff check . --fix

# Try again
git commit -m "message"

# Or skip hooks temporarily
git commit --no-verify -m "message"
```

### Ruff Not Found

```bash
# Reinstall ruff
pip install --upgrade ruff

# Check installation
ruff --version

# Check PATH
which ruff  # Linux/Mac
where ruff  # Windows
```

### Pre-commit Hooks Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Check installation
pre-commit --version
```

### VSCode Not Using Ruff

1. Reload window: Ctrl+Shift+P → "Reload Window"
2. Check output: View → Output → Select "Ruff" from dropdown
3. Check settings: Search "ruff" in settings
4. Reinstall extension

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/lint.yml`:

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install ruff pytest bandit[toml]
      - name: Run ruff
        run: |
          ruff check .
          ruff format --check .
      - name: Run tests
        run: pytest
      - name: Security check
        run: bandit -r . -c pyproject.toml
```

### Pre-commit.ci

Pre-commit.ci is a free CI service for open source projects.

1. Go to <https://pre-commit.ci>
2. Install the GitHub App
3. Hooks will run automatically on PRs

---

## Performance

### Ruff Performance

Ruff is extremely fast:

- **10-100x faster** than Flake8
- **Formats code in milliseconds**
- Can lint entire codebase in < 1 second

Example timings:

```
Ruff:    0.5 seconds
Black:   2.3 seconds
isort:   1.8 seconds
Flake8:  8.5 seconds
```

---

## Migration Notes

### From Black + isort + Flake8

Ruff replaces all three:

```bash
# Old way
black .
isort .
flake8 .

# New way (Ruff)
ruff format .
ruff check . --fix
```

### From existing config

Ruff can read some config from `pyproject.toml`, but we use `ruff.toml` for clarity.

---

## Resources

- **Ruff Documentation**: <https://docs.astral.sh/ruff/>
- **Pre-commit Documentation**: <https://pre-commit.com/>
- **Pytest Documentation**: <https://docs.pytest.org/>
- **Bandit Documentation**: <https://bandit.readthedocs.io/>

---

## Summary

✅ **Installed**: `ruff`, `pre-commit`, `pytest`, `bandit`
✅ **Configured**: `ruff.toml`, `.pre-commit-config.yaml`, `pyproject.toml`
✅ **Setup**: `pre-commit install`

**Daily workflow**:

1. Write code
2. Run `ruff check . --fix && ruff format .`
3. Run `pytest`
4. Commit (hooks run automatically)

**That's it!** The tools will keep your code clean and consistent. 🚀
