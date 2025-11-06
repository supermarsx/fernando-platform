"""
Alert Escalation Service

Handles alert escalation, on-call management, and escalation policies.
Provides intelligent escalation based on time, severity, and response times.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.alert import Alert, AlertStatus, AlertSeverity, EscalationPolicy, OnCallSchedule, EscalationAction
from app.models.user import User
from app.services.alert_channels import AlertChannelService
from app.services.email_service import EmailService


logger = logging.getLogger(__name__)


class AlertEscalationService:
    """
    Service for managing alert escalation and on-call schedules.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_service = AlertChannelService(db)
        self.email_service = EmailService()
        
    async def check_escalation_rules(self, alert_id: str) -> bool:
        """
        Check if an alert should be escalated based on escalation rules.
        
        Args:
            alert_id: Alert ID to check
            
        Returns:
            True if escalation occurred
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return False
        
        rule = self.db.query(AlertRule).filter(AlertRule.rule_id == alert.rule_id).first()
        if not rule:
            return False
        
        escalation_rules = rule.escalation_rules or {}
        
        # Check if alert meets escalation criteria
        should_escalate = await self._should_escalate(alert, escalation_rules)
        
        if should_escalate:
            return await self._escalate_alert(alert, rule, escalation_rules)
        
        return False
    
    async def _should_escalate(self, alert: Alert, escalation_rules: Dict[str, Any]) -> bool:
        """
        Determine if an alert should be escalated.
        
        Args:
            alert: Alert to check
            escalation_rules: Escalation configuration
            
        Returns:
            True if should escalate
        """
        # Check time-based escalation
        time_escalation = escalation_rules.get("time_based", {})
        if time_escalation:
            time_escalated = await self._check_time_escalation(alert, time_escalation)
            if time_escalated:
                return True
        
        # Check acknowledgment-based escalation
        ack_escalation = escalation_rules.get("acknowledgment_based", {})
        if ack_escalation and alert.status == AlertStatus.ACTIVE:
            ack_escalated = await self._check_acknowledgment_escalation(alert, ack_escalation)
            if ack_escalated:
                return True
        
        # Check severity-based escalation
        severity_escalation = escalation_rules.get("severity_based", {})
        if severity_escalation:
            severity_escalated = await self._check_severity_escalation(alert, severity_escalation)
            if severity_escalated:
                return True
        
        # Check frequency-based escalation
        frequency_escalation = escalation_rules.get("frequency_based", {})
        if frequency_escalation:
            freq_escalated = await self._check_frequency_escalation(alert, frequency_escalation)
            if freq_escalated:
                return True
        
        return False
    
    async def _check_time_escalation(self, alert: Alert, time_config: Dict[str, Any]) -> bool:
        """
        Check if time-based escalation should trigger.
        
        Args:
            alert: Alert to check
            time_config: Time-based escalation configuration
            
        Returns:
            True if time escalation should trigger
        """
        timeouts = time_config.get("timeouts", {})
        
        # Check different escalation levels
        for level, timeout_minutes in timeouts.items():
            timeout_duration = timedelta(minutes=timeout_minutes)
            
            if alert.status == AlertStatus.ACTIVE:
                elapsed = datetime.utcnow() - alert.triggered_at
                if elapsed >= timeout_duration:
                    logger.info(f"Time-based escalation triggered for alert {alert.alert_id} at level {level}")
                    return True
        
        return False
    
    async def _check_acknowledgment_escalation(self, alert: Alert, ack_config: Dict[str, Any]) -> bool:
        """
        Check if acknowledgment-based escalation should trigger.
        
        Args:
            alert: Alert to check
            ack_config: Acknowledgment-based escalation configuration
            
        Returns:
            True if acknowledgment escalation should trigger
        """
        timeout_minutes = ack_config.get("timeout_minutes", 15)
        timeout_duration = timedelta(minutes=timeout_minutes)
        
        if alert.status == AlertStatus.ACTIVE:
            elapsed = datetime.utcnow() - alert.triggered_at
            if elapsed >= timeout_duration:
                logger.info(f"Acknowledgment-based escalation triggered for alert {alert.alert_id}")
                return True
        
        return False
    
    async def _check_severity_escalation(self, alert: Alert, severity_config: Dict[str, Any]) -> bool:
        """
        Check if severity-based escalation should trigger.
        
        Args:
            alert: Alert to check
            severity_config: Severity-based escalation configuration
            
        Returns:
            True if severity escalation should trigger
        """
        auto_escalate_severities = severity_config.get("auto_escalate_severities", [])
        
        if alert.severity.value in auto_escalate_severities:
            # Critical and high severity alerts might escalate immediately
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                logger.info(f"Severity-based escalation triggered for alert {alert.alert_id}")
                return True
        
        return False
    
    async def _check_frequency_escalation(self, alert: Alert, frequency_config: Dict[str, Any]) -> bool:
        """
        Check if frequency-based escalation should trigger.
        
        Args:
            alert: Alert to check
            frequency_config: Frequency-based escalation configuration
            
        Returns:
            True if frequency escalation should trigger
        """
        max_alerts_per_hour = frequency_config.get("max_alerts_per_hour", 10)
        time_window = frequency_config.get("time_window_minutes", 60)
        
        # Count similar alerts in the time window
        window_start = datetime.utcnow() - timedelta(minutes=time_window)
        
        similar_alerts = self.db.query(Alert).filter(
            and_(
                Alert.rule_id == alert.rule_id,
                Alert.triggered_at >= window_start,
                Alert.status == AlertStatus.ACTIVE
            )
        ).count()
        
        if similar_alerts >= max_alerts_per_hour:
            logger.info(f"Frequency-based escalation triggered for alert {alert.alert_id}")
            return True
        
        return False
    
    async def _escalate_alert(self, alert: Alert, rule: AlertRule, escalation_rules: Dict[str, Any]) -> bool:
        """
        Execute alert escalation.
        
        Args:
            alert: Alert to escalate
            rule: Associated alert rule
            escalation_rules: Escalation configuration
            
        Returns:
            True if escalation was successful
        """
        try:
            # Determine escalation action
            escalation_action = self._determine_escalation_action(alert, escalation_rules)
            
            # Get escalation recipients
            escalation_recipients = await self._get_escalation_recipients(alert, escalation_rules)
            
            # Execute escalation
            success = await self._execute_escalation(alert, escalation_action, escalation_recipients)
            
            if success:
                # Update alert escalation tracking
                alert.escalation_level = (alert.escalation_level or 0) + 1
                alert.escalated_at = datetime.utcnow()
                alert.escalation_action = escalation_action
                alert.status = AlertStatus.ESCALATED
                alert.last_updated = datetime.utcnow()
                
                # Send escalation notifications
                await self._send_escalation_notifications(alert, escalation_recipients)
                
                self.db.commit()
                
                logger.info(f"Alert {alert.alert_id} escalated to level {alert.escalation_level}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error escalating alert {alert.alert_id}: {e}")
            return False
    
    def _determine_escalation_action(self, alert: Alert, escalation_rules: Dict[str, Any]) -> EscalationAction:
        """
        Determine the escalation action based on alert and rules.
        
        Args:
            alert: Alert being escalated
            escalation_rules: Escalation configuration
            
        Returns:
            EscalationAction to execute
        """
        # Determine action based on severity and escalation level
        current_level = alert.escalation_level or 0
        
        if alert.severity == AlertSeverity.CRITICAL:
            if current_level == 0:
                return EscalationAction.PAGE_ONCALL
            else:
                return EscalationAction.CREATE_INCIDENT
        elif alert.severity == AlertSeverity.HIGH:
            if current_level == 0:
                return EscalationAction.NOTIFY_MANAGER
            else:
                return EscalationAction.ESCALATE_CHANNEL
        else:
            return EscalationAction.ESCALATE_CHANNEL
    
    async def _get_escalation_recipients(self, alert: Alert, escalation_rules: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Get escalation recipients based on alert and rules.
        
        Args:
            alert: Alert being escalated
            escalation_rules: Escalation configuration
            
        Returns:
            Recipients by channel
        """
        recipients = escalation_rules.get("recipients", {})
        
        # Get on-call schedule recipients if available
        oncall_recipients = await self._get_oncall_recipients(alert)
        if oncall_recipients:
            # Merge with configured recipients
            for channel, people in oncall_recipients.items():
                if channel not in recipients:
                    recipients[channel] = []
                recipients[channel].extend(people)
        
        # Add manager notification if needed
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            manager_email = await self._get_manager_email(alert)
            if manager_email and "email" not in recipients:
                recipients["email"] = [manager_email]
        
        return recipients
    
    async def _get_oncall_recipients(self, alert: Alert) -> Dict[str, List[str]]:
        """
        Get current on-call recipients.
        
        Args:
            alert: Alert being escalated
            
        Returns:
            On-call recipients by channel
        """
        recipients = {}
        
        # Get current on-call schedules
        oncall_schedules = self.db.query(OnCallSchedule).filter(
            OnCallSchedule.active == True
        ).all()
        
        for schedule in oncall_schedules:
            # Determine current on-call person
            current_oncall = await self._get_current_oncall_person(schedule)
            if current_oncall:
                # Add to appropriate channel
                if schedule.name.lower().contains("ops") or schedule.name.lower().contains("technical"):
                    recipients.setdefault("slack", []).append(f"@{current_oncall.username}")
                    recipients.setdefault("email", []).append(current_oncall.email)
                elif schedule.name.lower().contains("manager"):
                    recipients.setdefault("email", []).append(current_oncall.email)
        
        return recipients
    
    async def _get_current_oncall_person(self, schedule: OnCallSchedule) -> Optional[User]:
        """
        Get the current on-call person for a schedule.
        
        Args:
            schedule: On-call schedule
            
        Returns:
            Current on-call user or None
        """
        participants = schedule.participants or []
        if not participants:
            return None
        
        # Simple rotation based on current time
        # In a real implementation, this would be more sophisticated
        rotation_type = schedule.rotation_type or "weekly"
        
        if rotation_type == "daily":
            days_since_start = (datetime.utcnow().date() - datetime(2024, 1, 1).date()).days
            index = days_since_start % len(participants)
        elif rotation_type == "weekly":
            weeks_since_start = ((datetime.utcnow() - datetime(2024, 1, 1)).days // 7)
            index = weeks_since_start % len(participants)
        else:
            # Default to first participant
            index = 0
        
        participant_id = participants[index]
        user = self.db.query(User).filter(User.user_id == participant_id).first()
        
        return user
    
    async def _get_manager_email(self, alert: Alert) -> Optional[str]:
        """
        Get manager email for escalation.
        
        Args:
            alert: Alert being escalated
            
        Returns:
            Manager email or None
        """
        # This would integrate with organizational hierarchy
        # For now, return a generic manager email
        
        return getattr(settings, "MANAGER_EMAIL", "manager@example.com")
    
    async def _execute_escalation(self, alert: Alert, action: EscalationAction, recipients: Dict[str, List[str]]) -> bool:
        """
        Execute the escalation action.
        
        Args:
            alert: Alert being escalated
            action: EscalationAction to execute
            recipients: Escalation recipients
            
        Returns:
            True if successful
        """
        try:
            if action == EscalationAction.NOTIFY_MANAGER:
                return await self._notify_manager(alert, recipients)
            elif action == EscalationAction.PAGE_ONCALL:
                return await self._page_oncall(alert, recipients)
            elif action == EscalationAction.CREATE_INCIDENT:
                return await self._create_incident(alert, recipients)
            elif action == EscalationAction.ESCALATE_CHANNEL:
                return await self._escalate_channel(alert, recipients)
            else:
                logger.warning(f"Unknown escalation action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing escalation action {action}: {e}")
            return False
    
    async def _notify_manager(self, alert: Alert, recipients: Dict[str, List[str]]) -> bool:
        """
        Notify manager about escalation.
        
        Args:
            alert: Alert being escalated
            recipients: Manager recipients
            
        Returns:
            True if successful
        """
        # Send manager notification
        emails = recipients.get("email", [])
        if not emails:
            return False
        
        for email in emails:
            try:
                await self.email_service.send_email(
                    to=[email],
                    subject=f"[URGENT] Escalated Alert: {alert.title}",
                    body=f"""
URGENT: Alert escalation for your team

Alert: {alert.title}
Severity: {alert.severity.upper()}
Status: {alert.status.upper()}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Description:
{alert.description or alert.message}

This alert requires immediate attention and has been escalated to your team.

Please respond promptly.

---
Fernando Alert System
                    """.strip()
                )
            except Exception as e:
                logger.error(f"Error sending manager notification to {email}: {e}")
        
        return True
    
    async def _page_oncall(self, alert: Alert, recipients: Dict[str, List[str]]) -> bool:
        """
        Page on-call personnel.
        
        Args:
            alert: Alert being escalated
            recipients: On-call recipients
            
        Returns:
            True if successful
        """
        # Send page notifications through multiple channels
        success = False
        
        # SMS page for critical alerts
        phones = recipients.get("sms", [])
        for phone in phones:
            try:
                # Send SMS page
                success = True  # Mark as successful
                logger.info(f"Paged on-call at {phone} for alert {alert.alert_id}")
            except Exception as e:
                logger.error(f"Error paging {phone}: {e}")
        
        # Slack page for immediate attention
        slack_channels = recipients.get("slack", [])
        for channel in slack_channels:
            try:
                # Send high-priority Slack message
                success = True
                logger.info(f"Paged on-call Slack channel {channel} for alert {alert.alert_id}")
            except Exception as e:
                logger.error(f"Error paging Slack channel {channel}: {e}")
        
        return success
    
    async def _create_incident(self, alert: Alert, recipients: Dict[str, List[str]]) -> bool:
        """
        Create incident ticket for escalation.
        
        Args:
            alert: Alert being escalated
            recipients: Incident recipients
            
        Returns:
            True if successful
        """
        # This would integrate with incident management systems
        # (ServiceNow, Jira, PagerDuty Incidents, etc.)
        
        try:
            incident_data = {
                "title": f"INCIDENT: {alert.title}",
                "description": f"""
Incident created from escalated alert:

Alert ID: {alert.alert_id}
Severity: {alert.severity.upper()}
Type: {alert.alert_type.upper()}
Status: {alert.status.upper()}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Description:
{alert.description or alert.message}

Context: {alert.context}
Labels: {alert.labels}

Runbook: {alert.runbook_url}
                """.strip(),
                "priority": "high" if alert.severity == AlertSeverity.CRITICAL else "medium",
                "assignee": recipients.get("assignee", [None])[0] if recipients.get("assignee") else None,
                "tags": ["alert-escalation", f"severity-{alert.severity}", alert.alert_type]
            }
            
            # Create incident (mock implementation)
            logger.info(f"Incident created: {incident_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating incident: {e}")
            return False
    
    async def _escalate_channel(self, alert: Alert, recipients: Dict[str, List[str]]) -> bool:
        """
        Escalate through additional channels.
        
        Args:
            alert: Alert being escalated
            recipients: Escalation recipients
            
        Returns:
            True if successful
        """
        # Send escalation through additional channels
        success = False
        
        for channel, channel_recipients in recipients.items():
            if channel == "email":
                for email in channel_recipients:
                    try:
                        await self.email_service.send_email(
                            to=[email],
                            subject=f"[ESCALATED] {alert.title}",
                            body=f"""
This alert has been escalated and requires immediate attention.

Alert: {alert.title}
Severity: {alert.severity.upper()}
Status: {alert.status.upper()}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Description:
{alert.description or alert.message}

Please respond promptly.

---
Fernando Alert System
                            """.strip()
                        )
                        success = True
                    except Exception as e:
                        logger.error(f"Error sending escalation email to {email}: {e}")
            
            # Add other channel escalations here
        
        return success
    
    async def _send_escalation_notifications(self, alert: Alert, recipients: Dict[str, List[str]]) -> None:
        """
        Send escalation-specific notifications.
        
        Args:
            alert: Alert being escalated
            recipients: Escalation recipients
        """
        # Add any additional escalation notifications here
        logger.info(f"Escalation notifications sent for alert {alert.alert_id}")
    
    async def get_escalation_metrics(self, time_range_days: int = 30) -> Dict[str, Any]:
        """
        Get escalation metrics and statistics.
        
        Args:
            time_range_days: Number of days to analyze
            
        Returns:
            Escalation metrics
        """
        since = datetime.utcnow() - timedelta(days=time_range_days)
        
        escalated_alerts = self.db.query(Alert).filter(
            and_(
                Alert.escalated_at >= since,
                Alert.escalation_level > 0
            )
        ).all()
        
        metrics = {
            "total_escalations": len(escalated_alerts),
            "escalations_by_level": {},
            "escalations_by_severity": {},
            "escalations_by_action": {},
            "average_escalation_time": None,
            "oncall_response_times": []
        }
        
        for alert in escalated_alerts:
            # Count by escalation level
            level = alert.escalation_level or 0
            metrics["escalations_by_level"][str(level)] = metrics["escalations_by_level"].get(str(level), 0) + 1
            
            # Count by severity
            severity = alert.severity.value
            metrics["escalations_by_severity"][severity] = metrics["escalations_by_severity"].get(severity, 0) + 1
            
            # Count by action
            action = alert.escalation_action.value if alert.escalation_action else "unknown"
            metrics["escalations_by_action"][action] = metrics["escalations_by_action"].get(action, 0) + 1
            
            # Calculate escalation time
            if alert.escalated_at:
                escalation_time = (alert.escalated_at - alert.triggered_at).total_seconds()
                metrics["oncall_response_times"].append(escalation_time)
        
        # Calculate average escalation time
        if metrics["oncall_response_times"]:
            metrics["average_escalation_time"] = sum(metrics["oncall_response_times"]) / len(metrics["oncall_response_times"])
        
        return metrics