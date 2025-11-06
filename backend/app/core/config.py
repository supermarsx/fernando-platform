from pydantic_settings import BaseSettings
from typing import Optional
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Fernando"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./accounting_automation.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File Upload
    UPLOAD_DIR: str = "./uploads/documents"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: Optional[str] = '["pdf", "jpg", "jpeg", "png", "tiff"]'
    
    @property
    def allowed_extensions_set(self) -> set:
        """Convert ALLOWED_EXTENSIONS string to set"""
        try:
            if isinstance(self.ALLOWED_EXTENSIONS, str):
                return set(json.loads(self.ALLOWED_EXTENSIONS))
            elif isinstance(self.ALLOWED_EXTENSIONS, set):
                return self.ALLOWED_EXTENSIONS
            else:
                return {".pdf", ".jpg", ".jpeg", ".png", ".tiff"}
        except (json.JSONDecodeError, TypeError):
            return {".pdf", ".jpg", ".jpeg", ".png", ".tiff"}
    
    # Enhanced Document Processing
    ENHANCED_PROCESSING_ENABLED: bool = True
    DOCUMENT_VALIDATION_ENABLED: bool = True
    PREVIEW_GENERATION_ENABLED: bool = True
    FORMAT_CONVERSION_ENABLED: bool = True
    
    # Document Format Limits
    MAX_PDF_PAGES: int = 200
    MAX_TIFF_PAGES: int = 500
    MAX_PDF_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_TIFF_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_IMAGE_SIZE: int = 25 * 1024 * 1024  # 25MB
    
    # Processing Settings
    DEFAULT_PROCESSING_QUALITY: str = "medium"  # fast, medium, high
    DEFAULT_DPI: int = 300
    MAX_PROCESSING_TIME: int = 300  # 5 minutes
    CONVERSION_TIMEOUT: int = 60  # 1 minute
    
    # Cache Settings
    PROCESSING_CACHE_ENABLED: bool = True
    CACHE_EXPIRY_HOURS: int = 24
    PREVIEW_CACHE_ENABLED: bool = True
    
    # Format Support by License Tier
    BASIC_FORMATS: set = {".pdf", ".jpg", ".jpeg", ".png"}
    PROFESSIONAL_FORMATS: set = {".pdf", ".jpg", ".jpeg", ".png", ".tiff"}
    ENTERPRISE_FORMATS: set = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    
    # Processing Performance
    PARALLEL_PROCESSING_ENABLED: bool = True
    MAX_CONCURRENT_PROCESSES: int = 4
    BACKGROUND_PROCESSING_ENABLED: bool = True
    
    # Quality vs Speed Trade-offs
    FAST_QUALITY_DPI: int = 150
    MEDIUM_QUALITY_DPI: int = 200
    HIGH_QUALITY_DPI: int = 300
    
    # Security Settings
    ENABLE_SECURITY_SCANNING: bool = True
    SCAN_SUSPICIOUS_PATTERNS: bool = True
    BLOCK_DANGEROUS_FILES: bool = True
    VALIDATION_LEVEL: str = "standard"  # basic, standard, comprehensive
    
    # Mock Services (set to True to use real APIs when available)
    USE_REAL_OCR: bool = False
    USE_REAL_LLM: bool = False
    USE_REAL_TOCONLINE: bool = False
    
    # External API Keys (optional)
    OPENAI_API_KEY: Optional[str] = None
    TOCONLINE_CLIENT_ID: Optional[str] = None
    TOCONLINE_CLIENT_SECRET: Optional[str] = None
    
    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # PayPal Configuration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # "sandbox" or "live"
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    
    # Cryptocurrency Payment Configuration
    COINBASE_COMMERCE_API_KEY: Optional[str] = None
    COINBASE_COMMERCE_WEBHOOK_SECRET: Optional[str] = None
    CRYPTO_PAYMENT_ENABLED: bool = False
    
    # Payment Security
    FRAUD_DETECTION_ENABLED: bool = True
    MAX_PAYMENT_ATTEMPTS_PER_DAY: int = 5
    MAX_PAYMENT_AMOUNT_WITHOUT_VERIFICATION: float = 1000.0
    PAYMENT_VELOCITY_CHECK_ENABLED: bool = True
    
    # Dunning Management
    DUNNING_ENABLED: bool = True
    DUNNING_RETRY_ATTEMPTS: int = 3
    DUNNING_RETRY_DELAYS_DAYS: str = "3,7,14"  # Comma-separated days
    DUNNING_EMAIL_ENABLED: bool = True
    
    # SEPA/ACH Configuration
    SEPA_ENABLED: bool = True
    ACH_ENABLED: bool = True
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Fernando Platform"
    
    # SendGrid (alternative to SMTP)
    SENDGRID_API_KEY: Optional[str] = None
    
    # Email Settings
    SEND_EMAILS: bool = True
    EMAIL_NOTIFICATIONS_ENABLED: bool = True
    
    # Telemetry and Observability Configuration
    TELEMETRY_ENABLED: bool = True
    TELEMETRY_VERBOSE: bool = False
    
    # Metrics Collection
    METRICS_ENABLED: bool = True
    METRICS_MAX_DATA_POINTS: int = 10000
    METRICS_RETENTION_HOURS: int = 24
    METRICS_COLLECTION_INTERVAL: int = 30  # seconds
    
    # Event Tracking
    EVENTS_ENABLED: bool = True
    EVENTS_MAX_EVENTS: int = 50000
    EVENTS_RETENTION_HOURS: int = 168  # 7 days
    EVENTS_VERBOSE_LOGGING: bool = False
    
    # Performance Monitoring
    PERFORMANCE_MONITORING_ENABLED: bool = True
    PERFORMANCE_MAX_DATA_POINTS: int = 10000
    PERFORMANCE_THRESHOLD_CHECK_INTERVAL: int = 30  # seconds
    PERFORMANCE_SLOW_QUERY_THRESHOLD: float = 1000.0  # ms
    PERFORMANCE_SLOW_API_THRESHOLD: float = 2000.0  # ms
    
    # Distributed Tracing
    DISTRIBUTED_TRACING_ENABLED: bool = True
    TRACING_MAX_TRACES: int = 10000
    TRACING_MAX_SPANS_PER_TRACE: int = 1000
    TRACING_SAMPLING_RATE: float = 1.0  # Sample all traces by default
    TRACING_SERVICE_NAME: str = "fernando"
    
    # Alert Management
    ALERTS_ENABLED: bool = True
    ALERTS_MAX_ALERTS: int = 1000
    ALERTS_CHECK_INTERVAL: int = 30  # seconds
    ALERTS_EMAIL_NOTIFICATIONS: bool = True
    ALERTS_SLACK_NOTIFICATIONS: bool = False
    
    # External Monitoring Integrations
    PROMETHEUS_ENABLED: bool = False
    PROMETHEUS_PORT: int = 9090
    JAEGER_ENABLED: bool = False
    JAEGER_ENDPOINT: Optional[str] = None
    DATADOG_ENABLED: bool = False
    DATADOG_API_KEY: Optional[str] = None
    NEW_RELIC_ENABLED: bool = False
    NEW_RELIC_LICENSE_KEY: Optional[str] = None
    
    # Business Metrics
    BUSINESS_METRICS_ENABLED: bool = True
    REVENUE_TRACKING_ENABLED: bool = True
    USER_ACTIVITY_TRACKING_ENABLED: bool = True
    FEATURE_USAGE_TRACKING_ENABLED: bool = True
    
    # Cost and Billing Metrics
    BILLING_METRICS_ENABLED: bool = True
    PAYMENT_SUCCESS_RATE_TRACKING: bool = True
    LICENSE_USAGE_TRACKING: bool = True
    COST_ALLOCATION_TRACKING: bool = True
    
    # Proxy Server Configuration
    PROXY_ENABLED: bool = True
    PROXY_FALLBACK_ENABLED: bool = True
    PROXY_TIMEOUT: int = 30
    PROXY_MAX_RETRIES: int = 3
    
    # LLM Proxy Configuration
    LLM_PROXY_ENDPOINT: str = "http://localhost:8000"
    LLM_PROXY_ENABLED: bool = True
    
    # OCR Proxy Configuration
    OCR_PROXY_ENDPOINT: str = "http://localhost:8001"
    OCR_PROXY_ENABLED: bool = True
    
    # ToConline Proxy Configuration
    TOCONLINE_PROXY_ENDPOINT: str = "http://localhost:8002"
    TOCONLINE_PROXY_ENABLED: bool = True
    
    # Stripe Proxy Configuration
    STRIPE_PROXY_ENDPOINT: str = "http://localhost:8003"
    STRIPE_PROXY_ENABLED: bool = True
    
    # PayPal Proxy Configuration
    PAYPAL_PROXY_ENDPOINT: str = "http://localhost:8004"
    PAYPAL_PROXY_ENABLED: bool = True
    
    # Coinbase Commerce Proxy Configuration
    COINBASE_PROXY_ENDPOINT: str = "http://localhost:8005"
    COINBASE_PROXY_ENABLED: bool = True
    
    # OpenAI Proxy Configuration
    OPENAI_PROXY_ENDPOINT: str = "http://localhost:8006"
    OPENAI_PROXY_ENABLED: bool = True
    
    # Proxy Security Configuration
    PROXY_API_KEY_HEADER: str = "X-API-Key"
    PROXY_AUTH_TYPE: str = "bearer"
    PROXY_ENCRYPTION_ENABLED: bool = True
    PROXY_REQUEST_SIGNING_ENABLED: bool = False
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 60
    CIRCUIT_BREAKER_MONITOR_WINDOW: int = 300
    
    class Config:
        env_file = ".env"


settings = Settings()
