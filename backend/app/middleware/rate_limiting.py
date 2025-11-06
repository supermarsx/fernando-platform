"""
Rate limiting middleware
"""
import time
from fastapi import Request, Response, JSONResponse
from app.core.config import settings

class RateLimitMiddleware:
    def __init__(self, app, calls_per_minute: int = None):
        self.app = app
        self.calls_per_minute = calls_per_minute or settings.RATE_LIMIT_CALLS_PER_MINUTE
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