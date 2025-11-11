from __future__ import annotations

import argparse
import importlib
import inspect
from pathlib import Path
import pkgutil
import sys
from typing import List, Set


# ============================================================================
# Audit Presets - Curated Tool Combinations
# ============================================================================

AUDIT_PRESETS = {
    "ui": [
        "validation.config_integrity",
        "validation.theme_audit",
        "dtc.probe",
        "diagnostics.signal_trace",
        "diagnostics.state_diff",
    ],
    "full": [
        "validation.*",
        "dtc.*",
        "diagnostics.*",
        "performance.*",
        "maintenance.*",
    ],
    "quick": [
        "validation.config_integrity",
        "dtc.probe",
    ],
    "validation": [
        "validation.*",
    ],
    "dtc": [
        "dtc.*",
    ],
    "performance": [
        "performance.*",
    ],
    "maintenance": [
        "maintenance.*",
        "reporting.*",
    ],
}


# ============================================================================
# Tool Discovery and Matching
# ============================================================================


def iter_tools() -> list[tuple[str, str]]:
    """
    Discover all tools with __scope__ attribute.

    Returns:
        List of (scope, module_name) tuples
    """
    tools_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(tools_dir))
    out = []
    for mod in pkgutil.iter_modules([str(tools_dir)]):
        if mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(mod.name)
        except Exception:
            continue
        scope = getattr(m, "__scope__", None)
        if scope:
            out.append((scope, mod.name))
    return sorted(out)


def match(scopes: list[str], pattern: str) -> list[str]:
    """
    Match scopes against a pattern.

    Supports:
        - Exact match: "validation.config_integrity"
        - Wildcard: "validation.*"

    Args:
        scopes: List of available scopes
        pattern: Pattern to match

    Returns:
        List of matching scopes
    """
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        return [m for m in scopes if m.startswith(prefix + ".")]
    else:
        return [m for m in scopes if m == pattern]


def expand_patterns(all_scopes: list[str], patterns: list[str]) -> set[str]:
    """
    Expand a list of scope patterns to concrete scopes.

    Args:
        all_scopes: All available scopes
        patterns: List of patterns (can include wildcards)

    Returns:
        Set of matched scopes
    """
    result = set()
    for pattern in patterns:
        matched = match(all_scopes, pattern)
        result.update(matched)
    return result


def run_tool(scope: str, mod_name: str) -> int:
    """
    Run a single tool by importing and calling its main().

    Args:
        scope: Tool scope (for display)
        mod_name: Module name to import

    Returns:
        0 on success, non-zero on failure
    """
    try:
        mod = importlib.import_module(mod_name)
        main_fn = getattr(mod, "main", None)
        if callable(main_fn):
            print(f"\n{'='*80}")
            print(f"[RUN] {scope}")
            print(f"{'='*80}")
            rc = main_fn([])
            if rc != 0:
                print(f"[FAIL] {scope} returned {rc}")
                return rc
            print(f"[PASS] {scope}")
            return 0
        else:
            print(f"[SKIP] {scope} (no main() function)")
            return 0
    except Exception as e:
        print(f"[ERR] {scope}: {e}")
        import traceback

        traceback.print_exc()
        return 1


def list_available_presets() -> None:
    """Print available audit presets."""
    print("\nAvailable Audit Presets:")
    print("=" * 80)
    for name, patterns in AUDIT_PRESETS.items():
        print(f"\n{name}:")
        for pattern in patterns:
            print(f"  - {pattern}")


def main(argv: list[str]) -> int:
    """
    Main entry point for audit tool orchestration.

    Supports three modes:
        1. --scope: Run tools matching a scope pattern
        2. --preset: Run a curated preset combination
        3. --list-presets: Show available presets
    """
    ap = argparse.ArgumentParser(
        description="Run code audit tools by scope pattern or preset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run by scope pattern
  %(prog)s --scope validation.*
  %(prog)s --scope dtc.probe

  # Run by preset
  %(prog)s --preset ui
  %(prog)s --preset full
  %(prog)s --preset quick

  # Exclude specific tools
  %(prog)s --scope validation.* --exclude dependencies
  %(prog)s --preset full --exclude validation.dependencies

  # List available presets
  %(prog)s --list-presets
        """,
    )

    # Mutually exclusive: scope OR preset OR list-presets
    group = ap.add_mutually_exclusive_group(required=False)
    group.add_argument("--scope", help="Scope pattern (e.g., validation.* or dtc.probe)")
    group.add_argument("--preset", choices=list(AUDIT_PRESETS.keys()), help="Audit preset name")
    group.add_argument("--list-presets", action="store_true", help="List available audit presets")

    ap.add_argument(
        "--exclude", action="append", default=[], help="Exclude specific scopes (can be used multiple times)"
    )

    args = ap.parse_args(argv)

    # List presets mode
    if args.list_presets:
        list_available_presets()
        return 0

    # Require either --scope or --preset
    if not args.scope and not args.preset:
        ap.print_help()
        print("\nError: Either --scope or --preset is required")
        return 1

    # Discover all tools
    items = iter_tools()
    all_scopes = [s for s, _ in items]
    scope_to_module = dict(items)

    # Determine patterns to run
    if args.preset:
        patterns = AUDIT_PRESETS[args.preset]
        print(f"\n{'='*80}")
        print(f"Running Audit Preset: {args.preset}")
        print(f"{'='*80}")
    else:
        patterns = [args.scope]

    # Expand patterns to concrete scopes
    matched_scopes = expand_patterns(all_scopes, patterns)

    # Apply exclusions
    if args.exclude:
        excluded_scopes = expand_patterns(all_scopes, args.exclude)
        matched_scopes -= excluded_scopes
        if excluded_scopes:
            print(f"\nExcluding: {', '.join(sorted(excluded_scopes))}")

    if not matched_scopes:
        print("No tools matched (after exclusions)")
        return 1

    # Sort for consistent order
    matched_scopes = sorted(matched_scopes)

    print(f"\nRunning {len(matched_scopes)} tool(s):")
    for scope in matched_scopes:
        print(f"  - {scope}")

    # Run all matched tools
    failed = []
    passed = []

    for scope in matched_scopes:
        mod_name = scope_to_module[scope]
        rc = run_tool(scope, mod_name)
        if rc != 0:
            failed.append(scope)
        else:
            passed.append(scope)

    # Summary
    print(f"\n{'='*80}")
    print("AUDIT SUMMARY")
    print(f"{'='*80}")
    print(f"Total: {len(matched_scopes)}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed tools:")
        for scope in failed:
            print(f"  [FAIL] {scope}")
        return 2

    print("\n[SUCCESS] All tools passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
