#!/usr/bin/env python3
# -------------------- [Theme Import Warning Probe] (start)

"""
Theme Import Warning Probe
--------------------------
Captures and reports any warnings that occur during import of
`config.theme` and `config.theme_schema`.

Usage:
    python tools/theme/warn_probe.py
    python tools/theme/warn_probe.py --reload
    python tools/theme/warn_probe.py --quiet

Flags:
    --reload   Force a module reload to surface cached warnings.
    --quiet    Suppress detailed traceback output; only show summary.

Exit Codes:
    0 = No warnings
    1 = One or more warnings captured
"""

from __future__ import annotations

import argparse
import importlib
import sys
import traceback
from types import ModuleType
from typing import List
import warnings


# ================================================================
#  Helpers
# ================================================================


class Colors:
    """Lightweight color constants for console output."""

    YELLOW = "\033[93m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def banner(text: str) -> None:
    print(f"\n{Colors.BLUE}{'=' * 80}\n{text}\n{'=' * 80}{Colors.RESET}")


def safe_import(name: str, reload: bool = False) -> ModuleType | None:
    """Import or reload a module safely and return it."""
    try:
        module = importlib.import_module(name)
        if reload:
            module = importlib.reload(module)
        return module
    except Exception:
        print(f"{Colors.RED}❌ Failed to import module: {name}{Colors.RESET}")
        traceback.print_exc()
        return None


# ================================================================
#  Core Probe
# ================================================================


def probe_theme_import(reload: bool = False, quiet: bool = False) -> int:
    """Capture and print all warnings emitted during theme import."""
    warnings.simplefilter("always")
    captured: list[warnings.WarningMessage] = []

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        theme_mod = safe_import("config.theme", reload=reload)
        schema_mod = safe_import("config.theme_schema", reload=reload)
        captured.extend(w)

    count = len(captured)
    banner("THEME IMPORT WARNING PROBE REPORT")

    if count == 0:
        print(f"{Colors.GREEN}✅ No warnings captured during import.{Colors.RESET}")
        return 0

    print(f"{Colors.YELLOW}⚠️  Captured {count} warning(s) during import.{Colors.RESET}\n")

    for i, wrn in enumerate(captured, 1):
        cat = wrn.category.__name__
        msg = str(wrn.message)
        src = getattr(wrn, "filename", None)
        line = getattr(wrn, "lineno", None)
        print(f"{Colors.YELLOW}[{i}] {cat}:{Colors.RESET} {msg}")
        if not quiet and src:
            print(f"    → {src}:{line}")
    print()

    if not quiet:
        print(
            f"{Colors.RED}Use pytest -q tests/test_theme_import_warnings.py "
            f"for automated detection in CI.{Colors.RESET}"
        )

    return 1


# ================================================================
#  Entrypoint
# ================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe import-time warnings for theme modules.")
    parser.add_argument("--reload", action="store_true", help="Force reload modules to surface warnings.")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed traceback output.")
    args = parser.parse_args()

    exit_code = probe_theme_import(reload=args.reload, quiet=args.quiet)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

# -------------------- [Theme Import Warning Probe] (end)
