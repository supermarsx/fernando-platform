#!/bin/bash

# Development setup script for Fernando project
set -e

echo "🚀 Setting up Fernando Development Environment"
echo "==========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    echo "🔍 Checking requirements..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9+"
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        print_error "pip is not installed. Please install pip"
        exit 1
    fi
    
    print_status "All requirements met"
}

# Setup Python environment
setup_python() {
    echo "🐍 Setting up Python environment..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip"
    pip install --upgrade pip
    
    # Install development dependencies
    print_status "Installing Python development dependencies"
    pip install -r requirements-dev.txt
    
    # Install main dependencies
    print_status "Installing Python main dependencies"
    pip install -r requirements.txt
    
    cd ..
    print_status "Python environment setup complete"
}

# Setup Node.js environment
setup_nodejs() {
    echo "📦 Setting up Node.js environment..."
    
    cd frontend/accounting-frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies"
    npm install
    
    cd ../..
    print_status "Node.js environment setup complete"
}

# Setup pre-commit hooks
setup_precommit() {
    echo "🔧 Setting up pre-commit hooks..."
    
    if ! command -v pre-commit &> /dev/null; then
        print_warning "pre-commit not found, installing..."
        pip install pre-commit
    fi
    
    pre-commit install
    pre-commit install --hook-type commit-msg
    
    print_status "Pre-commit hooks installed"
}

# Create environment files
setup_env_files() {
    echo "📝 Setting up environment files..."
    
    # Backend .env file
    if [ ! -f "backend/.env" ]; then
        cat > backend/.env << EOF
# Development Environment Configuration
DEBUG=true
DATABASE_URL=sqlite:///./accounting_automation.db
SECRET_KEY=development-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="Fernando API"
PROJECT_VERSION=0.1.0

# CORS Configuration
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]

# File Upload Configuration
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=uploads/documents

# Logging Configuration
LOG_LEVEL=INFO

# Feature Flags
ENABLE_DOCUMENT_PROCESSING=true
ENABLE_OCR_PROCESSING=true
ENABLE_LLM_EXTRACTION=true

# External Services (Development/Mock)
MOCK_LLM_SERVICE=true
MOCK_OCR_SERVICE=true
EOF
        print_status "Created backend .env file"
    else
        print_warning "Backend .env file already exists"
    fi
    
    # Frontend .env file
    if [ ! -f "frontend/accounting-frontend/.env.local" ]; then
        cat > frontend/accounting-frontend/.env.local << EOF
# Frontend Development Environment Configuration
VITE_API_URL=http://localhost:8000
VITE_API_V1_STR=/api/v1
VITE_APP_NAME=Fernando
VITE_APP_VERSION=0.1.0

# Development Configuration
VITE_DEBUG=true
VITE_LOG_LEVEL=debug

# Feature Flags
VITE_ENABLE_MOCK_DATA=true
VITE_ENABLE_DEV_TOOLS=true

# Upload Configuration
VITE_MAX_FILE_SIZE=10485760  # 10MB
VITE_ALLOWED_FILE_TYPES=pdf,jpg,jpeg,png,doc,docx

# UI Configuration
VITE_DEFAULT_THEME=light
VITE_ENABLE_DARK_MODE=true
EOF
        print_status "Created frontend .env.local file"
    else
        print_warning "Frontend .env.local file already exists"
    fi
}

# Initialize database
setup_database() {
    echo "🗄️ Setting up database..."
    
    cd backend
    source venv/bin/activate
    
    # Run database migrations
    print_status "Running database migrations"
    alembic upgrade head
    
    # Create upload directories
    mkdir -p uploads/documents
    mkdir -p uploads/temp
    
    cd ../..
    print_status "Database setup complete"
}

# Setup IDE configuration
setup_ide() {
    echo "🛠️ Setting up IDE configuration..."
    
    # VS Code settings
    mkdir -p .vscode
    
    # Python settings
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./backend/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/node_modules": true,
        "**/dist": true,
        "**/build": true
    }
}
EOF

    # JavaScript/TypeScript settings
    cat > frontend/accounting-frontend/.vscode/settings.json << EOF
{
    "typescript.preferences.importModuleSpecifier": "relative",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": true
    },
    "eslint.validate": [
        "javascript",
        "typescript",
        "typescriptreact"
    ],
    "files.exclude": {
        "**/node_modules": true,
        "**/dist": true,
        "**/build": true,
        "**/.next": true
    }
}
EOF

    print_status "IDE configuration created"
}

# Final setup
final_setup() {
    echo "🎉 Final setup steps..."
    
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    
    print_status "Setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Activate the Python virtual environment:"
    echo "   cd backend && source venv/bin/activate"
    echo ""
    echo "2. Start the development servers:"
    echo "   make dev-all"
    echo ""
    echo "3. Access the applications:"
    echo "   Frontend: http://localhost:5173"
    echo "   Backend API: http://localhost:8000"
    echo "   API Documentation: http://localhost:8000/docs"
    echo ""
    echo "4. Run tests:"
    echo "   make test"
    echo ""
    echo "📚 Useful commands:"
    echo "   make help          - Show all available commands"
    echo "   make lint          - Run code quality checks"
    echo "   make format        - Format code"
    echo "   make test-coverage - Run tests with coverage"
    echo ""
    echo "Happy coding! 🚀"
}

# Main execution
main() {
    check_requirements
    setup_python
    setup_nodejs
    setup_precommit
    setup_env_files
    setup_database
    setup_ide
    final_setup
}

# Run main function
main "$@"