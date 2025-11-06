"""
Redis Cache Configuration

This module provides comprehensive Redis caching configuration for the Fernando platform,
supporting multiple cache types, TTL management, and environment-specific settings.
"""

from pydantic_settings import BaseSettings
from typing import Dict, Optional, List, ClassVar
from datetime import timedelta


class CacheTTLConfig(BaseSettings):
    """TTL configuration for different cache types."""
    
    # Document Processing Caches
    DOCUMENT_HASH_CACHE: int = 86400  # 24 hours - Hash-based cache for identical documents
    OCR_RESULT_CACHE: int = 604800     # 7 days - Cache OCR extraction results
    LLM_EXTRACTION_CACHE: int = 2592000  # 30 days - Cache LLM processing results
    DOCUMENT_METADATA_CACHE: int = 3600  # 1 hour - Cache document metadata
    
    # Session & User Data Caches
    SESSION_CACHE: int = 86400         # 24 hours - User session data
    USER_PREFERENCES_CACHE: int = 3600 # 1 hour - User preferences and settings
    AUTH_TOKEN_CACHE: int = 3600       # 1 hour - Authentication tokens
    PERMISSION_CACHE: int = 1800       # 30 minutes - User permissions
    
    # API Response Caches
    API_RESPONSE_CACHE: int = 300      # 5 minutes - API response cache
    DASHBOARD_DATA_CACHE: int = 600    # 10 minutes - Dashboard data
    REPORT_DATA_CACHE: int = 1800      # 30 minutes - Report data
    REFERENCE_DATA_CACHE: int = 86400  # 24 hours - Reference/master data
    
    # Business Logic Caches
    BILLING_CACHE: int = 3600          # 1 hour - Billing information
    SUBSCRIPTION_CACHE: int = 1800     # 30 minutes - Subscription data
    LICENSE_CACHE: int = 1800          # 30 minutes - License information
    USAGE_STATS_CACHE: int = 1800      # 30 minutes - Usage statistics
    
    # ML & AI Caches
    ML_MODEL_CACHE: int = 43200        # 12 hours - ML model responses
    PREDICTION_CACHE: int = 7200       # 2 hours - ML predictions
    FEATURE_CACHE: int = 1800          # 30 minutes - ML features
    
    class Config:
        env_prefix = "CACHE_TTL_"


class RedisConnectionConfig(BaseSettings):
    """Redis connection configuration."""
    
    # Connection Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Connection Pool Settings
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_CONNECTION_POOL_SIZE: int = 20
    REDIS_CONNECTION_TIMEOUT: int = 30
    REDIS_SOCKET_TIMEOUT: int = 30
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    # SSL & Security
    REDIS_SSL: bool = False
    REDIS_SSL_CA_CERTS: Optional[str] = None
    REDIS_SSL_CERTFILE: Optional[str] = None
    REDIS_SSL_KEYFILE: Optional[str] = None
    REDIS_SSL_VERIFY_MODE: str = "none"
    
    # Sentinel Configuration
    REDIS_SENTINEL_ENABLED: bool = False
    REDIS_SENTINEL_SERVICE_NAME: str = "redis-sentinel"
    REDIS_SENTINEL_HOSTS: str = "localhost:26379"
    
    # Cluster Configuration
    REDIS_CLUSTER_ENABLED: bool = False
    REDIS_CLUSTER_NODES: str = "localhost:7000,localhost:7001"
    
    # Fallback & Testing
    REDIS_URL: Optional[str] = None
    REDIS_ENABLED: bool = True
    REDIS_MOCK_MODE: bool = False  # Use in-memory mock for testing
    
    class Config:
        env_prefix = "REDIS_"


class CachePerformanceConfig(BaseSettings):
    """Cache performance tuning configuration."""
    
    # Memory Management
    CACHE_MAX_MEMORY: str = "1gb"
    CACHE_MAX_MEMORY_POLICY: str = "allkeys-lru"
    CACHE_MEMORY_SAFETY_BUFFER: float = 0.8  # Use 80% of available memory
    
    # Cache Warming
    CACHE_WARMING_ENABLED: bool = True
    CACHE_WARMING_INTERVAL: int = 300  # 5 minutes
    CACHE_WARMING_BATCH_SIZE: int = 100
    
    # Cache Cleanup
    CACHE_CLEANUP_ENABLED: bool = True
    CACHE_CLEANUP_INTERVAL: int = 3600  # 1 hour
    CACHE_CLEANUP_EXPIRED_RATIO: float = 0.1  # Trigger cleanup if >10% expired
    
    # Cache Warming Strategy
    CACHE_WARM_STRATEGY: str = "predictive"  # "predictive", "frequency", "random"
    CACHE_WARM_THRESHOLD_ACCESS: int = 5  # Warm if accessed >5 times
    CACHE_WARM_THRESHOLD_TIME: int = 86400  # Warm if older than 24 hours
    
    # Invalidation Strategy
    CACHE_INVALIDATION_MODE: str = "lazy"  # "lazy", "eager", "hybrid"
    CACHE_INVALIDATION_DELAY: int = 60  # Delay before invalidating (seconds)
    
    # Compression
    CACHE_COMPRESSION_ENABLED: bool = True
    CACHE_COMPRESSION_THRESHOLD: int = 1024  # Compress if >1KB
    CACHE_COMPRESSION_ALGORITHM: str = "gzip"  # "gzip", "lz4", "zstd"
    
    # Monitoring
    CACHE_MONITORING_ENABLED: bool = True
    CACHE_METRICS_INTERVAL: int = 60  # Collect metrics every minute
    CACHE_ALERT_ENABLED: bool = True
    CACHE_SLOW_QUERY_THRESHOLD: float = 1000.0  # ms
    
    class Config:
        env_prefix = "CACHE_"


class CacheSettings(BaseSettings):
    """Main cache settings combining all configurations."""
    
    # Basic Settings
    CACHE_ENABLED: bool = True
    CACHE_NAMESPACE: str = "fernando"
    CACHE_PREFIX_DELIMITER: str = ":"
    
    # Environment Settings
    ENVIRONMENT: str = "development"
    CACHE_ENVIRONMENT_OVERRIDE: bool = False
    
    # Cache Configuration - Use ClassVar to avoid Pydantic field issues
    TTL_CONFIG: ClassVar[CacheTTLConfig] = CacheTTLConfig()
    CONNECTION_CONFIG: ClassVar[RedisConnectionConfig] = RedisConnectionConfig()
    PERFORMANCE_CONFIG: ClassVar[CachePerformanceConfig] = CachePerformanceConfig()
    
    # Multi-tenant Settings
    CACHE_MULTI_TENANT: bool = True
    CACHE_TENANT_ISOLATION: str = "namespace"  # "namespace", "database", "key"
    CACHE_SHARED_BETWEEN_TENANTS: bool = False
    
    # Security Settings
    CACHE_ENCRYPTION_ENABLED: bool = False
    CACHE_ENCRYPTION_KEY: Optional[str] = None
    CACHE_SECURE_SERIALIZATION: bool = True
    
    # Feature Flags
    CACHE_DOCUMENT_HASHING: bool = True
    CACHE_RESULT_SERIALIZATION: bool = True
    CACHE_BATCH_OPERATIONS: bool = True
    CACHE_PIPELINE_OPERATIONS: bool = True
    
    # Debugging & Development
    CACHE_DEBUG_MODE: bool = False
    CACHE_LOG_LEVEL: str = "INFO"
    CACHE_SLOW_LOG_THRESHOLD: float = 100.0  # ms
    
    class Config:
        env_file = ".env"
        env_prefix = "CACHE_"


class CacheNamespaceManager:
    """Manages cache namespaces for different tenants and environments."""
    
    def __init__(self, settings: CacheSettings):
        self.settings = settings
        self.namespace_delimiter = settings.CACHE_PREFIX_DELIMITER
    
    def get_base_namespace(self) -> str:
        """Get the base namespace for the current environment."""
        return f"{self.settings.CACHE_NAMESPACE}{self.namespace_delimiter}{self.settings.ENVIRONMENT}"
    
    def get_tenant_namespace(self, tenant_id: str) -> str:
        """Get tenant-specific namespace."""
        if not self.settings.CACHE_MULTI_TENANT:
            return self.get_base_namespace()
        
        return f"{self.get_base_namespace()}{self.namespace_delimiter}tenant_{tenant_id}"
    
    def get_cache_key(self, namespace: str, key: str) -> str:
        """Generate a namespaced cache key."""
        return f"{namespace}{self.namespace_delimiter}{key}"
    
    def get_document_hash_key(self, tenant_id: str, document_hash: str) -> str:
        """Generate a document hash cache key."""
        namespace = self.get_tenant_namespace(tenant_id)
        return self.get_cache_key(namespace, f"doc_hash:{document_hash}")
    
    def get_ocr_result_key(self, tenant_id: str, document_id: str) -> str:
        """Generate an OCR result cache key."""
        namespace = self.get_tenant_namespace(tenant_id)
        return self.get_cache_key(namespace, f"ocr:{document_id}")
    
    def get_llm_extraction_key(self, tenant_id: str, document_id: str) -> str:
        """Generate an LLM extraction cache key."""
        namespace = self.get_tenant_namespace(tenant_id)
        return self.get_cache_key(namespace, f"llm:{document_id}")
    
    def get_session_key(self, tenant_id: str, session_id: str) -> str:
        """Generate a session cache key."""
        namespace = self.get_tenant_namespace(tenant_id)
        return self.get_cache_key(namespace, f"session:{session_id}")
    
    def get_api_response_key(self, tenant_id: str, endpoint: str, params_hash: str) -> str:
        """Generate an API response cache key."""
        namespace = self.get_tenant_namespace(tenant_id)
        return self.get_cache_key(namespace, f"api:{endpoint}:{params_hash}")


# Global settings instance
cache_settings = CacheSettings()
namespace_manager = CacheNamespaceManager(cache_settings)


# Environment-specific cache configurations
ENVIRONMENT_CONFIGS = {
    "development": {
        "CACHE_ENABLED": True,
        "CACHE_DEBUG_MODE": True,
        "CACHE_TTL_DOCUMENT_HASH_CACHE": 3600,  # 1 hour in dev
        "CACHE_TTL_OCR_RESULT_CACHE": 86400,   # 1 day in dev
        "CACHE_TTL_LLM_EXTRACTION_CACHE": 2592000,  # 30 days in dev
    },
    "staging": {
        "CACHE_ENABLED": True,
        "CACHE_DEBUG_MODE": False,
        "CACHE_TTL_DOCUMENT_HASH_CACHE": 43200,  # 12 hours in staging
        "CACHE_TTL_OCR_RESULT_CACHE": 604800,   # 7 days in staging
        "CACHE_TTL_LLM_EXTRACTION_CACHE": 2592000,  # 30 days in staging
    },
    "production": {
        "CACHE_ENABLED": True,
        "CACHE_DEBUG_MODE": False,
        "CACHE_TTL_DOCUMENT_HASH_CACHE": 86400,  # 24 hours in production
        "CACHE_TTL_OCR_RESULT_CACHE": 604800,   # 7 days in production
        "CACHE_TTL_LLM_EXTRACTION_CACHE": 2592000,  # 30 days in production
        "CACHE_COMPRESSION_ENABLED": True,
        "CACHE_MONITORING_ENABLED": True,
        "CACHE_ALERT_ENABLED": True,
    },
}


def get_cache_ttl(cache_type: str) -> int:
    """Get TTL for a specific cache type."""
    if hasattr(cache_settings.TTL_CONFIG, cache_type.upper()):
        return getattr(cache_settings.TTL_CONFIG, cache_type.upper())
    
    # Default TTL for unknown cache types
    default_ttls = {
        "document": 3600,
        "ocr": 3600,
        "llm": 3600,
        "session": 3600,
        "api": 300,
        "dashboard": 600,
        "report": 1800,
        "reference": 3600,
    }
    
    return default_ttls.get(cache_type, 3600)


def get_cache_config_for_environment(env: str) -> Dict[str, str]:
    """Get cache configuration for a specific environment."""
    return ENVIRONMENT_CONFIGS.get(env, ENVIRONMENT_CONFIGS["development"])


def validate_cache_config() -> Dict[str, bool]:
    """Validate cache configuration and return validation results."""
    validation_results = {}
    
    # Check Redis connectivity
    validation_results["redis_configured"] = bool(
        cache_settings.CONNECTION_CONFIG.REDIS_URL or 
        (cache_settings.CONNECTION_CONFIG.REDIS_HOST and cache_settings.CONNECTION_CONFIG.REDIS_PORT)
    )
    
    # Check TTL configurations
    validation_results["ttl_configured"] = len(cache_settings.TTL_CONFIG.dict()) > 0
    
    # Check performance settings
    validation_results["performance_configured"] = cache_settings.PERFORMANCE_CONFIG.CACHE_MONITORING_ENABLED
    
    # Check namespace settings
    validation_results["namespace_configured"] = bool(cache_settings.CACHE_NAMESPACE)
    
    return validation_results
