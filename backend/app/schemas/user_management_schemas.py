"""
Pydantic schemas for User Management API

Provides request/response models for user management endpoints
including validation, serialization, and API documentation.
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


# Enums
class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRoleLevel(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"
    GUEST = "guest"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


# Base Schemas
class UserManagementBase(BaseModel):
    """Base schema with common fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# User Schemas
class UserCreateRequest(BaseModel):
    """Request schema for creating a user"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_id: Optional[str] = None
    roles: Optional[List[str]] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdateRequest(BaseModel):
    """Request schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[UserStatus] = None
    organization_id: Optional[str] = None
    email_verified: Optional[bool] = None
    phone_verified: Optional[bool] = None
    onboarding_completed: Optional[bool] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None


class UserResponse(UserManagementBase):
    """Response schema for user data"""
    user_id: str
    email: str
    full_name: str
    status: UserStatus
    organization_id: Optional[str] = None
    roles: List[str] = []  # For backward compatibility
    email_verified: bool = False
    phone_verified: bool = False
    onboarding_completed: bool = False
    last_login: Optional[datetime] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_orm(cls, user):
        """Create response from ORM model"""
        return cls(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            organization_id=user.organization_id,
            roles=user.roles or [],
            email_verified=user.email_verified or False,
            phone_verified=user.phone_verified or False,
            onboarding_completed=user.onboarding_completed or False,
            last_login=getattr(user, 'last_login', None),
            phone=getattr(user, 'phone', None),
            department=getattr(user, 'department', None),
            job_title=getattr(user, 'job_title', None),
            created_at=user.created_at,
            updated_at=getattr(user, 'updated_at', None)
        )
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response schema for user list with pagination"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class UserStatisticsResponse(BaseModel):
    """Response schema for user statistics"""
    user_id: str
    email: str
    full_name: str
    status: str
    organization_id: Optional[str]
    created_at: str
    last_login: Optional[str]
    total_sessions: int
    active_sessions: int
    activity_last_24h: int
    activity_last_7d: int
    logins_last_24h: int
    active_role_assignments: int
    email_verified: bool
    phone_verified: bool
    mfa_enabled: bool
    password_age_days: Optional[int]


# Role and Permission Schemas
class RoleCreateRequest(BaseModel):
    """Request schema for creating a role"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    level: int = Field(default=0, ge=0, le=10)
    permissions: Optional[List[str]] = None


class RoleResponse(BaseModel):
    """Response schema for role data"""
    role_id: str
    name: str
    description: Optional[str]
    level: int
    is_system_role: bool
    created_at: datetime
    permissions: Optional[List[str]] = None
    
    @classmethod
    def from_orm(cls, role):
        """Create response from ORM model"""
        return cls(
            role_id=role.role_id,
            name=role.name,
            description=role.description,
            level=role.level,
            is_system_role=role.is_system_role,
            created_at=role.created_at,
            permissions=[
                rp.permission.name for rp in role.permissions
            ] if role.permissions else None
        )
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Response schema for permission data"""
    permission_id: str
    name: str
    description: Optional[str]
    resource: str
    action: str
    conditions: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class RoleAssignmentRequest(BaseModel):
    """Request schema for role assignment"""
    role_id: str
    organization_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class RoleAssignmentResponse(BaseModel):
    """Response schema for role assignment"""
    assignment_id: str
    user_id: str
    role_id: str
    organization_id: Optional[str]
    assigned_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    role_name: Optional[str] = None
    
    @classmethod
    def from_orm(cls, assignment):
        """Create response from ORM model"""
        return cls(
            assignment_id=assignment.assignment_id,
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            organization_id=assignment.organization_id,
            assigned_at=assignment.assigned_at,
            expires_at=assignment.expires_at,
            is_active=assignment.is_active,
            role_name=assignment.role.name if assignment.role else None
        )
    
    class Config:
        from_attributes = True


# Session Schemas
class UserSessionResponse(BaseModel):
    """Response schema for user session data"""
    session_id: str
    user_id: str
    organization_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_info: Optional[Dict[str, Any]]
    location: Optional[Dict[str, Any]]
    login_at: datetime
    last_activity_at: datetime
    logout_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    mfa_verified: bool
    risk_score: int
    
    @classmethod
    def from_orm(cls, session):
        """Create response from ORM model"""
        return cls(
            session_id=session.session_id,
            user_id=session.user_id,
            organization_id=session.organization_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            device_info=session.device_info,
            location=session.location,
            login_at=session.login_at,
            last_activity_at=session.last_activity_at,
            logout_at=session.logout_at,
            expires_at=session.expires_at,
            is_active=session.is_active,
            mfa_verified=session.mfa_verified,
            risk_score=session.risk_score
        )
    
    class Config:
        from_attributes = True


# Activity Schemas
class UserActivityResponse(BaseModel):
    """Response schema for user activity data"""
    activity_id: str
    user_id: str
    organization_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    success: bool
    error_message: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime
    
    @classmethod
    def from_orm(cls, activity):
        """Create response from ORM model"""
        return cls(
            activity_id=activity.activity_id,
            user_id=activity.user_id,
            organization_id=activity.organization_id,
            action=activity.action,
            resource_type=activity.resource_type,
            resource_id=activity.resource_id,
            details=activity.details,
            ip_address=activity.ip_address,
            user_agent=activity.user_agent,
            session_id=activity.session_id,
            success=activity.success,
            error_message=activity.error_message,
            duration_ms=activity.duration_ms,
            created_at=activity.created_at
        )
    
    class Config:
        from_attributes = True


# Invitation Schemas
class UserInvitationRequest(BaseModel):
    """Request schema for user invitation"""
    email: EmailStr
    role_id: str
    message: Optional[str] = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class UserInvitationResponse(BaseModel):
    """Response schema for user invitation data"""
    invitation_id: str
    organization_id: str
    email: str
    role_id: Optional[str]
    invited_by: str
    token: str
    status: InvitationStatus
    expires_at: datetime
    accepted_at: Optional[datetime]
    accepted_user_id: Optional[str]
    message: Optional[str]
    created_at: datetime
    role_name: Optional[str] = None
    
    @classmethod
    def from_orm(cls, invitation):
        """Create response from ORM model"""
        return cls(
            invitation_id=invitation.invitation_id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role_id=invitation.role_id,
            invited_by=invitation.invited_by,
            token=invitation.token,
            status=invitation.status,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            accepted_user_id=invitation.accepted_user_id,
            message=invitation.message,
            created_at=invitation.created_at,
            role_name=invitation.role.name if invitation.role else None
        )
    
    class Config:
        from_attributes = True


class InvitationAcceptRequest(BaseModel):
    """Request schema for accepting invitation"""
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Password Management Schemas
class PasswordChangeRequest(BaseModel):
    """Request schema for password change"""
    old_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Organization Schemas
class OrganizationCreateRequest(BaseModel):
    """Request schema for creating organization"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None
    subscription_tier: str = Field(default="basic")
    max_users: int = Field(default=10, ge=1)
    max_documents: int = Field(default=1000, ge=1)
    max_storage_gb: int = Field(default=10, ge=1)
    billing_email: Optional[EmailStr] = None
    billing_address: Optional[str] = None
    tax_id: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Response schema for organization data"""
    organization_id: str
    name: str
    description: Optional[str]
    domain: Optional[str]
    subscription_tier: str
    subscription_status: str
    max_users: int
    max_documents: int
    max_storage_gb: int
    settings: Dict[str, Any]
    features: List[str]
    billing_email: Optional[str]
    billing_address: Optional[str]
    tax_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    @classmethod
    def from_orm(cls, org):
        """Create response from ORM model"""
        return cls(
            organization_id=org.organization_id,
            name=org.name,
            description=org.description,
            domain=org.domain,
            subscription_tier=org.subscription_tier,
            subscription_status=org.subscription_status,
            max_users=org.max_users,
            max_documents=org.max_documents,
            max_storage_gb=org.max_storage_gb,
            settings=org.settings or {},
            features=org.features or [],
            billing_email=org.billing_email,
            billing_address=org.billing_address,
            tax_id=org.tax_id,
            status=org.status,
            created_at=org.created_at,
            updated_at=org.updated_at
        )
    
    class Config:
        from_attributes = True


class OrganizationUpdateRequest(BaseModel):
    """Request schema for updating organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None
    subscription_tier: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_documents: Optional[int] = Field(None, ge=1)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    settings: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    billing_email: Optional[EmailStr] = None
    billing_address: Optional[str] = None
    tax_id: Optional[str] = None


# Bulk Operations
class BulkUserActionRequest(BaseModel):
    """Request schema for bulk user actions"""
    action: str = Field(..., regex="^(activate|deactivate|delete)$")
    user_ids: List[str] = Field(..., min_items=1, max_items=100)
    reason: Optional[str] = None


class BulkUserActionResult(BaseModel):
    """Result schema for bulk user actions"""
    user_id: str
    success: bool
    message: str


class BulkUserActionResponse(BaseModel):
    """Response schema for bulk user actions"""
    results: List[BulkUserActionResult]
    total_successful: int
    total_failed: int


# Search and Filter Schemas
class UserSearchRequest(BaseModel):
    """Request schema for user search"""
    query: str = Field(..., min_length=2, max_length=100)
    organization_id: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class UserSuggestion(BaseModel):
    """Schema for user search suggestions"""
    user_id: str
    email: str
    full_name: str
    display_text: str


# Preferences Schemas
class UserPreferencesRequest(BaseModel):
    """Request schema for user preferences"""
    theme: Optional[str] = Field(None, regex="^(light|dark|system)$")
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    email_notifications: Optional[Dict[str, bool]] = None
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=1440)


class UserPreferencesResponse(BaseModel):
    """Response schema for user preferences"""
    theme: str
    language: str
    timezone: str
    email_notifications: Dict[str, bool]
    two_factor_enabled: bool
    session_timeout_minutes: int
    api_key_enabled: Optional[bool] = None
    dashboard_layout: Optional[Dict[str, Any]] = None
    default_view: Optional[str] = None


# Security Schemas
class SecurityEventRequest(BaseModel):
    """Request schema for security events"""
    event_type: str = Field(..., regex="^(login_failed|password_changed|account_locked|mfa_enabled|mfa_disabled)$")
    details: Optional[Dict[str, Any]] = None


class SecuritySettingsResponse(BaseModel):
    """Response schema for security settings"""
    two_factor_enabled: bool
    password_last_changed: Optional[str]
    password_change_required: bool
    login_attempts: List[Dict[str, Any]]
    security_events: List[Dict[str, Any]]
    last_login_ip: Optional[str]
    last_login_at: Optional[str]


# Audit Log Schemas
class AuditLogRequest(BaseModel):
    """Request schema for audit log queries"""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)


class AuditLogResponse(BaseModel):
    """Response schema for audit log entries"""
    audit_id: str
    actor_user_id: Optional[str]
    actor_ip: Optional[str]
    actor_user_agent: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    changed_fields: Optional[List[str]]
    organization_id: Optional[str]
    session_id: Optional[str]
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    correlation_id: Optional[str]


# API Response Wrapper
class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool