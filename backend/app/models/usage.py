"""
Usage Tracking & Metering Models

This module defines comprehensive usage tracking models for real-time monitoring,
analytics, forecasting, and fraud detection.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.session import Base


class UsageMetricType(str, enum.Enum):
    """Types of usage metrics tracked"""
    DOCUMENT_PROCESSING = "document_processing"
    DOCUMENT_PAGES = "document_pages"
    API_CALLS = "api_calls"
    STORAGE_USAGE = "storage_usage"
    USER_SESSIONS = "user_sessions"
    BATCH_OPERATIONS = "batch_operations"
    EXPORT_OPERATIONS = "export_operations"
    OCR_OPERATIONS = "ocr_operations"
    LLM_OPERATIONS = "llm_operations"
    DATABASE_QUERIES = "database_queries"
    BANDWIDTH_USAGE = "bandwidth_usage"


class UsageAlertType(str, enum.Enum):
    """Types of usage alerts"""
    APPROACHING_LIMIT = "approaching_limit"  # 80% of quota
    SOFT_LIMIT_REACHED = "soft_limit_reached"  # 90% of quota
    HARD_LIMIT_REACHED = "hard_limit_reached"  # 100% of quota
    OVERAGE_USAGE = "overage_usage"  # Over 100%
    UNUSUAL_PATTERN = "unusual_pattern"  # Fraud detection
    QUOTA_RESET = "quota_reset"  # Monthly reset notification


class UsageAlertStatus(str, enum.Enum):
    """Status of usage alerts"""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class UsageMetric(Base):
    """
    Real-time usage metrics aggregated per time window
    """
    __tablename__ = "usage_metrics"
    __table_args__ = (
        Index('idx_usage_metrics_user_type_time', 'user_id', 'metric_type', 'timestamp'),
        Index('idx_usage_metrics_subscription_time', 'subscription_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'))  # For multi-tenant
    
    # Metric details
    metric_type = Column(String(50), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    unit = Column(String(20))  # documents, pages, MB, calls, etc.
    
    # Time window
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    window_type = Column(String(20), default="hourly")  # hourly, daily, monthly
    
    # Context
    resource_id = Column(String(100))  # Reference to specific resource (document_id, job_id, etc.)
    endpoint = Column(String(200))  # API endpoint if applicable
    operation = Column(String(100))  # Specific operation performed
    
    # Performance metrics
    response_time_ms = Column(Integer)
    error_occurred = Column(Boolean, default=False)
    error_code = Column(String(50))
    
    # Metadata
    meta_data = Column(JSON)  # Additional context (file_type, file_size, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageQuota(Base):
    """
    Usage quotas and limits per subscription/user
    """
    __tablename__ = "usage_quotas"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    
    # Quota definition
    metric_type = Column(String(50), nullable=False)
    quota_limit = Column(Float, nullable=False)  # Maximum allowed
    unit = Column(String(20))
    
    # Current usage
    current_usage = Column(Float, default=0, nullable=False)
    usage_percentage = Column(Float, default=0)  # Calculated field
    
    # Overage handling
    allow_overage = Column(Boolean, default=False)
    overage_limit = Column(Float)  # Maximum overage allowed
    overage_rate = Column(Float)  # Price per unit over quota
    current_overage = Column(Float, default=0)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    reset_schedule = Column(String(20), default="monthly")  # monthly, quarterly, annually
    last_reset_at = Column(DateTime)
    next_reset_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_exceeded = Column(Boolean, default=False)
    exceeded_at = Column(DateTime)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alerts = relationship("UsageAlert", back_populates="quota", cascade="all, delete-orphan")


class UsageAggregation(Base):
    """
    Pre-aggregated usage data for analytics and reporting
    """
    __tablename__ = "usage_aggregations"
    __table_args__ = (
        Index('idx_usage_agg_user_metric_date', 'user_id', 'metric_type', 'aggregation_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    organization_id = Column(Integer, ForeignKey('users.user_id'))
    
    # Aggregation details
    metric_type = Column(String(50), nullable=False)
    aggregation_type = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly
    aggregation_date = Column(DateTime, nullable=False, index=True)
    
    # Aggregated values
    total_value = Column(Float, nullable=False)
    average_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    count = Column(Integer, default=0)
    
    # Unit
    unit = Column(String(20))
    
    # Trend indicators
    previous_period_value = Column(Float)
    change_percentage = Column(Float)
    trend = Column(String(20))  # increasing, decreasing, stable
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageAlert(Base):
    """
    Usage alerts for quota limits and unusual patterns
    """
    __tablename__ = "usage_alerts"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    quota_id = Column(Integer, ForeignKey('usage_quotas.id'))
    
    # Alert details
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Context
    metric_type = Column(String(50))
    current_value = Column(Float)
    threshold_value = Column(Float)
    quota_percentage = Column(Float)
    
    # Status
    status = Column(String(20), default="pending")
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(Integer, ForeignKey('users.user_id'))
    resolved_at = Column(DateTime)
    
    # Actions taken
    action_taken = Column(String(100))  # throttled, blocked, charged_overage, etc.
    notification_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quota = relationship("UsageQuota", back_populates="alerts")


class UsageForecast(Base):
    """
    Usage forecasting data for predictive analytics
    """
    __tablename__ = "usage_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    
    # Forecast details
    metric_type = Column(String(50), nullable=False)
    forecast_date = Column(DateTime, nullable=False, index=True)
    forecast_horizon_days = Column(Integer, default=30)  # How far ahead
    
    # Predicted values
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float)  # Lower bound of confidence interval
    confidence_upper = Column(Float)  # Upper bound of confidence interval
    confidence_level = Column(Float, default=0.95)  # 95% confidence
    
    # Model information
    model_type = Column(String(50))  # linear_regression, arima, prophet, etc.
    model_accuracy = Column(Float)  # R-squared or similar metric
    
    # Historical data used
    training_data_points = Column(Integer)
    training_period_start = Column(DateTime)
    training_period_end = Column(DateTime)
    
    # Predictions
    will_exceed_quota = Column(Boolean, default=False)
    expected_overage = Column(Float, default=0)
    estimated_overage_cost = Column(Float)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageAnomaly(Base):
    """
    Detected usage anomalies for fraud detection
    """
    __tablename__ = "usage_anomalies"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    
    # Anomaly details
    anomaly_type = Column(String(50), nullable=False)  # spike, unusual_pattern, velocity, etc.
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    confidence_score = Column(Float, nullable=False)  # 0-1, how confident we are
    
    # Detection
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    detection_method = Column(String(50))  # statistical, ml, rule_based
    
    # Context
    metric_type = Column(String(50))
    observed_value = Column(Float)
    expected_value = Column(Float)
    deviation_percentage = Column(Float)
    
    # Pattern details
    pattern_description = Column(Text)
    time_window_start = Column(DateTime)
    time_window_end = Column(DateTime)
    
    # Risk assessment
    risk_score = Column(Integer, default=0)  # 0-100
    is_fraud_suspect = Column(Boolean, default=False)
    requires_review = Column(Boolean, default=False)
    
    # Response
    status = Column(String(20), default="detected")  # detected, investigating, resolved, false_positive
    investigated_at = Column(DateTime)
    investigated_by = Column(Integer, ForeignKey('users.user_id'))
    resolution = Column(Text)
    action_taken = Column(String(100))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageReport(Base):
    """
    Generated usage reports for export and analysis
    """
    __tablename__ = "usage_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    generated_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    # Report details
    report_type = Column(String(50), nullable=False)  # summary, detailed, forecast, anomaly
    report_format = Column(String(20), default="pdf")  # pdf, csv, json, excel
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Filters
    metric_types = Column(JSON)  # Array of metric types included
    filters = Column(JSON)  # Additional filters applied
    
    # File information
    file_path = Column(String(500))
    file_size_bytes = Column(Integer)
    file_url = Column(String(500))
    
    # Status
    status = Column(String(20), default="generating")  # generating, completed, failed
    generated_at = Column(DateTime)
    expires_at = Column(DateTime)  # When file will be deleted
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime)
    
    # Summary statistics (cached for quick access)
    total_documents_processed = Column(Integer)
    total_api_calls = Column(Integer)
    total_storage_gb = Column(Float)
    total_overage_charges = Column(Float)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageThreshold(Base):
    """
    Configurable usage thresholds for alerts
    """
    __tablename__ = "usage_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'))
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    
    # Threshold details
    metric_type = Column(String(50), nullable=False)
    threshold_type = Column(String(50), nullable=False)  # percentage, absolute, rate
    threshold_value = Column(Float, nullable=False)
    
    # Alert configuration
    alert_enabled = Column(Boolean, default=True)
    alert_severity = Column(String(20), default="medium")
    notification_channels = Column(JSON)  # [email, sms, webhook, etc.]
    
    # Cooldown to prevent alert spam
    cooldown_minutes = Column(Integer, default=60)
    last_triggered_at = Column(DateTime)
    
    # Actions
    auto_action = Column(String(50))  # throttle, block, upgrade_suggestion, etc.
    custom_message = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
