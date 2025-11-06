"""
Telemetry and Observability System for Fernando Platform

Provides structured logging, metrics collection, and performance monitoring
for all platform services.
"""

import time
import functools
import logging
import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict
import asyncio
from contextlib import contextmanager


class TelemetryLevel(Enum):
    """Telemetry log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TelemetryEvent(Enum):
    """Standard telemetry event types"""
    # License Events
    LICENSE_CREATED = "license.created"
    LICENSE_VALIDATED = "license.validated"
    LICENSE_RENEWED = "license.renewed"
    LICENSE_UPGRADED = "license.upgraded"
    LICENSE_SUSPENDED = "license.suspended"
    LICENSE_REVOKED = "license.revoked"
    LICENSE_EXPIRY_WARNING = "license.expiry_warning"
    
    # Payment Events
    PAYMENT_INTENT_CREATED = "payment.intent_created"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    INVOICE_GENERATED = "invoice.generated"
    
    # ML/Analytics Events
    LTV_PREDICTION_MADE = "ml.ltv_prediction_made"
    CHURN_ANALYSIS_COMPLETED = "ml.churn_analysis_completed"
    REVENUE_FORECAST_GENERATED = "ml.revenue_forecast_generated"
    ML_MODEL_ACCURACY_CALCULATED = "ml.accuracy_calculated"
    
    # Business KPIs
    REVENUE_CALCULATED = "kpi.revenue_calculated"
    USAGE_LIMITS_CHECKED = "kpi.usage_limits_checked"
    BILLING_CYCLE_COMPLETED = "kpi.billing_cycle_completed"
    CUSTOMER_ACQUIRED = "kpi.customer_acquired"
    CUSTOMER_CHURNED = "kpi.customer_churned"


@dataclass
class TelemetryEventData:
    """Structured telemetry event data"""
    event_type: str
    event_name: TelemetryEvent
    service_name: str
    method_name: str
    timestamp: str
    duration_ms: float
    status: str  # "success", "error", "warning"
    level: TelemetryLevel
    
    # Business metrics
    business_metric: Optional[str] = None
    metric_value: Optional[float] = None
    
    # Technical details
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    memory_usage_mb: Optional[float] = None
    cpu_time_ms: Optional[float] = None


class TelemetryCollector:
    """Central telemetry collection and storage"""
    
    def __init__(self):
        self.events: List[TelemetryEventData] = []
        self.business_metrics: Dict[str, List[float]] = defaultdict(list)
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        # Setup logger
        self.logger = logging.getLogger("telemetry")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_event(self, event_data: TelemetryEventData):
        """Log a telemetry event"""
        with self.lock:
            self.events.append(event_data)
        
        # Log to structured logger
        log_data = asdict(event_data)
        log_message = json.dumps(log_data, default=str)
        
        if event_data.level == TelemetryLevel.ERROR:
            self.logger.error(log_message)
        elif event_data.level == TelemetryLevel.WARNING:
            self.logger.warning(log_message)
        elif event_data.level == TelemetryLevel.INFO:
            self.logger.info(log_message)
        else:
            self.logger.debug(log_message)
    
    def record_business_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a business KPI metric"""
        with self.lock:
            self.business_metrics[metric_name].append({
                'timestamp': datetime.utcnow().isoformat(),
                'value': value,
                'tags': tags or {}
            })
    
    def record_performance_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        with self.lock:
            self.performance_metrics[metric_name].append({
                'timestamp': datetime.utcnow().isoformat(),
                'value': value,
                'tags': tags or {}
            })
    
    def get_events_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of events from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            recent_events = [
                event for event in self.events
                if datetime.fromisoformat(event.timestamp) > cutoff_time
            ]
        
        # Count events by type and status
        event_counts = defaultdict(int)
        status_counts = defaultdict(int)
        
        for event in recent_events:
            event_counts[event.event_type] += 1
            status_counts[event.status] += 1
        
        return {
            'total_events': len(recent_events),
            'event_types': dict(event_counts),
            'status_distribution': dict(status_counts),
            'time_range_hours': hours
        }
    
    def get_business_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of business metrics"""
        with self.lock:
            return {
                'metrics': dict(self.business_metrics),
                'metric_count': len(self.business_metrics)
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        with self.lock:
            summary = {}
            for metric_name, values in self.performance_metrics.items():
                if values:
                    summary[metric_name] = {
                        'count': len(values),
                        'avg': sum(v['value'] for v in values) / len(values),
                        'min': min(v['value'] for v in values),
                        'max': max(v['value'] for v in values),
                        'latest': values[-1]['value'] if values else None
                    }
            return summary


# Global telemetry collector instance
telemetry_collector = TelemetryCollector()


def telemetry_event(event_type: str, event_name: TelemetryEvent, level: TelemetryLevel = TelemetryLevel.INFO):
    """
    Decorator to automatically collect telemetry for service methods
    
    Args:
        event_type: Type of event (e.g., "license.created")
        event_name: Standardized event name from TelemetryEvent enum
        level: Log level for this event
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            service_name = "unknown"
            method_name = func.__name__
            
            # Extract service name from self if it's a method
            if args and hasattr(args[0], '__class__'):
                service_name = args[0].__class__.__name__
            
            status = "success"
            error_message = None
            error_traceback = None
            business_metric = None
            metric_value = None
            additional_data = {}
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Extract business metrics from result if it's a dict
                if isinstance(result, dict):
                    business_metric = result.get('business_metric')
                    metric_value = result.get('metric_value')
                    
                    # Add relevant data to additional_data
                    for key, value in result.items():
                        if key not in ['business_metric', 'metric_value'] and isinstance(value, (str, int, float, bool)):
                            additional_data[key] = value
                
                return result
                
            except Exception as e:
                status = "error"
                error_message = str(e)
                error_traceback = traceback.format_exc()
                raise
                
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Create telemetry event
                event_data = TelemetryEventData(
                    event_type=event_type,
                    event_name=event_name,
                    service_name=service_name,
                    method_name=method_name,
                    timestamp=datetime.utcnow().isoformat(),
                    duration_ms=duration_ms,
                    status=status,
                    level=level,
                    business_metric=business_metric,
                    metric_value=metric_value,
                    error_message=error_message,
                    error_traceback=error_traceback,
                    additional_data=additional_data
                )
                
                # Record performance metric
                telemetry_collector.record_performance_metric(
                    f"{service_name}.{method_name}.duration_ms", 
                    duration_ms,
                    {'service': service_name, 'method': method_name, 'status': status}
                )
                
                # Log the event
                telemetry_collector.log_event(event_data)
                
                # Record business metrics if available
                if business_metric and metric_value is not None:
                    telemetry_collector.record_business_metric(
                        business_metric, 
                        metric_value,
                        {'service': service_name, 'method': method_name}
                    )
        
        return wrapper
    return decorator


@contextmanager
def telemetry_context(event_type: str, event_name: TelemetryEvent, additional_data: Optional[Dict[str, Any]] = None):
    """
    Context manager for telemetry collection
    
    Args:
        event_type: Type of event
        event_name: Standardized event name
        additional_data: Additional data to include in telemetry
    """
    start_time = time.time()
    service_name = "unknown"
    status = "success"
    error_message = None
    error_traceback = None
    
    try:
        yield
    except Exception as e:
        status = "error"
        error_message = str(e)
        error_traceback = traceback.format_exc()
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        
        event_data = TelemetryEventData(
            event_type=event_type,
            event_name=event_name,
            service_name=service_name,
            method_name="context_manager",
            timestamp=datetime.utcnow().isoformat(),
            duration_ms=duration_ms,
            status=status,
            level=TelemetryLevel.INFO,
            error_message=error_message,
            error_traceback=error_traceback,
            additional_data=additional_data
        )
        
        telemetry_collector.log_event(event_data)


class TelemetryMixin:
    """Mixin class to add telemetry capabilities to any service"""
    
    def log_telemetry_event(
        self, 
        event_type: str, 
        event_name: TelemetryEvent,
        level: TelemetryLevel = TelemetryLevel.INFO,
        additional_data: Optional[Dict[str, Any]] = None,
        business_metric: Optional[str] = None,
        metric_value: Optional[float] = None
    ):
        """Log a telemetry event"""
        service_name = self.__class__.__name__
        
        event_data = TelemetryEventData(
            event_type=event_type,
            event_name=event_name,
            service_name=service_name,
            method_name="manual",
            timestamp=datetime.utcnow().isoformat(),
            duration_ms=0,  # Manual events don't track duration
            status="success",
            level=level,
            business_metric=business_metric,
            metric_value=metric_value,
            additional_data=additional_data
        )
        
        telemetry_collector.log_event(event_data)
        
        # Record metrics if provided
        if business_metric and metric_value is not None:
            telemetry_collector.record_business_metric(
                business_metric, 
                metric_value,
                {'service': service_name}
            )
    
    def record_performance(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        service_name = self.__class__.__name__
        metric_tags = {'service': service_name}
        if tags:
            metric_tags.update(tags)
        
        telemetry_collector.record_performance_metric(metric_name, value, metric_tags)
    
    def record_business_kpi(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a business KPI"""
        service_name = self.__class__.__name__
        metric_tags = {'service': service_name}
        if tags:
            metric_tags.update(tags)
        
        telemetry_collector.record_business_metric(metric_name, value, metric_tags)


# Utility functions for common telemetry patterns
def get_telemetry_summary(hours: int = 24) -> Dict[str, Any]:
    """Get comprehensive telemetry summary"""
    return {
        'events': telemetry_collector.get_events_summary(hours),
        'business_metrics': telemetry_collector.get_business_metrics_summary(),
        'performance': telemetry_collector.get_performance_summary(),
        'timestamp': datetime.utcnow().isoformat()
    }


def record_custom_metric(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Record a custom metric"""
    telemetry_collector.record_business_metric(metric_name, value, tags)