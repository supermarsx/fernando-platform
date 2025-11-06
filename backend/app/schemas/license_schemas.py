from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class LicenseTier(str, Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


# License Tier Schemas
class LicenseTierBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    max_documents_per_month: int
    max_users: int
    max_storage_gb: int
    features: Dict[str, Any]


class LicenseTierCreate(LicenseTierBase):
    pass


class LicenseTierUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    max_documents_per_month: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LicenseTierResponse(LicenseTierBase):
    tier_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# License Schemas
class LicenseBase(BaseModel):
    tier_id: int
    organization_name: str
    organization_email: str
    expires_at: datetime
    max_activations: int = 1
    metadata: Optional[Dict[str, Any]] = None


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    tier_id: Optional[int] = None
    organization_name: Optional[str] = None
    organization_email: Optional[str] = None
    status: Optional[LicenseStatus] = None
    expires_at: Optional[datetime] = None
    max_activations: Optional[int] = None
    hardware_fingerprint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LicenseResponse(LicenseBase):
    license_id: int
    license_key: str
    status: LicenseStatus
    issued_at: datetime
    last_validated_at: Optional[datetime] = None
    hardware_fingerprint: Optional[str] = None
    current_activations: int
    documents_processed_this_month: int
    last_reset_at: datetime
    created_at: datetime
    updated_at: datetime
    tier: LicenseTierResponse

    class Config:
        from_attributes = True


class LicenseValidationRequest(BaseModel):
    license_key: str
    hardware_fingerprint: Optional[str] = None


class LicenseValidationResponse(BaseModel):
    valid: bool
    license: Optional[LicenseResponse] = None
    message: str
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None


# License Assignment Schemas
class LicenseAssignmentCreate(BaseModel):
    license_id: int
    user_id: int


class LicenseAssignmentResponse(BaseModel):
    assignment_id: int
    license_id: int
    user_id: int
    assigned_at: datetime
    assigned_by: Optional[int] = None
    is_active: bool
    deactivated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# License Usage Schemas
class LicenseUsageCreate(BaseModel):
    license_id: int
    user_id: Optional[int] = None
    feature_used: str
    usage_count: int = 1
    metadata: Optional[Dict[str, Any]] = None


class LicenseUsageResponse(BaseModel):
    usage_id: int
    license_id: int
    user_id: Optional[int] = None
    feature_used: str
    usage_count: int
    usage_timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# License Audit Log Schemas
class LicenseAuditLogCreate(BaseModel):
    license_id: int
    user_id: Optional[int] = None
    action: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LicenseAuditLogResponse(BaseModel):
    audit_id: int
    license_id: int
    user_id: Optional[int] = None
    action: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Analytics Schemas
class LicenseAnalytics(BaseModel):
    total_licenses: int
    active_licenses: int
    expired_licenses: int
    suspended_licenses: int
    revoked_licenses: int
    licenses_by_tier: Dict[str, int]
    total_revenue_monthly: float
    total_revenue_yearly: float
    usage_by_feature: Dict[str, int]
    top_organizations: List[Dict[str, Any]]


class LicenseUpgradeRequest(BaseModel):
    license_id: int
    new_tier_id: int
    effective_date: Optional[datetime] = None


class LicenseRenewalRequest(BaseModel):
    license_id: int
    renewal_period_months: int = 12
