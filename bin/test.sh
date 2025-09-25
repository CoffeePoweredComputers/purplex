#!/bin/bash
# =====================================================================================
# PURPLEX TEST RUNNER SCRIPT
# =====================================================================================
# Runs all test suites with proper configuration
# =====================================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}              Purplex Test Suite Runner                 ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"

# Parse arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-false}

# Show test plan
echo -e "\n${YELLOW}Test Configuration:${NC}"
echo -e "  • Test type: $TEST_TYPE"
echo -e "  • Coverage: $COVERAGE"

# Set up test environment
export PURPLEX_ENV=test
export DJANGO_SETTINGS_MODULE=purplex.settings

# Load test environment variables
if [ -f ".env.test" ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
fi

# Function to run tests with timing
run_test_suite() {
    local suite_name=$1
    local test_command=$2

    echo -e "\n${YELLOW}Running $suite_name...${NC}"
    START_TIME=$(date +%s)

    if eval $test_command; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo -e "${GREEN}✓ $suite_name passed (${DURATION}s)${NC}"
        return 0
    else
        echo -e "${RED}✗ $suite_name failed${NC}"
        return 1
    fi
}

# Initialize test results
FAILED_SUITES=()

# Run tests based on type
case $TEST_TYPE in
    unit)
        run_test_suite "Unit Tests" "pytest -m unit -q" || FAILED_SUITES+=("Unit")
        ;;
    integration)
        run_test_suite "Integration Tests" "pytest -m integration -q" || FAILED_SUITES+=("Integration")
        ;;
    frontend)
        run_test_suite "Frontend Tests" "cd purplex/client && yarn test:unit" || FAILED_SUITES+=("Frontend")
        ;;
    lint)
        run_test_suite "Python Linting" "flake8 purplex/ --max-line-length=120" || FAILED_SUITES+=("Python Lint")
        run_test_suite "Frontend Linting" "cd purplex/client && yarn lint:check" || FAILED_SUITES+=("Frontend Lint")
        ;;
    security)
        run_test_suite "Security Scan" "bandit -r purplex/ -ll" || FAILED_SUITES+=("Security")
        run_test_suite "Dependency Check" "safety check" || FAILED_SUITES+=("Dependencies")
        ;;
    all)
        # Run all test suites
        run_test_suite "Unit Tests" "pytest -m unit -q" || FAILED_SUITES+=("Unit")
        run_test_suite "Integration Tests" "pytest -m integration -q" || FAILED_SUITES+=("Integration")
        run_test_suite "Frontend Tests" "cd purplex/client && yarn test:unit" || FAILED_SUITES+=("Frontend")
        run_test_suite "Python Linting" "flake8 purplex/ --max-line-length=120" || FAILED_SUITES+=("Python Lint")
        run_test_suite "Frontend Linting" "cd purplex/client && yarn lint:check" || FAILED_SUITES+=("Frontend Lint")
        run_test_suite "Type Checking" "mypy purplex/ --ignore-missing-imports" || FAILED_SUITES+=("Type Check")
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Available types: unit, integration, frontend, lint, security, all"
        exit 1
        ;;
esac

# Run coverage if requested
if [ "$COVERAGE" == "coverage" ] || [ "$COVERAGE" == "true" ]; then
    echo -e "\n${YELLOW}Generating coverage report...${NC}"
    pytest --cov=purplex --cov-report=html --cov-report=term
    echo -e "${GREEN}✓ Coverage report generated in htmlcov/${NC}"
fi

# Summary
echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}"
if [ ${#FAILED_SUITES[@]} -eq 0 ]; then
    echo -e "${GREEN}         All tests passed successfully! 🎉             ${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}           Some tests failed! ❌                       ${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo -e "\n${RED}Failed suites:${NC}"
    for suite in "${FAILED_SUITES[@]}"; do
        echo -e "  • $suite"
    done
    exit 1
fi