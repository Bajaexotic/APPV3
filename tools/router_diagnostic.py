#!/usr/bin/env python
"""
MessageRouter Diagnostic Tool
Identifies and fixes common router handler errors
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_contextlib_import(file_path: Path) -> dict:
    """Check if contextlib is properly imported"""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)

    # Check for contextlib import
    contextlib_imported = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "contextlib":
                    contextlib_imported = True
                    break
        elif isinstance(node, ast.ImportFrom):
            if node.module == "contextlib":
                contextlib_imported = True
                break

    return {
        "contextlib_imported": contextlib_imported,
        "uses_contextlib": "contextlib.suppress" in content
    }


def check_structlog_usage(file_path: Path) -> list[dict]:
    """Check for incorrect structlog usage"""
    issues = []

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Known problematic patterns
    for i, line in enumerate(lines, 1):
        # Check for log.info/error with 'account' keyword
        if "log.info(" in line and "account=" in line:
            issues.append({
                "line": i,
                "type": "structlog_keyword",
                "message": "Using 'account' as keyword in log.info - may conflict with structlog",
                "code": line.strip()
            })

        # Check for contextlib usage in exception handlers
        if "with contextlib.suppress" in line:
            # Make sure contextlib is imported
            pass

    return issues


def check_signal_handlers(file_path: Path) -> list[dict]:
    """Check signal handler error handling"""
    issues = []

    with open(file_path, encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    # Find signal handler methods
    handler_methods = [
        "_on_order_signal",
        "_on_position_signal",
        "_on_balance_signal",
        "_on_trade_account_signal"
    ]

    for method in handler_methods:
        if method not in content:
            issues.append({
                "type": "missing_handler",
                "method": method,
                "message": f"Signal handler {method} not found"
            })

    return issues


def main():
    print("="*80)
    print("MessageRouter Diagnostic Tool")
    print("="*80)
    print()

    router_file = Path(__file__).parent.parent / "core" / "message_router.py"

    if not router_file.exists():
        print(f"ERROR: {router_file} not found")
        return 1

    print(f"Analyzing: {router_file}")
    print()

    # Check 1: Contextlib import
    print("[1] Checking contextlib import...")
    ctx_check = check_contextlib_import(router_file)
    if ctx_check["contextlib_imported"]:
        print("    [OK] contextlib is imported")
    else:
        print("    [ERROR] contextlib is NOT imported")

    if ctx_check["uses_contextlib"]:
        print("    [OK] contextlib.suppress is used in code")
    print()

    # Check 2: Structlog usage
    print("[2] Checking structlog usage...")
    structlog_issues = check_structlog_usage(router_file)
    if structlog_issues:
        print(f"    Found {len(structlog_issues)} potential issues:")
        for issue in structlog_issues:
            print(f"    Line {issue['line']}: {issue['message']}")
            print(f"      Code: {issue['code']}")
    else:
        print("    [OK] No structlog issues found")
    print()

    # Check 3: Signal handlers
    print("[3] Checking signal handlers...")
    handler_issues = check_signal_handlers(router_file)
    if handler_issues:
        print(f"    Found {len(handler_issues)} issues:")
        for issue in handler_issues:
            print(f"    {issue['message']}")
    else:
        print("    [OK] All signal handlers present")
    print()

    # Summary
    print("="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)

    total_issues = len(structlog_issues) + len(handler_issues)

    if total_issues == 0:
        print("[OK] No critical issues found")
        print("\nThe 'contextlib' error in runtime logs may be caused by:")
        print("  1. Import order issues during module initialization")
        print("  2. Circular import problems")
        print("  3. Exception occurring before imports complete")
        print("\nRecommendation: Check the actual exception traceback for root cause")
    else:
        print(f"[WARNING] Found {total_issues} potential issues")
        print("\nRecommended fixes:")

        if structlog_issues:
            print("\n  Structlog issues:")
            print("  - Replace 'account=' with structured logging attributes")
            print("  - Use log.bind(account=...).info(...) instead")

        if handler_issues:
            print("\n  Handler issues:")
            print("  - Implement missing signal handlers")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
