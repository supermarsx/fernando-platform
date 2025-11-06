"""
Distributed tracing service for the Fernando platform.

This module provides comprehensive distributed tracing capabilities including:
- Request tracing across services
- Service dependency mapping
- Trace correlation and propagation
- Performance bottleneck identification
- Service mesh visualization
- Error propagation tracking

Features:
- OpenTelemetry-compatible tracing
- Automatic span creation
- Context propagation
- Trace sampling
- Service dependency analysis
- Real-time trace streaming
"""

import asyncio
import time
import threading
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict
from contextvars import ContextVar
import json
import traceback
import weakref


logger = logging.getLogger(__name__)


class TraceStatus(Enum):
    """Trace execution status."""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpanType(Enum):
    """Types of spans in distributed tracing."""
    ENTRY = "entry"
    EXIT = "exit"
    INTERNAL = "internal"
    HTTP_REQUEST = "http_request"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    CACHE = "cache"
    EXTERNAL_API = "external_api"


@dataclass
class TraceContext:
    """Distributed trace context."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, Any] = field(default_factory=dict)
    trace_flags: int = 0x1  # Sampled flag
    trace_state: str = ""


@dataclass
class TraceAttribute:
    """Trace attribute key-value pair."""
    key: str
    value: Any
    type: str = "string"  # string, int, float, bool, json


@dataclass
class TraceEvent:
    """Trace event with timestamp."""
    name: str
    timestamp: datetime
    attributes: List[TraceAttribute] = field(default_factory=list)


@dataclass
class TraceSpan:
    """Individual trace span."""
    span_id: str
    trace_id: str
    name: str
    span_type: SpanType
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.OK
    parent_span_id: Optional[str] = None
    service_name: str = "unknown"
    operation_name: str = ""
    attributes: List[TraceAttribute] = field(default_factory=list)
    events: List[TraceEvent] = field(default_factory=list)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)  # Linked span IDs
    kind: str = "INTERNAL"  # INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER


class DistributedTracer:
    """
    Distributed tracing service for end-to-end request tracking.
    
    Provides comprehensive distributed tracing with automatic span creation,
    context propagation, and trace analysis capabilities.
    """
    
    def __init__(self, max_traces: int = 10000, max_spans_per_trace: int = 1000):
        """Initialize the distributed tracer.
        
        Args:
            max_traces: Maximum number of traces to keep in memory
            max_spans_per_trace: Maximum spans per trace
        """
        self.max_traces = max_traces
        self.max_spans_per_trace = max_spans_per_trace
        
        # Thread-safe data storage
        self._lock = threading.RLock()
        self._traces: Dict[str, Dict[str, TraceSpan]] = {}  # trace_id -> span_id -> span
        self._span_index: Dict[str, str] = {}  # span_id -> trace_id
        self._service_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._active_traces: Dict[str, TraceContext] = {}
        self._completed_traces: deque = deque(maxlen=max_traces)
        
        # Sampling configuration
        self._sampling_rate: float = 1.0  # Trace all spans by default
        self._sampling_rules: List[Callable[[str], bool]] = []
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Stream listeners for real-time trace access
        self._stream_listeners: List[Callable[[Dict[str, Any]], None]] = []
        
        # Context variables for automatic context management
        self._trace_context: ContextVar[Optional[TraceContext]] = ContextVar(
            'trace_context', default=None
        )
        
        logger.info("Distributed tracer initialized with max_traces=%d, max_spans_per_trace=%d",
                   max_traces, max_spans_per_trace)
    
    async def start(self):
        """Start the distributed tracer background tasks."""
        if self._running:
            return
            
        self._running = True
        self._cleanup_task = asyncio.create_task(self._background_cleanup())
        logger.info("Distributed tracer started")
    
    async def stop(self):
        """Stop the distributed tracer background tasks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Distributed tracer stopped")
    
    async def _background_cleanup(self):
        """Background task for periodic trace cleanup."""
        try:
            while self._running:
                await self._cleanup_old_traces()
                await asyncio.sleep(300)  # Run every 5 minutes
        except asyncio.CancelledError:
            logger.info("Trace cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in trace cleanup: {e}")
    
    async def _cleanup_old_traces(self):
        """Clean up old completed traces."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with self._lock:
            trace_ids_to_remove = []
            
            for trace_id, spans in self._traces.items():
                # Check if all spans in the trace are completed and old
                if all(span.end_time and span.end_time < cutoff_time for span in spans.values()):
                    trace_ids_to_remove.append(trace_id)
            
            for trace_id in trace_ids_to_remove:
                # Move to completed traces
                self._completed_traces.append(self._traces[trace_id].copy())
                del self._traces[trace_id]
                del self._active_traces[trace_id]
                
                # Clean up index
                for span_id in list(self._span_index.keys()):
                    if self._span_index[span_id] == trace_id:
                        del self._span_index[span_id]
    
    def set_trace_context(self, context: Optional[TraceContext]):
        """Set the current trace context."""
        self._trace_context.set(context)
    
    def get_current_context(self) -> Optional[TraceContext]:
        """Get the current trace context."""
        return self._trace_context.get()
    
    def create_trace_context(self, trace_id: Optional[str] = None,
                           parent_span_id: Optional[str] = None) -> TraceContext:
        """Create a new trace context."""
        if not trace_id:
            trace_id = str(uuid.uuid4()).replace('-', '')
        
        span_id = str(uuid.uuid4()).replace('-', '')
        
        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
    
    def start_span(self, name: str, span_type: SpanType = SpanType.INTERNAL,
                  service_name: str = "unknown", operation_name: str = "",
                  attributes: Optional[List[TraceAttribute]] = None,
                  parent_context: Optional[TraceContext] = None) -> TraceContext:
        """
        Start a new trace span.
        
        Args:
            name: Span name
            span_type: Type of span
            service_name: Name of the service
            operation_name: Operation being performed
            attributes: Optional span attributes
            parent_context: Parent trace context
            
        Returns:
            New trace context with span information
        """
        # Use provided context or create new one
        context = parent_context or self.get_current_context() or self.create_trace_context()
        
        # Create new span ID
        span_id = str(uuid.uuid4()).replace('-', '')
        
        # Create span
        span = TraceSpan(
            span_id=span_id,
            trace_id=context.trace_id,
            name=name,
            span_type=span_type,
            start_time=datetime.utcnow(),
            parent_span_id=context.parent_span_id,
            service_name=service_name,
            operation_name=operation_name or name,
            attributes=attributes or [],
            kind=self._determine_span_kind(span_type)
        )
        
        # Store span
        with self._lock:
            if context.trace_id not in self._traces:
                self._traces[context.trace_id] = {}
            
            # Check span limit per trace
            if len(self._traces[context.trace_id]) >= self.max_spans_per_trace:
                logger.warning(f"Max spans per trace reached for trace {context.trace_id}")
                return context
            
            self._traces[context.trace_id][span_id] = span
            self._span_index[span_id] = context.trace_id
        
        # Update service dependencies
        if parent_context:
            with self._lock:
                self._service_dependencies[service_name].add(parent_context.service_name)
        
        # Set new context
        new_context = TraceContext(
            trace_id=context.trace_id,
            span_id=span_id,
            parent_span_id=context.span_id,
            baggage=context.baggage.copy(),
            trace_flags=context.trace_flags,
            trace_state=context.trace_state
        )
        
        # Set as current context
        self.set_trace_context(new_context)
        
        logger.debug(f"Started span: {name} ({span_id}) in trace: {context.trace_id}")
        return new_context
    
    def end_span(self, status: TraceStatus = TraceStatus.OK,
                end_time: Optional[datetime] = None,
                attributes: Optional[List[TraceAttribute]] = None,
                events: Optional[List[TraceEvent]] = None) -> TraceContext:
        """
        End the current span.
        
        Args:
            status: Span completion status
            end_time: End timestamp (defaults to now)
            attributes: Optional additional attributes
            events: Optional span events
            
        Returns:
            Updated trace context
        """
        context = self.get_current_context()
        if not context:
            logger.warning("No active span to end")
            return None
        
        span_id = context.span_id
        trace_id = context.trace_id
        
        with self._lock:
            if trace_id in self._traces and span_id in self._traces[trace_id]:
                span = self._traces[trace_id][span_id]
                span.end_time = end_time or datetime.utcnow()
                span.status = status
                
                # Add attributes
                if attributes:
                    span.attributes.extend(attributes)
                
                # Add events
                if events:
                    span.events.extend(events)
                
                # Calculate duration
                duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
                span.attributes.append(TraceAttribute("duration_ms", duration_ms, "float"))
        
        # Stream completed span
        self._stream_completed_span(trace_id, span_id)
        
        # Return to parent context
        if context.parent_span_id:
            parent_context = TraceContext(
                trace_id=trace_id,
                span_id=context.parent_span_id,
                parent_span_id=span.parent_span_id,
                baggage=context.baggage,
                trace_flags=context.trace_flags,
                trace_state=context.trace_state
            )
            self.set_trace_context(parent_context)
            return parent_context
        else:
            # Root span completed, clear context
            self.set_trace_context(None)
            return None
    
    def add_span_attribute(self, key: str, value: Any, value_type: str = "string"):
        """Add an attribute to the current span."""
        context = self.get_current_context()
        if not context:
            return
        
        attribute = TraceAttribute(key, value, value_type)
        
        with self._lock:
            trace_id = context.trace_id
            span_id = context.span_id
            
            if trace_id in self._traces and span_id in self._traces[trace_id]:
                span = self._traces[trace_id][span_id]
                
                # Update existing attribute or add new one
                existing_attr = next((attr for attr in span.attributes if attr.key == key), None)
                if existing_attr:
                    existing_attr.value = value
                    existing_attr.type = value_type
                else:
                    span.attributes.append(attribute)
    
    def add_span_event(self, name: str, attributes: Optional[List[TraceAttribute]] = None):
        """Add an event to the current span."""
        context = self.get_current_context()
        if not context:
            return
        
        event = TraceEvent(
            name=name,
            timestamp=datetime.utcnow(),
            attributes=attributes or []
        )
        
        with self._lock:
            trace_id = context.trace_id
            span_id = context.span_id
            
            if trace_id in self._traces and span_id in self._traces[trace_id]:
                span = self._traces[trace_id][span_id]
                span.events.append(event)
    
    def link_span(self, linked_span_id: str):
        """Link the current span to another span."""
        context = self.get_current_context()
        if not context:
            return
        
        with self._lock:
            trace_id = context.trace_id
            span_id = context.span_id
            
            if trace_id in self._traces and span_id in self._traces[trace_id]:
                span = self._traces[trace_id][span_id]
                span.links.append(linked_span_id)
    
    def record_exception(self, exception: Exception, attributes: Optional[List[TraceAttribute]] = None):
        """Record an exception in the current span."""
        context = self.get_current_context()
        if not context:
            return
        
        exception_attrs = [
            TraceAttribute("exception.type", type(exception).__name__, "string"),
            TraceAttribute("exception.message", str(exception), "string"),
            TraceAttribute("exception.stacktrace", traceback.format_exc(), "string"),
        ]
        
        if attributes:
            exception_attrs.extend(attributes)
        
        self.add_span_event("exception", exception_attrs)
        self.end_span(TraceStatus.ERROR)
    
    def _determine_span_kind(self, span_type: SpanType) -> str:
        """Determine OpenTelemetry span kind from span type."""
        mapping = {
            SpanType.ENTRY: "SERVER",
            SpanType.EXIT: "CLIENT",
            SpanType.HTTP_REQUEST: "SERVER",
            SpanType.DATABASE: "CLIENT",
            SpanType.MESSAGE_QUEUE: "CLIENT",
            SpanType.CACHE: "CLIENT",
            SpanType.EXTERNAL_API: "CLIENT",
            SpanType.INTERNAL: "INTERNAL"
        }
        return mapping.get(span_type, "INTERNAL")
    
    def _stream_completed_span(self, trace_id: str, span_id: str):
        """Stream completed span to listeners."""
        span_data = self.get_span_data(trace_id, span_id)
        if span_data:
            for listener in self._stream_listeners:
                try:
                    listener(span_data)
                except Exception as e:
                    logger.error(f"Error in trace stream listener: {e}")
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, TraceSpan]]:
        """Get all spans for a trace."""
        with self._lock:
            return self._traces.get(trace_id, {}).copy()
    
    def get_span(self, trace_id: str, span_id: str) -> Optional[TraceSpan]:
        """Get a specific span."""
        with self._lock:
            if trace_id in self._traces and span_id in self._traces[trace_id]:
                return self._traces[trace_id][span_id]
        return None
    
    def get_span_data(self, trace_id: str, span_id: str) -> Optional[Dict[str, Any]]:
        """Get span data as dictionary for streaming."""
        span = self.get_span(trace_id, span_id)
        if not span:
            return None
        
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "name": span.name,
            "span_type": span.span_type.value,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "status": span.status.value,
            "parent_span_id": span.parent_span_id,
            "service_name": span.service_name,
            "operation_name": span.operation_name,
            "attributes": [{"key": attr.key, "value": attr.value, "type": attr.type} 
                          for attr in span.attributes],
            "events": [{"name": event.name, "timestamp": event.timestamp.isoformat(),
                       "attributes": [{"key": attr.key, "value": attr.value, "type": attr.type}
                                    for attr in event.attributes]}
                      for event in span.events],
            "links": span.links,
            "kind": span.kind
        }
    
    def get_traces_by_service(self, service_name: str, 
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[str]:
        """Get trace IDs containing spans for a specific service."""
        with self._lock:
            matching_traces = []
            
            for trace_id, spans in self._traces.items():
                # Check time range
                if start_time or end_time:
                    trace_start = min(span.start_time for span in spans.values())
                    trace_end = max(span.end_time or datetime.utcnow() for span in spans.values())
                    
                    if start_time and trace_end < start_time:
                        continue
                    if end_time and trace_start > end_time:
                        continue
                
                # Check if any span belongs to the service
                if any(span.service_name == service_name for span in spans.values()):
                    matching_traces.append(trace_id)
            
            return matching_traces
    
    def get_service_dependencies(self) -> Dict[str, List[str]]:
        """Get service dependency mapping."""
        with self._lock:
            return {service: list(dependencies) 
                   for service, dependencies in self._service_dependencies.items()}
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get trace statistics."""
        with self._lock:
            total_traces = len(self._traces)
            active_traces = len(self._active_traces)
            completed_traces = len(self._completed_traces)
            
            # Calculate span statistics
            total_spans = sum(len(spans) for spans in self._traces.values())
            error_spans = 0
            total_duration = 0
            
            for spans in self._traces.values():
                for span in spans.values():
                    if span.status == TraceStatus.ERROR:
                        error_spans += 1
                    if span.end_time:
                        total_duration += (span.end_time - span.start_time).total_seconds()
            
            # Service statistics
            service_stats = defaultdict(int)
            for spans in self._traces.values():
                for span in spans.values():
                    service_stats[span.service_name] += 1
            
            return {
                "total_traces": total_traces,
                "active_traces": active_traces,
                "completed_traces": completed_traces,
                "total_spans": total_spans,
                "error_spans": error_spans,
                "error_rate": (error_spans / total_spans * 100) if total_spans > 0 else 0,
                "avg_trace_duration": (total_duration / total_spans) if total_spans > 0 else 0,
                "services": dict(service_stats),
                "service_dependencies": self.get_service_dependencies()
            }
    
    def get_slowest_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest traces based on total duration."""
        with self._lock:
            trace_durations = []
            
            for trace_id, spans in self._traces.items():
                if all(span.end_time for span in spans.values()):  # Completed traces only
                    trace_start = min(span.start_time for span in spans.values())
                    trace_end = max(span.end_time for span in spans.values())
                    duration = (trace_end - trace_start).total_seconds()
                    
                    service_count = len(set(span.service_name for span in spans.values()))
                    
                    trace_durations.append({
                        "trace_id": trace_id,
                        "duration_seconds": duration,
                        "span_count": len(spans),
                        "service_count": service_count,
                        "start_time": trace_start.isoformat(),
                        "end_time": trace_end.isoformat()
                    })
            
            # Sort by duration (descending)
            trace_durations.sort(key=lambda x: x["duration_seconds"], reverse=True)
            
            return trace_durations[:limit]
    
    def set_sampling_rate(self, rate: float):
        """Set the sampling rate for trace collection."""
        self._sampling_rate = max(0.0, min(1.0, rate))  # Clamp between 0 and 1
        logger.info(f"Set sampling rate to {self._sampling_rate}")
    
    def add_sampling_rule(self, rule_func: Callable[[str], bool]):
        """Add a custom sampling rule."""
        self._sampling_rules.append(rule_func)
    
    def should_sample(self, trace_id: str) -> bool:
        """Determine if a trace should be sampled."""
        # Check sampling rate
        import random
        if random.random() > self._sampling_rate:
            return False
        
        # Check sampling rules
        for rule in self._sampling_rules:
            if not rule(trace_id):
                return False
        
        return True
    
    def add_stream_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """Add a real-time trace stream listener."""
        self._stream_listeners.append(listener)
    
    def export_trace(self, trace_id: str, format_type: str = "json") -> Optional[str]:
        """Export a trace in the specified format."""
        trace = self.get_trace(trace_id)
        if not trace:
            return None
        
        if format_type.lower() == "json":
            trace_data = {
                "trace_id": trace_id,
                "spans": [self.get_span_data(trace_id, span_id) for span_id in trace],
                "exported_at": datetime.utcnow().isoformat()
            }
            return json.dumps(trace_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


# Global distributed tracer instance
distributed_tracer = DistributedTracer()


# Context manager for automatic span management
class traced_operation:
    """Context manager for automatic span creation and management."""
    
    def __init__(self, name: str, span_type: SpanType = SpanType.INTERNAL,
                 service_name: str = "unknown", **kwargs):
        self.name = name
        self.span_type = span_type
        self.service_name = service_name
        self.kwargs = kwargs
        self.context = None
    
    def __enter__(self):
        self.context = distributed_tracer.start_span(
            self.name, self.span_type, self.service_name, **self.kwargs
        )
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            distributed_tracer.record_exception(exc_val)
        else:
            distributed_tracer.end_span(TraceStatus.OK)


# Decorator for automatic span creation
def trace_function(span_type: SpanType = SpanType.INTERNAL, service_name: str = "unknown"):
    """Decorator to automatically trace function execution."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            
            with traced_operation(operation_name, span_type, service_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for external use
def start_trace(name: str, **kwargs):
    """Start a new trace span."""
    return distributed_tracer.start_span(name, **kwargs)


def end_trace(status: TraceStatus = TraceStatus.OK):
    """End the current trace span."""
    return distributed_tracer.end_span(status)


def add_trace_attribute(key: str, value: Any, value_type: str = "string"):
    """Add an attribute to the current trace span."""
    distributed_tracer.add_span_attribute(key, value, value_type)


def add_trace_event(name: str, attributes: Optional[List[TraceAttribute]] = None):
    """Add an event to the current trace span."""
    distributed_tracer.add_span_event(name, attributes)


# OpenTelemetry compatibility helpers
def inject_trace_context(carrier: Dict[str, str]):
    """Inject trace context into a carrier (e.g., HTTP headers)."""
    context = distributed_tracer.get_current_context()
    if context:
        carrier["traceparent"] = f"00-{context.trace_id}-{context.span_id}-{context.trace_flags:02x}"
        if context.trace_state:
            carrier["tracestate"] = context.trace_state


def extract_trace_context(carrier: Dict[str, str]) -> Optional[TraceContext]:
    """Extract trace context from a carrier (e.g., HTTP headers)."""
    traceparent = carrier.get("traceparent")
    if not traceparent:
        return None
    
    try:
        parts = traceparent.split("-")
        if len(parts) >= 4:
            trace_id = parts[1]
            span_id = parts[2]
            trace_flags = int(parts[3], 16)
            
            return TraceContext(
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=trace_flags,
                trace_state=carrier.get("tracestate", "")
            )
    except (ValueError, IndexError):
        logger.warning(f"Invalid traceparent format: {traceparent}")
    
    return None