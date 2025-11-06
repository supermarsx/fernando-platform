"""
Cache Models

Database models for tracking cache statistics, invalidation rules, and performance metrics.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Float, 
    JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class CacheStatistics(Base):
    """Model for tracking cache statistics and performance metrics."""
    
    __tablename__ = "cache_statistics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_type = Column(String, nullable=False, index=True)  # "document", "ocr", "llm", etc.
    cache_key = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    
    # Hit/Miss Statistics
    hit_count = Column(Integer, default=0, nullable=False)
    miss_count = Column(Integer, default=0, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    
    # Performance Metrics
    avg_response_time_ms = Column(Float, default=0.0)
    min_response_time_ms = Column(Float, default=0.0)
    max_response_time_ms = Column(Float, default=0.0)
    
    # Cache Size Metrics
    cache_size_bytes = Column(Integer, default=0)
    value_size_bytes = Column(Integer, default=0)
    
    # TTL and Expiration
    ttl_seconds = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Status and Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    last_validated = Column(DateTime, default=datetime.utcnow)
    error_count = Column(Integer, default=0)
    
    # Additional Metadata
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invalidation_rules = relationship("CacheInvalidationRule", back_populates="cache_entry")


class CacheInvalidationRule(Base):
    """Model for cache invalidation rules and triggers."""
    
    __tablename__ = "cache_invalidation_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Rule Configuration
    cache_types = Column(JSON, nullable=False)  # ["document", "ocr", "llm"]
    key_patterns = Column(JSON, nullable=False)  # ["doc:*", "ocr:*"]
    
    # Invalidation Triggers
    trigger_events = Column(JSON, nullable=False)  # ["document.updated", "user.logout"]
    trigger_conditions = Column(JSON, nullable=True)  # Conditional logic
    
    # Invalidation Strategy
    invalidation_mode = Column(String, nullable=False, default="lazy")  # "lazy", "eager", "hybrid"
    delay_seconds = Column(Integer, default=60)
    batch_size = Column(Integer, default=100)
    
    # Rule Status
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0)  # Higher priority rules execute first
    
    # Execution Tracking
    last_executed = Column(DateTime, nullable=True)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    cache_entry_id = Column(String, ForeignKey("cache_statistics.id"), nullable=True)
    
    # Relationships
    cache_entry = relationship("CacheStatistics", back_populates="invalidation_rules")


class CachePerformanceMetrics(Base):
    """Model for detailed cache performance monitoring."""
    
    __tablename__ = "cache_performance_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Time-based Metrics
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    time_bucket = Column(String, nullable=False, index=True)  # "1min", "5min", "1hour"
    
    # Cache Operations
    cache_type = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)  # "get", "set", "delete", "clear"
    
    # Performance Data
    response_time_ms = Column(Float, nullable=False)
    bytes_processed = Column(Integer, default=0)
    success = Column(Boolean, default=True, nullable=False)
    
    # Error Information
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional Context
    tenant_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})


class CacheHealthStatus(Base):
    """Model for tracking overall cache system health."""
    
    __tablename__ = "cache_health_status"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Component Status
    component_name = Column(String, nullable=False, index=True)  # "redis", "cache_service"
    status = Column(String, nullable=False)  # "healthy", "degraded", "unhealthy"
    
    # Health Metrics
    availability_percent = Column(Float, default=100.0)
    response_time_avg_ms = Column(Float, default=0.0)
    error_rate_percent = Column(Float, default=0.0)
    
    # Resource Usage
    memory_usage_percent = Column(Float, default=0.0)
    cpu_usage_percent = Column(Float, default=0.0)
    connection_count = Column(Integer, default=0)
    
    # Alert Information
    alert_level = Column(String, nullable=True)  # "info", "warning", "critical"
    alert_message = Column(Text, nullable=True)
    last_alert_at = Column(DateTime, nullable=True)
    
    # Configuration
    configuration_version = Column(String, nullable=True)
    
    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_cache_health_component', 'component_name'),
        Index('idx_cache_health_checked_at', 'checked_at'),
        Index('idx_cache_health_status', 'status'),
    )


class CacheWarmupJob(Base):
    """Model for cache warming jobs and strategies."""
    
    __tablename__ = "cache_warmup_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Job Configuration
    cache_type = Column(String, nullable=False, index=True)
    target_keys = Column(JSON, nullable=True)  # Specific keys to warm
    selection_strategy = Column(String, nullable=False)  # "frequency", "timestamp", "custom"
    
    # Warmup Settings
    batch_size = Column(Integer, default=100)
    max_concurrent = Column(Integer, default=10)
    timeout_seconds = Column(Integer, default=300)
    
    # Scheduling
    schedule_cron = Column(String, nullable=True)  # Cron expression
    interval_minutes = Column(Integer, nullable=True)
    is_recurring = Column(Boolean, default=False)
    
    # Job Status
    status = Column(String, nullable=False, default="pending")  # "pending", "running", "completed", "failed"
    progress_percent = Column(Float, default=0.0)
    
    # Execution Results
    total_keys = Column(Integer, default=0)
    successfully_warmed = Column(Integer, default=0)
    failed_keys = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_warmup_status', 'status'),
        Index('idx_cache_warmup_type', 'cache_type'),
    )


class CacheEventLog(Base):
    """Model for detailed cache event logging and auditing."""
    
    __tablename__ = "cache_event_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Event Information
    event_type = Column(String, nullable=False, index=True)  # "hit", "miss", "set", "delete", "expire"
    cache_type = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)
    
    # Cache Key Information
    cache_key = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    
    # Performance Metrics
    response_time_ms = Column(Float, default=0.0)
    data_size_bytes = Column(Integer, default=0)
    
    # Cache Metadata
    ttl_seconds = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    hit_count = Column(Integer, default=0)
    
    # Event Context
    source = Column(String, nullable=True)  # "api", "service", "background_job"
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    
    # Error Information
    error_occurred = Column(Boolean, default=False)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_cache_event_log_type_time', 'event_type', 'timestamp'),
        Index('idx_cache_event_log_cache_type', 'cache_type'),
        Index('idx_cache_event_log_tenant', 'tenant_id'),
    )


# Database utility functions
def cleanup_expired_cache_statistics(days_old: int = 30) -> int:
    """Clean up expired cache statistics records."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # This would typically be implemented in a service layer
    # Placeholder for database cleanup logic
    return 0


def get_cache_hit_ratio(cache_type: str, days: int = 1) -> float:
    """Calculate cache hit ratio for a specific cache type."""
    # Placeholder for hit ratio calculation
    return 0.85  # 85% hit ratio


def get_top_cache_keys(limit: int = 100) -> List[Dict[str, Any]]:
    """Get top accessed cache keys."""
    # Placeholder for top keys query
    return []


def get_cache_performance_summary(hours: int = 24) -> Dict[str, Any]:
    """Get cache performance summary for the last N hours."""
    # Placeholder for performance summary
    return {
        "total_requests": 10000,
        "hit_ratio": 0.85,
        "avg_response_time": 15.5,
        "error_rate": 0.02,
        "cache_size_mb": 512.3
    }
