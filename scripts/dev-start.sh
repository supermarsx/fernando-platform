#!/bin/bash

# Quick development start script
set -e

echo "🚀 Starting Fernando Development Environment"
echo "========================================================"

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Python virtual environment not found. Please run setup-dev.sh first."
    exit 1
fi

# Function to kill background processes on script exit
cleanup() {
    echo ""
    echo "🛑 Shutting down development servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "✅ Development servers stopped."
    exit 0
}

trap cleanup INT TERM

# Activate Python virtual environment
echo "🐍 Activating Python virtual environment..."
source backend/venv/bin/activate

# Start backend server in background
echo "🔧 Starting backend server..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 3

# Start frontend server in background
echo "⚛️ Starting frontend server..."
cd frontend/accounting-frontend
npm run dev &
FRONTEND_PID=$!
cd ../../..

echo ""
echo "✅ Development servers started successfully!"
echo ""
echo "📍 Server URLs:"
echo "   Backend API:    http://localhost:8000"
echo "   API Docs:       http://localhost:8000/docs"
echo "   Frontend App:   http://localhost:5173"
echo ""
echo "🔧 Available commands:"
echo "   Backend logs:   docker-compose logs -f backend"
echo "   Frontend logs:  docker-compose logs -f frontend"
echo ""
echo "⏹️  Press Ctrl+C to stop all servers"
echo ""

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID