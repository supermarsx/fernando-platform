"""
Database Models for Server Architecture

This module contains SQLAlchemy models for the dual-server architecture,
including server configuration, client-server relationships, licensing, and communication.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Integer, Numeric, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class ServerType(str, enum.Enum):
    """Server type enumeration"""
    CLIENT = "client"
    SUPPLIER = "supplier"


class ServerStatus(str, enum.Enum):
    """Server status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class LicenseStatus(str, enum.Enum):
    """License status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class LicenseType(str, enum.Enum):
    """License type enumeration"""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingStatus(str, enum.Enum):
    """Billing status enumeration"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class CommunicationStatus(str, enum.Enum):
    """Communication status enumeration"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"


class SyncStatus(str, enum.Enum):
    """Synchronization status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"


class ServerArchitectureConfig(Base):
    """Server architecture configuration model"""
    __tablename__ = "server_architecture_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, unique=True, nullable=False, index=True)
    server_type = Column(SQLEnum(ServerType), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.INACTIVE)
    version = Column(String, default="1.0.0")
    
    # Network Configuration
    host = Column(String, default="0.0.0.0")
    port = Column(Integer, default=8000)
    ssl_enabled = Column(Boolean, default=False)
    api_base_url = Column(String)
    
    # Feature Configuration
    enabled_features = Column(JSON, default=list)
    disabled_features = Column(JSON, default=list)
    
    # Security Configuration
    api_key = Column(String)
    authentication_required = Column(Boolean, default=True)
    encryption_enabled = Column(Boolean, default=True)
    allowed_origins = Column(JSON, default=list)
    
    # Resource Limits
    max_concurrent_connections = Column(Integer, default=100)
    max_requests_per_minute = Column(Integer, default=1000)
    max_data_storage_gb = Column(Integer, default=10)
    
    # Monitoring
    health_check_url = Column(String, default="/health")
    metrics_enabled = Column(Boolean, default=True)
    logging_level = Column(String, default="INFO")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientServerRegistration(Base):
    """Client server registration model"""
    __tablename__ = "client_server_registrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, unique=True, nullable=False, index=True)
    server_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    supplier_server_url = Column(String, nullable=False)
    registration_token = Column(String, unique=True, nullable=False)
    
    # Status and metadata
    status = Column(String, default="active")
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    deactivated_at = Column(DateTime)
    deactivation_reason = Column(String)
    
    # Relationships
    client = relationship("Client", back_populates="server_registration")


class Client(Base):
    """Client model for customer management"""
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    contact_person = Column(String)
    phone = Column(String)
    address = Column(Text)
    
    # Status and configuration
    status = Column(String, default="pending")
    plan_type = Column(String, default="basic")
    onboarding_completed = Column(Boolean, default=False)
    
    # Relationships
    server_registration_id = Column(String, ForeignKey("client_server_registrations.id"))
    server_registration = relationship("ClientServerRegistration", back_populates="client")
    
    subscriptions = relationship("Subscription", back_populates="client")
    usage_records = relationship("UsageRecord", back_populates="client")
    customer_onboarding = relationship("CustomerOnboarding", uselist=False, back_populates="customer")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerOnboarding(Base):
    """Customer onboarding progress model"""
    __tablename__ = "customer_onboarding"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("clients.id"), unique=True, nullable=False)
    status = Column(String, default="initiated")
    steps_completed = Column(JSON, default=list)
    documents_provided = Column(JSON, default=list)
    api_keys_generated = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    customer = relationship("Client", back_populates="customer_onboarding")


class Subscription(Base):
    """Subscription model for billing"""
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    
    # Plan information
    plan_name = Column(String, nullable=False)
    billing_cycle = Column(String, default="monthly")  # monthly, yearly
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD")
    
    # Status
    status = Column(String, default="trial")
    last_payment_date = Column(DateTime)
    
    # Dates
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    next_billing_date = Column(DateTime)
    
    # Suspension
    suspension_reason = Column(String)
    suspended_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="subscriptions")


class UsageRecord(Base):
    """Usage tracking model"""
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    
    # Usage information
    usage_type = Column(String, nullable=False)  # document_processing, api_calls, storage, etc.
    amount = Column(Numeric(10, 3), nullable=False)
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="usage_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_customer_timestamp', 'customer_id', 'timestamp'),
    )


class BillingIntegration(Base):
    """Billing integration configuration model"""
    __tablename__ = "billing_integrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_type = Column(String, nullable=False)  # stripe, paypal, etc.
    config = Column(JSON, default=dict)
    webhook_url = Column(String)
    webhook_secret = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupplierServer(Base):
    """Supplier server model"""
    __tablename__ = "supplier_servers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    contact_email = Column(String)
    api_endpoint = Column(String)
    status = Column(String, default="active")
    
    # Metrics
    total_client_servers = Column(Integer, default=0)
    total_licenses = Column(Integer, default=0)
    total_revenue = Column(Numeric(15, 2), default=0)
    
    # Timestamps
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime)
    
    # Relationships
    licenses = relationship("License", back_populates="supplier_server")
    revenue_shares = relationship("RevenueShare", back_populates="supplier_server")


class License(Base):
    """License model for client server licensing"""
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_server_id = Column(String, ForeignKey("client_server_registrations.server_id"), nullable=False)
    supplier_server_id = Column(String, ForeignKey("supplier_servers.server_id"), nullable=False)
    
    # License details
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    status = Column(SQLEnum(LicenseStatus), default=LicenseStatus.TRIAL)
    
    # Billing
    billing_cycle = Column(String, default="monthly")
    amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), default=0.20)  # e.g., 0.20 = 20%
    
    # Features and limits
    features = Column(JSON, default=list)
    limits = Column(JSON, default=dict)
    
    # Dates
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    activation_date = Column(DateTime)
    
    # Suspension
    suspension_reason = Column(String)
    suspended_at = Column(DateTime)
    
    # Payment reference
    payment_reference = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier_server = relationship("SupplierServer", back_populates="licenses")
    client_server_registration = relationship("ClientServerRegistration", foreign_keys=[client_server_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_license_client_server', 'client_server_id'),
        Index('idx_license_supplier_server', 'supplier_server_id'),
    )


class LicenseTier(Base):
    """License tier configuration model"""
    __tablename__ = "license_tiers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    
    # Pricing
    monthly_price = Column(Numeric(10, 2), nullable=False)
    yearly_price = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    
    # Features and limits
    features = Column(JSON, default=list)
    limits = Column(JSON, default=dict)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientServerMetrics(Base):
    """Client server metrics model"""
    __tablename__ = "client_server_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, ForeignKey("client_server_registrations.server_id"), nullable=False)
    
    # Metrics data
    total_customers = Column(Integer, default=0)
    active_subscriptions = Column(Integer, default=0)
    total_revenue = Column(Numeric(15, 2), default=0)
    documents_processed = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    storage_used_gb = Column(Numeric(10, 3), default=0)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_server_period', 'server_id', 'period_start', 'period_end'),
    )


class RevenueShare(Base):
    """Revenue sharing model"""
    __tablename__ = "revenue_shares"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_server_id = Column(String, ForeignKey("supplier_servers.server_id"), nullable=False)
    
    # Revenue data
    gross_revenue = Column(Numeric(15, 2), nullable=False)
    commission_amount = Column(Numeric(15, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String, default="pending")  # pending, calculated, paid, disputed
    paid_at = Column(DateTime)
    payment_reference = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier_server = relationship("SupplierServer", back_populates="revenue_shares")
    
    # Indexes
    __table_args__ = (
        Index('idx_revenue_supplier_period', 'supplier_server_id', 'period_start', 'period_end'),
    )


class CommissionTracking(Base):
    """Commission tracking model"""
    __tablename__ = "commission_tracking"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = Column(String, ForeignKey("licenses.id"), nullable=False)
    
    # Commission data
    revenue_amount = Column(Numeric(15, 2), nullable=False)
    commission_amount = Column(Numeric(15, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    
    # Status
    status = Column(String, default="calculated")  # calculated, paid, disputed
    paid_at = Column(DateTime)
    payment_reference = Column(String)
    dispute_reason = Column(Text)
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    license = relationship("License")


class SupplierAnalytics(Base):
    """Supplier analytics model"""
    __tablename__ = "supplier_analytics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_server_id = Column(String, ForeignKey("supplier_servers.server_id"), nullable=False)
    
    # Analytics data
    metric_name = Column(String, nullable=False)
    metric_value = Column(Numeric(15, 2), nullable=False)
    metric_data = Column(JSON, default=dict)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_supplier_metric', 'supplier_server_id', 'metric_name', 'period_start'),
    )


class ServerCommunicationLog(Base):
    """Server communication log model"""
    __tablename__ = "server_communication_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, nullable=False, index=True)
    
    # Server identifiers
    source_server_id = Column(String, nullable=False)
    target_server_id = Column(String, nullable=False)
    
    # Message details
    message_type = Column(String, nullable=False)
    status = Column(SQLEnum(CommunicationStatus), default=CommunicationStatus.PENDING)
    payload = Column(JSON, default=dict)
    response = Column(JSON)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_comm_logs_source_target', 'source_server_id', 'target_server_id'),
        Index('idx_comm_logs_timestamp', 'timestamp'),
        Index('idx_comm_logs_status', 'status'),
    )


class SyncJob(Base):
    """Data synchronization job model"""
    __tablename__ = "sync_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Job details
    source_server_id = Column(String, nullable=False)
    target_server_id = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)  # periodic, manual, triggered
    data = Column(JSON, default=dict)
    
    # Status
    status = Column(SQLEnum(SyncStatus), default=SyncStatus.SCHEDULED)
    result = Column(JSON)
    error_message = Column(Text)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_sync_source_target', 'source_server_id', 'target_server_id'),
        Index('idx_sync_status', 'status'),
        Index('idx_sync_created', 'created_at'),
    )


class Tenant(Base):
    """Multi-tenant model"""
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, unique=True)
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.PENDING)
    
    # Configuration
    settings = Column(JSON, default=dict)
    features_enabled = Column(JSON, default=list)
    features_disabled = Column(JSON, default=list)
    
    # Customization
    custom_branding = Column(JSON, default=dict)
    integrations = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime)


class TenantConfig(Base):
    """Tenant configuration model"""
    __tablename__ = "tenant_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, unique=True, nullable=False, index=True)
    
    # Configuration
    name = Column(String, nullable=False)
    domain = Column(String)
    settings = Column(JSON, default=dict)
    features_enabled = Column(JSON, default=list)
    features_disabled = Column(JSON, default=list)
    custom_branding = Column(JSON, default=dict)
    integrations = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResourceQuota(Base):
    """Resource quota model for tenants"""
    __tablename__ = "resource_quotas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenant_configs.tenant_id"), nullable=False)
    
    # Resource information
    resource_type = Column(String, nullable=False)  # storage, memory, cpu, etc.
    limit = Column(Numeric(15, 3), nullable=False)
    unit = Column(String, default="units")
    used = Column(Numeric(15, 3), default=0)
    reserved = Column(Numeric(15, 3), default=0)
    
    # Reset period
    reset_period = Column(String, default="monthly")  # daily, monthly, yearly
    
    # Timestamps
    last_reset = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_quota_tenant_resource', 'tenant_id', 'resource_type'),
    )


class TenantFeature(Base):
    """Tenant feature configuration model"""
    __tablename__ = "tenant_features"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenant_configs.tenant_id"), nullable=False, index=True)
    
    # Feature information
    feature_name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    configuration = Column(JSON, default=dict)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_feature_unique', 'tenant_id', 'feature_name', unique=True),
    )


class TenantUsage(Base):
    """Tenant usage tracking model"""
    __tablename__ = "tenant_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenant_configs.tenant_id"), nullable=False)
    
    # Usage information
    usage_type = Column(String, nullable=False)
    amount = Column(Numeric(15, 3), nullable=False)
    metadata = Column(JSON, default=dict)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_tenant_period', 'tenant_id', 'period_start', 'period_end'),
    )