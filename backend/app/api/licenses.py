from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.license import License, LicenseTierModel
from app.schemas.license_schemas import (
    LicenseTierCreate, LicenseTierUpdate, LicenseTierResponse,
    LicenseCreate, LicenseUpdate, LicenseResponse,
    LicenseValidationRequest, LicenseValidationResponse,
    LicenseAnalytics, LicenseUpgradeRequest, LicenseRenewalRequest
)
from app.services.licensing_service import LicensingService, initialize_default_tiers

router = APIRouter(prefix="/api/v1/licenses", tags=["licenses"])


# License Tier Management (Admin Only)
@router.get("/tiers", response_model=List[LicenseTierResponse])
async def list_license_tiers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all license tiers"""
    tiers = db.query(LicenseTierModel).filter(LicenseTierModel.is_active == True).all()
    return tiers


@router.post("/tiers", response_model=LicenseTierResponse, dependencies=[Depends(require_role("admin"))])
async def create_license_tier(
    tier_data: LicenseTierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new license tier (Admin only)"""
    # Check if tier already exists
    existing = db.query(LicenseTierModel).filter(LicenseTierModel.name == tier_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License tier with this name already exists"
        )
    
    tier = LicenseTierModel(**tier_data.dict())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return tier


@router.put("/tiers/{tier_id}", response_model=LicenseTierResponse, dependencies=[Depends(require_role("admin"))])
async def update_license_tier(
    tier_id: int,
    tier_data: LicenseTierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a license tier (Admin only)"""
    tier = db.query(LicenseTierModel).filter(LicenseTierModel.tier_id == tier_id).first()
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License tier not found"
        )
    
    update_data = tier_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tier, field, value)
    
    db.commit()
    db.refresh(tier)
    return tier


# License Management
@router.get("", response_model=List[LicenseResponse], dependencies=[Depends(require_role("admin"))])
async def list_licenses(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    tier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all licenses (Admin only)"""
    query = db.query(License)
    
    if status_filter:
        query = query.filter(License.status == status_filter)
    
    if tier_id:
        query = query.filter(License.tier_id == tier_id)
    
    licenses = query.offset(skip).limit(limit).all()
    return licenses


@router.post("", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def create_license(
    license_data: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new license (Admin only)"""
    licensing_service = LicensingService(db)
    
    # Verify tier exists
    tier = db.query(LicenseTierModel).filter(LicenseTierModel.tier_id == license_data.tier_id).first()
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License tier not found"
        )
    
    license = licensing_service.create_license(
        license_data=license_data,
        created_by_user_id=current_user.user_id
    )
    
    return license


@router.get("/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get license details"""
    license = db.query(License).filter(License.license_id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    # Only admins can view any license, users can only view their assigned licenses
    if current_user.role != "admin":
        # Check if user has access to this license
        # Implementation depends on your license assignment logic
        pass
    
    return license


@router.put("/{license_id}", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def update_license(
    license_id: int,
    license_data: LicenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a license (Admin only)"""
    license = db.query(License).filter(License.license_id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    update_data = license_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(license, field, value)
    
    db.commit()
    db.refresh(license)
    return license


@router.post("/validate", response_model=LicenseValidationResponse)
async def validate_license(
    validation_request: LicenseValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate a license key"""
    licensing_service = LicensingService(db)
    return licensing_service.validate_license(validation_request)


@router.post("/{license_id}/renew", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def renew_license(
    license_id: int,
    renewal_request: LicenseRenewalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Renew a license (Admin only)"""
    licensing_service = LicensingService(db)
    
    try:
        license = licensing_service.renew_license(
            license_id=license_id,
            renewal_months=renewal_request.renewal_period_months,
            renewed_by_user_id=current_user.user_id
        )
        return license
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{license_id}/upgrade", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def upgrade_license(
    license_id: int,
    upgrade_request: LicenseUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upgrade a license to a new tier (Admin only)"""
    licensing_service = LicensingService(db)
    
    try:
        license = licensing_service.upgrade_license(
            license_id=license_id,
            new_tier_id=upgrade_request.new_tier_id,
            upgraded_by_user_id=current_user.user_id
        )
        return license
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{license_id}/suspend", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def suspend_license(
    license_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Suspend a license (Admin only)"""
    licensing_service = LicensingService(db)
    
    try:
        license = licensing_service.suspend_license(
            license_id=license_id,
            reason=reason,
            suspended_by_user_id=current_user.user_id
        )
        return license
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{license_id}/revoke", response_model=LicenseResponse, dependencies=[Depends(require_role("admin"))])
async def revoke_license(
    license_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a license (Admin only)"""
    licensing_service = LicensingService(db)
    
    try:
        license = licensing_service.revoke_license(
            license_id=license_id,
            reason=reason,
            revoked_by_user_id=current_user.user_id
        )
        return license
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/analytics/overview", response_model=LicenseAnalytics, dependencies=[Depends(require_role("admin"))])
async def get_license_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get licensing analytics (Admin only)"""
    licensing_service = LicensingService(db)
    analytics = licensing_service.get_license_analytics()
    
    # Calculate revenue
    tiers = db.query(LicenseTierModel).all()
    total_monthly = sum(tier.price_monthly * analytics["licenses_by_tier"].get(tier.name, 0) for tier in tiers)
    total_yearly = sum(tier.price_yearly * analytics["licenses_by_tier"].get(tier.name, 0) for tier in tiers)
    
    return {
        **analytics,
        "total_revenue_monthly": total_monthly,
        "total_revenue_yearly": total_yearly,
        "usage_by_feature": {},
        "top_organizations": []
    }


@router.post("/initialize-tiers", dependencies=[Depends(require_role("admin"))])
async def initialize_tiers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initialize default license tiers (Admin only)"""
    initialize_default_tiers(db)
    return {"message": "Default license tiers initialized"}
