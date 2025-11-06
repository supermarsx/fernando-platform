#!/bin/bash
cd /workspace/fernando/backend
. venv/bin/activate
echo "Installing missing dependencies..."
pip install -q jinja2 stripe requests
echo "✓ Dependencies installed"
export PYTHONPATH=/workspace/fernando/backend:$PYTHONPATH
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
