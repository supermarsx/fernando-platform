"""
Cache Decorators and Middleware

Provides decorators and middleware for automatic caching of API endpoints,
business logic functions, and database queries with intelligent cache invalidation.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.services.cache.redis_cache import cache_service, cache_result, cache_result_sync
from app.core.cache_config import cache_settings, namespace_manager
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel


logger = logging.getLogger(__name__)


def cache_api_response(cache_key_func: Callable = None, ttl: int = None, 
                      cache_type: str = "api", tenant_key: str = "tenant_id"):
    """
    Decorator to cache API endpoint responses.
    
    Args:
        cache_key_func: Function to generate cache key from request parameters
        ttl: Time-to-live in seconds
        cache_type: Type of cache (api, dashboard, report, etc.)
        tenant_key: Parameter name containing tenant ID
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request information
            request = None
            tenant_id = None
            
            # Find the request object in args
            for arg in args:
                if hasattr(arg, 'url') and hasattr(arg, 'method'):
                    request = arg
                    break
            
            # Extract tenant ID
            if tenant_key in kwargs:
                tenant_id = kwargs[tenant_key]
            elif request and hasattr(request, 'state') and hasattr(request.state, 'tenant_id'):
                tenant_id = request.state.tenant_id
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            elif request:
                # Generate key from request path and parameters
                path = request.url.path
                query_params = dict(request.query_params)
                key_data = f"{path}:{json.dumps(query_params, sort_keys=True)}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            else:
                # Fallback: use function name and args
                key_data = f"{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            start_time = time.time()
            try:
                cached_response = await cache_service.get(cache_key, cache_type, tenant_id)
                if cached_response is not None:
                    response_time = (time.time() - start_time) * 1000
                    
                    # Log cache hit
                    event_tracker.track_api_event(
                        "GET", request.url.path if request else "unknown", 
                        200, response_time, 
                        {"cache_hit": True, "cache_type": cache_type}
                    )
                    
                    # Return cached response
                    if isinstance(cached_response, dict):
                        return JSONResponse(content=cached_response)
                    else:
                        return cached_response
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache the response
            if result and ttl:
                try:
                    cache_ttl = ttl
                    await cache_service.set(
                        cache_key, result, cache_type, tenant_id, cache_ttl
                    )
                except Exception as e:
                    logger.warning(f"Cache storage failed: {e}")
            
            return result
        
        return wrapper
    return decorator


def cache_api_response_sync(cache_key_func: Callable = None, ttl: int = None,
                           cache_type: str = "api", tenant_key: str = "tenant_id"):
    """Synchronous version of cache_api_response decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request information
            request = None
            tenant_id = None
            
            # Find the request object in args
            for arg in args:
                if hasattr(arg, 'url') and hasattr(arg, 'method'):
                    request = arg
                    break
            
            # Extract tenant ID
            if tenant_key in kwargs:
                tenant_id = kwargs[tenant_key]
            elif request and hasattr(request, 'state') and hasattr(request.state, 'tenant_id'):
                tenant_id = request.state.tenant_id
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            elif request:
                # Generate key from request path and parameters
                path = request.url.path
                query_params = dict(request.query_params)
                key_data = f"{path}:{json.dumps(query_params, sort_keys=True)}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            else:
                # Fallback: use function name and args
                key_data = f"{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache (synchronous version)
            start_time = time.time()
            try:
                # This would need a synchronous Redis client
                # For now, we'll skip cache retrieval and always execute
                cached_response = None
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
                cached_response = None
            
            if cached_response is not None:
                response_time = (time.time() - start_time) * 1000
                event_tracker.track_api_event(
                    "GET", request.url.path if request else "unknown",
                    200, response_time,
                    {"cache_hit": True, "cache_type": cache_type}
                )
                return cached_response
            
            # Execute function and cache result asynchronously
            result = func(*args, **kwargs)
            
            if result and ttl:
                # Cache asynchronously (fire and forget)
                asyncio.create_task(cache_service.set(
                    cache_key, result, cache_type, tenant_id, ttl
                ))
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str, tenant_id: Optional[str] = None):
    """Invalidate cache entries matching a pattern."""
    async def invalidator():
        try:
            deleted_count = await cache_service.delete_pattern(pattern, tenant_id)
            logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
            
            event_tracker.track_system_event(
                "cache_invalidation", EventLevel.INFO,
                {"pattern": pattern, "deleted_count": deleted_count, "tenant_id": tenant_id}
            )
            
            return deleted_count
        except Exception as e:
            logger.error(f"Cache invalidation failed for pattern {pattern}: {e}")
            return 0
    
    return invalidator


def cache_business_data(ttl: int = 3600, cache_type: str = "business"):
    """Decorator to cache business logic data and computations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{func.__module__}.{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key, cache_type)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache_service.set(cache_key, result, cache_type, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_database_query(ttl: int = 1800, key_prefix: str = "query"):
    """Decorator to cache database query results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{key_prefix}:{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key, "database")
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache_service.set(cache_key, result, "database", ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


class CacheMiddleware:
    """FastAPI middleware for automatic response caching."""
    
    def __init__(self, app, cache_patterns: List[str] = None):
        self.app = app
        self.cache_patterns = cache_patterns or []
        self.exclude_paths = [
            "/health", "/metrics", "/docs", "/redoc", 
            "/openapi.json", "/favicon.ico"
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        
        # Skip caching for certain paths
        if request.url.path in self.exclude_paths:
            await self.app(scope, receive, send)
            return
        
        # Only cache GET requests
        if request.method != "GET":
            await self.app(scope, receive, send)
            return
        
        # Check if path matches cache patterns
        should_cache = any(
            request.url.path.startswith(pattern) for pattern in self.cache_patterns
        )
        
        if not should_cache:
            await self.app(scope, receive, send)
            return
        
        # Generate cache key
        query_params = dict(request.query_params)
        key_data = f"{request.method}:{request.url.path}:{json.dumps(query_params, sort_keys=True)}"
        cache_key = hashlib.md5(key_data.encode()).hexdigest()
        
        # Try to get from cache
        try:
            cached_response = await cache_service.get(cache_key, "api")
            if cached_response:
                # Return cached response
                headers = cached_response.get("headers", {})
                content = cached_response.get("content")
                status_code = cached_response.get("status_code", 200)
                
                response = Response(
                    content=content,
                    status_code=status_code,
                    headers=headers,
                    media_type=cached_response.get("media_type")
                )
                
                event_tracker.track_api_event(
                    request.method, request.url.path, status_code, 0.0,
                    {"cache_hit": True, "middleware": True}
                )
                
                await response(scope, receive, send)
                return
        except Exception as e:
            logger.warning(f"Cache middleware retrieval failed: {e}")
        
        # Process request normally and cache response
        response_started = False
        response_data = {}
        
        async def send_wrapper(message):
            nonlocal response_started, response_data
            
            if message["type"] == "http.response.start":
                response_started = True
                response_data["status_code"] = message["status"]
                response_data["headers"] = dict(message.get("headers", []))
            elif message["type"] == "http.response.body":
                if not response_data.get("content"):
                    response_data["content"] = b""
                response_data["content"] += message.get("body", b"")
            
            await send(message)
        
        # Process the request
        await self.app(scope, receive, send_wrapper)
        
        # Cache the response if successful
        if (response_started and 
            200 <= response_data.get("status_code", 500) < 300 and 
            response_data.get("content")):
            
            try:
                # Determine media type from headers
                content_type = response_data.get("headers", {}).get("content-type", "application/json")
                
                cache_data = {
                    "status_code": response_data["status_code"],
                    "headers": response_data["headers"],
                    "content": response_data["content"],
                    "media_type": content_type
                }
                
                # Use appropriate TTL based on endpoint
                ttl = self._get_ttl_for_path(request.url.path)
                tenant_id = getattr(request.state, 'tenant_id', None)
                
                await cache_service.set(
                    cache_key, cache_data, "api", tenant_id, ttl
                )
                
                logger.debug(f"Cached response for {request.method} {request.url.path}")
                
            except Exception as e:
                logger.warning(f"Cache middleware storage failed: {e}")
    
    def _get_ttl_for_path(self, path: str) -> int:
        """Get appropriate TTL for a specific path."""
        # Customize TTL based on endpoint type
        if "/dashboard" in path:
            return cache_settings.TTL_CONFIG.DASHBOARD_DATA_CACHE
        elif "/reports" in path:
            return cache_settings.TTL_CONFIG.REPORT_DATA_CACHE
        elif "/api/" in path:
            return cache_settings.TTL_CONFIG.API_RESPONSE_CACHE
        else:
            return cache_settings.TTL_CONFIG.API_RESPONSE_CACHE


def generate_cache_key_from_params(*params, **kwargs) -> str:
    """Generate a cache key from function parameters."""
    # Create a stable string representation
    key_data = f"params:{json.dumps(params, sort_keys=True)}:kwargs:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_with_tenant_isolation(cache_key_func: Callable = None, 
                               ttl: Optional[int] = None,
                               cache_type: str = "default"):
    """Decorator that automatically includes tenant isolation in cache keys."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract tenant ID from function context
            tenant_id = kwargs.get('tenant_id')
            
            # If no explicit tenant_id, try to find it in function parameters
            if not tenant_id:
                # Look for common parameter names
                for param_name in ['user_id', 'user', 'current_user']:
                    if param_name in kwargs:
                        tenant_id = kwargs[param_name]
                        break
            
            # Generate base cache key
            if cache_key_func:
                base_key = cache_key_func(*args, **kwargs)
            else:
                base_key = f"{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
            
            # Include tenant in key for isolation
            if tenant_id:
                full_key = f"tenant_{tenant_id}:{base_key}"
            else:
                full_key = f"no_tenant:{base_key}"
            
            # Try to get from cache
            cached_result = await cache_service.get(full_key, cache_type, tenant_id)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None and ttl:
                await cache_service.set(full_key, result, cache_type, tenant_id, ttl)
            
            return result
        
        return wrapper
    return decorator


# Utility functions for common caching patterns

async def cache_user_dashboard_data(user_id: str, tenant_id: str) -> Dict[str, Any]:
    """Cache user dashboard data."""
    cache_key = f"dashboard:user:{user_id}"
    cached_data = await cache_service.get(cache_key, "dashboard", tenant_id)
    
    if cached_data:
        return cached_data
    
    # Generate dashboard data
    dashboard_data = {
        "user_id": user_id,
        "last_login": datetime.utcnow().isoformat(),
        "metrics": {
            "documents_processed": 0,  # Would be fetched from database
            "extraction_success_rate": 0.95,
            "average_processing_time": 2.5
        }
    }
    
    await cache_service.set(
        cache_key, dashboard_data, "dashboard", tenant_id, 
        cache_settings.TTL_CONFIG.DASHBOARD_DATA_CACHE
    )
    
    return dashboard_data


async def cache_billing_summary(tenant_id: str) -> Dict[str, Any]:
    """Cache billing summary data."""
    cache_key = f"billing:summary:{tenant_id}"
    cached_data = await cache_service.get(cache_key, "billing", tenant_id)
    
    if cached_data:
        return cached_data
    
    # Generate billing summary
    billing_summary = {
        "tenant_id": tenant_id,
        "current_period": {
            "start_date": datetime.utcnow().replace(day=1).isoformat(),
            "end_date": datetime.utcnow().isoformat()
        },
        "usage": {
            "documents_processed": 0,
            "api_calls": 0,
            "storage_used_mb": 0
        },
        "costs": {
            "current_month": 0.0,
            "estimated_next_month": 0.0
        }
    }
    
    await cache_service.set(
        cache_key, billing_summary, "billing", tenant_id,
        cache_settings.TTL_CONFIG.BILLING_CACHE
    )
    
    return billing_summary


def invalidate_user_cache(user_id: str, tenant_id: str):
    """Invalidate all cache entries for a user."""
    async def invalidator():
        patterns = [
            f"dashboard:user:{user_id}",
            f"session:*user_{user_id}*",
            f"api:*user_{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await cache_service.delete_pattern(pattern, tenant_id)
            total_deleted += deleted
        
        event_tracker.track_business_event(
            "user_cache_invalidated", 
            {"user_id": user_id, "deleted_entries": total_deleted}
        )
        
        return total_deleted
    
    return invalidator()
