"""
Business logic telemetry decorators for the Fernando platform.

This module provides easy-to-use decorators for adding comprehensive telemetry
to business logic functions without changing their core implementation.

Features:
- Automatic function execution tracking
- Performance monitoring
- Business event recording
- Error handling and reporting
- Custom metrics collection
- Distributed tracing integration
- Context enrichment
"""

import time
import functools
import logging
from typing import Any, Callable, Dict, Optional, List
from contextlib import contextmanager

from app.services.telemetry import (
    event_tracker, performance_monitor, distributed_tracer,
    metrics_collector, alert_manager,
    EventContext, EventCategory, EventLevel, SpanType,
    traced_operation, track_function,
    record_business_metric, record_custom_metric,
    increment_metric, timer_metric
)


logger = logging.getLogger(__name__)


# Generic business function telemetry decorator
def business_telemetry(
    operation_name: Optional[str] = None,
    category: EventCategory = EventCategory.BUSINESS,
    track_performance: bool = True,
    track_events: bool = True,
    track_metrics: bool = True,
    custom_attributes: Optional[Dict[str, Any]] = None,
    success_metric: Optional[str] = None,
    error_metric: Optional[str] = None,
    alert_on_slow: Optional[float] = None,
    service_name: str = "business"
):
    """
    Comprehensive business function telemetry decorator.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        category: Event category for tracking
        track_performance: Whether to track performance metrics
        track_events: Whether to track events
        track_metrics: Whether to track metrics
        custom_attributes: Custom attributes to add to events/metrics
        success_metric: Metric name to increment on success
        error_metric: Metric name to increment on error
        alert_on_slow: Alert threshold in milliseconds
        service_name: Service name for distributed tracing
    """
    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            custom_attrs = custom_attributes or {}
            
            # Add function metadata to context
            custom_attrs.update({
                "function_name": func.__name__,
                "function_module": func.__module__,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            })
            
            # Start distributed tracing span
            with traced_operation(op_name, SpanType.INTERNAL, service_name):
                try:
                    # Track function start event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.started",
                            category=category,
                            level=EventLevel.INFO,
                            data=custom_attrs
                        )
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Calculate execution time
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Track success metrics
                    if track_metrics:
                        if success_metric:
                            increment_metric(success_metric, 1.0, custom_attrs)
                        
                        # Generic success metric
                        increment_metric(f"{op_name}.success", 1.0, custom_attrs)
                    
                    # Track success event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.completed",
                            category=category,
                            level=EventLevel.INFO,
                            data={
                                **custom_attrs,
                                "duration_ms": duration_ms,
                                "result_type": type(result).__name__
                            }
                        )
                    
                    # Track performance
                    if track_performance:
                        performance_monitor.record_performance_metric(
                            f"{op_name}.duration_ms",
                            duration_ms,
                            custom_attrs,
                            [category.value, "success"]
                        )
                        
                        # Check for slow execution alert
                        if alert_on_slow and duration_ms > alert_on_slow:
                            alert_manager.check_custom_condition(
                                lambda: duration_ms > alert_on_slow,
                                f"Slow Execution: {op_name}",
                                f"Function took {duration_ms:.2f}ms (threshold: {alert_on_slow}ms)",
                                AlertSeverity.MEDIUM
                            )
                    
                    return result
                    
                except Exception as e:
                    # Calculate execution time for error
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Track error metrics
                    if track_metrics:
                        if error_metric:
                            increment_metric(error_metric, 1.0, custom_attrs)
                        
                        # Generic error metric
                        increment_metric(f"{op_name}.error", 1.0, custom_attrs)
                    
                    # Track error event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.error",
                            category=EventCategory.ERROR,
                            level=EventLevel.ERROR,
                            data={
                                **custom_attrs,
                                "duration_ms": duration_ms,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                    
                    # Track performance for errors
                    if track_performance:
                        performance_monitor.record_performance_metric(
                            f"{op_name}.error_duration_ms",
                            duration_ms,
                            {**custom_attrs, "error": type(e).__name__},
                            [category.value, "error"]
                        )
                    
                    # Re-raise the exception
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            custom_attrs = custom_attributes or {}
            
            # Add function metadata to context
            custom_attrs.update({
                "function_name": func.__name__,
                "function_module": func.__module__,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            })
            
            # Start distributed tracing span
            with traced_operation(op_name, SpanType.INTERNAL, service_name):
                try:
                    # Track function start event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.started",
                            category=category,
                            level=EventLevel.INFO,
                            data=custom_attrs
                        )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Calculate execution time
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Track success metrics
                    if track_metrics:
                        if success_metric:
                            increment_metric(success_metric, 1.0, custom_attrs)
                        
                        # Generic success metric
                        increment_metric(f"{op_name}.success", 1.0, custom_attrs)
                    
                    # Track success event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.completed",
                            category=category,
                            level=EventLevel.INFO,
                            data={
                                **custom_attrs,
                                "duration_ms": duration_ms,
                                "result_type": type(result).__name__
                            }
                        )
                    
                    # Track performance
                    if track_performance:
                        performance_monitor.record_performance_metric(
                            f"{op_name}.duration_ms",
                            duration_ms,
                            custom_attrs,
                            [category.value, "success"]
                        )
                    
                    return result
                    
                except Exception as e:
                    # Calculate execution time for error
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Track error metrics
                    if track_metrics:
                        if error_metric:
                            increment_metric(error_metric, 1.0, custom_attrs)
                        
                        # Generic error metric
                        increment_metric(f"{op_name}.error", 1.0, custom_attrs)
                    
                    # Track error event
                    if track_events:
                        event_tracker.track_event(
                            name=f"{op_name}.error",
                            category=EventCategory.ERROR,
                            level=EventLevel.ERROR,
                            data={
                                **custom_attrs,
                                "duration_ms": duration_ms,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                    
                    # Track performance for errors
                    if track_performance:
                        performance_monitor.record_performance_metric(
                            f"{op_name}.error_duration_ms",
                            duration_ms,
                            {**custom_attrs, "error": type(e).__name__},
                            [category.value, "error"]
                        )
                    
                    # Re-raise the exception
                    raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Specific decorators for different business domains

def billing_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for billing operations.
    
    Automatically tracks:
    - Billing events
    - Payment processing metrics
    - Revenue metrics
    - Error tracking for payment failures
    """
    default_attrs = {
        "domain": "billing",
        "track_revenue": True
    }
    default_attrs.update(kwargs)
    
    return business_telemetry(
        operation_name=operation_name,
        category=EventCategory.BILLING,
        custom_attributes=default_attrs,
        success_metric="billing.operations.success",
        error_metric="billing.operations.error",
        alert_on_slow=5000,  # 5 second threshold for billing operations
        service_name="billing"
    )


def payment_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for payment operations.
    
    Automatically tracks:
    - Payment events
    - Payment success/failure rates
    - Payment processing times
    - Gateway performance
    """
    default_attrs = {
        "domain": "payment",
        "track_payment_metrics": True
    }
    default_attrs.update(kwargs)
    
    return business_telemetry(
        operation_name=operation_name,
        category=EventCategory.PAYMENT,
        custom_attributes=default_attrs,
        success_metric="payment.operations.success",
        error_metric="payment.operations.error",
        alert_on_slow=10000,  # 10 second threshold for payment operations
        service_name="payment"
    )


def license_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for license operations.
    
    Automatically tracks:
    - License events
    - License usage metrics
    - Feature access tracking
    - Compliance events
    """
    default_attrs = {
        "domain": "license",
        "track_usage": True
    }
    default_attrs.update(kwargs)
    
    return business_telemetry(
        operation_name=operation_name,
        category=EventCategory.LICENSE,
        custom_attributes=default_attrs,
        success_metric="license.operations.success",
        error_metric="license.operations.error",
        alert_on_slow=2000,  # 2 second threshold for license operations
        service_name="license"
    )


def document_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for document processing operations.
    
    Automatically tracks:
    - Document processing events
    - OCR performance
    - Extraction accuracy
    - Processing times
    """
    default_attrs = {
        "domain": "document",
        "track_processing": True
    }
    default_attrs.update(kwargs)
    
    return business_telemetry(
        operation_name=operation_name,
        category=EventCategory.DOCUMENT,
        custom_attributes=default_attrs,
        success_metric="document.operations.success",
        error_metric="document.operations.error",
        alert_on_slow=30000,  # 30 second threshold for document processing
        service_name="document"
    )


def extraction_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for data extraction operations.
    
    Automatically tracks:
    - Extraction events
    - ML model performance
    - Accuracy metrics
    - Processing success rates
    """
    default_attrs = {
        "domain": "extraction",
        "track_ml_performance": True
    }
    default_attrs.update(kwargs)
    
    return business_telemetry(
        operation_name=operation_name,
        category=EventCategory.EXTRACTION,
        custom_attributes=default_attrs,
        success_metric="extraction.operations.success",
        error_metric="extraction.operations.error",
        alert_on_slow=15000,  # 15 second threshold for extraction operations
        service_name="extraction"
    )


def user_activity_telemetry(operation_name: Optional[str] = None, **kwargs):
    """
    Decorator specifically for user activity tracking.
    
    Automatically tracks:
    - User actions
    - Feature usage
    - Session data
    - Engagement metrics
    """
    def extract_user_id(*args, **kwargs):
        """Extract user ID from function arguments."""
        # Look for common user parameter names
        for arg in args:
            if hasattr(arg, 'user_id'):
                return arg.user_id
            elif hasattr(arg, 'id') and hasattr(arg, '__class__') and 'User' in arg.__class__.__name__:
                return arg.id
        
        for key, value in kwargs.items():
            if 'user_id' in key:
                return value
            elif hasattr(value, 'user_id'):
                return value.user_id
        
        return None
    
    default_attrs = {
        "domain": "user_activity",
        "track_usage": True
    }
    default_attrs.update(kwargs)
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            user_id = extract_user_id(*args, **kwargs)
            custom_attrs = {**default_attrs}
            
            if user_id:
                custom_attrs["user_id"] = user_id
                
                # Track user action event
                event_tracker.track_user_action(
                    action=operation_name or func.__name__,
                    user_id=user_id,
                    data=custom_attrs
                )
            
            # Call the main telemetry decorator
            wrapper = business_telemetry(
                operation_name=operation_name,
                category=EventCategory.USER_ACTION,
                custom_attributes=custom_attrs,
                success_metric="user.actions.success",
                error_metric="user.actions.error",
                service_name="user_activity"
            )
            
            return await wrapper(func)(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            user_id = extract_user_id(*args, **kwargs)
            custom_attrs = {**default_attrs}
            
            if user_id:
                custom_attrs["user_id"] = user_id
                
                # Track user action event
                event_tracker.track_user_action(
                    action=operation_name or func.__name__,
                    user_id=user_id,
                    data=custom_attrs
                )
            
            # Call the main telemetry decorator
            wrapper = business_telemetry(
                operation_name=operation_name,
                category=EventCategory.USER_ACTION,
                custom_attributes=custom_attrs,
                success_metric="user.actions.success",
                error_metric="user.actions.error",
                service_name="user_activity"
            )
            
            return wrapper(func)(*args, **kwargs)
        
        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Context managers for advanced telemetry scenarios
@contextmanager
def business_operation_telemetry(operation_name: str, category: EventCategory = EventCategory.BUSINESS,
                                custom_attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for business operation telemetry.
    
    Usage:
        with business_operation_telemetry("user_registration", EventCategory.USER_ACTION) as ctx:
            # Your business logic here
            register_user()
            ctx.add_attribute("registration_method", "email")
    """
    custom_attrs = custom_attributes or {}
    
    # Start tracing span
    span_context = distributed_tracer.start_span(
        name=f"business.{operation_name}",
        span_type=SpanType.INTERNAL,
        service_name="business"
    )
    
    # Start timing
    start_time = time.time()
    
    # Track start event
    event_tracker.track_event(
        name=f"business.{operation_name}.started",
        category=category,
        level=EventLevel.INFO,
        data=custom_attrs
    )
    
    class TelemetryContext:
        def add_attribute(self, key: str, value: Any):
            """Add attribute to the current span and events."""
            distributed_tracer.add_span_attribute(key, value)
            custom_attrs[key] = value
        
        def add_metric(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None):
            """Record a custom metric."""
            labels = labels or {}
            labels.update(custom_attrs)
            metrics_collector.record_metric(name, value, MetricType.GAUGE, labels)
        
        def add_event(self, name: str, data: Optional[Dict[str, Any]] = None):
            """Add a custom event."""
            event_data = {**custom_attrs}
            if data:
                event_data.update(data)
            event_tracker.track_event(
                name=f"business.{operation_name}.{name}",
                category=category,
                level=EventLevel.INFO,
                data=event_data
            )
    
    context = TelemetryContext()
    
    try:
        yield context
        
        # Track success
        duration_ms = (time.time() - start_time) * 1000
        event_tracker.track_event(
            name=f"business.{operation_name}.completed",
            category=category,
            level=EventLevel.INFO,
            data={**custom_attrs, "duration_ms": duration_ms}
        )
        
        performance_monitor.record_performance_metric(
            f"business.{operation_name}.duration_ms",
            duration_ms,
            custom_attrs,
            [category.value]
        )
        
    except Exception as e:
        # Track error
        duration_ms = (time.time() - start_time) * 1000
        event_tracker.track_error(e, additional_data={**custom_attrs, "duration_ms": duration_ms})
        
        performance_monitor.record_performance_metric(
            f"business.{operation_name}.error_duration_ms",
            duration_ms,
            {**custom_attrs, "error": type(e).__name__},
            [category.value, "error"]
        )
        
        raise
    
    finally:
        # End span
        distributed_tracer.end_span()


# Utility functions for common telemetry patterns
def track_revenue_event(event_name: str, amount: float, currency: str = "USD",
                       user_id: Optional[str] = None, **kwargs):
    """Track revenue-related events with proper business metrics."""
    # Track the event
    event_tracker.track_billing_event(
        event_name=event_name,
        amount=amount,
        currency=currency,
        data=kwargs
    )
    
    # Record revenue metrics
    record_business_metric("revenue.total", amount, {
        "currency": currency,
        "event_type": event_name,
        "user_id": user_id
    })
    
    # Track daily revenue
    from datetime import datetime
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    record_business_metric(f"revenue.daily.{date_str}", amount, {
        "currency": currency,
        "event_type": event_name
    })


def track_user_engagement(action: str, user_id: str, session_id: Optional[str] = None,
                         additional_data: Optional[Dict[str, Any]] = None):
    """Track user engagement events."""
    data = {
        "action": action,
        "user_id": user_id,
        "timestamp": time.time()
    }
    if session_id:
        data["session_id"] = session_id
    if additional_data:
        data.update(additional_data)
    
    # Track user action
    event_tracker.track_user_action(action, user_id, data)
    
    # Record engagement metrics
    record_custom_metric("user.engagement.actions", 1.0, {
        "action": action,
        "user_id": user_id,
        "has_session": "true" if session_id else "false"
    })


def track_api_usage(endpoint: str, method: str, user_id: Optional[str] = None,
                   response_time_ms: Optional[float] = None, **kwargs):
    """Track API usage patterns."""
    data = {
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id
    }
    if response_time_ms:
        data["response_time_ms"] = response_time_ms
    data.update(kwargs)
    
    # Track API event
    event_tracker.track_event(
        name=f"api.usage.{endpoint}",
        category=EventCategory.API,
        level=EventLevel.INFO,
        data=data
    )
    
    # Record usage metrics
    increment_metric("api.usage.count", 1.0, {
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id
    })


# Pre-defined decorator sets for quick application
QUICK_DECORATORS = {
    # Billing operations
    "billing": billing_telemetry,
    "payment": payment_telemetry,
    "license": license_telemetry,
    
    # Document processing
    "document": document_telemetry,
    "extraction": extraction_telemetry,
    
    # User activity
    "user": user_activity_telemetry,
    
    # Generic business logic
    "business": business_telemetry,
    "system": lambda op=None, **kwargs: business_telemetry(op, EventCategory.SYSTEM, **kwargs),
    "performance": lambda op=None, **kwargs: business_telemetry(op, EventCategory.PERFORMANCE, **kwargs),
    "security": lambda op=None, **kwargs: business_telemetry(op, EventCategory.SECURITY, **kwargs),
}


def apply_quick_telemetry(domain: str, operation_name: Optional[str] = None, **kwargs):
    """Apply a quick telemetry decorator by domain."""
    if domain not in QUICK_DECORATORS:
        raise ValueError(f"Unknown telemetry domain: {domain}. Available: {list(QUICK_DECORATORS.keys())}")
    
    return QUICK_DECORATORS[domain](operation_name, **kwargs)


# Export commonly used items
__all__ = [
    "business_telemetry",
    "billing_telemetry",
    "payment_telemetry", 
    "license_telemetry",
    "document_telemetry",
    "extraction_telemetry",
    "user_activity_telemetry",
    "business_operation_telemetry",
    "track_revenue_event",
    "track_user_engagement",
    "track_api_usage",
    "apply_quick_telemetry",
    "QUICK_DECORATORS"
]