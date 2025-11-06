"""
Document Processing Service

Orchestrates the complete document processing pipeline:
1. Visual analysis (layout detection)
2. OCR (text extraction) - Production-ready with multiple backends
3. LLM extraction (structured fields) - OpenAI/Claude/local models
4. Validation
"""
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.document import Document
from app.models.extraction import ExtractionRun, ExtractionField
from app.models.audit import AuditLog

# Import real services
from app.services.ocr_service import get_ocr_service
from app.services.llm_service import get_llm_service
from app.services.cache.redis_cache import cache_service, cache_result
from app.middleware.telemetry_decorators import (
    document_telemetry, extraction_telemetry, business_telemetry,
    record_business_metric, increment_metric
)

# Fallback to mock services if real ones not available
try:
    from app.services.mock_ocr import MockOCRService
    from app.services.mock_llm import MockLLMService
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False


class DocumentProcessingService:
    """Service to process documents through the complete pipeline with Redis caching"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Use environment variable to control mock vs real services
        use_mock = os.getenv("ENABLE_MOCK_SERVICES", "false").lower() == "true"
        
        if use_mock and MOCK_AVAILABLE:
            print("Using MOCK services for OCR and LLM")
            self.ocr_service = MockOCRService()
            self.llm_service = MockLLMService()
        else:
            print("Using PRODUCTION services for OCR and LLM")
            self.ocr_service = get_ocr_service()
            self.llm_service = get_llm_service()
        
        # Initialize cache settings
        self.cache_enabled = True
        self.tenant_id = None  # Will be set per request
    
    def set_tenant_context(self, tenant_id: str):
        """Set tenant context for multi-tenant caching."""
        self.tenant_id = tenant_id
    
    def _get_document_hash(self, document: Document) -> str:
        """Get or calculate document hash for caching."""
        if document.checksum_sha256:
            return document.checksum_sha256
        
        # Calculate hash from file path if checksum not available
        return calculate_file_checksum(document.storage_url)
    
    def _cache_key_doc_hash(self, document_hash: str) -> str:
        """Generate cache key for document hash."""
        return f"doc_processed:{document_hash}"
    
    @document_telemetry("process_document")
    async def process_document(self, document: Document, user_id: str) -> ExtractionRun:
        """
        Process a document through the complete pipeline with caching
        
        Args:
            document: Document model instance
            user_id: ID of user who initiated processing
        
        Returns:
            Final extraction run with all fields
        """
        # Update job status
        job = self.db.query(Job).filter(Job.job_id == document.job_id).first()
        if job:
            job.status = "processing"
            job.started_at = datetime.utcnow()
            self.db.commit()
        
        try:
            # Check cache for identical document (hash-based caching)
            document_hash = self._get_document_hash(document)
            
            if self.cache_enabled and self.tenant_id:
                cached_result = await cache_service.get_cached_document(document_hash, self.tenant_id)
                if cached_result:
                    # Return cached result - create new ExtractionRun from cached data
                    validation_run = ExtractionRun(
                        document_id=document.document_id,
                        stage="cached",
                        status="success",
                        engine_name=cached_result.get("engine", "cache"),
                        model_version=cached_result.get("version", "1.0"),
                        confidence_avg=cached_result.get("confidence_avg", 0.0),
                        started_at=datetime.utcnow(),
                        finished_at=datetime.utcnow()
                    )
                    self.db.add(validation_run)
                    self.db.commit()
                    self.db.refresh(validation_run)
                    
                    # Log cache hit
                    self._log_audit_event(
                        user_id=user_id,
                        action="document.cached_processing",
                        target_type="document",
                        target_id=document.document_id,
                        metadata={"document_hash": document_hash, "cache_hit": True}
                    )
                    
                    # Update job status
                    if job:
                        job.status = "needs_review"
                        job.updated_at = datetime.utcnow()
                        self.db.commit()
                    
                    return validation_run
            
            # Process document normally if not cached
            # Stage 1: OCR Processing
            ocr_run = await self._run_ocr_stage(document, user_id)
            
            # Stage 2: LLM Extraction
            llm_run = await self._run_llm_stage(document, ocr_run, user_id)
            
            # Stage 3: Validation
            validation_run = self._run_validation_stage(llm_run, user_id)
            
            # Cache the processed result
            if self.cache_enabled and self.tenant_id:
                cache_data = {
                    "document_hash": document_hash,
                    "document_id": document.document_id,
                    "engine": llm_run.engine_name,
                    "version": llm_run.model_version,
                    "confidence_avg": llm_run.confidence_avg,
                    "fields_count": len(self._get_extraction_fields(llm_run.run_id)),
                    "processed_at": validation_run.finished_at.isoformat()
                }
                await cache_service.cache_document_hash(
                    document_hash, cache_data, self.tenant_id
                )
            
            # Update job status
            if job:
                job.status = "needs_review"
                job.updated_at = datetime.utcnow()
                self.db.commit()
            
            return validation_run
            
        except Exception as e:
            # Handle errors
            if job:
                job.status = "failed"
                job.error_code = "PROCESSING_ERROR"
                job.finished_at = datetime.utcnow()
                self.db.commit()
            
            # Log audit event
            self._log_audit_event(
                user_id=user_id,
                action="job.failed",
                target_type="job",
                target_id=document.job_id,
                metadata={"error": str(e)}
            )
            
            raise
    
    @extraction_telemetry("run_ocr_stage")
    async def _run_ocr_stage(self, document: Document, user_id: str) -> ExtractionRun:
        """Run OCR stage with caching and create extraction run"""
        started_at = datetime.utcnow()
        
        # Check cache for OCR results
        cached_ocr = None
        if self.cache_enabled and self.tenant_id:
            cached_ocr = await cache_service.get_cached_ocr(document.document_id, self.tenant_id)
        
        if cached_ocr:
            # Use cached OCR result
            ocr_result = cached_ocr
            source = "cache"
        else:
            # Run OCR
            ocr_result = self.ocr_service.process_document(document.storage_url)
            source = "processing"
            
            # Cache the OCR result
            if self.cache_enabled and self.tenant_id:
                await cache_service.cache_ocr_result(
                    document.document_id, ocr_result, self.tenant_id
                )
        
        # Create extraction run
        ocr_run = ExtractionRun(
            document_id=document.document_id,
            stage="ocr",
            status="success",
            engine_name=ocr_result["engine"],
            model_version=ocr_result["version"],
            confidence_avg=ocr_result["confidence"],
            started_at=started_at,
            finished_at=datetime.utcnow()
        )
        self.db.add(ocr_run)
        self.db.commit()
        self.db.refresh(ocr_run)
        
        # Store OCR text as a field
        ocr_text_field = ExtractionField(
            run_id=ocr_run.run_id,
            field_name="ocr_text",
            value=ocr_result["text"],
            confidence=ocr_result["confidence"],
            validation_status="valid"
        )
        self.db.add(ocr_text_field)
        self.db.commit()
        
        # Log audit event
        self._log_audit_event(
            user_id=user_id,
            action=f"extraction.ocr_complete_{source}",
            target_type="extraction_run",
            target_id=ocr_run.run_id,
            metadata={
                "confidence": ocr_result["confidence"],
                "source": source
            }
        )
        
        return ocr_run
    
    @extraction_telemetry("run_llm_stage")
    async def _run_llm_stage(self, document: Document, ocr_run: ExtractionRun, user_id: str) -> ExtractionRun:
        """Run LLM extraction stage with caching"""
        started_at = datetime.utcnow()
        
        # Check cache for LLM extraction results
        cached_llm = None
        if self.cache_enabled and self.tenant_id:
            cached_llm = await cache_service.get_cached_llm_extraction(document.document_id, self.tenant_id)
        
        if cached_llm:
            # Use cached LLM result
            llm_result = cached_llm
            source = "cache"
        else:
            # Get OCR text
            ocr_text_field = self.db.query(ExtractionField).filter(
                ExtractionField.run_id == ocr_run.run_id,
                ExtractionField.field_name == "ocr_text"
            ).first()
            
            ocr_text = ocr_text_field.value if ocr_text_field else ""
            
            # Run LLM extraction
            llm_result = self.llm_service.extract_fields(ocr_text)
            source = "processing"
            
            # Cache the LLM result
            if self.cache_enabled and self.tenant_id:
                await cache_service.cache_llm_extraction(
                    document.document_id, llm_result, self.tenant_id
                )
        
        # Calculate average confidence
        confidences = [field_data["confidence"] for field_data in llm_result["fields"].values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Create extraction run
        llm_run = ExtractionRun(
            document_id=document.document_id,
            stage="llm",
            status="success",
            engine_name=llm_result["model"],
            model_version=llm_result["version"],
            confidence_avg=avg_confidence,
            started_at=started_at,
            finished_at=datetime.utcnow()
        )
        self.db.add(llm_run)
        self.db.commit()
        self.db.refresh(llm_run)
        
        # Store extracted fields
        for field_name, field_data in llm_result["fields"].items():
            extraction_field = ExtractionField(
                run_id=llm_run.run_id,
                field_name=field_name,
                value=field_data["value"],
                confidence=field_data["confidence"],
                validation_status="pending"
            )
            self.db.add(extraction_field)
        
        self.db.commit()
        
        # Log audit event
        self._log_audit_event(
            user_id=user_id,
            action=f"extraction.llm_complete_{source}",
            target_type="extraction_run",
            target_id=llm_run.run_id,
            metadata={
                "confidence": avg_confidence, 
                "fields_extracted": len(llm_result["fields"]),
                "source": source
            }
        )
        
        return llm_run
    
    @extraction_telemetry("run_validation_stage")
    def _run_validation_stage(self, llm_run: ExtractionRun, user_id: str) -> ExtractionRun:
        """Run validation stage"""
        # Get all fields from LLM run
        fields = self.db.query(ExtractionField).filter(
            ExtractionField.run_id == llm_run.run_id
        ).all()
        
        # Prepare fields dict for validation
        fields_dict = {
            field.field_name: {"value": field.value, "confidence": field.confidence}
            for field in fields
        }
        
        # Run validation
        validations = self.llm_service.validate_extraction(fields_dict)
        
        # Update field validation status
        for field in fields:
            if field.field_name in validations:
                field.validation_status = "valid" if validations[field.field_name] else "invalid"
                field.normalized_value = field.value  # In real implementation, apply normalization
        
        self.db.commit()
        
        # Log audit event
        valid_count = sum(1 for v in validations.values() if v)
        self._log_audit_event(
            user_id=user_id,
            action="extraction.validation_complete",
            target_type="extraction_run",
            target_id=llm_run.run_id,
            metadata={"valid_fields": valid_count, "total_fields": len(validations)}
        )
        
        return llm_run
    
    def _log_audit_event(self, user_id: str, action: str, target_type: str, 
                         target_id: str, metadata: dict = None):
        """Log an audit event"""
        audit_log = AuditLog(
            actor_user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata
        )
        self.db.add(audit_log)
        self.db.commit()
    
    def _get_extraction_fields(self, run_id: str) -> List[ExtractionField]:
        """Get all extraction fields for a run."""
        return self.db.query(ExtractionField).filter(
            ExtractionField.run_id == run_id
        ).all()


def calculate_file_checksum(file_path: str) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
