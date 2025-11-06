import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from app.db.session import Base


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    
    run_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    stage = Column(String, nullable=False)  # visual, ocr, llm, validate
    status = Column(String, nullable=False)  # success, partial, failed
    engine_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    confidence_avg = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=False)


class ExtractionField(Base):
    __tablename__ = "extraction_fields"
    
    field_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("extraction_runs.run_id"), nullable=False)
    field_name = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)  # 0.0-1.0
    validation_status = Column(String, default="pending")  # pending, valid, invalid, corrected
    correction_applied = Column(Boolean, default=False)
    normalized_value = Column(Text, nullable=True)
