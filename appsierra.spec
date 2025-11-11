# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for APPSIERRA

This file configures how PyInstaller builds the APPSIERRA executable.

Usage:
    poetry run pyinstaller appsierra.spec

Output:
    - dist/APPSIERRA/       (directory with executable and dependencies)
    - dist/APPSIERRA.exe    (Windows) or dist/APPSIERRA (Linux/Mac)
"""

import sys
from pathlib import Path

# ============================================================================
# Build Configuration
# ============================================================================

block_cipher = None
project_root = Path(".").absolute()

# Application metadata
APP_NAME = "APPSIERRA"
APP_VERSION = "0.1.0"
APP_AUTHOR = "APPSIERRA Team"

# ============================================================================
# Analysis - Collect all Python files and dependencies
# ============================================================================

a = Analysis(
    ['main.py'],  # Entry point
    pathex=[str(project_root)],  # Additional paths to search for imports
    binaries=[],  # Binary dependencies (e.g., compiled libraries)
    datas=[
        # Add data files here (images, configs, etc.)
        # Example: ('config/settings.json', 'config'),
        # Example: ('assets/*.png', 'assets'),
    ],
    hiddenimports=[
        # Add hidden imports that PyInstaller might miss
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pyqtgraph',
        'config.theme',
        'config.settings',
        'core.app_manager',
        'panels',
        'services',
        'ui',
        'utils',
        'widgets',
    ],
    hookspath=[],  # Custom hooks directory
    hooksconfig={},
    runtime_hooks=[],  # Runtime hooks to execute at startup
    excludes=[
        # Exclude unnecessary packages to reduce size
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'wheel',
        'pip',
        'pytest',
        'mypy',
        'ruff',
        'black',
        'isort',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# PYZ - Create a compressed archive of Python modules
# ============================================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# ============================================================================
# EXE - Create the executable
# ============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Create a one-folder distribution
    name=APP_NAME,
    debug=False,  # Set to True for debug output
    bootloader_ignore_signals=False,
    strip=False,  # Strip symbols (reduces size on Linux/Mac)
    upx=True,  # Use UPX compression (set to False if issues occur)
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows-specific options
    version='file_version_info.txt' if sys.platform == 'win32' else None,
    icon='assets/appsierra.ico' if Path('assets/appsierra.ico').exists() else None,
)

# ============================================================================
# COLLECT - Collect all files into distribution directory
# ============================================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# ============================================================================
# Build Notes
# ============================================================================
#
# One-File Build (alternative):
# To create a single executable file instead of a directory, modify EXE:
#
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,     # Add these
#     a.zipfiles,     # Add these
#     a.datas,        # Add these
#     [],
#     name=APP_NAME,
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     disable_windowed_traceback=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )
#
# Remove the COLLECT section when using one-file mode.
#
# ============================================================================
# Common Issues
# ============================================================================
#
# 1. Missing Qt plugins:
#    Add to datas: ('path/to/PyQt6/Qt6/plugins', 'PyQt6/Qt6/plugins')
#
# 2. Missing DLLs (Windows):
#    Add to binaries: ('path/to/file.dll', '.')
#
# 3. Application doesn't start:
#    Set console=True to see error messages
#
# 4. Large executable size:
#    - Set upx=False if UPX causes issues
#    - Add more packages to excludes list
#    - Use --exclude-module flag with pyinstaller command
#
# 5. PyQt6 not found:
#    Ensure PyQt6 is installed in the same environment as PyInstaller
#
# ============================================================================
