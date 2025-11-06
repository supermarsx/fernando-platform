#!/bin/bash
set -e

echo "=== Installing pytest and running Enterprise Billing Tests ==="
echo ""

# Activate virtual environment
source /workspace/fernando/backend/venv/bin/activate

# Navigate to backend directory
cd /workspace/fernando/backend

# Set PYTHONPATH
export PYTHONPATH=/workspace/fernando/backend:$PYTHONPATH

echo "Installing pytest..."
pip install -q pytest pytest-asyncio
echo "✓ pytest installed"
echo ""

echo "Running comprehensive test suite..."
python -m pytest test_enterprise_billing.py -v --tb=short
echo ""

echo "=== Tests Complete ==="
