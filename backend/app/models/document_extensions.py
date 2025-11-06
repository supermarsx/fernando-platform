"""
Document Processing Database Extensions

Extensions to the document model to support multi-format processing,
preview generation, processing metadata, and conversion history.
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.db.session import Base
import uuid
from datetime import datetime

class DocumentFormatInfo(Base):
    """Extended document format information and processing metadata"""
    __tablename__ = "document_format_info"
    
    format_info_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    
    # Format detection results
    detected_format = Column(String, nullable=False)  # pdf, tiff, png, jpeg, jpg
    format_confidence = Column(Float, default=0.0)
    detection_method = Column(String, default="combined")  # magic_bytes, mime_type, extension, combined
    
    # Format-specific metadata
    format_metadata = Column(JSON, default={})  # Detailed format information
    
    # Technical specifications
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    dimensions_width = Column(Integer, nullable=True)
    dimensions_height = Column(Integer, nullable=True)
    color_mode = Column(String, nullable=True)  # RGB, RGBA, L, P, etc.
    compression_type = Column(String, nullable=True)
    
    # Processing status
    format_validated = Column(Boolean, default=False)
    processing_ready = Column(Boolean, default=False)
    validation_passed = Column(Boolean, default=False)
    
    # Timestamps
    format_detected_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="format_info")
    preview_images = relationship("DocumentPreview", back_populates="format_info", cascade="all, delete-orphan")
    conversion_history = relationship("DocumentConversion", back_populates="source_format_info")


class DocumentPreview(Base):
    """Document preview images and thumbnails"""
    __tablename__ = "document_previews"
    
    preview_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    format_info_id = Column(String, ForeignKey("document_format_info.format_info_id"), nullable=False)
    
    # Preview specifications
    preview_type = Column(String, nullable=False)  # thumbnail, preview, page_preview
    size_category = Column(String, nullable=False)  # small, medium, large
    image_format = Column(String, default="JPEG")  # JPEG, PNG
    
    # File information
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generation_method = Column(String, default="pil")  # pil, convert, external
    quality_settings = Column(JSON, default={})  # DPI, quality settings used
    
    # Page-specific (for multi-page documents)
    page_number = Column(Integer, nullable=True)
    
    # Relationships
    format_info = relationship("DocumentFormatInfo", back_populates="preview_images")


class DocumentConversion(Base):
    """Document conversion history and results"""
    __tablename__ = "document_conversions"
    
    conversion_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    source_format_info_id = Column(String, ForeignKey("document_format_info.format_info_id"), nullable=False)
    
    # Conversion details
    source_format = Column(String, nullable=False)
    target_format = Column(String, nullable=False)
    conversion_method = Column(String, nullable=False)  # pdf_to_png, tiff_to_jpeg, etc.
    
    # Conversion settings
    conversion_options = Column(JSON, default={})  # DPI, quality, page_range, etc.
    
    # Results
    conversion_successful = Column(Boolean, default=False)
    output_files = Column(JSON, default=[])  # List of output file paths
    page_count_converted = Column(Integer, default=0)
    
    # Performance metrics
    conversion_time_seconds = Column(Float, default=0.0)
    quality_loss = Column(String, nullable=True)  # none, minimal, moderate, high
    
    # Error information
    error_message = Column(Text, nullable=True)
    warning_messages = Column(JSON, default=[])
    
    # Timestamps
    conversion_started_at = Column(DateTime, default=datetime.utcnow)
    conversion_completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    source_format_info = relationship("DocumentFormatInfo", back_populates="conversion_history")


class DocumentValidation(Base):
    """Document validation results and security scan information"""
    __tablename__ = "document_validations"
    
    validation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    
    # Overall validation status
    is_valid = Column(Boolean, default=False)
    is_safe = Column(Boolean, default=False)
    is_processable = Column(Boolean, default=False)
    validation_level = Column(String, default="basic")  # basic, standard, comprehensive
    
    # Security scan results
    security_status = Column(String, default="pending")  # passed, failed, warning, error
    threats_detected = Column(JSON, default=[])
    security_scan_method = Column(String, default="pattern_matching")
    
    # Content analysis
    content_analysis = Column(JSON, default={})
    file_entropy = Column(Float, nullable=True)
    content_type = Column(String, nullable=True)  # text_like, binary, mixed
    has_structured_content = Column(Boolean, default=False)
    
    # Validation checks
    checks_performed = Column(JSON, default=[])
    checks_passed = Column(JSON, default=[])
    validation_errors = Column(JSON, default=[])
    validation_warnings = Column(JSON, default=[])
    
    # Processing readiness
    readiness_score = Column(Float, default=0.0)
    blocking_issues = Column(JSON, default=[])
    processing_recommendations = Column(JSON, default=[])
    
    # Timestamps
    validation_started_at = Column(DateTime, default=datetime.utcnow)
    validation_completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    validation_metadata = Column(JSON, default={})


class DocumentProcessingPipeline(Base):
    """Document processing pipeline execution tracking"""
    __tablename__ = "document_processing_pipelines"
    
    pipeline_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    
    # Pipeline execution
    pipeline_version = Column(String, default="1.0")
    execution_mode = Column(String, default="standard")  # standard, fast, comprehensive
    pipeline_steps = Column(JSON, default=[])  # List of pipeline steps executed
    
    # Step results
    step_results = Column(JSON, default={})  # Results for each pipeline step
    step_errors = Column(JSON, default={})  # Errors for each pipeline step
    step_warnings = Column(JSON, default={})  # Warnings for each pipeline step
    
    # Performance metrics
    total_processing_time = Column(Float, default=0.0)
    pipeline_success = Column(Boolean, default=False)
    processing_metadata = Column(JSON, default={})
    
    # Options and configuration
    processing_options = Column(JSON, default={})
    tenant_restrictions = Column(JSON, default={})
    
    # Timestamps
    pipeline_started_at = Column(DateTime, default=datetime.utcnow)
    pipeline_completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    pipeline_runs = relationship("ProcessingStepRun", back_populates="pipeline", cascade="all, delete-orphan")


class ProcessingStepRun(Base):
    """Individual processing step execution tracking"""
    __tablename__ = "processing_step_runs"
    
    step_run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String, ForeignKey("document_processing_pipelines.pipeline_id"), nullable=False)
    
    # Step information
    step_name = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)  # format_detection, validation, conversion, etc.
    
    # Execution details
    step_success = Column(Boolean, default=False)
    step_result = Column(JSON, default={})
    step_error = Column(Text, nullable=True)
    step_warnings = Column(JSON, default=[])
    
    # Performance
    step_start_time = Column(DateTime, nullable=True)
    step_end_time = Column(DateTime, nullable=True)
    step_duration = Column(Float, default=0.0)
    
    # Input/output data
    input_data = Column(JSON, default={})
    output_data = Column(JSON, default={})
    
    # Relationships
    pipeline = relationship("DocumentProcessingPipeline", back_populates="pipeline_runs")


class DocumentProcessingCache(Base):
    """Document processing cache for performance optimization"""
    __tablename__ = "document_processing_cache"
    
    cache_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Cache key
    cache_key = Column(String, nullable=False, unique=True, index=True)
    document_hash = Column(String, nullable=False, index=True)  # SHA256 of document
    
    # Cached data
    cache_type = Column(String, nullable=False)  # format_detection, validation, preview, etc.
    cached_result = Column(JSON, default={})
    cache_metadata = Column(JSON, default={})
    
    # Cache management
    cache_version = Column(String, default="1.0")
    expires_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# Extended relationships for the main Document model
def extend_document_model():
    """Extend the Document model with new relationships (called from main models)"""
    # This function would be called to add relationships to the existing Document model
    pass

# Additional utility functions for document processing database operations

def get_document_format_info(db_session, document_id: str) -> DocumentFormatInfo:
    """Get document format information"""
    return db_session.query(DocumentFormatInfo).filter(
        DocumentFormatInfo.document_id == document_id
    ).first()


def create_document_preview(db_session, document_id: str, format_info_id: str,
                          preview_type: str, size_category: str, file_path: str,
                          **kwargs) -> DocumentPreview:
    """Create a new document preview"""
    preview = DocumentPreview(
        document_id=document_id,
        format_info_id=format_info_id,
        preview_type=preview_type,
        size_category=size_category,
        file_path=file_path,
        **kwargs
    )
    db_session.add(preview)
    db_session.commit()
    db_session.refresh(preview)
    return preview


def get_document_conversions(db_session, document_id: str) -> list:
    """Get document conversion history"""
    return db_session.query(DocumentConversion).filter(
        DocumentConversion.document_id == document_id
    ).order_by(DocumentConversion.conversion_started_at.desc()).all()


def create_processing_pipeline(db_session, document_id: str, 
                             pipeline_steps: list, **kwargs) -> DocumentProcessingPipeline:
    """Create a new document processing pipeline execution"""
    pipeline = DocumentProcessingPipeline(
        document_id=document_id,
        pipeline_steps=pipeline_steps,
        **kwargs
    )
    db_session.add(pipeline)
    db_session.commit()
    db_session.refresh(pipeline)
    return pipeline


def cache_processing_result(db_session, cache_key: str, document_hash: str,
                          cache_type: str, result: dict, expires_in_hours: int = 24):
    """Cache processing result for performance"""
    from datetime import timedelta
    
    cache_entry = DocumentProcessingCache(
        cache_key=cache_key,
        document_hash=document_hash,
        cache_type=cache_type,
        cached_result=result,
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
    )
    
    # Remove existing cache entry with same key
    existing = db_session.query(DocumentProcessingCache).filter(
        DocumentProcessingCache.cache_key == cache_key
    ).first()
    
    if existing:
        db_session.delete(existing)
    
    db_session.add(cache_entry)
    db_session.commit()
    db_session.refresh(cache_entry)
    return cache_entry


def get_cached_processing_result(db_session, cache_key: str) -> DocumentProcessingCache:
    """Get cached processing result"""
    cache_entry = db_session.query(DocumentProcessingCache).filter(
        DocumentProcessingCache.cache_key == cache_key,
        DocumentProcessingCache.expires_at > datetime.utcnow()
    ).first()
    
    if cache_entry:
        cache_entry.access_count += 1
        cache_entry.last_accessed_at = datetime.utcnow()
        db_session.commit()
    
    return cache_entry


def cleanup_expired_cache(db_session):
    """Clean up expired cache entries"""
    expired_count = db_session.query(DocumentProcessingCache).filter(
        DocumentProcessingCache.expires_at <= datetime.utcnow()
    ).delete(synchronize_session=False)
    
    db_session.commit()
    return expired_count