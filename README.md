# Fernando - Portuguese Invoice Processing Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![React Version](https://img.shields.io/badge/react-18+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://www.typescriptlang.org/)

A comprehensive, production-ready platform for automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration. Built with modern technologies and enterprise-grade architecture.

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Development](#-development)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [Security](#-security)
- [Performance](#-performance)
- [Monitoring](#-monitoring)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)
- [Support](#-support)

## 🎯 Project Overview

Fernando is a complete full-stack application designed to automate the extraction and processing of Portuguese accounting documents, specifically invoices and receipts. The platform leverages modern AI technologies including Optical Character Recognition (OCR) and Large Language Models (LLM) to extract structured data from documents, validate the information, and integrate seamlessly with the TOCOnline accounting platform.

### What Makes Fernando Special

- **Production-Ready**: Built with enterprise-grade architecture and security
- **Mock Services**: Fully functional with realistic mock implementations for development
- **Portuguese Language Optimized**: Specifically designed for Portuguese invoice formats and tax requirements
- **Comprehensive Audit Trail**: Complete tracking of all operations and user actions
- **Role-Based Access Control**: Multi-level user permissions and access management
- **Real-time Processing**: Live status updates and progress tracking
- **Manual Review Interface**: Human-in-the-loop validation and correction capabilities
- **Extensible Architecture**: Easy integration with real OCR, LLM, and API services

## ✨ Key Features

### Document Processing Pipeline
- **Multi-format Support**: PDF, JPEG, PNG, TIFF files
- **Drag & Drop Upload**: Intuitive document upload interface
- **Automatic Processing**: 6-stage pipeline from upload to posting
- **Confidence Scoring**: Per-field confidence levels with validation
- **Multi-page Document Handling**: Automatic segmentation and processing
- **Duplicate Detection**: SHA-256 checksums prevent duplicate processing

### AI-Powered Extraction
- **OCR Processing**: Text extraction from images and PDFs (mock implementation)
- **LLM Field Extraction**: Intelligent extraction of key invoice data
- **Portuguese Language Support**: Optimized for Portuguese invoice formats
- **Structured Data Output**: JSON-formatted extraction results
- **Validation Engine**: Business rule validation for extracted fields

### Business Features
- **Manual Review Interface**: Web UI for reviewing and correcting extractions
- **Approval Workflow**: Multi-level approval process before posting
- **TOCOnline Integration**: Seamless integration with Portuguese accounting system
- **Job Tracking**: Real-time status updates and progress monitoring
- **Bulk Processing**: Process multiple documents simultaneously
- **Export Capabilities**: Download results in various formats

### Enterprise Features
- **Multi-user Support**: Different user roles and permissions
- **Audit Logging**: Comprehensive audit trail for all operations
- **Admin Dashboard**: System metrics and user management
- **Security**: JWT authentication, password hashing, CORS protection
- **Database Management**: SQLite for development, PostgreSQL for production
- **API Documentation**: Interactive OpenAPI/Swagger documentation

## 🏗️ Architecture

### System Architecture Diagram

![System Architecture](docs/system_architecture_diagram.png)

The Fernando platform follows a modern microservices-inspired architecture with clear separation of concerns:

- **Frontend Layer**: React-based web application with TypeScript
- **API Gateway**: FastAPI-based REST API with authentication
- **Processing Engine**: Asynchronous document processing pipeline
- **Storage Layer**: File storage abstraction supporting local, S3, and MinIO
- **Database Layer**: Relational database for operational data and audit logs
- **Mock Services**: Realistic implementations for development and testing

### Database Schema

![Database Schema](docs/database_schema_diagram.png)

The platform uses a normalized relational database with 6 core entities:
- **Users**: Authentication and role management
- **Jobs**: Processing job tracking and status
- **Documents**: File metadata and storage references
- **Extraction Runs**: OCR/LLM processing results
- **Extraction Fields**: Individual field extractions with confidence scores
- **Audit Logs**: Complete audit trail for compliance

### Processing Pipeline

![Processing Pipeline](docs/processing_pipeline_diagram.png)

The 6-stage document processing pipeline:
1. **Visual Analysis**: Layout and structure detection
2. **OCR Processing**: Text extraction from visual elements
3. **LLM Extraction**: Intelligent field extraction
4. **Validation**: Business rule validation
5. **Manual Review**: Human correction and approval
6. **TOCOnline Posting**: Integration with accounting system

## 🛠️ Technology Stack

### Backend
- **Python 3.9+**: Modern Python with type hints
- **FastAPI**: High-performance async API framework
- **SQLAlchemy**: Python SQL toolkit and ORM
- **PostgreSQL/SQLite**: Relational database
- **Pydantic**: Data validation using Python type annotations
- **JWT**: JSON Web Tokens for authentication
- **Alembic**: Database migration tool
- **Celery**: Distributed task queue (optional)

### Frontend
- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn/ui**: Modern component library
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **React Query**: Server state management

### Development Tools
- **Black**: Python code formatter
- **isort**: Python import sorter
- **flake8**: Python linting
- **MyPy**: Static type checking
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatter
- **pytest**: Python testing framework
- **Vitest**: JavaScript testing framework
- **pre-commit**: Git hooks framework

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **GitHub Actions**: CI/CD pipeline
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Sentry**: Error tracking
- **Loki**: Log aggregation

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm or pnpm
- Git

### System Requirements

- **Development**: 4GB RAM, 2 CPU cores
- **Production**: 8GB RAM, 4 CPU cores (recommended)
- **Storage**: 10GB+ for development, 100GB+ for production

### Quick Installation

Run the automated setup script:

```bash
# Clone the repository
git clone https://github.com/your-org/fernando.git
cd fernando

# Run the comprehensive setup script
./scripts/setup-dev.sh
```

This script will automatically:
- Install all dependencies
- Set up Python virtual environment
- Install Node.js packages
- Configure pre-commit hooks
- Create environment files
- Initialize database
- Configure IDE settings

### Manual Installation

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install email validator
pip install email-validator

# Set up database
alembic upgrade head

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend/accounting-frontend

# Install dependencies
npm install
# or
pnpm install

# Start development server
npm run dev
# or
pnpm dev
```

### Docker Installation

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f
```

## 🚀 Quick Start

### 1. Start the Application

```bash
# Start both backend and frontend
make dev-all

# Or use the convenience script
./scripts/dev-start.sh
```

### 2. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:5173/admin

### 3. First Time Usage

1. **Register Account**
   - Navigate to http://localhost:5173
   - Click "Register" and create an account
   - Default role: Uploader

2. **Upload Documents**
   - Use the drag-and-drop interface
   - Upload PDF or image files
   - Files up to 10MB supported

3. **Monitor Processing**
   - View job status in real-time
   - Processing typically takes 5-15 seconds

4. **Review Results**
   - Check extracted fields
   - Make corrections if needed
   - Approve for posting

5. **View Results**
   - See posting status
   - Download processed results
   - Review audit log

### Sample API Usage

```bash
# Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure123", "full_name": "John Doe"}'

# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure123"}' | jq -r '.access_token')

# Create a processing job
curl -X POST http://localhost:8000/jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"priority": 0}'

# Upload a document
curl -X POST "http://localhost:8000/jobs/{job_id}/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@invoice.pdf"
```

## 📚 API Documentation

### Interactive Documentation

The platform provides comprehensive API documentation via:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Core API Endpoints

#### Authentication
```
POST /auth/register     - Register new user
POST /auth/login        - Login and get JWT token
GET  /auth/me          - Get current user info
POST /auth/logout       - Logout and invalidate token
```

#### Document Processing
```
POST /jobs/                    - Create new processing job
GET  /jobs/                    - List user jobs
GET  /jobs/{job_id}            - Get job details
POST /jobs/{job_id}/upload     - Upload documents to job
DELETE /jobs/{job_id}          - Cancel job
```

#### Extractions
```
GET  /extractions/document/{document_id}  - Get extraction results
PUT  /extractions/{run_id}               - Update extraction fields
POST /extractions/{run_id}/approve       - Approve extraction for posting
GET  /extractions/{run_id}/validate      - Validate extraction
```

#### TOCOnline Integration
```
POST /toconline/post           - Post document to TOCOnline
GET  /toconline/status/{id}    - Get document posting status
GET  /toconline/documents      - List posted documents
```

#### Admin Endpoints
```
GET  /admin/metrics            - System metrics
GET  /admin/audit-logs         - Audit log entries
GET  /admin/users              - List all users
PUT  /admin/users/{id}/roles   - Update user roles
GET  /admin/jobs               - All system jobs
GET  /admin/statistics         - Processing statistics
```

### Request/Response Examples

#### Create Job Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "priority": 0,
  "uploaded_by": "user-uuid",
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Extraction Result
```json
{
  "run_id": "extraction-uuid",
  "document_id": "doc-uuid",
  "stage": "llm",
  "status": "success",
  "fields": [
    {
      "field_name": "supplier_name",
      "value": "Empresa ABC Lda",
      "confidence": 0.95,
      "validation_status": "valid"
    },
    {
      "field_name": "total_amount",
      "value": "150.00",
      "confidence": 0.98,
      "validation_status": "valid"
    }
  ]
}
```

## ⚙️ Configuration

### Environment Variables

#### Backend Configuration (.env)

```bash
# Application Settings
DEBUG=true
API_V1_STR=/api/v1
PROJECT_NAME="Fernando API"
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./fernando.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost:5432/fernando

# Security
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
ALGORITHM=HS256

# Storage
STORAGE_BACKEND=local
# For S3:
# STORAGE_BACKEND=s3
# STORAGE_BUCKET=fernando-documents
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret

# Mock Services
MOCK_OCR_ENABLED=true
MOCK_LLM_ENABLED=true
MOCK_TOCONLINE_ENABLED=true

# Optional: Real API Keys
# OPENAI_API_KEY=your-openai-key
# TOCONLINE_API_KEY=your-toconline-key
```

#### Frontend Configuration (.env.local)

```bash
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_V1_STR=/api/v1

# Development
VITE_DEBUG=true
VITE_ENABLE_MOCK_DATA=true

# Feature Flags
VITE_ENABLE_ADMIN_PANEL=true
VITE_ENABLE_AUDIT_LOGS=true
```

### Configuration Files

#### Backend (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = ['py39', 'py310', 'py311', 'py312']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--cov=app", "--cov-report=html", "--cov-fail-under=80"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
]

[tool.mypy]
python_version = "3.9"
disallow_untyped_defs = true
warn_return_any = true
warn_unused_configs = true
```

#### Frontend (eslint.config.js)

```javascript
export default tseslint.config(
  { ignores: ['dist', 'build'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    rules: {
      '@typescript-eslint/no-unused-vars': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
)
```

## 🚀 Deployment

### Development Deployment

```bash
# Using Docker Compose
docker-compose up -d

# Manual deployment
make dev-all
```

### Production Deployment

#### Using Docker

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with production settings
docker-compose -f docker-compose.prod.yml up -d
```

#### Using Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n fernando

# View logs
kubectl logs -f deployment/fernando-backend -n fernando
```

#### Manual Production Setup

```bash
# Backend
cd backend
export DEBUG=false
export DATABASE_URL=postgresql://user:pass@localhost:5432/fernando
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend/accounting-frontend
npm run build
# Serve dist/ directory with nginx or similar
```

### Environment-Specific Configurations

#### Development
- SQLite database
- Mock services enabled
- Debug logging
- CORS enabled for localhost
- Hot reload enabled

#### Staging
- PostgreSQL database
- Mock services for testing
- Info level logging
- Restricted CORS
- SSL/TLS enabled

#### Production
- PostgreSQL with read replicas
- Real API services
- Error level logging
- Strict CORS
- Full SSL/TLS
- Load balancing
- Monitoring enabled

### Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL/TLS certificates installed
- [ ] Security headers configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Health checks configured
- [ ] Load balancer configured
- [ ] DNS configured

## 🛠️ Development

### Development Workflow

1. **Setup Development Environment**
   ```bash
   ./scripts/setup-dev.sh
   ```

2. **Start Development Servers**
   ```bash
   make dev-all
   ```

3. **Make Changes**
   - Backend: Modify Python files in `backend/app/`
   - Frontend: Modify TypeScript files in `frontend/accounting-frontend/src/`

4. **Run Tests**
   ```bash
   make test
   ```

5. **Code Quality Checks**
   ```bash
   make check
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

### Code Standards

#### Python Code Style
- **Formatter**: Black (88 character line length)
- **Import Sorting**: isort
- **Linting**: flake8
- **Type Checking**: MyPy
- **Documentation**: Google-style docstrings

#### TypeScript Code Style
- **Formatter**: Prettier
- **Linting**: ESLint with TypeScript rules
- **Type Safety**: Strict TypeScript configuration
- **Testing**: Vitest with React Testing Library

### Development Scripts

```bash
# Available make commands
make help              # Show all available commands
make install           # Install all dependencies
make dev-setup         # Set up development environment
make dev-all           # Start development servers
make dev-backend       # Start backend only
make dev-frontend      # Start frontend only
make lint              # Run all linting tools
make format            # Format all code
make type-check        # Type checking
make test              # Run all tests
make test-backend      # Backend tests
make test-frontend     # Frontend tests
make test-coverage     # Tests with coverage
make clean             # Clean build artifacts
make docker-build      # Build Docker images
make docker-run        # Run with Docker
```

### Adding New Features

1. **Backend Features**
   - Add models in `backend/app/models/`
   - Add schemas in `backend/app/schemas/`
   - Add API endpoints in `backend/app/api/`
   - Add business logic in `backend/app/services/`
   - Add tests in `backend/tests/`

2. **Frontend Features**
   - Add components in `frontend/accounting-frontend/src/components/`
   - Add pages in `frontend/accounting-frontend/src/pages/`
   - Add hooks in `frontend/accounting-frontend/src/hooks/`
   - Add utilities in `frontend/accounting-frontend/src/utils/`
   - Add tests in `frontend/accounting-frontend/src/test/`

## 🧪 Testing

### Test Structure

```
backend/tests/
├── conftest.py           # Shared fixtures
├── test_main.py          # Main app tests
├── test_models.py        # Database model tests
├── test_api.py           # API endpoint tests
├── test_services.py      # Service layer tests
└── test_auth.py          # Authentication tests

frontend/accounting-frontend/src/test/
├── setup.ts              # Test environment setup
├── App.test.tsx          # Component tests
├── components/           # Component tests
├── hooks/                # Hook tests
└── utils/                # Utility tests
```

### Running Tests

```bash
# All tests
make test

# Backend tests
make test-backend
cd backend && pytest

# Frontend tests
make test-frontend
cd frontend/accounting-frontend && npm run test

# Tests with coverage
make test-coverage
pytest --cov=app --cov-report=html
npm run test:coverage
```

### Test Types

#### Unit Tests
- Test individual functions and components
- Fast execution
- No external dependencies

#### Integration Tests
- Test component interactions
- Database operations
- API integrations

#### End-to-End Tests
- Full user workflows
- Browser automation
- Complete system testing

#### Performance Tests
- Load testing
- Stress testing
- Response time benchmarks

### Test Coverage

- **Backend**: Minimum 80% coverage
- **Frontend**: Minimum 80% coverage
- **Critical paths**: 100% coverage required

## 🤝 Contributing

We welcome contributions to Fernando! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

### Contribution Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/fernando.git
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Follow code style guidelines
   - Add tests for new features
   - Update documentation

4. **Run Quality Checks**
   ```bash
   make check
   make test
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions or updates
- `chore:` Build process or auxiliary tool changes

### Pull Request Guidelines

- Provide a clear description of changes
- Link related issues
- Include screenshots for UI changes
- Ensure all tests pass
- Update documentation as needed
- Follow the code style guidelines

### Development Guidelines

#### Security
- Never commit secrets or API keys
- Use environment variables for configuration
- Follow OWASP security guidelines
- Run security scans regularly

#### Performance
- Optimize database queries
- Use async/await appropriately
- Implement caching where beneficial
- Monitor performance metrics

#### Documentation
- Update README for significant changes
- Document new API endpoints
- Include code comments for complex logic
- Update architecture diagrams as needed

## 🔒 Security

### Security Features

- **Authentication**: JWT-based authentication with secure token handling
- **Authorization**: Role-based access control (RBAC)
- **Password Security**: bcrypt hashing with salt
- **Input Validation**: Comprehensive input validation using Pydantic
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Content Security Policy and input sanitization
- **CSRF Protection**: Cross-site request forgery protection
- **CORS Configuration**: Properly configured cross-origin resource sharing
- **Rate Limiting**: API rate limiting to prevent abuse
- **Audit Logging**: Comprehensive audit trail for all operations

### Security Best Practices

1. **Environment Variables**: Never hardcode secrets
2. **Database Security**: Use parameterized queries, least privilege access
3. **API Security**: Validate all inputs, implement rate limiting
4. **Frontend Security**: Sanitize user inputs, use HTTPS
5. **Dependency Management**: Keep dependencies updated, scan for vulnerabilities
6. **Access Control**: Implement proper authorization checks
7. **Data Protection**: Encrypt sensitive data at rest and in transit

### Security Testing

```bash
# Run security scans
make security

# Python security analysis
bandit -r backend/
safety check

# JavaScript security analysis
npm audit
```

## ⚡ Performance

### Performance Optimizations

#### Backend
- **Database Optimization**: Indexed queries, connection pooling
- **Async Processing**: Non-blocking I/O operations
- **Caching**: Redis caching for frequently accessed data
- **Background Jobs**: Celery for heavy processing tasks
- **Response Compression**: Gzip compression for API responses

#### Frontend
- **Code Splitting**: Dynamic imports for route-based splitting
- **Bundle Optimization**: Tree shaking, minification
- **Image Optimization**: Lazy loading, WebP format
- **Caching Strategy**: Service worker caching, HTTP caching
- **Performance Monitoring**: Web Vitals tracking

### Performance Metrics

- **API Response Time**: p95 < 500ms
- **Page Load Time**: < 2 seconds
- **Database Query Time**: p95 < 100ms
- **File Processing Time**: < 30 seconds per document
- **Memory Usage**: < 500MB per service

### Performance Monitoring

```bash
# Backend profiling
make profile

# Database performance
EXPLAIN ANALYZE SELECT * FROM ...;

# Frontend performance
npm run lighthouse
```

## 📊 Monitoring

### Monitoring Stack

- **Prometheus**: Metrics collection and storage
- **Grafana**: Metrics visualization and dashboards
- **Sentry**: Error tracking and performance monitoring
- **Loki**: Log aggregation and analysis
- **AlertManager**: Alert routing and notifications

### Key Metrics

#### Application Metrics
- Request rate and response times
- Error rates by endpoint
- Database connection pool usage
- Job processing queue size
- Document processing throughput

#### Business Metrics
- Daily document processing volume
- Extraction accuracy rates
- User activity and engagement
- API usage patterns
- Cost per document processed

#### Infrastructure Metrics
- CPU and memory usage
- Disk I/O and storage utilization
- Network traffic and latency
- Container health and restart counts
- Database performance metrics

### Alerting

#### Critical Alerts
- Application down or unresponsive
- High error rate (>5%)
- Database connection failures
- Storage space critical
- Security incidents

#### Warning Alerts
- High response times
- Low disk space
- Failed background jobs
- Certificate expiration
- High memory usage

### Log Management

```bash
# View application logs
make logs

# Follow logs in real-time
tail -f logs/fernando.log

# Search logs
grep "ERROR" logs/fernando.log
```

## 🔧 Troubleshooting

### Common Issues

#### Backend Issues

**Port Already in Use**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Database Connection Issues**
```bash
# Check database file permissions
ls -la fernando.db
chmod 664 fernando.db

# Reset database
rm fernando.db
alembic upgrade head
```

**Import Errors**
```bash
# Ensure virtual environment is activated
source backend/venv/bin/activate

# Set Python path
export PYTHONPATH=$PYTHONPATH:/path/to/fernando/backend
```

#### Frontend Issues

**Node.js Version Issues**
```bash
# Check Node.js version
node --version  # Should be 18+

# Install correct version using nvm
nvm install 18
nvm use 18
```

**Build Failures**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npm run type-check
```

**CORS Issues**
```bash
# Verify backend CORS configuration
# Check environment variables
echo $BACKEND_CORS_ORIGINS
```

#### Development Issues

**Pre-commit Hook Failures**
```bash
# Update hooks
pre-commit autoupdate

# Run hooks manually
pre-commit run --all-files

# Skip hooks for urgent fix
git commit --no-verify -m "urgent fix"
```

**Test Failures**
```bash
# Run tests in debug mode
pytest -s -v

# Check test coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::test_create_job
```

### Debug Mode

```bash
# Backend debug
DEBUG=true uvicorn app.main:app --reload --log-level debug

# Frontend debug
npm run dev -- --debug

# Database debug
alembic current --verbose
```

### Getting Help

1. **Check Documentation**: Review this README and other docs
2. **Search Issues**: Look for existing GitHub issues
3. **Run Diagnostics**: `make status` and `make logs`
4. **Contact Support**: See [Support](#-support) section

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

- **Commercial Use**: ✅ Allowed
- **Modification**: ✅ Allowed
- **Distribution**: ✅ Allowed
- **Private Use**: ✅ Allowed
- **Liability**: ❌ Not liable
- **Warranty**: ❌ No warranty

### Third-Party Licenses

This project uses several open-source libraries. See [THIRD-PARTY-LICENSES](THIRD-PARTY-LICENSES) for complete attribution.

## 💬 Support

### Getting Help

- **Documentation**: Check this README and other docs in the `/docs` directory
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Email**: Contact the maintainers

### Reporting Issues

When reporting issues, please include:

1. **Environment Details**
   - Operating system
   - Python version
   - Node.js version
   - Docker version (if applicable)

2. **Issue Description**
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs

3. **Configuration**
   - Relevant environment variables
   - Configuration file contents
   - Database information

### Feature Requests

For feature requests, please:

1. Check existing issues and discussions
2. Describe the use case
3. Provide implementation suggestions
4. Consider contributing the feature

### Community

- **Discord**: [Join our Discord server](https://discord.gg/fernando)
- **Slack**: [Join our Slack workspace](https://fernando.slack.com)
- **LinkedIn**: [Follow us on LinkedIn](https://linkedin.com/company/fernando-platform)

### Professional Support

For enterprise support, training, or consulting:

- **Email**: enterprise@fernando-platform.com
- **Website**: https://fernando-platform.com/enterprise

---

**Fernando Platform** - Automating Portuguese Invoice Processing with AI

Built with ❤️ by the Fernando Team
