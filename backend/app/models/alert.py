"""
Alert Models for comprehensive monitoring and alerting system.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class AlertType(str, Enum):
    """Types of alerts"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"
    CUSTOM = "custom"


class AlertChannel(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"


class EscalationAction(str, Enum):
    """Escalation actions"""
    NOTIFY_MANAGER = "notify_manager"
    PAGE_ONCALL = "page_oncall"
    CREATE_INCIDENT = "create_incident"
    ESCALATE_CHANNEL = "escalate_channel"


class AlertRule(Base):
    """Alert rule configuration"""
    __tablename__ = "alert_rules"
    
    rule_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    
    # Rule configuration
    condition = Column(JSON, nullable=False)  # JSON defining the alert condition
    threshold_config = Column(JSON)  # Threshold and time window configuration
    query_config = Column(JSON)  # Data source query configuration
    
    # Alerting configuration
    channels = Column(JSON, nullable=False, default=[])  # List of notification channels
    recipients = Column(JSON, default=[])  # List of recipients for each channel
    
    # Rule state
    enabled = Column(Boolean, default=True)
    evaluation_frequency = Column(Integer, default=300)  # Seconds between evaluations
    sustained_duration = Column(Integer, default=60)  # Seconds before triggering
    cooldown_period = Column(Integer, default=300)  # Seconds to wait before re-triggering
    
    # Escalation
    escalation_rules = Column(JSON)  # Escalation configuration
    
    # Metadata
    tags = Column(JSON, default=[])
    metadata = Column(JSON, default={})
    
    created_by = Column(String, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    alerts = relationship("Alert", back_populates="rule")


class Alert(Base):
    """Alert instance"""
    __tablename__ = "alerts"
    
    alert_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, ForeignKey("alert_rules.rule_id"), nullable=False)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    
    # Alert content
    title = Column(String, nullable=False)
    description = Column(Text)
    message = Column(Text, nullable=False)
    
    # Context data
    context = Column(JSON, default={})  # Additional context data
    metric_value = Column(Float)  # Current metric value
    threshold_value = Column(Float)  # Threshold value
    labels = Column(JSON, default={})  # Alert labels/tags
    
    # Timing
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Acknowledgment
    acknowledged_by = Column(String, ForeignKey("users.user_id"))
    resolved_by = Column(String, ForeignKey("users.user_id"))
    resolution_notes = Column(Text)
    
    # Notification tracking
    notifications_sent = Column(JSON, default={})  # Track notifications sent per channel
    notification_count = Column(Integer, default=0)
    last_notification_sent = Column(DateTime)
    
    # Escalation
    escalation_level = Column(Integer, default=0)
    escalated_at = Column(DateTime)
    escalation_action = Column(SQLEnum(EscalationAction))
    
    # Metadata
    dedup_key = Column(String, index=True)  # For deduplication
    runbook_url = Column(String)  # Link to runbook for resolution
    source_system = Column(String)  # System that generated the alert
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    notifications = relationship("AlertNotification", back_populates="alert")


class AlertNotification(Base):
    """Alert notification tracking"""
    __tablename__ = "alert_notifications"
    
    notification_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=False)
    channel = Column(SQLEnum(AlertChannel), nullable=False)
    recipient = Column(String, nullable=False)
    
    # Notification status
    status = Column(String, default="pending")  # pending, sent, failed, delivered, bounced
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    error_message = Column(Text)
    
    # Content
    subject = Column(String)
    content = Column(Text)
    message_id = Column(String)  # External message ID for tracking
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alert = relationship("Alert", back_populates="notifications")


class EscalationPolicy(Base):
    """Escalation policy configuration"""
    __tablename__ = "escalation_policies"
    
    policy_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Policy rules
    escalation_levels = Column(JSON, nullable=False)  # List of escalation levels
    escalation_rules = Column(JSON, nullable=False)  # Escalation logic
    
    # Policy configuration
    enabled = Column(Boolean, default=True)
    auto_resolution = Column(Boolean, default=False)
    
    # Timing
    escalation_timeouts = Column(JSON)  # Timeouts for each escalation level
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OnCallSchedule(Base):
    """On-call schedule configuration"""
    __tablename__ = "oncall_schedules"
    
    schedule_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Schedule configuration
    rotation_type = Column(String)  # daily, weekly, custom
    participants = Column(JSON, nullable=False)  # List of participant user IDs
    
    # Time configuration
    timezone = Column(String, default="UTC")
    working_hours = Column(JSON)  # Working hours configuration
    holidays = Column(JSON, default=[])  # Holiday calendar
    
    # Escalation
    escalation_chain = Column(JSON)  # Escalation chain configuration
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertTemplate(Base):
    """Alert notification templates"""
    __tablename__ = "alert_templates"
    
    template_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    channel = Column(SQLEnum(AlertChannel), nullable=False)
    alert_type = Column(SQLEnum(AlertType))
    severity = Column(SQLEnum(AlertSeverity))
    
    # Template content
    subject_template = Column(String)  # Subject line template
    body_template = Column(Text, nullable=False)  # Body content template
    variables = Column(JSON, default=[])  # Available template variables
    
    # Template configuration
    template_type = Column(String, default="default")  # default, custom
    format_type = Column(String)  # html, text, markdown
    
    # Metadata
    description = Column(Text)
    tags = Column(JSON, default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MetricThreshold(Base):
    """Metric threshold configuration for dynamic alert rules"""
    __tablename__ = "metric_thresholds"
    
    threshold_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    
    # Threshold configuration
    operator = Column(String, nullable=False)  # gt, gte, lt, lte, eq, ne
    warning_threshold = Column(Float)
    critical_threshold = Column(Float)
    time_window = Column(Integer, default=300)  # Seconds
    
    # Aggregation
    aggregation_method = Column(String, default="avg")  # avg, sum, max, min, count
    evaluation_period = Column(Integer, default=60)  # Seconds
    
    # Context
    labels = Column(JSON, default={})  # Metric labels for filtering
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)