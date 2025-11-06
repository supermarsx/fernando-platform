#!/bin/bash
cd /workspace/accounting-automation/backend
. venv/bin/activate
export PYTHONPATH=/workspace/accounting-automation/backend:$PYTHONPATH
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
