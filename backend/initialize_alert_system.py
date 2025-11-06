"""
Alert System Initialization Script

Sets up default alert rules, templates, and configurations for the alerting system.
Run this script after database migration to initialize the alerting system.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.alert import (
    AlertRule, AlertTemplate, AlertType, AlertSeverity, AlertChannel,
    EscalationPolicy, OnCallSchedule
)
from app.models.user import User


logger = logging.getLogger(__name__)


def initialize_alert_system(db: Session) -> None:
    """
    Initialize the alerting system with default configurations.
    
    Args:
        db: Database session
    """
    logger.info("Initializing alert system...")
    
    # Create default templates
    create_default_templates(db)
    
    # Create default alert rules
    create_default_alert_rules(db)
    
    # Create default escalation policies
    create_default_escalation_policies(db)
    
    # Create default on-call schedules
    create_default_oncall_schedules(db)
    
    logger.info("Alert system initialization completed")


def create_default_templates(db: Session) -> None:
    """
    Create default notification templates.
    
    Args:
        db: Database session
    """
    templates = [
        {
            "name": "Critical System Alert",
            "channel": AlertChannel.EMAIL,
            "alert_type": AlertType.SYSTEM,
            "severity": AlertSeverity.CRITICAL,
            "subject_template": "🚨 CRITICAL: {{alert.rule_name}}",
            "body_template": """
🚨 CRITICAL ALERT 🚨

Alert: {{alert.rule_name}}
Severity: {{alert.severity.upper()}}
Type: {{alert.type.upper()}}
Triggered: {{timestamp}}

Description:
{{alert.rule_description}}

Current Value: {{metric_value}}
Threshold: {{threshold_value}}

Context:
{% for key, value in context.items() %}
{{key}}: {{value}}
{% endfor %}

Runbook: {{runbook_url if runbook_url else 'Not available'}}

This is a CRITICAL alert that requires immediate attention.
            """.strip(),
            "template_type": "default",
            "format_type": "html",
            "description": "Template for critical system alerts via email"
        },
        {
            "name": "High System Alert",
            "channel": AlertChannel.EMAIL,
            "alert_type": AlertType.SYSTEM,
            "severity": AlertSeverity.HIGH,
            "subject_template": "⚠️ HIGH: {{alert.rule_name}}",
            "body_template": """
⚠️ HIGH PRIORITY ALERT ⚠️

Alert: {{alert.rule_name}}
Severity: {{alert.severity.upper()}}
Type: {{alert.type.upper()}}
Triggered: {{timestamp}}

Description:
{{alert.rule_description}}

Current Value: {{metric_value}}
Threshold: {{threshold_value}}

Please investigate this high priority alert.

Runbook: {{runbook_url if runbook_url else 'Not available'}}
            """.strip(),
            "template_type": "default",
            "format_type": "html",
            "description": "Template for high priority system alerts via email"
        },
        {
            "name": "System Alert - Slack",
            "channel": AlertChannel.SLACK,
            "alert_type": AlertType.SYSTEM,
            "severity": AlertSeverity.MEDIUM,
            "subject_template": "{{alert.rule_name}}",
            "body_template": """
*Alert:* {{alert.rule_name}}
*Severity:* {{alert.severity.upper()}}
*Type:* {{alert.type.upper()}}
*Time:* {{timestamp}}

{{alert.rule_description}}

Current: {{metric_value}} | Threshold: {{threshold_value}}

{% if runbook_url %}Runbook: {{runbook_url}}{% endif %}
            """.strip(),
            "template_type": "default",
            "format_type": "markdown",
            "description": "Template for system alerts via Slack"
        },
        {
            "name": "Application Error Alert",
            "channel": AlertChannel.SLACK,
            "alert_type": AlertType.APPLICATION,
            "severity": AlertSeverity.HIGH,
            "subject_template": "🐛 Application Error: {{alert.rule_name}}",
            "body_template": """
🐛 APPLICATION ERROR

*Alert:* {{alert.rule_name}}
*Error Rate:* {{metric_value}}%
*Threshold:* {{threshold_value}}%
*Time:* {{timestamp}}

{{alert.rule_description}}

This alert indicates elevated error rates in the application.
Please check the application logs and investigate the root cause.

{% if runbook_url %}Runbook: {{runbook_url}}{% endif %}
            """.strip(),
            "template_type": "default",
            "format_type": "markdown",
            "description": "Template for application error alerts"
        },
        {
            "name": "Business Metric Alert",
            "channel": AlertChannel.EMAIL,
            "alert_type": AlertType.BUSINESS,
            "severity": AlertSeverity.MEDIUM,
            "subject_template": "📊 Business Alert: {{alert.rule_name}}",
            "body_template": """
📊 BUSINESS METRIC ALERT

Alert: {{alert.rule_name}}
Metric: {{metric_name}}
Current Value: {{metric_value}}
Expected Range: {{threshold_value}}

Time: {{timestamp}}

{{alert.rule_description}}

This alert indicates a business metric has deviated from expected ranges.
Please review the business impact and take appropriate action.

{% if runbook_url %}Runbook: {{runbook_url}}{% endif %}
            """.strip(),
            "template_type": "default",
            "format_type": "html",
            "description": "Template for business metric alerts"
        },
        {
            "name": "Security Alert",
            "channel": AlertChannel.SLACK,
            "alert_type": AlertType.SECURITY,
            "severity": AlertSeverity.HIGH,
            "subject_template": "🔒 SECURITY ALERT: {{alert.rule_name}}",
            "body_template": """
🔒 SECURITY ALERT

*Alert:* {{alert.rule_name}}
*Severity:* {{alert.severity.upper()}}
*Type:* {{alert.type.upper()}}
*Time:* {{timestamp}}

{{alert.rule_description}}

This is a security-related alert that requires immediate investigation.
Please review the security logs and take appropriate action.

{% if runbook_url %}Security Runbook: {{runbook_url}}{% endif %}
            """.strip(),
            "template_type": "default",
            "format_type": "markdown",
            "description": "Template for security alerts"
        }
    ]
    
    for template_data in templates:
        # Check if template already exists
        existing = db.query(AlertTemplate).filter(
            AlertTemplate.name == template_data["name"]
        ).first()
        
        if not existing:
            template = AlertTemplate(**template_data)
            db.add(template)
            logger.info(f"Created template: {template_data['name']}")
    
    db.commit()


def create_default_alert_rules(db: Session) -> None:
    """
    Create default alert rules.
    
    Args:
        db: Database session
    """
    rules = [
        {
            "name": "High CPU Usage",
            "description": "Alert when CPU usage exceeds 80% for more than 5 minutes",
            "alert_type": AlertType.SYSTEM,
            "severity": AlertSeverity.HIGH,
            "condition": {
                "type": "threshold",
                "operator": "gt",
                "value": 80.0
            },
            "threshold_config": {
                "critical": 90.0,
                "high": 80.0,
                "warning": 70.0,
                "operator": "gt"
            },
            "query_config": {
                "metric_name": "cpu_usage",
                "data_source": "system",
                "filters": {"host": "*.prod.example.com"},
                "time_window": 300
            },
            "channels": [AlertChannel.SLACK, AlertChannel.EMAIL],
            "recipients": {
                "slack": ["#ops-alerts"],
                "email": ["ops-team@example.com"]
            },
            "enabled": True,
            "evaluation_frequency": 60,
            "sustained_duration": 300,
            "cooldown_period": 600,
            "escalation_rules": {
                "time_based": {"timeouts": {"level_1": 15, "level_2": 30}},
                "acknowledgment_based": {"timeout_minutes": 15},
                "recipients": {"email": ["manager@example.com"]}
            },
            "tags": ["infrastructure", "performance"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/high-cpu-usage",
                "source_system": "prometheus"
            }
        },
        {
            "name": "High Error Rate",
            "description": "Alert when application error rate exceeds 5%",
            "alert_type": AlertType.APPLICATION,
            "severity": AlertSeverity.HIGH,
            "condition": {
                "type": "threshold",
                "operator": "gt",
                "value": 5.0
            },
            "threshold_config": {
                "critical": 15.0,
                "high": 5.0,
                "medium": 2.0,
                "operator": "gt"
            },
            "query_config": {
                "metric_name": "error_rate",
                "data_source": "application",
                "filters": {"service": "document_processor"},
                "time_window": 300
            },
            "channels": [AlertChannel.SLACK],
            "recipients": {
                "slack": ["#dev-alerts"]
            },
            "enabled": True,
            "evaluation_frequency": 120,
            "sustained_duration": 180,
            "cooldown_period": 900,
            "tags": ["application", "errors"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/high-error-rate",
                "source_system": "application_metrics"
            }
        },
        {
            "name": "Low Revenue",
            "description": "Alert when hourly revenue drops below $100",
            "alert_type": AlertType.BUSINESS,
            "severity": AlertSeverity.MEDIUM,
            "condition": {
                "type": "threshold",
                "operator": "lt",
                "value": 100.0
            },
            "threshold_config": {
                "critical": 50.0,
                "high": 75.0,
                "medium": 100.0,
                "operator": "lt"
            },
            "query_config": {
                "metric_name": "revenue_per_hour",
                "data_source": "business",
                "time_window": 3600
            },
            "channels": [AlertChannel.EMAIL],
            "recipients": {
                "email": ["business-team@example.com"]
            },
            "enabled": True,
            "evaluation_frequency": 3600,
            "sustained_duration": 1800,
            "cooldown_period": 7200,
            "tags": ["business", "revenue"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/low-revenue",
                "source_system": "billing_system"
            }
        },
        {
            "name": "Failed Login Attempts",
            "description": "Alert on suspicious login activity",
            "alert_type": AlertType.SECURITY,
            "severity": AlertSeverity.HIGH,
            "condition": {
                "type": "threshold",
                "operator": "gt",
                "value": 10
            },
            "threshold_config": {
                "critical": 50,
                "high": 10,
                "operator": "gt"
            },
            "query_config": {
                "metric_name": "failed_logins_per_hour",
                "data_source": "security",
                "time_window": 3600
            },
            "channels": [AlertChannel.SLACK, AlertChannel.EMAIL],
            "recipients": {
                "slack": ["#security-alerts"],
                "email": ["security-team@example.com"]
            },
            "enabled": True,
            "evaluation_frequency": 300,
            "sustained_duration": 60,
            "cooldown_period": 1800,
            "escalation_rules": {
                "severity_based": {
                    "auto_escalate_severities": ["critical"]
                },
                "recipients": {
                    "email": ["security-manager@example.com"]
                }
            },
            "tags": ["security", "authentication"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/suspicious-login",
                "source_system": "security_monitor"
            }
        },
        {
            "name": "Disk Space Low",
            "description": "Alert when disk usage exceeds 85%",
            "alert_type": AlertType.SYSTEM,
            "severity": AlertSeverity.MEDIUM,
            "condition": {
                "type": "threshold",
                "operator": "gt",
                "value": 85.0
            },
            "threshold_config": {
                "critical": 95.0,
                "high": 85.0,
                "medium": 75.0,
                "operator": "gt"
            },
            "query_config": {
                "metric_name": "disk_usage",
                "data_source": "system",
                "filters": {"device": "/dev/sda1"},
                "time_window": 300
            },
            "channels": [AlertChannel.SLACK],
            "recipients": {
                "slack": ["#ops-alerts"]
            },
            "enabled": True,
            "evaluation_frequency": 300,
            "sustained_duration": 600,
            "cooldown_period": 3600,
            "tags": ["infrastructure", "storage"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/disk-space",
                "source_system": "system_monitor"
            }
        },
        {
            "name": "API Response Time",
            "description": "Alert when API response time exceeds 2 seconds",
            "alert_type": AlertType.APPLICATION,
            "severity": AlertSeverity.MEDIUM,
            "condition": {
                "type": "threshold",
                "operator": "gt",
                "value": 2.0
            },
            "threshold_config": {
                "critical": 5.0,
                "high": 3.0,
                "medium": 2.0,
                "operator": "gt"
            },
            "query_config": {
                "metric_name": "response_time",
                "data_source": "application",
                "filters": {"endpoint": "/api/*"},
                "time_window": 300
            },
            "channels": [AlertChannel.SLACK],
            "recipients": {
                "slack": ["#dev-alerts"]
            },
            "enabled": True,
            "evaluation_frequency": 60,
            "sustained_duration": 120,
            "cooldown_period": 600,
            "tags": ["application", "performance"],
            "metadata": {
                "runbook_url": "https://wiki.example.com/runbooks/slow-api",
                "source_system": "apm"
            }
        }
    ]
    
    for rule_data in rules:
        # Check if rule already exists
        existing = db.query(AlertRule).filter(
            AlertRule.name == rule_data["name"]
        ).first()
        
        if not existing:
            # Convert enum values to actual enum instances
            rule_data["alert_type"] = AlertType(rule_data["alert_type"])
            rule_data["severity"] = AlertSeverity(rule_data["severity"])
            rule_data["channels"] = [AlertChannel(channel) for channel in rule_data["channels"]]
            
            rule = AlertRule(**rule_data)
            db.add(rule)
            logger.info(f"Created rule: {rule_data['name']}")
    
    db.commit()


def create_default_escalation_policies(db: Session) -> None:
    """
    Create default escalation policies.
    
    Args:
        db: Database session
    """
    policies = [
        {
            "name": "Standard Escalation",
            "description": "Standard escalation policy for most alerts",
            "escalation_levels": [
                {
                    "level": 1,
                    "delay_minutes": 15,
                    "actions": ["notify_team", "page_oncall"],
                    "channels": ["slack", "email"]
                },
                {
                    "level": 2,
                    "delay_minutes": 30,
                    "actions": ["notify_manager", "escalate_channel"],
                    "channels": ["email", "sms"]
                },
                {
                    "level": 3,
                    "delay_minutes": 60,
                    "actions": ["create_incident", "page_management"],
                    "channels": ["email", "sms", "phone"]
                }
            ],
            "escalation_rules": {
                "timeouts": {"level_1": 15, "level_2": 30, "level_3": 60},
                "max_escalation_level": 3
            },
            "enabled": True,
            "auto_resolution": False
        },
        {
            "name": "Critical Alert Escalation",
            "description": "Rapid escalation for critical alerts",
            "escalation_levels": [
                {
                    "level": 1,
                    "delay_minutes": 5,
                    "actions": ["page_oncall", "notify_team"],
                    "channels": ["sms", "slack"]
                },
                {
                    "level": 2,
                    "delay_minutes": 10,
                    "actions": ["notify_manager", "create_incident"],
                    "channels": ["email", "sms", "phone"]
                }
            ],
            "escalation_rules": {
                "timeouts": {"level_1": 5, "level_2": 10},
                "max_escalation_level": 2
            },
            "enabled": True,
            "auto_resolution": False
        }
    ]
    
    for policy_data in policies:
        existing = db.query(EscalationPolicy).filter(
            EscalationPolicy.name == policy_data["name"]
        ).first()
        
        if not existing:
            policy = EscalationPolicy(**policy_data)
            db.add(policy)
            logger.info(f"Created escalation policy: {policy_data['name']}")
    
    db.commit()


def create_default_oncall_schedules(db: Session) -> None:
    """
    Create default on-call schedules.
    
    Args:
        db: Database session
    """
    schedules = [
        {
            "name": "Primary On-Call",
            "description": "Primary on-call rotation for critical systems",
            "rotation_type": "weekly",
            "participants": [],  # Will be populated with actual user IDs
            "timezone": "UTC",
            "working_hours": {
                "start": "09:00",
                "end": "17:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            "holidays": [],
            "escalation_chain": ["manager@example.com"],
            "active": True
        },
        {
            "name": "Security On-Call",
            "description": "Security team on-call rotation",
            "rotation_type": "daily",
            "participants": [],
            "timezone": "UTC",
            "working_hours": {
                "start": "00:00",
                "end": "23:59",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            },
            "holidays": [],
            "escalation_chain": ["security-manager@example.com"],
            "active": True
        }
    ]
    
    # Get some user IDs to populate schedules (if users exist)
    users = db.query(User).limit(4).all()
    if users:
        schedules[0]["participants"] = [users[0].user_id, users[1].user_id]
        schedules[1]["participants"] = [users[2].user_id, users[3].user_id]
    
    for schedule_data in schedules:
        existing = db.query(OnCallSchedule).filter(
            OnCallSchedule.name == schedule_data["name"]
        ).first()
        
        if not existing:
            schedule = OnCallSchedule(**schedule_data)
            db.add(schedule)
            logger.info(f"Created on-call schedule: {schedule_data['name']}")
    
    db.commit()


def main():
    """Main initialization function."""
    logging.basicConfig(level=logging.INFO)
    
    db = SessionLocal()
    try:
        initialize_alert_system(db)
        print("Alert system initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error initializing alert system: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()