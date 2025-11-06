from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
from typing import Optional
import uuid
import redis
import json

app = FastAPI(title="OCR Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client for job queue
redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

class OCRRequest(BaseModel):
    document_url: str
    language: str = "por"  # Portuguese
    engine: str = "tesseract"  # tesseract, paddleocr, easyocr
    
class OCRResponse(BaseModel):
    job_id: str
    status: str
    message: str


async def process_ocr_job(job_id: str, document_url: str, language: str, engine: str):
    """Background task to process OCR"""
    try:
        # Update status to processing
        redis_client.hset(f"ocr:job:{job_id}", mapping={
            "status": "processing",
            "progress": "0"
        })
        
        # Simulate OCR processing (in production, call real OCR service)
        await asyncio.sleep(2)  # Simulate processing time
        
        # Mock OCR result
        result = {
            "text": "Sample extracted text from Portuguese invoice...",
            "confidence": 0.95,
            "language": language,
            "engine": engine
        }
        
        # Store result
        redis_client.hset(f"ocr:job:{job_id}", mapping={
            "status": "completed",
            "progress": "100",
            "result": json.dumps(result)
        })
        
    except Exception as e:
        redis_client.hset(f"ocr:job:{job_id}", mapping={
            "status": "failed",
            "error": str(e)
        })


@app.post("/ocr/process", response_model=OCRResponse)
async def process_ocr(
    request: OCRRequest,
    background_tasks: BackgroundTasks
):
    """Submit OCR processing job"""
    job_id = str(uuid.uuid4())
    
    # Store job in Redis
    redis_client.hset(f"ocr:job:{job_id}", mapping={
        "status": "queued",
        "document_url": request.document_url,
        "language": request.language,
        "engine": request.engine
    })
    
    # Add to processing queue
    background_tasks.add_task(
        process_ocr_job,
        job_id,
        request.document_url,
        request.language,
        request.engine
    )
    
    return OCRResponse(
        job_id=job_id,
        status="queued",
        message="OCR job submitted successfully"
    )


@app.get("/ocr/status/{job_id}")
async def get_ocr_status(job_id: str):
    """Get OCR job status"""
    job_data = redis_client.hgetall(f"ocr:job:{job_id}")
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        "job_id": job_id,
        "status": job_data.get("status"),
        "progress": job_data.get("progress", "0")
    }
    
    if job_data.get("status") == "completed":
        response["result"] = json.loads(job_data.get("result", "{}"))
    elif job_data.get("status") == "failed":
        response["error"] = job_data.get("error")
    
    return response


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ocr-proxy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
