#!/bin/bash
set -e

echo "=== Enterprise Billing Setup ==="
echo ""

# Activate virtual environment
source /workspace/fernando/backend/venv/bin/activate

# Navigate to backend directory
cd /workspace/fernando/backend

# Set PYTHONPATH to include backend directory
export PYTHONPATH=/workspace/fernando/backend:$PYTHONPATH

echo "Step 1: Running database migration..."
python migrations/versions/007_add_enterprise_billing.py
echo "✓ Migration completed"
echo ""

echo "Step 2: Initializing sample data..."
python initialize_enterprise_billing.py
echo "✓ Initialization completed"
echo ""

echo "Step 3: Running comprehensive test suite..."
python -m pytest test_enterprise_billing.py -v --tb=short
echo ""

echo "=== Setup Complete ==="
