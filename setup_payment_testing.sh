#!/bin/bash

# Payment System Testing Setup Script
# This script installs dependencies and starts the servers

echo "=========================================="
echo "Payment Integration Testing Setup"
echo "=========================================="
echo ""

# Step 1: Install Backend Dependencies
echo "[1/5] Installing backend Python dependencies..."
cd /workspace/fernando/backend
/usr/bin/python3 -m pip install --quiet --upgrade pip
/usr/bin/python3 -m pip install --quiet -r requirements.txt
/usr/bin/python3 -m pip install --quiet stripe requests

echo "✓ Backend dependencies installed"
echo ""

# Step 2: Verify Installation
echo "[2/5] Verifying package installation..."
/usr/bin/python3 -c "import sqlalchemy, fastapi, stripe; print('✓ Core packages verified')"
echo ""

# Step 3: Initialize Database
echo "[3/5] Initializing database and seeding subscription plans..."
cd /workspace/fernando/backend
/usr/bin/python3 -c "from app.db.session import init_db; init_db(); print('✓ Database initialized')"
/usr/bin/python3 seed_subscription_plans.py
echo ""

# Step 4: Start Backend Server
echo "[4/5] Starting backend server..."
echo "Backend will run on: http://0.0.0.0:8000"
echo "API docs available at: http://localhost:8000/docs"
cd /workspace/fernando/backend
/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
sleep 5
echo ""

# Step 5: Verify Backend
echo "[5/5] Verifying backend is running..."
curl -s http://localhost:8000/docs > /dev/null && echo "✓ Backend is responding" || echo "✗ Backend not responding"
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "1. Start frontend: cd frontend/accounting-frontend && npm run dev"
echo "2. Open browser to http://localhost:3000"
echo "3. Register a test user"
echo "4. Navigate to /billing"
echo "5. Test payment with card: 4242 4242 4242 4242"
echo ""
echo "Backend PID: $BACKEND_PID (use 'kill $BACKEND_PID' to stop)"
