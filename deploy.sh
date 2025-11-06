#!/bin/bash

# Production Deployment Script for Fernando Platform
# This script deploys the complete enterprise application

set -e  # Exit on any error

echo "========================================="
echo "  Fernando Platform"
echo "  Production Deployment Script"
echo "========================================="
echo ""

# Configuration
PROJECT_DIR="/workspace/fernando"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend/accounting-frontend"
DEPLOY_ENV=${1:-"production"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    print_warning "pnpm not found, installing..."
    npm install -g pnpm
fi

print_step "Prerequisites check passed"

# Step 2: Create environment file if not exists
print_step "Setting up environment configuration..."

if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_warning ".env file not found, creating from example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    print_warning "Please edit .env file with your API keys before continuing"
    print_warning "Press Enter when ready..."
    read
fi

# Step 3: Install backend dependencies
print_step "Installing backend dependencies..."
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install production OCR and LLM packages
pip install paddleocr paddlepaddle openai anthropic

print_step "Backend dependencies installed"

# Step 4: Initialize database
print_step "Initializing database..."

# Run migrations if alembic is configured
if [ -f "alembic.ini" ]; then
    alembic upgrade head
else
    # Database will be auto-created on first run
    print_warning "No alembic.ini found, database will be created on first run"
fi

print_step "Database initialized"

# Step 5: Build frontend
print_step "Building frontend..."
cd "$FRONTEND_DIR"

pnpm install
pnpm run build

print_step "Frontend build completed"

# Step 6: Create necessary directories
print_step "Creating required directories..."
cd "$PROJECT_DIR"

mkdir -p uploads/documents
mkdir -p uploads/temp
mkdir -p logs

print_step "Directories created"

# Step 7: Set up systemd service (optional)
if command -v systemctl &> /dev/null; then
    print_step "Setting up systemd service..."
    
    cat > /tmp/fernando.service << EOF
[Unit]
Description=Fernando Platform
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
Environment="PYTHONPATH=$BACKEND_DIR"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    print_warning "Systemd service file created at /tmp/fernando.service"
    print_warning "To install: sudo cp /tmp/fernando.service /etc/systemd/system/"
    print_warning "Then: sudo systemctl enable fernando && sudo systemctl start fernando"
fi

# Step 8: Start services
print_step "Starting services..."

# Kill existing processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "python3 -m http.server 3000" 2>/dev/null || true

# Start backend
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PROJECT_DIR/backend.pid"

sleep 3

# Check if backend started
if ps -p $BACKEND_PID > /dev/null; then
    print_step "Backend started successfully (PID: $BACKEND_PID)"
else
    print_error "Backend failed to start. Check logs at $PROJECT_DIR/logs/backend.log"
    exit 1
fi

# Start frontend
cd "$FRONTEND_DIR/dist"
nohup python3 -m http.server 3000 > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PROJECT_DIR/frontend.pid"

sleep 2

if ps -p $FRONTEND_PID > /dev/null; then
    print_step "Frontend started successfully (PID: $FRONTEND_PID)"
else
    print_error "Frontend failed to start. Check logs at $PROJECT_DIR/logs/frontend.log"
    exit 1
fi

# Step 9: Health check
print_step "Performing health check..."

sleep 3

BACKEND_HEALTH=$(curl -s http://localhost:8000/health || echo "failed")
if [[ "$BACKEND_HEALTH" == *"healthy"* ]]; then
    print_step "Backend health check passed"
else
    print_error "Backend health check failed"
    cat "$PROJECT_DIR/logs/backend.log" | tail -20
    exit 1
fi

FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/)
if [ "$FRONTEND_HEALTH" = "200" ]; then
    print_step "Frontend health check passed"
else
    print_error "Frontend health check failed (HTTP $FRONTEND_HEALTH)"
    exit 1
fi

# Step 10: Display deployment information
echo ""
echo "========================================="
echo "  DEPLOYMENT SUCCESSFUL!"
echo "========================================="
echo ""
echo -e "${GREEN}Application URLs:${NC}"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Admin:     http://localhost:3000/admin"
echo ""
echo -e "${GREEN}Process Information:${NC}"
echo "  Backend PID:   $BACKEND_PID"
echo "  Frontend PID:  $FRONTEND_PID"
echo ""
echo -e "${GREEN}Log Files:${NC}"
echo "  Backend:  $PROJECT_DIR/logs/backend.log"
echo "  Frontend: $PROJECT_DIR/logs/frontend.log"
echo ""
echo -e "${GREEN}Management Commands:${NC}"
echo "  Stop:    pkill -f 'uvicorn app.main:app' && pkill -f 'python3 -m http.server 3000'"
echo "  Restart: $0"
echo "  Logs:    tail -f $PROJECT_DIR/logs/backend.log"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Configure .env with your API keys"
echo "  2. Set up SSL certificate for HTTPS"
echo "  3. Configure reverse proxy (nginx/apache)"
echo "  4. Set up monitoring and alerts"
echo "  5. Configure automatic backups"
echo ""
echo "========================================="
