#!/usr/bin/env python3
"""Build Script for APPSIERRA Executable

This script builds the APPSIERRA executable using PyInstaller.

Usage:
    poetry run python build.py              # Build with default settings
    poetry run python build.py --clean      # Clean build (remove old files)
    poetry run python build.py --onefile    # Build single executable
    poetry run python build.py --debug      # Build with debug console
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def clean_build_dirs() -> None:
    """Remove build artifacts and dist directories."""
    print("🧹 Cleaning build directories...")
    dirs_to_clean = ["build", "dist", "__pycache__"]

    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  ✓ Removed {dir_name}/")

    # Remove .spec generated cache
    for spec_cache in Path(".").glob("*.spec.cache"):
        spec_cache.unlink()
        print(f"  ✓ Removed {spec_cache}")

    print("✅ Clean complete\n")


def run_pyinstaller(onefile: bool = False, debug: bool = False) -> int:
    """
    Run PyInstaller to build the executable.

    Args:
        onefile: Build as single file instead of directory
        debug: Enable debug mode (console window)

    Returns:
        Exit code from PyInstaller
    """
    print("🔨 Building APPSIERRA executable...\n")

    cmd = ["poetry", "run", "pyinstaller"]

    if onefile:
        cmd.extend(
            [
                "--onefile",
                "--name",
                "APPSIERRA",
                "--windowed",  # No console for GUI app (unless debug)
            ]
        )
        if debug:
            cmd.remove("--windowed")
            cmd.append("--console")
        cmd.append("main.py")
    else:
        # Use the spec file for directory build
        if debug:
            print("⚠️ Debug mode: Modifying spec for console output")
        cmd.append("appsierra.spec")

    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running PyInstaller: {e}")
        return 1


def show_build_info() -> None:
    """Display build output information."""
    dist_dir = Path("dist")

    if not dist_dir.exists():
        print("⚠️ No dist/ directory found")
        return

    print("\n" + "=" * 70)
    print("✅ Build completed successfully!")
    print("=" * 70)
    print("\n📦 Output location:")

    for item in dist_dir.iterdir():
        size_mb = sum(f.stat().st_size for f in item.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  • {item.name} ({size_mb:.1f} MB)")

    print("\n🚀 To run the executable:")
    if (dist_dir / "APPSIERRA").is_dir():
        print("  cd dist/APPSIERRA")
        print("  ./APPSIERRA  (Linux/Mac)")
        print("  APPSIERRA.exe  (Windows)")
    else:
        print("  cd dist")
        print("  ./APPSIERRA  (Linux/Mac)")
        print("  APPSIERRA.exe  (Windows)")
    print()


def main() -> int:
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(description="Build APPSIERRA executable with PyInstaller")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build as single executable file (slower startup, more portable)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with console window for debugging",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  APPSIERRA Build Script")
    print("=" * 70)
    print()

    # Clean if requested
    if args.clean:
        clean_build_dirs()

    # Run build
    exit_code = run_pyinstaller(onefile=args.onefile, debug=args.debug)

    if exit_code == 0:
        show_build_info()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
