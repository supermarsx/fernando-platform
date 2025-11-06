from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class LicenseCreate(BaseModel):
    user_id: str
    company_name: str
    contact_email: EmailStr
    tier: str  # free, pro, enterprise
    hardware_fingerprint: Optional[str] = None
    expires_days: Optional[int] = 365


class LicenseResponse(BaseModel):
    license_id: str
    user_id: str
    company_name: str
    contact_email: str
    tier: str
    status: str
    hardware_fingerprint: Optional[str]
    docs_processed_this_month: int
    total_docs_processed: int
    features_enabled: List[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    last_validated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class LicenseValidateRequest(BaseModel):
    license_token: str
    hardware_fingerprint: str
    client_version: Optional[str] = None


class LicenseValidateResponse(BaseModel):
    is_valid: bool
    license_id: Optional[str]
    tier: Optional[str]
    message: str
    limits: Optional[dict] = None
    usage: Optional[dict] = None


class LicenseRenewRequest(BaseModel):
    license_id: str
    extend_days: int = 365


class UsageLogRequest(BaseModel):
    license_id: str
    action: str
    resource_type: Optional[str] = None
    quantity: int = 1
    metadata: Optional[dict] = None


class UsageStatsResponse(BaseModel):
    license_id: str
    current_month_usage: int
    total_usage: int
    limit: int
    remaining: int
    usage_percentage: float
