import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class License(Base):
    __tablename__ = "licenses"
    
    license_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    
    # License details
    tier = Column(String, nullable=False)  # free, pro, enterprise
    status = Column(String, default="active")  # active, suspended, expired, revoked
    hardware_fingerprint = Column(String, nullable=True)
    
    # Limits and usage
    docs_processed_this_month = Column(Integer, default=0)
    total_docs_processed = Column(Integer, default=0)
    features_enabled = Column(JSON, default=[])
    
    # Dates
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_validated_at = Column(DateTime, nullable=True)
    last_renewed_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LicenseValidation(Base):
    __tablename__ = "license_validations"
    
    validation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = Column(String, nullable=False, index=True)
    hardware_fingerprint = Column(String, nullable=False)
    
    # Validation result
    is_valid = Column(Boolean, nullable=False)
    validation_message = Column(String, nullable=True)
    
    # Client info
    client_version = Column(String, nullable=True)
    client_ip = Column(String, nullable=True)
    
    # Timestamp
    validated_at = Column(DateTime, default=datetime.utcnow, index=True)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = Column(String, nullable=False, index=True)
    
    # Usage details
    action = Column(String, nullable=False)  # document_processed, api_call, etc.
    resource_type = Column(String, nullable=True)  # ocr, llm, toconline
    quantity = Column(Integer, default=1)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamp
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)
