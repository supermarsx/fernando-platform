import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    audit_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    action = Column(String, nullable=False)  # upload.created, extraction.corrected, job.approved, etc.
    target_type = Column(String, nullable=False)  # job, document, extraction_run, extraction_field
    target_id = Column(String, nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
