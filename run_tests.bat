@echo off
REM APPSIERRA Test Runner with Auto-Healing (Windows)
REM
REM This script runs the complete test suite and automatically triggers
REM self-healing if tests fail.
REM
REM Usage:
REM   run_tests.bat                    - Run all tests
REM   run_tests.bat --install          - Install dependencies first
REM   run_tests.bat --coverage         - Run with coverage report
REM   run_tests.bat --performance      - Run only performance tests

echo ======================================================================
echo APPSIERRA Test Suite with Self-Healing
echo ======================================================================

set INSTALL=0
set COVERAGE=0
set PERFORMANCE_ONLY=0

REM Parse arguments
:parse_args
if "%1"=="--install" set INSTALL=1 & shift & goto parse_args
if "%1"=="--coverage" set COVERAGE=1 & shift & goto parse_args
if "%1"=="--performance" set PERFORMANCE_ONLY=1 & shift & goto parse_args

REM Install dependencies if requested
if %INSTALL%==1 (
    echo Installing test dependencies...
    pip install -r requirements-test.txt
    echo Dependencies installed!
)

REM Build pytest command
set PYTEST_CMD=python -m pytest

if %PERFORMANCE_ONLY%==1 (
    set PYTEST_CMD=%PYTEST_CMD% -m performance
)

if %COVERAGE%==1 (
    set PYTEST_CMD=%PYTEST_CMD% -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings
) else (
    set PYTEST_CMD=%PYTEST_CMD% -q --disable-warnings
)

REM Run tests
echo.
echo Running tests...
echo Command: %PYTEST_CMD%
echo.

%PYTEST_CMD%
set TEST_EXIT_CODE=%ERRORLEVEL%

if %TEST_EXIT_CODE%==0 (
    echo.
    echo ======================================================================
    echo TESTS PASSED!
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo TESTS FAILED (Exit code: %TEST_EXIT_CODE%)
    echo ======================================================================
)

REM Check if diagnostic file was generated
if exist test_diagnostics.json (
    echo.
    echo Diagnostic data generated: test_diagnostics.json
) else (
    echo.
    echo No diagnostic data found (tests may not have run)
)

REM Run self-healing if tests failed
if %TEST_EXIT_CODE% NEQ 0 (
    echo.
    echo ======================================================================
    echo TRIGGERING SELF-HEALING SYSTEM
    echo ======================================================================
    echo.

    python selfheal.py
    set HEAL_EXIT_CODE=%ERRORLEVEL%

    if exist selfheal_report.json (
        echo.
        echo Self-healing report generated: selfheal_report.json
    )
) else (
    echo.
    echo Self-healing skipped (tests passed)
)

REM Show coverage if generated
if %COVERAGE%==1 (
    if exist .coverage (
        echo.
        echo Coverage report generated!
        echo View HTML report: htmlcov\index.html
    )
)

REM Final status
echo.
echo ======================================================================
if %TEST_EXIT_CODE%==0 (
    echo STATUS: SUCCESS
) else (
    echo STATUS: FAILURES DETECTED
    echo Review selfheal_report.json for automatic fixes
)
echo ======================================================================
echo.

exit /b %TEST_EXIT_CODE%
