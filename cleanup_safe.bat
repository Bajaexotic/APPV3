@echo off
REM ============================================================================
REM Safe Cleanup Script for APPSIERRA
REM Removes only CONFIRMED unused/redundant files
REM ============================================================================

echo.
echo ============================================================================
echo  APPSIERRA - Safe Cleanup Script
echo ============================================================================
echo.
echo This script will remove:
echo   - Unused DTC client (dtc_json_client.py)
echo   - Unused services (dtc_ledger, dtc_report_cli, market_joiner)
echo   - Unused trade_metrics
echo   - Temporary files (.tmp)
echo   - Build artifacts
echo.
echo Files will be DELETED (but recoverable via Git)
echo.
pause

cd /d "%~dp0"

echo.
echo [1/5] Deleting unused DTC client...
if exist services\dtc_json_client.py (
    del services\dtc_json_client.py
    echo   DELETED: services\dtc_json_client.py
) else (
    echo   SKIP: File not found
)

echo.
echo [2/5] Deleting unused services...
if exist services\dtc_ledger.py (
    del services\dtc_ledger.py
    echo   DELETED: services\dtc_ledger.py
)
if exist services\dtc_report_cli.py (
    del services\dtc_report_cli.py
    echo   DELETED: services\dtc_report_cli.py
)
if exist services\market_joiner.py (
    del services\market_joiner.py
    echo   DELETED: services\market_joiner.py
)
if exist services\trade_metrics.py (
    del services\trade_metrics.py
    echo   DELETED: services\trade_metrics.py
)

echo.
echo [3/5] Deleting temporary files...
if exist panels\panel1.py.tmp (
    del panels\panel1.py.tmp
    echo   DELETED: panels\panel1.py.tmp
)

echo.
echo [4/5] Deleting build artifacts...
if exist main.build (
    rmdir /s /q main.build
    echo   DELETED: main.build\
)
if exist main.onefile-build (
    rmdir /s /q main.onefile-build
    echo   DELETED: main.onefile-build\
)
if exist main.dist (
    rmdir /s /q main.dist
    echo   DELETED: main.dist\
)

echo.
echo [5/5] Cleaning Python cache files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rmdir /s /q "%%d"
    echo   DELETED: %%d
)

echo.
echo ============================================================================
echo  Cleanup Complete!
echo ============================================================================
echo.
echo Summary:
echo   - Removed unused DTC client (~30KB)
echo   - Removed unused services (~21KB)
echo   - Removed temp files
echo   - Removed build artifacts (~10-100MB)
echo   - Cleaned Python caches
echo.
echo Next steps:
echo   1. Run: python main.py  (to verify app still works)
echo   2. Run: git status      (to see what was deleted)
echo   3. Run: git add -A      (to stage changes)
echo   4. Run: git commit -m "chore: cleanup unused code"
echo.
pause
