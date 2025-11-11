@echo off
REM DTC Verification Script
REM This sets up debug flags and runs the app with full DTC logging

title DTC Verification - APPSIERRA
cls

echo.
echo ============================================================================
echo DTC MESSAGE FLOW VERIFICATION
echo ============================================================================
echo.
echo This will start APPSIERRA with full DTC debug logging enabled.
echo You will see EVERY DTC message printed to console.
echo.
echo Expected sequence:
echo   1. "DTC connected"
echo   2. "Type: 2 (LogonResponse)"
echo   3. "Type: 401 (TradeAccountResponse)"
echo   4. "Type: 306 (PositionUpdate)" messages
echo   5. "Type: 600 or 602 (Balance...)" messages
echo.
echo Press ANY KEY to continue...
pause >nul

cls
echo.
echo ============================================================================
echo Starting APPSIERRA with DEBUG_DTC=1 and DEBUG_DATA=1
echo ============================================================================
echo.

REM Enable debug flags
set DEBUG_DTC=1
set DEBUG_DATA=1
set DEBUG_NETWORK=1

REM Run the app
python main.py

echo.
echo ============================================================================
echo DTC Verification Complete
echo Check the messages above for DTC handshake and message flow
echo ============================================================================
echo.
pause
