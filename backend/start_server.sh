#!/bin/bash
cd /workspace/fernando/backend
. venv/bin/activate
export PYTHONPATH=/workspace/fernando/backend:$PYTHONPATH
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
