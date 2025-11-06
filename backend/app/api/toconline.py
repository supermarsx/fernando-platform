from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.extraction import ExtractionRun, ExtractionField
from app.models.audit import AuditLog
from app.schemas.schemas import TOCOnlinePostRequest, TOCOnlinePostResponse
from app.core.security import require_role
from app.services.mock_toconline import MockTOCOnlineService

router = APIRouter(prefix="/toconline", tags=["toconline"])


@router.post("/post", response_model=TOCOnlinePostResponse)
def post_to_toconline(
    post_data: TOCOnlinePostRequest,
    current_user: User = Depends(require_role("reviewer")),
    db: Session = Depends(get_db)
):
    """Post approved extraction to TOCOnline"""
    # Get extraction run
    extraction_run = db.query(ExtractionRun).filter(
        ExtractionRun.run_id == post_data.run_id
    ).first()
    
    if not extraction_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction run not found"
        )
    
    # Get all fields
    fields = db.query(ExtractionField).filter(
        ExtractionField.run_id == post_data.run_id
    ).all()
    
    # Build fields dictionary
    fields_dict = {
        field.field_name: {
            "value": field.normalized_value or field.value,
            "confidence": field.confidence
        }
        for field in fields
    }
    
    # Initialize TOCOnline service
    toconline_service = MockTOCOnlineService()
    
    # Authenticate
    auth_result = toconline_service.authenticate()
    
    # Map fields to TOCOnline schema
    mapped_data = toconline_service.map_fields_to_toconline(fields_dict)
    
    # Validate before posting
    validation = toconline_service.validate_document(mapped_data)
    
    if not validation["valid"]:
        # Log validation errors
        audit_log = AuditLog(
            actor_user_id=current_user.user_id,
            action="toconline.validation_failed",
            target_type="extraction_run",
            target_id=post_data.run_id,
            metadata_json={
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        )
        db.add(audit_log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Document validation failed",
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        )
    
    # Post to TOCOnline
    post_result = toconline_service.post_document(mapped_data)
    
    # Handle response
    if post_result["status"] == "success":
        # Log success
        audit_log = AuditLog(
            actor_user_id=current_user.user_id,
            action="toconline.posted",
            target_type="extraction_run",
            target_id=post_data.run_id,
            metadata_json={
                "toconline_record_id": post_result["recordId"],
                "at_reference": post_result.get("atReference"),
                "validation_status": post_result.get("validationStatus")
            }
        )
        db.add(audit_log)
        db.commit()
        
        return TOCOnlinePostResponse(
            toconline_record_id=post_result["recordId"],
            status="success",
            error_code=None
        )
    else:
        # Log error
        audit_log = AuditLog(
            actor_user_id=current_user.user_id,
            action="toconline.post_failed",
            target_type="extraction_run",
            target_id=post_data.run_id,
            metadata_json={
                "error_code": post_result["errorCode"],
                "error_message": post_result["message"]
            }
        )
        db.add(audit_log)
        db.commit()
        
        return TOCOnlinePostResponse(
            toconline_record_id=None,
            status="error",
            error_code=post_result["errorCode"]
        )


@router.get("/status/{record_id}", response_model=dict)
def get_toconline_status(
    record_id: str,
    current_user: User = Depends(require_role("reviewer")),
    db: Session = Depends(get_db)
):
    """Get status of a document in TOCOnline"""
    toconline_service = MockTOCOnlineService()
    
    # Authenticate
    auth_result = toconline_service.authenticate()
    
    # Get status
    status_result = toconline_service.get_document_status(record_id)
    
    return status_result
