#!/bin/bash
set -e

echo "Installing backend dependencies..."
cd /workspace/fernando/backend
. venv/bin/activate
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

echo "Starting backend server..."
export PYTHONPATH=/workspace/fernando/backend:$PYTHONPATH
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
