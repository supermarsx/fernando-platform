"""
Performance monitoring service for the Fernando platform.

This module provides comprehensive performance monitoring capabilities including:
- Request/response time tracking
- Database query performance
- External API call monitoring
- Resource utilization tracking
- Performance threshold alerting
- Performance trend analysis

Features:
- Real-time performance metrics
- Automated performance benchmarking
- Bottleneck detection
- Performance regression detection
- Resource usage correlation
- Performance optimization recommendations
"""

import asyncio
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import statistics
import psutil
import json


logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Types of performance metrics."""
    RESPONSE_TIME = "response_time"
    CPU_TIME = "cpu_time"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_QUERY_TIME = "db_query_time"
    EXTERNAL_API_TIME = "api_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class PerformanceLevel(Enum):
    """Performance threshold levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceData:
    """Performance measurement data."""
    metric_name: str
    value: float
    timestamp: datetime
    threshold_level: PerformanceLevel
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str = "ms"
    enabled: bool = True


@dataclass
class EndpointMetrics:
    """Metrics for a specific endpoint."""
    endpoint: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_updated: datetime = field(default_factory=datetime.utcnow)


class PerformanceMonitor:
    """
    Comprehensive performance monitoring service.
    
    Provides real-time performance tracking, threshold monitoring,
    and performance analytics.
    """
    
    def __init__(self, max_data_points: int = 10000):
        """Initialize the performance monitor.
        
        Args:
            max_data_points: Maximum data points to keep per metric
        """
        self.max_data_points = max_data_points
        
        # Thread-safe data storage
        self._lock = threading.RLock()
        self._performance_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_data_points)
        )
        self._endpoints: Dict[str, EndpointMetrics] = {}
        self._thresholds: List[PerformanceThreshold] = []
        self._performance_alerts: List[Callable[[PerformanceData], None]] = []
        
        # System performance tracking
        self._system_baseline: Dict[str, float] = {}
        self._resource_tracking: deque = deque(maxlen=1000)
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Default performance thresholds
        self._setup_default_thresholds()
        
        logger.info("Performance monitor initialized with max_data_points=%d", max_data_points)
    
    def _setup_default_thresholds(self):
        """Setup default performance thresholds."""
        default_thresholds = [
            PerformanceThreshold("response_time", 500, 2000, "ms"),
            PerformanceThreshold("db_query_time", 100, 500, "ms"),
            PerformanceThreshold("api_time", 1000, 5000, "ms"),
            PerformanceThreshold("memory_usage", 80, 95, "%"),
            PerformanceThreshold("cpu_usage", 70, 90, "%"),
            PerformanceThreshold("error_rate", 5, 10, "%"),
        ]
        
        self._thresholds.extend(default_thresholds)
    
    async def start(self):
        """Start the performance monitoring."""
        if self._running:
            return
            
        self._running = True
        self._monitoring_task = asyncio.create_task(self._background_monitoring())
        logger.info("Performance monitor started")
    
    async def stop(self):
        """Stop the performance monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitor stopped")
    
    async def _background_monitoring(self):
        """Background task for continuous performance monitoring."""
        try:
            while self._running:
                await self._collect_system_performance()
                await self._check_performance_thresholds()
                await asyncio.sleep(30)  # Monitor every 30 seconds
        except asyncio.CancelledError:
            logger.info("Performance monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")
    
    async def _collect_system_performance(self):
        """Collect system-level performance metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            
            performance_data = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_read_bytes": disk.read_bytes if disk else 0,
                "disk_write_bytes": disk.write_bytes if disk else 0,
                "network_sent_bytes": network.bytes_sent,
                "network_recv_bytes": network.bytes_recv,
                "timestamp": datetime.utcnow()
            }
            
            self._resource_tracking.append(performance_data)
            
            # Store individual metrics
            self.record_performance_metric("cpu_usage", cpu_percent, 
                                         {"component": "system"})
            self.record_performance_metric("memory_usage", memory.percent,
                                         {"component": "system"})
            
        except Exception as e:
            logger.error(f"Error collecting system performance: {e}")
    
    async def _check_performance_thresholds(self):
        """Check performance metrics against thresholds."""
        current_time = datetime.utcnow()
        
        for threshold in self._thresholds:
            if not threshold.enabled:
                continue
            
            # Get recent metric data
            recent_data = self.get_recent_metrics(threshold.metric_name, minutes=5)
            
            if not recent_data:
                continue
            
            # Calculate average
            avg_value = statistics.mean([d.value for d in recent_data])
            
            # Determine performance level
            if avg_value >= threshold.critical_threshold:
                level = PerformanceLevel.CRITICAL
            elif avg_value >= threshold.warning_threshold:
                level = PerformanceLevel.POOR
            elif avg_value >= threshold.warning_threshold * 0.7:
                level = PerformanceLevel.ACCEPTABLE
            elif avg_value >= threshold.warning_threshold * 0.5:
                level = PerformanceLevel.GOOD
            else:
                level = PerformanceLevel.EXCELLENT
            
            # Create performance data point
            perf_data = PerformanceData(
                metric_name=threshold.metric_name,
                value=avg_value,
                timestamp=current_time,
                threshold_level=level,
                context={"threshold_warning": threshold.warning_threshold,
                        "threshold_critical": threshold.critical_threshold}
            )
            
            # Alert if performance is poor or critical
            if level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                for alert_handler in self._performance_alerts:
                    try:
                        alert_handler(perf_data)
                    except Exception as e:
                        logger.error(f"Error in performance alert handler: {e}")
    
    def record_performance_metric(self, metric_name: str, value: float,
                                context: Optional[Dict[str, Any]] = None,
                                tags: Optional[List[str]] = None) -> None:
        """Record a performance metric."""
        if context is None:
            context = {}
        if tags is None:
            tags = []
        
        # Determine threshold level
        level = self._determine_performance_level(metric_name, value)
        
        perf_data = PerformanceData(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.utcnow(),
            threshold_level=level,
            context=context,
            tags=tags
        )
        
        with self._lock:
            self._performance_data[metric_name].append(perf_data)
    
    def track_request_performance(self, method: str, endpoint: str,
                                response_time_ms: float, status_code: int,
                                context: Optional[Dict[str, Any]] = None) -> None:
        """Track API request performance."""
        endpoint_key = f"{method.upper()} {endpoint}"
        
        with self._lock:
            if endpoint_key not in self._endpoints:
                self._endpoints[endpoint_key] = EndpointMetrics(
                    endpoint=endpoint,
                    method=method.upper()
                )
            
            metrics = self._endpoints[endpoint_key]
            metrics.total_requests += 1
            metrics.total_response_time += response_time_ms
            
            if status_code < 400:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
            
            metrics.response_times.append(response_time_ms)
            metrics.min_response_time = min(metrics.min_response_time, response_time_ms)
            metrics.max_response_time = max(metrics.max_response_time, response_time_ms)
            metrics.last_updated = datetime.utcnow()
        
        # Record individual metrics
        self.record_performance_metric(
            "response_time", response_time_ms,
            {"endpoint": endpoint, "method": method, "status_code": status_code},
            ["api", method.lower()]
        )
        
        # Record error rate
        if metrics.total_requests > 0:
            error_rate = (metrics.failed_requests / metrics.total_requests) * 100
            self.record_performance_metric(
                "error_rate", error_rate,
                {"endpoint": endpoint, "method": method},
                ["api", "error_rate"]
            )
    
    def track_database_query(self, query: str, duration_ms: float,
                           context: Optional[Dict[str, Any]] = None) -> None:
        """Track database query performance."""
        self.record_performance_metric(
            "db_query_time", duration_ms,
            {"query_type": self._classify_query(query), "query_length": len(query)},
            ["database", "query"]
        )
    
    def track_external_api_call(self, api_name: str, endpoint: str,
                              duration_ms: float, status_code: int,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Track external API call performance."""
        self.record_performance_metric(
            "api_time", duration_ms,
            {"api": api_name, "endpoint": endpoint, "status_code": status_code},
            ["external_api", api_name.lower()]
        )
    
    def track_cache_performance(self, operation: str, hit: bool,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Track cache performance."""
        # Track cache hits/misses
        metric_value = 1.0 if hit else 0.0
        self.record_performance_metric(
            "cache_hit_rate", metric_value,
            {"operation": operation},
            ["cache", operation]
        )
    
    def _classify_query(self, query: str) -> str:
        """Classify database query type."""
        query_upper = query.upper().strip()
        if query_upper.startswith("SELECT"):
            return "select"
        elif query_upper.startswith("INSERT"):
            return "insert"
        elif query_upper.startswith("UPDATE"):
            return "update"
        elif query_upper.startswith("DELETE"):
            return "delete"
        else:
            return "other"
    
    def _determine_performance_level(self, metric_name: str, value: float) -> PerformanceLevel:
        """Determine performance level based on thresholds."""
        threshold = next((t for t in self._thresholds if t.metric_name == metric_name), None)
        
        if not threshold:
            return PerformanceLevel.GOOD  # Default level if no threshold
        
        if value >= threshold.critical_threshold:
            return PerformanceLevel.CRITICAL
        elif value >= threshold.warning_threshold:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.GOOD
    
    def get_recent_metrics(self, metric_name: str, minutes: int = 60) -> List[PerformanceData]:
        """Get recent metrics for a specific metric."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self._lock:
            metrics = list(self._performance_data.get(metric_name, []))
        
        return [m for m in metrics if m.timestamp >= cutoff_time]
    
    def get_endpoint_performance(self, endpoint: str) -> Optional[EndpointMetrics]:
        """Get performance metrics for a specific endpoint."""
        with self._lock:
            # Find endpoint metrics (case-insensitive search)
            for key, metrics in self._endpoints.items():
                if key.upper() == endpoint.upper():
                    return metrics
        return None
    
    def get_performance_statistics(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get performance statistics for a metric over a time period."""
        recent_data = self.get_recent_metrics(metric_name, hours * 60)
        
        if not recent_data:
            return {"error": "No data available"}
        
        values = [d.value for d in recent_data]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "p90": self._percentile(values, 90),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
            "time_period_hours": hours
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from values list."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a comprehensive performance summary."""
        with self._lock:
            endpoint_count = len(self._endpoints)
            
            # Calculate overall system performance
            system_metrics = {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
            
            # Get recent performance data
            recent_performance = {}
            for metric_name in self._performance_data:
                recent_data = self.get_recent_metrics(metric_name, 60)  # Last hour
                if recent_data:
                    recent_performance[metric_name] = {
                        "count": len(recent_data),
                        "latest_value": recent_data[-1].value,
                        "avg_last_hour": statistics.mean([d.value for d in recent_data])
                    }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "monitored_endpoints": endpoint_count,
                "system_performance": system_metrics,
                "recent_performance": recent_performance,
                "threshold_status": self._get_threshold_status(),
                "performance_trends": self._analyze_performance_trends()
            }
    
    def _get_threshold_status(self) -> Dict[str, str]:
        """Get current threshold status for all metrics."""
        status = {}
        
        for threshold in self._thresholds:
            if not threshold.enabled:
                continue
            
            recent_data = self.get_recent_metrics(threshold.metric_name, 30)  # Last 30 minutes
            if recent_data:
                avg_value = statistics.mean([d.value for d in recent_data])
                
                if avg_value >= threshold.critical_threshold:
                    status[threshold.metric_name] = "critical"
                elif avg_value >= threshold.warning_threshold:
                    status[threshold.metric_name] = "warning"
                else:
                    status[threshold.metric_name] = "normal"
            else:
                status[threshold.metric_name] = "no_data"
        
        return status
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        trends = {}
        
        for metric_name in self._performance_data:
            recent_data = self.get_recent_metrics(metric_name, 120)  # Last 2 hours
            
            if len(recent_data) < 10:  # Need enough data points
                continue
            
            # Split data into two halves
            midpoint = len(recent_data) // 2
            first_half = [d.value for d in recent_data[:midpoint]]
            second_half = [d.value for d in recent_data[midpoint:]]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            # Calculate trend
            if second_avg > first_avg * 1.1:
                trend = "increasing"
            elif second_avg < first_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
            
            trends[metric_name] = {
                "trend": trend,
                "change_percent": ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
            }
        
        return trends
    
    def add_performance_alert(self, alert_handler: Callable[[PerformanceData], None]):
        """Add a performance alert handler."""
        self._performance_alerts.append(alert_handler)
    
    def set_performance_threshold(self, metric_name: str, warning_threshold: float,
                                critical_threshold: float, unit: str = "ms"):
        """Set or update a performance threshold."""
        # Remove existing threshold
        self._thresholds = [t for t in self._thresholds if t.metric_name != metric_name]
        
        # Add new threshold
        threshold = PerformanceThreshold(
            metric_name=metric_name,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            unit=unit
        )
        self._thresholds.append(threshold)
        
        logger.info(f"Updated performance threshold for {metric_name}: warning={warning_threshold}, critical={critical_threshold}")
    
    def get_slowest_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest endpoints based on average response time."""
        with self._lock:
            endpoint_list = []
            
            for endpoint_key, metrics in self._endpoints.items():
                if metrics.total_requests > 0:
                    avg_response_time = metrics.total_response_time / metrics.total_requests
                    error_rate = (metrics.failed_requests / metrics.total_requests) * 100
                    
                    endpoint_list.append({
                        "endpoint": metrics.endpoint,
                        "method": metrics.method,
                        "avg_response_time_ms": avg_response_time,
                        "total_requests": metrics.total_requests,
                        "error_rate_percent": error_rate,
                        "success_rate_percent": (metrics.successful_requests / metrics.total_requests) * 100
                    })
            
            # Sort by average response time (descending)
            endpoint_list.sort(key=lambda x: x["avg_response_time_ms"], reverse=True)
            
            return endpoint_list[:limit]


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for automatic performance tracking
def monitor_performance(metric_name: str = None):
    """Decorator to automatically track function performance."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            name = metric_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_performance_metric(name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_performance_metric(f"{name}_error", duration_ms)
                raise
        return wrapper
    return decorator


# Context manager for performance tracking
class performance_timer:
    """Context manager for timing operations."""
    
    def __init__(self, metric_name: str, context: Optional[Dict[str, Any]] = None):
        self.metric_name = metric_name
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            performance_monitor.record_performance_metric(self.metric_name, duration_ms, self.context)


# Convenience functions for external use
def track_response_time(endpoint: str, method: str, response_time_ms: float, status_code: int):
    """Track API response time."""
    performance_monitor.track_request_performance(method, endpoint, response_time_ms, status_code)


def track_db_query(query: str, duration_ms: float):
    """Track database query performance."""
    performance_monitor.track_database_query(query, duration_ms)


def track_api_call(api_name: str, endpoint: str, duration_ms: float, status_code: int):
    """Track external API call performance."""
    performance_monitor.track_external_api_call(api_name, endpoint, duration_ms, status_code)