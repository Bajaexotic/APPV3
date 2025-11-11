#!/usr/bin/env python
"""
Verify Router Handler Fixes
Confirms both contextlib and structlog errors are resolved
"""
import sys
from pathlib import Path


def check_file_for_issue(file_path: Path, import_name: str, usage_pattern: str) -> dict:
    """Check if a file imports a module it uses"""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    has_import = f"import {import_name}" in content
    has_usage = usage_pattern in content

    return {
        "file": file_path.name,
        "has_import": has_import,
        "has_usage": has_usage,
        "status": "OK" if (not has_usage or has_import) else "ERROR"
    }


def main():
    print("="*80)
    print("Router Handler Fixes Verification")
    print("="*80)
    print()

    base_path = Path(__file__).parent.parent

    # Check 1: state_manager contextlib import
    print("[1] Checking state_manager.py for contextlib import...")
    state_check = check_file_for_issue(
        base_path / "core" / "state_manager.py",
        "contextlib",
        "contextlib.suppress"
    )

    if state_check["status"] == "OK":
        print(f"    [OK] {state_check['file']}")
        print(f"         Import: {state_check['has_import']}, Usage: {state_check['has_usage']}")
    else:
        print(f"    [ERROR] {state_check['file']} uses contextlib but doesn't import it!")

    print()

    # Check 2: message_router structlog usage
    print("[2] Checking message_router.py for structlog keyword conflict...")
    router_file = base_path / "core" / "message_router.py"

    with open(router_file, encoding="utf-8") as f:
        content = f.read()

    # Check for the problematic pattern
    has_old_pattern = 'log.info("router.trade_account", account=' in content
    has_new_pattern = 'log.info("router.trade_account", account_id=' in content

    if has_new_pattern and not has_old_pattern:
        print("    [OK] message_router.py")
        print("         Using 'account_id=' instead of 'account='")
    elif has_old_pattern:
        print("    [ERROR] Still using problematic 'account=' keyword")
    else:
        print("    [WARNING] Pattern not found - verify manually")

    print()

    # Summary
    print("="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    all_ok = (
        state_check["status"] == "OK" and
        has_new_pattern and
        not has_old_pattern
    )

    if all_ok:
        print("[OK] All router handler errors have been fixed!")
        print()
        print("Fixed Issues:")
        print("  1. state_manager.py - Added missing contextlib import")
        print("  2. message_router.py - Changed 'account=' to 'account_id='")
        return 0
    else:
        print("[ERROR] Some issues remain")
        return 1


if __name__ == "__main__":
    sys.exit(main())
