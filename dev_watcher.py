#!/usr/bin/env python3
"""Development File Watcher for APPSIERRA

This script uses Watchdog to monitor file changes and automatically:
- Run linting (ruff)
- Run type checking (mypy)
- Run tests (pytest)
- Restart the application (optional)

Usage:
    poetry run python dev_watcher.py --mode lint        # Only lint on changes
    poetry run python dev_watcher.py --mode test        # Run tests on changes
    poetry run python dev_watcher.py --mode full        # Lint + test + type check
    poetry run python dev_watcher.py --mode restart     # Restart app on changes
"""

import argparse
from pathlib import Path
import subprocess
import sys
import time
from typing import Optional


try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("ERROR: watchdog is not installed.")
    print("Install it with: poetry add --group dev watchdog")
    sys.exit(1)


class DevelopmentWatcher(FileSystemEventHandler):
    """File system event handler for development workflow."""

    def __init__(self, mode: str = "lint", debounce_seconds: float = 1.0):
        """
        Initialize the development watcher.

        Args:
            mode: Watch mode (lint, test, full, restart)
            debounce_seconds: Minimum time between command executions
        """
        self.mode = mode
        self.debounce_seconds = debounce_seconds
        self.last_run_time = 0.0
        self.project_root = Path(__file__).parent

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only process Python files
        if not event.src_path.endswith(".py"):
            return

        # Debounce: Don't run too frequently
        current_time = time.time()
        if current_time - self.last_run_time < self.debounce_seconds:
            return

        self.last_run_time = current_time

        # Get relative path for cleaner output
        try:
            rel_path = Path(event.src_path).relative_to(self.project_root)
        except ValueError:
            rel_path = Path(event.src_path)

        print(f"\n{'=' * 70}")
        print(f"📝 File changed: {rel_path}")
        print(f"{'=' * 70}\n")

        # Execute based on mode
        if self.mode == "lint":
            self.run_lint()
        elif self.mode == "test":
            self.run_tests()
        elif self.mode == "full":
            self.run_full_check()
        elif self.mode == "restart":
            self.restart_app()

    def run_lint(self) -> None:
        """Run linting with ruff."""
        print("🔍 Running ruff linter...")
        try:
            result = subprocess.run(
                ["poetry", "run", "ruff", "check", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print("✅ Linting passed!")
            else:
                print("❌ Linting issues found:")
                print(result.stdout)
        except subprocess.TimeoutExpired:
            print("⏱️ Linting timed out")
        except Exception as e:
            print(f"❌ Error running linter: {e}")

    def run_tests(self) -> None:
        """Run pytest tests."""
        print("🧪 Running tests...")
        try:
            result = subprocess.run(
                ["poetry", "run", "pytest", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("✅ All tests passed!")
            else:
                print("❌ Some tests failed:")
                print(result.stdout)
        except subprocess.TimeoutExpired:
            print("⏱️ Tests timed out")
        except Exception as e:
            print(f"❌ Error running tests: {e}")

    def run_mypy(self) -> None:
        """Run mypy type checking."""
        print("🔎 Running mypy type checker...")
        try:
            result = subprocess.run(
                ["poetry", "run", "mypy", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print("✅ Type checking passed!")
            else:
                print("⚠️ Type checking issues found:")
                print(result.stdout)
        except subprocess.TimeoutExpired:
            print("⏱️ Type checking timed out")
        except Exception as e:
            print(f"❌ Error running type checker: {e}")

    def run_full_check(self) -> None:
        """Run full checks: lint + type check + tests."""
        self.run_lint()
        print()
        self.run_mypy()
        print()
        self.run_tests()

    def restart_app(self) -> None:
        """Restart the application (placeholder)."""
        print("🔄 App restart mode activated")
        print("⚠️ Note: Actual restart logic depends on your app architecture")
        print("   Consider using a process manager like supervisor or systemd")


def main() -> None:
    """Main entry point for the development watcher."""
    parser = argparse.ArgumentParser(description="Watch Python files and run development tasks on changes")
    parser.add_argument(
        "--mode",
        choices=["lint", "test", "full", "restart"],
        default="lint",
        help="Watch mode: lint (ruff), test (pytest), full (all checks), restart (app reload)",
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.0,
        help="Debounce time in seconds between runs (default: 1.0)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to watch (default: current directory)",
    )

    args = parser.parse_args()

    # Set up event handler and observer
    event_handler = DevelopmentWatcher(mode=args.mode, debounce_seconds=args.debounce)
    observer = Observer()

    watch_path = Path(args.path).resolve()
    observer.schedule(event_handler, str(watch_path), recursive=True)

    print(f"👀 Watching for changes in: {watch_path}")
    print(f"🔧 Mode: {args.mode}")
    print(f"⏱️ Debounce: {args.debounce}s")
    print("Press Ctrl+C to stop\n")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping watcher...")
        observer.stop()
        observer.join()
        print("✅ Watcher stopped")


if __name__ == "__main__":
    main()
