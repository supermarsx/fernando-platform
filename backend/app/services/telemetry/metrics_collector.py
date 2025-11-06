"""
Real-time metrics collection service for the Fernando platform.

This module provides comprehensive metrics collection capabilities including:
- System metrics (CPU, memory, disk, network)
- Application metrics (requests, responses, errors)
- Business metrics (user actions, feature usage)
- Custom metrics (billing, licensing, payments)

Features:
- Real-time collection and aggregation
- Efficient in-memory storage with configurable limits
- Thread-safe operations
- Automatic cleanup of expired metrics
- Integration with popular monitoring backends
"""

import asyncio
import time
import threading
import psutil
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import hashlib


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricData:
    """Data structure for storing individual metric points."""
    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    labels: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class SystemMetrics:
    """System metrics snapshot."""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_usage_percent: float
    disk_used: int
    disk_total: int
    network_sent: int
    network_recv: int
    process_count: int
    thread_count: int
    timestamp: datetime


class MetricsCollector:
    """
    High-performance real-time metrics collection service.
    
    Provides thread-safe metrics collection with automatic aggregation
    and cleanup capabilities.
    """
    
    def __init__(self, max_metrics: int = 10000, retention_period_hours: int = 24):
        """Initialize the metrics collector.
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
            retention_period_hours: How long to keep metrics before cleanup
        """
        self.max_metrics = max_metrics
        self.retention_period = timedelta(hours=retention_period_hours)
        
        # Thread-safe data structures
        self._lock = threading.RLock()
        self._metrics: deque = deque(maxlen=max_metrics)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(lambda: deque(maxlen=1000))
        
        # Aggregation buckets for time-series data
        self._minute_buckets: Dict[str, List[MetricData]] = defaultdict(list)
        self._hourly_buckets: Dict[str, List[MetricData]] = defaultdict(list)
        
        # Background tasks
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("Metrics collector initialized with max_metrics=%d, retention_period_hours=%d",
                   max_metrics, retention_period_hours)
    
    async def start(self):
        """Start the background metrics collection tasks."""
        if self._running:
            return
            
        self._running = True
        self._background_task = asyncio.create_task(self._background_collector())
        logger.info("Metrics collector started")
    
    async def stop(self):
        """Stop the background metrics collection tasks."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")
    
    async def _background_collector(self):
        """Background task for continuous metrics collection."""
        try:
            while self._running:
                # Collect system metrics every 30 seconds
                await self._collect_system_metrics()
                
                # Clean up expired metrics every 5 minutes
                await self._cleanup_expired_metrics()
                
                # Aggregate metrics every minute
                await self._aggregate_metrics()
                
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Background collector task cancelled")
        except Exception as e:
            logger.error(f"Error in background collector: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Process information
            process_count = len(psutil.pids())
            thread_count = sum(p.num_threads() for p in psutil.process_iter(['num_threads']) 
                             if p.info['num_threads'])
            
            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_total=memory.total,
                disk_usage_percent=disk.percent,
                disk_used=disk.used,
                disk_total=disk.total,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
                timestamp=datetime.utcnow()
            )
            
            # Store system metrics
            self.record_metric("system.cpu.percent", cpu_percent, MetricType.GAUGE, 
                             labels={"host": "localhost"})
            self.record_metric("system.memory.percent", memory.percent, MetricType.GAUGE,
                             labels={"host": "localhost"})
            self.record_metric("system.disk.percent", disk.percent, MetricType.GAUGE,
                             labels={"host": "localhost"})
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _cleanup_expired_metrics(self):
        """Remove expired metrics from all storage structures."""
        cutoff_time = datetime.utcnow() - self.retention_period
        
        with self._lock:
            # Clean main metrics deque
            while self._metrics and self._metrics[0].timestamp < cutoff_time:
                self._metrics.popleft()
            
            # Clean buckets
            for bucket_dict in [self._minute_buckets, self._hourly_buckets]:
                for name in bucket_dict:
                    bucket_dict[name] = [
                        m for m in bucket_dict[name] if m.timestamp >= cutoff_time
                    ]
    
    async def _aggregate_metrics(self):
        """Aggregate metrics into time buckets."""
        current_time = datetime.utcnow()
        minute_bucket = current_time.replace(second=0, microsecond=0)
        
        with self._lock:
            # Move recent metrics to minute bucket
            for metric in list(self._metrics):
                if metric.timestamp >= minute_bucket:
                    self._minute_buckets[metric.name].append(metric)
    
    def record_metric(self, name: str, value: float, metric_type: MetricType,
                     labels: Optional[Dict[str, Any]] = None,
                     tags: Optional[List[str]] = None) -> None:
        """
        Record a new metric point.
        
        Args:
            name: Metric name (e.g., "requests.total", "response.time")
            value: Metric value
            metric_type: Type of metric (counter, gauge, histogram, timer)
            labels: Optional labels for categorization
            tags: Optional tags for filtering
        """
        if labels is None:
            labels = {}
        if tags is None:
            tags = []
        
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            metric_type=metric_type,
            labels=labels,
            tags=tags
        )
        
        with self._lock:
            self._metrics.append(metric)
            
            # Update aggregate data structures
            if metric_type == MetricType.COUNTER:
                key = self._make_key(name, labels)
                self._counters[key] += value
            elif metric_type == MetricType.GAUGE:
                key = self._make_key(name, labels)
                self._gauges[key] = value
            elif metric_type == MetricType.HISTOGRAM:
                key = self._make_key(name, labels)
                self._histograms[key].append(value)
    
    def increment_counter(self, name: str, value: float = 1.0,
                         labels: Optional[Dict[str, Any]] = None,
                         tags: Optional[List[str]] = None) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, labels, tags)
    
    def set_gauge(self, name: str, value: float,
                 labels: Optional[Dict[str, Any]] = None,
                 tags: Optional[List[str]] = None) -> None:
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, labels, tags)
    
    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict[str, Any]] = None,
                        tags: Optional[List[str]] = None) -> None:
        """Record a histogram metric."""
        self.record_metric(name, value, MetricType.HISTOGRAM, labels, tags)
    
    def record_timer(self, name: str, duration_seconds: float,
                    labels: Optional[Dict[str, Any]] = None,
                    tags: Optional[List[str]] = None) -> None:
        """Record a timer metric (specialized histogram for durations)."""
        self.record_metric(name, duration_seconds, MetricType.TIMER, labels, tags)
    
    def get_current_value(self, name: str, labels: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Get the current value for a gauge metric."""
        key = self._make_key(name, labels or {})
        return self._gauges.get(key)
    
    def get_counter_value(self, name: str, labels: Optional[Dict[str, Any]] = None) -> float:
        """Get the cumulative value for a counter metric."""
        key = self._make_key(name, labels or {})
        return self._counters.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, float]]:
        """Get statistics for a histogram metric."""
        key = self._make_key(name, labels or {})
        values = list(self._histograms.get(key, []))
        
        if not values:
            return None
        
        values.sort()
        count = len(values)
        return {
            "count": count,
            "min": values[0],
            "max": values[-1],
            "mean": sum(values) / count,
            "p50": values[int(count * 0.5)],
            "p90": values[int(count * 0.9)],
            "p95": values[int(count * 0.95)],
            "p99": values[int(count * 0.99)]
        }
    
    def get_recent_metrics(self, name: str, duration_minutes: int = 60,
                          labels: Optional[Dict[str, Any]] = None) -> List[MetricData]:
        """Get recent metrics within the specified duration."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            filtered_metrics = [
                m for m in self._metrics
                if m.name == name and m.timestamp >= cutoff_time
            ]
            
            if labels:
                filtered_metrics = [
                    m for m in filtered_metrics
                    if all(m.labels.get(k) == v for k, v in labels.items())
                ]
            
            return sorted(filtered_metrics, key=lambda x: x.timestamp)
    
    def get_system_metrics_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current system metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics snapshot: {e}")
            return {}
    
    def _make_key(self, name: str, labels: Dict[str, Any]) -> str:
        """Create a unique key for metrics with labels."""
        label_str = json.dumps(labels, sort_keys=True, default=str)
        return f"{name}:{hashlib.md5(label_str.encode()).hexdigest()[:8]}"
    
    def export_metrics(self, format_type: str = "json") -> str:
        """
        Export all metrics in the specified format.
        
        Args:
            format_type: Export format ("json", "prometheus")
            
        Returns:
            Exported metrics as string
        """
        with self._lock:
            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: {
                        "count": len(values),
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0,
                        "mean": sum(values) / len(values) if values else 0
                    }
                    for name, values in self._histograms.items()
                },
                "system": self.get_system_metrics_snapshot()
            }
            
            if format_type.lower() == "json":
                return json.dumps(metrics_data, indent=2, default=str)
            elif format_type.lower() == "prometheus":
                return self._export_prometheus_format(metrics_data)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_prometheus_format(self, metrics_data: Dict[str, Any]) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        # Add counters
        for name, value in metrics_data["counters"].items():
            lines.append(f"{name} {value}")
        
        # Add gauges
        for name, value in metrics_data["gauges"].items():
            lines.append(f"{name} {value}")
        
        # Add histograms
        for name, stats in metrics_data["histograms"].items():
            for stat, value in stats.items():
                lines.append(f"{name}_{stat} {value}")
        
        return "\n".join(lines)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of collected metrics."""
        with self._lock:
            return {
                "total_metrics": len(self._metrics),
                "active_counters": len(self._counters),
                "active_gauges": len(self._gauges),
                "active_histograms": len(self._histograms),
                "storage_usage": {
                    "current_metrics": len(self._metrics),
                    "max_metrics": self.max_metrics,
                    "usage_percent": (len(self._metrics) / self.max_metrics) * 100
                },
                "system_snapshot": self.get_system_metrics_snapshot()
            }


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Convenience functions for external use
def record_business_metric(name: str, value: float, **kwargs):
    """Record a business metric."""
    metrics_collector.record_metric(f"business.{name}", value, MetricType.GAUGE, kwargs)


def record_application_metric(name: str, value: float, **kwargs):
    """Record an application metric."""
    metrics_collector.record_metric(f"app.{name}", value, MetricType.GAUGE, kwargs)


def record_custom_metric(name: str, value: float, **kwargs):
    """Record a custom metric."""
    metrics_collector.record_metric(f"custom.{name}", value, MetricType.GAUGE, kwargs)


def increment_metric(name: str, value: float = 1.0, **kwargs):
    """Increment a counter metric."""
    metrics_collector.increment_counter(f"metric.{name}", value, kwargs)


def timer_metric(name: str):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics_collector.record_timer(f"function.{name}", duration)
        return wrapper
    return decorator