# Deployment Instructions

## Complete Fernando Platform

### System Architecture

**Backend (FastAPI):**
- Location: `/workspace/fernando/backend`
- Database: SQLite (development) / PostgreSQL (production)
- Port: 8000
- Authentication: JWT tokens
- Mock services for OCR, LLM, and TOCOnline

**Frontend (React + TypeScript):**
- Location: `/workspace/fernando/frontend/accounting-frontend`
- Framework: React 18 + Vite + Tailwind CSS
- Port: 5173 (development)
- API Connection: http://localhost:8000

### Step 1: Backend Setup

```bash
# Navigate to backend directory
cd /workspace/fernando/backend

# Install Python dependencies
uv pip install -r requirements.txt

# Install email validator (required for Pydantic)
uv pip install email-validator

# Start the backend server
cd /workspace/fernando/backend
PYTHONPATH=/workspace/fernando/backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be available at:
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Step 2: Frontend Setup

```bash
# Navigate to frontend directory
cd /workspace/fernando/frontend/accounting-frontend

# Install dependencies
pnpm install

# Start development server
pnpm run dev
```

The frontend will be available at: http://localhost:5173

### Step 3: First Time Usage

1. Open your browser to http://localhost:5173
2. Click "Register" to create a new account
3. After registration, you'll be logged in automatically
4. Upload documents using the "Upload Documents" button
5. Track processing status in the dashboard

### Default User Roles

- New users get "uploader" role by default
- Use the admin API to assign additional roles:
  - `reviewer` - Can review and approve documents
  - `auditor` - Can view audit logs (read-only)
  - `admin` - Full system access

### API Endpoints Overview

**Authentication:**
- POST /auth/register - Register new user
- POST /auth/login - Login and get JWT token
- GET /auth/me - Get current user info

**Jobs:**
- POST /jobs/ - Create new job
- POST /jobs/{job_id}/upload - Upload documents
- GET /jobs/{job_id} - Get job details
- GET /jobs/ - List jobs

**Extractions:**
- GET /extractions/document/{document_id} - Get extraction results
- PUT /extractions/{run_id} - Update fields (manual correction)
- POST /extractions/{run_id}/approve - Approve for posting

**TOCOnline:**
- POST /toconline/post - Post to TOCOnline
- GET /toconline/status/{record_id} - Get status

**Admin:**
- GET /admin/metrics - System metrics
- GET /admin/audit-logs - Audit logs
- GET /admin/users - List users
- PUT /admin/users/{user_id}/roles - Update roles

### Mock Services

The application uses mock implementations for:

1. **OCR Service** (`app/services/mock_ocr.py`)
   - Simulates text extraction from documents
   - Returns realistic Portuguese invoice text
   - Provides confidence scores

2. **LLM Service** (`app/services/mock_llm.py`)
   - Simulates AI-based field extraction
   - Extracts: supplier, NIF, date, amounts, VAT
   - Validates extracted data

3. **TOCOnline Service** (`app/services/mock_toconline.py`)
   - Simulates OAuth2 authentication
   - Mock document posting with success/error scenarios
   - Status checking functionality

### Database Schema

Tables created automatically on first run:
- `users` - User accounts and authentication
- `jobs` - Processing jobs
- `documents` - Uploaded documents
- `extraction_runs` - OCR/LLM extraction runs
- `extraction_fields` - Extracted field values
- `audit_logs` - Comprehensive audit trail

Database file: `accounting_automation.db` (SQLite)

### Testing the Application

1. **Register a User:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "full_name": "Test User"
  }'
```

2. **Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

3. **Check Health:**
```bash
curl http://localhost:8000/health
```

### Production Deployment

**Backend:**
1. Set `DEBUG=False` in `.env`
2. Use PostgreSQL instead of SQLite
3. Set strong `SECRET_KEY`
4. Use production WSGI server (gunicorn)
5. Set up HTTPS with reverse proxy (nginx)

**Frontend:**
1. Build for production:
```bash
cd frontend/accounting-frontend
pnpm run build
```

2. Deploy `dist` directory to web server
3. Configure backend API URL in production

### Troubleshooting

**Backend won't start:**
- Check Python version (3.10+)
- Ensure all dependencies installed
- Check PYTHONPATH is set correctly
- Review logs for error messages

**Frontend won't build:**
- Clear node_modules and reinstall
- Check Node version (18+)
- Ensure pnpm is installed

**Database errors:**
- Delete `accounting_automation.db` to reset
- Check file permissions
- Review migration logs

### Features Implemented

- User authentication with JWT
- Document upload (drag-and-drop)
- Automatic OCR processing (mocked)
- LLM field extraction (mocked)
- Manual review interface
- TOCOnline integration (mocked)
- Job tracking dashboard
- Audit logging system
- Role-based access control
- Admin metrics and monitoring

### Next Steps

When real API keys become available:
1. Replace mock OCR with real Tesseract/PaddleOCR
2. Integrate OpenAI API or local Phi-4 model
3. Connect real TOCOnline API with OAuth2
4. Add email notifications
5. Implement batch processing queue

