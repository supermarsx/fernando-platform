"""
Database Models for Notifications, Webhooks, and Hooks System
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON, Float, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as sa
import enum
import uuid

Base = declarative_base()

# Enums for better type safety
class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class WebhookStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"

class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

# Notification Models

class Notification(Base):
    """Central notification model"""
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default={})
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL, index=True)
    
    # Delivery tracking
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Delivery results
    delivery_results = Column(JSON, default=[])
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, status={self.status})>"

class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = "notification_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    notification_type = Column(String, nullable=False, index=True)
    
    # Preference settings
    enabled = Column(Boolean, default=True)
    channels = Column(JSON, default=[])  # List of enabled channels
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    frequency = Column(String, default="immediate")  # immediate, hourly, daily
    quiet_hours = Column(JSON, default={})
    conditions = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_notification_preferences_user_type', 'user_id', 'notification_type', unique=True),
    )
    
    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id}, type={self.notification_type}, enabled={self.enabled})>"

class UserNotificationSettings(Base):
    """Global user notification settings"""
    __tablename__ = "user_notification_settings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, unique=True, index=True)
    
    # Global settings
    enabled_channels = Column(JSON, default=["push"])  # List of enabled channels
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")
    do_not_disturb = Column(Boolean, default=False)
    notification_sound = Column(Boolean, default=True)
    notification_badge = Column(Boolean, default=True)
    notification_history_days = Column(Integer, default=30)
    
    # Email settings
    email_frequency = Column(String, default="immediate")  # immediate, digest, never
    email_enabled = Column(Boolean, default=True)
    
    # SMS settings
    sms_enabled = Column(Boolean, default=False)
    sms_frequency = Column(String, default="immediate")
    
    # Push notification settings
    push_enabled = Column(Boolean, default=True)
    push_frequency = Column(String, default="immediate")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserNotificationSettings(user_id={self.user_id}, enabled_channels={self.enabled_channels})>"

# Email Models

class EmailNotification(Base):
    """Email notification delivery tracking"""
    __tablename__ = "email_notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    to_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    
    # Template information
    template_id = Column(String, nullable=True)
    template_variables = Column(JSON, default={})
    
    # Delivery tracking
    status = Column(String, default="pending", index=True)  # pending, sent, failed, bounced
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    
    # Provider information
    provider = Column(String, default="smtp")
    provider_message_id = Column(String, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Analytics
    opens = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    last_opened_at = Column(DateTime, nullable=True)
    last_clicked_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<EmailNotification(id={self.id}, user_id={self.user_id}, to_email={self.to_email}, status={self.status})>"

class EmailTemplate(Base):
    """Email template management"""
    __tablename__ = "email_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Template content
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    
    # Template configuration
    variables = Column(JSON, default=[])
    category = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EmailTemplate(name={self.name}, category={self.category}, active={self.active})>"

# SMS Models

class SMSNotification(Base):
    """SMS notification delivery tracking"""
    __tablename__ = "sms_notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    to_phone = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Template information
    template_id = Column(String, nullable=True)
    template_variables = Column(JSON, default={})
    
    # Delivery tracking
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Provider information
    provider = Column(String, default="twilio")
    provider_message_id = Column(String, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Message details
    character_count = Column(Integer, default=0)
    message_parts = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<SMSNotification(id={self.id}, user_id={self.user_id}, to_phone={self.to_phone}, status={self.status})>"

class UserPhoneNumber(Base):
    """User phone number management"""
    __tablename__ = "user_phone_numbers"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    phone_number = Column(String, nullable=False, index=True)
    
    # Phone number details
    country_code = Column(String, nullable=True)
    phone_type = Column(String, default="mobile")  # mobile, landline, fax
    verified = Column(Boolean, default=False)
    primary = Column(Boolean, default=False)
    
    # Verification details
    verification_code = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_phone_numbers_user_primary', 'user_id', 'primary', unique=True),
        Index('idx_user_phone_numbers_phone_verified', 'phone_number', 'verified'),
    )
    
    def __repr__(self):
        return f"<UserPhoneNumber(user_id={self.user_id}, phone_number={self.phone_number}, verified={self.verified})>"

# Push Notification Models

class PushNotification(Base):
    """Push notification delivery tracking"""
    __tablename__ = "push_notifications"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    device_token_id = Column(String, nullable=True, index=True)
    
    # Notification content
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, default={})
    
    # Delivery tracking
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Provider information
    provider = Column(String, default="web")
    provider_message_id = Column(String, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Priority and urgency
    priority = Column(String, default="normal")
    urgent = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<PushNotification(id={self.id}, user_id={self.user_id}, title={self.title}, status={self.status})>"

class PushSubscription(Base):
    """Push notification subscription management"""
    __tablename__ = "push_subscriptions"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Subscription details
    provider = Column(String, nullable=False)  # web, fcm, apns
    endpoint = Column(String, nullable=False, unique=True)
    endpoint_info = Column(JSON, nullable=False)  # Subscription details from client
    
    # Device information
    device_token_id = Column(String, nullable=True, index=True)
    device_type = Column(String, nullable=True)  # desktop, mobile, tablet
    platform = Column(String, nullable=True)  # web, ios, android
    
    # Subscription status
    active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device_token = relationship("DeviceToken", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<PushSubscription(user_id={self.user_id}, provider={self.provider}, active={self.active})>"

class DeviceToken(Base):
    """Device token management"""
    __tablename__ = "device_tokens"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    
    # Device information
    platform = Column(String, nullable=True)  # web, ios, android
    device_type = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Token metadata
    app_version = Column(String, nullable=True)
    sdk_version = Column(String, nullable=True)
    push_type = Column(String, nullable=True)  # alert, background
    
    # Status
    active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("PushSubscription", back_populates="device_token")
    
    def __repr__(self):
        return f"<DeviceToken(user_id={self.user_id}, token={self.token[:10]}..., platform={self.platform})>"

# Webhook Models

class WebhookEndpoint(Base):
    """Webhook endpoint management"""
    __tablename__ = "webhook_endpoints"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=False)  # For signature verification
    
    # Configuration
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    
    # Statistics
    successful_deliveries_count = Column(Integer, default=0)
    failed_deliveries_count = Column(Integer, default=0)
    last_delivery_at = Column(DateTime, nullable=True)
    last_delivery_status = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("WebhookEvent", back_populates="webhook_endpoint", cascade="all, delete-orphan")
    deliveries = relationship("WebhookDelivery", back_populates="webhook_endpoint", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WebhookEndpoint(id={self.id}, user_id={self.user_id}, name={self.name}, url={self.url})>"

class WebhookEvent(Base):
    """Webhook events registration"""
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    webhook_endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_name = Column(String, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    webhook_endpoint = relationship("WebhookEndpoint", back_populates="events")
    
    def __repr__(self):
        return f"<WebhookEvent(webhook_endpoint_id={self.webhook_endpoint_id}, event_name={self.event_name})>"

class WebhookDelivery(Base):
    """Webhook delivery tracking"""
    __tablename__ = "webhook_deliveries"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    webhook_endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_name = Column(String, nullable=False, index=True)
    
    # Delivery status
    status = Column(Enum(WebhookStatus), default=WebhookStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Payload and response
    payload = Column(JSON, nullable=False)
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Response tracking
    webhook_response_id = Column(String, nullable=True)
    
    # Relationships
    webhook_endpoint = relationship("WebhookEndpoint", back_populates="deliveries")
    
    def __repr__(self):
        return f"<WebhookDelivery(id={self.id}, webhook_endpoint_id={self.webhook_endpoint_id}, status={self.status})>"

# Event Hooks Models

class EventHook(Base):
    """Event hook definitions"""
    __tablename__ = "event_hooks"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Hook configuration
    hook_type = Column(String, nullable=False)  # webhook, function, integration, plugin
    category = Column(String, nullable=False)  # document, user, billing, system, security
    event_patterns = Column(JSON, nullable=False)  # List of event patterns
    
    # Parameters
    required_parameters = Column(JSON, default=[])
    optional_parameters = Column(JSON, default=[])
    
    # Examples and documentation
    examples = Column(JSON, default={})
    documentation_url = Column(String, nullable=True)
    
    # Metadata
    version = Column(String, default="1.0.0")
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EventHook(name={self.name}, hook_type={self.hook_type}, category={self.category})>"

class EventSubscription(Base):
    """Event subscription management"""
    __tablename__ = "event_subscriptions"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    event_pattern = Column(String, nullable=False, index=True)
    
    # Subscription configuration
    callback_function_name = Column(String, nullable=False)
    filter_conditions = Column(JSON, nullable=True)
    priority = Column(String, default="normal")  # low, normal, high, critical
    
    # Execution settings
    max_concurrent = Column(Integer, default=10)
    retry_enabled = Column(Boolean, default=True)
    timeout_seconds = Column(Integer, default=300)
    
    # Status
    active = Column(Boolean, default=True)
    
    # Statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EventSubscription(name={self.name}, event_pattern={self.event_pattern}, active={self.active})>"

class HookRegistry(Base):
    """Hook registry for managing available hooks"""
    __tablename__ = "hook_registry"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    hook_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Hook metadata
    hook_type = Column(String, nullable=False)  # webhook, function, integration, plugin
    category = Column(String, nullable=False)
    event_patterns = Column(JSON, nullable=False)
    
    # Parameters
    required_parameters = Column(JSON, default=[])
    optional_parameters = Column(JSON, default=[])
    
    # Examples and documentation
    examples = Column(JSON, default={})
    documentation_url = Column(String, nullable=True)
    
    # Version and status
    version = Column(String, default="1.0.0")
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<HookRegistry(hook_id={self.hook_id}, name={self.name}, hook_type={self.hook_type})>"

# Custom Integration Models

class CustomIntegration(Base):
    """Custom integration management"""
    __tablename__ = "custom_integrations"
    
    id = Column(String, primary_key, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Integration configuration
    integration_type = Column(String, nullable=False)  # webhook, function, plugin, api, task, transformer
    config_data = Column(JSON, nullable=False)
    environment_variables = Column(JSON, default={})
    secrets = Column(JSON, default={})
    
    # Execution settings
    timeout_seconds = Column(Integer, default=300)
    retry_count = Column(Integer, default=3)
    
    # Status and metadata
    status = Column(String, default="active")  # active, inactive, error, maintenance
    version = Column(String, default="1.0.0")
    
    # Statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CustomIntegration(id={self.id}, name={self.name}, integration_type={self.integration_type}, status={self.status})>"

# Relationship Models (to be added to existing User model)

def add_notification_relationships():
    """Add notification relationships to existing User model"""
    
    # This would be added to the existing User model
    # relationships.append(
    #     relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    # )

# Indexes for performance optimization

# Notification indexes
Index('idx_notifications_user_status_created', Notification.user_id, Notification.status, Notification.created_at)
Index('idx_notifications_scheduled', Notification.scheduled_at, Notification.status)
Index('idx_notifications_type_status', Notification.type, Notification.status)

# Webhook indexes
Index('idx_webhook_deliveries_endpoint_status', WebhookDelivery.webhook_endpoint_id, WebhookDelivery.status)
Index('idx_webhook_deliveries_event_status', WebhookDelivery.event_name, WebhookDelivery.status)
Index('idx_webhook_endpoints_user_active', WebhookEndpoint.user_id, WebhookEndpoint.active)

# Integration indexes
Index('idx_custom_integrations_type_status', CustomIntegration.integration_type, CustomIntegration.status)
Index('idx_event_subscriptions_pattern_active', EventSubscription.event_pattern, EventSubscription.active)

# Common utility functions for notifications

def get_notification_summary(user_id: str) -> Dict[str, Any]:
    """Get notification summary for a user"""
    # This would be a query function
    pass

def cleanup_old_notifications(days: int = 30) -> int:
    """Clean up old notification records"""
    # This would be a cleanup function
    pass

def get_webhook_analytics(endpoint_id: str, days: int = 30) -> Dict[str, Any]:
    """Get webhook analytics for an endpoint"""
    # This would be an analytics function
    pass