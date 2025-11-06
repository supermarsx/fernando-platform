import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"
    
    document_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)  # Multi-tenant support
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    original_filename = Column(String, nullable=False)
    storage_url = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    pages = Column(Integer, default=1)
    checksum_sha256 = Column(String, unique=True, index=True)
    file_size_bytes = Column(Integer, default=0)
    uploaded_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    is_confidential = Column(Boolean, default=False)
    retention_period_days = Column(Integer, nullable=365)  # Default 1 year
    tags = Column(JSON, default=[])  # Custom tags for organization
    doc_metadata = Column(JSON, default={})  # Document metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Enhanced document processing relationships
    format_info = relationship("DocumentFormatInfo", back_populates="document", uselist=False, cascade="all, delete-orphan")
    validations = relationship("DocumentValidation", back_populates="document", cascade="all, delete-orphan")
    processing_pipelines = relationship("DocumentProcessingPipeline", back_populates="document", cascade="all, delete-orphan")
    previews = relationship("DocumentPreview", back_populates="document", cascade="all, delete-orphan")
