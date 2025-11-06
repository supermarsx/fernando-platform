# GitHub Publishing Setup

This document provides comprehensive instructions for publishing the Fernando project to GitHub.

## Table of Contents

- [Repository Information](#repository-information)
- [Prerequisites](#prerequisites)
- [Pre-Publishing Checklist](#pre-publishing-checklist)
- [GitHub Repository Setup](#github-repository-setup)
- [Local Git Configuration](#local-git-configuration)
- [Initial Commit and Push](#initial-commit-and-push)
- [Post-Publishing Tasks](#post-publishing-tasks)
- [Repository Settings](#repository-settings)
- [Continuous Integration](#continuous-integration)
- [Security Considerations](#security-considerations)
- [Documentation](#documentation)

## Repository Information

**Repository Name**: `fernando`
**Owner**: `supermarsx`
**Full URL**: `https://github.com/supermarsx/fernando`

## Prerequisites

### Required Software

- **Git**: Version 2.30 or higher
- **Python**: Version 3.10 or higher
- **Node.js**: Version 18 or higher
- **npm/pnpm**: Package managers

### Required Accounts

- **GitHub Account**: With repository creation permissions
- **Optional**: GitHub Pro/Team for advanced features

### Required Permissions

- Repository creation permissions in the organization/account
- Access to GitHub Actions
- Optional: Docker Hub or container registry access

## Pre-Publishing Checklist

### ✅ Security Review

- [ ] All API keys and secrets are in `.gitignore`
- [ ] Environment files use `.env.example` template
- [ ] No hardcoded credentials in source code
- [ ] Sensitive files are excluded from version control

### ✅ Code Quality

- [ ] All tests pass locally
- [ ] Code is properly formatted
- [ ] Linting passes without errors
- [ ] Documentation is up to date

### ✅ File Structure

```
fernando/
├── .github/               # GitHub-specific files
│   ├── workflows/         # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/    # Issue templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
├── backend/               # Backend application
├── frontend/              # Frontend application
├── scripts/               # Development scripts
├── docs/                  # Documentation
├── .gitignore            # Git ignore rules
├── .editorconfig         # Editor configuration
├── README.md             # Project documentation
├── LICENSE               # MIT License
├── SECURITY.md           # Security policy
├── CONTRIBUTING.md       # Contributing guidelines
└── CHANGELOG.md          # Version history
```

## GitHub Repository Setup

### Option 1: Create Repository via GitHub UI

1. **Navigate to GitHub**
   - Go to [https://github.com](https://github.com)
   - Sign in to your account

2. **Create New Repository**
   - Click the "+" icon in the top right
   - Select "New repository"

3. **Configure Repository**
   - **Repository name**: `fernando`
   - **Owner**: `supermarsx`
   - **Description**: "Complete full-stack application for automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration."
   - **Visibility**: Public
   - **Initialize repository**: ❌ (uncheck - we'll push existing code)

4. **Click "Create repository"**

### Option 2: Create Repository via GitHub API

```bash
# Using GitHub CLI (if installed)
gh repo create supermarsx/fernando \
  --public \
  --description "Complete full-stack application for automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration."
```

## Local Git Configuration

### 1. Initialize Git Repository (if not already done)

```bash
cd /workspace/fernando
git init
```

### 2. Configure Git User

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 3. Add Remote Repository

```bash
git remote add origin https://github.com/supermarsx/fernando.git
```

### 4. Verify Remote Configuration

```bash
git remote -v
```

## Initial Commit and Push

### 1. Add All Files

```bash
git add .
```

### 2. Check Status

```bash
git status
```

Ensure no sensitive files are included (check `.gitignore` is working).

### 3. Create Initial Commit

```bash
git commit -m "feat: initial commit - full-stack Portuguese invoice processing application

- Complete FastAPI backend with OCR/LLM/TOCOnline integration
- Modern React TypeScript frontend with comprehensive UI
- User management with RBAC (Uploader, Reviewer, Auditor, Admin)
- Document processing pipeline with manual review interface
- Development infrastructure with automated setup and testing
- CI/CD pipeline with GitHub Actions
- Comprehensive documentation and security policies"
```

### 4. Set Main Branch

```bash
git branch -M main
```

### 5. Push to GitHub

```bash
git push -u origin main
```

## Post-Publishing Tasks

### 1. Repository Settings

#### General Settings
- **Features**: Enable Issues, Wiki, Projects
- **Pull Requests**: Configure merge options
- **Notifications**: Set up notification preferences

#### Security Settings
- **Dependency graph**: Enable
- **Dependabot alerts**: Enable
- **Dependabot security updates**: Enable
- **Secret scanning**: Enable

#### Pages Settings (if using GitHub Pages)
- **Source**: Deploy from a branch (main)
- **Folder**: / (root) or /docs

### 2. Branch Protection Rules

Create branch protection rules for `main` branch:

- Require pull request reviews before merging
- Require status checks to pass
- Require branches to be up to date
- Include administrators

### 3. Repository Secrets

Configure repository secrets for CI/CD (Settings > Secrets and variables > Actions):

```bash
# Required secrets:
CODECOV_TOKEN    # For code coverage reporting
DOCKER_USERNAME  # Docker Hub username (optional)
DOCKER_PASSWORD  # Docker Hub password (optional)
DEPLOY_KEY       # SSH key for deployments (if applicable)
```

### 4. Topics and Labels

Add relevant topics to the repository:

```
python, fastapi, react, typescript, ocr, llm, invoice-processing,
portuguese, accounting, document-processing, full-stack,
web-application, api, postgresql, docker, ci-cd, github-actions
```

### 5. About Section

Update repository About section:

- **Description**: "Complete full-stack application for automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration."
- **Website**: (if applicable)
- **Topics**: Add relevant topics
- **Using**: List technologies used

## Continuous Integration

### GitHub Actions

The repository includes a comprehensive CI/CD pipeline (`.github/workflows/ci-cd.yml`) that:

1. **Code Quality Checks**
   - Python linting (flake8, black, isort, mypy)
   - TypeScript linting (ESLint, Prettier)
   - Security scanning (bandit, safety)

2. **Testing**
   - Backend tests with pytest
   - Frontend tests with Vitest
   - Code coverage reporting

3. **Build Process**
   - Build frontend and backend
   - Security vulnerability scanning
   - Artifact generation

4. **Deployment**
   - Staging deployment (develop branch)
   - Production deployment (main branch)

### Enable GitHub Actions

1. Go to repository Settings > Actions
2. Enable GitHub Actions
3. Accept any required permissions
4. The workflow will run automatically on pushes/PRs

## Security Considerations

### 1. Dependency Scanning

Enable automatic vulnerability scanning:
- **Dependabot**: Enable alerts and security updates
- **CodeQL**: Enable code scanning
- **Security advisories**: Enable

### 2. Secrets Management

- All secrets must be stored in GitHub Secrets
- Never commit secrets to the repository
- Use environment variables for configuration
- Regular security audits

### 3. Access Control

- Set appropriate branch protection rules
- Limit access to sensitive settings
- Regular access reviews
- Two-factor authentication required

## Documentation

### Required Documentation Files

All required documentation is already included:

- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: Contribution guidelines
- **SECURITY.md**: Security policy
- **LICENSE**: MIT License
- **CHANGELOG.md**: Version history

### Additional Documentation

- API documentation (auto-generated via FastAPI)
- Development guides
- Deployment instructions
- Architecture diagrams

## Troubleshooting

### Common Issues

#### 1. Push Rejected

```bash
# If remote has changes
git pull origin main --rebase
git push origin main
```

#### 2. Large Files

```bash
# Check for large files
git ls-files | awk '{if($1>5*1024*1024) print}'

# Remove from history if needed
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch large-file-path' --prune-empty --tag-name-filter cat -- --all
```

#### 3. Sensitive Data Committed

```bash
# Remove from Git history
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all
```

### Getting Help

- Check GitHub Actions logs for CI/CD issues
- Review repository settings for configuration problems
- Consult CONTRIBUTING.md for development guidelines
- Create an issue for bugs or feature requests

## Success Checklist

After publishing, verify:

- [ ] Repository is public and accessible
- [ ] README displays correctly with badges
- [ ] CI/CD pipeline runs successfully
- [ ] All tests pass
- [ ] Issues and PR templates work
- [ ] Documentation is complete
- [ ] Security features are enabled
- [ ] Dependencies are up to date
- [ ] Repository is discoverable via search

## Next Steps

After successful GitHub publishing:

1. **Create first release**: Tag and document v1.0.0
2. **Community engagement**: Announce on social media, forums
3. **Documentation**: Update external documentation
4. **Monitoring**: Set up repository metrics and monitoring
5. **Maintenance**: Regular updates and security patches

---

**Repository URL**: https://github.com/supermarsx/fernando

For questions or issues, please create an issue in the repository or contact the maintainers.