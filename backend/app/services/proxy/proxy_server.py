"""
Centralized Proxy Server Core

Main proxy server implementation with zero client API key exposure,
intelligent request routing, and comprehensive security features.

Features:
- Zero API key exposure to clients
- Intelligent request routing and load balancing
- Automatic failover and health checking
- Request/response caching with TTL
- Rate limiting and quota management
- Circuit breaker pattern for external services
- Comprehensive logging and monitoring
- Security middleware and validation
"""

import asyncio
import time
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.models.proxy import (
    ProxyEndpoint, ApiKey, ProxyRequestLog, ProxyPerformanceMetrics,
    ProxySecurityEvent, CircuitBreakerState
)
from app.services.proxy.request_router import RequestRouter
from app.services.proxy.load_balancer import LoadBalancer
from app.services.proxy.failover_manager import FailoverManager
from app.services.proxy.proxy_security import ProxySecurityMiddleware
from app.services.api_management.api_key_manager import ApiKeyManager
from app.services.proxy_caching.response_cache import ResponseCache
from app.services.rate_limiting.rate_limiter import RateLimiter
from app.services.circuit_breaker.circuit_breaker import CircuitBreaker
from app.services.proxy_monitoring.request_logger import RequestLogger
from app.services.proxy_monitoring.performance_monitor import PerformanceMonitor
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel, EventContext
from app.services.cache.redis_cache import cache_service

logger = logging.getLogger(__name__)


@dataclass
class ProxyRequest:
    """Represents a proxied request."""
    id: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: Optional[bytes]
    client_ip: str
    user_agent: str
    auth_token: Optional[str]
    tenant_id: Optional[str]
    user_id: Optional[str]
    start_time: float
    timestamp: datetime


@dataclass
class ProxyResponse:
    """Represents a proxied response."""
    id: str
    status_code: int
    headers: Dict[str, str]
    content: Union[bytes, Any]
    duration_ms: float
    cached: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class ProxyServer:
    """
    Centralized proxy server with comprehensive features.
    
    Manages all proxy functionality including routing, caching,
    rate limiting, circuit breakers, and monitoring.
    """
    
    def __init__(self, app: FastAPI):
        """Initialize the proxy server."""
        self.app = app
        self.request_router: Optional[RequestRouter] = None
        self.load_balancer: Optional[LoadBalancer] = None
        self.failover_manager: Optional[FailoverManager] = None
        self.api_key_manager: Optional[ApiKeyManager] = None
        self.response_cache: Optional[ResponseCache] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_logger: Optional[RequestLogger] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        
        # HTTP client for upstream requests
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Configuration
        self.config = {
            "timeout": 30.0,
            "max_retries": 3,
            "retry_delay": 1.0,
            "compression_enabled": True,
            "streaming_enabled": True,
            "health_check_interval": 60,
        }
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "rate_limited_requests": 0,
            "circuit_breaker_trips": 0,
            "start_time": None
        }
        
        logger.info("Proxy server initialized")
    
    async def initialize(self):
        """Initialize all proxy server components."""
        logger.info("Initializing proxy server components...")
        
        try:
            # Initialize core components
            self.request_router = RequestRouter()
            await self.request_router.initialize()
            
            self.load_balancer = LoadBalancer()
            await self.load_balancer.initialize()
            
            self.failover_manager = FailoverManager()
            await self.failover_manager.initialize()
            
            self.api_key_manager = ApiKeyManager()
            await self.api_key_manager.initialize()
            
            self.response_cache = ResponseCache()
            await self.response_cache.initialize()
            
            self.rate_limiter = RateLimiter()
            await self.rate_limiter.initialize()
            
            self.request_logger = RequestLogger()
            await self.request_logger.initialize()
            
            self.performance_monitor = PerformanceMonitor()
            await self.performance_monitor.initialize()
            
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config["timeout"]),
                limits=httpx.Limits(max_keepalive_connections=100, max_connections=200)
            )
            
            # Initialize circuit breakers for all endpoints
            await self._initialize_circuit_breakers()
            
            # Update stats
            self.stats["start_time"] = datetime.utcnow()
            
            logger.info("Proxy server components initialized successfully")
            
            # Track initialization event
            event_tracker.track_system_event(
                "proxy_server_initialized",
                EventLevel.INFO,
                {"components": len(self.circuit_breakers)}
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize proxy server: {e}")
            raise
    
    async def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all proxy endpoints."""
        try:
            # Get all active proxy endpoints from database
            # This would typically use a database session
            endpoints = []  # Placeholder for database query
            
            for endpoint in endpoints:
                breaker = CircuitBreaker(
                    name=f"endpoint_{endpoint.id}",
                    failure_threshold=endpoint.failure_threshold,
                    recovery_timeout=endpoint.recovery_timeout_seconds,
                    expected_exception=httpx.HTTPError
                )
                await breaker.initialize()
                self.circuit_breakers[endpoint.id] = breaker
            
            logger.info(f"Initialized {len(self.circuit_breakers)} circuit breakers")
            
        except Exception as e:
            logger.error(f"Failed to initialize circuit breakers: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the proxy server and cleanup resources."""
        logger.info("Shutting down proxy server...")
        
        try:
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
            
            # Shutdown components
            components = [
                self.request_router,
                self.load_balancer,
                self.failover_manager,
                self.api_key_manager,
                self.response_cache,
                self.rate_limiter,
                self.request_logger,
                self.performance_monitor
            ]
            
            for component in components:
                if component and hasattr(component, 'shutdown'):
                    await component.shutdown()
            
            # Shutdown circuit breakers
            for breaker in self.circuit_breakers.values():
                if hasattr(breaker, 'shutdown'):
                    await breaker.shutdown()
            
            logger.info("Proxy server shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during proxy server shutdown: {e}")
    
    async def proxy_request(self, request: Request) -> Response:
        """
        Main proxy request handler.
        
        This method orchestrates the entire proxy request flow:
        1. Parse and validate request
        2. Route to appropriate endpoint
        3. Apply rate limiting
        4. Check cache
        5. Apply circuit breaker
        6. Execute upstream request
        7. Process and cache response
        8. Log request
        9. Return response
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Parse request
            proxy_request = await self._parse_request(request, request_id)
            
            # Track request start
            event_tracker.set_request_context(EventContext(
                request_id=request_id,
                source="proxy",
                correlation_id=proxy_request.id
            ))
            
            # Step 1: Route request to endpoint
            endpoint = await self.request_router.route_request(proxy_request)
            if not endpoint:
                raise HTTPException(status_code=404, detail="No matching endpoint found")
            
            # Step 2: Check rate limits
            rate_limit_result = await self.rate_limiter.check_rate_limit(
                proxy_request, endpoint
            )
            
            if not rate_limit_result.allowed:
                self.stats["rate_limited_requests"] += 1
                event_tracker.track_system_event(
                    "request_rate_limited",
                    EventLevel.WARNING,
                    {
                        "endpoint": endpoint.path_pattern,
                        "reason": rate_limit_result.reason,
                        "client_ip": proxy_request.client_ip
                    }
                )
                return await self._create_rate_limit_response(rate_limit_result)
            
            # Step 3: Check cache
            cached_response = await self.response_cache.get_cached_response(
                proxy_request, endpoint
            )
            
            if cached_response:
                self.stats["cached_requests"] += 1
                await self.request_logger.log_request(
                    proxy_request, cached_response, cached=True
                )
                return await self._create_cached_response(cached_response)
            
            # Step 4: Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(endpoint.id)
            if circuit_breaker:
                if circuit_breaker.state == CircuitBreakerState.OPEN:
                    # Circuit breaker is open, use fallback or return error
                    fallback_response = await self._handle_circuit_breaker_open(
                        circuit_breaker, proxy_request
                    )
                    if fallback_response:
                        return fallback_response
                    else:
                        raise HTTPException(
                            status_code=503,
                            detail="Service temporarily unavailable due to circuit breaker"
                        )
                
                if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                    # Allow request but monitor closely
                    pass
            
            # Step 5: Execute upstream request
            proxy_response = await self._execute_upstream_request(
                proxy_request, endpoint, circuit_breaker
            )
            
            # Step 6: Update statistics
            self.stats["total_requests"] += 1
            if proxy_response.status_code < 400:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
            
            # Step 7: Cache response if applicable
            if proxy_response.status_code < 400 and endpoint.cache_enabled:
                await self.response_cache.cache_response(
                    proxy_request, proxy_response, endpoint
                )
            
            # Step 8: Log request
            await self.request_logger.log_request(
                proxy_request, proxy_response, cached=False
            )
            
            # Step 9: Return response
            return await self._create_response(proxy_response)
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.stats["failed_requests"] += 1
            
            logger.error(f"Proxy request failed: {e}", exc_info=True)
            
            # Track error
            event_tracker.track_error(
                e,
                additional_data={
                    "request_id": request_id,
                    "proxy_operation": "proxy_request"
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal proxy error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _parse_request(self, request: Request, request_id: str) -> ProxyRequest:
        """Parse incoming request into ProxyRequest object."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Parse query parameters
        query_params = dict(request.query_params)
        
        # Get headers
        headers = dict(request.headers)
        
        # Extract authentication
        auth_token = headers.get("Authorization") or headers.get("X-API-Key")
        
        # Extract user context (would integrate with auth system)
        user_id = None
        tenant_id = None
        
        return ProxyRequest(
            id=request_id,
            method=request.method,
            path=str(request.url.path),
            headers=headers,
            query_params=query_params,
            body=body,
            client_ip=client_ip,
            user_agent=headers.get("User-Agent", ""),
            auth_token=auth_token,
            tenant_id=tenant_id,
            user_id=user_id,
            start_time=time.time(),
            timestamp=datetime.utcnow()
        )
    
    async def _execute_upstream_request(
        self,
        proxy_request: ProxyRequest,
        endpoint: ProxyEndpoint,
        circuit_breaker: Optional[CircuitBreaker]
    ) -> ProxyResponse:
        """Execute the upstream request with circuit breaker protection."""
        
        def execute_request():
            if circuit_breaker:
                with circuit_breaker:
                    return self._make_upstream_request(proxy_request, endpoint)
            else:
                return self._make_upstream_request(proxy_request, endpoint)
        
        try:
            # Execute with circuit breaker protection
            response = await asyncio.wait_for(execute_request(), timeout=self.config["timeout"])
            
            # Record successful request in circuit breaker
            if circuit_breaker:
                await circuit_breaker.record_success()
            
            return response
            
        except asyncio.TimeoutError:
            # Record timeout in circuit breaker
            if circuit_breaker:
                await circuit_breaker.record_failure(Exception("Request timeout"))
            
            raise HTTPException(
                status_code=504,
                detail="Upstream request timeout"
            )
        
        except httpx.HTTPError as e:
            # Record HTTP error in circuit breaker
            if circuit_breaker:
                await circuit_breaker.record_failure(e)
            
            raise HTTPException(
                status_code=502,
                detail=f"Upstream request failed: {str(e)}"
            )
    
    async def _make_upstream_request(
        self,
        proxy_request: ProxyRequest,
        endpoint: ProxyEndpoint
    ) -> ProxyResponse:
        """Make the actual upstream request."""
        
        start_time = time.time()
        
        try:
            # Build upstream URL
            upstream_url = urljoin(endpoint.upstream_url, proxy_request.path)
            if proxy_request.query_params:
                from urllib.parse import urlencode
                query_string = urlencode(proxy_request.query_params)
                upstream_url += f"?{query_string}"
            
            # Prepare headers
            upstream_headers = proxy_request.headers.copy()
            
            # Add API key if required
            if endpoint.requires_auth:
                api_key = await self.api_key_manager.get_healthy_api_key(
                    endpoint.id, proxy_request.tenant_id
                )
                if not api_key:
                    raise HTTPException(
                        status_code=503,
                        detail="No healthy API key available"
                    )
                
                # Add authentication header
                auth_header = await self._build_auth_header(api_key, endpoint)
                upstream_headers.update(auth_header)
            
            # Remove proxy-specific headers
            proxy_headers = [
                "host", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host",
                "x-real-ip", "x-proxy-authorization", "x-proxy-client-ip"
            ]
            for header in proxy_headers:
                upstream_headers.pop(header, None)
            
            # Add upstream headers
            upstream_headers.update(endpoint.request_headers)
            
            # Make request
            response = await self.http_client.request(
                method=proxy_request.method,
                url=upstream_url,
                headers=upstream_headers,
                content=proxy_request.body,
                follow_redirects=False
            )
            
            # Build response
            response_headers = dict(response.headers)
            
            # Apply response header transformations
            for old_header, new_header in endpoint.header_transformations.items():
                if old_header in response_headers:
                    response_headers[new_header] = response_headers[old_header]
                    del response_headers[old_header]
            
            # Add proxy-specific headers
            response_headers["X-Proxied-By"] = "Fernando-Proxy"
            response_headers["X-Proxy-Request-ID"] = proxy_request.id
            
            duration_ms = (time.time() - start_time) * 1000
            
            return ProxyResponse(
                id=proxy_request.id,
                status_code=response.status_code,
                headers=response_headers,
                content=response.content,
                duration_ms=duration_ms,
                cached=False,
                metadata={
                    "upstream_url": upstream_url,
                    "api_key_used": endpoint.requires_auth
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Upstream request failed: {e}")
            
            return ProxyResponse(
                id=proxy_request.id,
                status_code=500,
                headers={},
                content=b"",
                duration_ms=duration_ms,
                cached=False,
                error=str(e)
            )
    
    async def _build_auth_header(
        self,
        api_key: ApiKey,
        endpoint: ProxyEndpoint
    ) -> Dict[str, str]:
        """Build authentication header for API key."""
        
        # This would decrypt the API key and format appropriately
        # based on the provider and endpoint requirements
        
        decrypted_key = await self.api_key_manager.decrypt_api_key(api_key.encrypted_key)
        
        # Determine auth method based on provider
        if endpoint.provider == "openai":
            return {"Authorization": f"Bearer {decrypted_key}"}
        elif endpoint.provider == "azure":
            # Azure OpenAI uses different authentication
            return {"api-key": decrypted_key}
        elif endpoint.provider == "stripe":
            return {"Authorization": f"Bearer {decrypted_key}"}
        else:
            # Generic API key header
            return {"X-API-Key": decrypted_key}
    
    async def _handle_circuit_breaker_open(
        self,
        circuit_breaker: CircuitBreaker,
        proxy_request: ProxyRequest
    ) -> Optional[Response]:
        """Handle requests when circuit breaker is open."""
        
        # Log the circuit breaker trip
        event_tracker.track_system_event(
            "circuit_breaker_open",
            EventLevel.WARNING,
            {
                "circuit_breaker": circuit_breaker.name,
                "endpoint": proxy_request.path,
                "client_ip": proxy_request.client_ip
            }
        )
        
        self.stats["circuit_breaker_trips"] += 1
        
        # For some endpoints, we might have fallback responses
        if proxy_request.path.endswith("/health"):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "reason": "circuit_breaker_open",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return None
    
    async def _create_rate_limit_response(self, rate_limit_result) -> Response:
        """Create rate limit exceeded response."""
        
        headers = {
            "X-RateLimit-Limit": str(rate_limit_result.limit),
            "X-RateLimit-Remaining": str(rate_limit_result.remaining),
            "X-RateLimit-Reset": str(int(rate_limit_result.reset_time.timestamp())),
            "X-RateLimit-Type": rate_limit_result.limit_type
        }
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": rate_limit_result.reason,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers=headers
        )
    
    async def _create_cached_response(self, cached_response: ProxyResponse) -> Response:
        """Create response from cached data."""
        
        headers = cached_response.headers.copy()
        headers["X-Cache"] = "HIT"
        headers["X-Cache-Key"] = cached_response.metadata.get("cache_key", "")
        
        return Response(
            content=cached_response.content,
            status_code=cached_response.status_code,
            headers=headers
        )
    
    async def _create_response(self, proxy_response: ProxyResponse) -> Response:
        """Create final response from ProxyResponse."""
        
        headers = proxy_response.headers.copy()
        headers["X-Cache"] = "MISS"
        
        if proxy_response.status_code >= 400:
            headers["X-Error"] = proxy_response.error or "Unknown error"
        
        # Check if response should be streamed
        if self.config["streaming_enabled"] and isinstance(proxy_response.content, bytes):
            content_length = len(proxy_response.content)
            headers["Content-Length"] = str(content_length)
            
            if content_length > 1024 * 1024:  # 1MB
                # Stream large responses
                return StreamingResponse(
                    iter([proxy_response.content]),
                    status_code=proxy_response.status_code,
                    headers=headers
                )
        
        return Response(
            content=proxy_response.content,
            status_code=proxy_response.status_code,
            headers=headers
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive proxy server health status."""
        
        uptime_seconds = 0
        if self.stats["start_time"]:
            uptime_seconds = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        
        # Component health
        component_status = {}
        for name, component in [
            ("request_router", self.request_router),
            ("load_balancer", self.load_balancer),
            ("failover_manager", self.failover_manager),
            ("api_key_manager", self.api_key_manager),
            ("response_cache", self.response_cache),
            ("rate_limiter", self.rate_limiter),
            ("request_logger", self.request_logger),
            ("performance_monitor", self.performance_monitor)
        ]:
            if component:
                # Get health status from each component
                # This would be implemented based on each component's health check method
                component_status[name] = "healthy"
        
        # Circuit breaker status
        breaker_status = {}
        for endpoint_id, breaker in self.circuit_breakers.items():
            breaker_status[endpoint_id] = {
                "state": breaker.state.value if hasattr(breaker.state, 'value') else str(breaker.state),
                "failure_count": getattr(breaker, 'failure_count', 0),
                "last_failure": getattr(breaker, 'last_failure_time', None)
            }
        
        return {
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "statistics": self.stats,
            "components": component_status,
            "circuit_breakers": breaker_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        
        stats = self.stats.copy()
        
        # Calculate derived metrics
        if stats["total_requests"] > 0:
            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
            stats["error_rate"] = (stats["failed_requests"] / stats["total_requests"]) * 100
            stats["cache_hit_rate"] = (stats["cached_requests"] / stats["total_requests"]) * 100
        else:
            stats["success_rate"] = 0.0
            stats["error_rate"] = 0.0
            stats["cache_hit_rate"] = 0.0
        
        return stats


# Global proxy server instance
_proxy_server: Optional[ProxyServer] = None


async def get_proxy_server() -> ProxyServer:
    """Get the global proxy server instance."""
    global _proxy_server
    if _proxy_server is None:
        raise RuntimeError("Proxy server not initialized")
    return _proxy_server


def create_proxy_app() -> FastAPI:
    """Create and configure the proxy FastAPI application."""
    
    app = FastAPI(
        title="Fernando Proxy Server",
        description="Centralized proxy server with zero API key exposure",
        version="1.0.0"
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    
    # Add proxy security middleware
    app.add_middleware(ProxySecurityMiddleware)
    
    global _proxy_server
    _proxy_server = ProxyServer(app)
    
    # Proxy endpoint
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    async def proxy_endpoint(request: Request):
        """Main proxy endpoint that handles all requests."""
        return await _proxy_server.proxy_request(request)
    
    # Health check endpoint
    @app.get("/proxy/health")
    async def proxy_health():
        """Proxy server health check."""
        return await _proxy_server.get_health_status()
    
    # Statistics endpoint
    @app.get("/proxy/stats")
    async def proxy_stats():
        """Proxy server performance statistics."""
        return await _proxy_server.get_performance_stats()
    
    # Admin endpoints (would be protected in production)
    @app.post("/proxy/admin/reload")
    async def reload_proxy_config():
        """Reload proxy configuration."""
        await _proxy_server.request_router.reload_routes()
        return {"status": "configuration_reloaded"}
    
    return app
