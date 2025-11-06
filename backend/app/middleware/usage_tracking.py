"""
Usage Tracking Middleware

Automatically tracks API usage, response times, and errors for all endpoints.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
from typing import Callable
import time
import logging

from app.services.usage_tracking_service import UsageTrackingService
from app.models.usage import UsageMetricType
from app.db.session import get_db

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track API usage metrics
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.excluded_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/health",
            "/metrics"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tracking for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        subscription_id = getattr(request.state, "subscription_id", None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Track usage if user is authenticated
        if user_id:
            try:
                # Determine metric type based on endpoint
                metric_type = self._get_metric_type(request.url.path, request.method)
                
                if metric_type:
                    # Get database session
                    db = next(get_db())
                    tracking_service = UsageTrackingService(db)
                    
                    # Track API call
                    await tracking_service.track_usage(
                        user_id=user_id,
                        metric_type=UsageMetricType.API_CALLS,
                        metric_value=1,
                        subscription_id=subscription_id,
                        endpoint=request.url.path,
                        operation=request.method,
                        response_time_ms=response_time_ms,
                        error_occurred=response.status_code >= 400,
                        error_code=str(response.status_code) if response.status_code >= 400 else None,
                        metadata={
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                            "user_agent": request.headers.get("user-agent", "")
                        }
                    )
                    
                    # Track specific resource usage
                    if metric_type != UsageMetricType.API_CALLS:
                        await tracking_service.track_usage(
                            user_id=user_id,
                            metric_type=metric_type,
                            metric_value=1,
                            subscription_id=subscription_id,
                            endpoint=request.url.path,
                            operation=request.method,
                            response_time_ms=response_time_ms,
                            error_occurred=response.status_code >= 400,
                            metadata={
                                "method": request.method,
                                "path": request.url.path
                            }
                        )
                    
                    db.close()
                    
            except Exception as e:
                logger.error(f"Error tracking usage: {str(e)}")
                # Don't fail the request if tracking fails
        
        return response
    
    def _get_metric_type(self, path: str, method: str) -> str:
        """
        Determine metric type based on endpoint path
        """
        # Document processing endpoints
        if "/jobs" in path and method == "POST":
            return UsageMetricType.DOCUMENT_PROCESSING
        elif "/documents" in path and method == "POST":
            return UsageMetricType.DOCUMENT_PROCESSING
        
        # OCR endpoints
        elif "/ocr" in path:
            return UsageMetricType.OCR_OPERATIONS
        
        # LLM/extraction endpoints
        elif "/extract" in path or "/llm" in path:
            return UsageMetricType.LLM_OPERATIONS
        
        # Export endpoints
        elif "/export" in path:
            return UsageMetricType.EXPORT_OPERATIONS
        
        # Batch operations
        elif "/batch" in path:
            return UsageMetricType.BATCH_OPERATIONS
        
        # Default to API calls
        else:
            return UsageMetricType.API_CALLS


def track_document_processing(func):
    """
    Decorator to track document processing usage
    """
    async def wrapper(*args, **kwargs):
        # Extract user info from kwargs or request
        user_id = kwargs.get("user_id") or kwargs.get("current_user", {}).get("user_id")
        subscription_id = kwargs.get("subscription_id")
        
        # Execute function
        result = await func(*args, **kwargs)
        
        # Track usage
        if user_id:
            try:
                db = next(get_db())
                tracking_service = UsageTrackingService(db)
                
                # Track document processing
                await tracking_service.track_usage(
                    user_id=user_id,
                    metric_type=UsageMetricType.DOCUMENT_PROCESSING,
                    metric_value=1,
                    subscription_id=subscription_id,
                    resource_id=result.get("document_id") if isinstance(result, dict) else None,
                    metadata={
                        "function": func.__name__,
                        "success": True
                    }
                )
                
                # Track pages if available
                if isinstance(result, dict) and "pages_count" in result:
                    await tracking_service.track_usage(
                        user_id=user_id,
                        metric_type=UsageMetricType.DOCUMENT_PAGES,
                        metric_value=result["pages_count"],
                        subscription_id=subscription_id,
                        resource_id=result.get("document_id")
                    )
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error tracking document processing: {str(e)}")
        
        return result
    
    return wrapper


def track_storage_usage(func):
    """
    Decorator to track storage usage
    """
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get("user_id") or kwargs.get("current_user", {}).get("user_id")
        subscription_id = kwargs.get("subscription_id")
        
        result = await func(*args, **kwargs)
        
        if user_id and isinstance(result, dict) and "file_size" in result:
            try:
                db = next(get_db())
                tracking_service = UsageTrackingService(db)
                
                # Convert bytes to GB
                file_size_gb = result["file_size"] / (1024 ** 3)
                
                await tracking_service.track_usage(
                    user_id=user_id,
                    metric_type=UsageMetricType.STORAGE_USAGE,
                    metric_value=file_size_gb,
                    subscription_id=subscription_id,
                    resource_id=result.get("file_id"),
                    metadata={
                        "file_name": result.get("file_name"),
                        "file_size_bytes": result["file_size"]
                    }
                )
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error tracking storage usage: {str(e)}")
        
        return result
    
    return wrapper


def check_quota_before_processing(metric_type: str, required_quantity: float = 1.0):
    """
    Decorator to check quota availability before processing
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or kwargs.get("current_user", {}).get("user_id")
            subscription_id = kwargs.get("subscription_id")
            
            if user_id and subscription_id:
                try:
                    db = next(get_db())
                    tracking_service = UsageTrackingService(db)
                    
                    # Check quota availability
                    is_available, error_message, quota_info = tracking_service.check_quota_available(
                        user_id=user_id,
                        subscription_id=subscription_id,
                        metric_type=metric_type,
                        required_quantity=required_quantity
                    )
                    
                    if not is_available:
                        db.close()
                        raise Exception(f"Quota exceeded: {error_message}")
                    
                    # If overage will be charged, add to metadata
                    if quota_info and "overage_cost" in quota_info:
                        if "metadata" not in kwargs:
                            kwargs["metadata"] = {}
                        kwargs["metadata"]["overage_cost"] = quota_info["overage_cost"]
                    
                    db.close()
                    
                except Exception as e:
                    logger.error(f"Error checking quota: {str(e)}")
                    raise
            
            # Execute function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
