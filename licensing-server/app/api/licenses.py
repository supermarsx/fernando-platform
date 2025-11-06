from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.licensing import (
    create_license_token,
    verify_license_token,
    get_tier_limits,
    get_hardware_fingerprint
)
from app.models.license import License, LicenseValidation, UsageLog
from app.schemas.license import (
    LicenseCreate,
    LicenseResponse,
    LicenseValidateRequest,
    LicenseValidateResponse,
    LicenseRenewRequest,
    UsageLogRequest,
    UsageStatsResponse
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_license(
    license_data: LicenseCreate,
    db: Session = Depends(get_db)
):
    """Create a new license"""
    # Create license record
    expires_at = datetime.utcnow() + timedelta(days=license_data.expires_days)
    
    new_license = License(
        user_id=license_data.user_id,
        company_name=license_data.company_name,
        contact_email=license_data.contact_email,
        tier=license_data.tier,
        hardware_fingerprint=license_data.hardware_fingerprint,
        expires_at=expires_at,
        features_enabled=get_tier_limits(license_data.tier)["features"]
    )
    
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    
    # Generate license token
    license_token = create_license_token(
        license_id=new_license.license_id,
        user_id=new_license.user_id,
        tier=new_license.tier,
        hardware_fingerprint=license_data.hardware_fingerprint or "",
        expires_delta=timedelta(days=license_data.expires_days)
    )
    
    return {
        "license_id": new_license.license_id,
        "license_token": license_token,
        "tier": new_license.tier,
        "expires_at": new_license.expires_at,
        "message": "License created successfully"
    }


@router.post("/validate", response_model=LicenseValidateResponse)
def validate_license(
    request_data: LicenseValidateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Validate a license token"""
    try:
        # Verify token
        payload = verify_license_token(
            request_data.license_token,
            request_data.hardware_fingerprint
        )
        
        license_id = payload["sub"]
        
        # Get license from database
        license_record = db.query(License).filter(License.license_id == license_id).first()
        
        if not license_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        # Check license status
        is_valid = True
        message = "License is valid"
        
        if license_record.status != "active":
            is_valid = False
            message = f"License is {license_record.status}"
        
        if license_record.expires_at and license_record.expires_at < datetime.utcnow():
            is_valid = False
            message = "License has expired"
        
        # Log validation
        validation_log = LicenseValidation(
            license_id=license_id,
            hardware_fingerprint=request_data.hardware_fingerprint,
            is_valid=is_valid,
            validation_message=message,
            client_version=request_data.client_version,
            client_ip=request.client.host if request.client else None
        )
        
        db.add(validation_log)
        
        # Update last validated
        license_record.last_validated_at = datetime.utcnow()
        
        db.commit()
        
        # Get tier limits and usage
        limits = get_tier_limits(license_record.tier)
        usage = {
            "current_month": license_record.docs_processed_this_month,
            "total": license_record.total_docs_processed
        }
        
        return LicenseValidateResponse(
            is_valid=is_valid,
            license_id=license_id,
            tier=license_record.tier,
            message=message,
            limits=limits,
            usage=usage
        )
        
    except ValueError as e:
        return LicenseValidateResponse(
            is_valid=False,
            license_id=None,
            tier=None,
            message=str(e)
        )


@router.get("/{license_id}", response_model=LicenseResponse)
def get_license(license_id: str, db: Session = Depends(get_db)):
    """Get license details"""
    license_record = db.query(License).filter(License.license_id == license_id).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    return license_record


@router.post("/{license_id}/renew", response_model=dict)
def renew_license(
    license_id: str,
    renew_data: LicenseRenewRequest,
    db: Session = Depends(get_db)
):
    """Renew a license"""
    license_record = db.query(License).filter(License.license_id == license_id).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    # Extend expiration
    current_expires = license_record.expires_at or datetime.utcnow()
    new_expires = max(current_expires, datetime.utcnow()) + timedelta(days=renew_data.extend_days)
    
    license_record.expires_at = new_expires
    license_record.last_renewed_at = datetime.utcnow()
    license_record.status = "active"
    
    db.commit()
    
    # Generate new token
    new_token = create_license_token(
        license_id=license_record.license_id,
        user_id=license_record.user_id,
        tier=license_record.tier,
        hardware_fingerprint=license_record.hardware_fingerprint or "",
        expires_delta=timedelta(days=renew_data.extend_days)
    )
    
    return {
        "license_id": license_id,
        "license_token": new_token,
        "expires_at": new_expires,
        "message": "License renewed successfully"
    }


@router.post("/{license_id}/usage", status_code=status.HTTP_201_CREATED)
def log_usage(
    license_id: str,
    usage_data: UsageLogRequest,
    db: Session = Depends(get_db)
):
    """Log usage for a license"""
    license_record = db.query(License).filter(License.license_id == license_id).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    # Create usage log
    usage_log = UsageLog(
        license_id=license_id,
        action=usage_data.action,
        resource_type=usage_data.resource_type,
        quantity=usage_data.quantity,
        metadata=usage_data.metadata
    )
    
    db.add(usage_log)
    
    # Update license usage counters
    if usage_data.action == "document_processed":
        license_record.docs_processed_this_month += usage_data.quantity
        license_record.total_docs_processed += usage_data.quantity
    
    db.commit()
    
    return {"message": "Usage logged successfully"}


@router.get("/{license_id}/usage-stats", response_model=UsageStatsResponse)
def get_usage_stats(license_id: str, db: Session = Depends(get_db)):
    """Get usage statistics for a license"""
    license_record = db.query(License).filter(License.license_id == license_id).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    limits = get_tier_limits(license_record.tier)
    limit = limits["docs_per_month"]
    current_usage = license_record.docs_processed_this_month
    
    remaining = limit - current_usage if limit > 0 else -1
    usage_percentage = (current_usage / limit * 100) if limit > 0 else 0
    
    return UsageStatsResponse(
        license_id=license_id,
        current_month_usage=current_usage,
        total_usage=license_record.total_docs_processed,
        limit=limit,
        remaining=remaining,
        usage_percentage=usage_percentage
    )


@router.delete("/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_license(license_id: str, db: Session = Depends(get_db)):
    """Revoke a license"""
    license_record = db.query(License).filter(License.license_id == license_id).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    license_record.status = "revoked"
    db.commit()
    
    return None
