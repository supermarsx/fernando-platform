from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.extraction import ExtractionRun, ExtractionField
from app.models.audit import AuditLog
from app.schemas.schemas import (
    ExtractionRunResponse, 
    ExtractionFieldResponse,
    ExtractionUpdateRequest
)
from app.core.security import get_current_user, require_role

router = APIRouter(prefix="/extractions", tags=["extractions"])


@router.get("/document/{document_id}", response_model=ExtractionRunResponse)
def get_extraction(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get extraction results for a document"""
    # Get the latest LLM extraction run
    extraction_run = db.query(ExtractionRun).filter(
        ExtractionRun.document_id == document_id,
        ExtractionRun.stage == "llm"
    ).order_by(ExtractionRun.finished_at.desc()).first()
    
    if not extraction_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extraction found for this document"
        )
    
    # Get all fields for this run
    fields = db.query(ExtractionField).filter(
        ExtractionField.run_id == extraction_run.run_id
    ).all()
    
    # Build response
    response = ExtractionRunResponse(
        run_id=extraction_run.run_id,
        document_id=extraction_run.document_id,
        stage=extraction_run.stage,
        status=extraction_run.status,
        engine_name=extraction_run.engine_name,
        model_version=extraction_run.model_version,
        confidence_avg=extraction_run.confidence_avg,
        fields=[ExtractionFieldResponse(
            field_id=f.field_id,
            field_name=f.field_name,
            value=f.value,
            confidence=f.confidence,
            validation_status=f.validation_status,
            correction_applied=f.correction_applied,
            normalized_value=f.normalized_value
        ) for f in fields],
        started_at=extraction_run.started_at,
        finished_at=extraction_run.finished_at
    )
    
    return response


@router.put("/{run_id}", response_model=dict)
def update_extraction(
    run_id: str,
    update_data: ExtractionUpdateRequest,
    current_user: User = Depends(require_role("reviewer")),
    db: Session = Depends(get_db)
):
    """Update extracted fields (manual review/correction)"""
    # Verify run exists
    extraction_run = db.query(ExtractionRun).filter(
        ExtractionRun.run_id == run_id
    ).first()
    
    if not extraction_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction run not found"
        )
    
    updated_fields = []
    
    for field_update in update_data.fields:
        # Get field
        field = db.query(ExtractionField).filter(
            ExtractionField.field_id == field_update.field_id,
            ExtractionField.run_id == run_id
        ).first()
        
        if not field:
            continue
        
        # Store old value for audit
        old_value = field.value
        
        # Update field
        field.value = field_update.value
        field.normalized_value = field_update.normalized_value or field_update.value
        field.validation_status = field_update.validation_status
        field.correction_applied = True
        
        updated_fields.append({
            "field_id": field.field_id,
            "field_name": field.field_name,
            "old_value": old_value,
            "new_value": field.value
        })
        
        # Log audit event
        audit_log = AuditLog(
            actor_user_id=current_user.user_id,
            action="extraction.corrected",
            target_type="extraction_field",
            target_id=field.field_id,
            metadata_json={
                "run_id": run_id,
                "field_name": field.field_name,
                "old_value": old_value,
                "new_value": field.value
            }
        )
        db.add(audit_log)
    
    db.commit()
    
    return {
        "run_id": run_id,
        "updated_fields": updated_fields,
        "message": f"Updated {len(updated_fields)} fields"
    }


@router.post("/{run_id}/approve", response_model=dict)
def approve_extraction(
    run_id: str,
    current_user: User = Depends(require_role("reviewer")),
    db: Session = Depends(get_db)
):
    """Approve extraction for posting to TOCOnline"""
    # Get extraction run
    extraction_run = db.query(ExtractionRun).filter(
        ExtractionRun.run_id == run_id
    ).first()
    
    if not extraction_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction run not found"
        )
    
    # Get document and job
    document = db.query(Document).filter(
        Document.document_id == extraction_run.document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update job status
    from app.models.job import Job
    job = db.query(Job).filter(Job.job_id == document.job_id).first()
    if job:
        job.status = "posted"  # Would be "approved" and then posted via TOCOnline
        job.finished_at = db.func.now()
    
    # Log audit event
    audit_log = AuditLog(
        actor_user_id=current_user.user_id,
        action="extraction.approved",
        target_type="extraction_run",
        target_id=run_id,
        metadata_json={
            "document_id": extraction_run.document_id,
            "job_id": document.job_id
        }
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "run_id": run_id,
        "status": "approved",
        "message": "Extraction approved for posting"
    }
