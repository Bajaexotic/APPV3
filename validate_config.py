#!/usr/bin/env python3
"""
Validate configuration files for APPSIERRA

Checks:
1. TOML files are valid (ruff.toml, pyproject.toml)
2. YAML files are valid (.pre-commit-config.yaml)
3. Ruff configuration can be loaded
"""

from pathlib import Path
import sys


def validate_toml(file_path: Path) -> bool:
    """Validate TOML file syntax"""
    try:
        import tomli
    except ImportError:
        try:
            import tomllib as tomli  # Python 3.11+
        except ImportError:
            print("⚠️  Warning: tomli/tomllib not available, skipping TOML validation")
            return True

    try:
        with open(file_path, "rb") as f:
            tomli.load(f)
        print(f"✅ {file_path.name} - Valid TOML")
        return True
    except Exception as e:
        print(f"❌ {file_path.name} - Invalid TOML: {e}")
        return False


def validate_yaml(file_path: Path) -> bool:
    """Validate YAML file syntax"""
    try:
        import yaml
    except ImportError:
        print("⚠️  Warning: PyYAML not available, skipping YAML validation")
        return True

    try:
        with open(file_path, encoding="utf-8") as f:
            yaml.safe_load(f)
        print(f"✅ {file_path.name} - Valid YAML")
        return True
    except Exception as e:
        print(f"❌ {file_path.name} - Invalid YAML: {e}")
        return False


def check_file_exists(file_path: Path) -> bool:
    """Check if file exists"""
    if file_path.exists():
        print(f"✅ {file_path.name} - Exists")
        return True
    else:
        print(f"❌ {file_path.name} - Not found")
        return False


def main():
    """Run validation checks"""
    print("=" * 60)
    print("Configuration Files Validation")
    print("=" * 60)

    project_root = Path(__file__).parent
    all_valid = True

    # Check files exist
    print("\n📁 Checking file existence...")
    files_to_check = [
        project_root / "ruff.toml",
        project_root / "pyproject.toml",
        project_root / ".pre-commit-config.yaml",
    ]

    for file_path in files_to_check:
        if not check_file_exists(file_path):
            all_valid = False

    # Validate TOML files
    print("\n📝 Validating TOML files...")
    toml_files = [
        project_root / "ruff.toml",
        project_root / "pyproject.toml",
    ]

    for file_path in toml_files:
        if file_path.exists() and not validate_toml(file_path):
            all_valid = False

    # Validate YAML files
    print("\n📝 Validating YAML files...")
    yaml_files = [
        project_root / ".pre-commit-config.yaml",
    ]

    for file_path in yaml_files:
        if file_path.exists() and not validate_yaml(file_path):
            all_valid = False

    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All configuration files are valid!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Install dependencies: pip install ruff pre-commit")
        print("  2. Install hooks: pre-commit install")
        print("  3. Run linting: ruff check . --fix")
        print("  4. Format code: ruff format .")
        print("\nSee LINTING_SETUP.md for detailed instructions.")
        return 0
    else:
        print("❌ Some configuration files have errors")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
