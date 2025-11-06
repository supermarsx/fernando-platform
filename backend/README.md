# Fernando Backend

FastAPI backend for automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration.

## Features

- User authentication with JWT tokens
- Document upload and processing
- OCR text extraction (mocked)
- LLM-based field extraction (mocked)
- Manual review and correction interface
- TOCOnline API integration (mocked)
- Comprehensive audit logging
- Admin dashboard with metrics

## Setup

1. Install dependencies:
```bash
uv pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:
```bash
cd app
python main.py
```

The API will be available at `http://localhost:8000`

API documentation at `http://localhost:8000/docs`

## Default User

The first user you register will have uploader role.
Use the admin API to assign additional roles (reviewer, auditor, admin).

## API Endpoints

### Authentication
- POST /auth/register - Register new user
- POST /auth/login - Login and get token
- GET /auth/me - Get current user info

### Jobs
- POST /jobs/ - Create new job
- POST /jobs/{job_id}/upload - Upload documents
- GET /jobs/{job_id} - Get job details
- GET /jobs/ - List jobs
- DELETE /jobs/{job_id} - Cancel job

### Extractions
- GET /extractions/document/{document_id} - Get extraction results
- PUT /extractions/{run_id} - Update extraction fields
- POST /extractions/{run_id}/approve - Approve for posting

### TOCOnline
- POST /toconline/post - Post to TOCOnline
- GET /toconline/status/{record_id} - Get document status

### Admin
- GET /admin/metrics - Get system metrics
- GET /admin/audit-logs - Get audit logs
- GET /admin/users - List users
- PUT /admin/users/{user_id}/roles - Update user roles

## Database Schema

- users - User accounts and authentication
- jobs - Processing jobs
- documents - Uploaded documents
- extraction_runs - OCR/LLM extraction runs
- extraction_fields - Extracted field values
- audit_logs - Comprehensive audit trail

## Mock Services

By default, the application uses mock implementations for:
- OCR (simulates Tesseract/PaddleOCR)
- LLM (simulates OpenAI/Phi-4)
- TOCOnline API (simulates real API)

To use real services, set environment variables in `.env` and update USE_REAL_* flags.
