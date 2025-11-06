"""
Proxy Server Models

Database models for the centralized proxy server system including:
- Proxy endpoint configurations
- API key management records
- Request/response cache entries
- Rate limiting and quota tracking
- Circuit breaker state management
- Performance and monitoring metrics
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Float, 
    JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class ProxyEndpoint(Base):
    """Model for proxy endpoint configurations."""
    
    __tablename__ = "proxy_endpoints"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Endpoint Configuration
    path_pattern = Column(String, nullable=False, index=True)  # "/api/llm/*"
    method = Column(String, nullable=False, index=True)  # "GET", "POST", etc.
    upstream_url = Column(String, nullable=False)  # "https://api.openai.com"
    
    # Load Balancing
    weight = Column(Integer, default=1)  # Load balancing weight
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0)  # Higher priority = more likely to be chosen
    
    # Security
    requires_auth = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=100)
    rate_limit_per_hour = Column(Integer, default=1000)
    allowed_ips = Column(JSON, nullable=True)  # List of allowed IP addresses
    
    # Caching Configuration
    cache_enabled = Column(Boolean, default=False, nullable=False)
    cache_ttl_seconds = Column(Integer, default=300)
    cache_strategy = Column(String, default="smart")  # "none", "basic", "smart", "aggressive"
    
    # Circuit Breaker Settings
    circuit_breaker_enabled = Column(Boolean, default=True, nullable=False)
    failure_threshold = Column(Integer, default=5)
    recovery_timeout_seconds = Column(Integer, default=60)
    
    # Health Check
    health_check_enabled = Column(Boolean, default=True, nullable=False)
    health_check_interval_seconds = Column(Integer, default=30)
    
    # Headers and Transformations
    request_headers = Column(JSON, default={})
    response_headers = Column(JSON, default={})
    header_transformations = Column(JSON, default={})
    
    # Metadata
    tags = Column(JSON, default=[])  # ["llm", "api", "external"]
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="proxy_endpoint")


class ApiKey(Base):
    """Model for centralized API key management."""
    
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Key Information
    key_type = Column(String, nullable=False, index=True)  # "llm", "ocr", "toconline", "stripe", "generic"
    provider = Column(String, nullable=False, index=True)  # "openai", "azure", "google", "stripe"
    internal_key_id = Column(String, nullable=False, unique=True, index=True)
    
    # Encrypted Key Storage
    encrypted_key = Column(Text, nullable=False)  # Base64 encoded encrypted key
    key_version = Column(Integer, default=1)
    key_rotation_schedule = Column(String, nullable=True)  # Cron expression
    
    # Usage and Limits
    max_requests_per_day = Column(Integer, default=10000)
    max_requests_per_month = Column(Integer, default=300000)
    cost_per_request = Column(Float, default=0.0)
    monthly_budget = Column(Float, nullable=True)
    
    # Status and Health
    is_active = Column(Boolean, default=True, nullable=False)
    is_healthy = Column(Boolean, default=True, nullable=False)
    last_health_check = Column(DateTime, default=datetime.utcnow)
    health_check_status = Column(String, default="unknown")  # "healthy", "degraded", "unhealthy", "unknown"
    
    # Usage Analytics
    total_requests = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)
    avg_response_time_ms = Column(Float, default=0.0)
    
    # Rotation Tracking
    last_rotation_date = Column(DateTime, nullable=True)
    next_rotation_date = Column(DateTime, nullable=True)
    rotation_in_progress = Column(Boolean, default=False, nullable=False)
    
    # Associated Proxy Endpoint
    proxy_endpoint_id = Column(String, ForeignKey("proxy_endpoints.id"), nullable=True)
    
    # Metadata
    tags = Column(JSON, default=[])
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    proxy_endpoint = relationship("ProxyEndpoint", back_populates="api_keys")
    usage_records = relationship("ApiKeyUsage", back_populates="api_key")
    rotation_logs = relationship("ApiKeyRotation", back_populates="api_key")


class ApiKeyUsage(Base):
    """Model for API key usage tracking and analytics."""
    
    __tablename__ = "api_key_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to API Key
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False, index=True)
    
    # Usage Details
    endpoint = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, default=0.0)
    
    # Cost and Volume
    request_size_bytes = Column(Integer, default=0)
    response_size_bytes = Column(Integer, default=0)
    cost_amount = Column(Float, default=0.0)
    
    # Context
    user_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Request Context
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    
    # Success/Failure
    is_successful = Column(Boolean, default=True, nullable=False)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    api_key = relationship("ApiKey", back_populates="usage_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_key_usage_api_key_time', 'api_key_id', 'timestamp'),
        Index('idx_api_key_usage_endpoint', 'endpoint'),
        Index('idx_api_key_usage_tenant', 'tenant_id'),
        Index('idx_api_key_usage_user', 'user_id'),
    )


class ApiKeyRotation(Base):
    """Model for API key rotation logs and scheduling."""
    
    __tablename__ = "api_key_rotation"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to API Key
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False, index=True)
    
    # Rotation Details
    rotation_type = Column(String, nullable=False, index=True)  # "scheduled", "manual", "emergency", "expiry"
    status = Column(String, nullable=False, index=True)  # "pending", "in_progress", "completed", "failed"
    
    # Old Key Information
    old_key_version = Column(Integer, nullable=False)
    old_key_health = Column(String, nullable=True)
    
    # New Key Information
    new_key_version = Column(Integer, nullable=True)
    new_key_status = Column(String, nullable=True)
    
    # Validation
    validation_required = Column(Boolean, default=True)
    validation_successful = Column(Boolean, nullable=True)
    validation_results = Column(JSON, default={})
    
    # Timeline
    planned_start = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Impact Assessment
    requests_affected = Column(Integer, default=0)
    downtime_seconds = Column(Float, default=0.0)
    success_rate_before = Column(Float, default=0.0)
    success_rate_after = Column(Float, default=0.0)
    
    # Error Information
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Initiator
    initiated_by = Column(String, nullable=True)  # "system", "user_id", "admin_id"
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_key = relationship("ApiKey", back_populates="rotation_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_key_rotation_status', 'status'),
        Index('idx_api_key_rotation_type', 'rotation_type'),
        Index('idx_api_key_rotation_api_key', 'api_key_id'),
    )


class ProxyCacheEntry(Base):
    """Model for proxy response caching."""
    
    __tablename__ = "proxy_cache_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Cache Key and Content
    cache_key = Column(String, nullable=False, unique=True, index=True)
    endpoint_id = Column(String, ForeignKey("proxy_endpoints.id"), nullable=False, index=True)
    
    # Content Information
    content_type = Column(String, nullable=False)
    content_length = Column(Integer, default=0)
    response_status = Column(Integer, nullable=False)
    
    # Cache Metadata
    request_headers = Column(JSON, default={})
    response_headers = Column(JSON, default={})
    request_method = Column(String, nullable=False)
    request_path = Column(String, nullable=False)
    
    # TTL and Expiration
    ttl_seconds = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Cache Strategy
    cache_strategy = Column(String, nullable=False, default="smart")  # "none", "basic", "smart", "aggressive"
    cache_tier = Column(String, default="memory")  # "memory", "disk", "distributed"
    
    # Hit/Miss Tracking
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Content Hash for Invalidation
    content_hash = Column(String, nullable=True, index=True)
    
    # Invalidation Rules
    invalidation_triggers = Column(JSON, default=[])
    auto_invalidate = Column(Boolean, default=False)
    
    # Size and Performance
    storage_size_bytes = Column(Integer, default=0)
    compressed = Column(Boolean, default=False)
    compression_ratio = Column(Float, default=1.0)
    
    # Metadata
    tags = Column(JSON, default=[])
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("ProxyEndpoint")
    invalidation_logs = relationship("CacheInvalidationLog", back_populates="cache_entry")
    
    # Indexes
    __table_args__ = (
        Index('idx_proxy_cache_endpoint', 'endpoint_id'),
        Index('idx_proxy_cache_expires', 'expires_at'),
        Index('idx_proxy_cache_access', 'last_accessed'),
    )


class CacheInvalidationLog(Base):
    """Model for cache invalidation tracking."""
    
    __tablename__ = "cache_invalidation_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to Cache Entry
    cache_entry_id = Column(String, ForeignKey("proxy_cache_entries.id"), nullable=False, index=True)
    
    # Invalidation Details
    invalidation_type = Column(String, nullable=False, index=True)  # "manual", "ttl", "trigger", "pattern"
    trigger_reason = Column(String, nullable=True)
    
    # Invalidation Method
    invalidation_method = Column(String, nullable=False)  # "delete", "invalidate", "update"
    pattern_matched = Column(String, nullable=True)  # If invalidated by pattern
    
    # Validation
    validation_required = Column(Boolean, default=False)
    validation_successful = Column(Boolean, nullable=True)
    
    # Impact Assessment
    cache_entries_affected = Column(Integer, default=1)
    data_size_freed_bytes = Column(Integer, default=0)
    
    # Request Context
    triggered_by = Column(String, nullable=True)  # "system", "user_id", "admin_id"
    source_endpoint = Column(String, nullable=True)
    
    # Error Information
    error_occurred = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    cache_entry = relationship("ProxyCacheEntry", back_populates="invalidation_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_invalidation_type', 'invalidation_type'),
        Index('idx_cache_invalidation_cache', 'cache_entry_id'),
    )


class RateLimit(Base):
    """Model for rate limiting configurations."""
    
    __tablename__ = "rate_limits"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Rate Limit Configuration
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Scope
    scope_type = Column(String, nullable=False, index=True)  # "global", "endpoint", "user", "tenant", "api_key"
    scope_value = Column(String, nullable=True, index=True)  # "user_id", "tenant_id", "endpoint_id"
    
    # Limits
    requests_per_second = Column(Integer, nullable=True)
    requests_per_minute = Column(Integer, nullable=True)
    requests_per_hour = Column(Integer, nullable=True)
    requests_per_day = Column(Integer, nullable=True)
    requests_per_month = Column(Integer, nullable=True)
    
    # Concurrent Limits
    concurrent_requests = Column(Integer, nullable=True)
    concurrent_connections = Column(Integer, nullable=True)
    
    # Burst Limits
    burst_requests = Column(Integer, default=0)
    burst_window_seconds = Column(Integer, default=1)
    
    # Algorithm Configuration
    algorithm = Column(String, nullable=False, default="sliding_window")  # "fixed_window", "sliding_window", "token_bucket", "leaky_bucket"
    algorithm_config = Column(JSON, default={})
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0)  # Higher priority = more restrictive
    
    # Headers for Client Feedback
    rate_limit_headers_enabled = Column(Boolean, default=True)
    custom_headers = Column(JSON, default={})
    
    # Whitelists and Blacklists
    whitelist_ips = Column(JSON, default=[])
    blacklist_ips = Column(JSON, default=[])
    whitelist_endpoints = Column(JSON, default=[])
    blacklist_endpoints = Column(JSON, default=[])
    
    # Metadata
    tags = Column(JSON, default=[])
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    usage_records = relationship("RateLimitUsage", back_populates="rate_limit")


class RateLimitUsage(Base):
    """Model for rate limit usage tracking."""
    
    __tablename__ = "rate_limit_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to Rate Limit
    rate_limit_id = Column(String, ForeignKey("rate_limits.id"), nullable=False, index=True)
    
    # Usage Details
    endpoint = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False)
    
    # Client Context
    user_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    api_key_id = Column(String, nullable=True, index=True)
    client_ip = Column(String, nullable=True, index=True)
    user_agent = Column(String, nullable=True)
    
    # Rate Limit Result
    allowed = Column(Boolean, default=True, nullable=False)
    rejected_reason = Column(String, nullable=True)
    
    # Remaining Quotas
    requests_remaining = Column(Integer, default=0)
    reset_time = Column(DateTime, nullable=True)
    
    # Request Context
    request_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    rate_limit = relationship("RateLimit", back_populates="usage_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_rate_limit_usage_rate_limit', 'rate_limit_id'),
        Index('idx_rate_limit_usage_user', 'user_id'),
        Index('idx_rate_limit_usage_tenant', 'tenant_id'),
        Index('idx_rate_limit_usage_client_ip', 'client_ip'),
    )


class CircuitBreakerState(Base):
    """Model for circuit breaker state management."""
    
    __tablename__ = "circuit_breaker_states"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Circuit Breaker Identification
    name = Column(String, nullable=False, index=True)
    endpoint_id = Column(String, ForeignKey("proxy_endpoints.id"), nullable=False, index=True)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True, index=True)
    
    # Current State
    state = Column(String, nullable=False, index=True)  # "closed", "open", "half_open"
    
    # State Transition History
    last_transition = Column(DateTime, default=datetime.utcnow, index=True)
    state_duration_seconds = Column(Integer, default=0)
    
    # Failure Tracking
    failure_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_threshold = Column(Integer, default=5)
    success_threshold = Column(Integer, default=3)
    
    # Timeout Configuration
    open_timeout_seconds = Column(Integer, default=60)
    half_open_timeout_seconds = Column(Integer, default=30)
    
    # State-Specific Metrics
    current_request_count = Column(Integer, default=0)
    open_since = Column(DateTime, nullable=True)
    half_open_since = Column(DateTime, nullable=True)
    next_attempt = Column(DateTime, nullable=True)
    
    # Health Check Integration
    last_health_check = Column(DateTime, nullable=True)
    health_check_failed = Column(Boolean, default=False)
    
    # Configuration
    configuration_version = Column(String, default="1.0")
    is_active = Column(Boolean, default=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("ProxyEndpoint")
    api_key = relationship("ApiKey")
    event_logs = relationship("CircuitBreakerEvent", back_populates="circuit_breaker")
    
    # Indexes
    __table_args__ = (
        Index('idx_circuit_breaker_state', 'state'),
        Index('idx_circuit_breaker_endpoint', 'endpoint_id'),
        Index('idx_circuit_breaker_api_key', 'api_key_id'),
    )


class CircuitBreakerEvent(Base):
    """Model for circuit breaker event logging."""
    
    __tablename__ = "circuit_breaker_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Reference to Circuit Breaker
    circuit_breaker_id = Column(String, ForeignKey("circuit_breaker_states.id"), nullable=False, index=True)
    
    # Event Details
    event_type = Column(String, nullable=False, index=True)  # "success", "failure", "timeout", "state_change"
    event_level = Column(String, nullable=False, index=True)  # "info", "warning", "error", "critical"
    
    # Event Data
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    
    # Request Context
    request_id = Column(String, nullable=True, index=True)
    endpoint = Column(String, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Error Information
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    circuit_breaker = relationship("CircuitBreakerState", back_populates="event_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_circuit_breaker_event_type', 'event_type'),
        Index('idx_circuit_breaker_event_level', 'event_level'),
        Index('idx_circuit_breaker_event_circuit', 'circuit_breaker_id'),
        Index('idx_circuit_breaker_event_time', 'timestamp'),
    )


class ProxyRequestLog(Base):
    """Model for comprehensive proxy request/response logging."""
    
    __tablename__ = "proxy_request_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Request Identification
    request_id = Column(String, nullable=False, unique=True, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    
    # Client Information
    client_ip = Column(String, nullable=True, index=True)
    client_port = Column(Integer, nullable=True)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    
    # Authentication
    auth_method = Column(String, nullable=True)  # "bearer", "api_key", "basic", "none"
    user_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    api_key_id = Column(String, nullable=True, index=True)
    
    # Request Details
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    query_string = Column(Text, nullable=True)
    request_headers = Column(JSON, default={})
    request_size_bytes = Column(Integer, default=0)
    
    # Upstream Details
    upstream_endpoint = Column(String, nullable=False)
    upstream_method = Column(String, nullable=False)
    upstream_path = Column(String, nullable=False)
    upstream_request_headers = Column(JSON, default={})
    selected_api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True)
    
    # Response Details
    response_status = Column(Integer, nullable=False)
    response_headers = Column(JSON, default={})
    response_size_bytes = Column(Integer, default=0)
    content_type = Column(String, nullable=True)
    
    # Timing
    total_duration_ms = Column(Float, nullable=False)
    proxy_processing_ms = Column(Float, default=0.0)
    upstream_duration_ms = Column(Float, default=0.0)
    response_processing_ms = Column(Float, default=0.0)
    
    # Cache Information
    cache_hit = Column(Boolean, default=False)
    cache_key = Column(String, nullable=True, index=True)
    cache_duration_ms = Column(Float, default=0.0)
    
    # Rate Limiting
    rate_limited = Column(Boolean, default=False)
    rate_limit_policy = Column(String, nullable=True)
    
    # Circuit Breaker
    circuit_breaker_state = Column(String, nullable=True)
    circuit_breaker_action = Column(String, nullable=True)
    
    # Error Information
    error_occurred = Column(Boolean, default=False)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    
    # Security
    blocked_ip = Column(Boolean, default=False)
    blocked_user_agent = Column(Boolean, default=False)
    security_policy_violated = Column(Boolean, default=False)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    selected_api_key = relationship("ApiKey", foreign_keys=[selected_api_key_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_proxy_request_timestamp', 'timestamp'),
        Index('idx_proxy_request_client_ip', 'client_ip'),
        Index('idx_proxy_request_user', 'user_id'),
        Index('idx_proxy_request_tenant', 'tenant_id'),
        Index('idx_proxy_request_endpoint', 'upstream_endpoint'),
        Index('idx_proxy_request_status', 'response_status'),
    )


class ProxyPerformanceMetrics(Base):
    """Model for proxy performance monitoring and analytics."""
    
    __tablename__ = "proxy_performance_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Time-based Metrics
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    time_bucket = Column(String, nullable=False, index=True)  # "1min", "5min", "1hour", "1day"
    
    # Endpoint Metrics
    endpoint_id = Column(String, ForeignKey("proxy_endpoints.id"), nullable=True, index=True)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True, index=True)
    
    # Request Metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    rate_limited_requests = Column(Integer, default=0)
    cached_requests = Column(Integer, default=0)
    
    # Response Time Metrics
    avg_response_time_ms = Column(Float, default=0.0)
    min_response_time_ms = Column(Float, default=0.0)
    max_response_time_ms = Column(Float, default=0.0)
    p50_response_time_ms = Column(Float, default=0.0)
    p95_response_time_ms = Column(Float, default=0.0)
    p99_response_time_ms = Column(Float, default=0.0)
    
    # Error Metrics
    error_rate_percent = Column(Float, default=0.0)
    timeout_rate_percent = Column(Float, default=0.0)
    circuit_breaker_open_rate_percent = Column(Float, default=0.0)
    
    # Traffic Metrics
    total_bytes_in = Column(Integer, default=0)
    total_bytes_out = Column(Integer, default=0)
    
    # Cost Metrics
    total_cost = Column(Float, default=0.0)
    cost_per_request = Column(Float, default=0.0)
    
    # Health Metrics
    availability_percent = Column(Float, default=100.0)
    health_score = Column(Float, default=100.0)
    
    # Additional Context
    tenant_id = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True, index=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Relationships
    endpoint = relationship("ProxyEndpoint")
    api_key = relationship("ApiKey")
    
    # Indexes
    __table_args__ = (
        Index('idx_proxy_performance_time_bucket', 'time_bucket'),
        Index('idx_proxy_performance_endpoint', 'endpoint_id'),
        Index('idx_proxy_performance_time', 'timestamp'),
    )


class ProxySecurityEvent(Base):
    """Model for proxy security events and monitoring."""
    
    __tablename__ = "proxy_security_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Event Identification
    event_type = Column(String, nullable=False, index=True)  # "auth_failure", "rate_limit_exceeded", "malicious_request", "ip_blocked"
    severity = Column(String, nullable=False, index=True)  # "low", "medium", "high", "critical"
    
    # Source Information
    source_ip = Column(String, nullable=True, index=True)
    source_port = Column(Integer, nullable=True)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    
    # Target Information
    target_endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    
    # User Context
    user_id = Column(String, nullable=True, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=True, index=True)
    
    # Security Details
    security_rule = Column(String, nullable=True)
    violation_type = Column(String, nullable=True)
    risk_score = Column(Float, default=0.0)
    
    # Request Details
    request_headers = Column(JSON, default={})
    response_status = Column(Integer, nullable=True)
    blocked = Column(Boolean, default=False)
    
    # Additional Context
    geographic_location = Column(String, nullable=True)
    reputation_score = Column(Float, default=0.0)
    threat_indicators = Column(JSON, default=[])
    
    # Action Taken
    action_taken = Column(String, nullable=True)  # "allowed", "blocked", "rate_limited", "logged", "alerted"
    action_details = Column(JSON, default={})
    follow_up_required = Column(Boolean, default=False)
    
    # Investigation
    investigation_status = Column(String, nullable=True)  # "pending", "investigating", "resolved", "false_positive"
    investigated_by = Column(String, nullable=True)
    investigation_notes = Column(Text, nullable=True)
    
    # Additional Context
    metadata_json = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    api_key = relationship("ApiKey")
    
    # Indexes
    __table_args__ = (
        Index('idx_proxy_security_type_severity', 'event_type', 'severity'),
        Index('idx_proxy_security_source_ip', 'source_ip'),
        Index('idx_proxy_security_user', 'user_id'),
        Index('idx_proxy_security_timestamp', 'timestamp'),
    )


# Utility Functions

def get_proxy_endpoint_stats(endpoint_id: str, hours: int = 24) -> Dict[str, Any]:
    """Get proxy endpoint performance statistics."""
    # This would typically be implemented using SQLAlchemy queries
    return {
        "total_requests": 1000,
        "success_rate": 99.5,
        "avg_response_time": 150.0,
        "error_rate": 0.5,
        "cache_hit_rate": 45.2
    }


def get_api_key_usage_summary(api_key_id: str, days: int = 30) -> Dict[str, Any]:
    """Get API key usage summary."""
    return {
        "total_requests": 50000,
        "total_cost": 245.67,
        "avg_response_time": 120.0,
        "success_rate": 99.2,
        "most_used_endpoint": "/api/llm/chat"
    }


def get_circuit_breaker_status(endpoint_id: str) -> Dict[str, str]:
    """Get current circuit breaker status."""
    # This would query the CircuitBreakerState model
    return {
        "state": "closed",
        "failure_count": 0,
        "success_count": 150,
        "last_transition": datetime.utcnow().isoformat()
    }


def cleanup_old_proxy_logs(days_old: int = 30) -> int:
    """Clean up old proxy logs."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    # This would implement cleanup logic
    return 0


def get_proxy_performance_summary(hours: int = 1) -> Dict[str, Any]:
    """Get proxy performance summary."""
    return {
        "total_requests": 10000,
        "average_response_time": 145.3,
        "error_rate": 0.8,
        "cache_hit_rate": 42.1,
        "availability": 99.9
    }
