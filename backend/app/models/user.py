import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Boolean, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    """Enhanced user model with comprehensive user management capabilities"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=True)  # Can be null for existing single-tenant installations
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    status = Column(String, default="active")  # active, inactive, suspended, deleted
    roles = Column(JSON, default=["uploader"])  # uploader, reviewer, auditor, admin (legacy support)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enhanced user management fields
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=True)
    
    # Security and verification
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    phone = Column(String, nullable=True)
    
    # Account lifecycle
    onboarding_completed = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, default=datetime.utcnow)
    
    # Multi-factor authentication
    mfa_enabled = Column(Boolean, default=False)
    
    # API access
    api_key = Column(String, unique=True, nullable=True, index=True)
    api_key_expires_at = Column(DateTime, nullable=True)
    api_key_last_used = Column(DateTime, nullable=True)
    
    # User profile
    department = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Legacy support - keep existing fields for backward compatibility
    def get_legacy_role(self) -> str:
        """Get primary role for backward compatibility"""
        if self.roles and len(self.roles) > 0:
            role_priority = {"admin": 4, "auditor": 3, "reviewer": 2, "uploader": 1}
            sorted_roles = sorted(self.roles, key=lambda r: role_priority.get(r, 0), reverse=True)
            return sorted_roles[0] if sorted_roles else "uploader"
        return "uploader"


# Enhanced relationships for User
# Add new user management relationships
try:
    from app.models.user_management import (
        Organization, UserRoleAssignment, UserSession, UserActivity,
        UserPreferences, AccountSecurity, AuditLog
    )
    
    # New relationships
    User.organization = relationship("Organization", back_populates="users")
    User.user_role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    User.user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    User.user_activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    User.user_preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    User.account_security = relationship("AccountSecurity", back_populates="user", uselist=False, cascade="all, delete-orphan")
    User.audit_logs = relationship("AuditLog", back_populates="user", foreign_keys=[AuditLog.actor_user_id])
    
except ImportError:
    # Models might not be available yet during initial import
    pass


# Telemetry relationships for User
# These are added here to avoid circular import issues
try:
    from app.models.telemetry import TelemetryEvent, BusinessMetric, AlertRule, Alert, Trace
    
    User.telemetry_events = relationship("TelemetryEvent", back_populates="user", cascade="all, delete-orphan")
    User.business_metrics = relationship("BusinessMetric", back_populates="user", cascade="all, delete-orphan")
    User.created_alert_rules = relationship("AlertRule", foreign_keys=[AlertRule.created_by], back_populates="created_by_user")
    User.updated_alert_rules = relationship("AlertRule", foreign_keys=[AlertRule.updated_by], back_populates="updated_by_user")
    User.assigned_alerts = relationship("Alert", foreign_keys=[Alert.assigned_to], back_populates="assigned_user")
    User.traces = relationship("Trace", back_populates="user", cascade="all, delete-orphan")
except ImportError:
    # Models might not be available yet during initial import
    pass


# User helper methods
def get_user_display_name(user: User) -> str:
    """Get display name for user"""
    if user.full_name:
        return user.full_name
    return user.email.split('@')[0] if '@' in user.email else user.email


def is_user_admin(user: User, organization_id: str = None) -> bool:
    """Check if user has admin privileges"""
    # Check legacy roles first (backward compatibility)
    if user.roles and "admin" in user.roles:
        return True
    
    # Check new role assignments
    try:
        from app.core.rbac import permission_checker
        from app.db.session import Session
        from sqlalchemy.orm import sessionmaker
        
        # This would need to be called with a proper database session
        # For now, return based on legacy roles
        return "admin" in (user.roles or [])
    except:
        return False


def is_user_active(user: User) -> bool:
    """Check if user is active"""
    return user.status == "active"


def has_permission(user: User, permission: str, resource: str = None, organization_id: str = None) -> bool:
    """Check if user has specific permission"""
    # Check legacy roles first (backward compatibility)
    role_permissions = {
        "admin": ["*"],  # Admin has all permissions
        "auditor": ["documents.read", "documents.review", "reports.read"],
        "reviewer": ["documents.read", "documents.review"],
        "uploader": ["documents.upload", "documents.read"]
    }
    
    # If user has admin role, grant all permissions
    if user.roles and "admin" in user.roles:
        return True
    
    # Check specific permissions based on roles
    user_permissions = set()
    for role in user.roles or []:
        if role in role_permissions:
            user_permissions.update(role_permissions[role])
    
    # Check for wildcard permissions
    for perm in user_permissions:
        if perm == "*":
            return True
        if resource and perm == f"{resource}.*":
            return True
        if resource and permission and perm == f"{resource}.{permission}":
            return True
    
    # Fallback to legacy role checking
    role_hierarchies = {
        "admin": 4,
        "auditor": 3,
        "reviewer": 2,
        "uploader": 1
    }
    
    def has_role_permission(role: str, req_permission: str) -> bool:
        role_perms = role_permissions.get(role, [])
        return req_permission in role_perms or "*" in role_perms
    
    user_max_role_level = max(
        [role_hierarchies.get(role, 0) for role in user.roles or []],
        default=0
    )
    
    # Simple permission checking based on role hierarchy
    for role in user.roles or []:
        if has_role_permission(role, permission):
            return True
    
    return False
