import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)  # Multi-tenant support
    status = Column(String, default="queued")  # queued, processing, needs_review, posted, failed, canceled
    priority = Column(Integer, default=0)
    queue_name = Column(String, default="default")
    uploaded_by = Column(String, ForeignKey("users.user_id"), nullable=False)
    assigned_to = Column(String, ForeignKey("users.user_id"), nullable=True)
    estimated_duration = Column(Integer, nullable=True)  # seconds
    actual_duration = Column(Integer, nullable=True)    # seconds
    retry_count = Column(Integer, default=0)
    job_metadata = Column(JSON, default={})  # Additional job metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_code = Column(String, nullable=True)
    error_details = Column(String, nullable=True)
    progress_percentage = Column(Integer, default=0)  # For batch processing
