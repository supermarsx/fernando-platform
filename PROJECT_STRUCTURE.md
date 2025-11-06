# Project Structure

This document describes the complete structure of the Fernando project, explaining the purpose and contents of each directory and key files.

## Overview

Fernando is organized as a monorepo with multiple components:

```
fernando/
├── backend/                 # FastAPI backend application
├── frontend/               # React frontend application
├── desktop/               # Electron desktop application (optional)
├── proxy-servers/         # Microservices for external API proxying
├── licensing-server/      # License validation server
├── scripts/               # Utility scripts for development
├── docs/                  # Project documentation
└── docker/                # Docker configuration files
```

## Root Directory Structure

```
fernando/
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
├── README.md             # Main project documentation
├── CHANGELOG.md          # Version history and changes
├── CONTRIBUTING.md       # Contribution guidelines
├── CODE_OF_CONDUCT.md    # Code of conduct
├── Makefile             # Development automation commands
├── PROJECT_STRUCTURE.md # This file
├── docker-compose.yml    # Docker Compose configuration
├── docker-compose.dev.yml # Development Docker setup
├── docker-compose.prod.yml # Production Docker setup
└── Dockerfile           # Main application Docker image
```

## Backend Structure

```
backend/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── api/               # API route handlers
│   │   ├── __init__.py
│   │   ├── admin.py       # Admin endpoints
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── billing.py     # Billing system endpoints
│   │   ├── enterprise.py  # Enterprise features
│   │   ├── extractions.py # OCR/LLM extraction endpoints
│   │   ├── jobs.py        # Job processing endpoints
│   │   ├── licenses.py    # License management endpoints
│   │   ├── payments.py    # Payment processing endpoints
│   │   ├── queue.py       # Background job queue
│   │   ├── revenue.py     # Revenue operations endpoints
│   │   ├── toconline.py   # TOCOnline integration endpoints
│   │   └── usage.py       # Usage tracking endpoints
│   ├── core/              # Core application components
│   │   ├── __init__.py
│   │   ├── cache_config.py    # Redis caching configuration
│   │   ├── config.py          # Application configuration
│   │   ├── database.py        # Database connection and models
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── logging_config.py  # Logging configuration
│   │   ├── security.py        # Security utilities
│   │   └── ...
│   ├── models/            # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── base.py        # Base model class
│   │   ├── user.py        # User model
│   │   ├── job.py         # Job processing model
│   │   ├── document.py    # Document model
│   │   ├── extraction.py  # Data extraction model
│   │   ├── audit.py       # Audit logging model
│   │   └── ...
│   ├── schemas/           # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py        # User schemas
│   │   ├── job.py         # Job schemas
│   │   ├── extraction.py  # Extraction schemas
│   │   └── ...
│   ├── services/          # Business logic services
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Authentication service
│   │   ├── ocr_service.py       # OCR processing service
│   │   ├── llm_service.py       # LLM processing service
│   │   ├── toconline_service.py # TOCOnline integration
│   │   ├── billing_service.py   # Billing management
│   │   └── ...
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   ├── file_handler.py      # File upload handling
│   │   ├── validators.py        # Data validation utilities
│   │   ├── formatters.py        # Data formatting utilities
│   │   └── ...
│   └── tests/             # Backend tests
├── alembic/               # Database migrations
│   ├── versions/          # Migration files
│   ├── env.py            # Alembic configuration
│   └── script.py.mako    # Migration template
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── requirements-test.txt  # Testing dependencies
├── pytest.ini           # Pytest configuration
├── Dockerfile           # Backend Docker image
├── docker-compose.yml   # Backend Docker setup
└── README.md            # Backend documentation
```

## Frontend Structure

```
frontend/accounting-frontend/
├── public/               # Static assets
│   ├── favicon.ico
│   ├── robots.txt
│   └── ...
├── src/                  # Source code
│   ├── components/       # React components
│   │   ├── ui/          # Reusable UI components
│   │   ├── auth/        # Authentication components
│   │   ├── dashboard/   # Dashboard components
│   │   ├── documents/   # Document handling components
│   │   ├── jobs/        # Job management components
│   │   ├── proxy/       # Proxy integration components
│   │   ├── common/      # Shared components
│   │   └── ...
│   ├── hooks/           # Custom React hooks
│   │   ├── useAuth.ts
│   │   useDocuments.ts
│   │   useJobs.ts
│   │   └── ...
│   ├── lib/             # Utility libraries
│   │   ├── api.ts       # API client
│   │   ├── auth.ts      # Authentication utilities
│   │   ├── utils.ts     # General utilities
│   │   └── ...
│   ├── pages/           # Page components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Documents.tsx
│   │   ├── Jobs.tsx
│   │   ├── Admin.tsx
│   │   └── ...
│   ├── stores/          # State management
│   │   ├── authStore.ts
│   │   ├── documentStore.ts
│   │   └── ...
│   ├── styles/          # Styling
│   │   ├── globals.css
│   │   └── ...
│   ├── types/           # TypeScript type definitions
│   │   ├── api.ts
│   │   ├── user.ts
│   │   └── ...
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Application entry point
│   └── vite-env.d.ts    # Vite type definitions
├── tests/               # Frontend tests
│   ├── components/      # Component tests
│   ├── pages/          # Page tests
│   ├── hooks/          # Hook tests
│   └── utils/          # Utility tests
├── package.json         # NPM dependencies and scripts
├── package-lock.json    # Locked dependency versions
├── tsconfig.json        # TypeScript configuration
├── tsconfig.node.json   # Node.js TypeScript config
├── vite.config.ts       # Vite build configuration
├── tailwind.config.js   # Tailwind CSS configuration
├── postcss.config.js    # PostCSS configuration
├── .env.example         # Environment variables template
├── .eslintrc.js         # ESLint configuration
├── .prettierrc          # Prettier configuration
├── Dockerfile           # Frontend Docker image
└── README.md            # Frontend documentation
```

## Desktop Application (Optional)

```
desktop/
├── src/                  # Electron main process
│   ├── main.ts          # Main Electron process
│   ├── preload.ts       # Preload scripts
│   └── ...
├── public/              # Static files
├── build/               # Build outputs
├── dist/               # Distribution files
├── package.json        # Desktop dependencies
├── tsconfig.json       # TypeScript configuration
├── vite.config.ts      # Vite configuration
├── electron-builder.json5 # Build configuration
└── README.md           # Desktop documentation
```

## Proxy Servers

```
proxy-servers/
├── openai/             # OpenAI API proxy
│   ├── app/
│   │   ├── main.py     # Proxy server entry point
│   │   ├── routes/     # API routes
│   │   ├── middleware/ # Request/response middleware
│   │   └── utils/      # Utility functions
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── llm/                # LLM service proxy
├── ocr/                # OCR service proxy
├── toconline/          # TOCOnline API proxy
├── stripe/             # Stripe payment proxy
├── paypal/             # PayPal payment proxy
├── coinbase/           # Coinbase payment proxy
└── README.md           # Proxy servers documentation
```

## Licensing Server

```
licensing-server/
├── app/                # License validation server
│   ├── main.py         # FastAPI application
│   ├── models/         # License models
│   ├── services/       # License validation logic
│   └── utils/          # Cryptographic utilities
├── requirements.txt    # Dependencies
├── Dockerfile         # Docker image
├── README.md          # Documentation
└── tests/             # Tests
```

## Documentation

```
docs/
├── api/                # API documentation
│   ├── openapi.yaml   # OpenAPI specification
│   └── ...
├── architecture/       # System architecture docs
│   ├── overview.md
│   ├── database-schema.md
│   └── ...
├── user-guide/         # End-user documentation
│   ├── getting-started.md
│   ├── uploading-documents.md
│   └── ...
├── admin-guide/        # Administrative documentation
│   ├── system-admin.md
│   ├── user-management.md
│   └── ...
└── development/        # Developer documentation
    ├── setup.md
    ├── testing.md
    └── ...
```

## Scripts

```
scripts/
├── setup-dev.sh        # Development environment setup
├── dev-start.sh        # Start development servers
├── quality-check.sh    # Run quality checks
├── test-all.sh         # Run all tests
├── deploy-staging.sh   # Staging deployment
├── deploy-production.sh # Production deployment
└── ...
```

## Key Configuration Files

### Development
- `.env.example` - Environment variables template
- `docker-compose.yml` - Development Docker setup
- `.gitignore` - Git ignore rules

### Backend
- `backend/requirements.txt` - Python dependencies
- `backend/pytest.ini` - Test configuration
- `backend/alembic.ini` - Database migration config

### Frontend
- `frontend/accounting-frontend/package.json` - Node.js dependencies
- `frontend/accounting-frontend/vite.config.ts` - Build configuration
- `frontend/accounting-frontend/tailwind.config.js` - CSS framework config

### Quality Assurance
- `.pre-commit-config.yaml` - Pre-commit hooks
- `.github/workflows/ci-cd.yml` - CI/CD pipeline
- `Makefile` - Development automation

## File Naming Conventions

### Backend (Python)
- **Models**: `snake_case.py`
- **API Routes**: `snake_case.py`
- **Services**: `snake_case_service.py`
- **Utils**: `snake_case_utils.py`

### Frontend (TypeScript)
- **Components**: `PascalCase.tsx`
- **Hooks**: `usePascalCase.ts`
- **Utils**: `camelCase.ts`
- **Types**: `camelCase.ts`

### Configuration
- **Environment**: `.env.example`
- **Docker**: `docker-compose.yml`
- **Documentation**: `Title-Case.md`

## Development Workflow

1. **Setup**: Run `./scripts/setup-dev.sh`
2. **Development**: Use `make dev-all` to start services
3. **Testing**: Use `make test` to run all tests
4. **Quality**: Use `make check` to run quality checks
5. **Deployment**: Use `make deploy-staging` or `make deploy-production`

## Deployment Structure

### Production
- Backend runs on FastAPI with Uvicorn
- Frontend builds to static files and serves via Nginx
- PostgreSQL for production database
- Redis for caching and sessions
- Docker containers orchestrated via Docker Compose

### Staging
- Similar to production but with debugging enabled
- Mock services for external APIs
- Test data and fixtures

### Development
- SQLite for quick local development
- Mock services for external APIs
- Hot reload for both backend and frontend
- Detailed logging and error reporting

This structure supports scalable development, testing, and deployment while maintaining clear separation of concerns and modularity.