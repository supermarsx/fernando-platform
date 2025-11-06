import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, Text, Float
from sqlalchemy.orm import relationship
from app.db.session import Base


class Tenant(Base):
    """Multi-tenant support with data isolation"""
    __tablename__ = "tenants"
    
    tenant_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, suspended, deleted
    subscription_plan = Column(String, default="basic")  # basic, professional, enterprise
    max_users = Column(Integer, default=10)
    max_jobs_per_month = Column(Integer, default=1000)
    max_storage_gb = Column(Integer, default=5)
    features = Column(JSON, default={})  # Feature flags per tenant
    settings = Column(JSON, default={})  # Custom tenant settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    users = relationship("UserEnterprise", back_populates="tenant")
    groups = relationship("Group", back_populates="tenant")
    quota_usage = relationship("QuotaUsage", back_populates="tenant", uselist=False)


class UserEnterprise(Base):
    """Enhanced user model with group support"""
    __tablename__ = "users_enterprise"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    status = Column(String, default="active")  # active, disabled, pending
    is_tenant_admin = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    force_password_change = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)
    last_modified_by = Column(String, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    group_memberships = relationship("GroupMember", back_populates="user")
    permissions = relationship("UserPermission", back_populates="user")


class Group(Base):
    """User groups with hierarchical permissions"""
    __tablename__ = "groups"
    
    group_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)  # Built-in groups like "Administrators"
    parent_group_id = Column(String, ForeignKey("groups.group_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="groups")
    parent = relationship("Group", remote_side=[group_id], backref="children")
    members = relationship("GroupMember", back_populates="group")
    permissions = relationship("GroupPermission", back_populates="group")


class GroupMember(Base):
    """Many-to-many relationship between users and groups"""
    __tablename__ = "group_members"
    
    member_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users_enterprise.user_id"), nullable=False)
    group_id = Column(String, ForeignKey("groups.group_id"), nullable=False)
    added_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserEnterprise", back_populates="group_memberships")
    group = relationship("Group", back_populates="members")


class Permission(Base):
    """System-wide permissions"""
    __tablename__ = "permissions"
    
    permission_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    resource = Column(String, nullable=False)  # jobs, documents, users, etc.
    action = Column(String, nullable=False)    # create, read, update, delete, approve
    scope = Column(String, default="own")      # own, tenant, all
    is_system = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    group_permissions = relationship("GroupPermission", back_populates="permission")
    user_permissions = relationship("UserPermission", back_populates="permission")


class GroupPermission(Base):
    """Permissions assigned to groups"""
    __tablename__ = "group_permissions"
    
    permission_id = Column(String, ForeignKey("permissions.permission_id"), primary_key=True)
    group_id = Column(String, ForeignKey("groups.group_id"), primary_key=True)
    granted_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    permission = relationship("Permission", back_populates="group_permissions")
    group = relationship("Group", back_populates="permissions")


class UserPermission(Base):
    """Direct permissions assigned to users (overrides group permissions)"""
    __tablename__ = "user_permissions"
    
    permission_id = Column(String, ForeignKey("permissions.permission_id"), primary_key=True)
    user_id = Column(String, ForeignKey("users_enterprise.user_id"), primary_key=True)
    granted_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    permission = relationship("Permission", back_populates="user_permissions")
    user = relationship("UserEnterprise", back_populates="permissions")


class JobQueue(Base):
    """Enhanced job queue management"""
    __tablename__ = "job_queues"
    
    queue_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    max_concurrent_jobs = Column(Integer, default=5)
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    timeout_seconds = Column(Integer, default=3600)
    priority_min = Column(Integer, default=-10)
    priority_max = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuotaUsage(Base):
    """Track quota usage for rate limiting"""
    __tablename__ = "quota_usage"
    
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), primary_key=True)
    current_month = Column(Integer, default=datetime.utcnow().month)
    current_year = Column(Integer, default=datetime.utcnow().year)
    jobs_processed = Column(Integer, default=0)
    storage_used_mb = Column(Float, default=0.0)
    api_calls_made = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="quota_usage")


class ExportJob(Base):
    """Export/import job tracking"""
    __tablename__ = "export_jobs"
    
    export_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=True)  # For single job exports
    export_type = Column(String, nullable=False)  # csv, excel, json, pdf
    export_format = Column(String, nullable=False)  # detailed, summary, custom
    filters = Column(JSON, default={})
    status = Column(String, default="queued")  # queued, processing, completed, failed
    file_url = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    records_count = Column(Integer, nullable=True)
    created_by = Column(String, ForeignKey("users_enterprise.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class AuditTrail(Base):
    """Enhanced audit trail for compliance"""
    __tablename__ = "audit_trail"
    
    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users_enterprise.user_id"), nullable=True)
    action = Column(String, nullable=False)  # create, update, delete, login, logout, etc.
    resource_type = Column(String, nullable=False)  # user, job, document, etc.
    resource_id = Column(String, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String, nullable=True)
    risk_level = Column(String, default="low")  # low, medium, high, critical
    compliance_tags = Column(JSON, default=[])  # GDPR, SOX, HIPAA, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional context
    api_endpoint = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)


class ScheduledTask(Base):
    """Advanced job scheduling and automation"""
    __tablename__ = "scheduled_tasks"
    
    task_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String, nullable=False)  # export, cleanup, report, webhook
    schedule_cron = Column(String, nullable=True)  # Cron expression
    schedule_interval = Column(Integer, nullable=True)  # Interval in seconds
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    config = Column(JSON, default={})
    created_by = Column(String, ForeignKey("users_enterprise.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Task execution history
    runs = relationship("TaskRun", back_populates="task")


class TaskRun(Base):
    """History of scheduled task executions"""
    __tablename__ = "task_runs"
    
    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("scheduled_tasks.task_id"), nullable=False)
    status = Column(String, default="running")  # running, completed, failed, canceled
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("ScheduledTask", back_populates="runs")


class RateLimit(Base):
    """API rate limiting configuration"""
    __tablename__ = "rate_limits"
    
    limit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    endpoint_pattern = Column(String, nullable=False)
    requests_per_hour = Column(Integer, default=1000)
    requests_per_day = Column(Integer, default=10000)
    burst_limit = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceReport(Base):
    """Compliance reporting and audit summaries"""
    __tablename__ = "compliance_reports"
    
    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    report_type = Column(String, nullable=False)  # GDPR, SOX, ISO27001, etc.
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String, default="generating")  # generating, completed, failed
    file_url = Column(String, nullable=True)
    summary = Column(JSON, nullable=True)
    generated_by = Column(String, ForeignKey("users_enterprise.user_id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
