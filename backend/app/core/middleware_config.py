"""
Middleware configuration and setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.middleware.usage_tracking import UsageTrackingMiddleware
from app.middleware.cache_decorators import CacheMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware
from app.core.config import settings

def setup_middleware(app: FastAPI):
    """Configure all middleware for the application"""
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom middleware
    app.add_middleware(UsageTrackingMiddleware)
    app.add_middleware(CacheMiddleware, cache_patterns=settings.CACHE_PATTERNS)
    app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.RATE_LIMIT_CALLS_PER_MINUTE)
    
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

    from fastapi import Request
    app.add_middleware(EnterpriseFeatureMiddleware)