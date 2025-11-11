# Poetry Setup Guide for APPSIERRA

## Overview

Poetry is a modern Python dependency management and packaging tool. This guide will help you set up and use Poetry with the APPSIERRA project.

---

## ⚡ Quick Start (Windows)

```powershell
# 1. Install Poetry (if not already installed)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# 2. Add Poetry to PATH (if needed - restart PowerShell after)
# Poetry installer will show the path to add

# 3. Verify installation
poetry --version

# 4. Configure Poetry to create virtual environments in project folder
poetry config virtualenvs.in-project true

# 5. Install dependencies
cd C:\Users\cgrah\Desktop\APPSIERRA
poetry install

# 6. Activate the virtual environment
poetry shell

# 7. Run the app
python main.py
```

---

## Installation

### Windows PowerShell (Recommended)

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

### Windows (pipx)

```powershell
# Install pipx first
python -m pip install --user pipx
python -m pipx ensurepath

# Install Poetry with pipx
pipx install poetry
```

### Verify Installation

```powershell
poetry --version
# Should output: Poetry (version 1.7.0 or higher)
```

---

## Configuration

### Set Virtual Environment Location

By default, Poetry creates virtual environments in a central location. Configure it to create them in the project folder instead:

```powershell
poetry config virtualenvs.in-project true
```

This creates a `.venv` folder in your project directory.

### View Current Configuration

```powershell
poetry config --list
```

---

## Daily Usage

### Install Dependencies

```powershell
# Install all dependencies (including dev dependencies)
poetry install

# Install only production dependencies
poetry install --without dev

# Install with extras
poetry install --extras "dev"
```

### Add Dependencies

```powershell
# Add a production dependency
poetry add package-name

# Add a specific version
poetry add "PyQt6>=6.6.0"

# Add a dev dependency
poetry add --group dev pytest

# Add multiple packages
poetry add requests pandas numpy
```

### Remove Dependencies

```powershell
# Remove a package
poetry remove package-name

# Remove a dev dependency
poetry remove --group dev package-name
```

### Update Dependencies

```powershell
# Update all dependencies
poetry update

# Update specific package
poetry update PyQt6

# Show what would be updated without updating
poetry update --dry-run
```

### Activate Virtual Environment

```powershell
# Activate the virtual environment
poetry shell

# Your prompt will change to show (.venv)
(.venv) PS C:\Users\cgrah\Desktop\APPSIERRA>

# Deactivate
exit
```

### Run Commands Without Activating

```powershell
# Run Python script
poetry run python main.py

# Run pytest
poetry run pytest

# Run ruff
poetry run ruff check .
```

---

## Poetry Commands Reference

### Project Management

```powershell
# Initialize a new Poetry project (not needed for APPSIERRA)
poetry init

# Show project information
poetry show

# Show dependency tree
poetry show --tree

# Check if dependencies are valid
poetry check

# Show installed packages
poetry show --installed
```

### Dependency Management

```powershell
# List all dependencies
poetry show

# Show details about a specific package
poetry show PyQt6

# Show outdated packages
poetry show --outdated

# Export requirements.txt (for compatibility)
poetry export -f requirements.txt --output requirements.txt

# Export dev requirements
poetry export --with dev -f requirements.txt --output requirements-dev.txt
```

### Lock File

```powershell
# Update poetry.lock without installing
poetry lock

# Update lock file with latest versions
poetry lock --no-update
```

### Virtual Environment

```powershell
# Show virtual environment info
poetry env info

# List all virtual environments
poetry env list

# Remove virtual environment
poetry env remove python

# Use a specific Python version
poetry env use python3.11
poetry env use 3.11
poetry env use C:\Python311\python.exe
```

---

## Project Structure

After running `poetry install`, your project will have:

```
APPSIERRA/
├── .venv/                    # Virtual environment (if configured)
├── pyproject.toml            # Poetry configuration & dependencies
├── poetry.lock               # Locked dependency versions (will be created)
├── config/
├── core/
├── panels/
├── services/
├── ui/
├── utils/
├── widgets/
└── main.py
```

---

## pyproject.toml Structure

The Poetry configuration in `pyproject.toml`:

```toml
[tool.poetry]
name = "appsierra"
version = "0.1.0"
description = "APPSIERRA - Sierra Chart Trading Monitor with PyQt6"
authors = ["APPSIERRA Team"]

[tool.poetry.dependencies]
python = "^3.11"
PyQt6 = "^6.0.0"
pyqtgraph = "^0.13.0"

[tool.poetry.group.dev.dependencies]
ruff = "^0.1.0"
pre-commit = "^3.0.0"
pytest = "^7.0.0"
pytest-cov = "^4.0.0"
pytest-qt = "^4.0.0"
bandit = {extras = ["toml"], version = "^1.7.0"}

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

---

## Version Constraints

Poetry uses semantic versioning constraints:

| Constraint | Meaning             | Example          |
| ---------- | ------------------- | ---------------- |
| `^3.11`    | `>=3.11.0, <4.0.0`  | Latest 3.x       |
| `~3.11`    | `>=3.11.0, <3.12.0` | Latest 3.11.x    |
| `>=3.11`   | `>=3.11.0`          | 3.11 or higher   |
| `*`        | Any version         | Latest available |
| `3.11.*`   | `>=3.11.0, <3.12.0` | Any 3.11 version |

---

## Common Workflows

### Fresh Install

```powershell
# Clone repo
git clone <repo-url>
cd APPSIERRA

# Install Poetry (if needed)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Configure Poetry
poetry config virtualenvs.in-project true

# Install dependencies
poetry install

# Activate environment
poetry shell

# Run app
python main.py
```

### Daily Development

```powershell
# Activate environment
poetry shell

# Run app
python main.py

# Run tests
pytest

# Run linting
ruff check . --fix && ruff format .

# When done
exit
```

### Adding a New Package

```powershell
# Add package
poetry add requests

# Test it works
poetry run python -c "import requests; print(requests.__version__)"

# Commit the changes
git add pyproject.toml poetry.lock
git commit -m "Add requests dependency"
```

### Updating Dependencies

```powershell
# Check for updates
poetry show --outdated

# Update all
poetry update

# Update specific package
poetry update PyQt6

# Test everything still works
poetry run pytest
```

---

## Integration with Other Tools

### Pre-commit

Pre-commit works seamlessly with Poetry:

```powershell
# Install pre-commit hooks
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

### Ruff

```powershell
# Run ruff linter
poetry run ruff check .

# Run ruff formatter
poetry run ruff format .
```

### Pytest

```powershell
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov
```

---

## Troubleshooting

### Poetry Not Found

After installation, if `poetry` command is not found:

1. Restart PowerShell
2. Check PATH contains Poetry directory
3. Add manually if needed:

   ```powershell
   $env:Path += ";$env:APPDATA\Python\Scripts"
   ```

### Wrong Python Version

```powershell
# Check current Python
poetry env info

# Use specific Python version
poetry env use C:\Python311\python.exe

# Or use version number
poetry env use 3.11
```

### Virtual Environment Issues

```powershell
# Remove and recreate virtual environment
poetry env remove python
poetry install
```

### Lock File Issues

```powershell
# Recreate lock file
poetry lock --no-update

# Force update
poetry lock
```

### Dependency Conflicts

```powershell
# Show dependency tree to find conflicts
poetry show --tree

# Update conflicting packages
poetry update package-name

# If still failing, try:
poetry lock --no-update
poetry install
```

---

## Migrating from pip/venv

If you were using `pip` and `venv` before:

### Old Way (pip + venv)

```powershell
# Create virtual environment
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run app
python main.py
```

### New Way (Poetry)

```powershell
# Install dependencies (creates venv automatically)
poetry install

# Activate
poetry shell

# Run app
python main.py
```

### Benefits of Poetry

✅ **Automatic venv management**: No need to create/activate manually
✅ **Dependency resolution**: Resolves conflicts automatically
✅ **Lock file**: Ensures reproducible builds
✅ **Dev dependencies**: Separate production and dev packages
✅ **Easy updates**: `poetry update` updates everything safely
✅ **Export compatibility**: Can generate requirements.txt if needed

---

## Tips & Best Practices

### 1. Always use poetry.lock

Commit `poetry.lock` to git to ensure everyone uses the same dependency versions.

```powershell
git add poetry.lock
git commit -m "Update dependencies"
```

### 2. Use dependency groups

Separate dev dependencies from production:

```powershell
# Dev dependencies
poetry add --group dev pytest

# Production dependencies
poetry add requests
```

### 3. Pin Python version

The `python = "^3.11"` constraint ensures compatibility.

### 4. Use `poetry shell` for development

Instead of activating/deactivating, use `poetry shell` which handles everything.

### 5. Export for CI/CD

Generate `requirements.txt` for systems that don't support Poetry:

```powershell
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### 6. Keep dependencies updated

Regularly check for updates:

```powershell
poetry show --outdated
poetry update
```

---

## VS Code Integration

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true,
  "python.poetryPath": "poetry"
}
```

VS Code should automatically detect the Poetry virtual environment.

---

## Comparison: Poetry vs pip

| Feature               | Poetry                 | pip                    |
| --------------------- | ---------------------- | ---------------------- |
| Dependency resolution | ✅ Automatic           | ❌ Manual              |
| Lock file             | ✅ Yes (`poetry.lock`) | ❌ No                  |
| Virtual env           | ✅ Automatic           | ❌ Manual (`venv`)     |
| Dev dependencies      | ✅ Built-in            | ⚠️ Separate file       |
| Update all            | ✅ `poetry update`     | ❌ Manual each package |
| Build system          | ✅ Built-in            | ❌ Needs `setuptools`  |
| Publishing            | ✅ `poetry publish`    | ⚠️ Manual with `twine` |

---

## Resources

- **Poetry Documentation**: <https://python-poetry.org/docs/>
- **Poetry Commands**: <https://python-poetry.org/docs/cli/>
- **Dependency Specification**: <https://python-poetry.org/docs/dependency-specification/>
- **PyPI Package Index**: <https://pypi.org/>

---

## Quick Command Reference

```powershell
# Setup
poetry install              # Install all dependencies
poetry shell               # Activate virtual environment

# Dependencies
poetry add package         # Add package
poetry remove package      # Remove package
poetry update             # Update all packages
poetry show               # List packages

# Running
poetry run python main.py  # Run script
poetry run pytest         # Run tests

# Environment
poetry env info           # Show env info
poetry env list           # List environments
poetry env remove python  # Remove environment

# Lock file
poetry lock               # Update lock file
poetry export             # Export requirements.txt
```

---

## Summary

✅ **Installed**: Poetry package manager
✅ **Configured**: `pyproject.toml` for Poetry
✅ **Ready**: Dependencies defined and ready to install

**To get started**:

```powershell
poetry install
poetry shell
python main.py
```

That's it! Poetry will handle the rest. 🚀
