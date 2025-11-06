from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.models.audit import AuditLog
from app.schemas.schemas import JobCreate, JobResponse, DocumentResponse
from app.core.security import get_current_user
from app.core.config import settings
from app.services.document_processor import DocumentProcessingService, calculate_file_checksum
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=2)


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new processing job"""
    new_job = Job(
        priority=job_data.priority,
        queue_name=job_data.queue_name,
        uploaded_by=current_user.user_id,
        status="queued"
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Log audit event
    audit_log = AuditLog(
        actor_user_id=current_user.user_id,
        action="job.created",
        target_type="job",
        target_id=new_job.job_id,
        metadata_json={"priority": job_data.priority, "queue": job_data.queue_name}
    )
    db.add(audit_log)
    db.commit()
    
    return new_job


@router.post("/{job_id}/upload", response_model=List[DocumentResponse])
async def upload_documents(
    job_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload documents to a job and start processing"""
    # Verify job exists and belongs to user
    job = db.query(Job).filter(
        Job.job_id == job_id,
        Job.uploaded_by == current_user.user_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    documents = []
    
    for file in files:
        # Validate file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {file_extension}"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        storage_filename = f"{file_id}{file_extension}"
        storage_path = upload_dir / storage_filename
        
        # Save file
        with storage_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Calculate checksum
        checksum = calculate_file_checksum(str(storage_path))
        
        # Check for duplicates
        existing_doc = db.query(Document).filter(
            Document.checksum_sha256 == checksum
        ).first()
        
        if existing_doc:
            # Remove duplicate file
            storage_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document already uploaded: {file.filename}"
            )
        
        # Create document record
        document = Document(
            job_id=job_id,
            original_filename=file.filename,
            storage_url=str(storage_path),
            mime_type=file.content_type or "application/octet-stream",
            pages=1,  # Would be determined by actual file analysis
            checksum_sha256=checksum,
            uploaded_by=current_user.user_id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        documents.append(document)
        
        # Log audit event
        audit_log = AuditLog(
            actor_user_id=current_user.user_id,
            action="document.uploaded",
            target_type="document",
            target_id=document.document_id,
            metadata_json={
                "filename": file.filename,
                "size": storage_path.stat().st_size,
                "checksum": checksum
            }
        )
        db.add(audit_log)
    
    db.commit()
    
    # Start processing asynchronously
    for document in documents:
        # In production, this would be a Celery task
        executor.submit(process_document_background, document.document_id, current_user.user_id)
    
    return documents


def process_document_background(document_id: str, user_id: str):
    """Background task to process document"""
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.document_id == document_id).first()
        if document:
            processor = DocumentProcessingService(db)
            processor.process_document(document, user_id)
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
    finally:
        db.close()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job details"""
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check permissions
    if job.uploaded_by != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job"
        )
    
    return job


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    status: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List jobs for current user"""
    query = db.query(Job)
    
    # Filter by user unless admin
    if "admin" not in current_user.roles:
        query = query.filter(Job.uploaded_by == current_user.user_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Job.status == status)
    
    # Order by creation date descending
    query = query.order_by(Job.created_at.desc())
    
    # Pagination
    jobs = query.offset(skip).limit(limit).all()
    
    return jobs


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a job"""
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check permissions
    if job.uploaded_by != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this job"
        )
    
    # Update status
    job.status = "canceled"
    job.finished_at = db.func.now()
    
    # Log audit event
    audit_log = AuditLog(
        actor_user_id=current_user.user_id,
        action="job.canceled",
        target_type="job",
        target_id=job_id
    )
    db.add(audit_log)
    
    db.commit()
    
    return None
