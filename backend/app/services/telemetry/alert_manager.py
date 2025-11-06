"""
Alerting system for critical metrics in the Fernando platform.

This module provides comprehensive alerting capabilities including:
- Metric threshold alerting
- Performance degradation alerts
- Error rate monitoring
- System resource alerts
- Custom business logic alerts
- Alert escalation and notification
- Alert acknowledgment and resolution

Features:
- Real-time metric monitoring
- Configurable alert thresholds
- Multiple notification channels
- Alert correlation and grouping
- Alert history and analytics
- Integration with external alerting systems
"""

import asyncio
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict
import json


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status values."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCategory(Enum):
    """Alert categories."""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SECURITY = "security"
    BUSINESS = "business"
    SYSTEM = "system"
    COST = "cost"
    COMPLIANCE = "compliance"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    category: AlertCategory
    severity: AlertSeverity
    metric_name: str
    condition: str  # e.g., ">", "<", ">=", "<=", "==", "!="
    threshold: float
    evaluation_period: int  # seconds
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert instance."""
    id: str
    rule_name: str
    rule_category: AlertCategory
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    occurrences: int = 1
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationChannel:
    """Notification channel configuration."""
    name: str
    type: str  # email, slack, webhook, sms
    config: Dict[str, Any]
    enabled: bool = True
    severity_filter: List[AlertSeverity] = field(default_factory=list)


class AlertManager:
    """
    Comprehensive alert management system.
    
    Provides real-time alerting based on metrics thresholds,
    performance monitoring, and custom business logic.
    """
    
    def __init__(self, max_alerts: int = 1000):
        """Initialize the alert manager.
        
        Args:
            max_alerts: Maximum number of alerts to keep in memory
        """
        self.max_alerts = max_alerts
        
        # Thread-safe data storage
        self._lock = threading.RLock()
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=max_alerts)
        self._notification_channels: Dict[str, NotificationChannel] = {}
        
        # Alert statistics and tracking
        self._alert_statistics: Dict[str, int] = defaultdict(int)
        self._severity_counts: Dict[AlertSeverity, int] = defaultdict(int)
        self._category_counts: Dict[AlertCategory, int] = defaultdict(int)
        
        # Background alert monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Alert event handlers
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._resolution_handlers: List[Callable[[Alert], None]] = []
        
        # Default alert rules
        self._setup_default_alert_rules()
        
        logger.info("Alert manager initialized with max_alerts=%d", max_alerts)
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules."""
        default_rules = [
            # Performance alerts
            AlertRule(
                name="High Response Time",
                category=AlertCategory.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                metric_name="response_time",
                condition=">",
                threshold=2000.0,
                evaluation_period=300,
                metadata={"unit": "ms", "description": "API response time exceeds 2 seconds"}
            ),
            AlertRule(
                name="High Error Rate",
                category=AlertCategory.RELIABILITY,
                severity=AlertSeverity.CRITICAL,
                metric_name="error_rate",
                condition=">",
                threshold=10.0,
                evaluation_period=60,
                metadata={"unit": "%", "description": "Error rate exceeds 10%"}
            ),
            # System alerts
            AlertRule(
                name="High CPU Usage",
                category=AlertCategory.SYSTEM,
                severity=AlertSeverity.HIGH,
                metric_name="cpu_usage",
                condition=">",
                threshold=90.0,
                evaluation_period=180,
                metadata={"unit": "%", "description": "CPU usage exceeds 90%"}
            ),
            AlertRule(
                name="High Memory Usage",
                category=AlertCategory.SYSTEM,
                severity=AlertSeverity.HIGH,
                metric_name="memory_usage",
                condition=">",
                threshold=95.0,
                evaluation_period=180,
                metadata={"unit": "%", "description": "Memory usage exceeds 95%"}
            ),
            # Business alerts
            AlertRule(
                name="Payment Failure Rate",
                category=AlertCategory.BUSINESS,
                severity=AlertSeverity.HIGH,
                metric_name="payment_failure_rate",
                condition=">",
                threshold=5.0,
                evaluation_period=300,
                metadata={"unit": "%", "description": "Payment failure rate exceeds 5%"}
            ),
            AlertRule(
                name="Low Success Rate",
                category=AlertCategory.RELIABILITY,
                severity=AlertSeverity.MEDIUM,
                metric_name="success_rate",
                condition="<",
                threshold=95.0,
                evaluation_period=300,
                metadata={"unit": "%", "description": "Success rate below 95%"}
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.name] = rule
        
        logger.info(f"Setup {len(default_rules)} default alert rules")
    
    async def start(self):
        """Start the alert manager monitoring."""
        if self._running:
            return
            
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_alerts())
        logger.info("Alert manager started")
    
    async def stop(self):
        """Stop the alert manager monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert manager stopped")
    
    async def _monitor_alerts(self):
        """Background task for continuous alert monitoring."""
        try:
            while self._running:
                await self._evaluate_alert_rules()
                await asyncio.sleep(30)  # Check every 30 seconds
        except asyncio.CancelledError:
            logger.info("Alert monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")
    
    async def _evaluate_alert_rules(self):
        """Evaluate all enabled alert rules."""
        from .metrics_collector import metrics_collector
        
        for rule_name, rule in self._alert_rules.items():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_single_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule_name}: {e}")
    
    async def _evaluate_single_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        from .metrics_collector import metrics_collector
        
        # Get recent metrics data
        cutoff_time = datetime.utcnow() - timedelta(seconds=rule.evaluation_period)
        recent_metrics = metrics_collector.get_recent_metrics(
            rule.metric_name, 
            duration_minutes=rule.evaluation_period // 60
        )
        
        if not recent_metrics:
            return
        
        # Calculate average value over evaluation period
        values = [m.value for m in recent_metrics if m.timestamp >= cutoff_time]
        if not values:
            return
        
        avg_value = sum(values) / len(values)
        
        # Check if condition is met
        if self._check_condition(avg_value, rule.condition, rule.threshold):
            await self._trigger_alert(rule, avg_value)
        else:
            await self._resolve_alert_if_exists(rule.name, avg_value)
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check if a condition is met."""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return abs(value - threshold) < 0.001  # Small epsilon for float comparison
        elif condition == "!=":
            return abs(value - threshold) >= 0.001
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule, current_value: float):
        """Trigger an alert for a rule."""
        alert_id = rule.name
        
        with self._lock:
            if alert_id in self._active_alerts:
                # Alert already active, increment occurrence count
                alert = self._active_alerts[alert_id]
                alert.occurrences += 1
                alert.current_value = current_value
            else:
                # Create new alert
                alert = Alert(
                    id=alert_id,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    title=f"Alert: {rule.name}",
                    message=f"{rule.metric_name} is {current_value:.2f}, threshold is {rule.threshold}",
                    metric_name=rule.metric_name,
                    current_value=current_value,
                    threshold=rule.threshold,
                    triggered_at=datetime.utcnow(),
                    metadata=rule.metadata.copy(),
                    tags=rule.tags.copy()
                )
                
                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)
                
                # Update statistics
                self._alert_statistics["total_alerts"] += 1
                self._severity_counts[rule.severity] += 1
                self._category_counts[rule.category] += 1
                
                logger.warning(f"Alert triggered: {rule.name} - {rule.metric_name} = {current_value}")
                
                # Send notifications
                await self._send_notifications(alert)
                
                # Call alert handlers
                for handler in self._alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Error in alert handler: {e}")
    
    async def _resolve_alert_if_exists(self, rule_name: str, current_value: float):
        """Resolve an alert if the condition is no longer met."""
        if rule_name not in self._active_alerts:
            return
        
        alert = self._active_alerts[rule_name]
        
        # Only resolve if alert has been active for some time
        if (datetime.utcnow() - alert.triggered_at).total_seconds() < 60:
            return
        
        with self._lock:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.current_value = current_value
            
            # Remove from active alerts
            del self._active_alerts[rule_name]
            
            logger.info(f"Alert resolved: {rule_name} - value normalized to {current_value}")
            
            # Call resolution handlers
            for handler in self._resolution_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Error in resolution handler: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        for channel_name, channel in self._notification_channels.items():
            if not channel.enabled:
                continue
            
            # Check severity filter
            if channel.severity_filter and alert.severity not in channel.severity_filter:
                continue
            
            try:
                await self._send_to_channel(channel, alert)
            except Exception as e:
                logger.error(f"Error sending notification to {channel_name}: {e}")
    
    async def _send_to_channel(self, channel: NotificationChannel, alert: Alert):
        """Send notification to a specific channel."""
        if channel.type == "email":
            await self._send_email_notification(channel, alert)
        elif channel.type == "slack":
            await self._send_slack_notification(channel, alert)
        elif channel.type == "webhook":
            await self._send_webhook_notification(channel, alert)
        elif channel.type == "console":
            await self._send_console_notification(channel, alert)
        else:
            logger.warning(f"Unknown notification channel type: {channel.type}")
    
    async def _send_email_notification(self, channel: NotificationChannel, alert: Alert):
        """Send email notification."""
        # This would integrate with actual email service
        logger.info(f"Email notification: {alert.title}")
    
    async def _send_slack_notification(self, channel: NotificationChannel, alert: Alert):
        """Send Slack notification."""
        # This would integrate with actual Slack API
        logger.info(f"Slack notification: {alert.title}")
    
    async def _send_webhook_notification(self, channel: NotificationChannel, alert: Alert):
        """Send webhook notification."""
        import aiohttp
        
        webhook_url = channel.config.get("url")
        if not webhook_url:
            return
        
        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "triggered_at": alert.triggered_at.isoformat(),
            "tags": alert.tags
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.debug(f"Webhook notification sent successfully: {alert.id}")
                    else:
                        logger.warning(f"Webhook notification failed: {response.status}")
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    async def _send_console_notification(self, channel: NotificationChannel, alert: Alert):
        """Send console notification."""
        color = {
            AlertSeverity.CRITICAL: "\033[91m",  # Red
            AlertSeverity.HIGH: "\033[93m",      # Yellow
            AlertSeverity.MEDIUM: "\033[94m",    # Blue
            AlertSeverity.LOW: "\033[92m",       # Green
            AlertSeverity.INFO: "\033[96m"       # Cyan
        }.get(alert.severity, "\033[0m")
        
        reset_color = "\033[0m"
        
        print(f"{color}ALERT: {alert.title}{reset_color}")
        print(f"Severity: {alert.severity.value}")
        print(f"Metric: {alert.metric_name} = {alert.current_value:.2f} (threshold: {alert.threshold})")
        print(f"Time: {alert.triggered_at}")
        print("-" * 50)
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        with self._lock:
            self._alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        with self._lock:
            if rule_name in self._alert_rules:
                del self._alert_rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
            else:
                logger.warning(f"Alert rule not found: {rule_name}")
    
    def update_alert_rule(self, rule_name: str, **updates):
        """Update an existing alert rule."""
        with self._lock:
            if rule_name not in self._alert_rules:
                logger.warning(f"Alert rule not found: {rule_name}")
                return
            
            rule = self._alert_rules[rule_name]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
        
        logger.info(f"Updated alert rule: {rule_name}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge an alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.utcnow()
                alert.metadata["acknowledged_by"] = acknowledged_by
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            else:
                logger.warning(f"Alert not found for acknowledgment: {alert_id}")
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system"):
        """Manually resolve an alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.metadata["resolved_by"] = resolved_by
                
                del self._active_alerts[alert_id]
                
                logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            else:
                logger.warning(f"Alert not found for resolution: {alert_id}")
    
    def suppress_alert(self, alert_id: str, duration_minutes: int = 60):
        """Suppress an alert for a specified duration."""
        suppression_end = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.SUPPRESSED
                alert.metadata["suppression_end"] = suppression_end.isoformat()
                
                logger.info(f"Alert suppressed: {alert_id} for {duration_minutes} minutes")
            else:
                logger.warning(f"Alert not found for suppression: {alert_id}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self._lock:
            return list(self._active_alerts.values())
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Alert]:
        """Get alert history."""
        with self._lock:
            history = list(self._alert_history)
            if limit:
                history = history[-limit:]
            return history
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity level."""
        with self._lock:
            return [alert for alert in self._active_alerts.values() 
                   if alert.severity == severity]
    
    def get_alerts_by_category(self, category: AlertCategory) -> List[Alert]:
        """Get alerts by category."""
        with self._lock:
            return [alert for alert in self._active_alerts.values() 
                   if alert.rule_category == category]
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel."""
        with self._lock:
            self._notification_channels[channel.name] = channel
        logger.info(f"Added notification channel: {channel.name}")
    
    def remove_notification_channel(self, channel_name: str):
        """Remove a notification channel."""
        with self._lock:
            if channel_name in self._notification_channels:
                del self._notification_channels[channel_name]
                logger.info(f"Removed notification channel: {channel_name}")
            else:
                logger.warning(f"Notification channel not found: {channel_name}")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert event handler."""
        self._alert_handlers.append(handler)
    
    def add_resolution_handler(self, handler: Callable[[Alert], None]):
        """Add an alert resolution event handler."""
        self._resolution_handlers.append(handler)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        with self._lock:
            # Calculate resolution statistics
            total_history = len(self._alert_history)
            resolved_alerts = sum(1 for alert in self._alert_history if alert.status == AlertStatus.RESOLVED)
            active_alerts = len(self._active_alerts)
            
            # Time-based statistics
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            alerts_last_24h = sum(1 for alert in self._alert_history 
                                if alert.triggered_at >= last_24h)
            
            # Average resolution time
            resolution_times = []
            for alert in self._alert_history:
                if alert.resolved_at:
                    resolution_time = (alert.resolved_at - alert.triggered_at).total_seconds()
                    resolution_times.append(resolution_time)
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            return {
                "total_alerts": total_history + active_alerts,
                "active_alerts": active_alerts,
                "resolved_alerts": resolved_alerts,
                "alerts_last_24h": alerts_last_24h,
                "severity_distribution": {sev.value: count for sev, count in self._severity_counts.items()},
                "category_distribution": {cat.value: count for cat, count in self._category_counts.items()},
                "avg_resolution_time_seconds": avg_resolution_time,
                "resolution_rate": (resolved_alerts / total_history * 100) if total_history > 0 else 0,
                "notification_channels": len(self._notification_channels),
                "alert_rules": len(self._alert_rules)
            }
    
    def check_custom_condition(self, condition_func: Callable[[], bool], 
                             alert_title: str, alert_message: str,
                             severity: AlertSeverity = AlertSeverity.MEDIUM,
                             category: AlertCategory = AlertCategory.SYSTEM) -> str:
        """Check a custom condition and trigger alert if needed."""
        try:
            if condition_func():
                # Create a temporary rule for this custom alert
                rule = AlertRule(
                    name=f"Custom: {alert_title}",
                    category=category,
                    severity=severity,
                    metric_name="custom",
                    condition="custom",
                    threshold=0,
                    evaluation_period=0  # Immediate evaluation
                )
                
                # Generate a unique alert ID
                alert_id = f"custom_{int(time.time())}_{hash(alert_title) % 10000}"
                
                asyncio.create_task(self._trigger_custom_alert(rule, alert_id, alert_message))
                return alert_id
        except Exception as e:
            logger.error(f"Error checking custom condition: {e}")
        
        return ""
    
    async def _trigger_custom_alert(self, rule: AlertRule, alert_id: str, message: str):
        """Trigger a custom alert."""
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            rule_category=rule.category,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=rule.name,
            message=message,
            metric_name="custom",
            current_value=0.0,
            threshold=0.0,
            triggered_at=datetime.utcnow()
        )
        
        with self._lock:
            self._active_alerts[alert_id] = alert
            self._alert_history.append(alert)
        
        await self._send_notifications(alert)
        
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in custom alert handler: {e}")


# Global alert manager instance
alert_manager = AlertManager()


# Convenience functions for external use
def create_alert_rule(name: str, metric_name: str, condition: str, threshold: float,
                     severity: AlertSeverity = AlertSeverity.MEDIUM,
                     category: AlertCategory = AlertCategory.SYSTEM) -> AlertRule:
    """Create an alert rule."""
    return AlertRule(
        name=name,
        category=category,
        severity=severity,
        metric_name=metric_name,
        condition=condition,
        threshold=threshold,
        evaluation_period=300  # 5 minutes default
    )


def add_alert_rule(rule: AlertRule):
    """Add an alert rule to the global alert manager."""
    alert_manager.add_alert_rule(rule)


def create_notification_channel(name: str, type: str, config: Dict[str, Any],
                               severity_filter: Optional[List[AlertSeverity]] = None) -> NotificationChannel:
    """Create a notification channel."""
    return NotificationChannel(
        name=name,
        type=type,
        config=config,
        severity_filter=severity_filter or []
    )


def add_notification_channel(channel: NotificationChannel):
    """Add a notification channel to the global alert manager."""
    alert_manager.add_notification_channel(channel)


def check_alert_condition(condition_func: Callable[[], bool], title: str, message: str,
                         severity: AlertSeverity = AlertSeverity.MEDIUM) -> str:
    """Check a custom alert condition."""
    return alert_manager.check_custom_condition(condition_func, title, message, severity)