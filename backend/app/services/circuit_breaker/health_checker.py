"""
Health Checker Service

Provides comprehensive health monitoring for external services including
ping checks, dependency analysis, performance metrics, SLA monitoring,
and automated alerting for degraded or failed services.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
import json
import statistics
import aiohttp
import ssl

from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class HealthCheckStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"

class HealthCheckType(Enum):
    """Types of health checks"""
    HTTP = "http"
    TCP = "tcp"
    PING = "ping"
    CUSTOM = "custom"
    DEPENDENCY = "dependency"
    SLA = "sla"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    check_interval_seconds: int = 30
    timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    consecutive_failures_threshold: int = 3
    consecutive_successes_threshold: int = 2
    response_time_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.05  # 5% error rate
    availability_threshold: float = 0.99  # 99% availability
    enabled: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    expected_status_codes: List[int] = field(default_factory=lambda: [200, 201, 202])
    expected_response_pattern: Optional[str] = None
    ssl_verify: bool = True
    follow_redirects: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheckResult:
    """Health check result"""
    service_name: str
    check_type: HealthCheckType
    status: HealthCheckStatus
    response_time_ms: float
    timestamp: datetime
    message: str
    error_details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status_code: Optional[int] = None
    ssl_info: Optional[Dict[str, Any]] = None

@dataclass
class ServiceHealthReport:
    """Comprehensive service health report"""
    service_name: str
    overall_status: HealthCheckStatus
    availability_percent: float
    avg_response_time_ms: float
    error_rate_percent: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    last_check_time: Optional[datetime]
    last_success_time: Optional[datetime]
    last_failure_time: Optional[datetime]
    consecutive_failures: int
    consecutive_successes: int
    sla_compliance: float
    performance_score: float
    check_results: List[HealthCheckResult] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

@dataclass
class HealthAlert:
    """Health alert definition"""
    id: str
    service_name: str
    alert_type: str
    severity: AlertSeverity
    message: str
    threshold_value: float
    current_value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ServiceHealthMonitor:
    """Individual service health monitor"""
    
    def __init__(self, service_name: str, config: HealthCheckConfig):
        self.service_name = service_name
        self.config = config
        
        # Health tracking
        self.check_history = deque(maxlen=1000)
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_check_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.last_failure_time: Optional[datetime] = None
        
        # Metrics aggregation
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.total_response_time = 0.0
        
        # Alert state
        self.active_alerts = {}
        
        logger.info(f"Created health monitor for service: {service_name}")
    
    async def perform_health_check(self, check_type: HealthCheckType, **kwargs) -> HealthCheckResult:
        """Perform a health check"""
        start_time = time.time()
        current_time = datetime.now(timezone.utc)
        
        try:
            if check_type == HealthCheckType.HTTP:
                result = await self._perform_http_check(**kwargs)
            elif check_type == HealthCheckType.TCP:
                result = await self._perform_tcp_check(**kwargs)
            elif check_type == HealthCheckType.PING:
                result = await self._perform_ping_check(**kwargs)
            elif check_type == HealthCheckType.CUSTOM:
                result = await self._perform_custom_check(**kwargs)
            elif check_type == HealthCheckType.SLA:
                result = await self._perform_sla_check(**kwargs)
            else:
                raise ValueError(f"Unsupported health check type: {check_type}")
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Update result with timing
            result.response_time_ms = response_time
            result.timestamp = current_time
            
            # Update metrics
            await self._update_metrics(result)
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                service_name=self.service_name,
                check_type=check_type,
                status=HealthCheckStatus.ERROR,
                response_time_ms=response_time,
                timestamp=current_time,
                message=f"Health check failed: {str(e)}",
                error_details=str(e)
            )
            
            await self._update_metrics(result)
            return result
    
    async def _perform_http_check(self, url: str, method: str = "GET", **kwargs) -> HealthCheckResult:
        """Perform HTTP health check"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                ssl=ssl.create_default_context() if self.config.ssl_verify else False
            ) as session:
                
                headers = self.config.custom_headers.copy()
                headers.update(kwargs.get('headers', {}))
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    allow_redirects=self.config.follow_redirects
                ) as response:
                    
                    content = await response.text()
                    
                    # Check status code
                    if response.status not in self.config.expected_status_codes:
                        return HealthCheckResult(
                            service_name=self.service_name,
                            check_type=HealthCheckType.HTTP,
                            status=HealthCheckStatus.UNHEALTHY,
                            response_time_ms=0,
                            timestamp=datetime.now(timezone.utc),
                            message=f"Unexpected status code: {response.status}",
                            status_code=response.status
                        )
                    
                    # Check response pattern if specified
                    if self.config.expected_response_pattern:
                        if self.config.expected_response_pattern not in content:
                            return HealthCheckResult(
                                service_name=self.service_name,
                                check_type=HealthCheckType.HTTP,
                                status=HealthCheckStatus.DEGRADED,
                                response_time_ms=0,
                                timestamp=datetime.now(timezone.utc),
                                message="Response pattern mismatch"
                            )
                    
                    return HealthCheckResult(
                        service_name=self.service_name,
                        check_type=HealthCheckType.HTTP,
                        status=HealthCheckStatus.HEALTHY,
                        response_time_ms=0,
                        timestamp=datetime.now(timezone.utc),
                        message="HTTP health check successful",
                        status_code=response.status,
                        ssl_info={
                            'version': response.version,
                            'compress': response.compression,
                            'headers': dict(response.headers)
                        }
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.HTTP,
                status=HealthCheckStatus.TIMEOUT,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"HTTP health check timeout after {self.config.timeout_seconds}s"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.HTTP,
                status=HealthCheckStatus.ERROR,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"HTTP health check error: {str(e)}",
                error_details=str(e)
            )
    
    async def _perform_tcp_check(self, host: str, port: int) -> HealthCheckResult:
        """Perform TCP health check"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.config.timeout_seconds
            )
            
            writer.close()
            await writer.wait_closed()
            
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.TCP,
                status=HealthCheckStatus.HEALTHY,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"TCP connection to {host}:{port} successful"
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.TCP,
                status=HealthCheckStatus.TIMEOUT,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"TCP connection timeout to {host}:{port}"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.TCP,
                status=HealthCheckStatus.ERROR,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"TCP connection error to {host}:{port}: {str(e)}",
                error_details=str(e)
            )
    
    async def _perform_ping_check(self, host: str) -> HealthCheckResult:
        """Perform ping health check"""
        try:
            # Use system ping command
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', str(int(self.config.timeout_seconds)), host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return HealthCheckResult(
                    service_name=self.service_name,
                    check_type=HealthCheckType.PING,
                    status=HealthCheckStatus.HEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Ping to {host} successful"
                )
            else:
                return HealthCheckResult(
                    service_name=self.service_name,
                    check_type=HealthCheckType.PING,
                    status=HealthCheckStatus.UNHEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Ping to {host} failed"
                )
                
        except Exception as e:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.PING,
                status=HealthCheckStatus.ERROR,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"Ping error to {host}: {str(e)}",
                error_details=str(e)
            )
    
    async def _perform_custom_check(self, check_function: Callable, **kwargs) -> HealthCheckResult:
        """Perform custom health check"""
        try:
            if asyncio.iscoroutinefunction(check_function):
                result = await check_function(**kwargs)
            else:
                result = check_function(**kwargs)
            
            # Assume custom function returns a boolean or HealthCheckResult-like object
            if isinstance(result, bool):
                status = HealthCheckStatus.HEALTHY if result else HealthCheckStatus.UNHEALTHY
                message = "Custom health check passed" if result else "Custom health check failed"
            else:
                # Assume it's a dict with status and message
                status = HealthCheckStatus(result.get('status', 'unknown'))
                message = result.get('message', 'Custom health check completed')
            
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.CUSTOM,
                status=status,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=message,
                metadata=kwargs
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.CUSTOM,
                status=HealthCheckStatus.ERROR,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"Custom health check error: {str(e)}",
                error_details=str(e)
            )
    
    async def _perform_sla_check(self, **kwargs) -> HealthCheckResult:
        """Perform SLA-based health check"""
        try:
            # Get recent check results
            recent_results = list(self.check_history)[-20:]  # Last 20 checks
            
            if len(recent_results) < 5:
                return HealthCheckResult(
                    service_name=self.service_name,
                    check_type=HealthCheckType.SLA,
                    status=HealthCheckStatus.UNKNOWN,
                    response_time_ms=0,
                    timestamp=datetime.now(timezone.utc),
                    message="Insufficient data for SLA assessment"
                )
            
            # Calculate SLA metrics
            successful_checks = sum(1 for result in recent_results if result.status == HealthCheckStatus.HEALTHY)
            availability = successful_checks / len(recent_results)
            
            # Check response times
            response_times = [result.response_time_ms for result in recent_results if result.response_time_ms > 0]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Determine SLA compliance
            sla_compliant = (
                availability >= self.config.availability_threshold and
                avg_response_time <= self.config.response_time_threshold_ms
            )
            
            status = HealthCheckStatus.HEALTHY if sla_compliant else HealthCheckStatus.DEGRADED
            
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.SLA,
                status=status,
                response_time_ms=avg_response_time,
                timestamp=datetime.now(timezone.utc),
                message=f"SLA compliance: {availability*100:.1f}% availability, {avg_response_time:.1f}ms avg response time",
                metadata={
                    'availability': availability,
                    'avg_response_time': avg_response_time,
                    'checks_sample_size': len(recent_results)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name=self.service_name,
                check_type=HealthCheckType.SLA,
                status=HealthCheckStatus.ERROR,
                response_time_ms=0,
                timestamp=datetime.now(timezone.utc),
                message=f"SLA check error: {str(e)}",
                error_details=str(e)
            )
    
    async def _update_metrics(self, result: HealthCheckResult) -> None:
        """Update health monitoring metrics"""
        current_time = datetime.now(timezone.utc)
        
        # Add to history
        self.check_history.append(result)
        
        # Update counters
        self.total_checks += 1
        
        if result.status in [HealthCheckStatus.HEALTHY, HealthCheckStatus.DEGRADED]:
            self.successful_checks += 1
            self.consecutive_failures = 0
            self.consecutive_successes += 1
            self.last_success_time = current_time
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            self.last_failure_time = current_time
        
        self.last_check_time = current_time
        
        # Update response time tracking
        if result.response_time_ms > 0:
            self.total_response_time += result.response_time_ms
        
        logger.debug(f"Updated metrics for {self.service_name}: {result.status.value}")
    
    def get_current_status(self) -> HealthCheckStatus:
        """Get current service status based on consecutive failures"""
        if self.consecutive_failures >= self.config.consecutive_failures_threshold:
            return HealthCheckStatus.UNHEALTHY
        elif self.consecutive_failures > 0:
            return HealthCheckStatus.DEGRADED
        elif self.consecutive_successes >= self.config.consecutive_successes_threshold:
            return HealthCheckStatus.HEALTHY
        else:
            return HealthCheckStatus.UNKNOWN

class HealthChecker:
    """
    Comprehensive Health Monitoring Service
    
    Provides centralized health monitoring for multiple services with:
    - Multiple health check types (HTTP, TCP, Ping, Custom, SLA)
    - Configurable thresholds and monitoring intervals
    - Real-time alerting and notification
    - SLA compliance tracking
    - Performance analytics and trending
    - Dependency health analysis
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Service monitors
        self._monitors: Dict[str, ServiceHealthMonitor] = {}
        
        # Global configuration
        self.config = {
            'default_check_interval': 30,
            'alert_cooldown_minutes': 15,
            'health_history_retention_hours': 168,  # 7 days
            'sla_monitoring_enabled': True,
            'alert_notification_enabled': True,
            'redis_namespace': 'health_checker'
        }
        
        # Statistics
        self._global_stats = {
            'total_services_monitored': 0,
            'healthy_services': 0,
            'degraded_services': 0,
            'unhealthy_services': 0,
            'total_checks_performed': 0
        }
        
        # Background monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("HealthChecker initialized")
    
    async def register_service(
        self,
        service_name: str,
        health_check_config: HealthCheckConfig,
        service_url: Optional[str] = None,
        service_type: HealthCheckType = HealthCheckType.HTTP,
        dependencies: Optional[List[str]] = None
    ) -> bool:
        """Register a service for health monitoring"""
        try:
            monitor = ServiceHealthMonitor(service_name, health_check_config)
            self._monitors[service_name] = monitor
            
            # Store service metadata
            service_metadata = {
                'service_name': service_name,
                'service_url': service_url,
                'service_type': service_type.value,
                'dependencies': dependencies or [],
                'config': health_check_config.__dict__,
                'registered_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._store_service_metadata(service_name, service_metadata)
            
            # Update global statistics
            self._global_stats['total_services_monitored'] += 1
            
            logger.info(f"Registered service for health monitoring: {service_name}")
            
            await self.event_tracker.track_event(
                "health_check_service_registered",
                {
                    "service_name": service_name,
                    "service_type": service_type.value,
                    "check_interval": health_check_config.check_interval_seconds,
                    "dependencies": dependencies or []
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    async def unregister_service(self, service_name: str) -> bool:
        """Unregister a service from health monitoring"""
        try:
            if service_name not in self._monitors:
                return False
            
            del self._monitors[service_name]
            
            # Remove from metadata storage
            await self._remove_service_metadata(service_name)
            
            # Update global statistics
            self._global_stats['total_services_monitored'] -= 1
            
            logger.info(f"Unregistered service from health monitoring: {service_name}")
            
            await self.event_tracker.track_event(
                "health_check_service_unregistered",
                {"service_name": service_name}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister service {service_name}: {e}")
            return False
    
    async def check_service_health(
        self,
        service_name: str,
        check_type: Optional[HealthCheckType] = None,
        **kwargs
    ) -> HealthCheckResult:
        """Perform immediate health check for a service"""
        if service_name not in self._monitors:
            raise ValueError(f"Service {service_name} not registered")
        
        monitor = self._monitors[service_name]
        
        if check_type is None:
            # Use default check type based on configuration
            check_type = HealthCheckType.HTTP  # Default
        
        result = await monitor.perform_health_check(check_type, **kwargs)
        
        # Check for alerts
        await self._check_and_create_alerts(monitor, result)
        
        return result
    
    async def get_service_health_report(self, service_name: str) -> ServiceHealthReport:
        """Get comprehensive health report for a service"""
        if service_name not in self._monitors:
            raise ValueError(f"Service {service_name} not registered")
        
        monitor = self._monitors[service_name]
        
        # Calculate metrics
        total_checks = monitor.total_checks
        successful_checks = monitor.successful_checks
        failed_checks = monitor.failed_checks
        
        availability_percent = (successful_checks / max(1, total_checks)) * 100
        error_rate_percent = (failed_checks / max(1, total_checks)) * 100
        
        avg_response_time = monitor.total_response_time / max(1, successful_checks) if successful_checks > 0 else 0
        
        # Get recent check results
        recent_results = list(monitor.check_history)[-10:]  # Last 10 checks
        
        # Calculate SLA compliance (simplified)
        sla_compliance = 100.0
        if total_checks > 0:
            healthy_checks = sum(1 for result in recent_results if result.status == HealthCheckStatus.HEALTHY)
            sla_compliance = (healthy_checks / len(recent_results)) * 100 if recent_results else 0
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(
            availability_percent, avg_response_time, error_rate_percent
        )
        
        # Get dependencies
        service_metadata = await self._get_service_metadata(service_name)
        dependencies = service_metadata.get('dependencies', []) if service_metadata else []
        
        return ServiceHealthReport(
            service_name=service_name,
            overall_status=monitor.get_current_status(),
            availability_percent=round(availability_percent, 2),
            avg_response_time_ms=round(avg_response_time, 2),
            error_rate_percent=round(error_rate_percent, 2),
            total_checks=total_checks,
            successful_checks=successful_checks,
            failed_checks=failed_checks,
            last_check_time=monitor.last_check_time,
            last_success_time=monitor.last_success_time,
            last_failure_time=monitor.last_failure_time,
            consecutive_failures=monitor.consecutive_failures,
            consecutive_successes=monitor.consecutive_successes,
            sla_compliance=round(sla_compliance, 2),
            performance_score=round(performance_score, 2),
            check_results=recent_results,
            dependencies=dependencies
        )
    
    async def get_all_services_health(self) -> Dict[str, ServiceHealthReport]:
        """Get health reports for all monitored services"""
        reports = {}
        
        for service_name in self._monitors.keys():
            try:
                report = await self.get_service_health_report(service_name)
                reports[service_name] = report
            except Exception as e:
                logger.error(f"Failed to get health report for {service_name}: {e}")
                reports[service_name] = ServiceHealthReport(
                    service_name=service_name,
                    overall_status=HealthCheckStatus.ERROR,
                    availability_percent=0.0,
                    avg_response_time_ms=0.0,
                    error_rate_percent=100.0,
                    total_checks=0,
                    successful_checks=0,
                    failed_checks=0,
                    last_check_time=None,
                    last_success_time=None,
                    last_failure_time=None,
                    consecutive_failures=0,
                    consecutive_successes=0,
                    sla_compliance=0.0,
                    performance_score=0.0
                )
        
        return reports
    
    async def get_global_health_status(self) -> Dict[str, Any]:
        """Get global health monitoring status"""
        current_time = datetime.now(timezone.utc)
        
        # Calculate global statistics
        total_services = len(self._monitors)
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for monitor in self._monitors.values():
            status = monitor.get_current_status()
            if status == HealthCheckStatus.HEALTHY:
                healthy_count += 1
            elif status == HealthCheckStatus.DEGRADED:
                degraded_count += 1
            elif status == HealthCheckStatus.UNHEALTHY:
                unhealthy_count += 1
        
        # Update global stats
        self._global_stats.update({
            'healthy_services': healthy_count,
            'degraded_services': degraded_count,
            'unhealthy_services': unhealthy_count
        })
        
        # Calculate overall system health score
        if total_services > 0:
            health_score = (healthy_count / total_services) * 100
        else:
            health_score = 0.0
        
        return {
            'timestamp': current_time.isoformat(),
            'overview': {
                'total_services': total_services,
                'healthy_services': healthy_count,
                'degraded_services': degraded_count,
                'unhealthy_services': unhealthy_count,
                'system_health_score': round(health_score, 2),
                'health_percentage': round((healthy_count / max(1, total_services)) * 100, 2)
            },
            'service_statuses': {
                service_name: monitor.get_current_status().value
                for service_name, monitor in self._monitors.items()
            },
            'global_statistics': self._global_stats,
            'monitoring_status': {
                'active_monitors': len(self._monitors),
                'total_checks_performed': self._global_stats['total_checks_performed'],
                'average_check_interval': self.config['default_check_interval']
            }
        }
    
    async def get_health_analytics(
        self,
        service_name: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get health analytics and trends"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
            
            if service_name:
                # Get analytics for specific service
                return await self._get_service_analytics(service_name, start_time, end_time)
            else:
                # Get global analytics
                return await self._get_global_analytics(start_time, end_time)
                
        except Exception as e:
            logger.error(f"Failed to get health analytics: {e}")
            return {'error': str(e)}
    
    async def start_monitoring(self) -> None:
        """Start background health monitoring"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started background health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background health monitoring"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while True:
            try:
                tasks = []
                
                for service_name, monitor in self._monitors.items():
                    if not monitor.config.enabled:
                        continue
                    
                    # Check if it's time for this service's health check
                    if (monitor.last_check_time is None or
                        (datetime.now(timezone.utc) - monitor.last_check_time).total_seconds() >= 
                        monitor.config.check_interval_seconds):
                        
                        # Create health check task
                        task = asyncio.create_task(
                            self._perform_scheduled_health_check(service_name)
                        )
                        tasks.append(task)
                
                # Wait for all checks to complete (with timeout)
                if tasks:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=300)
                
                # Sleep until next cycle
                await asyncio.sleep(self.config['default_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _perform_scheduled_health_check(self, service_name: str) -> None:
        """Perform scheduled health check for service"""
        try:
            monitor = self._monitors[service_name]
            
            # Perform health check
            result = await monitor.perform_health_check(HealthCheckType.HTTP)
            
            # Update global statistics
            self._global_stats['total_checks_performed'] += 1
            
            # Check for alerts
            await self._check_and_create_alerts(monitor, result)
            
            # Store result in cache
            await self._store_health_result(service_name, result)
            
        except Exception as e:
            logger.error(f"Scheduled health check failed for {service_name}: {e}")
    
    async def _check_and_create_alerts(self, monitor: ServiceHealthMonitor, result: HealthCheckResult) -> None:
        """Check conditions and create alerts if necessary"""
        try:
            alert_conditions = [
                (HealthCheckStatus.UNHEALTHY, AlertSeverity.ERROR, "Service is unhealthy"),
                (HealthCheckStatus.TIMEOUT, AlertSeverity.WARNING, "Service is timing out"),
                (HealthCheckStatus.ERROR, AlertSeverity.ERROR, "Service check error"),
                (HealthCheckStatus.DEGRADED, AlertSeverity.WARNING, "Service performance degraded")
            ]
            
            for status, severity, base_message in alert_conditions:
                if result.status == status:
                    await self._create_alert(
                        monitor.service_name,
                        base_message,
                        severity,
                        result,
                        f"{status.value}_threshold"
                    )
                    
                    break
            
            # Check response time threshold
            if (result.response_time_ms > monitor.config.response_time_threshold_ms and 
                result.response_time_ms > 0):
                await self._create_alert(
                    monitor.service_name,
                    f"High response time: {result.response_time_ms:.1f}ms",
                    AlertSeverity.WARNING,
                    result,
                    "response_time_threshold"
                )
            
        except Exception as e:
            logger.error(f"Failed to check alerts for {monitor.service_name}: {e}")
    
    async def _create_alert(
        self,
        service_name: str,
        message: str,
        severity: AlertSeverity,
        result: HealthCheckResult,
        alert_type: str
    ) -> None:
        """Create health alert"""
        try:
            alert_id = f"{service_name}:{alert_type}:{int(time.time())}"
            
            # Check cooldown period
            cooldown_key = f"{self.config['redis_namespace']}:alerts:cooldown:{service_name}:{alert_type}"
            last_alert_time = await self.redis_cache.get(cooldown_key)
            
            if last_alert_time:
                last_alert = datetime.fromisoformat(last_alert_time)
                time_diff = datetime.now(timezone.utc) - last_alert
                if time_diff.total_seconds() < self.config['alert_cooldown_minutes'] * 60:
                    return  # Still in cooldown
            
            # Create alert
            alert = HealthAlert(
                id=alert_id,
                service_name=service_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                threshold_value=0,  # Would be calculated based on type
                current_value=0,    # Would be calculated based on type
                metadata={
                    'health_check_result': result.__dict__,
                    'check_type': result.check_type.value,
                    'response_time_ms': result.response_time_ms
                }
            )
            
            # Store alert
            await self._store_alert(alert)
            
            # Set cooldown
            await self.redis_cache.set(
                cooldown_key,
                datetime.now(timezone.utc).isoformat(),
                ttl=self.config['alert_cooldown_minutes'] * 60
            )
            
            # Track alert in telemetry
            await self.event_tracker.track_event(
                "health_check_alert_created",
                {
                    "service_name": service_name,
                    "alert_type": alert_type,
                    "severity": severity.value,
                    "message": message[:100]
                }
            )
            
            logger.warning(f"Health alert created for {service_name}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to create alert for {service_name}: {e}")
    
    def _calculate_performance_score(
        self,
        availability_percent: float,
        avg_response_time_ms: float,
        error_rate_percent: float
    ) -> float:
        """Calculate overall performance score (0-100)"""
        # Availability component (40% weight)
        availability_score = min(availability_percent, 100) * 0.4
        
        # Response time component (35% weight)
        # Normalize response time (1000ms = 0 score)
        response_time_score = max(0, (1000 - avg_response_time_ms) / 1000) * 35
        
        # Error rate component (25% weight)
        # Normalize error rate (10% = 0 score)
        error_rate_score = max(0, (10 - error_rate_percent) / 10) * 25
        
        return availability_score + response_time_score + error_rate_score
    
    async def _get_service_analytics(self, service_name: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get analytics for specific service"""
        if service_name not in self._monitors:
            return {'error': f'Service {service_name} not found'}
        
        monitor = self._monitors[service_name]
        
        # Filter check history by time range
        filtered_results = [
            result for result in monitor.check_history
            if start_time <= result.timestamp <= end_time
        ]
        
        if not filtered_results:
            return {
                'service_name': service_name,
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'message': 'No health check data available for this period'
            }
        
        # Calculate analytics
        status_distribution = defaultdict(int)
        response_times = []
        total_checks = len(filtered_results)
        
        for result in filtered_results:
            status_distribution[result.status.value] += 1
            if result.response_time_ms > 0:
                response_times.append(result.response_time_ms)
        
        # Calculate trends
        hourly_stats = self._calculate_hourly_trends(filtered_results)
        
        return {
            'service_name': service_name,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'overview': {
                'total_checks': total_checks,
                'status_distribution': dict(status_distribution),
                'availability_percent': (status_distribution['healthy'] / max(1, total_checks)) * 100
            },
            'performance': {
                'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
                'median_response_time_ms': statistics.median(response_times) if response_times else 0,
                'p95_response_time_ms': self._calculate_percentile(response_times, 95) if response_times else 0,
                'max_response_time_ms': max(response_times) if response_times else 0,
                'min_response_time_ms': min(response_times) if response_times else 0
            },
            'trends': hourly_stats,
            'reliability': {
                'mttr_minutes': self._calculate_mttr(filtered_results),
                'mtbf_hours': self._calculate_mtbf(filtered_results),
                'uptime_percentage': (status_distribution['healthy'] / max(1, total_checks)) * 100
            }
        }
    
    async def _get_global_analytics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get global health analytics"""
        all_results = []
        
        for monitor in self._monitors.values():
            filtered_results = [
                result for result in monitor.check_history
                if start_time <= result.timestamp <= end_time
            ]
            all_results.extend(filtered_results)
        
        if not all_results:
            return {
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'message': 'No health check data available for this period'
            }
        
        # Aggregate statistics across all services
        global_status_distribution = defaultdict(int)
        service_health_summary = {}
        
        for service_name, monitor in self._monitors.items():
            service_health_summary[service_name] = {
                'current_status': monitor.get_current_status().value,
                'total_checks': monitor.total_checks,
                'success_rate': (monitor.successful_checks / max(1, monitor.total_checks)) * 100
            }
            
            for result in monitor.check_history:
                if start_time <= result.timestamp <= end_time:
                    global_status_distribution[result.status.value] += 1
        
        return {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'global_overview': {
                'total_services': len(self._monitors),
                'total_checks': len(all_results),
                'global_status_distribution': dict(global_status_distribution)
            },
            'service_summaries': service_health_summary,
            'system_health': {
                'overall_availability': (global_status_distribution['healthy'] / max(1, len(all_results))) * 100,
                'services_healthy': len([s for s in service_health_summary.values() if s['current_status'] == 'healthy']),
                'services_degraded': len([s for s in service_health_summary.values() if s['current_status'] == 'degraded']),
                'services_unhealthy': len([s for s in service_health_summary.values() if s['current_status'] == 'unhealthy'])
            }
        }
    
    def _calculate_hourly_trends(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Calculate hourly trend statistics"""
        hourly_data = defaultdict(lambda: {'total': 0, 'healthy': 0, 'response_times': []})
        
        for result in results:
            hour = result.timestamp.strftime('%Y-%m-%d-%H')
            hourly_data[hour]['total'] += 1
            if result.status == HealthCheckStatus.HEALTHY:
                hourly_data[hour]['healthy'] += 1
            if result.response_time_ms > 0:
                hourly_data[hour]['response_times'].append(result.response_time_ms)
        
        # Calculate trends
        hourly_stats = []
        for hour, data in sorted(hourly_data.items()):
            availability = (data['healthy'] / max(1, data['total'])) * 100
            avg_response_time = statistics.mean(data['response_times']) if data['response_times'] else 0
            
            hourly_stats.append({
                'hour': hour,
                'availability_percent': round(availability, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'total_checks': data['total'],
                'healthy_checks': data['healthy']
            })
        
        return {
            'hourly_breakdown': hourly_stats,
            'trend_analysis': self._analyze_trend(hourly_stats)
        }
    
    def _analyze_trend(self, hourly_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in hourly data"""
        if len(hourly_stats) < 2:
            return {'trend': 'insufficient_data'}
        
        availability_values = [stat['availability_percent'] for stat in hourly_stats]
        
        # Calculate trend direction
        recent_avg = statistics.mean(availability_values[-3:])  # Last 3 hours
        earlier_avg = statistics.mean(availability_values[:3])  # First 3 hours
        
        if recent_avg > earlier_avg * 1.02:
            trend = 'improving'
        elif recent_avg < earlier_avg * 0.98:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # Calculate volatility
        volatility = statistics.stdev(availability_values) if len(availability_values) > 1 else 0
        
        return {
            'trend_direction': trend,
            'volatility': round(volatility, 2),
            'stability_score': max(0, 100 - volatility)
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _calculate_mttr(self, results: List[HealthCheckResult]) -> float:
        """Calculate Mean Time To Recovery in minutes"""
        failure_periods = []
        current_failure_start = None
        
        for result in results:
            if result.status != HealthCheckStatus.HEALTHY:
                if current_failure_start is None:
                    current_failure_start = result.timestamp
            else:
                if current_failure_start is not None:
                    failure_periods.append((result.timestamp - current_failure_start).total_seconds() / 60)
                    current_failure_start = None
        
        if failure_periods:
            return statistics.mean(failure_periods)
        return 0.0
    
    def _calculate_mtbf(self, results: List[HealthCheckResult]) -> float:
        """Calculate Mean Time Between Failures in hours"""
        uptime_periods = []
        last_failure_time = None
        
        for result in results:
            if result.status != HealthCheckStatus.HEALTHY:
                last_failure_time = result.timestamp
            else:
                if last_failure_time is not None:
                    # Calculate time until next failure or end of period
                    uptime_periods.append((result.timestamp - last_failure_time).total_seconds() / 3600)
        
        if uptime_periods:
            return statistics.mean(uptime_periods)
        return 0.0
    
    # Storage methods (simplified implementations)
    async def _store_service_metadata(self, service_name: str, metadata: Dict[str, Any]) -> None:
        """Store service metadata"""
        cache_key = f"{self.config['redis_namespace']}:service:{service_name}"
        await self.redis_cache.set(cache_key, json.dumps(metadata), ttl=86400 * 7)  # 7 days
    
    async def _get_service_metadata(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service metadata"""
        cache_key = f"{self.config['redis_namespace']}:service:{service_name}"
        cached_metadata = await self.redis_cache.get(cache_key)
        
        if cached_metadata:
            try:
                return json.loads(cached_metadata)
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def _remove_service_metadata(self, service_name: str) -> None:
        """Remove service metadata"""
        cache_key = f"{self.config['redis_namespace']}:service:{service_name}"
        await self.redis_cache.delete(cache_key)
    
    async def _store_health_result(self, service_name: str, result: HealthCheckResult) -> None:
        """Store health check result"""
        cache_key = f"{self.config['redis_namespace']}:results:{service_name}"
        result_data = {
            'service_name': result.service_name,
            'check_type': result.check_type.value,
            'status': result.status.value,
            'response_time_ms': result.response_time_ms,
            'timestamp': result.timestamp.isoformat(),
            'message': result.message,
            'error_details': result.error_details,
            'status_code': result.status_code
        }
        
        await self.redis_cache.lpush(cache_key, json.dumps(result_data))
        await self.redis_cache.ltrim(cache_key, 0, 999)  # Keep last 1000 results
        await self.redis_cache.expire(cache_key, 86400 * 7)  # 7 days
    
    async def _store_alert(self, alert: HealthAlert) -> None:
        """Store health alert"""
        cache_key = f"{self.config['redis_namespace']}:alerts"
        alert_data = {
            'id': alert.id,
            'service_name': alert.service_name,
            'alert_type': alert.alert_type,
            'severity': alert.severity.value,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'acknowledged': alert.acknowledged,
            'resolved': alert.resolved,
            'metadata': alert.metadata
        }
        
        await self.redis_cache.lpush(cache_key, json.dumps(alert_data))
        await self.redis_cache.ltrim(cache_key, 0, 999)  # Keep last 1000 alerts
        await self.redis_cache.expire(cache_key, 86400 * 30)  # 30 days
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired health data"""
        try:
            cleanup_count = 0
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=self.config['health_history_retention_hours'])
            
            for monitor in self._monitors.values():
                # Clean up old check history
                old_results = [
                    result for result in monitor.check_history
                    if result.timestamp < cutoff_time
                ]
                
                for old_result in old_results:
                    if old_result in monitor.check_history:
                        monitor.check_history.remove(old_result)
                        cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired health check results")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        await self.stop_monitoring()
        
        # Clear all monitors
        self._monitors.clear()
        
        logger.info("HealthChecker closed")