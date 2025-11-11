#!/bin/bash
# APPSIERRA Test Runner with Auto-Healing
#
# This script runs the complete test suite and automatically triggers
# self-healing if tests fail.
#
# Usage:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh --install          # Install dependencies first
#   ./run_tests.sh --coverage         # Run with coverage report
#   ./run_tests.sh --performance      # Run only performance tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}APPSIERRA Test Suite with Self-Healing${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Parse arguments
INSTALL=false
COVERAGE=false
PERFORMANCE_ONLY=false

for arg in "$@"; do
    case $arg in
        --install)
            INSTALL=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --performance)
            PERFORMANCE_ONLY=true
            shift
            ;;
    esac
done

# Install dependencies if requested
if [ "$INSTALL" = true ]; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
    echo -e "${GREEN}Dependencies installed!${NC}"
fi

# Build pytest command
PYTEST_CMD="python -m pytest"

if [ "$PERFORMANCE_ONLY" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -m performance"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -q --cov=panels --cov=core --cov-report=term-missing --disable-warnings"
else
    PYTEST_CMD="$PYTEST_CMD -q --disable-warnings"
fi

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
echo -e "${BLUE}Command: $PYTEST_CMD${NC}\n"

if $PYTEST_CMD; then
    TEST_EXIT_CODE=0
    echo -e "\n${GREEN}======================================================================${NC}"
    echo -e "${GREEN}TESTS PASSED!${NC}"
    echo -e "${GREEN}======================================================================${NC}"
else
    TEST_EXIT_CODE=$?
    echo -e "\n${RED}======================================================================${NC}"
    echo -e "${RED}TESTS FAILED (Exit code: $TEST_EXIT_CODE)${NC}"
    echo -e "${RED}======================================================================${NC}"
fi

# Check if diagnostic file was generated
if [ -f "test_diagnostics.json" ]; then
    echo -e "\n${YELLOW}Diagnostic data generated: test_diagnostics.json${NC}"
else
    echo -e "\n${YELLOW}No diagnostic data found (tests may not have run)${NC}"
fi

# Run self-healing if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo -e "\n${YELLOW}======================================================================${NC}"
    echo -e "${YELLOW}TRIGGERING SELF-HEALING SYSTEM${NC}"
    echo -e "${YELLOW}======================================================================${NC}\n"

    if python selfheal.py; then
        HEAL_EXIT_CODE=$?
    else
        HEAL_EXIT_CODE=$?
    fi

    if [ -f "selfheal_report.json" ]; then
        echo -e "\n${GREEN}Self-healing report generated: selfheal_report.json${NC}"

        # Show summary
        if command -v jq &> /dev/null; then
            echo -e "\n${BLUE}Issue Summary:${NC}"
            jq '.summary' selfheal_report.json
        fi
    fi
else
    echo -e "\n${YELLOW}Self-healing skipped (tests passed)${NC}"
fi

# Show coverage if generated
if [ "$COVERAGE" = true ] && [ -f ".coverage" ]; then
    echo -e "\n${BLUE}Coverage report generated!${NC}"
    echo -e "${BLUE}View HTML report: htmlcov/index.html${NC}"
fi

# Final status
echo -e "\n${BLUE}======================================================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}STATUS: SUCCESS${NC}"
else
    echo -e "${RED}STATUS: FAILURES DETECTED${NC}"
    echo -e "${YELLOW}Review selfheal_report.json for automatic fixes${NC}"
fi
echo -e "${BLUE}======================================================================${NC}\n"

exit $TEST_EXIT_CODE
