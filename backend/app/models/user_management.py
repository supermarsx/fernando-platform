import uuid
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, DateTime, JSON, Boolean, Text, Integer, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum
from typing import Dict, Any


class UserRole(Base):
    """Extended role system with hierarchical permissions"""
    __tablename__ = "user_roles"
    
    role_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    level = Column(Integer, default=0)  # Hierarchical level (0=highest)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRoleAssignment", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserRole(name='{self.name}', level={self.level})>"


class Permission(Base):
    """System permissions"""
    __tablename__ = "permissions"
    
    permission_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    resource = Column(String, nullable=False)  # e.g., 'users', 'documents', 'billing'
    action = Column(String, nullable=False)    # e.g., 'create', 'read', 'update', 'delete'
    conditions = Column(JSON)  # Additional conditions/restrictions
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Permission(name='{self.name}', resource='{self.resource}', action='{self.action}')>"


class RolePermission(Base):
    """Many-to-many relationship between roles and permissions"""
    __tablename__ = "role_permissions"
    
    role_id = Column(String, ForeignKey("user_roles.role_id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.permission_id"), primary_key=True)
    granted_by = Column(String, ForeignKey("users.user_id"))  # Who granted this permission
    granted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    role = relationship("UserRole", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


class Organization(Base):
    """Multi-tenant organization/company management"""
    __tablename__ = "organizations"
    
    organization_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    domain = Column(String, unique=True, nullable=True)  # For email domain verification
    subscription_tier = Column(String, default="basic")  # basic, professional, enterprise
    subscription_status = Column(String, default="active")  # active, suspended, cancelled
    
    # Limits and quotas
    max_users = Column(Integer, default=10)
    max_documents = Column(Integer, default=1000)
    max_storage_gb = Column(Integer, default=10)
    
    # Organization settings
    settings = Column(JSON, default={})
    features = Column(JSON, default=[])  # Enabled features
    
    # Billing information
    billing_email = Column(String)
    billing_address = Column(Text)
    tax_id = Column(String)
    
    # Status and tracking
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    user_sessions = relationship("UserSession", back_populates="organization")
    user_invitations = relationship("UserInvitation", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(name='{self.name}', domain='{self.domain}')>"


class UserRoleAssignment(Base):
    """User role assignments within organizations"""
    __tablename__ = "user_role_assignments"
    
    assignment_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    role_id = Column(String, ForeignKey("user_roles.role_id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=True)
    
    # Assignment details
    assigned_by = Column(String, ForeignKey("users.user_id"))  # Who assigned this role
    assigned_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("UserRole", back_populates="user_roles")
    organization = relationship("Organization")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org'),
        Index('ix_user_role_user_org', 'user_id', 'organization_id'),
    )


class UserSession(Base):
    """User session tracking and management"""
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=True)
    
    # Session data
    ip_address = Column(String)
    user_agent = Column(Text)
    device_info = Column(JSON)
    location = Column(JSON)  # {country, city, lat, lon}
    
    # Session lifecycle
    login_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    logout_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Security
    is_active = Column(Boolean, default=True)
    mfa_verified = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)  # Security risk assessment
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
    organization = relationship("Organization", back_populates="user_sessions")


class UserInvitation(Base):
    """User invitation and onboarding system"""
    __tablename__ = "user_invitations"
    
    invitation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=False)
    
    # Invitation details
    email = Column(String, nullable=False, index=True)
    role_id = Column(String, ForeignKey("user_roles.role_id"))
    invited_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    
    # Invitation lifecycle
    token = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="pending")  # pending, accepted, expired, cancelled
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    
    # Acceptance details
    accepted_at = Column(DateTime, nullable=True)
    accepted_user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    
    # Resend tracking
    resent_at = Column(DateTime, nullable=True)
    resent_by = Column(String, ForeignKey("users.user_id"), nullable=True)
    
    # Custom message
    message = Column(Text)
    
    # Relationships
    organization = relationship("Organization", back_populates="user_invitations")
    role = relationship("UserRole")
    invited_by_user = relationship("User", foreign_keys=[invited_by])
    accepted_user = relationship("User", foreign_keys=[accepted_user_id])
    
    def __repr__(self):
        return f"<UserInvitation(email='{self.email}', status='{self.status}')>"


class UserActivity(Base):
    """User activity tracking and audit trail"""
    __tablename__ = "user_activities"
    
    activity_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=True)
    
    # Activity details
    action = Column(String, nullable=False)  # login, upload_document, create_user, etc.
    resource_type = Column(String)  # document, user, organization, etc.
    resource_id = Column(String)  # ID of the resource
    details = Column(JSON)  # Additional details
    
    # Context
    ip_address = Column(String)
    user_agent = Column(Text)
    session_id = Column(String, ForeignKey("user_sessions.session_id"))
    
    # Metadata
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer)  # Operation duration
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_activities")
    organization = relationship("Organization")
    session = relationship("UserSession")


class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"
    
    preference_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)
    
    # Notification preferences
    email_notifications = Column(JSON, default={
        'login_alerts': True,
        'security_alerts': True,
        'system_updates': False,
        'marketing_emails': False
    })
    
    # UI preferences
    theme = Column(String, default="system")  # light, dark, system
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    date_format = Column(String, default="YYYY-MM-DD")
    
    # Security preferences
    two_factor_enabled = Column(Boolean, default=False)
    session_timeout_minutes = Column(Integer, default=30)
    password_last_changed = Column(DateTime, default=datetime.utcnow)
    
    # Dashboard preferences
    dashboard_layout = Column(JSON, default={})
    default_view = Column(String, default="dashboard")
    
    # API preferences
    api_key_enabled = Column(Boolean, default=False)
    api_key_last_used = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")


class AccountSecurity(Base):
    """Enhanced account security settings"""
    __tablename__ = "account_security"
    
    security_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, unique=True)
    
    # Password security
    password_failed_attempts = Column(Integer, default=0)
    password_last_failed_at = Column(DateTime, nullable=True)
    password_locked_until = Column(DateTime, nullable=True)
    password_change_required = Column(Boolean, default=False)
    
    # Two-factor authentication
    two_factor_secret = Column(String, nullable=True)  # Encrypted TOTP secret
    two_factor_backup_codes = Column(JSON, nullable=True)  # Backup codes
    two_factor_enabled_at = Column(DateTime, nullable=True)
    two_factor_last_used = Column(DateTime, nullable=True)
    
    # Login tracking
    login_attempts = Column(JSON, default=[])  # Recent login attempts
    last_login_ip = Column(String, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    
    # Security events
    security_events = Column(JSON, default=[])  # Recent security events
    
    # Relationships
    user = relationship("User", back_populates="account_security")


class AuditLog(Base):
    """Comprehensive audit logging for compliance"""
    __tablename__ = "audit_logs"
    
    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Actor information
    actor_user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    actor_ip = Column(String)
    actor_user_agent = Column(Text)
    
    # Action information
    action = Column(String, nullable=False)  # create, update, delete, login, etc.
    resource_type = Column(String, nullable=False)  # user, organization, document, etc.
    resource_id = Column(String, nullable=True)
    
    # Changes
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_fields = Column(JSON, nullable=True)
    
    # Context
    organization_id = Column(String, ForeignKey("organizations.organization_id"), nullable=True)
    session_id = Column(String, ForeignKey("user_sessions.session_id"), nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    correlation_id = Column(String, index=True)  # For tracing related events
    
    # Relationships
    user = relationship("User", foreign_keys=[actor_user_id])
    organization = relationship("Organization")


# Extend the existing User model with relationships
try:
    from app.models.user import User
    
    # Add new relationships to existing User model
    # Note: All column attributes already exist in User model
    # Only add relationships that don't exist
    User.organization = relationship("Organization", back_populates="users")
    User.user_role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    User.user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    User.user_activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    User.user_preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    User.account_security = relationship("AccountSecurity", back_populates="user", uselist=False, cascade="all, delete-orphan")
    User.audit_logs = relationship("AuditLog", back_populates="user", foreign_keys=[AuditLog.actor_user_id])
    
except ImportError:
    # User model might not be available yet during initial import
    pass


# Indexes for performance
Index('idx_user_activities_user_created', UserActivity.user_id, UserActivity.created_at)
Index('idx_user_activities_org_created', UserActivity.organization_id, UserActivity.created_at)
Index('idx_user_sessions_user_active', UserSession.user_id, UserSession.is_active)
Index('idx_user_sessions_expires', UserSession.expires_at)
Index('idx_audit_logs_timestamp', AuditLog.timestamp)
Index('idx_audit_logs_actor_resource', AuditLog.actor_user_id, AuditLog.resource_type, AuditLog.resource_id)
Index('idx_user_invitations_token', UserInvitation.token)
Index('idx_user_invitations_email_status', UserInvitation.email, UserInvitation.status)