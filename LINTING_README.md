# Code Quality Setup - Quick Reference

## ⚡ Quick Start (1 minute)

```bash
# 1. Install tools
pip install ruff pre-commit

# 2. Install git hooks
pre-commit install

# 3. Done! Hooks will run automatically on commit
```

---

## 🚀 Daily Usage

```bash
# Fix code before committing
ruff check . --fix && ruff format .

# Run tests
pytest

# Commit (hooks run automatically)
git commit -m "Your message"
```

---

## 📁 Configuration Files

| File                      | Purpose                          |
| ------------------------- | -------------------------------- |
| `ruff.toml`               | Main linting & formatting config |
| `.pre-commit-config.yaml` | Git hooks configuration          |
| `pyproject.toml`          | Project metadata & tool configs  |
| `LINTING_SETUP.md`        | Detailed documentation           |

---

## 🛠️ Tools Included

1. **Ruff** - Ultra-fast Python linter & formatter
   - Replaces: black, isort, flake8, pyupgrade, and more
   - 10-100x faster than alternatives
   - Auto-fixes most issues

2. **Pre-commit** - Automated git hooks
   - Runs checks before each commit
   - Prevents bad code from being committed
   - Can be skipped with `git commit --no-verify`

3. **Additional Hooks**:
   - YAML/JSON/TOML syntax validation
   - Markdown linting
   - Security scanning (Bandit)
   - Spelling checks (Codespell)
   - File cleanup (trailing whitespace, EOF newlines)

---

## 📖 Key Commands

### Linting

```bash
# Check for issues
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code
ruff format .

# Check specific file
ruff check path/to/file.py
```

### Pre-commit

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update to latest versions
pre-commit autoupdate
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Skip slow tests
pytest -m "not slow"
```

---

## 🎯 What Gets Checked?

✅ **Code Style**

- PEP 8 compliance
- Line length (120 chars)
- Import organization
- Naming conventions

✅ **Code Quality**

- Unused imports/variables
- Undefined names
- Potential bugs
- Code simplification opportunities
- Type checking

✅ **Security**

- Common vulnerabilities
- Hardcoded secrets
- Dangerous function usage

✅ **File Quality**

- YAML/JSON/TOML syntax
- No merge conflicts
- No large files
- Proper line endings
- No trailing whitespace

---

## 🔧 IDE Integration

### VSCode

1. Install "Ruff" extension by Astral Software
2. Add to settings.json:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

### PyCharm

1. Settings → Tools → External Tools → Add:
   - Program: `ruff`
   - Arguments: `check $FilePath$ --fix`

---

## 🚫 Ignoring Issues

### In Code

```python
# Ignore for one line
dangerous_code()  # noqa: S307

# Ignore for entire file (top of file)
# ruff: noqa: E501
```

### In Config

Edit `ruff.toml`:

```toml
[lint]
ignore = ["E501"]  # Add rule codes to ignore
```

---

## ❓ Troubleshooting

**Hooks not running?**

```bash
pre-commit install
```

**Ruff not found?**

```bash
pip install --upgrade ruff
```

**Want to skip hooks temporarily?**

```bash
git commit --no-verify -m "message"
```

---

## 📚 Documentation

- **Full Setup Guide**: See `LINTING_SETUP.md`
- **Ruff Docs**: <https://docs.astral.sh/ruff/>
- **Pre-commit Docs**: <https://pre-commit.com/>

---

## ✨ Benefits

- 🚀 **Fast**: Ruff is 10-100x faster than alternatives
- 🔧 **Auto-fix**: Most issues are fixed automatically
- 🛡️ **Safe**: Catches bugs before they reach production
- 📏 **Consistent**: Enforces consistent code style
- 🤖 **Automated**: Runs on every commit
- 📦 **Integrated**: Works with your IDE

---

## 🎉 You're All Set

The configuration is complete and validated. Just install the tools and start coding!

```bash
pip install ruff pre-commit
pre-commit install
```

Happy coding! 🚀
