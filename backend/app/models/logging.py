"""
Database Models for Logging and Audit System

Provides comprehensive database models for structured logging, audit trails, and compliance.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer, Float, 
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint,
    LargeBinary, Binary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class LogEntry(Base):
    """Structured log entries with full-text search support"""
    __tablename__ = "log_entries"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    
    # Context fields
    correlation_id = Column(String(100), index=True)
    user_id = Column(String(100), index=True)
    request_id = Column(String(100), index=True)
    session_id = Column(String(100), index=True)
    tenant_id = Column(String(100), index=True)
    
    # Data and tags
    data = Column(JSONB)
    tags = Column(JSONB, default=list)
    
    # Metadata
    host = Column(String(100))
    application = Column(String(100))
    version = Column(String(50))
    environment = Column(String(50))
    
    # Performance metrics
    processing_time_ms = Column(Float)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_events = relationship("AuditEvent", back_populates="log_entry")
    
    __table_args__ = (
        Index('idx_log_entries_composite', 'timestamp', 'category', 'level'),
        Index('idx_log_entries_search', 'message', postgresql_using='gin'),
        Index('idx_log_entries_correlation', 'correlation_id', 'timestamp'),
    )


class AuditEvent(Base):
    """Comprehensive audit trail records with immutable storage"""
    __tablename__ = "audit_events"
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_entry_id = Column(UUID(as_uuid=True), ForeignKey("log_entries.log_id"))
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), index=True)
    user_id = Column(String(100), index=True)
    
    # Outcome and severity
    outcome = Column(String(20), nullable=False, index=True)  # success, failure, partial
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    
    # Description and details
    description = Column(Text, nullable=False)
    details = Column(JSONB)
    
    # Network context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    session_id = Column(String(100), index=True)
    
    # Compliance
    compliance_tags = Column(JSONB, default=list)
    retention_period_days = Column(Integer)
    article_references = Column(JSONB, default=list)
    
    # Integrity
    event_hash = Column(String(64), nullable=False)  # SHA-256 hash
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    log_entry = relationship("LogEntry", back_populates="audit_events")
    audit_trail = relationship("AuditTrail", back_populates="audit_event")
    compliance_logs = relationship("ComplianceLog", back_populates="audit_event")
    
    __table_args__ = (
        Index('idx_audit_events_composite', 'timestamp', 'event_type', 'user_id'),
        Index('idx_audit_events_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_events_compliance', 'compliance_tags', 'timestamp'),
    )


class AuditTrail(Base):
    """Immutable audit trail with chain of custody"""
    __tablename__ = "audit_trails"
    
    trail_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_event_id = Column(UUID(as_uuid=True), ForeignKey("audit_events.event_id"), unique=True)
    
    # Chain of custody
    previous_hash = Column(String(64))  # Hash of previous trail entry
    chain_hash = Column(String(64), nullable=False)  # Current chain hash
    
    # Compliance metadata
    compliance_metadata = Column(JSONB)
    regulation_standards = Column(JSONB, default=list)
    
    # Verification
    verified_at = Column(DateTime)
    verification_status = Column(String(20), default="pending")  # pending, verified, failed
    verification_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_event = relationship("AuditEvent", back_populates="audit_trail")
    
    __table_args__ = (
        Index('idx_audit_trail_chain', 'chain_hash'),
        Index('idx_audit_trail_verification', 'verification_status', 'created_at'),
    )


class ForensicLog(Base):
    """Forensic investigation logs with tamper-evidence"""
    __tablename__ = "forensic_logs"
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(50), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    
    # Investigation context
    investigator_id = Column(String(100), nullable=False, index=True)
    metadata = Column(JSONB)
    threat_indicators = Column(JSONB, default=list)
    
    # Anomaly detection
    anomaly_score = Column(Float)
    pattern_matches = Column(JSONB)
    
    # Integrity
    log_hash = Column(String(64), nullable=False)
    chain_of_custody = Column(JSONB, default=list)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    investigation_case = relationship("InvestigationCase", back_populates="forensic_logs")
    
    __table_args__ = (
        Index('idx_forensic_logs_case', 'case_id', 'timestamp'),
        Index('idx_forensic_logs_investigator', 'investigator_id', 'timestamp'),
        Index('idx_forensic_logs_integrity', 'log_hash'),
    )


class InvestigationCase(Base):
    """Security investigation case management"""
    __tablename__ = "investigation_cases"
    
    case_id = Column(String(50), primary_key=True)
    incident_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    
    # Case details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, index=True)  # open, in_progress, closed
    
    # Investigation details
    created_by = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    closed_by = Column(String(100))
    
    # Case metadata
    affected_systems = Column(JSONB, default=list)
    initial_indicators = Column(JSONB, default=list)
    compliance_tags = Column(JSONB, default=list)
    
    # Resolution
    closure_reason = Column(Text)
    resolution_summary = Column(Text)
    lessons_learned = Column(JSONB, default=list)
    recommendations = Column(JSONB, default=list)
    
    # Relationships
    forensic_logs = relationship("ForensicLog", back_populates="investigation_case")
    evidence_records = relationship("EvidenceRecord", back_populates="investigation_case")
    
    __table_args__ = (
        Index('idx_investigation_cases_status', 'status', 'created_at'),
        Index('idx_investigation_cases_severity', 'severity', 'created_at'),
    )


class EvidenceRecord(Base):
    """Digital evidence records with chain of custody"""
    __tablename__ = "evidence_records"
    
    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(50), ForeignKey("investigation_cases.case_id"), nullable=False)
    
    # Evidence details
    evidence_type = Column(String(50), nullable=False, index=True)
    evidence_description = Column(Text, nullable=False)
    file_path = Column(Text)  # Path to evidence file
    data_hash = Column(String(64), nullable=False)  # SHA-256 hash of evidence
    
    # Collection details
    collected_by = Column(String(100), nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, index=True)
    collection_method = Column(String(50))  # manual, automated, forensic_tool
    
    # Chain of custody
    chain_of_custody = Column(JSONB, default=list)
    last_custodian = Column(String(100))
    last_custody_action = Column(String(100))
    
    # Forensic tools and metadata
    forensic_tools_used = Column(JSONB, default=list)
    metadata = Column(JSONB)
    evidence_integrity_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    investigation_case = relationship("InvestigationCase", back_populates="evidence_records")
    
    __table_args__ = (
        Index('idx_evidence_case', 'case_id', 'collected_at'),
        Index('idx_evidence_integrity', 'data_hash'),
        Index('idx_evidence_custodian', 'collected_by', 'collected_at'),
    )


class ComplianceLog(Base):
    """Compliance tracking and regulatory reporting"""
    __tablename__ = "compliance_logs"
    
    compliance_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_event_id = Column(UUID(as_uuid=True), ForeignKey("audit_events.event_id"))
    
    # Compliance details
    regulation_standard = Column(String(50), nullable=False, index=True)  # gdpr, sox, pci_dss
    data_subject_id = Column(String(100), index=True)  # Hash or pseudonymous ID
    
    # Operation details
    operation_type = Column(String(50), nullable=False, index=True)
    lawful_basis = Column(String(100))  # GDPR lawful basis
    processing_purpose = Column(Text, nullable=False)
    data_categories = Column(JSONB, default=list)
    
    # User context
    user_id = Column(String(100), index=True)
    article_references = Column(JSONB, default=list)
    
    # Compliance status
    compliance_status = Column(String(20), nullable=False, index=True)  # compliant, non_compliant, requires_review
    checked_at = Column(DateTime, nullable=False, index=True)
    retention_until = Column(DateTime, nullable=False, index=True)
    
    # Critical incidents
    critical_incident = Column(Boolean, default=False)
    
    # Metadata and audit trail
    metadata = Column(JSONB)
    audit_trail_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_event = relationship("AuditEvent", back_populates="compliance_logs")
    
    __table_args__ = (
        Index('idx_compliance_logs_regulation', 'regulation_standard', 'checked_at'),
        Index('idx_compliance_logs_retention', 'retention_until'),
        Index('idx_compliance_logs_subject', 'data_subject_id'),
        Index('idx_compliance_logs_critical', 'critical_incident', 'checked_at'),
    )


class DataSubjectRecord(Base):
    """Data subject records for GDPR compliance (Right to be Forgotten)"""
    __tablename__ = "data_subject_records"
    
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_subject_id = Column(String(100), nullable=False, index=True)
    
    # Request details
    request_type = Column(String(50), nullable=False, index=True)  # right_to_be_forgotten, data_portability
    request_reason = Column(Text)
    status = Column(String(20), nullable=False, index=True)  # pending, in_progress, completed
    
    # Timeline
    requested_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    
    # Processing details
    processing_steps = Column(JSONB, default=list)
    requester_id = Column(String(100), index=True)  # User who made the request
    
    # Compliance
    regulatory_basis = Column(String(50))  # GDPR Article 17, etc.
    data_categories_affected = Column(JSONB, default=list)
    third_parties_notified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_data_subject_requests', 'data_subject_id', 'status'),
        Index('idx_data_subject_timeline', 'requested_at', 'status'),
    )


class LogRetentionPolicy(Base):
    """Log retention policies for automated cleanup"""
    __tablename__ = "log_retention_policies"
    
    policy_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    
    # Policy details
    category = Column(String(50), nullable=False, index=True)
    retention_period_days = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # delete, archive, compress
    
    # Configuration
    archive_path = Column(Text)
    compression_enabled = Column(Boolean, default=False)
    encryption_enabled = Column(Boolean, default=False)
    
    # Compliance
    compliance_requirements = Column(JSONB, default=list)
    min_severity = Column(String(20), default="info")
    max_file_size_mb = Column(Integer, default=1000)
    batch_size = Column(Integer, default=1000)
    
    # Status
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    log_archives = relationship("LogArchive", back_populates="retention_policy")
    
    __table_args__ = (
        Index('idx_retention_policies_category', 'category', 'enabled'),
        Index('idx_retention_policies_compliance', 'compliance_requirements'),
    )


class LogArchive(Base):
    """Log archive records for compliance and backup"""
    __tablename__ = "log_archives"
    
    archive_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(String(50), ForeignKey("log_retention_policies.policy_id"))
    
    # Archive details
    archive_name = Column(String(200), nullable=False)
    archive_path = Column(Text, nullable=False)
    log_category = Column(String(50), nullable=False, index=True)
    
    # Content details
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    file_count = Column(Integer, default=0)
    archive_size_bytes = Column(Integer, default=0)
    compression_ratio = Column(Float)
    
    # Integrity
    checksum = Column(String(64))  # SHA-256 of archive
    integrity_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime)
    
    # Status
    status = Column(String(20), default="active")  # active, restored, deleted
    restore_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    retention_policy = relationship("LogRetentionPolicy", back_populates="log_archives")
    
    __table_args__ = (
        Index('idx_log_archives_category', 'log_category', 'start_date'),
        Index('idx_log_archives_retention', 'policy_id', 'created_at'),
        Index('idx_log_archives_integrity', 'checksum'),
    )


class LogIndexTemplate(Base):
    """Elasticsearch index templates for log management"""
    __tablename__ = "log_index_templates"
    
    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(100), nullable=False, unique=True)
    
    # Template details
    index_pattern = Column(String(200), nullable=False)
    template_body = Column(JSONB, nullable=False)
    
    # Elasticsearch settings
    settings = Column(JSONB)
    mappings = Column(JSONB)
    
    # Status
    version = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    elk_configurations = relationship("ELKConfiguration", back_populates="index_template")
    
    __table_args__ = (
        Index('idx_log_index_templates_pattern', 'index_pattern'),
    )


class ELKConfiguration(Base):
    """ELK stack configuration and monitoring"""
    __tablename__ = "elk_configurations"
    
    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    
    # Connection details
    elasticsearch_url = Column(String(500), nullable=False)
    kibana_url = Column(String(500))
    logstash_url = Column(String(500))
    
    # Authentication
    username = Column(String(100))
    encrypted_password = Column(Text)  # Encrypted password
    api_key = Column(Text)  # Encrypted API key
    authentication_type = Column(String(20))  # basic, api_key, oauth
    
    # Configuration
    index_template_id = Column(UUID(as_uuid=True), ForeignKey("log_index_templates.template_id"))
    default_index_pattern = Column(String(200))
    
    # Monitoring
    health_check_enabled = Column(Boolean, default=True)
    last_health_check = Column(DateTime)
    health_status = Column(String(20), default="unknown")
    
    # Status
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    index_template = relationship("LogIndexTemplate", back_populates="elk_configurations")
    search_queries = relationship("SearchQuery", back_populates="elk_config")
    
    __table_args__ = (
        Index('idx_elk_configurations_enabled', 'enabled', 'created_at'),
    )


class SearchQuery(Base):
    """Saved search queries for log analysis"""
    __tablename__ = "search_queries"
    
    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elk_config_id = Column(UUID(as_uuid=True), ForeignKey("elk_configurations.config_id"))
    
    # Query details
    query_name = Column(String(200), nullable=False)
    description = Column(Text)
    query_body = Column(JSONB, nullable=False)
    index_pattern = Column(String(200))
    
    # Query metadata
    query_type = Column(String(50))  # match, bool, aggregation, etc.
    saved_by = Column(String(100), index=True)
    is_public = Column(Boolean, default=False)
    
    # Usage tracking
    execution_count = Column(Integer, default=0)
    last_executed = Column(DateTime)
    avg_execution_time_ms = Column(Float)
    
    # Status
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    elk_config = relationship("ELKConfiguration", back_populates="search_queries")
    
    __table_args__ = (
        Index('idx_search_queries_user', 'saved_by', 'created_at'),
        Index('idx_search_queries_public', 'is_public', 'query_type'),
    )


class LogDestination(Base):
    """Log destination configurations for multi-output logging"""
    __tablename__ = "log_destinations"
    
    destination_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    
    # Destination details
    destination_type = Column(String(50), nullable=False, index=True)  # file, database, elasticsearch, kafka
    config = Column(JSONB, nullable=False)
    
    # Status
    enabled = Column(Boolean, default=True)
    last_error = Column(Text)
    last_success = Column(DateTime)
    error_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    
    # Health monitoring
    health_check_enabled = Column(Boolean, default=True)
    health_check_interval_seconds = Column(Integer, default=300)
    last_health_check = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_log_destinations_type', 'destination_type', 'enabled'),
    )


class LogBatch(Base):
    """Log batches for efficient processing and transmission"""
    __tablename__ = "log_batches"
    
    batch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Batch details
    logs = Column(JSONB, nullable=False)  # Array of log entries
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    batch_size = Column(Integer, nullable=False)
    
    # Processing status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime)
    processing_duration_ms = Column(Float)
    
    # Destinations
    destinations = Column(JSONB)  # List of destinations
    delivery_status = Column(JSONB)  # Status per destination
    
    # Performance metrics
    total_size_bytes = Column(Integer)
    compression_ratio = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_log_batches_timestamp', 'timestamp', 'status'),
        Index('idx_log_batches_source', 'source', 'batch_size'),
    )


class RetentionMetrics(Base):
    """Metrics for retention policy performance and compliance"""
    __tablename__ = "retention_metrics"
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(String(50), ForeignKey("log_retention_policies.policy_id"))
    
    # Metrics
    metric_date = Column(DateTime, nullable=False, index=True)
    logs_processed = Column(Integer, default=0)
    logs_archived = Column(Integer, default=0)
    logs_deleted = Column(Integer, default=0)
    space_freed_mb = Column(Float, default=0.0)
    space_archived_mb = Column(Float, default=0.0)
    
    # Performance
    processing_duration_seconds = Column(Float)
    batch_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Compliance
    compliance_violations = Column(Integer, default=0)
    overdue_deletions = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    retention_policy = relationship("LogRetentionPolicy")
    
    __table_args__ = (
        Index('idx_retention_metrics_policy', 'policy_id', 'metric_date'),
        Index('idx_retention_metrics_compliance', 'compliance_violations', 'metric_date'),
    )


class ChainOfCustody(Base):
    """Chain of custody tracking for digital evidence and audit logs"""
    __tablename__ = "chain_of_custody"
    
    custody_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Evidence identification
    evidence_id = Column(String(100), nullable=False, index=True)  # Can reference different evidence types
    evidence_type = Column(String(50), nullable=False)  # log, document, file, etc.
    
    # Custody details
    custodian = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # collected, transferred, accessed, analyzed
    location = Column(String(200))
    
    # Context
    case_id = Column(String(50))  # Optional case association
    operation_id = Column(String(100))  # Operation that triggered custody change
    
    # Integrity
    previous_custodian = Column(String(100))
    integrity_hash = Column(String(64))  # Hash for integrity verification
    verification_status = Column(String(20), default="pending")  # pending, verified, failed
    
    # Metadata
    metadata = Column(JSONB)
    notes = Column(Text)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chain_custody_evidence', 'evidence_id', 'evidence_type'),
        Index('idx_chain_custody_custodian', 'custodian', 'timestamp'),
        Index('idx_chain_custody_case', 'case_id', 'timestamp'),
    )


# Database triggers and functions for audit trail integrity
def create_audit_triggers():
    """
    Create database triggers for audit trail integrity.
    This would be implemented using Alembic migrations in production.
    """
    pass


# Utility functions for log management
def cleanup_old_logs(days_to_keep: int = 30) -> int:
    """Utility function to clean up old log entries"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old log entries
        deleted_count = db.query(LogEntry).filter(
            LogEntry.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        return deleted_count
        
    except Exception as e:
        db.rollback()
        structured_logger.error(f"Error cleaning up old logs: {str(e)}")
        return 0
    finally:
        db.close()


def verify_audit_trail_integrity() -> Dict[str, Any]:
    """Verify audit trail integrity across the chain"""
    db = SessionLocal()
    try:
        # Get all audit trail entries ordered by creation time
        trail_entries = db.query(AuditTrail).order_by(AuditTrail.created_at).all()
        
        integrity_results = {
            'total_entries': len(trail_entries),
            'verified_entries': 0,
            'corrupted_entries': 0,
            'chain_valid': True,
            'corruption_details': []
        }
        
        previous_hash = None
        
        for trail in trail_entries:
            # Verify chain hash
            if previous_hash:
                expected_hash = create_chain_hash(trail.audit_event.event_hash, previous_hash)
                
                if trail.chain_hash != expected_hash:
                    integrity_results['chain_valid'] = False
                    integrity_results['corrupted_entries'] += 1
                    integrity_results['corruption_details'].append({
                        'trail_id': str(trail.trail_id),
                        'audit_event_id': str(trail.audit_event_id),
                        'expected_hash': expected_hash,
                        'actual_hash': trail.chain_hash,
                        'corruption_type': 'chain_hash_mismatch'
                    })
                else:
                    integrity_results['verified_entries'] += 1
            else:
                # First entry - verify hash exists
                if trail.chain_hash:
                    integrity_results['verified_entries'] += 1
                else:
                    integrity_results['corrupted_entries'] += 1
                    integrity_results['corruption_details'].append({
                        'trail_id': str(trail.trail_id),
                        'audit_event_id': str(trail.audit_event_id),
                        'corruption_type': 'missing_chain_hash'
                    })
            
            previous_hash = trail.chain_hash
        
        return integrity_results
        
    finally:
        db.close()


def create_chain_hash(event_hash: str, previous_hash: str) -> str:
    """Create chain hash for audit trail integrity"""
    import hashlib
    chain_data = f"{event_hash}{previous_hash}"
    return hashlib.sha256(chain_data.encode()).hexdigest()


# Indexes for performance optimization
def create_performance_indexes():
    """Create additional indexes for performance optimization"""
    pass