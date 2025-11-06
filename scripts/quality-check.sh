#!/bin/bash

# Code quality check script
set -e

echo "🔍 Running Code Quality Checks"
echo "=============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Function to run command and check result
run_check() {
    local cmd=$1
    local name=$2
    
    echo -n "🔍 $name... "
    if $cmd; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "🐍 Backend Code Quality Checks"
echo "------------------------------"

cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Python virtual environment not found${NC}"
    echo "Please run: ./scripts/setup-dev.sh"
    exit 1
fi

source venv/bin/activate

# Run all backend checks
run_check "black --check ." "Black formatter"
run_check "isort --check-only ." "Import sorting"
run_check "flake8 ." "Flake8 linting"
run_check "mypy ." "Type checking"
run_check "pytest -q --tb=short" "Unit tests"

cd ..

echo ""
echo "⚛️ Frontend Code Quality Checks"
echo "-------------------------------"

cd frontend/accounting-frontend

# Run all frontend checks
run_check "npm run lint --silent" "ESLint"
run_check "npm run type-check --silent" "TypeScript check"
run_check "npm run test:run --silent" "Unit tests"

cd ../../..

echo ""
echo "🔐 Security Checks"
echo "------------------"

cd backend
run_check "safety check" "Dependency vulnerabilities"
run_check "bandit -r . -f json" "Security analysis"
cd ..

echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All code quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS check(s) failed${NC}"
    echo ""
    echo "To fix common issues, run:"
    echo "  make format        - Auto-format code"
    echo "  make lint:fix      - Auto-fix linting issues"
    echo ""
    exit 1
fi