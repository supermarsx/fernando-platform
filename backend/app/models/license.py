from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime
import enum


class LicenseTier(str, enum.Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseTierModel(Base):
    __tablename__ = "license_tiers"

    tier_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)
    
    # Feature limits
    max_documents_per_month = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=False)
    max_storage_gb = Column(Integer, nullable=False)
    
    # Feature flags
    features = Column(JSON, nullable=False)  # {"batch_processing": true, "api_access": false, ...}
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    licenses = relationship("License", back_populates="tier")


class License(Base):
    __tablename__ = "licenses"

    license_id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, nullable=False, index=True)
    
    # Tier reference
    tier_id = Column(Integer, ForeignKey("license_tiers.tier_id"), nullable=False)
    tier = relationship("LicenseTierModel", back_populates="licenses")
    
    # Organization info
    organization_name = Column(String, nullable=False)
    organization_email = Column(String, nullable=False)
    
    # License status
    status = Column(SQLEnum("active", "expired", "suspended", "revoked", name="license_status"), default="active")
    
    # Validity period
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_validated_at = Column(DateTime)
    
    # Offline validation
    hardware_fingerprint = Column(String)  # SHA256 hash of hardware ID
    max_activations = Column(Integer, default=1)
    current_activations = Column(Integer, default=0)
    
    # Usage tracking
    documents_processed_this_month = Column(Integer, default=0)
    last_reset_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    meta_data = Column(JSON)  # Custom fields, notes, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignments = relationship("LicenseAssignment", back_populates="license", cascade="all, delete-orphan")
    usage_logs = relationship("LicenseUsage", back_populates="license", cascade="all, delete-orphan")
    audit_logs = relationship("LicenseAuditLog", back_populates="license", cascade="all, delete-orphan")


class LicenseAssignment(Base):
    __tablename__ = "license_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True)
    
    # References
    license_id = Column(Integer, ForeignKey("licenses.license_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    # Assignment details
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.user_id"))
    
    # Status
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime)
    deactivated_by = Column(Integer, ForeignKey("users.user_id"))
    
    # Relationships
    license = relationship("License", back_populates="assignments")


class LicenseUsage(Base):
    __tablename__ = "license_usage"

    usage_id = Column(Integer, primary_key=True, index=True)
    
    # References
    license_id = Column(Integer, ForeignKey("licenses.license_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    
    # Usage details
    feature_used = Column(String, nullable=False)  # "document_processing", "batch_upload", etc.
    usage_count = Column(Integer, default=1)
    usage_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    meta_data = Column(JSON)  # Additional context
    
    # Relationships
    license = relationship("License", back_populates="usage_logs")


class LicenseAuditLog(Base):
    __tablename__ = "license_audit_logs"

    audit_id = Column(Integer, primary_key=True, index=True)
    
    # References
    license_id = Column(Integer, ForeignKey("licenses.license_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    
    # Audit details
    action = Column(String, nullable=False)  # "created", "activated", "renewed", "suspended", "revoked"
    description = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    meta_data = Column(JSON)
    
    # Relationships
    license = relationship("License", back_populates="audit_logs")


# Telemetry relationships for License
License.telemetry_events = relationship("TelemetryEvent", back_populates="license", cascade="all, delete-orphan")
License.business_metrics = relationship("BusinessMetric", back_populates="license", cascade="all, delete-orphan")
License.alert_rules = relationship("AlertRule", back_populates="license", cascade="all, delete-orphan")
License.traces = relationship("Trace", back_populates="license", cascade="all, delete-orphan")
