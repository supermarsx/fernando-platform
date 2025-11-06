"""
Database models for human verification and quality control workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, Float, 
    JSON, ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class VerificationStatus(str, Enum):
    """Verification task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    BATCH_PROCESSING = "batch_processing"


class PriorityLevel(str, Enum):
    """Priority levels for verification tasks."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class QualityScore(str, Enum):
    """Quality score levels."""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"  # 85-94%
    ACCEPTABLE = "acceptable"  # 70-84%
    POOR = "poor"  # Below 70%


class VerificationType(str, Enum):
    """Types of verification processes."""
    INITIAL = "initial"
    PEER_REVIEW = "peer_review"
    SUPERVISOR_REVIEW = "supervisor_review"
    QUALITY_CHECK = "quality_check"
    REWORK = "rework"
    BATCH_VERIFICATION = "batch_verification"


class VerificationTask(Base):
    """Main verification task model."""
    __tablename__ = "verification_tasks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Task Identification
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    document_id = Column(String(255), index=True, nullable=False)
    extraction_id = Column(String(255), index=True, nullable=False)
    
    # Task Details
    task_type = Column(SQLEnum(VerificationType), nullable=False)
    status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING)
    priority = Column(SQLEnum(PriorityLevel), default=PriorityLevel.NORMAL)
    
    # Assignment
    assigned_to = Column(String(255), index=True)
    assigned_team = Column(String(255), index=True)
    assigned_by = Column(String(255))
    assigned_at = Column(DateTime)
    due_date = Column(DateTime)
    
    # Processing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time_seconds = Column(Integer)
    
    # AI Data
    ai_confidence_score = Column(Float)  # 0-1 scale
    ai_suggestions = Column(JSON)  # AI-generated suggestions
    ai_detected_anomalies = Column(JSON)  # Anomalies detected by AI
    
    # Human Verification
    verified_data = Column(JSON)  # Human-verified extracted data
    verification_comments = Column(Text)
    corrections_made = Column(JSON)  # List of corrections made
    quality_score = Column(SQLEnum(QualityScore))
    verification_accuracy = Column(Float)  # Percentage accuracy
    
    # Workflow
    parent_task_id = Column(Integer, ForeignKey("verification_tasks.id"))
    escalation_level = Column(Integer, default=0)
    is_urgent = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    last_modified_by = Column(String(255))
    
    # Relationships
    parent_task = relationship("VerificationTask", remote_side=[id], backref="child_tasks")
    quality_reviews = relationship("QualityReview", back_populates="verification_task")


class QualityReview(Base):
    """Quality control review records."""
    __tablename__ = "quality_reviews"

    id = Column(Integer, primary_key=True, index=True)
    
    # Review Identification
    review_id = Column(String(255), unique=True, index=True, nullable=False)
    verification_task_id = Column(Integer, ForeignKey("verification_tasks.id"), nullable=False)
    
    # Review Details
    reviewer_id = Column(String(255), index=True)
    reviewer_role = Column(String(100))  # peer, supervisor, quality_specialist
    review_type = Column(SQLEnum(VerificationType), nullable=False)
    
    # Review Results
    quality_score = Column(Float)  # 0-100 scale
    overall_rating = Column(SQLEnum(QualityScore))
    is_approved = Column(Boolean)
    
    # Detailed Assessment
    accuracy_score = Column(Float)  # Data accuracy percentage
    completeness_score = Column(Float)  # Data completeness percentage
    consistency_score = Column(Float)  # Data consistency percentage
    efficiency_score = Column(Float)  # Processing efficiency percentage
    
    # Feedback
    strengths = Column(JSON)  # List of positive aspects
    weaknesses = Column(JSON)  # Areas for improvement
    recommendations = Column(JSON)  # Specific recommendations
    corrective_actions = Column(JSON)  # Required corrective actions
    
    # Review Process
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    review_time_seconds = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    review_notes = Column(Text)
    
    # Relationships
    verification_task = relationship("VerificationTask", back_populates="quality_reviews")


class AIAssistanceLog(Base):
    """AI assistance and learning log."""
    __tablename__ = "ai_assistance_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Log Identification
    log_id = Column(String(255), unique=True, index=True, nullable=False)
    verification_task_id = Column(Integer, ForeignKey("verification_tasks.id"), index=True)
    
    # AI Analysis
    ai_model_version = Column(String(100))
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Confidence and Scoring
    overall_confidence = Column(Float)  # Overall AI confidence 0-1
    field_confidences = Column(JSON)  # Per-field confidence scores
    anomaly_score = Column(Float)  # Anomaly detection score 0-1
    
    # AI Suggestions
    field_suggestions = Column(JSON)  # AI field value suggestions
    validation_flags = Column(JSON)  # Validation result flags
    anomaly_alerts = Column(JSON)  # Detected anomalies
    
    # Learning Data
    human_corrections = Column(JSON)  # Corrections made by humans
    correction_patterns = Column(JSON)  # Patterns in corrections
    learning_opportunities = Column(JSON)  # Areas for AI improvement
    
    # Model Updates
    update_triggered = Column(Boolean, default=False)
    model_improvement_suggestions = Column(JSON)
    
    # Metadata
    processing_time_ms = Column(Integer)
    token_usage = Column(Integer)
    api_calls_made = Column(Integer)


class VerificationTeam(Base):
    """Verification team management."""
    __tablename__ = "verification_teams"

    id = Column(Integer, primary_key=True, index=True)
    
    # Team Details
    team_name = Column(String(255), unique=True, index=True, nullable=False)
    team_code = Column(String(50), unique=True, nullable=False)
    team_description = Column(Text)
    
    # Specialization
    specialization_area = Column(String(100))  # invoices, receipts, contracts, etc.
    expertise_level = Column(String(50))  # junior, senior, expert
    
    # Team Members
    team_lead = Column(String(255))
    members = Column(JSON)  # List of team member IDs
    
    # Capacity and Performance
    max_concurrent_tasks = Column(Integer, default=10)
    average_processing_time = Column(Float)  # seconds
    quality_accuracy_rate = Column(Float)  # percentage
    
    # Workload Management
    is_active = Column(Boolean, default=True)
    working_hours_start = Column(DateTime)
    working_hours_end = Column(DateTime)
    timezone = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))


class VerificationPerformance(Base):
    """Team and individual performance metrics."""
    __tablename__ = "verification_performance"

    id = Column(Integer, primary_key=True, index=True)
    
    # Performance Period
    metric_date = Column(DateTime, index=True)
    metric_period = Column(String(50))  # daily, weekly, monthly
    
    # Entity
    user_id = Column(String(255), index=True)
    team_id = Column(Integer, ForeignKey("verification_teams.id"), index=True)
    
    # Performance Metrics
    tasks_completed = Column(Integer, default=0)
    tasks_assigned = Column(Integer, default=0)
    tasks_pending = Column(Integer, default=0)
    
    # Quality Metrics
    average_accuracy = Column(Float)  # percentage
    quality_score_distribution = Column(JSON)  # quality score breakdown
    error_rate = Column(Float)  # percentage of errors
    
    # Efficiency Metrics
    average_processing_time = Column(Float)  # seconds
    total_processing_time = Column(Float)  # seconds
    productivity_rate = Column(Float)  # tasks per hour
    
    # Learning Metrics
    corrections_improved = Column(Integer, default=0)
    learning_points = Column(JSON)  # learning insights
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VerificationWorkflow(Base):
    """Workflow configuration and state tracking."""
    __tablename__ = "verification_workflows"

    id = Column(Integer, primary_key=True, index=True)
    
    # Workflow Definition
    workflow_name = Column(String(255), unique=True, index=True, nullable=False)
    workflow_type = Column(String(100))  # standard, custom, emergency
    document_type = Column(String(100))  # invoice, receipt, contract, etc.
    
    # Workflow Steps
    steps = Column(JSON)  # List of workflow steps
    current_step = Column(String(100))
    step_status = Column(SQLEnum(VerificationStatus))
    
    # Assignment Logic
    assignment_rules = Column(JSON)  # Auto-assignment rules
    escalation_rules = Column(JSON)  # Escalation logic
    quality_thresholds = Column(JSON)  # Quality score thresholds
    
    # Timing Configuration
    sla_time_hours = Column(Integer)  # Service level agreement time
    escalation_timeout_hours = Column(Integer)
    auto_assignment_delay_minutes = Column(Integer)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    version = Column(String(50), default="1.0")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))


class VerificationAudit(Base):
    """Comprehensive audit trail for verification activities."""
    __tablename__ = "verification_audit"

    id = Column(Integer, primary_key=True, index=True)
    
    # Audit Entry
    audit_id = Column(String(255), unique=True, index=True, nullable=False)
    entity_type = Column(String(100))  # task, review, team, workflow
    entity_id = Column(String(255))
    
    # Action Details
    action = Column(String(100))  # create, update, complete, escalate, etc.
    action_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # User and Context
    user_id = Column(String(255), index=True)
    user_role = Column(String(100))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Change Details
    field_changes = Column(JSON)  # What fields changed
    old_values = Column(JSON)  # Previous values
    new_values = Column(JSON)  # New values
    
    # Additional Context
    verification_task_id = Column(Integer, ForeignKey("verification_tasks.id"), index=True)
    metadata = Column(JSON)  # Additional context data
    
    # Risk and Compliance
    risk_level = Column(String(50))  # low, medium, high, critical
    compliance_flags = Column(JSON)  # Compliance-related flags


# Database Indexes for Performance
Index("idx_verification_task_status", VerificationTask.status)
Index("idx_verification_task_assigned", VerificationTask.assigned_to)
Index("idx_verification_task_priority", VerificationTask.priority)
Index("idx_verification_task_created", VerificationTask.created_at)
Index("idx_verification_task_due", VerificationTask.due_date)
Index("idx_verification_task_document", VerificationTask.document_id)

Index("idx_quality_review_task", QualityReview.verification_task_id)
Index("idx_quality_review_reviewer", QualityReview.reviewer_id)

Index("idx_ai_assistance_task", AIAssistanceLog.verification_task_id)
Index("idx_ai_assistance_timestamp", AIAssistanceLog.analysis_timestamp)

Index("idx_performance_user_date", VerificationPerformance.user_id, VerificationPerformance.metric_date)
Index("idx_performance_team_date", VerificationPerformance.team_id, VerificationPerformance.metric_date)

Index("idx_audit_entity", VerificationAudit.entity_type, VerificationAudit.entity_id)
Index("idx_audit_timestamp", VerificationAudit.action_timestamp)
Index("idx_audit_user", VerificationAudit.user_id)