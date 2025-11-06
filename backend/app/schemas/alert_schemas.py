"""
Alert Schemas for API validation and response models.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class AlertType(str, Enum):
    """Types of alerts"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"
    CUSTOM = "custom"


class AlertChannel(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"


# Base schemas
class AlertBase(BaseModel):
    """Base alert schema"""
    title: str = Field(..., description="Alert title")
    description: Optional[str] = Field(None, description="Alert description")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity")
    alert_type: AlertType = Field(..., description="Alert type")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="Alert labels")
    runbook_url: Optional[str] = Field(None, description="Link to runbook")


class AlertRuleBase(BaseModel):
    """Base alert rule schema"""
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    alert_type: AlertType = Field(..., description="Alert type")
    severity: AlertSeverity = Field(..., description="Alert severity")
    condition: Dict[str, Any] = Field(..., description="Alert condition")
    threshold_config: Optional[Dict[str, Any]] = Field(None, description="Threshold configuration")
    query_config: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    channels: List[AlertChannel] = Field(default_factory=list, description="Notification channels")
    recipients: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="Recipients by channel")
    enabled: bool = Field(default=True, description="Rule enabled status")
    evaluation_frequency: int = Field(default=300, description="Evaluation frequency in seconds")
    sustained_duration: int = Field(default=60, description="Sustained duration in seconds")
    cooldown_period: int = Field(default=300, description="Cooldown period in seconds")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    tags: Optional[List[str]] = Field(default_factory=list, description="Rule tags")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Rule metadata")


# Create schemas
class AlertCreate(AlertBase):
    """Schema for creating alerts"""
    rule_id: Optional[str] = Field(None, description="Associated rule ID")
    metric_value: Optional[float] = Field(None, description="Current metric value")
    threshold_value: Optional[float] = Field(None, description="Threshold value")
    dedup_key: Optional[str] = Field(None, description="Deduplication key")
    source_system: Optional[str] = Field(None, description="Source system")


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating alert rules"""
    pass


# Update schemas
class AlertUpdate(BaseModel):
    """Schema for updating alerts"""
    status: Optional[AlertStatus] = Field(None, description="Alert status")
    title: Optional[str] = Field(None, description="Alert title")
    description: Optional[str] = Field(None, description="Alert description")
    message: Optional[str] = Field(None, description="Alert message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    labels: Optional[Dict[str, str]] = Field(None, description="Alert labels")
    runbook_url: Optional[str] = Field(None, description="Link to runbook")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class AlertRuleUpdate(BaseModel):
    """Schema for updating alert rules"""
    name: Optional[str] = Field(None, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    alert_type: Optional[AlertType] = Field(None, description="Alert type")
    severity: Optional[AlertSeverity] = Field(None, description="Alert severity")
    condition: Optional[Dict[str, Any]] = Field(None, description="Alert condition")
    threshold_config: Optional[Dict[str, Any]] = Field(None, description="Threshold configuration")
    query_config: Optional[Dict[str, Any]] = Field(None, description="Query configuration")
    channels: Optional[List[AlertChannel]] = Field(None, description="Notification channels")
    recipients: Optional[Dict[str, List[str]]] = Field(None, description="Recipients by channel")
    enabled: Optional[bool] = Field(None, description="Rule enabled status")
    evaluation_frequency: Optional[int] = Field(None, description="Evaluation frequency in seconds")
    sustained_duration: Optional[int] = Field(None, description="Sustained duration in seconds")
    cooldown_period: Optional[int] = Field(None, description="Cooldown period in seconds")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    tags: Optional[List[str]] = Field(None, description="Rule tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Rule metadata")


# Response schemas
class AlertResponse(AlertBase):
    """Schema for alert responses"""
    alert_id: str = Field(..., description="Alert ID")
    rule_id: Optional[str] = Field(None, description="Associated rule ID")
    status: AlertStatus = Field(..., description="Alert status")
    triggered_at: datetime = Field(..., description="When alert was triggered")
    acknowledged_at: Optional[datetime] = Field(None, description="When alert was acknowledged")
    resolved_at: Optional[datetime] = Field(None, description="When alert was resolved")
    last_updated: datetime = Field(..., description="Last update time")
    acknowledged_by: Optional[str] = Field(None, description="User who acknowledged")
    resolved_by: Optional[str] = Field(None, description="User who resolved")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    metric_value: Optional[float] = Field(None, description="Current metric value")
    threshold_value: Optional[float] = Field(None, description="Threshold value")
    notifications_sent: Dict[str, Any] = Field(default_factory=dict, description="Notifications sent")
    notification_count: int = Field(default=0, description="Notification count")
    last_notification_sent: Optional[datetime] = Field(None, description="Last notification time")
    escalation_level: int = Field(default=0, description="Escalation level")
    escalated_at: Optional[datetime] = Field(None, description="When escalated")
    dedup_key: Optional[str] = Field(None, description="Deduplication key")
    runbook_url: Optional[str] = Field(None, description="Link to runbook")
    source_system: Optional[str] = Field(None, description="Source system")
    
    class Config:
        from_attributes = True


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule responses"""
    rule_id: str = Field(..., description="Rule ID")
    created_by: Optional[str] = Field(None, description="Created by user ID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    alert_count: Optional[int] = Field(0, description="Number of alerts triggered")
    
    class Config:
        from_attributes = True


# Notification schemas
class AlertAcknowledgment(BaseModel):
    """Schema for acknowledging alerts"""
    note: Optional[str] = Field(None, description="Acknowledgment note")


class AlertResolution(BaseModel):
    """Schema for resolving alerts"""
    resolution_notes: str = Field(..., description="Resolution notes")


# Statistics schemas
class AlertStatistics(BaseModel):
    """Schema for alert statistics"""
    total_alerts: int = Field(..., description="Total alerts")
    active_alerts: int = Field(..., description="Active alerts")
    acknowledged_alerts: int = Field(..., description="Acknowledged alerts")
    resolved_alerts: int = Field(..., description="Resolved alerts")
    critical_alerts: int = Field(..., description="Critical alerts")
    high_alerts: int = Field(..., description="High alerts")
    medium_alerts: int = Field(..., description="Medium alerts")
    low_alerts: int = Field(..., description="Low alerts")
    average_resolution_time: Optional[float] = Field(None, description="Average resolution time in minutes")
    alerts_by_type: Dict[str, int] = Field(default_factory=dict, description="Alerts by type")
    alerts_by_channel: Dict[str, int] = Field(default_factory=dict, description="Alerts by notification channel")


class AlertRuleStatistics(BaseModel):
    """Schema for alert rule statistics"""
    total_rules: int = Field(..., description="Total rules")
    enabled_rules: int = Field(..., description="Enabled rules")
    disabled_rules: int = Field(..., description="Disabled rules")
    rules_by_type: Dict[str, int] = Field(default_factory=dict, description="Rules by type")
    rules_by_severity: Dict[str, int] = Field(default_factory=dict, description="Rules by severity")
    most_triggered_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Most triggered rules")


# Template schemas
class AlertTemplateBase(BaseModel):
    """Base alert template schema"""
    name: str = Field(..., description="Template name")
    channel: AlertChannel = Field(..., description="Notification channel")
    alert_type: Optional[AlertType] = Field(None, description="Alert type")
    severity: Optional[AlertSeverity] = Field(None, description="Alert severity")
    subject_template: Optional[str] = Field(None, description="Subject template")
    body_template: str = Field(..., description="Body template")
    variables: Optional[List[str]] = Field(default_factory=list, description="Template variables")
    description: Optional[str] = Field(None, description="Template description")
    tags: Optional[List[str]] = Field(default_factory=list, description="Template tags")


class AlertTemplateCreate(AlertTemplateBase):
    """Schema for creating alert templates"""
    pass


class AlertTemplateUpdate(BaseModel):
    """Schema for updating alert templates"""
    name: Optional[str] = Field(None, description="Template name")
    channel: Optional[AlertChannel] = Field(None, description="Notification channel")
    alert_type: Optional[AlertType] = Field(None, description="Alert type")
    severity: Optional[AlertSeverity] = Field(None, description="Alert severity")
    subject_template: Optional[str] = Field(None, description="Subject template")
    body_template: Optional[str] = Field(None, description="Body template")
    variables: Optional[List[str]] = Field(None, description="Template variables")
    description: Optional[str] = Field(None, description="Template description")
    tags: Optional[List[str]] = Field(None, description="Template tags")


class AlertTemplateResponse(AlertTemplateBase):
    """Schema for alert template responses"""
    template_id: str = Field(..., description="Template ID")
    template_type: str = Field(..., description="Template type")
    format_type: str = Field(..., description="Format type")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    class Config:
        from_attributes = True


# Bulk operations
class BulkAlertAction(BaseModel):
    """Schema for bulk alert operations"""
    alert_ids: List[str] = Field(..., description="List of alert IDs")
    action: str = Field(..., description="Action to perform: acknowledge, resolve, suppress, escalate")
    notes: Optional[str] = Field(None, description="Notes for the action")


# Search and filter schemas
class AlertFilter(BaseModel):
    """Schema for filtering alerts"""
    status: Optional[List[AlertStatus]] = Field(None, description="Filter by status")
    severity: Optional[List[AlertSeverity]] = Field(None, description="Filter by severity")
    alert_type: Optional[List[AlertType]] = Field(None, description="Filter by type")
    rule_id: Optional[str] = Field(None, description="Filter by rule ID")
    acknowledged_by: Optional[str] = Field(None, description="Filter by acknowledged user")
    resolved_by: Optional[str] = Field(None, description="Filter by resolved user")
    triggered_after: Optional[datetime] = Field(None, description="Filter by trigger time (after)")
    triggered_before: Optional[datetime] = Field(None, description="Filter by trigger time (before)")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class AlertRuleFilter(BaseModel):
    """Schema for filtering alert rules"""
    alert_type: Optional[List[AlertType]] = Field(None, description="Filter by type")
    severity: Optional[List[AlertSeverity]] = Field(None, description="Filter by severity")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")
    created_by: Optional[str] = Field(None, description="Filter by creator")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


# Health check schemas
class AlertSystemHealth(BaseModel):
    """Schema for alerting system health"""
    status: str = Field(..., description="Overall health status")
    last_evaluation: Optional[datetime] = Field(None, description="Last rule evaluation time")
    active_rules: int = Field(..., description="Number of active rules")
    pending_notifications: int = Field(..., description="Number of pending notifications")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System metrics")
    components: Dict[str, str] = Field(default_factory=dict, description="Component health status")