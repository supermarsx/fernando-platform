# Development Infrastructure Guide

Comprehensive guide for the Fernando development infrastructure setup and workflows.

## Table of Contents

1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Development Workflow](#development-workflow)
4. [Code Quality Tools](#code-quality-tools)
5. [Testing Framework](#testing-framework)
6. [Pre-commit Hooks](#pre-commit-hooks)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Configuration Reference](#configuration-reference)
9. [Troubleshooting](#troubleshooting)

## Overview

This project includes a comprehensive development infrastructure designed to ensure code quality, consistency, and automated workflows. The infrastructure covers:

- **Code Formatting**: Black (Python), Prettier (JavaScript/TypeScript)
- **Linting**: flake8/Ruff (Python), ESLint (JavaScript/TypeScript)
- **Type Checking**: MyPy (Python), TypeScript compiler (JavaScript/TypeScript)
- **Testing**: pytest (Python), Vitest (JavaScript/TypeScript)
- **Pre-commit Hooks**: Automated quality checks before commits
- **CI/CD Pipeline**: Automated testing and deployment
- **Documentation**: Automated documentation generation

## Initial Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or pnpm
- Git

### Quick Setup

Run the automated setup script:

```bash
./scripts/setup-dev.sh
```

This will:
- Install all dependencies
- Set up Python virtual environment
- Configure pre-commit hooks
- Create environment files
- Initialize database
- Configure IDE settings

### Manual Setup

If you prefer manual setup:

```bash
# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Frontend setup
cd frontend/accounting-frontend
npm install

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Starting Development

```bash
# Start both servers
make dev-all

# Or start individually
make dev-backend
make dev-frontend

# Using convenience script
./scripts/dev-start.sh
```

### Daily Development Cycle

1. **Pull latest changes**: `git pull`
2. **Run quality checks**: `make check`
3. **Start development servers**: `make dev-all`
4. **Make changes and test**
5. **Run tests**: `make test`
6. **Format code**: `make format`
7. **Commit changes**: `git commit` (pre-commit hooks will run)

### Code Quality Checks

```bash
# Run all quality checks
make check

# Individual checks
make lint          # All linting tools
make format        # Code formatting
make type-check    # Type checking
make security      # Security analysis
```

## Code Quality Tools

### Python Tools

#### Black (Code Formatting)
- Line length: 88 characters
- Target versions: Python 3.9-3.12
- Configuration: `pyproject.toml`

```bash
# Format code
black .

# Check formatting
black --check .
```

#### isort (Import Sorting)
- Profile: black (compatible with Black)
- Configuration: `pyproject.toml`

```bash
# Sort imports
isort .

# Check import order
isort --check-only .
```

#### flake8 (Linting)
- Max line length: 88 (compatible with Black)
- Extensions ignored: E203, W503, E501
- Configuration: `.flake8`

```bash
# Lint code
flake8 .

# With specific config
flake8 --config=.flake8 .
```

#### MyPy (Type Checking)
- Strict mode enabled
- Configuration: `pyproject.toml`

```bash
# Type check
mypy .

# With specific config
mypy --config-file=pyproject.toml .
```

#### pytest (Testing)
- Coverage threshold: 80%
- Configuration: `pytest.ini`
- Fixtures: `tests/conftest.py`

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_main.py
```

### JavaScript/TypeScript Tools

#### ESLint (Linting)
- Extends: TypeScript recommended rules
- Plugins: React hooks, React refresh
- Configuration: `eslint.config.js`

```bash
# Lint code
npm run lint

# Auto-fix issues
npm run lint:fix
```

#### Prettier (Code Formatting)
- Line length: 100 characters
- Semi-colons: enabled
- Single quotes: enabled
- Configuration: `.prettierrc`

```bash
# Format code
npm run format

# Check formatting
npm run format:check
```

#### TypeScript Compiler
- Strict mode enabled
- NoEmit on check
- Configuration: `tsconfig.json`

```bash
# Type check
npm run type-check

# Compile
tsc -b
```

#### Vitest (Testing)
- Environment: jsdom
- Coverage: v8 provider
- Configuration: `vitest.config.ts`

```bash
# Run tests
npm run test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

## Testing Framework

### Backend Testing (pytest)

#### Test Structure
```
backend/tests/
├── conftest.py           # Shared fixtures
├── test_main.py          # Main app tests
├── test_models.py        # Model tests
├── test_api.py           # API endpoint tests
└── test_services.py      # Service layer tests
```

#### Test Configuration
- **Coverage threshold**: 80%
- **Test discovery**: `tests/` directory
- **Markers**: slow, integration, unit, smoke
- **Parallel execution**: pytest-xdist

#### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

#### Fixtures

```python
@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('app.core.config.settings') as mock:
        mock.DEBUG = True
        yield mock

@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "id": 1,
        "filename": "test_document.pdf",
        "status": "pending"
    }
```

### Frontend Testing (Vitest)

#### Test Structure
```
frontend/accounting-frontend/src/test/
├── setup.ts              # Test environment setup
├── App.test.tsx          # Component tests
├── hooks/                # Hook tests
├── components/           # Component tests
└── utils/                # Utility tests
```

#### Test Configuration
- **Environment**: jsdom
- **Coverage**: v8 provider
- **Threshold**: 80%
- **Setup**: Testing Library + DOM testing

#### Writing Tests

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App Component', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(document.body).toBeInTheDocument()
  })
})
```

#### Mocking

```typescript
// Mock external dependencies
vi.mock('../components/LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>,
}))

// Mock API calls
vi.mock('../services/api', () => ({
  fetchDocuments: vi.fn(),
}))
```

## Pre-commit Hooks

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

### Hook Configuration

The `.pre-commit-config.yaml` includes:

1. **General hooks**: trailing whitespace, large files, merge conflicts
2. **Python hooks**: Black, isort, flake8, MyPy, bandit
3. **JavaScript hooks**: ESLint, Prettier
4. **Security hooks**: detect-secrets, safety
5. **Commit message hooks**: conventional commits

### Running Hooks

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Update hooks
pre-commit autoupdate

# Skip hooks for a commit
git commit --no-verify
```

### Custom Hooks

To add custom hooks, edit `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: custom-check
        name: Custom Check
        entry: python scripts/custom_check.py
        language: system
        files: \.py$
```

## CI/CD Pipeline

### Pipeline Stages

#### 1. Quality Checks
- Code formatting verification
- Linting (flake8, ESLint)
- Type checking (MyPy, TypeScript)
- Security scanning (bandit, safety)

#### 2. Testing
- Backend tests with coverage
- Frontend tests with coverage
- Integration tests
- E2E tests

#### 3. Build & Security
- Build artifacts
- Dependency vulnerability scanning
- Container image building
- Security analysis

#### 4. Deployment
- Staging deployment (develop branch)
- Production deployment (main branch)
- Health checks
- Rollback capabilities

### Configuration

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  quality-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: make check
```

### Setting up Codecov

1. Add repository to Codecov
2. Configure coverage thresholds
3. Add badge to README
4. Set up PR status checks

## Configuration Reference

### Backend Configuration (`pyproject.toml`)

```toml
[tool.black]
line-length = 88
target-version = ['py39', 'py310', 'py311', 'py312']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=app", "--cov-fail-under=80"]

[tool.mypy]
python_version = "3.9"
disallow_untyped_defs = true
```

### Frontend Configuration

#### ESLint (`eslint.config.js`)
```javascript
export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    rules: {
      '@typescript-eslint/no-unused-vars': 'error',
      'react-hooks/rules-of-hooks': 'error',
    },
  },
)
```

#### Prettier (`.prettierrc`)
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2
}
```

### Environment Variables

#### Backend (`.env`)
```bash
DEBUG=true
DATABASE_URL=sqlite:///./accounting_automation.db
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Frontend (`.env.local`)
```bash
VITE_API_URL=http://localhost:8000
VITE_DEBUG=true
VITE_ENABLE_MOCK_DATA=true
```

## Troubleshooting

### Common Issues

#### Python Issues

**Virtual environment not activated:**
```bash
cd backend
source venv/bin/activate
```

**Import errors:**
```bash
# Ensure you're in the right directory
cd backend
# Check Python path
python -c "import sys; print(sys.path)"
```

**MyPy errors:**
```bash
# Install missing type stubs
pip install types-requests types-PyYAML
```

#### Node.js Issues

**npm install fails:**
```bash
# Clear cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**TypeScript errors:**
```bash
# Check tsconfig.json
# Ensure all paths are correct
npm run type-check
```

#### Pre-commit Issues

**Hooks fail:**
```bash
# Update hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install
```

**Black formatting conflicts:**
```bash
# Ensure consistent line length (88 chars)
# Check .flake8 configuration
# Run black manually
black .
```

#### GitHub Actions Issues

**Tests fail in CI but pass locally:**
```bash
# Check Python/Node.js versions
# Ensure environment variables are set
# Run same commands locally
```

**Coverage too low:**
```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Check which lines are not covered
# Add tests for missing coverage
```

### Getting Help

#### Check Status
```bash
make status          # Check application status
make logs            # View application logs
./scripts/quality-check.sh  # Run quality checks
```

#### Debug Mode
```bash
# Backend debug
DEBUG=true uvicorn app.main:app --reload

# Frontend debug
npm run dev -- --debug
```

#### Clean Restart
```bash
# Clean everything
make clean
./scripts/setup-dev.sh
```

### Best Practices

1. **Run quality checks before committing**
2. **Write tests for new features**
3. **Keep dependencies updated**
4. **Use meaningful commit messages**
5. **Review pull requests thoroughly**
6. **Monitor CI/CD pipeline status**
7. **Keep environment files secure**
8. **Document new configurations**

### Performance Tips

1. **Use parallel testing**: `pytest -n auto`
2. **Cache dependencies**: Already configured in CI/CD
3. **Use fast mode for development**: `pytest -x`
4. **Profile slow tests**: `pytest --durations=10`
5. **Use selective reloading**: Configure Vite for faster HMR

### Security Checklist

- [ ] No secrets in code
- [ ] Dependencies are up to date
- [ ] Security scans pass
- [ ] Environment variables are properly set
- [ ] HTTPS in production
- [ ] Proper CORS configuration
- [ ] Input validation implemented
- [ ] Authentication/authorization tested