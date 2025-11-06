"""
Telemetry Data Models for Fernando Platform

Comprehensive telemetry system supporting:
- Event tracking and user actions
- System and business metrics collection
- Custom alerting rules and notifications
- Distributed tracing for performance monitoring
- Time-series optimized storage with partitioning support
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, JSON, Float, Text, 
    Index, ForeignKey, Enum as SQLEnum, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class EventType(str):
    """Event type constants for categorization"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    BUSINESS_EVENT = "business_event"
    SECURITY_EVENT = "security_event"
    PERFORMANCE_EVENT = "performance_event"
    ERROR_EVENT = "error_event"
    API_EVENT = "api_event"


class MetricType(str):
    """Metric type constants"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    DISTRIBUTION = "distribution"


class SeverityLevel(str):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TelemetryEvent(Base):
    """
    Stores individual events and user actions for analytics and debugging.
    Optimized for high-volume inserts and efficient time-based queries.
    """
    __tablename__ = "telemetry_events"
    
    # Primary identification
    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Event categorization
    event_type = Column(SQLEnum(
        EventType.USER_ACTION, EventType.SYSTEM_EVENT, EventType.BUSINESS_EVENT,
        EventType.SECURITY_EVENT, EventType.PERFORMANCE_EVENT, EventType.ERROR_EVENT,
        EventType.API_EVENT, name="event_type"
    ), nullable=False, index=True)
    
    # Event details
    event_name = Column(String, nullable=False, index=True)  # e.g., "user_login", "document_processed"
    event_category = Column(String, index=True)  # e.g., "authentication", "processing", "billing"
    
    # Context and attribution
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    license_id = Column(Integer, ForeignKey("licenses.license_id"), index=True)
    session_id = Column(String, index=True)
    
    # Timestamps
    event_timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Event data
    event_data = Column(JSON)  # Flexible event payload
    
    # Source tracking
    source = Column(String, index=True)  # e.g., "web", "api", "mobile", "batch_job"
    source_version = Column(String)
    source_ip = Column(String, index=True)
    user_agent = Column(Text)
    
    # Performance metrics
    duration_ms = Column(Integer)  # Duration in milliseconds if applicable
    
    # Processing status
    is_processed = Column(Boolean, default=False, index=True)
    processing_batch_id = Column(String, index=True)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Note: Relationships are defined in User and License models to avoid circular imports
    # user = relationship("User")
    # license = relationship("License")
    
    # Indexes for performance optimization
    __table_args__ = (
        # Time-series optimized indexes
        Index('idx_telemetry_events_timestamp', 'event_timestamp'),
        Index('idx_telemetry_events_type_time', 'event_type', 'event_timestamp'),
        Index('idx_telemetry_events_user_time', 'user_id', 'event_timestamp'),
        Index('idx_telemetry_events_license_time', 'license_id', 'event_timestamp'),
        Index('idx_telemetry_events_category_time', 'event_category', 'event_timestamp'),
        Index('idx_telemetry_events_source_time', 'source', 'event_timestamp'),
        Index('idx_telemetry_events_processed', 'is_processed', 'processing_batch_id'),
        
        # Composite indexes for common queries
        Index('idx_telemetry_events_user_category_time', 'user_id', 'event_category', 'event_timestamp'),
        Index('idx_telemetry_events_license_type_time', 'license_id', 'event_type', 'event_timestamp'),
    )


class SystemMetric(Base):
    """
    Stores system performance metrics and infrastructure monitoring data.
    Optimized for time-series analysis and capacity planning.
    """
    __tablename__ = "system_metrics"
    
    # Primary identification
    metric_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Metric identification
    metric_name = Column(String, nullable=False, index=True)  # e.g., "cpu_usage", "memory_usage"
    metric_type = Column(SQLEnum(
        MetricType.COUNTER, MetricType.GAUGE, MetricType.HISTOGRAM,
        MetricType.TIMER, MetricType.DISTRIBUTION, name="metric_type"
    ), nullable=False, index=True)
    
    # Resource identification
    service_name = Column(String, index=True)  # e.g., "api", "worker", "database"
    host_name = Column(String, index=True)
    instance_id = Column(String, index=True)  # Container/instance identifier
    
    # Metric values
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String)  # e.g., "bytes", "seconds", "percentage"
    
    # Timestamps
    metric_timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Aggregation data (for histograms/distributions)
    percentile_50 = Column(Float)
    percentile_90 = Column(Float)
    percentile_95 = Column(Float)
    percentile_99 = Column(Float)
    
    # Context data
    labels = Column(JSON)  # Additional dimensions/tags
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for time-series queries
    __table_args__ = (
        Index('idx_system_metrics_timestamp', 'metric_timestamp'),
        Index('idx_system_metrics_service_time', 'service_name', 'metric_timestamp'),
        Index('idx_system_metrics_name_time', 'metric_name', 'metric_timestamp'),
        Index('idx_system_metrics_type_time', 'metric_type', 'metric_timestamp'),
        Index('idx_system_metrics_host_time', 'host_name', 'metric_timestamp'),
        
        # Composite indexes for monitoring dashboards
        Index('idx_system_metrics_service_name_time', 'service_name', 'metric_name', 'metric_timestamp'),
        Index('idx_system_metrics_instance_time', 'instance_id', 'metric_timestamp'),
    )


class BusinessMetric(Base):
    """
    Stores business-related metrics for KPI tracking and analytics.
    Supports customer lifecycle metrics, revenue tracking, and operational KPIs.
    """
    __tablename__ = "business_metrics"
    
    # Primary identification
    metric_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Metric identification
    metric_name = Column(String, nullable=False, index=True)  # e.g., "daily_active_users", "revenue_per_user"
    metric_category = Column(String, index=True)  # e.g., "user_engagement", "revenue", "retention"
    
    # Attribution
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    license_id = Column(Integer, ForeignKey("licenses.license_id"), index=True)
    organization_id = Column(String, index=True)  # If multi-tenant
    
    # Metric value
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String)  # e.g., "usd", "count", "percentage"
    currency = Column(String)  # For monetary metrics
    
    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    period_type = Column(String, index=True)  # "hourly", "daily", "weekly", "monthly"
    
    # Calculation context
    calculation_method = Column(String, index=True)  # "sum", "avg", "median", "distinct_count"
    
    # Context and dimensions
    dimensions = Column(JSON)  # Additional business context
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Note: Relationships are defined in User and License models to avoid circular imports
    # user = relationship("User")
    # license = relationship("License")
    
    # Indexes for business analytics
    __table_args__ = (
        Index('idx_business_metrics_period', 'period_start', 'period_end'),
        Index('idx_business_metrics_category_period', 'metric_category', 'period_start'),
        Index('idx_business_metrics_name_period', 'metric_name', 'period_start'),
        Index('idx_business_metrics_user_period', 'user_id', 'period_start'),
        Index('idx_business_metrics_license_period', 'license_id', 'period_start'),
        Index('idx_business_metrics_org_period', 'organization_id', 'period_start'),
        Index('idx_business_metrics_period_type', 'period_type', 'period_start'),
        
        # Composite indexes for reporting
        Index('idx_business_metrics_license_category_period', 'license_id', 'metric_category', 'period_start'),
        Index('idx_business_metrics_user_category_period', 'user_id', 'metric_category', 'period_start'),
    )


class AlertRule(Base):
    """
    Stores custom alerting rules for proactive monitoring and notifications.
    Supports complex conditions and multiple notification channels.
    """
    __tablename__ = "alert_rules"
    
    # Primary identification
    rule_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Rule identification
    rule_name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text)
    
    # Rule scope
    license_id = Column(Integer, ForeignKey("licenses.license_id"), index=True)
    organization_id = Column(String, index=True)
    
    # Rule definition
    rule_type = Column(String, index=True)  # "metric_threshold", "event_frequency", "anomaly_detection"
    source_type = Column(String, index=True)  # "system_metric", "business_metric", "telemetry_event"
    
    # Condition definition (JSON-based for flexibility)
    condition_config = Column(JSON, nullable=False)  # {"metric": "cpu_usage", "operator": ">", "threshold": 80}
    
    # Time window for evaluation
    evaluation_window_minutes = Column(Integer, default=5)
    check_interval_seconds = Column(Integer, default=60)
    
    # Severity and status
    severity = Column(SQLEnum(
        SeverityLevel.INFO, SeverityLevel.WARNING, SeverityLevel.ERROR,
        SeverityLevel.CRITICAL, name="severity_level"
    ), nullable=False, index=True)
    
    is_enabled = Column(Boolean, default=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Notification settings
    notification_channels = Column(JSON)  # ["email", "slack", "webhook"]
    notification_config = Column(JSON)  # Channel-specific configuration
    
    # Ownership
    created_by = Column(String, ForeignKey("users.user_id"), index=True)
    updated_by = Column(String, ForeignKey("users.user_id"))
    
    # Metadata
    tags = Column(JSON)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # license = relationship("License")
    # created_by_user = relationship("User", foreign_keys=[created_by])
    # updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_rules_enabled_active', 'is_enabled', 'is_active'),
        Index('idx_alert_rules_license', 'license_id'),
        Index('idx_alert_rules_organization', 'organization_id'),
        Index('idx_alert_rules_type', 'rule_type'),
        Index('idx_alert_rules_severity', 'severity'),
    )


class Alert(Base):
    """
    Stores triggered alerts from monitoring rules.
    Supports alert lifecycle management and resolution tracking.
    """
    __tablename__ = "alerts"
    
    # Primary identification
    alert_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationship to rule
    rule_id = Column(String, ForeignKey("alert_rules.rule_id"), nullable=False, index=True)
    
    # Alert identification
    alert_name = Column(String, nullable=False, index=True)
    severity = Column(SQLEnum(
        SeverityLevel.INFO, SeverityLevel.WARNING, SeverityLevel.ERROR,
        SeverityLevel.CRITICAL, name="severity_level"
    ), nullable=False, index=True)
    
    # Alert content
    title = Column(String, nullable=False)
    description = Column(Text)
    message = Column(Text)
    
    # Context and details
    alert_context = Column(JSON)  # Current state that triggered the alert
    alert_data = Column(JSON)  # Additional data for investigation
    
    # Timeline
    triggered_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, index=True)
    resolved_at = Column(DateTime, index=True)
    
    # Status management
    status = Column(SQLEnum(
        "active", "acknowledged", "resolved", "suppressed", name="alert_status"
    ), default="active", index=True)
    
    # Assignment
    assigned_to = Column(String, ForeignKey("users.user_id"), index=True)
    
    # Impact assessment
    impact_level = Column(String, index=True)  # "low", "medium", "high", "critical"
    affected_services = Column(JSON)  # List of affected services/systems
    
    # Notifications sent
    notifications_sent = Column(JSON, default=list)  # Track which notifications were sent
    notification_attempts = Column(Integer, default=0)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # rule = relationship("AlertRule")
    # assigned_user = relationship("User", foreign_keys=[assigned_to])
    
    # Indexes for alert management
    __table_args__ = (
        Index('idx_alerts_status_time', 'status', 'triggered_at'),
        Index('idx_alerts_severity_time', 'severity', 'triggered_at'),
        Index('idx_alerts_rule_time', 'rule_id', 'triggered_at'),
        Index('idx_alerts_assigned', 'assigned_to', 'status'),
        Index('idx_alerts_license', 'rule_id'),  # Via rule relationship
    )


class Trace(Base):
    """
    Stores distributed tracing data for request tracking and performance analysis.
    Supports microservices architecture tracing and bottleneck identification.
    """
    __tablename__ = "traces"
    
    # Primary identification
    trace_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    span_id = Column(String, nullable=False, index=True)  # Unique per span
    
    # Trace hierarchy
    parent_span_id = Column(String, index=True)  # Parent span ID for nested traces
    root_span_id = Column(String, index=True)  # Root span for the entire trace
    
    # Request identification
    request_id = Column(String, index=True)  # HTTP request ID or correlation ID
    session_id = Column(String, index=True)
    
    # Service information
    service_name = Column(String, nullable=False, index=True)
    operation_name = Column(String, nullable=False, index=True)
    version = Column(String, index=True)
    
    # Attribution
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    license_id = Column(Integer, ForeignKey("licenses.license_id"), index=True)
    
    # Timing information
    start_time = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    end_time = Column(DateTime, index=True)
    duration_ms = Column(Integer, index=True)
    
    # Status and errors
    status_code = Column(Integer, index=True)  # HTTP status code or custom status
    error_message = Column(Text)
    error_stack = Column(Text)
    
    # Request/response data
    http_method = Column(String, index=True)
    http_url = Column(Text)
    http_status_code = Column(Integer, index=True)
    
    # Resource information
    resource_type = Column(String, index=True)  # "database", "external_api", "internal_service"
    resource_name = Column(String, index=True)  # Specific resource accessed
    
    # Tagging and metadata
    tags = Column(JSON)  # Key-value pairs for additional context
    baggage = Column(JSON)  # Cross-span context propagation
    meta_data = Column(JSON)
    
    # Note: Relationships are defined in User and License models to avoid circular imports
    # user = relationship("User")
    # license = relationship("License")
    
    # Indexes for distributed tracing queries
    __table_args__ = (
        Index('idx_traces_trace_id_time', 'trace_id', 'start_time'),
        Index('idx_traces_root_span_time', 'root_span_id', 'start_time'),
        Index('idx_traces_service_time', 'service_name', 'start_time'),
        Index('idx_traces_operation_time', 'operation_name', 'start_time'),
        Index('idx_traces_user_time', 'user_id', 'start_time'),
        Index('idx_traces_license_time', 'license_id', 'start_time'),
        Index('idx_traces_status_code', 'status_code'),
        Index('idx_traces_resource', 'resource_type', 'resource_name'),
        Index('idx_traces_duration', 'duration_ms'),
        Index('idx_traces_error', 'error_message'),
        
        # Composite indexes for performance analysis
        Index('idx_traces_service_operation', 'service_name', 'operation_name', 'start_time'),
        Index('idx_traces_user_service_time', 'user_id', 'service_name', 'start_time'),
    )


# Add relationships to existing models
# Note: These relationships are defined in the respective model files
# to avoid circular import issues
# User.telemetry_events = relationship("TelemetryEvent", back_populates="user", cascade="all, delete-orphan")
# User.business_metrics = relationship("BusinessMetric", back_populates="user", cascade="all, delete-orphan")
# User.created_alert_rules = relationship("AlertRule", foreign_keys=[AlertRule.created_by], back_populates="created_by_user")
# User.updated_alert_rules = relationship("AlertRule", foreign_keys=[AlertRule.updated_by], back_populates="updated_by_user")
# User.assigned_alerts = relationship("Alert", foreign_keys=[Alert.assigned_to], back_populates="assigned_user")
# User.traces = relationship("Trace", back_populates="user", cascade="all, delete-orphan")

# License.telemetry_events = relationship("TelemetryEvent", back_populates="license", cascade="all, delete-orphan")
# License.business_metrics = relationship("BusinessMetric", back_populates="license", cascade="all, delete-orphan")
# License.alert_rules = relationship("AlertRule", back_populates="license", cascade="all, delete-orphan")
# License.traces = relationship("Trace", back_populates="license", cascade="all, delete-orphan")

# AlertRule.alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")