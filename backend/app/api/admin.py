from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.models.extraction import ExtractionRun
from app.models.audit import AuditLog
from app.schemas.schemas import AuditLogResponse
from app.core.security import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=dict)
def get_metrics(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get system metrics for admin dashboard"""
    # Job statistics
    total_jobs = db.query(func.count(Job.job_id)).scalar()
    queued_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "queued").scalar()
    processing_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "processing").scalar()
    needs_review_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "needs_review").scalar()
    posted_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "posted").scalar()
    failed_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "failed").scalar()
    
    # Document statistics
    total_documents = db.query(func.count(Document.document_id)).scalar()
    
    # Extraction statistics
    total_extractions = db.query(func.count(ExtractionRun.run_id)).scalar()
    avg_confidence = db.query(func.avg(ExtractionRun.confidence_avg)).scalar()
    
    # User statistics
    total_users = db.query(func.count(User.user_id)).scalar()
    active_users = db.query(func.count(User.user_id)).filter(User.status == "active").scalar()
    
    return {
        "jobs": {
            "total": total_jobs,
            "queued": queued_jobs,
            "processing": processing_jobs,
            "needs_review": needs_review_jobs,
            "posted": posted_jobs,
            "failed": failed_jobs
        },
        "documents": {
            "total": total_documents
        },
        "extractions": {
            "total": total_extractions,
            "average_confidence": round(avg_confidence or 0.0, 3)
        },
        "users": {
            "total": total_users,
            "active": active_users
        }
    }


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: str = None,
    target_type: str = None,
    current_user: User = Depends(require_role("auditor")),
    db: Session = Depends(get_db)
):
    """Get audit logs"""
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    
    # Order by creation date descending
    query = query.order_by(AuditLog.created_at.desc())
    
    # Pagination
    logs = query.offset(skip).limit(limit).all()
    
    return logs


@router.get("/users", response_model=List[dict])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all users"""
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
            "roles": user.roles,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.put("/users/{user_id}/roles", response_model=dict)
def update_user_roles(
    user_id: str,
    roles: List[str],
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update user roles"""
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate roles
    valid_roles = ["uploader", "reviewer", "auditor", "admin"]
    for role in roles:
        if role not in valid_roles:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
    
    user.roles = roles
    
    # Log audit event
    audit_log = AuditLog(
        actor_user_id=current_user.user_id,
        action="user.roles_updated",
        target_type="user",
        target_id=user_id,
        metadata_json={"roles": roles}
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "user_id": user_id,
        "roles": roles,
        "message": "User roles updated successfully"
    }
