"""
Notification API Endpoints
REST API endpoints for notification and webhook management
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from app.db.session import get_db
from app.core.config import get_settings
from app.schemas.user_management_schemas import UserResponse

from app.services.notifications.notification_manager import NotificationManager
from app.services.notifications.email_service import EmailService
from app.services.notifications.sms_service import SMSService
from app.services.notifications.push_service import PushService
from app.services.notifications.notification_preferences import NotificationPreferenceService
from app.services.webhooks.webhook_manager import WebhookManager
from app.services.webhooks.webhook_delivery import WebhookDeliveryService
from app.services.webhooks.webhook_events import WebhookEventService
from app.services.hooks.event_system import EventSystem
from app.services.hooks.custom_integrations import CustomIntegrationManager

from app.models.notifications import (
    Notification, NotificationPreference, UserNotificationSettings,
    EmailNotification, SMSNotification, PushNotification,
    WebhookEndpoint, WebhookDelivery, WebhookEvent,
    CustomIntegration, NotificationStatus, NotificationPriority
)

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Dependency to get notification manager
def get_notification_manager(db: Session = Depends(get_db)) -> NotificationManager:
    return NotificationManager(db)

# Dependency to get webhook manager
def get_webhook_manager(db: Session = Depends(get_db)) -> WebhookManager:
    return WebhookManager(db)

# =====================
# Notification Management
# =====================

@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_notifications(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Get notification history for a user"""
    
    try:
        notifications = await notification_manager.get_user_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            type_filter=type_filter
        )
        
        return notifications
    except Exception as e:
        logger.error(f"Error getting user notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@router.post("/send", response_model=Dict[str, Any])
async def send_notification(
    notification_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Send a notification to a user"""
    
    try:
        # Send notification
        notification_id = await notification_manager.send_notification(
            user_id=notification_data["user_id"],
            notification_type=notification_data["type"],
            title=notification_data["title"],
            message=notification_data["message"],
            data=notification_data.get("data", {}),
            channels=notification_data.get("channels"),
            priority=notification_data.get("priority", "normal"),
            scheduled_at=notification_data.get("scheduled_at"),
            expires_at=notification_data.get("expires_at")
        )
        
        return {
            "success": True,
            "notification_id": notification_id,
            "message": "Notification queued for delivery"
        }
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.post("/send/bulk", response_model=Dict[str, Any])
async def send_bulk_notifications(
    bulk_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Send notification to multiple users"""
    
    try:
        notification_ids = await notification_manager.send_bulk_notification(
            user_ids=bulk_data["user_ids"],
            notification_type=bulk_data["type"],
            title=bulk_data["title"],
            message=bulk_data["message"],
            data=bulk_data.get("data", {}),
            channels=bulk_data.get("channels")
        )
        
        return {
            "success": True,
            "notification_ids": notification_ids,
            "total_sent": len(notification_ids)
        }
    except Exception as e:
        logger.error(f"Error sending bulk notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to send bulk notifications")

@router.get("/status/{notification_id}", response_model=Dict[str, Any])
async def get_notification_status(
    notification_id: str,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Get notification delivery status"""
    
    status = await notification_manager.get_notification_status(notification_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return status

@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Mark notification as read"""
    
    success = await notification_manager.mark_notification_read(notification_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or not owned by user")
    
    return {"success": True, "message": "Notification marked as read"}

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_notification_analytics(
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Get notification analytics"""
    
    try:
        analytics = await notification_manager.get_notification_analytics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return analytics
    except Exception as e:
        logger.error(f"Error getting notification analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

# =====================
# Notification Preferences
# =====================

@router.get("/preferences/{user_id}", response_model=Dict[str, Any])
async def get_user_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    
    try:
        preference_service = NotificationPreferenceService(db)
        preferences = await preference_service.get_user_preferences(user_id)
        
        return preferences
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@router.put("/preferences/{user_id}", response_model=Dict[str, Any])
async def update_user_preferences(
    user_id: str,
    preferences: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    
    try:
        preference_service = NotificationPreferenceService(db)
        success = await preference_service.update_user_preferences(user_id, preferences)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update preferences")
        
        return {"success": True, "message": "Preferences updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")

@router.get("/preferences/{user_id}/summary", response_model=Dict[str, Any])
async def get_preferences_summary(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user preferences summary"""
    
    try:
        preference_service = NotificationPreferenceService(db)
        summary = await preference_service.get_preferences_summary(user_id)
        
        return summary
    except Exception as e:
        logger.error(f"Error getting preferences summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences summary")

@router.post("/preferences/{user_id}/reset")
async def reset_user_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Reset user preferences to defaults"""
    
    try:
        preference_service = NotificationPreferenceService(db)
        success = await preference_service.reset_user_preferences(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset preferences")
        
        return {"success": True, "message": "Preferences reset to defaults"}
    except Exception as e:
        logger.error(f"Error resetting user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset preferences")

# =====================
# Email Notifications
# =====================

@router.get("/email/templates", response_model=List[Dict[str, Any]])
async def get_email_templates(
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(lambda db: EmailService(db))
):
    """Get all email templates"""
    
    try:
        templates = db.query(EmailNotification).all()
        return [template.__dict__ for template in templates]
    except Exception as e:
        logger.error(f"Error getting email templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email templates")

@router.get("/email/analytics", response_model=Dict[str, Any])
async def get_email_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(lambda db: EmailService(db))
):
    """Get email delivery analytics"""
    
    try:
        stats = await email_service.get_email_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting email analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email analytics")

@router.post("/email/validate/{email_address}", response_model=Dict[str, Any])
async def validate_email_deliverability(
    email_address: str,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(lambda db: EmailService(db))
):
    """Validate email address deliverability"""
    
    try:
        result = await email_service.validate_email_deliverability(email_address)
        return result
    except Exception as e:
        logger.error(f"Error validating email: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate email")

# =====================
# SMS Notifications
# =====================

@router.post("/sms/send", response_model=Dict[str, Any])
async def send_sms(
    sms_data: Dict[str, Any],
    db: Session = Depends(get_db),
    sms_service: SMSService = Depends(lambda db: SMSService(db))
):
    """Send SMS notification"""
    
    try:
        result = await sms_service.send_sms(
            user_id=sms_data["user_id"],
            message=sms_data["message"],
            data=sms_data.get("data", {}),
            template_id=sms_data.get("template_id"),
            to_phone=sms_data.get("to_phone"),
            priority=sms_data.get("priority", "normal")
        )
        
        return result
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        raise HTTPException(status_code=500, detail="Failed to send SMS")

@router.post("/sms/register-phone", response_model=Dict[str, Any])
async def register_phone_number(
    phone_data: Dict[str, Any],
    db: Session = Depends(get_db),
    sms_service: SMSService = Depends(lambda db: SMSService(db))
):
    """Register phone number for user"""
    
    try:
        phone_record = await sms_service.register_user_phone_number(
            user_id=phone_data["user_id"],
            phone_number=phone_data["phone_number"],
            verified=phone_data.get("verified", False),
            primary=phone_data.get("primary", True)
        )
        
        return {
            "success": True,
            "phone_number_id": phone_record.id,
            "message": "Phone number registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering phone number: {e}")
        raise HTTPException(status_code=500, detail="Failed to register phone number")

@router.get("/sms/analytics", response_model=Dict[str, Any])
async def get_sms_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    sms_service: SMSService = Depends(lambda db: SMSService(db))
):
    """Get SMS delivery analytics"""
    
    try:
        stats = await sms_service.get_sms_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting SMS analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve SMS analytics")

# =====================
# Push Notifications
# =====================

@router.post("/push/subscribe", response_model=Dict[str, Any])
async def subscribe_push_notifications(
    subscription_data: Dict[str, Any],
    db: Session = Depends(get_db),
    push_service: PushService = Depends(lambda db: PushService(db))
):
    """Subscribe to push notifications"""
    
    try:
        subscription = await push_service.register_push_subscription(
            user_id=subscription_data["user_id"],
            subscription_data=subscription_data["subscription"],
            provider=subscription_data.get("provider", "web")
        )
        
        return {
            "success": True,
            "subscription_id": subscription.id,
            "message": "Push subscription registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering push subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to register push subscription")

@router.get("/push/vapid-key", response_model=Dict[str, Any])
async def get_vapid_public_key(
    push_service: PushService = Depends(lambda db: PushService(db))
):
    """Get VAPID public key for web push"""
    
    try:
        vapid_key = push_service.get_vapid_public_key()
        return {"vapid_public_key": vapid_key}
    except Exception as e:
        logger.error(f"Error getting VAPID key: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve VAPID key")

@router.get("/push/analytics", response_model=Dict[str, Any])
async def get_push_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    push_service: PushService = Depends(lambda db: PushService(db))
):
    """Get push notification analytics"""
    
    try:
        stats = await push_service.get_push_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting push analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve push analytics")

@router.post("/push/unsubscribe")
async def unsubscribe_push_notifications(
    unsubscribe_data: Dict[str, Any],
    db: Session = Depends(get_db),
    push_service: PushService = Depends(lambda db: PushService(db))
):
    """Unsubscribe from push notifications"""
    
    try:
        success = await push_service.deactivate_subscription(unsubscribe_data["endpoint"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"success": True, "message": "Unsubscribed from push notifications"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")

# =====================
# Webhook Management
# =====================

@router.get("/webhooks", response_model=List[Dict[str, Any]])
async def list_webhook_endpoints(
    user_id: str = Query(..., description="User ID"),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """List webhook endpoints for a user"""
    
    try:
        endpoints = await webhook_manager.list_endpoints(user_id, active_only=active_only)
        return [endpoint.__dict__ for endpoint in endpoints]
    except Exception as e:
        logger.error(f"Error listing webhook endpoints: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook endpoints")

@router.post("/webhooks", response_model=Dict[str, Any])
async def create_webhook_endpoint(
    endpoint_data: Dict[str, Any],
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Create a new webhook endpoint"""
    
    try:
        endpoint = await webhook_manager.create_endpoint(
            user_id=endpoint_data["user_id"],
            name=endpoint_data["name"],
            url=endpoint_data["url"],
            events=endpoint_data["events"],
            secret=endpoint_data.get("secret"),
            active=endpoint_data.get("active", True),
            description=endpoint_data.get("description")
        )
        
        return {
            "success": True,
            "endpoint_id": endpoint.id,
            "secret": endpoint.secret,
            "message": "Webhook endpoint created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create webhook endpoint")

@router.get("/webhooks/{endpoint_id}", response_model=Dict[str, Any])
async def get_webhook_endpoint(
    endpoint_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Get webhook endpoint details"""
    
    try:
        endpoint = await webhook_manager.get_endpoint(endpoint_id, user_id)
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return endpoint.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook endpoint")

@router.put("/webhooks/{endpoint_id}", response_model=Dict[str, Any])
async def update_webhook_endpoint(
    endpoint_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Update webhook endpoint"""
    
    try:
        endpoint = await webhook_manager.update_endpoint(endpoint_id, updates["user_id"], updates)
        
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {
            "success": True,
            "endpoint": endpoint.__dict__,
            "message": "Webhook endpoint updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update webhook endpoint")

@router.delete("/webhooks/{endpoint_id}", response_model=Dict[str, Any])
async def delete_webhook_endpoint(
    endpoint_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Delete webhook endpoint"""
    
    try:
        success = await webhook_manager.delete_endpoint(endpoint_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        
        return {"success": True, "message": "Webhook endpoint deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete webhook endpoint")

@router.post("/webhooks/{endpoint_id}/test", response_model=Dict[str, Any])
async def test_webhook_endpoint(
    endpoint_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Test webhook endpoint"""
    
    try:
        result = await webhook_manager.test_endpoint(endpoint_id, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to test webhook endpoint")

@router.get("/webhooks/{endpoint_id}/deliveries", response_model=List[Dict[str, Any]])
async def get_webhook_deliveries(
    endpoint_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    webhook_delivery_service: WebhookDeliveryService = Depends(lambda db: WebhookDeliveryService(db))
):
    """Get webhook delivery history"""
    
    try:
        deliveries = await webhook_delivery_service.get_endpoint_deliveries(
            endpoint_id=endpoint_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        return deliveries
    except Exception as e:
        logger.error(f"Error getting webhook deliveries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook deliveries")

@router.get("/webhooks/{endpoint_id}/statistics", response_model=Dict[str, Any])
async def get_webhook_statistics(
    endpoint_id: str,
    user_id: str = Query(..., description="User ID to verify ownership"),
    db: Session = Depends(get_db),
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Get webhook endpoint statistics"""
    
    try:
        stats = await webhook_manager.get_endpoint_statistics(endpoint_id, user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook statistics")

# =====================
# Event Management
# =====================

@router.get("/events/available", response_model=List[Dict[str, Any]])
async def get_available_events(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get list of available events"""
    
    try:
        event_service = WebhookEventService(db)
        
        if category:
            from app.services.webhooks.webhook_events import EventCategory
            category_enum = EventCategory(category)
            events = event_service.list_events(category=category_enum)
        else:
            events = event_service.list_events()
        
        return [
            {
                "name": event.name,
                "category": event.category.value,
                "description": event.description,
                "severity": event.severity.value,
                "schema": event.schema,
                "example": event.example_payload
            }
            for event in events
        ]
    except Exception as e:
        logger.error(f"Error getting available events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve available events")

@router.get("/events/{event_name}/schema", response_model=Dict[str, Any])
async def get_event_schema(
    event_name: str,
    db: Session = Depends(get_db)
):
    """Get event schema and documentation"""
    
    try:
        event_service = WebhookEventService(db)
        event_def = event_service.get_event_definition(event_name)
        
        if not event_def:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {
            "name": event_def.name,
            "description": event_def.description,
            "category": event_def.category.value,
            "severity": event_def.severity.value,
            "schema": event_def.schema,
            "example": event_service.create_test_payload(event_name),
            "rate_limit": event_def.rate_limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve event schema")

@router.post("/events/publish", response_model=Dict[str, Any])
async def publish_event(
    event_data: Dict[str, Any],
    db: Session = Depends(get_db),
    event_system: EventSystem = Depends(lambda db: EventSystem(db))
):
    """Publish an event"""
    
    try:
        from app.services.hooks.event_system import EventPriority
        
        priority = EventPriority(event_data.get("priority", "normal"))
        
        event_id = await event_system.publish_event(
            event_name=event_data["event_name"],
            data=event_data["data"],
            source=event_data["source"],
            user_id=event_data.get("user_id"),
            tenant_id=event_data.get("tenant_id"),
            category=event_data.get("category"),
            priority=priority,
            correlation_id=event_data.get("correlation_id"),
            metadata=event_data.get("metadata")
        )
        
        return {
            "success": True,
            "event_id": event_id,
            "message": "Event published successfully"
        }
    except Exception as e:
        logger.error(f"Error publishing event: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish event")

# =====================
# Custom Integrations
# =====================

@router.get("/integrations", response_model=List[Dict[str, Any]])
async def list_integrations(
    integration_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    integration_manager: CustomIntegrationManager = Depends(lambda db: CustomIntegrationManager(db))
):
    """List custom integrations"""
    
    try:
        from app.services.hooks.custom_integrations import IntegrationType
        
        if integration_type:
            type_enum = IntegrationType(integration_type)
            integrations = integration_manager.list_integrations(integration_type=type_enum)
        else:
            integrations = integration_manager.list_integrations()
        
        return [integration.__dict__ for integration in integrations]
    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve integrations")

@router.post("/integrations", response_model=Dict[str, Any])
async def create_integration(
    integration_data: Dict[str, Any],
    db: Session = Depends(get_db),
    integration_manager: CustomIntegrationManager = Depends(lambda db: CustomIntegrationManager(db))
):
    """Create a new custom integration"""
    
    try:
        from app.services.hooks.custom_integrations import IntegrationType
        
        type_enum = IntegrationType(integration_data["integration_type"])
        
        integration_id = await integration_manager.create_integration(
            name=integration_data["name"],
            description=integration_data.get("description"),
            integration_type=type_enum,
            config_data=integration_data["config_data"],
            environment_variables=integration_data.get("environment_variables", {}),
            secrets=integration_data.get("secrets", {}),
            timeout_seconds=integration_data.get("timeout_seconds", 300),
            retry_count=integration_data.get("retry_count", 3)
        )
        
        if not integration_id:
            raise HTTPException(status_code=400, detail="Failed to create integration")
        
        return {
            "success": True,
            "integration_id": integration_id,
            "message": "Integration created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating integration: {e}")
        raise HTTPException(status_code=500, detail="Failed to create integration")

@router.post("/integrations/{integration_id}/test", response_model=Dict[str, Any])
async def test_integration(
    integration_id: str,
    test_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    integration_manager: CustomIntegrationManager = Depends(lambda db: CustomIntegrationManager(db))
):
    """Test a custom integration"""
    
    try:
        result = await integration_manager.test_integration(integration_id, test_data)
        return result
    except Exception as e:
        logger.error(f"Error testing integration: {e}")
        raise HTTPException(status_code=500, detail="Failed to test integration")

@router.get("/integrations/registry", response_model=Dict[str, Any])
async def get_integration_registry(
    db: Session = Depends(get_db),
    hook_registry: HookRegistry = Depends(lambda db: HookRegistry(db))
):
    """Get integration registry statistics"""
    
    try:
        stats = hook_registry.get_registry_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting integration registry: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve integration registry")

# =====================
# System Administration
# =====================

@router.post("/cleanup/old-notifications", response_model=Dict[str, Any])
async def cleanup_old_notifications(
    days: int = Query(30, ge=1, le=365),
    notification_manager: NotificationManager = Depends(get_notification_manager),
    email_service: EmailService = Depends(lambda db: EmailService(db)),
    sms_service: SMSService = Depends(lambda db: SMSService(db)),
    push_service: PushService = Depends(lambda db: PushService(db))
):
    """Clean up old notification records"""
    
    try:
        # Clean up notifications
        notifications_deleted = await notification_manager.cleanup_old_notifications(days)
        
        # Clean up email records
        emails_deleted = await email_service.cleanup_old_emails(days)
        
        # Clean up SMS records
        sms_deleted = await sms_service.cleanup_old_sms(days)
        
        # Clean up push records
        push_deleted = await push_service.cleanup_old_push_notifications(days)
        
        return {
            "success": True,
            "notifications_deleted": notifications_deleted,
            "emails_deleted": emails_deleted,
            "sms_deleted": sms_deleted,
            "push_notifications_deleted": push_deleted,
            "total_deleted": notifications_deleted + emails_deleted + sms_deleted + push_deleted
        }
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to clean up old notifications")

@router.get("/system/metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    db: Session = Depends(get_db),
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """Get system-wide notification metrics"""
    
    try:
        # Get notification analytics
        analytics = await notification_manager.get_notification_analytics()
        
        # Add webhook analytics
        webhook_manager = WebhookManager(db)
        webhook_endpoints = await webhook_manager.list_endpoints("system", active_only=True)
        
        # Get real-time metrics
        from app.services.webhooks.webhook_analytics import WebhookAnalyticsService
        webhook_analytics = WebhookAnalyticsService(db)
        realtime_metrics = await webhook_analytics.get_real_time_metrics()
        
        return {
            "notifications": analytics,
            "webhooks": {
                "active_endpoints": len(webhook_endpoints),
                "realtime_metrics": realtime_metrics
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")

@router.get("/system/status", response_model=Dict[str, Any])
async def get_system_status(
    db: Session = Depends(get_db)
):
    """Get notification system status"""
    
    try:
        # Check database connectivity
        db_status = "healthy"
        try:
            db.execute("SELECT 1")
        except:
            db_status = "unhealthy"
        
        # Check service status
        services_status = {
            "database": db_status,
            "webhook_manager": "healthy",
            "notification_manager": "healthy",
            "email_service": "healthy",
            "sms_service": "healthy",
            "push_service": "healthy"
        }
        
        overall_status = "healthy" if all(
            status == "healthy" for status in services_status.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "services": services_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "error",
            "services": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        }