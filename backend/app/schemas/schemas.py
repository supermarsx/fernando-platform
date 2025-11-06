from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    user_id: str
    status: str
    roles: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class JobCreate(BaseModel):
    priority: int = 0
    queue_name: str = "default"


class JobResponse(BaseModel):
    job_id: str
    status: str
    priority: int
    queue_name: str
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_code: Optional[str]
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    document_id: str
    job_id: str
    original_filename: str
    storage_url: str
    mime_type: str
    pages: int
    checksum_sha256: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExtractionFieldResponse(BaseModel):
    field_id: str
    field_name: str
    value: str
    confidence: float
    validation_status: str
    correction_applied: bool
    normalized_value: Optional[str]
    
    class Config:
        from_attributes = True


class ExtractionRunResponse(BaseModel):
    run_id: str
    document_id: str
    stage: str
    status: str
    engine_name: str
    model_version: str
    confidence_avg: Optional[float]
    fields: List[ExtractionFieldResponse] = []
    started_at: datetime
    finished_at: datetime
    
    class Config:
        from_attributes = True


class FieldUpdate(BaseModel):
    field_id: str
    value: str
    normalized_value: Optional[str] = None
    validation_status: str = "corrected"


class ExtractionUpdateRequest(BaseModel):
    fields: List[FieldUpdate]


class TOCOnlinePostRequest(BaseModel):
    run_id: str


class TOCOnlinePostResponse(BaseModel):
    toconline_record_id: str
    status: str
    error_code: Optional[str] = None


class AuditLogResponse(BaseModel):
    audit_id: str
    actor_user_id: str
    action: str
    target_type: str
    target_id: str
    metadata_json: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True
