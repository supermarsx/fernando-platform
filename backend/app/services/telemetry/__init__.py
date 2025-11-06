"""
Telemetry Services Package for the Fernando Platform

This package provides comprehensive telemetry and observability capabilities including:
- Real-time metrics collection
- Event tracking and logging
- Performance monitoring
- Distributed tracing
- Alert management
- Background task processing

Main Components:
- metrics_collector: Real-time metrics collection service
- event_tracker: Event tracking and logging service
- performance_monitor: Performance monitoring with response times
- distributed_tracer: Distributed tracing capabilities
- alert_manager: Alerting system for critical metrics
- background_tasks: Background aggregation and analysis tasks

Quick Start:
    from app.services.telemetry import (
        metrics_collector, event_tracker, performance_monitor,
        initialize_telemetry_services
    )
    
    # Initialize all services
    await initialize_telemetry_services()
    
    # Record a metric
    metrics_collector.record_metric("api.requests", 1.0, MetricType.COUNTER)
    
    # Track an event
    event_tracker.track_business_event("user_signup", {"user_id": "123"})
    
    # Monitor performance
    with performance_timer("database_query"):
        # Your database operation here
        pass

Global Services:
    metrics_collector: Global metrics collector instance
    event_tracker: Global event tracker instance
    performance_monitor: Global performance monitor instance
    distributed_tracer: Global distributed tracer instance
    alert_manager: Global alert manager instance
    telemetry_background_tasks: Global background tasks instance
"""

from .metrics_collector import (
    MetricsCollector, MetricType, MetricData, SystemMetrics,
    metrics_collector, record_business_metric, record_application_metric,
    record_custom_metric, increment_metric, timer_metric
)

from .event_tracker import (
    EventTracker, EventLevel, EventCategory, EventContext, Event,
    event_tracker, tracked_operation, track_function,
    track_user_action, track_business_event, track_api_call, track_billing_event
)

from .performance_monitor import (
    PerformanceMonitor, PerformanceMetric, PerformanceLevel,
    PerformanceData, PerformanceThreshold, EndpointMetrics,
    performance_monitor, monitor_performance, performance_timer,
    track_response_time, track_db_query, track_api_call
)

from .distributed_tracer import (
    DistributedTracer, TraceStatus, SpanType, TraceContext,
    TraceAttribute, TraceEvent, TraceSpan,
    distributed_tracer, traced_operation, trace_function,
    start_trace, end_trace, add_trace_attribute, add_trace_event,
    inject_trace_context, extract_trace_context
)

from .alert_manager import (
    AlertManager, AlertSeverity, AlertStatus, AlertCategory,
    AlertRule, Alert, NotificationChannel,
    alert_manager, create_alert_rule, add_alert_rule,
    create_notification_channel, add_notification_channel,
    check_alert_condition
)

from .background_tasks import (
    TelemetryBackgroundTasks,
    telemetry_background_tasks,
    start_telemetry_background_tasks,
    stop_telemetry_background_tasks,
    configure_telemetry_task,
    get_telemetry_tasks_status,
    check_telemetry_background_tasks_health
)

__all__ = [
    # Metrics Collector
    "MetricsCollector", "MetricType", "MetricData", "SystemMetrics",
    "metrics_collector", "record_business_metric", "record_application_metric",
    "record_custom_metric", "increment_metric", "timer_metric",
    
    # Event Tracker
    "EventTracker", "EventLevel", "EventCategory", "EventContext", "Event",
    "event_tracker", "tracked_operation", "track_function",
    "track_user_action", "track_business_event", "track_api_call", "track_billing_event",
    
    # Performance Monitor
    "PerformanceMonitor", "PerformanceMetric", "PerformanceLevel",
    "PerformanceData", "PerformanceThreshold", "EndpointMetrics",
    "performance_monitor", "monitor_performance", "performance_timer",
    "track_response_time", "track_db_query", "track_api_call",
    
    # Distributed Tracer
    "DistributedTracer", "TraceStatus", "SpanType", "TraceContext",
    "TraceAttribute", "TraceEvent", "TraceSpan",
    "distributed_tracer", "traced_operation", "trace_function",
    "start_trace", "end_trace", "add_trace_attribute", "add_trace_event",
    "inject_trace_context", "extract_trace_context",
    
    # Alert Manager
    "AlertManager", "AlertSeverity", "AlertStatus", "AlertCategory",
    "AlertRule", "Alert", "NotificationChannel",
    "alert_manager", "create_alert_rule", "add_alert_rule",
    "create_notification_channel", "add_notification_channel",
    "check_alert_condition",
    
    # Background Tasks
    "TelemetryBackgroundTasks",
    "telemetry_background_tasks",
    "start_telemetry_background_tasks",
    "stop_telemetry_background_tasks",
    "configure_telemetry_task",
    "get_telemetry_tasks_status",
    "check_telemetry_background_tasks_health"
]


# Service initialization helper
async def initialize_telemetry_services():
    """Initialize all telemetry services."""
    from app.core.config import settings
    
    # Start all core services
    await metrics_collector.start()
    await event_tracker.start()
    await performance_monitor.start()
    await distributed_tracer.start()
    await alert_manager.start()
    
    # Start background tasks if enabled
    if settings.TELEMETRY_ENABLED:
        await start_telemetry_background_tasks()
    
    # Configure default alert rules if not already configured
    _configure_default_alerts()
    
    # Configure default notification channels
    _configure_default_channels()
    
    print("✅ All telemetry services initialized successfully")


async def shutdown_telemetry_services():
    """Shutdown all telemetry services."""
    # Stop background tasks first
    await stop_telemetry_background_tasks()
    
    # Stop all core services
    await metrics_collector.stop()
    await event_tracker.stop()
    await performance_monitor.stop()
    await distributed_tracer.stop()
    await alert_manager.stop()
    
    print("✅ All telemetry services shutdown completed")


def _configure_default_alerts():
    """Configure default alert rules."""
    # Only add default alerts if none exist
    if not alert_manager._alert_rules:
        # Performance alerts
        high_response_time = create_alert_rule(
            "High Response Time",
            "response_time",
            ">",
            2000.0,
            AlertSeverity.HIGH,
            AlertCategory.PERFORMANCE
        )
        add_alert_rule(high_response_time)
        
        # System alerts
        high_cpu = create_alert_rule(
            "High CPU Usage",
            "cpu_usage",
            ">",
            90.0,
            AlertSeverity.HIGH,
            AlertCategory.SYSTEM
        )
        add_alert_rule(high_cpu)
        
        # Reliability alerts
        high_error_rate = create_alert_rule(
            "High Error Rate",
            "error_rate",
            ">",
            5.0,
            AlertSeverity.CRITICAL,
            AlertCategory.RELIABILITY
        )
        add_alert_rule(high_error_rate)


def _configure_default_channels():
    """Configure default notification channels."""
    # Console notification for all severities
    console_channel = create_notification_channel(
        "console",
        "console",
        {}
    )
    add_notification_channel(console_channel)


# Health check helper
def get_telemetry_health_status() -> dict:
    """Get health status of all telemetry services."""
    import asyncio
    
    # Get background tasks health status
    background_health = {}
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we can't await the health check
            # This is a limitation of the synchronous health check
            background_health = {"status": "unknown", "note": "Async context - run check_telemetry_background_tasks_health() separately"}
        else:
            background_health = loop.run_until_complete(check_telemetry_background_tasks_health())
    except Exception:
        background_health = {"status": "error", "note": "Could not check background tasks health"}
    
    return {
        "metrics_collector": {
            "status": "healthy",
            "total_metrics": len(metrics_collector._metrics),
            "active_gauges": len(metrics_collector._gauges),
        },
        "event_tracker": {
            "status": "healthy", 
            "total_events": len(event_tracker._events),
            "active_categories": len(event_tracker._category_counts),
        },
        "performance_monitor": {
            "status": "healthy",
            "monitored_endpoints": len(performance_monitor._endpoints),
            "tracked_metrics": len(performance_monitor._performance_data),
        },
        "distributed_tracer": {
            "status": "healthy",
            "active_traces": len(distributed_tracer._active_traces),
            "total_spans": sum(len(spans) for spans in distributed_tracer._traces.values()),
        },
        "alert_manager": {
            "status": "healthy",
            "active_alerts": len(alert_manager._active_alerts),
            "configured_rules": len(alert_manager._alert_rules),
        },
        "background_tasks": background_health
    }


# Convenience decorator for comprehensive telemetry
def telemetry_monitor(service_name: str = "unknown"):
    """
    Comprehensive telemetry decorator that tracks:
    - Performance (response time)
    - Events (start/completion/errors)
    - Metrics (success/failure rates)
    - Traces (function execution)
    """
    def decorator(func):
        # Combine multiple telemetry decorators
        @trace_function(SpanType.INTERNAL, service_name)
        @monitor_performance()
        @track_function()
        def wrapper(*args, **kwargs):
            try:
                # Track function start
                event_tracker.track_event(
                    name=f"function_start.{func.__name__}",
                    category=EventCategory.SYSTEM,
                    level=EventLevel.INFO,
                    data={"args_count": len(args), "kwargs_count": len(kwargs)}
                )
                
                result = func(*args, **kwargs)
                
                # Track successful completion
                event_tracker.track_event(
                    name=f"function_success.{func.__name__}",
                    category=EventCategory.SYSTEM,
                    level=EventLevel.INFO,
                    data={"result_type": type(result).__name__}
                )
                
                return result
                
            except Exception as e:
                # Track error
                event_tracker.track_error(e)
                raise
        
        return wrapper
    return decorator


# Export main instances for easy access
__version__ = "1.0.0"
__author__ = "Fernando Platform Team"
__email__ = "dev@fernando-platform.com"