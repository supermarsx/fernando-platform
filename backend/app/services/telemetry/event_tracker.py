"""
Event tracking and logging service for the Fernando platform.

This module provides comprehensive event tracking capabilities including:
- User action tracking
- System events
- Business events
- Performance events
- Error events
- Audit trail events

Features:
- Structured event logging
- Event correlation and chaining
- Performance impact monitoring
- Configurable event retention
- Integration with external logging systems
- Real-time event streaming
"""

import asyncio
import time
import threading
import logging
import uuid
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict
from contextvars import ContextVar
import traceback


logger = logging.getLogger(__name__)


class EventLevel(Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(Enum):
    """Event categories for organization."""
    USER_ACTION = "user_action"
    SYSTEM = "system"
    BUSINESS = "business"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ERROR = "error"
    AUDIT = "audit"
    API = "api"
    BILLING = "billing"
    LICENSE = "license"
    PAYMENT = "payment"
    DOCUMENT = "document"
    EXTRACTION = "extraction"


@dataclass
class EventContext:
    """Context information for events."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source: str = "application"
    environment: str = "development"
    version: str = "1.0.0"


@dataclass
class Event:
    """Event data structure."""
    id: str
    name: str
    category: EventCategory
    level: EventLevel
    timestamp: datetime
    context: EventContext
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)


class EventTracker:
    """
    Comprehensive event tracking and logging service.
    
    Provides structured event logging with correlation,
    filtering, and export capabilities.
    """
    
    def __init__(self, max_events: int = 50000, retention_hours: int = 168):
        """Initialize the event tracker.
        
        Args:
            max_events: Maximum number of events to keep in memory
            retention_hours: How long to keep events before cleanup
        """
        self.max_events = max_events
        self.retention_period = timedelta(hours=retention_hours)
        
        # Thread-safe event storage
        self._lock = threading.RLock()
        self._events: deque = deque(maxlen=max_events)
        self._event_index: Dict[str, int] = {}  # event_id -> index
        self._category_counts: defaultdict = defaultdict(int)
        self._level_counts: defaultdict = defaultdict(int)
        
        # Event filters and streaming
        self._filters: List[Callable[[Event], bool]] = []
        self._stream_listeners: List[Callable[[Event], None]] = []
        
        # Context variables for automatic context tracking
        self._request_context: ContextVar[Optional[EventContext]] = ContextVar(
            'request_context', default=None
        )
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("Event tracker initialized with max_events=%d, retention_hours=%d",
                   max_events, retention_hours)
    
    async def start(self):
        """Start the event tracker background tasks."""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._background_cleanup())
        logger.info("Event tracker started")
    
    async def stop(self):
        """Stop the event tracker background tasks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Event tracker stopped")
    
    async def _background_cleanup(self):
        """Background task for periodic event cleanup."""
        try:
            while self._running:
                await self._cleanup_expired_events()
                await asyncio.sleep(300)  # Run every 5 minutes
        except asyncio.CancelledError:
            logger.info("Event cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in event cleanup: {e}")
    
    async def _cleanup_expired_events(self):
        """Remove expired events from storage."""
        cutoff_time = datetime.utcnow() - self.retention_period
        
        with self._lock:
            # Remove expired events from the front of the deque
            while self._events and self._events[0].timestamp < cutoff_time:
                expired_event = self._events.popleft()
                # Update counters
                self._category_counts[expired_event.category.value] -= 1
                self._level_counts[expired_event.level.value] -= 1
                # Remove from index
                if expired_event.id in self._event_index:
                    del self._event_index[expired_event.id]
    
    def set_request_context(self, context: EventContext):
        """Set the current request context for automatic event enrichment."""
        self._request_context.set(context)
    
    def get_current_context(self) -> Optional[EventContext]:
        """Get the current request context."""
        return self._request_context.get()
    
    def track_event(self, name: str, category: EventCategory, level: EventLevel,
                   data: Optional[Dict[str, Any]] = None,
                   context: Optional[EventContext] = None,
                   duration_ms: Optional[float] = None,
                   error_details: Optional[Dict[str, Any]] = None,
                   tags: Optional[List[str]] = None) -> str:
        """
        Track a new event.
        
        Args:
            name: Event name/description
            category: Event category
            level: Event severity level
            data: Optional event data
            context: Optional event context (uses current context if None)
            duration_ms: Optional duration in milliseconds
            error_details: Optional error details
            tags: Optional event tags
            
        Returns:
            Event ID for correlation
        """
        if data is None:
            data = {}
        if tags is None:
            tags = []
        
        # Use provided context or current context
        event_context = context or self.get_current_context() or EventContext()
        
        # Generate unique event ID
        event_id = str(uuid.uuid4())
        
        # Create event
        event = Event(
            id=event_id,
            name=name,
            category=category,
            level=level,
            timestamp=datetime.utcnow(),
            context=event_context,
            data=data,
            duration_ms=duration_ms,
            error_details=error_details,
            tags=tags
        )
        
        # Store event
        with self._lock:
            self._events.append(event)
            self._event_index[event_id] = len(self._events) - 1
            self._category_counts[category.value] += 1
            self._level_counts[level.value] += 1
        
        # Stream to listeners
        for listener in self._stream_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event stream listener: {e}")
        
        logger.debug(f"Event tracked: {name} ({category.value}, {level.value})")
        return event_id
    
    def track_user_action(self, action: str, user_id: str,
                         data: Optional[Dict[str, Any]] = None,
                         **kwargs) -> str:
        """Track a user action event."""
        context = EventContext(user_id=user_id, source="user_action")
        return self.track_event(
            name=f"user.{action}",
            category=EventCategory.USER_ACTION,
            level=EventLevel.INFO,
            data=data or {},
            context=context,
            tags=["user_action", action] + kwargs.get('tags', [])
        )
    
    def track_system_event(self, event_name: str, level: EventLevel,
                          data: Optional[Dict[str, Any]] = None,
                          **kwargs) -> str:
        """Track a system event."""
        return self.track_event(
            name=f"system.{event_name}",
            category=EventCategory.SYSTEM,
            level=level,
            data=data or {},
            tags=["system"] + kwargs.get('tags', [])
        )
    
    def track_business_event(self, event_name: str, data: Optional[Dict[str, Any]] = None,
                           **kwargs) -> str:
        """Track a business event."""
        return self.track_event(
            name=f"business.{event_name}",
            category=EventCategory.BUSINESS,
            level=EventLevel.INFO,
            data=data or {},
            tags=["business"] + kwargs.get('tags', [])
        )
    
    def track_api_event(self, method: str, endpoint: str, status_code: int,
                       response_time_ms: float, data: Optional[Dict[str, Any]] = None) -> str:
        """Track an API request/response event."""
        level = EventLevel.ERROR if status_code >= 400 else EventLevel.INFO
        
        api_data = {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time_ms": response_time_ms
        }
        if data:
            api_data.update(data)
        
        return self.track_event(
            name=f"api.{method}.{endpoint}",
            category=EventCategory.API,
            level=level,
            data=api_data,
            duration_ms=response_time_ms,
            tags=["api", method.lower(), f"status_{status_code}"]
        )
    
    def track_performance_event(self, operation: str, duration_ms: float,
                              data: Optional[Dict[str, Any]] = None,
                              **kwargs) -> str:
        """Track a performance event."""
        level = EventLevel.WARNING if duration_ms > 1000 else EventLevel.INFO
        
        perf_data = {"operation": operation, "duration_ms": duration_ms}
        if data:
            perf_data.update(data)
        
        return self.track_event(
            name=f"performance.{operation}",
            category=EventCategory.PERFORMANCE,
            level=level,
            data=perf_data,
            duration_ms=duration_ms,
            tags=["performance"] + kwargs.get('tags', [])
        )
    
    def track_error(self, error: Exception, context: Optional[EventContext] = None,
                   additional_data: Optional[Dict[str, Any]] = None) -> str:
        """Track an error event."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        }
        if additional_data:
            error_details.update(additional_data)
        
        return self.track_event(
            name=f"error.{type(error).__name__}",
            category=EventCategory.ERROR,
            level=EventLevel.ERROR,
            data={"exception": str(error)},
            context=context,
            error_details=error_details,
            tags=["error", type(error).__name__]
        )
    
    def track_audit_event(self, action: str, resource: str,
                         user_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Track an audit trail event."""
        audit_data = {
            "action": action,
            "resource": resource,
            "user_id": user_id
        }
        if data:
            audit_data.update(data)
        
        return self.track_event(
            name=f"audit.{action}",
            category=EventCategory.AUDIT,
            level=EventLevel.INFO,
            data=audit_data,
            context=EventContext(user_id=user_id, source="audit"),
            tags=["audit", action, resource]
        )
    
    def track_billing_event(self, event_name: str, amount: Optional[float] = None,
                           currency: Optional[str] = None,
                           data: Optional[Dict[str, Any]] = None) -> str:
        """Track a billing-related event."""
        billing_data = {}
        if amount is not None:
            billing_data["amount"] = amount
        if currency:
            billing_data["currency"] = currency
        if data:
            billing_data.update(data)
        
        return self.track_event(
            name=f"billing.{event_name}",
            category=EventCategory.BILLING,
            level=EventLevel.INFO,
            data=billing_data,
            tags=["billing", event_name]
        )
    
    def track_payment_event(self, event_name: str, payment_id: str,
                           amount: float, currency: str,
                           status: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Track a payment event."""
        payment_data = {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": status
        }
        if data:
            payment_data.update(data)
        
        level = EventLevel.ERROR if status in ["failed", "cancelled"] else EventLevel.INFO
        
        return self.track_event(
            name=f"payment.{event_name}",
            category=EventCategory.PAYMENT,
            level=level,
            data=payment_data,
            tags=["payment", status]
        )
    
    def add_event_filter(self, filter_func: Callable[[Event], bool]):
        """Add an event filter function."""
        self._filters.append(filter_func)
    
    def add_stream_listener(self, listener: Callable[[Event], None]):
        """Add an event stream listener."""
        self._stream_listeners.append(listener)
    
    def get_events(self, filters: Optional[Dict[str, Any]] = None,
                  limit: Optional[int] = None,
                  offset: int = 0) -> List[Event]:
        """Get events based on filters."""
        with self._lock:
            events = list(self._events)
        
        # Apply filters
        if filters:
            events = self._apply_filters(events, filters)
        
        # Apply user-defined filters
        for filter_func in self._filters:
            events = [e for e in events if filter_func(e)]
        
        # Apply pagination
        if offset > 0:
            events = events[offset:]
        if limit:
            events = events[:limit]
        
        return events
    
    def _apply_filters(self, events: List[Event], filters: Dict[str, Any]) -> List[Event]:
        """Apply filters to events list."""
        filtered = events
        
        if "category" in filters:
            filtered = [e for e in filtered if e.category.value == filters["category"]]
        
        if "level" in filters:
            filtered = [e for e in filtered if e.level.value == filters["level"]]
        
        if "start_time" in filters:
            start_time = filters["start_time"]
            filtered = [e for e in filtered if e.timestamp >= start_time]
        
        if "end_time" in filters:
            end_time = filters["end_time"]
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        if "user_id" in filters:
            filtered = [e for e in filtered if e.context.user_id == filters["user_id"]]
        
        if "tags" in filters:
            required_tags = filters["tags"]
            filtered = [e for e in filtered if any(tag in e.tags for tag in required_tags)]
        
        return filtered
    
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get a specific event by ID."""
        with self._lock:
            if event_id in self._event_index:
                index = self._event_index[event_id]
                if index < len(self._events):
                    return self._events[index]
        return None
    
    def get_correlated_events(self, correlation_id: str) -> List[Event]:
        """Get all events with the same correlation ID."""
        with self._lock:
            return [e for e in self._events if e.context.correlation_id == correlation_id]
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event tracking statistics."""
        with self._lock:
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            
            recent_events = [e for e in self._events if e.timestamp >= last_hour]
            daily_events = [e for e in self._events if e.timestamp >= last_24h]
            
            return {
                "total_events": len(self._events),
                "events_last_hour": len(recent_events),
                "events_last_24h": len(daily_events),
                "category_distribution": dict(self._category_counts),
                "level_distribution": dict(self._level_counts),
                "storage_usage": {
                    "current_events": len(self._events),
                    "max_events": self.max_events,
                    "usage_percent": (len(self._events) / self.max_events) * 100
                }
            }
    
    def export_events(self, format_type: str = "json", limit: Optional[int] = None) -> str:
        """Export events in the specified format."""
        events = self.get_events(limit=limit)
        
        if format_type.lower() == "json":
            events_data = [asdict(event) for event in events]
            # Convert datetime objects to ISO strings
            for event_data in events_data:
                event_data["timestamp"] = event_data["timestamp"].isoformat()
                if event_data["context"]:
                    event_data["context"] = asdict(event_data["context"])
            return json.dumps(events_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


# Global event tracker instance
event_tracker = EventTracker()


# Context manager for automatic event tracking
class tracked_operation:
    """Context manager for automatic operation tracking."""
    
    def __init__(self, operation_name: str, category: EventCategory = EventCategory.SYSTEM,
                 level: EventLevel = EventLevel.INFO, **kwargs):
        self.operation_name = operation_name
        self.category = category
        self.level = level
        self.kwargs = kwargs
        self.start_time = None
        self.event_id = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            # Track error
            error_details = {
                "operation": self.operation_name,
                "duration_ms": duration_ms,
                "exception": str(exc_val)
            }
            event_tracker.track_error(exc_val, additional_data=error_details)
        else:
            # Track successful operation
            event_tracker.track_event(
                name=f"operation.{self.operation_name}",
                category=self.category,
                level=self.level,
                duration_ms=duration_ms,
                data=self.kwargs
            )


# Decorator for automatic function tracking
def track_function(category: EventCategory = EventCategory.SYSTEM,
                  level: EventLevel = EventLevel.INFO):
    """Decorator to automatically track function execution."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            
            with tracked_operation(operation_name, category, level):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for external use
def track_user_action(action: str, user_id: str, **kwargs):
    """Track a user action."""
    return event_tracker.track_user_action(action, user_id, kwargs)


def track_business_event(event_name: str, **kwargs):
    """Track a business event."""
    return event_tracker.track_business_event(event_name, kwargs)


def track_api_call(method: str, endpoint: str, status_code: int,
                  response_time_ms: float, **kwargs):
    """Track an API call."""
    return event_tracker.track_api_event(method, endpoint, status_code,
                                       response_time_ms, kwargs)


def track_billing_event(event_name: str, **kwargs):
    """Track a billing event."""
    return event_tracker.track_billing_event(event_name, **kwargs)