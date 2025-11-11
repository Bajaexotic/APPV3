#!/usr/bin/env python3
# -------------------- Poetry Dependency Audit (start)
import os
from pathlib import Path
import re
import subprocess


__scope__ = "validation.dependencies"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_FILES = list(PROJECT_ROOT.rglob("*.py"))
POETRY_CMD = ["poetry", "show", "--with", "dev", "--no-ansi"]


def extract_imports():
    imports = set()
    pattern = re.compile(r"^(?:from|import)\s+([\w\d_\.]+)", re.MULTILINE)
    for file_path in PYTHON_FILES:
        if ".venv" in str(file_path):
            continue
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for match in pattern.findall(content):
                    root_pkg = match.split(".")[0]
                    if not root_pkg.startswith(("_", ".")):
                        imports.add(root_pkg)
        except Exception:
            pass
    return imports


def get_poetry_packages():
    result = subprocess.run(POETRY_CMD, capture_output=True, text=True)
    pkgs = set()
    for line in result.stdout.splitlines():
        name = line.split()[0].strip().lower()
        if name and not name.startswith("-"):
            pkgs.add(name)
    return pkgs


def normalize(pkg):
    return pkg.lower().replace("_", "-")


def map_import_to_package(import_name):
    """Map import names to actual package names"""
    mapping = {
        "yaml": "pyyaml",
        "pyqt6": "pyqt6",
        "cv2": "opencv-python",
        "pil": "pillow",
        "sklearn": "scikit-learn",
        "pytest": "pytest",
    }
    normalized = normalize(import_name)
    return mapping.get(normalized, normalized)


def main():
    print("\n🔍 Running Poetry Dependency Audit...\n")
    imported_raw = extract_imports()
    imported = {map_import_to_package(i) for i in imported_raw}
    poetry_pkgs = get_poetry_packages()

    # Standard library modules
    stdlib = {
        "os",
        "sys",
        "re",
        "json",
        "math",
        "datetime",
        "typing",
        "itertools",
        "functools",
        "pathlib",
        "subprocess",
        "logging",
        "collections",
        "traceback",
        "asyncio",
        "enum",
        "time",
        "inspect",
        "threading",
        "queue",
        "copy",
        "importlib",
        "unittest",
        "argparse",
        "platform",
        "dataclasses",
        "csv",
        "io",
        "tempfile",
        "shutil",
        "contextlib",
        "abc",
        "socket",
        "ssl",
        "sqlite3",
        "struct",
        "gc",
        "random",
        "statistics",
        "types",
        "builtins",
        "warnings",
        "weakref",
        "operator",
        "pickle",
        "codecs",
        "string",
        "textwrap",
        "pprint",
        "email",
        "http",
        "urllib",
        "html",
        "xml",
        "hashlib",
        "hmac",
        "secrets",
        "uuid",
        "decimal",
    }

    # Local project modules (not external packages)
    local_modules = {"config", "core", "panels", "services", "utils", "widgets", "tools", "ui", "data"}

    imported = {p for p in imported if p not in stdlib and p not in local_modules}

    missing = sorted(imported - poetry_pkgs)

    # Filter out known sub-dependencies and dev tools from "extra"
    known_subdeps = {
        "pyqt6-qt6",
        "pyqt6-sip",  # PyQt6 sub-packages
        "pydantic-core",
        "annotated-types",  # Pydantic sub-deps
        "typing-extensions",
        "typing-inspection",  # Typing sub-deps
        "setuptools",
        "packaging",
        "platformdirs",  # Build tools
        "certifi",
        "charset-normalizer",
        "idna",
        "urllib3",
        "requests",  # HTTP stack
        "attrs",
        "cattrs",  # Serialization deps
        "pluggy",
        "iniconfig",
        "tomli-w",  # Config tools
    }

    dev_tools = {
        "pytest-cov",
        "pytest-qt",
        "coverage",  # Testing
        "ruff",
        "mypy",
        "mypy-extensions",
        "bandit",  # Linting
        "pre-commit",
        "nodeenv",
        "identify",
        "cfgv",
        "virtualenv",  # Pre-commit
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "altgraph",  # Packaging
        "py-spy",
        "memory-profiler",
        "watchdog",  # Profiling
        "rich",
        "rich-argparse",
        "pygments",
        "markdown-it-py",
        "mdurl",  # CLI tools
    }

    # Only show truly unused packages
    extra_filtered = sorted((poetry_pkgs - imported) - known_subdeps - dev_tools)

    print(f"✅ Total imported modules found: {len(imported)}")
    print(f"📦 Poetry-managed packages: {len(poetry_pkgs)}\n")

    # Missing Packages
    if missing:
        print("⚠️  Missing (imported but not in Poetry):")
        for m in missing:
            print(f"   - {m}")
        print("\n💡 Suggested fix:")
        print(f"poetry add {' '.join(missing)}")
    else:
        print("✅ No missing packages!\n")

    # Unused Packages (filtered)
    if extra_filtered:
        print("\n🧹 Possibly Unused (in Poetry but not imported):")
        for e in extra_filtered:
            print(f"   - {e}")
        print("\n💡 Suggested cleanup:")
        print(f"poetry remove {' '.join(extra_filtered)}")
        print("\nNote: Filtered out dev tools and known sub-dependencies")
    else:
        print("✅ No extra packages!\n")

    print("📋 Audit complete.\n")


if __name__ == "__main__":
    main()
# -------------------- Poetry Dependency Audit (end)
