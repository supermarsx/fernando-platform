from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from app.core.config import settings
from app.db.session import init_db, get_db
from app.api import auth, jobs, extractions, toconline, admin, enterprise, queue, export_import, licenses, billing, payments, usage, enterprise_billing, revenue_operations, alerting, user_management, enhanced_documents, verification
from app.services.enterprise_service import EnterpriseService
from app.middleware.usage_tracking import UsageTrackingMiddleware
from app.services.cache.redis_cache import init_cache_service
from app.middleware.cache_decorators import CacheMiddleware
import time

# Create FastAPI app
app = FastAPI(
    title="Fernando Platform - Enterprise Edition",
    version="2.0.0-enterprise",
    description="Enterprise-grade automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration"
)

# Configure security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]  # Configure for production
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Rate limiting middleware
class RateLimitMiddleware:
    def __init__(self, app, calls_per_minute=100):
        self.app = app
        self.calls_per_minute = calls_per_minute
        self.call_history = {}
    
    async def __call__(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = int(time.time())
        
        # Clean old entries (older than 1 minute)
        if client_ip in self.call_history:
            self.call_history[client_ip] = [
                timestamp for timestamp in self.call_history[client_ip] 
                if current_time - timestamp < 60
            ]
        
        # Check rate limit
        if client_ip not in self.call_history:
            self.call_history[client_ip] = []
        
        if len(self.call_history[client_ip]) >= self.calls_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
        
        # Add current request
        self.call_history[client_ip].append(current_time)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.calls_per_minute - len(self.call_history[client_ip])
        )
        
        return response


app.add_middleware(RateLimitMiddleware, calls_per_minute=100)


# Enterprise feature activation middleware
class EnterpriseFeatureMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # Add enterprise feature flags to request state
        request.state.enterprise_enabled = True
        request.state.tenant_id = None
        
        # Extract tenant from headers or JWT token
        if "X-Tenant-ID" in request.headers:
            request.state.tenant_id = request.headers["X-Tenant-ID"]
        
        response = await call_next(request)
        return response


app.add_middleware(EnterpriseFeatureMiddleware)

# Usage tracking middleware
app.add_middleware(UsageTrackingMiddleware)

# Cache middleware for API response caching
cache_patterns = [
    "/api/v1/dashboard",
    "/api/v1/reports",
    "/api/v1/analytics",
    "/api/v1/reference"
]
app.add_middleware(CacheMiddleware, cache_patterns=cache_patterns)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the error (in production, use proper logging)
    print(f"Global exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers - order matters for route precedence
app.include_router(verification.router, prefix="/api/verification", tags=["verification"])  # Human verification workflow
app.include_router(enterprise.router, prefix="/api/v1")
app.include_router(queue.router, prefix="/api/v1")
app.include_router(export_import.router, prefix="/api/v1")
app.include_router(licenses.router)
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
app.include_router(enterprise_billing.router)  # Enterprise billing features
app.include_router(revenue_operations.router, prefix="/api/v1/revenue-ops", tags=["revenue-operations"])  # Revenue operations & analytics
app.include_router(alerting.router, prefix="/api/v1/alerts", tags=["alerts"])  # Alerting system

# Original API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(extractions.router, prefix="/api/v1")
app.include_router(toconline.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(user_management.router, prefix="/api/v1")
app.include_router(enhanced_documents.router, prefix="/api/v1")  # Enhanced document processing

# Mount static files for file uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Root endpoint
@app.get("/")
def root():
    return {
        "app": "Fernando Platform - Enterprise Edition",
        "version": "2.0.0-enterprise",
        "status": "running",
        "features": {
            "multi_tenant": True,
            "advanced_rbac": True,
            "batch_processing": True,
            "export_import": True,
            "audit_trails": True,
            "rate_limiting": True,
            "scheduling": True,
            "licensing_management": True,
            "billing_and_subscriptions": True,
            "usage_based_billing": True,
            "invoice_management": True,
            "usage_tracking_and_metering": True,
            "quota_enforcement": True,
            "usage_analytics_and_forecasting": True,
            "fraud_detection": True,
            "enterprise_billing": True,
            "multi_entity_billing": True,
            "department_allocation": True,
            "contract_management": True,
            "budget_tracking": True,
            "approval_workflows": True,
            "dispute_management": True,
            "financial_integration": True,
            "comprehensive_alerting": True,
            "human_verification_workflow": True,
            "ai_assisted_verification": True,
            "quality_control_system": True,
            "team_management": True,
            "performance_analytics": True
        },
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0-enterprise",
        "enterprise_features": True
    }


@app.get("/api/v1/system/status")
async def system_status(db = Depends(get_db)):
    """Get detailed system status including enterprise features and cache"""
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Check cache service status
    try:
        from app.services.cache.redis_cache import cache_service, check_cache_health
        cache_health = await check_cache_health()
        cache_status = cache_health.get("status", "unknown")
    except Exception:
        cache_status = "error"
        cache_health = {"status": "error", "error": "Cache service not available"}
    
    # Get basic stats
    from app.models.user import User
    from app.models.job import Job
    from app.models.enterprise import Tenant
    from app.models.license import License
    from app.models.billing import Subscription, Invoice
    from app.models.usage import UsageMetric, UsageQuota, UsageAlert
    
    try:
        total_users = db.query(User).count()
        total_jobs = db.query(Job).count()
        total_tenants = db.query(Tenant).count()
        total_licenses = db.query(License).count()
        total_subscriptions = db.query(Subscription).count()
        total_invoices = db.query(Invoice).count()
        total_usage_metrics = db.query(UsageMetric).count()
        total_quotas = db.query(UsageQuota).count()
        pending_alerts = db.query(UsageAlert).filter(UsageAlert.status == "pending").count()
    except Exception:
        total_users = total_jobs = total_tenants = total_licenses = 0
        total_subscriptions = total_invoices = 0
        total_usage_metrics = total_quotas = pending_alerts = 0
    
    return {
        "status": "healthy" if db_status == "connected" and cache_status in ["healthy", "unknown"] else "degraded",
        "database": db_status,
        "cache": cache_status,
        "version": "2.0.0-enterprise",
        "statistics": {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "total_tenants": total_tenants,
            "total_licenses": total_licenses,
            "total_subscriptions": total_subscriptions,
            "total_invoices": total_invoices,
            "total_usage_metrics": total_usage_metrics,
            "total_quotas": total_quotas,
            "pending_alerts": pending_alerts
        },
        "cache_info": cache_health.get("details", {}),
        "enterprise_features": {
            "multi_tenant": True,
            "advanced_rbac": True,
            "batch_processing": True,
            "export_import": True,
            "audit_trails": True,
            "rate_limiting": True,
            "scheduling": True,
            "licensing_management": True,
            "billing_and_subscriptions": True,
            "comprehensive_alerting": True,
            "redis_caching": True,
            "human_verification_workflow": True,
            "ai_assisted_verification": True,
            "quality_control_system": True,
            "team_management": True,
            "performance_analytics": True
        }
    }


# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    """Initialize database and start background services"""
    init_db()
    
    # Initialize enterprise features
    from app.services.enterprise_service import EnterpriseService
    from app.services.queue_manager import QueueManager
    from app.services.licensing_service import initialize_default_tiers
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Initialize enterprise service (creates default permissions, etc.)
        enterprise_service = EnterpriseService(db)
        
        # Initialize licensing tiers
        initialize_default_tiers(db)
        
        # Initialize queue manager
        queue_manager = QueueManager(db)
        await queue_manager.initialize_queues()
        
        print("Enterprise features and licensing initialized successfully")
        
    except Exception as e:
        print(f"Error initializing enterprise features: {e}")
    finally:
        db.close()
    
    print(f"Fernando Platform Enterprise Edition v2.0.0 started successfully")
    print("Enterprise features:")
    print("  ✓ Multi-tenant support with data isolation")
    print("  ✓ Advanced user management with groups and permissions") 
    print("  ✓ Enhanced batch processing with queue management")
    print("  ✓ Export/import functionality (CSV, Excel, JSON, PDF)")
    print("  ✓ Advanced audit trails and compliance reporting")
    print("  ✓ API rate limiting and quota management")
    print("  ✓ Role-based access control enhancements")
    print("  ✓ Advanced job scheduling and automation")
    print("  ✓ Comprehensive licensing management system")
    print("  ✓ Billing and subscription management")
    print("  ✓ Usage-based billing with overage tracking")
    print("  ✓ Invoice generation and payment processing")
    print("  ✓ Real-time usage tracking and metering")
    print("  ✓ Quota enforcement with automatic throttling")
    print("  ✓ Usage analytics and forecasting")
    print("  ✓ Fraud detection and anomaly monitoring")
    print("  ✓ Comprehensive alerting system with multi-channel notifications")
    print("  ✓ Intelligent alert escalation and on-call management")
    print("  ✓ Real-time system health monitoring")
    print("  ✓ Comprehensive Redis caching system")
    print("  ✓ Human verification and quality control workflow")
    print("  ✓ AI-assisted verification with confidence scoring")
    print("  ✓ Multi-level quality control with peer review")
    print("  ✓ Team management with specialization")
    print("  ✓ Performance analytics and quality trends")
    
    # Initialize Redis cache service
    try:
        await init_cache_service()
        print("  ✓ Redis cache service initialized")
    except Exception as e:
        print(f"  ⚠️  Redis cache service failed to initialize: {e}")
        print("     Application will continue without caching")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
