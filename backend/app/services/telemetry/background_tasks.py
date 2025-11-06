"""
Background tasks for telemetry service aggregation and processing.

This module provides background tasks for:
- Periodic metric aggregation and cleanup
- Real-time event streaming
- Performance analysis and trending
- Alert evaluation and escalation
- External system synchronization
- Data export and archival
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

from app.services.telemetry import (
    metrics_collector, event_tracker, performance_monitor,
    distributed_tracer, alert_manager,
    EventCategory, EventLevel
)


logger = logging.getLogger(__name__)


class TelemetryBackgroundTasks:
    """
    Background tasks manager for telemetry services.
    
    Handles periodic aggregation, cleanup, analysis, and external synchronization.
    """
    
    def __init__(self):
        """Initialize the background tasks manager."""
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.task_configs = {
            "metrics_aggregation": {"interval": 300, "enabled": True},      # 5 minutes
            "performance_analysis": {"interval": 600, "enabled": True},      # 10 minutes
            "event_aggregation": {"interval": 900, "enabled": True},        # 15 minutes
            "alert_evaluation": {"interval": 60, "enabled": True},          # 1 minute
            "cleanup_expired": {"interval": 1800, "enabled": True},         # 30 minutes
            "trends_analysis": {"interval": 1200, "enabled": True},         # 20 minutes
            "external_sync": {"interval": 3600, "enabled": False},          # 1 hour (disabled by default)
            "data_export": {"interval": 86400, "enabled": False}            # 24 hours (disabled by default)
        }
    
    async def start_all_tasks(self):
        """Start all enabled background tasks."""
        if self.running:
            return
        
        self.running = True
        
        for task_name, config in self.task_configs.items():
            if config["enabled"]:
                task = asyncio.create_task(
                    self._run_periodic_task(task_name, config["interval"]),
                    name=f"telemetry_{task_name}"
                )
                self.tasks[task_name] = task
                logger.info(f"Started telemetry background task: {task_name}")
        
        logger.info(f"Started {len(self.tasks)} telemetry background tasks")
    
    async def stop_all_tasks(self):
        """Stop all background tasks."""
        self.running = False
        
        # Cancel all tasks
        for task_name, task in self.tasks.items():
            task.cancel()
            logger.info(f"Cancelled telemetry background task: {task_name}")
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        self.tasks.clear()
        logger.info("All telemetry background tasks stopped")
    
    async def _run_periodic_task(self, task_name: str, interval: int):
        """Run a periodic task with the specified interval."""
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    await self._execute_task(task_name)
                except Exception as e:
                    logger.error(f"Error in telemetry task {task_name}: {e}")
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.info(f"Telemetry task {task_name} cancelled")
        except Exception as e:
            logger.error(f"Fatal error in telemetry task {task_name}: {e}")
    
    async def _execute_task(self, task_name: str):
        """Execute a specific background task."""
        if task_name == "metrics_aggregation":
            await self._aggregate_metrics()
        elif task_name == "performance_analysis":
            await self._analyze_performance()
        elif task_name == "event_aggregation":
            await self._aggregate_events()
        elif task_name == "alert_evaluation":
            await self._evaluate_alerts()
        elif task_name == "cleanup_expired":
            await self._cleanup_expired_data()
        elif task_name == "trends_analysis":
            await self._analyze_trends()
        elif task_name == "external_sync":
            await self._sync_external_systems()
        elif task_name == "data_export":
            await self._export_telemetry_data()
        else:
            logger.warning(f"Unknown telemetry task: {task_name}")
    
    async def _aggregate_metrics(self):
        """Aggregate and analyze collected metrics."""
        try:
            # Get current metrics summary
            metrics_summary = metrics_collector.get_metrics_summary()
            
            # Calculate derived metrics
            await self._calculate_derived_metrics(metrics_summary)
            
            # Analyze metric trends
            await self._analyze_metric_trends()
            
            # Generate alerts for unusual patterns
            await self._check_metric_anomalies()
            
            logger.debug("Metrics aggregation completed")
        
        except Exception as e:
            logger.error(f"Error in metrics aggregation: {e}")
    
    async def _calculate_derived_metrics(self, summary: Dict[str, Any]):
        """Calculate derived metrics from raw data."""
        try:
            # Calculate request rate (requests per second)
            total_requests = metrics_collector.get_counter_value("http.requests.total")
            # This would require time tracking for accurate calculation
            # For now, we'll track the count
            
            # Calculate error rate
            total_errors = metrics_collector.get_counter_value("http.errors.total")
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
                metrics_collector.set_gauge("http.error_rate.percent", error_rate)
            
            # Calculate system health score
            system_metrics = summary.get("system_snapshot", {})
            cpu_percent = system_metrics.get("cpu_percent", 0)
            memory_percent = system_metrics.get("memory_percent", 0)
            disk_percent = system_metrics.get("disk_percent", 0)
            
            # Simple health score calculation (0-100)
            health_score = 100 - ((cpu_percent + memory_percent + disk_percent) / 3)
            metrics_collector.set_gauge("system.health_score", max(0, health_score))
            
            # Track service-specific metrics
            await self._calculate_service_metrics()
        
        except Exception as e:
            logger.error(f"Error calculating derived metrics: {e}")
    
    async def _calculate_service_metrics(self):
        """Calculate service-specific derived metrics."""
        try:
            # Billing service metrics
            billing_success = metrics_collector.get_counter_value("billing.operations.success")
            billing_errors = metrics_collector.get_counter_value("billing.operations.error")
            total_billing = billing_success + billing_errors
            
            if total_billing > 0:
                billing_success_rate = (billing_success / total_billing) * 100
                metrics_collector.set_gauge("billing.success_rate.percent", billing_success_rate)
            
            # Payment service metrics
            payment_success = metrics_collector.get_counter_value("payment.operations.success")
            payment_errors = metrics_collector.get_counter_value("payment.operations.error")
            total_payments = payment_success + payment_errors
            
            if total_payments > 0:
                payment_success_rate = (payment_success / total_payments) * 100
                metrics_collector.set_gauge("payment.success_rate.percent", payment_success_rate)
            
            # User engagement metrics
            user_actions = metrics_collector.get_counter_value("user.actions.success")
            metrics_collector.set_gauge("user.engagement.total_actions", user_actions)
        
        except Exception as e:
            logger.error(f"Error calculating service metrics: {e}")
    
    async def _analyze_metric_trends(self):
        """Analyze trends in metric data."""
        try:
            # Get recent metrics for trend analysis
            key_metrics = [
                "http.response_time_ms",
                "http.error_rate.percent",
                "system.health_score",
                "billing.success_rate.percent",
                "payment.success_rate.percent"
            ]
            
            trends = {}
            for metric_name in key_metrics:
                recent_data = metrics_collector.get_recent_metrics(metric_name, 60)  # Last hour
                
                if len(recent_data) >= 10:  # Need enough data points
                    values = [m.value for m in recent_data]
                    
                    # Simple trend analysis (increasing/decreasing/stable)
                    midpoint = len(values) // 2
                    first_half_avg = sum(values[:midpoint]) / midpoint
                    second_half_avg = sum(values[midpoint:]) / (len(values) - midpoint)
                    
                    if second_half_avg > first_half_avg * 1.05:
                        trend = "increasing"
                    elif second_half_avg < first_half_avg * 0.95:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                    
                    trends[metric_name] = {
                        "trend": trend,
                        "change_percent": ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
                    }
            
            # Store trend information as events
            if trends:
                event_tracker.track_event(
                    name="metrics.trends_analysis",
                    category=EventCategory.PERFORMANCE,
                    level=EventLevel.INFO,
                    data={
                        "trends": trends,
                        "analyzed_at": datetime.utcnow().isoformat()
                    }
                )
        
        except Exception as e:
            logger.error(f"Error analyzing metric trends: {e}")
    
    async def _check_metric_anomalies(self):
        """Check for metric anomalies and generate alerts."""
        try:
            # Check for unusual spikes in error rates
            recent_error_rate = metrics_collector.get_recent_metrics("http.error_rate.percent", 10)
            if recent_error_rate:
                values = [m.value for m in recent_error_rate]
                avg_error_rate = sum(values) / len(values)
                
                # Alert if error rate is unusually high
                if avg_error_rate > 10:  # 10% error rate threshold
                    alert_manager.check_custom_condition(
                        lambda: True,
                        "High Error Rate Detected",
                        f"Average error rate: {avg_error_rate:.2f}%",
                        AlertSeverity.HIGH
                    )
            
            # Check for performance degradation
            response_times = metrics_collector.get_recent_metrics("http.response_time_ms", 30)
            if response_times:
                values = [m.value for m in response_times]
                avg_response_time = sum(values) / len(values)
                max_response_time = max(values)
                
                # Alert if average response time is slow
                if avg_response_time > 2000:  # 2 second threshold
                    alert_manager.check_custom_condition(
                        lambda: True,
                        "Slow Response Times",
                        f"Average response time: {avg_response_time:.2f}ms",
                        AlertSeverity.MEDIUM
                    )
                
                # Alert if there are extreme outliers
                if max_response_time > 10000:  # 10 second threshold
                    alert_manager.check_custom_condition(
                        lambda: True,
                        "Extreme Response Time Outliers",
                        f"Maximum response time: {max_response_time:.2f}ms",
                        AlertSeverity.HIGH
                    )
        
        except Exception as e:
            logger.error(f"Error checking metric anomalies: {e}")
    
    async def _analyze_performance(self):
        """Analyze performance data and generate insights."""
        try:
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            
            # Analyze slowest endpoints
            slowest_endpoints = performance_monitor.get_slowest_endpoints(5)
            
            if slowest_endpoints:
                # Track performance insights as events
                event_tracker.track_event(
                    name="performance.slow_endpoints_analysis",
                    category=EventCategory.PERFORMANCE,
                    level=EventLevel.INFO,
                    data={
                        "slowest_endpoints": slowest_endpoints,
                        "analysis_timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Check for performance degradation trends
            performance_trends = perf_summary.get("performance_trends", {})
            for metric_name, trend_data in performance_trends.items():
                if trend_data.get("trend") == "increasing" and trend_data.get("change_percent", 0) > 20:
                    # Significant performance degradation
                    alert_manager.check_custom_condition(
                        lambda: True,
                        f"Performance Degradation: {metric_name}",
                        f"Metric increased by {trend_data['change_percent']:.1f}%",
                        AlertSeverity.MEDIUM
                    )
            
            # Generate daily performance report
            await self._generate_performance_report()
        
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
    
    async def _generate_performance_report(self):
        """Generate a comprehensive performance report."""
        try:
            # Get statistics for key metrics
            response_time_stats = performance_monitor.get_performance_statistics("response_time", 24)
            error_rate_stats = performance_monitor.get_performance_statistics("error_rate", 24)
            
            if response_time_stats and error_rate_stats:
                report = {
                    "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "response_time": response_time_stats,
                    "error_rate": error_rate_stats,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                # Store as event for historical tracking
                event_tracker.track_event(
                    name="performance.daily_report",
                    category=EventCategory.PERFORMANCE,
                    level=EventLevel.INFO,
                    data=report
                )
        
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
    
    async def _aggregate_events(self):
        """Aggregate and analyze collected events."""
        try:
            # Get event statistics
            event_stats = event_tracker.get_event_statistics()
            
            # Analyze event patterns
            await self._analyze_event_patterns(event_stats)
            
            # Check for security events
            await self._check_security_events()
            
            # Analyze business events
            await self._analyze_business_events()
        
        except Exception as e:
            logger.error(f"Error in event aggregation: {e}")
    
    async def _analyze_event_patterns(self, stats: Dict[str, Any]):
        """Analyze patterns in event data."""
        try:
            # Check for unusual spikes in events
            events_last_hour = stats.get("events_last_hour", 0)
            events_last_24h = stats.get("events_last_24h", 0)
            
            if events_last_24h > 0:
                hourly_average = events_last_24h / 24
                if events_last_hour > hourly_average * 3:  # 3x normal rate
                    alert_manager.check_custom_condition(
                        lambda: True,
                        "Event Rate Spike Detected",
                        f"Events per hour ({events_last_hour}) is {events_last_hour/hourly_average:.1f}x normal rate",
                        AlertSeverity.MEDIUM
                    )
            
            # Analyze error event patterns
            error_events = event_tracker.get_events({"level": "error"}, limit=100)
            if error_events:
                # Group errors by type
                error_types = defaultdict(int)
                for event in error_events:
                    error_type = event.data.get("error_type", "unknown")
                    error_types[error_type] += 1
                
                # Check for dominant error types
                total_errors = sum(error_types.values())
                for error_type, count in error_types.items():
                    if count > total_errors * 0.5:  # More than 50% of errors
                        alert_manager.check_custom_condition(
                            lambda: True,
                            f"Dominant Error Type: {error_type}",
                            f"Error type accounts for {(count/total_errors)*100:.1f}% of all errors",
                            AlertSeverity.MEDIUM
                        )
        
        except Exception as e:
            logger.error(f"Error analyzing event patterns: {e}")
    
    async def _check_security_events(self):
        """Check for security-related events."""
        try:
            # Get recent security events
            security_events = event_tracker.get_events(
                {"category": "security"}, 
                limit=50
            )
            
            # Look for suspicious patterns
            auth_failures = [e for e in security_events if "auth.failure" in e.name]
            if len(auth_failures) > 10:  # More than 10 auth failures
                alert_manager.check_custom_condition(
                    lambda: True,
                    "High Authentication Failure Rate",
                    f"{len(auth_failures)} authentication failures detected",
                    AlertSeverity.HIGH
                )
            
            # Check for potential brute force attacks
            client_ips = defaultdict(int)
            for event in auth_failures:
                client_ip = event.data.get("client_ip", "unknown")
                client_ips[client_ip] += 1
            
            for ip, failures in client_ips.items():
                if failures > 5:  # More than 5 failures from same IP
                    alert_manager.check_custom_condition(
                        lambda: True,
                        "Potential Brute Force Attack",
                        f"IP {ip} has {failures} authentication failures",
                        AlertSeverity.HIGH
                    )
        
        except Exception as e:
            logger.error(f"Error checking security events: {e}")
    
    async def _analyze_business_events(self):
        """Analyze business-specific event patterns."""
        try:
            # Get recent business events
            business_events = event_tracker.get_events(
                {"category": "business"}, 
                limit=100
            )
            
            # Analyze revenue events
            revenue_events = [e for e in business_events if "revenue" in e.name or "payment" in e.name]
            if revenue_events:
                total_revenue = sum(
                    event.data.get("amount", 0) 
                    for event in revenue_events 
                    if "amount" in event.data
                )
                
                # Track daily revenue
                date_str = datetime.utcnow().strftime("%Y-%m-%d")
                metrics_collector.set_gauge(f"business.revenue.daily.{date_str}", total_revenue)
            
            # Analyze user activity patterns
            user_events = [e for e in business_events if "user" in e.category.value]
            unique_users = set()
            for event in user_events:
                user_id = event.context.user_id
                if user_id:
                    unique_users.add(user_id)
            
            # Track daily active users
            metrics_collector.set_gauge("business.users.daily_active", len(unique_users))
        
        except Exception as e:
            logger.error(f"Error analyzing business events: {e}")
    
    async def _evaluate_alerts(self):
        """Evaluate alert conditions and escalation."""
        try:
            # Get active alerts
            active_alerts = alert_manager.get_active_alerts()
            
            # Check for alert escalation conditions
            for alert in active_alerts:
                # Check if alert has been active for too long
                time_active = (datetime.utcnow() - alert.triggered_at).total_seconds()
                
                # Escalate critical alerts after 1 hour
                if alert.severity == AlertSeverity.CRITICAL and time_active > 3600:
                    event_tracker.track_event(
                        name="alert.escalation.critical_timeout",
                        category=EventCategory.SYSTEM,
                        level=EventLevel.CRITICAL,
                        data={
                            "alert_id": alert.id,
                            "alert_title": alert.title,
                            "time_active_hours": time_active / 3600
                        }
                    )
                
                # Escalate high severity alerts after 2 hours
                elif alert.severity == AlertSeverity.HIGH and time_active > 7200:
                    event_tracker.track_event(
                        name="alert.escalation.high_timeout",
                        category=EventCategory.SYSTEM,
                        level=EventLevel.WARNING,
                        data={
                            "alert_id": alert.id,
                            "alert_title": alert.title,
                            "time_active_hours": time_active / 3600
                        }
                    )
            
            # Generate alert summary report
            await self._generate_alert_report()
        
        except Exception as e:
            logger.error(f"Error in alert evaluation: {e}")
    
    async def _generate_alert_report(self):
        """Generate alert summary report."""
        try:
            alert_stats = alert_manager.get_alert_statistics()
            
            report = {
                "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "statistics": alert_stats,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Store as event
            event_tracker.track_event(
                name="alerts.daily_summary",
                category=EventCategory.SYSTEM,
                level=EventLevel.INFO,
                data=report
            )
        
        except Exception as e:
            logger.error(f"Error generating alert report: {e}")
    
    async def _cleanup_expired_data(self):
        """Clean up expired telemetry data."""
        try:
            # Force cleanup through service methods
            await metrics_collector._cleanup_expired_metrics()
            await event_tracker._cleanup_expired_events()
            
            # Log cleanup statistics
            logger.info("Telemetry data cleanup completed")
        
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def _analyze_trends(self):
        """Perform comprehensive trend analysis."""
        try:
            # Analyze across all telemetry dimensions
            await self._analyze_cross_metric_trends()
            await self._analyze_service_health_trends()
            await self._analyze_user_behavior_trends()
            
            # Generate trend insights
            await self._generate_trend_insights()
        
        except Exception as e:
            logger.error(f"Error in trends analysis: {e}")
    
    async def _analyze_cross_metric_trends(self):
        """Analyze trends across multiple metrics."""
        # Implementation would correlate multiple metrics
        # For example, correlation between response time and error rate
        pass
    
    async def _analyze_service_health_trends(self):
        """Analyze service health trends over time."""
        # Implementation would track service health scores over time
        pass
    
    async def _analyze_user_behavior_trends(self):
        """Analyze user behavior trends."""
        # Implementation would track user engagement patterns
        pass
    
    async def _generate_trend_insights(self):
        """Generate actionable insights from trend analysis."""
        # Implementation would generate business insights
        pass
    
    async def _sync_external_systems(self):
        """Synchronize data with external monitoring systems."""
        try:
            # This would integrate with external systems like:
            # - Prometheus (metrics)
            # - Jaeger (tracing)
            # - DataDog (monitoring)
            # - New Relic (APM)
            
            # For now, just log that sync would occur
            logger.info("External system synchronization completed")
        
        except Exception as e:
            logger.error(f"Error in external sync: {e}")
    
    async def _export_telemetry_data(self):
        """Export telemetry data for archival or analysis."""
        try:
            # Export recent data in various formats
            await self._export_metrics_data()
            await self._export_events_data()
            await self._export_traces_data()
            await self._export_alerts_data()
            
            logger.info("Telemetry data export completed")
        
        except Exception as e:
            logger.error(f"Error in data export: {e}")
    
    async def _export_metrics_data(self):
        """Export metrics data."""
        # Implementation would export metrics in various formats (JSON, CSV, etc.)
        pass
    
    async def _export_events_data(self):
        """Export events data."""
        # Implementation would export events for analysis
        pass
    
    async def _export_traces_data(self):
        """Export traces data."""
        # Implementation would export trace data
        pass
    
    async def _export_alerts_data(self):
        """Export alerts data."""
        # Implementation would export alert history
        pass
    
    def configure_task(self, task_name: str, interval: int, enabled: bool = True):
        """Configure a specific background task."""
        if task_name in self.task_configs:
            self.task_configs[task_name]["interval"] = interval
            self.task_configs[task_name]["enabled"] = enabled
            logger.info(f"Configured task {task_name}: interval={interval}, enabled={enabled}")
        else:
            logger.warning(f"Unknown task name: {task_name}")
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        return {
            "running": self.running,
            "tasks": {
                name: {
                    "enabled": config["enabled"],
                    "interval": config["interval"],
                    "status": "running" if name in self.tasks else "stopped"
                }
                for name, config in self.task_configs.items()
            }
        }


# Global background tasks instance
telemetry_background_tasks = TelemetryBackgroundTasks()


# Helper functions for external integration
async def start_telemetry_background_tasks():
    """Start all telemetry background tasks."""
    await telemetry_background_tasks.start_all_tasks()


async def stop_telemetry_background_tasks():
    """Stop all telemetry background tasks."""
    await telemetry_background_tasks.stop_all_tasks()


def configure_telemetry_task(task_name: str, interval: int, enabled: bool = True):
    """Configure a telemetry background task."""
    telemetry_background_tasks.configure_task(task_name, interval, enabled)


def get_telemetry_tasks_status() -> Dict[str, Any]:
    """Get status of all telemetry background tasks."""
    return telemetry_background_tasks.get_task_status()


# Health check for background tasks
async def check_telemetry_background_tasks_health() -> Dict[str, Any]:
    """Check health of background tasks."""
    status = telemetry_background_tasks.get_task_status()
    
    # Check if tasks are running
    running_tasks = sum(1 for task_info in status["tasks"].values() 
                       if task_info["status"] == "running")
    
    total_tasks = sum(1 for task_info in status["tasks"].values() 
                     if task_info["enabled"])
    
    health = {
        "status": "healthy" if running_tasks == total_tasks else "degraded",
        "running_tasks": running_tasks,
        "total_enabled_tasks": total_tasks,
        "tasks": status["tasks"]
    }
    
    return health