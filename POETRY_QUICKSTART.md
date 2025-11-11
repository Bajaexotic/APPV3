# Poetry Quick Start - APPSIERRA

## 🚀 Installation (Windows)

```powershell
# Install Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Verify
poetry --version

# Configure (create .venv in project)
poetry config virtualenvs.in-project true
```

---

## ⚡ Setup Project

```powershell
# Navigate to project
cd C:\Users\cgrah\Desktop\APPSIERRA

# Install all dependencies
poetry install

# Activate virtual environment
poetry shell
```

---

## 📦 Daily Usage

```powershell
# Activate environment
poetry shell

# Run application
python main.py

# Run tests
pytest

# Run linting
ruff check . --fix && ruff format .

# Deactivate (when done)
exit
```

---

## 🔧 Common Commands

```powershell
# Add package
poetry add package-name

# Remove package
poetry remove package-name

# Update all packages
poetry update

# Show installed packages
poetry show

# Run without activating
poetry run python main.py
```

---

## ✅ You're Ready

Your `pyproject.toml` is now configured for Poetry. Just run:

```powershell
poetry install
poetry shell
python main.py
```

See **POETRY_SETUP.md** for detailed documentation.
