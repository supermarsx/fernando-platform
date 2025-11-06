"""
Alert Channels Service

Handles sending notifications through various channels including
email, Slack, Discord, webhooks, SMS, and push notifications.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.alert import Alert, AlertNotification, AlertChannel, AlertStatus
from app.models.user import User
from app.services.email_service import EmailService
import httpx
from jinja2 import Template


logger = logging.getLogger(__name__)


class AlertChannelService:
    """
    Service for sending alert notifications through various channels.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self._channel_configs = self._load_channel_configurations()
    
    def _load_channel_configurations(self) -> Dict[str, Any]:
        """
        Load channel configurations from environment or database.
        
        Returns:
            Channel configurations dictionary
        """
        return {
            "slack": {
                "webhook_url": getattr(settings, "SLACK_WEBHOOK_URL", None),
                "bot_token": getattr(settings, "SLACK_BOT_TOKEN", None),
                "default_channel": getattr(settings, "SLACK_DEFAULT_CHANNEL", "#alerts")
            },
            "discord": {
                "webhook_url": getattr(settings, "DISCORD_WEBHOOK_URL", None),
                "default_channel": getattr(settings, "DISCORD_DEFAULT_CHANNEL", None)
            },
            "webhook": {
                "timeout": getattr(settings, "WEBHOOK_TIMEOUT", 30),
                "retry_count": getattr(settings, "WEBHOOK_RETRY_COUNT", 3)
            },
            "sms": {
                "provider": getattr(settings, "SMS_PROVIDER", "twilio"),
                "account_sid": getattr(settings, "TWILIO_ACCOUNT_SID", None),
                "auth_token": getattr(settings, "TWILIO_AUTH_TOKEN", None),
                "from_number": getattr(settings, "TWILIO_FROM_NUMBER", None)
            },
            "push": {
                "firebase_key": getattr(settings, "FIREBASE_SERVER_KEY", None),
                "apns_key": getattr(settings, "APNS_KEY", None)
            }
        }
    
    async def send_notifications(self, alert: Alert, channel: AlertChannel, recipients: List[str]) -> Dict[str, Any]:
        """
        Send notifications for an alert through specified channel.
        
        Args:
            alert: Alert to send notifications for
            channel: AlertChannel to use
            recipients: List of recipient identifiers
            
        Returns:
            Notification results
        """
        results = {"successful": [], "failed": []}
        
        for recipient in recipients:
            try:
                success = await self._send_single_notification(alert, channel, recipient)
                if success:
                    results["successful"].append(recipient)
                else:
                    results["failed"].append(recipient)
            except Exception as e:
                logger.error(f"Error sending notification to {recipient} via {channel}: {e}")
                results["failed"].append(recipient)
        
        return results
    
    async def _send_single_notification(self, alert: Alert, channel: AlertChannel, recipient: str) -> bool:
        """
        Send a single notification.
        
        Args:
            alert: Alert to send
            channel: Notification channel
            recipient: Recipient identifier
            
        Returns:
            True if successful
        """
        # Create notification record
        notification = AlertNotification(
            alert_id=alert.alert_id,
            channel=channel,
            recipient=recipient,
            status="pending",
            subject=await self._generate_subject(alert, channel),
            content=await self._generate_content(alert, channel)
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Send based on channel type
        try:
            if channel == AlertChannel.EMAIL:
                success = await self._send_email(alert, recipient, notification)
            elif channel == AlertChannel.SLACK:
                success = await self._send_slack(alert, recipient, notification)
            elif channel == AlertChannel.DISCORD:
                success = await self._send_discord(alert, recipient, notification)
            elif channel == AlertChannel.WEBHOOK:
                success = await self._send_webhook(alert, recipient, notification)
            elif channel == AlertChannel.SMS:
                success = await self._send_sms(alert, recipient, notification)
            elif channel == AlertChannel.PUSH:
                success = await self._send_push(alert, recipient, notification)
            else:
                logger.error(f"Unsupported channel type: {channel}")
                success = False
            
            # Update notification status
            if success:
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = "failed"
                notification.error_message = "Failed to send notification"
            
            notification.last_updated = datetime.utcnow()
            self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending {channel} notification: {e}")
            notification.status = "failed"
            notification.error_message = str(e)
            self.db.commit()
            return False
    
    async def _send_email(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send email notification.
        
        Args:
            alert: Alert to send
            recipient: Email address
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            # Prepare email content
            subject = notification.subject
            body = await self._format_email_body(alert)
            
            # Send email using existing email service
            await self.email_service.send_email(
                to=[recipient],
                subject=subject,
                body=body,
                html_body=await self._format_email_html(alert)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {e}")
            return False
    
    async def _send_slack(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send Slack notification.
        
        Args:
            alert: Alert to send
            recipient: Slack channel or user
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            webhook_url = self._channel_configs["slack"].get("webhook_url")
            if not webhook_url:
                logger.error("Slack webhook URL not configured")
                return False
            
            # Format Slack message
            payload = {
                "channel": recipient,
                "text": notification.subject,
                "attachments": [{
                    "color": self._get_slack_color(alert.severity),
                    "title": alert.title,
                    "text": notification.content,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.upper(), "short": True},
                        {"title": "Type", "value": alert.alert_type.upper(), "short": True},
                        {"title": "Status", "value": alert.status.upper(), "short": True},
                        {"title": "Triggered", "value": alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True}
                    ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "Acknowledge",
                            "style": "primary",
                            "url": f"{getattr(settings, 'BASE_URL', 'http://localhost')}/alerts/{alert.alert_id}/acknowledge"
                        },
                        {
                            "type": "button",
                            "text": "Resolve",
                            "style": "danger",
                            "url": f"{getattr(settings, 'BASE_URL', 'http://localhost')}/alerts/{alert.alert_id}/resolve"
                        }
                    ] if alert.status == "active" else []
                }]
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    async def _send_discord(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send Discord notification.
        
        Args:
            alert: Alert to send
            recipient: Discord webhook URL or channel
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            webhook_url = self._channel_configs["discord"].get("webhook_url")
            if not webhook_url:
                logger.error("Discord webhook URL not configured")
                return False
            
            # Format Discord embed
            embed = {
                "title": alert.title,
                "description": notification.content,
                "color": self._get_discord_color(alert.severity),
                "timestamp": alert.triggered_at.isoformat(),
                "fields": [
                    {
                        "name": "Severity",
                        "value": alert.severity.upper(),
                        "inline": True
                    },
                    {
                        "name": "Type", 
                        "value": alert.alert_type.upper(),
                        "inline": True
                    },
                    {
                        "name": "Status",
                        "value": alert.status.upper(),
                        "inline": True
                    }
                ]
            }
            
            payload = {
                "embeds": [embed]
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False
    
    async def _send_webhook(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send webhook notification.
        
        Args:
            alert: Alert to send
            recipient: Webhook URL
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            # Prepare webhook payload
            payload = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "type": alert.alert_type,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat(),
                "context": alert.context,
                "labels": alert.labels,
                "runbook_url": alert.runbook_url
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Fernando-AlertSystem/1.0"
            }
            
            timeout = self._channel_configs["webhook"]["timeout"]
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(recipient, json=payload, headers=headers)
                response.raise_for_status()
            
            notification.message_id = response.headers.get("X-Message-ID", "")
            return True
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
    
    async def _send_sms(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send SMS notification.
        
        Args:
            alert: Alert to send
            recipient: Phone number
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            # This would integrate with SMS provider (Twilio, etc.)
            # For now, log the SMS that would be sent
            
            sms_content = f"[{alert.severity.upper()}] {alert.title}\n{notification.content}"
            logger.info(f"SMS to {recipient}: {sms_content}")
            
            # TODO: Integrate with actual SMS provider
            # Example with Twilio:
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # client.messages.create(to=recipient, from_=from_number, body=sms_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            return False
    
    async def _send_push(self, alert: Alert, recipient: str, notification: AlertNotification) -> bool:
        """
        Send push notification.
        
        Args:
            alert: Alert to send
            recipient: Push notification identifier
            notification: Notification record
            
        Returns:
            True if successful
        """
        try:
            # This would integrate with push notification service
            # (Firebase FCM, Apple APNs, etc.)
            
            push_payload = {
                "to": recipient,
                "notification": {
                    "title": alert.title,
                    "body": notification.content,
                    "icon": "ic_alert",
                    "color": self._get_push_color(alert.severity)
                },
                "data": {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "type": alert.alert_type,
                    "url": f"{getattr(settings, 'BASE_URL', 'http://localhost')}/alerts/{alert.alert_id}"
                }
            }
            
            logger.info(f"Push notification to {recipient}: {push_payload}")
            
            # TODO: Integrate with actual push service
            return True
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return False
    
    async def _generate_subject(self, alert: Alert, channel: AlertChannel) -> str:
        """
        Generate notification subject based on channel and alert.
        
        Args:
            alert: Alert to generate subject for
            channel: Notification channel
            
        Returns:
            Subject line
        """
        severity_prefix = f"[{alert.severity.upper()}]"
        
        if channel in [AlertChannel.SLACK, AlertChannel.DISCORD]:
            return f"{severity_prefix} {alert.title}"
        elif channel == AlertChannel.EMAIL:
            return f"{severity_prefix} Alert: {alert.title}"
        else:
            return alert.title
    
    async def _generate_content(self, alert: Alert, channel: AlertChannel) -> str:
        """
        Generate notification content based on channel.
        
        Args:
            alert: Alert to generate content for
            channel: Notification channel
            
        Returns:
            Notification content
        """
        base_content = f"{alert.message}\n\nTriggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        if alert.context:
            context_str = "\n".join([f"{k}: {v}" for k, v in alert.context.items()])
            base_content += f"\n\nContext:\n{context_str}"
        
        if alert.runbook_url:
            base_content += f"\n\nRunbook: {alert.runbook_url}"
        
        return base_content
    
    async def _format_email_body(self, alert: Alert) -> str:
        """
        Format alert content for email body.
        
        Args:
            alert: Alert to format
            
        Returns:
            Email body text
        """
        body = f"""
Alert: {alert.title}

Severity: {alert.severity.upper()}
Type: {alert.alert_type.upper()}
Status: {alert.status.upper()}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Description:
{alert.description or alert.message}

{f'Context: {json.dumps(alert.context, indent=2)}' if alert.context else ''}

{f'Runbook: {alert.runbook_url}' if alert.runbook_url else ''}

---
This alert was generated by the Fernando Alert System.
        """.strip()
        
        return body
    
    async def _format_email_html(self, alert: Alert) -> str:
        """
        Format alert content for email HTML.
        
        Args:
            alert: Alert to format
            
        Returns:
            Email HTML content
        """
        severity_color = {
            "critical": "#dc3545",
            "high": "#fd7e14", 
            "medium": "#ffc107",
            "low": "#17a2b8",
            "info": "#6c757d"
        }.get(alert.severity, "#6c757d")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ margin-top: 20px; }}
                .field {{ margin-bottom: 10px; }}
                .label {{ font-weight: bold; }}
                .context {{ background-color: #f8f9fa; padding: 10px; border-radius: 5px; }}
                .runbook {{ margin-top: 20px; padding: 10px; background-color: #e9ecef; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Alert: {alert.title}</h2>
            </div>
            <div class="content">
                <div class="field">
                    <span class="label">Severity:</span> {alert.severity.upper()}
                </div>
                <div class="field">
                    <span class="label">Type:</span> {alert.alert_type.upper()}
                </div>
                <div class="field">
                    <span class="label">Status:</span> {alert.status.upper()}
                </div>
                <div class="field">
                    <span class="label">Triggered:</span> {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
                </div>
                <div class="field">
                    <span class="label">Description:</span><br>
                    {alert.description or alert.message}
                </div>
                {f'<div class="context"><div class="label">Context:</div><pre>{json.dumps(alert.context, indent=2)}</pre></div>' if alert.context else ''}
                {f'<div class="runbook"><a href="{alert.runbook_url}">View Runbook</a></div>' if alert.runbook_url else ''}
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_slack_color(self, severity: str) -> str:
        """
        Get Slack color for alert severity.
        
        Args:
            severity: Alert severity
            
        Returns:
            Slack color hex code
        """
        colors = {
            "critical": "danger",
            "high": "warning",
            "medium": "#ff9800",
            "low": "#2196f3",
            "info": "#9e9e9e"
        }
        return colors.get(severity, "#9e9e9e")
    
    def _get_discord_color(self, severity: str) -> int:
        """
        Get Discord color for alert severity.
        
        Args:
            severity: Alert severity
            
        Returns:
            Discord color integer
        """
        colors = {
            "critical": 0xFF0000,  # Red
            "high": 0xFF6600,      # Orange
            "medium": 0xFFFF00,    # Yellow
            "low": 0x00FF00,       # Green
            "info": 0x808080       # Gray
        }
        return colors.get(severity, 0x808080)
    
    def _get_push_color(self, severity: str) -> str:
        """
        Get push notification color for alert severity.
        
        Args:
            severity: Alert severity
            
        Returns:
            Color hex code
        """
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107", 
            "low": "#17a2b8",
            "info": "#6c757d"
        }
        return colors.get(severity, "#6c757d")
    
    async def get_notification_summary(self, alert_id: str) -> Dict[str, Any]:
        """
        Get notification summary for an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Notification summary
        """
        notifications = self.db.query(AlertNotification).filter(
            AlertNotification.alert_id == alert_id
        ).all()
        
        summary = {
            "total_count": len(notifications),
            "by_channel": {},
            "by_status": {},
            "last_sent": None
        }
        
        for notification in notifications:
            # Count by channel
            channel = notification.channel.value
            summary["by_channel"][channel] = summary["by_channel"].get(channel, 0) + 1
            
            # Count by status
            status = notification.status
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Track last sent time
            if notification.sent_at and (not summary["last_sent"] or notification.sent_at > summary["last_sent"]):
                summary["last_sent"] = notification.sent_at
        
        return summary
    
    async def retry_failed_notifications(self, max_retries: int = 3) -> int:
        """
        Retry failed notifications.
        
        Args:
            max_retries: Maximum retry attempts
            
        Returns:
            Number of notifications retried
        """
        failed_notifications = self.db.query(AlertNotification).filter(
            and_(
                AlertNotification.status == "failed",
                AlertNotification.retry_count < max_retries
            )
        ).all()
        
        retried_count = 0
        for notification in failed_notifications:
            try:
                alert = self.db.query(Alert).filter(Alert.alert_id == notification.alert_id).first()
                if alert:
                    success = await self._send_single_notification(
                        alert,
                        notification.channel,
                        notification.recipient
                    )
                    
                    if success:
                        notification.retry_count += 1
                        retried_count += 1
                    
            except Exception as e:
                logger.error(f"Error retrying notification {notification.notification_id}: {e}")
        
        self.db.commit()
        return retried_count
    
    def validate_channel_configuration(self, channel: AlertChannel) -> Dict[str, Any]:
        """
        Validate channel configuration.
        
        Args:
            channel: Channel to validate
            
        Returns:
            Validation results
        """
        config = self._channel_configs.get(channel.value, {})
        validation = {"valid": True, "errors": [], "warnings": []}
        
        if channel == AlertChannel.SLACK:
            if not config.get("webhook_url"):
                validation["errors"].append("Slack webhook URL not configured")
                validation["valid"] = False
        
        elif channel == AlertChannel.DISCORD:
            if not config.get("webhook_url"):
                validation["errors"].append("Discord webhook URL not configured")
                validation["valid"] = False
        
        elif channel == AlertChannel.SMS:
            required_fields = ["account_sid", "auth_token", "from_number"]
            for field in required_fields:
                if not config.get(field):
                    validation["errors"].append(f"SMS {field} not configured")
                    validation["valid"] = False
        
        elif channel == AlertChannel.PUSH:
            if not any([config.get("firebase_key"), config.get("apns_key")]):
                validation["warnings"].append("No push notification keys configured")
        
        return validation