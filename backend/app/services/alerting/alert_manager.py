"""
Central Alert Manager Service

Handles all alert-related operations including rule evaluation,
alert triggering, and coordination with notification services.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from jinja2 import Template

from app.models.alert import Alert, AlertRule, AlertStatus, AlertSeverity, AlertType, AlertTemplate, MetricThreshold
from app.models.user import User
from app.services.alert_channels import AlertChannelService
from app.services.alert_escalation import AlertEscalationService
from app.services.alert_rules import AlertRuleEngine
from app.core.config import settings


logger = logging.getLogger(__name__)


class AlertManager:
    """
    Central alert management service that coordinates all alerting operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_service = AlertChannelService(db)
        self.escalation_service = AlertEscalationService(db)
        self.rule_engine = AlertRuleEngine(db)
        self._active_evaluations = set()
        
    async def evaluate_all_rules(self) -> Dict[str, Any]:
        """
        Evaluate all enabled alert rules and trigger alerts as needed.
        
        Returns:
            Evaluation results with summary statistics
        """
        start_time = datetime.utcnow()
        results = {
            "evaluation_time": start_time,
            "rules_evaluated": 0,
            "alerts_triggered": 0,
            "alerts_resolved": 0,
            "errors": []
        }
        
        try:
            # Get all enabled rules
            rules = self.db.query(AlertRule).filter(
                AlertRule.enabled == True
            ).all()
            
            results["rules_evaluated"] = len(rules)
            
            # Evaluate rules in batches to avoid overwhelming the system
            batch_size = 10
            for i in range(0, len(rules), batch_size):
                batch = rules[i:i + batch_size]
                
                # Evaluate rules concurrently with proper rate limiting
                tasks = []
                for rule in batch:
                    if rule.rule_id not in self._active_evaluations:
                        task = asyncio.create_task(self._evaluate_rule(rule))
                        tasks.append(task)
                        self._active_evaluations.add(rule.rule_id)
                
                if tasks:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for i, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            results["errors"].append({
                                "rule_id": batch[i].rule_id,
                                "error": str(result)
                            })
                            logger.error(f"Error evaluating rule {batch[i].rule_id}: {result}")
                        elif result:
                            if result.get("triggered"):
                                results["alerts_triggered"] += 1
                            if result.get("resolved"):
                                results["alerts_resolved"] += 1
                
                # Clean up completed evaluations
                for rule in batch:
                    self._active_evaluations.discard(rule.rule_id)
                
                # Small delay between batches to prevent overwhelming
                if i + batch_size < len(rules):
                    await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error during rule evaluation: {e}")
            results["errors"].append({"error": str(e)})
        
        # Send system health metrics
        await self._send_health_metrics(results)
        
        logger.info(f"Rule evaluation completed: {results}")
        return results
    
    async def _evaluate_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """
        Evaluate a single alert rule.
        
        Args:
            rule: AlertRule to evaluate
            
        Returns:
            Evaluation results
        """
        try:
            # Use the rule engine to evaluate the condition
            evaluation_result = await self.rule_engine.evaluate_rule(rule)
            
            if not evaluation_result:
                return {"triggered": False, "resolved": False}
            
            triggered = evaluation_result.get("triggered", False)
            resolved = evaluation_result.get("resolved", False)
            context = evaluation_result.get("context", {})
            
            if triggered:
                # Check if alert should be triggered based on cooldown
                should_trigger = await self._should_trigger_alert(rule, context)
                if should_trigger:
                    alert = await self.trigger_alert(rule, context)
                    await self.process_alert_notifications(alert.alert_id)
                    await self.check_escalation(alert.alert_id)
                    
                    return {"triggered": True, "resolved": False, "alert_id": alert.alert_id}
            
            elif resolved:
                # Auto-resolve related alerts
                resolved_count = await self.auto_resolve_alerts(rule.rule_id, context)
                return {"triggered": False, "resolved": True, "resolved_count": resolved_count}
            
            return {"triggered": False, "resolved": False}
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            raise
    
    async def _should_trigger_alert(self, rule: AlertRule, context: Dict[str, Any]) -> bool:
        """
        Check if an alert should be triggered based on cooldown and deduplication.
        
        Args:
            rule: AlertRule being evaluated
            context: Evaluation context
            
        Returns:
            True if alert should be triggered
        """
        # Generate deduplication key
        dedup_key = self._generate_dedup_key(rule, context)
        
        # Check for existing active alerts with same dedup key
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.dedup_key == dedup_key,
                Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                Alert.triggered_at >= datetime.utcnow() - timedelta(seconds=rule.cooldown_period)
            )
        ).first()
        
        if existing_alert:
            return False
        
        return True
    
    def _generate_dedup_key(self, rule: AlertRule, context: Dict[str, Any]) -> str:
        """
        Generate a deduplication key for alert deduplication.
        
        Args:
            rule: AlertRule
            context: Evaluation context
            
        Returns:
            Deduplication key
        """
        import hashlib
        
        # Create a deterministic key based on rule and key context elements
        key_components = [
            rule.rule_id,
            str(sorted(context.get("labels", {}).items())),
            context.get("metric_name", ""),
            str(context.get("threshold_value", ""))
        ]
        
        key_string = "|".join(str(comp) for comp in key_components)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def trigger_alert(self, rule: AlertRule, context: Dict[str, Any]) -> Alert:
        """
        Trigger a new alert based on rule evaluation.
        
        Args:
            rule: AlertRule that triggered
            context: Evaluation context
            
        Returns:
            Created Alert instance
        """
        # Generate alert content from context
        alert_content = await self._generate_alert_content(rule, context)
        
        # Create alert
        alert = Alert(
            rule_id=rule.rule_id,
            status=AlertStatus.ACTIVE,
            severity=rule.severity,
            alert_type=rule.alert_type,
            title=alert_content["title"],
            description=alert_content["description"],
            message=alert_content["message"],
            context=context,
            metric_value=context.get("metric_value"),
            threshold_value=context.get("threshold_value"),
            labels=context.get("labels", {}),
            dedup_key=self._generate_dedup_key(rule, context),
            runbook_url=rule.metadata.get("runbook_url"),
            source_system=context.get("source_system", "alert_manager")
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert triggered: {alert.alert_id} for rule: {rule.rule_id}")
        
        # Update rule statistics
        await self._update_rule_statistics(rule)
        
        return alert
    
    async def _generate_alert_content(self, rule: AlertRule, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate alert content using templates or defaults.
        
        Args:
            rule: AlertRule
            context: Evaluation context
            
        Returns:
            Alert content dictionary with title, description, message
        """
        # Try to find a matching template
        template = self.db.query(AlertTemplate).filter(
            and_(
                AlertTemplate.channel == None,  # Default template
                or_(
                    AlertTemplate.alert_type == rule.alert_type,
                    AlertTemplate.alert_type == None
                ),
                or_(
                    AlertTemplate.severity == rule.severity,
                    AlertTemplate.severity == None
                )
            )
        ).first()
        
        if template:
            return await self._render_template_content(template, rule, context)
        else:
            return self._generate_default_content(rule, context)
    
    async def _render_template_content(self, template: AlertTemplate, rule: AlertRule, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Render alert content from template.
        
        Args:
            template: AlertTemplate
            rule: AlertRule
            context: Evaluation context
            
        Returns:
            Rendered content
        """
        try:
            # Prepare template variables
            template_vars = {
                "alert": {
                    "severity": rule.severity,
                    "type": rule.alert_type,
                    "rule_name": rule.name,
                    "rule_description": rule.description
                },
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
                "metric_value": context.get("metric_value"),
                "threshold_value": context.get("threshold_value"),
                "labels": context.get("labels", {})
            }
            
            title_template = Template(template.subject_template or "{{alert.rule_name}}")
            body_template = Template(template.body_template)
            
            content = {
                "title": title_template.render(**template_vars),
                "description": rule.description or "",
                "message": body_template.render(**template_vars)
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Error rendering template {template.template_id}: {e}")
            return self._generate_default_content(rule, context)
    
    def _generate_default_content(self, rule: AlertRule, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate default alert content when no template is available.
        
        Args:
            rule: AlertRule
            context: Evaluation context
            
        Returns:
            Default content
        """
        metric_value = context.get("metric_value")
        threshold_value = context.get("threshold_value")
        metric_name = context.get("metric_name", "metric")
        
        title = f"{rule.severity.upper()} - {rule.name}"
        
        if metric_value is not None and threshold_value is not None:
            message = f"Alert triggered: {metric_name} value ({metric_value}) exceeds threshold ({threshold_value})"
        else:
            message = f"Alert rule '{rule.name}' has been triggered"
        
        description = rule.description or f"Alert rule: {rule.alert_type} - {rule.severity}"
        
        return {
            "title": title,
            "description": description,
            "message": message
        }
    
    async def process_alert_notifications(self, alert_id: str) -> None:
        """
        Process notifications for a triggered alert.
        
        Args:
            alert_id: Alert ID to process notifications for
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return
        
        rule = alert.rule
        if not rule or not rule.channels:
            return
        
        try:
            # Process notifications for each channel
            for channel in rule.channels:
                if channel in rule.recipients:
                    recipients = rule.recipients[channel]
                    await self.channel_service.send_notifications(
                        alert=alert,
                        channel=channel,
                        recipients=recipients
                    )
            
            # Update alert notification tracking
            await self._update_notification_tracking(alert)
            
        except Exception as e:
            logger.error(f"Error processing notifications for alert {alert_id}: {e}")
    
    async def _update_notification_tracking(self, alert: Alert) -> None:
        """
        Update alert with notification tracking information.
        
        Args:
            alert: Alert to update
        """
        notification_summary = await self.channel_service.get_notification_summary(alert.alert_id)
        
        alert.notifications_sent = notification_summary
        alert.notification_count = notification_summary.get("total_count", 0)
        alert.last_notification_sent = datetime.utcnow()
        alert.last_updated = datetime.utcnow()
        
        self.db.commit()
    
    async def check_escalation(self, alert_id: str) -> None:
        """
        Check if an alert should be escalated.
        
        Args:
            alert_id: Alert ID to check for escalation
        """
        try:
            await self.escalation_service.check_escalation_rules(alert_id)
        except Exception as e:
            logger.error(f"Error checking escalation for alert {alert_id}: {e}")
    
    async def auto_resolve_alerts(self, rule_id: str, context: Dict[str, Any]) -> int:
        """
        Automatically resolve alerts for a rule when condition is no longer met.
        
        Args:
            rule_id: Rule ID
            context: Resolution context
            
        Returns:
            Number of alerts resolved
        """
        dedup_key = self._generate_dedup_key(
            self.db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first(),
            context
        )
        
        # Find active/acknowledged alerts that should be resolved
        alerts_to_resolve = self.db.query(Alert).filter(
            and_(
                Alert.rule_id == rule_id,
                Alert.dedup_key == dedup_key,
                Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
            )
        ).all()
        
        resolved_count = 0
        for alert in alerts_to_resolve:
            await self.resolve_alert(alert.alert_id, auto_resolved=True)
            resolved_count += 1
        
        return resolved_count
    
    async def acknowledge_alert(self, alert_id: str, user_id: str, note: Optional[str] = None) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            user_id: User ID acknowledging the alert
            note: Optional acknowledgment note
            
        Returns:
            True if successful
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert or alert.status != AlertStatus.ACTIVE:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        alert.last_updated = datetime.utcnow()
        
        if note:
            alert.resolution_notes = f"Acknowledged: {note}"
        
        self.db.commit()
        
        logger.info(f"Alert acknowledged: {alert_id} by user: {user_id}")
        return True
    
    async def resolve_alert(self, alert_id: str, user_id: Optional[str] = None, 
                          resolution_notes: Optional[str] = None, auto_resolved: bool = False) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
            user_id: Optional user ID resolving the alert
            resolution_notes: Resolution notes
            auto_resolved: Whether this was auto-resolved
            
        Returns:
            True if successful
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert or alert.status == AlertStatus.RESOLVED:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        alert.last_updated = datetime.utcnow()
        
        if resolution_notes:
            if auto_resolved:
                alert.resolution_notes = f"Auto-resolved: {resolution_notes}"
            else:
                alert.resolution_notes = f"Resolved: {resolution_notes}"
        
        self.db.commit()
        
        logger.info(f"Alert resolved: {alert_id} by user: {user_id or 'auto'}")
        return True
    
    async def suppress_alert(self, alert_id: str, reason: Optional[str] = None) -> bool:
        """
        Suppress an alert temporarily.
        
        Args:
            alert_id: Alert ID
            reason: Suppression reason
            
        Returns:
            True if successful
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert or alert.status == AlertStatus.SUPPRESSED:
            return False
        
        alert.status = AlertStatus.SUPPRESSED
        alert.last_updated = datetime.utcnow()
        
        if reason:
            alert.resolution_notes = f"Suppressed: {reason}"
        
        self.db.commit()
        
        logger.info(f"Alert suppressed: {alert_id}")
        return True
    
    async def get_alert_statistics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get comprehensive alert statistics.
        
        Args:
            time_range: Optional time range to filter statistics
            
        Returns:
            Statistics dictionary
        """
        query = self.db.query(Alert)
        
        if time_range:
            query = query.filter(Alert.triggered_at >= datetime.utcnow() - time_range)
        
        alerts = query.all()
        
        # Calculate statistics
        stats = {
            "total_alerts": len(alerts),
            "active_alerts": len([a for a in alerts if a.status == AlertStatus.ACTIVE]),
            "acknowledged_alerts": len([a for a in alerts if a.status == AlertStatus.ACKNOWLEDGED]),
            "resolved_alerts": len([a for a in alerts if a.status == AlertStatus.RESOLVED]),
            "critical_alerts": len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
            "high_alerts": len([a for a in alerts if a.severity == AlertSeverity.HIGH]),
            "medium_alerts": len([a for a in alerts if a.severity == AlertSeverity.MEDIUM]),
            "low_alerts": len([a for a in alerts if a.severity == AlertSeverity.LOW]),
            "alerts_by_type": {},
            "alerts_by_channel": {},
            "average_resolution_time": None
        }
        
        # Group by type
        for alert_type in AlertType:
            stats["alerts_by_type"][alert_type] = len([a for a in alerts if a.alert_type == alert_type])
        
        # Calculate average resolution time
        resolved_alerts = [a for a in alerts if a.status == AlertStatus.RESOLVED and a.resolved_at]
        if resolved_alerts:
            total_resolution_time = sum([
                (a.resolved_at - a.triggered_at).total_seconds() 
                for a in resolved_alerts
            ])
            stats["average_resolution_time"] = total_resolution_time / len(resolved_alerts) / 60  # minutes
        
        return stats
    
    async def _update_rule_statistics(self, rule: AlertRule) -> None:
        """
        Update rule statistics after alert trigger.
        
        Args:
            rule: AlertRule to update
        """
        # This would typically update counters, last_triggered, etc.
        # Implementation depends on specific requirements
        pass
    
    async def _send_health_metrics(self, evaluation_results: Dict[str, Any]) -> None:
        """
        Send health metrics to monitoring systems.
        
        Args:
            evaluation_results: Results from rule evaluation
        """
        try:
            metrics = {
                "alert_rules_evaluated": evaluation_results.get("rules_evaluated", 0),
                "alert_evaluation_errors": len(evaluation_results.get("errors", [])),
                "alerts_triggered": evaluation_results.get("alerts_triggered", 0),
                "alerts_resolved": evaluation_results.get("alerts_resolved", 0),
                "evaluation_duration": (datetime.utcnow() - evaluation_results["evaluation_time"]).total_seconds()
            }
            
            # Send to monitoring system (implementation depends on the system)
            logger.info(f"Sending health metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Error sending health metrics: {e}")
    
    def get_active_evaluation_count(self) -> int:
        """
        Get the number of currently active rule evaluations.
        
        Returns:
            Number of active evaluations
        """
        return len(self._active_evaluations)
    
    def cleanup_stuck_evaluations(self, timeout_minutes: int = 5) -> None:
        """
        Clean up stuck evaluations that have been running too long.
        
        Args:
            timeout_minutes: Timeout in minutes
        """
        # This would track evaluation start times and clean up stuck ones
        # Implementation depends on tracking mechanism
        pass


# Global alert manager instance (will be initialized per request)
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(db: Session) -> AlertManager:
    """
    Get or create alert manager instance.
    
    Args:
        db: Database session
        
    Returns:
        AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(db)
    return _alert_manager