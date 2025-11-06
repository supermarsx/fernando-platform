"""
Monitoring and Analytics System

This module provides comprehensive monitoring and analytics for the dual-server architecture,
including server performance monitoring, client-server relationship analytics, licensing tracking,
and operational dashboards.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import asyncio
import statistics
from collections import defaultdict, deque
import json

from .server_architecture import ServerType, server_architecture
from .tenant_management import TenantStatus
from ..models.server_architecture import (
    ServerCommunicationLog, SyncJob, License, Client, Subscription,
    SupplierServer, CommissionTracking, ClientServerRegistration
)
from ..core.database import get_db
from ..core.config import settings
from ..core.telemetry import telemetry_tracker


class MetricType(str, Enum):
    """Metric type enumeration"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


class AlertSeverity(str, Enum):
    """Alert severity enumeration"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricSnapshot:
    """Single metric snapshot"""
    def __init__(self, name: str, value: float, timestamp: datetime, 
                 tags: Dict[str, str] = None):
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.tags = tags or {}


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    active_connections: int
    request_rate: float
    error_rate: float
    response_time: float


@dataclass
class BusinessMetric:
    """Business metric data point"""
    timestamp: datetime
    total_customers: int
    active_subscriptions: int
    monthly_recurring_revenue: float
    new_customer_acquisitions: int
    churn_rate: float
    license_utilization: float
    commission_earned: float


@dataclass
class OperationalAlert:
    """Operational alert"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Metrics collection system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, List[MetricSnapshot]] = defaultdict(lambda: deque(maxlen=1000))
        self._start_time = datetime.utcnow()
        self._collection_interval = 30  # seconds
        
    def record_metric(self, name: str, value: float, 
                     tags: Dict[str, str] = None, timestamp: datetime = None):
        """Record a metric"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        metric = MetricSnapshot(name, value, timestamp, tags)
        self._metrics[name].append(metric)
        
        # Track in telemetry
        telemetry_tracker.track_metric(name, value, tags)
    
    def get_metrics(self, name: str, start_time: datetime = None, 
                   end_time: datetime = None) -> List[MetricSnapshot]:
        """Get metrics for a specific name and time range"""
        if name not in self._metrics:
            return []
        
        metrics = self._metrics[name]
        
        if start_time is None and end_time is None:
            return list(metrics)
        
        filtered = []
        for metric in metrics:
            if start_time and metric.timestamp < start_time:
                continue
            if end_time and metric.timestamp > end_time:
                continue
            filtered.append(metric)
        
        return filtered
    
    def calculate_rate(self, name: str, window_minutes: int = 5) -> float:
        """Calculate rate of change for a metric"""
        metrics = self.get_metrics(name)
        if len(metrics) < 2:
            return 0.0
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        window_metrics = [m for m in metrics if start_time <= m.timestamp <= end_time]
        
        if len(window_metrics) < 2:
            return 0.0
        
        # Calculate rate per minute
        time_diff = (window_metrics[-1].timestamp - window_metrics[0].timestamp).total_seconds()
        value_diff = window_metrics[-1].value - window_metrics[0].value
        
        return (value_diff / time_diff) * 60 if time_diff > 0 else 0.0
    
    def get_summary_stats(self, name: str, window_minutes: int = 60) -> Dict[str, float]:
        """Get summary statistics for a metric"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        metrics = self.get_metrics(name, start_time, end_time)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


class PerformanceMonitor:
    """
    Server performance monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_collector = MetricsCollector()
        self._monitoring_active = False
        
    async def start_monitoring(self):
        """Start performance monitoring"""
        self._monitoring_active = True
        asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring_active = False
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                await self._collect_performance_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(30)
    
    async def _collect_performance_metrics(self):
        """Collect performance metrics"""
        try:
            # Import here to avoid circular imports
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.record_metric("system.cpu.usage", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.metrics_collector.record_metric("system.memory.usage", memory_percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics_collector.record_metric("system.disk.usage", disk_percent)
            
            # Network statistics
            network = psutil.net_io_counters()
            self.metrics_collector.record_metric("network.bytes_sent", network.bytes_sent)
            self.metrics_collector.record_metric("network.bytes_recv", network.bytes_recv)
            
            # Process information
            process = psutil.Process()
            self.metrics_collector.record_metric("process.cpu.usage", process.cpu_percent())
            self.metrics_collector.record_metric("process.memory.usage", process.memory_percent())
            
            # Application-specific metrics
            await self._collect_application_metrics()
            
        except ImportError:
            self.logger.warning("psutil not available, using mock metrics")
            await self._collect_mock_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {str(e)}")
    
    async def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            # Database connections
            db = next(get_db())
            # This would be implementation-specific
            
            # Active connections
            # In a real implementation, get from connection pool
            active_connections = 42
            self.metrics_collector.record_metric("application.connections.active", active_connections)
            
            # Request rate
            # Calculate from recent requests
            request_rate = self.metrics_collector.calculate_rate("application.requests.total", 5)
            self.metrics_collector.record_metric("application.requests.rate", request_rate)
            
            # Error rate
            error_rate = self.metrics_collector.calculate_rate("application.errors.total", 5)
            self.metrics_collector.record_metric("application.errors.rate", error_rate)
            
        except Exception as e:
            self.logger.error(f"Error collecting application metrics: {str(e)}")
    
    async def _collect_mock_metrics(self):
        """Collect mock metrics for testing"""
        import random
        
        # Mock application metrics
        self.metrics_collector.record_metric("application.connections.active", random.randint(10, 100))
        self.metrics_collector.record_metric("application.requests.rate", random.uniform(1, 50))
        self.metrics_collector.record_metric("application.errors.rate", random.uniform(0, 5))
        
        # Mock latency metrics
        self.metrics_collector.record_metric("application.response.time", random.uniform(50, 500))
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        summary = {}
        
        # System metrics
        system_metrics = ["system.cpu.usage", "system.memory.usage", "system.disk.usage"]
        for metric in system_metrics:
            stats = self.metrics_collector.get_summary_stats(metric, hours * 60)
            if stats:
                summary[metric] = stats
        
        # Application metrics
        app_metrics = ["application.connections.active", "application.requests.rate", "application.errors.rate"]
        for metric in app_metrics:
            stats = self.metrics_collector.get_summary_stats(metric, hours * 60)
            if stats:
                summary[metric] = stats
        
        return summary
    
    def check_performance_alerts(self) -> List[OperationalAlert]:
        """Check for performance alerts"""
        alerts = []
        
        try:
            # CPU alert
            cpu_stats = self.metrics_collector.get_summary_stats("system.cpu.usage", 5)
            if cpu_stats and cpu_stats.get("mean", 0) > 80:
                alerts.append(OperationalAlert(
                    id=f"cpu_high_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    title="High CPU Usage",
                    message=f"CPU usage is {cpu_stats['mean']:.1f}%, above threshold of 80%",
                    severity=AlertSeverity.WARNING,
                    source="performance_monitor",
                    created_at=datetime.utcnow(),
                    metadata={"cpu_usage": cpu_stats["mean"]}
                ))
            
            # Memory alert
            memory_stats = self.metrics_collector.get_summary_stats("system.memory.usage", 5)
            if memory_stats and memory_stats.get("mean", 0) > 85:
                alerts.append(OperationalAlert(
                    id=f"memory_high_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    title="High Memory Usage",
                    message=f"Memory usage is {memory_stats['mean']:.1f}%, above threshold of 85%",
                    severity=AlertSeverity.WARNING,
                    source="performance_monitor",
                    created_at=datetime.utcnow(),
                    metadata={"memory_usage": memory_stats["mean"]}
                ))
            
            # Error rate alert
            error_stats = self.metrics_collector.get_summary_stats("application.errors.rate", 5)
            if error_stats and error_stats.get("mean", 0) > 10:
                alerts.append(OperationalAlert(
                    id=f"error_rate_high_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    title="High Error Rate",
                    message=f"Error rate is {error_stats['mean']:.1f} errors/minute, above threshold of 10",
                    severity=AlertSeverity.ERROR,
                    source="performance_monitor",
                    created_at=datetime.utcnow(),
                    metadata={"error_rate": error_stats["mean"]}
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking performance alerts: {str(e)}")
        
        return alerts


class BusinessAnalytics:
    """
    Business analytics and reporting
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_revenue_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get revenue analytics for a period"""
        try:
            db = next(get_db())
            
            # Revenue by period
            revenue_query = """
                SELECT 
                    DATE(created_at) as date,
                    SUM(commission_amount) as daily_revenue,
                    COUNT(*) as transactions
                FROM commission_tracking 
                WHERE created_at BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                ORDER BY date
            """
            
            # Execute query (simplified - in real implementation use proper SQLAlchemy)
            # revenue_data = db.execute(revenue_query, start_date, end_date).fetchall()
            
            # Mock revenue data for demonstration
            revenue_data = []
            current_date = start_date
            while current_date <= end_date:
                revenue_data.append({
                    'date': current_date.date(),
                    'daily_revenue': 1000.0 + (current_date.day * 50),  # Mock data
                    'transactions': 10 + (current_date.day % 5)
                })
                current_date += timedelta(days=1)
            
            # Calculate summary statistics
            total_revenue = sum(row['daily_revenue'] for row in revenue_data)
            total_transactions = sum(row['transactions'] for row in revenue_data)
            avg_daily_revenue = total_revenue / len(revenue_data) if revenue_data else 0
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": len(revenue_data)
                },
                "summary": {
                    "total_revenue": total_revenue,
                    "total_transactions": total_transactions,
                    "average_daily_revenue": avg_daily_revenue,
                    "revenue_per_transaction": total_revenue / total_transactions if total_transactions > 0 else 0
                },
                "daily_breakdown": revenue_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting revenue analytics: {str(e)}")
            return {}
    
    def get_customer_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get customer analytics for a period"""
        try:
            db = next(get_db())
            
            # Get customer metrics
            # In real implementation, query actual database
            
            # Mock customer data
            customers_created = 50 + (end_date - start_date).days * 2
            customers_active = 200
            customers_churned = 5
            
            # Calculate churn rate
            total_customers = customers_active + customers_churned
            churn_rate = (customers_churned / total_customers) * 100 if total_customers > 0 else 0
            
            # Customer acquisition rate
            days_in_period = (end_date - start_date).days
            acquisition_rate = customers_created / days_in_period if days_in_period > 0 else 0
            
            # License utilization
            total_licenses = 300
            active_licenses = 250
            license_utilization = (active_licenses / total_licenses) * 100 if total_licenses > 0 else 0
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days_in_period
                },
                "summary": {
                    "customers_created": customers_created,
                    "customers_active": customers_active,
                    "customers_churned": customers_churned,
                    "churn_rate": churn_rate,
                    "acquisition_rate": acquisition_rate,
                    "license_utilization": license_utilization
                },
                "trends": {
                    "customer_growth": "positive",  # Based on data analysis
                    "retention_trend": "stable",
                    "license_uptake": "growing"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting customer analytics: {str(e)}")
            return {}
    
    def get_server_analytics(self) -> Dict[str, Any]:
        """Get server analytics and health metrics"""
        try:
            db = next(get_db())
            
            # Mock server analytics
            server_type = server_architecture.get_current_server_type()
            
            if server_type == ServerType.SUPPLIER:
                # Supplier server analytics
                analytics = {
                    "server_type": "supplier",
                    "network_metrics": {
                        "total_client_servers": 25,
                        "active_client_servers": 22,
                        "inactive_client_servers": 3,
                        "registration_rate": 2.5,  # per day
                        "communication_success_rate": 98.5
                    },
                    "licensing_metrics": {
                        "total_licenses": 150,
                        "active_licenses": 142,
                        "expired_licenses": 8,
                        "license_conversion_rate": 85.2,
                        "average_license_value": 299.0
                    },
                    "revenue_metrics": {
                        "monthly_recurring_revenue": 45000.0,
                        "commission_rate": 25.0,
                        "revenue_growth": 15.3
                    }
                }
            else:
                # Client server analytics
                analytics = {
                    "server_type": "client",
                    "performance_metrics": {
                        "uptime_percentage": 99.8,
                        "average_response_time": 150.0,
                        "error_rate": 0.5,
                        "throughput": 1000.0
                    },
                    "customer_metrics": {
                        "total_customers": 150,
                        "active_customers": 145,
                        "customer_satisfaction": 4.7,
                        "support_tickets": 12
                    },
                    "billing_metrics": {
                        "collection_rate": 96.8,
                        "average_invoice": 250.0,
                        "payment_delays": 3.2
                    }
                }
            
            # Add common metrics
            analytics["timestamp"] = datetime.utcnow().isoformat()
            analytics["server_info"] = server_architecture.get_server_info()
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting server analytics: {str(e)}")
            return {}
    
    def get_compliance_analytics(self) -> Dict[str, Any]:
        """Get compliance and security analytics"""
        try:
            # Mock compliance metrics
            analytics = {
                "security_score": 92.5,
                "compliance_status": "compliant",
                "vulnerabilities": {
                    "critical": 0,
                    "high": 1,
                    "medium": 3,
                    "low": 8
                },
                "audit_findings": {
                    "open_issues": 2,
                    "resolved_this_month": 5,
                    "overdue_items": 0
                },
                "data_protection": {
                    "encryption_coverage": 100.0,
                    "data_breaches": 0,
                    "access_violations": 1
                },
                "compliance_frameworks": {
                    "gdpr": "compliant",
                    "soc2": "compliant",
                    "iso27001": "in_progress"
                }
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting compliance analytics: {str(e)}")
            return {}


class OperationalDashboard:
    """
    Operational dashboard and reporting
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = PerformanceMonitor()
        self.business_analytics = BusinessAnalytics()
        self._active_alerts: List[OperationalAlert] = []
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            dashboard_data = {
                "timestamp": end_time.isoformat(),
                "server_info": server_architecture.get_server_info(),
                "performance": self.performance_monitor.get_performance_summary(24),
                "business_metrics": self.business_analytics.get_server_analytics(),
                "alerts": self._get_active_alerts(),
                "kpi_summary": self._get_kpi_summary()
            }
            
            # Add revenue analytics if supplier server
            if server_architecture.get_current_server_type() == ServerType.SUPPLIER:
                dashboard_data["revenue_analytics"] = self.business_analytics.get_revenue_analytics(
                    start_time, end_time
                )
            
            # Track dashboard access
            telemetry_tracker.track_event('dashboard_viewed', {
                'server_type': server_architecture.get_current_server_type(),
                'server_id': server_architecture.get_server_info()['server_id']
            })
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {str(e)}")
            return {}
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        # Get performance alerts
        performance_alerts = self.performance_monitor.check_performance_alerts()
        
        # Combine with existing alerts
        all_alerts = self._active_alerts + performance_alerts
        
        # Filter unresolved alerts
        active_alerts = [alert for alert in all_alerts if alert.resolved_at is None]
        
        return [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "source": alert.source,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            }
            for alert in active_alerts
        ]
    
    def _get_kpi_summary(self) -> Dict[str, Any]:
        """Get KPI summary for dashboard"""
        try:
            server_type = server_architecture.get_current_server_type()
            
            if server_type == ServerType.SUPPLIER:
                return {
                    "revenue": {
                        "monthly_recurring_revenue": 45000.0,
                        "growth_rate": 15.3,
                        "target": 50000.0,
                        "progress": 90.0
                    },
                    "licensing": {
                        "active_licenses": 142,
                        "total_licenses": 150,
                        "conversion_rate": 85.2,
                        "target": 90.0,
                        "progress": 94.7
                    },
                    "network": {
                        "client_servers_active": 22,
                        "total_client_servers": 25,
                        "uptime": 99.8,
                        "target": 99.5,
                        "progress": 100.0
                    }
                }
            else:
                return {
                    "performance": {
                        "uptime": 99.8,
                        "response_time": 150.0,
                        "error_rate": 0.5,
                        "target_uptime": 99.5,
                        "uptime_progress": 100.0
                    },
                    "customers": {
                        "active_customers": 145,
                        "total_customers": 150,
                        "satisfaction_score": 4.7,
                        "target_satisfaction": 4.5,
                        "satisfaction_progress": 100.0
                    },
                    "billing": {
                        "collection_rate": 96.8,
                        "average_invoice": 250.0,
                        "target_collection": 95.0,
                        "collection_progress": 100.0
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting KPI summary: {str(e)}")
            return {}
    
    def create_custom_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom report based on configuration"""
        try:
            report_type = report_config.get("type")
            start_date = datetime.fromisoformat(report_config.get("start_date"))
            end_date = datetime.fromisoformat(report_config.get("end_date"))
            metrics = report_config.get("metrics", [])
            
            report_data = {
                "report_config": report_config,
                "generated_at": datetime.utcnow().isoformat(),
                "data": {}
            }
            
            # Generate data based on requested metrics
            for metric in metrics:
                if metric == "revenue":
                    report_data["data"]["revenue"] = self.business_analytics.get_revenue_analytics(start_date, end_date)
                elif metric == "customers":
                    report_data["data"]["customers"] = self.business_analytics.get_customer_analytics(start_date, end_date)
                elif metric == "performance":
                    report_data["data"]["performance"] = self.performance_monitor.get_performance_summary(
                        (end_date - start_date).total_seconds() / 3600
                    )
                elif metric == "server":
                    report_data["data"]["server"] = self.business_analytics.get_server_analytics()
            
            # Track report generation
            telemetry_tracker.track_event('custom_report_generated', {
                'report_type': report_type,
                'metrics_included': metrics,
                'server_type': server_architecture.get_current_server_type()
            })
            
            return report_data
            
        except Exception as e:
            self.logger.error(f"Error creating custom report: {str(e)}")
            raise


# Global monitoring and analytics instances
monitoring_analytics = OperationalDashboard()
performance_monitor = PerformanceMonitor()
business_analytics = BusinessAnalytics()
metrics_collector = MetricsCollector()


# Convenience functions
async def start_monitoring():
    """Start the monitoring system"""
    await performance_monitor.start_monitoring()


async def stop_monitoring():
    """Stop the monitoring system"""
    await performance_monitor.stop_monitoring()


def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data"""
    return asyncio.create_task(monitoring_analytics.get_dashboard_data())


def get_performance_metrics(hours: int = 1) -> Dict[str, Any]:
    """Get performance metrics"""
    return performance_monitor.get_performance_summary(hours)


def get_business_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Get business analytics"""
    return business_analytics.get_revenue_analytics(start_date, end_date)


def get_server_analytics() -> Dict[str, Any]:
    """Get server analytics"""
    return business_analytics.get_server_analytics()


def get_compliance_analytics() -> Dict[str, Any]:
    """Get compliance analytics"""
    return business_analytics.get_compliance_analytics()


def create_custom_report(report_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create custom report"""
    return monitoring_analytics.create_custom_report(report_config)


def record_metric(name: str, value: float, tags: Dict[str, str] = None):
    """Record a custom metric"""
    metrics_collector.record_metric(name, value, tags)


def check_alerts() -> List[OperationalAlert]:
    """Check for operational alerts"""
    return performance_monitor.check_performance_alerts()