# Contributing to Fernando

Thank you for your interest in contributing to Fernando! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Standards](#code-standards)
- [Documentation](#documentation)
- [Submitting Pull Requests](#submitting-pull-requests)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Ways to Contribute

1. **Bug Reports**: Report issues you encounter
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Fix bugs or implement features
4. **Documentation**: Improve docs, guides, and examples
5. **Testing**: Help test new features and report issues
6. **Translations**: Help translate the application
7. **Design**: Improve UI/UX and visual design

### Prerequisites

Before contributing, ensure you have:

- Git installed and configured
- Python 3.10+ installed
- Node.js 18+ installed
- Docker (optional, for containerized development)
- PostgreSQL (for full-featured development)

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/your-username/fernando.git
cd fernando

# Add upstream remote
git remote add upstream https://github.com/fernando-project/fernando.git
```

### 2. Automated Setup

```bash
# Run the comprehensive setup script
./scripts/setup-dev.sh

# This will:
# - Install all dependencies
# - Set up virtual environments
# - Configure pre-commit hooks
# - Create environment files
# - Initialize the database
```

### 3. Manual Setup

If you prefer manual setup:

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Install pre-commit hooks
pre-commit install

# Initialize database
python -m alembic upgrade head
```

#### Frontend Setup

```bash
cd frontend/accounting-frontend

# Install dependencies
pnpm install  # or npm install

# Set up environment
cp .env.example .env.local
```

### 4. Verify Setup

```bash
# Run quality checks
make check

# Start development environment
make dev-all

# Navigate to http://localhost:5173
```

## Making Changes

### Branch Naming Convention

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test-related changes

### Example Workflow

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/add-invoice-export

# Make your changes
# ... edit files ...

# Stage and commit changes
git add .
git commit -m "feat: add invoice export to CSV format"

# Push to your fork
git push origin feature/add-invoice-export
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Backend tests only
make test-backend
cd backend && pytest

# Frontend tests only
make test-frontend
cd frontend/accounting-frontend && npm run test

# Tests with coverage
make test-coverage
```

### Writing Tests

#### Backend Tests

- Place tests in `backend/tests/` directory
- Use `pytest` framework
- Follow naming convention: `test_feature_name.py`
- Include both unit and integration tests
- Mock external services (OCR, LLM, TOCOnline)

Example:
```python
import pytest
from app.main import app
from app.tests.conftest import test_user

def test_create_job(client, test_user):
    response = client.post(
        "/api/v1/jobs/",
        json={"name": "Test Job"},
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    assert response.status_code == 201
    assert "job_id" in response.json()
```

#### Frontend Tests

- Use Vitest for unit tests
- Use React Testing Library for component tests
- Place tests alongside components: `Component.test.tsx`

Example:
```typescript
import { render, screen } from '@testing-library/react'
import { JobCard } from './JobCard'

describe('JobCard', () => {
  it('displays job information correctly', () => {
    const job = { id: '1', name: 'Test Job', status: 'processing' }
    render(<JobCard job={job} />)
    
    expect(screen.getByText('Test Job')).toBeInTheDocument()
    expect(screen.getByText('processing')).toBeInTheDocument()
  })
})
```

### Test Coverage

- Maintain test coverage above 80%
- Focus on critical business logic
- Include edge cases and error scenarios
- Test both success and failure paths

## Code Standards

### Backend (Python)

#### Formatting and Style

```bash
# Format code
make format-backend
# or
cd backend && black . && isort .

# Lint code
make lint-backend
# or
cd backend && flake8 . && mypy .
```

#### Guidelines

- Follow PEP 8 style guidelines
- Use Black for code formatting (88 character line length)
- Use isort for import sorting
- Use type hints for all functions
- Write descriptive docstrings
- Keep functions small and focused
- Use meaningful variable names

#### Example Code

```python
from typing import List, Optional
from fastapi import HTTPException

async def process_invoice(
    invoice_data: dict,
    user_id: int
) -> dict:
    """
    Process invoice data through OCR and LLM extraction.
    
    Args:
        invoice_data: Raw invoice data from upload
        user_id: ID of the user requesting processing
        
    Returns:
        Processed invoice data with extracted fields
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        # Extract text using OCR
        ocr_text = await extract_text(invoice_data["file"])
        
        # Extract structured data using LLM
        extracted_data = await extract_invoice_fields(ocr_text)
        
        # Save to database
        await save_processed_invoice(
            user_id=user_id,
            raw_data=invoice_data,
            extracted_data=extracted_data
        )
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Invoice processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process invoice"
        )
```

### Frontend (TypeScript/React)

#### Formatting and Style

```bash
# Format code
make format-frontend
# or
cd frontend/accounting-frontend && npm run format

# Lint code
make lint-frontend
# or
cd frontend/accounting-frontend && npm run lint
```

#### Guidelines

- Use TypeScript for type safety
- Follow React best practices and hooks patterns
- Use functional components with hooks
- Implement proper error boundaries
- Use Tailwind CSS for styling
- Follow accessibility guidelines (WCAG 2.1)

#### Example Component

```typescript
import { useState, useEffect } from 'react'
import { Upload, FileText, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface InvoiceUploadProps {
  onUpload: (file: File) => void
  isProcessing?: boolean
}

export function InvoiceUpload({ onUpload, isProcessing = false }: InvoiceUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    const file = e.dataTransfer.files?.[0]
    if (file && file.type === 'application/pdf') {
      onUpload(file)
    }
  }
  
  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragActive
          ? 'border-blue-400 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      } ${isProcessing ? 'opacity-50 pointer-events-none' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      {isProcessing ? (
        <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
      ) : (
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
      )}
      
      <p className="mt-4 text-lg font-medium">
        {isProcessing ? 'Processing...' : 'Drop invoice here or click to upload'}
      </p>
      
      <p className="text-sm text-gray-500 mt-2">
        Supports PDF files up to 50MB
      </p>
    </div>
  )
}
```

## Documentation

### Documentation Standards

- Update documentation for all changes
- Include code examples where relevant
- Use clear, concise language
- Add screenshots for UI changes
- Update API documentation for endpoint changes

### Types of Documentation

1. **API Documentation**: Auto-generated from code comments
2. **User Guides**: Step-by-step instructions for end users
3. **Developer Docs**: Technical documentation for contributors
4. **Deployment Guides**: Production deployment instructions
5. **Architecture Docs**: System design and architecture

### Writing Documentation

```markdown
# Feature Name

Brief description of the feature.

## Overview

Detailed explanation of what the feature does and why it exists.

## Usage

```python
# Code example
result = await process_invoice(data)
```

## API Reference

- `endpoint`: Description and parameters
- `response`: Expected response format

## Configuration

Environment variables and configuration options.

## Troubleshooting

Common issues and solutions.
```

## Submitting Pull Requests

### Pull Request Template

When creating a pull request, use the following template:

```markdown
## Description

Brief description of changes made.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Test coverage maintained

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Environment variables documented
- [ ] Database migrations included (if needed)

## Screenshots

If applicable, add screenshots of UI changes.
```

### Review Process

1. **Automated Checks**: All CI/CD checks must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Manual testing may be required for UI changes
4. **Documentation**: Ensure docs are updated
5. **Security**: Review for security implications

### After Approval

Once approved:
1. Squash and merge commits
2. Delete feature branch
3. Issue will be automatically closed
4. Release notes will be updated

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

### Release Workflow

1. **Feature Development**: Work on feature branches
2. **Release Preparation**: Create release branch
3. **Testing**: Comprehensive testing on release branch
4. **Documentation**: Update docs and changelog
5. **Release**: Merge to main and tag release
6. **Deployment**: Deploy to production

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Changelog updated with new version
- [ ] Version numbers updated in code
- [ ] Migration scripts tested
- [ ] Performance testing completed
- [ ] Security review completed

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search GitHub issues
3. Create a new issue with the "question" label
4. Join our community discussions

## Recognition

Contributors will be recognized in:

- README.md contributors section
- Release notes for significant contributions
- Annual contributor appreciation posts

Thank you for contributing to Fernando! 🚀