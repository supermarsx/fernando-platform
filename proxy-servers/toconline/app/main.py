from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uuid
import random

app = FastAPI(title="TOCOnline Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TOCOnlinePostRequest(BaseModel):
    supplier: str
    supplier_tax_id: str
    document_number: str
    document_date: str
    currency: str
    net_amount: float
    vat_amount: float
    gross_amount: float
    vat_rate: float

class TOCOnlinePostResponse(BaseModel):
    status: str
    record_id: Optional[str]
    message: str
    at_reference: Optional[str]  # Portuguese tax authority reference


@app.post("/toconline/auth")
async def authenticate():
    """Authenticate with TOCOnline API"""
    # Mock OAuth2 authentication
    return {
        "access_token": f"mock_token_{uuid.uuid4().hex}",
        "token_type": "Bearer",
        "expires_in": 3600
    }


@app.post("/toconline/post", response_model=TOCOnlinePostResponse)
async def post_document(request: TOCOnlinePostRequest):
    """Post document to TOCOnline"""
    
    # Validate data
    if abs(request.net_amount + request.vat_amount - request.gross_amount) > 0.01:
        raise HTTPException(
            status_code=400,
            detail="VAT calculation error"
        )
    
    # Simulate success/failure (95% success rate)
    if random.random() < 0.95:
        record_id = f"TOC{uuid.uuid4().hex[:12].upper()}"
        at_reference = f"AT{random.randint(100000000, 999999999)}"
        
        return TOCOnlinePostResponse(
            status="success",
            record_id=record_id,
            message="Document posted successfully",
            at_reference=at_reference
        )
    else:
        # Simulate error
        errors = [
            "Duplicate document number",
            "Invalid tax ID",
            "Missing required field"
        ]
        error_msg = random.choice(errors)
        
        return TOCOnlinePostResponse(
            status="error",
            record_id=None,
            message=error_msg,
            at_reference=None
        )


@app.get("/toconline/status/{record_id}")
async def get_status(record_id: str):
    """Get document status from TOCOnline"""
    statuses = ["DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "FINALIZED"]
    
    return {
        "record_id": record_id,
        "status": random.choice(statuses),
        "last_updated": "2025-11-06T00:00:00Z"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "toconline-proxy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
