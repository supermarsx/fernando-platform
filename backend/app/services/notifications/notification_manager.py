"""
Notification Manager Service
Central coordination service for all notification types and channels
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.notifications import (
    Notification, 
    NotificationChannel, 
    NotificationPreference,
    NotificationTemplate,
    UserNotificationSettings
)
from app.services.notifications.email_service import EmailService
from app.services.notifications.sms_service import SMSService
from app.services.notifications.push_service import PushService
from app.services.notifications.notification_preferences import NotificationPreferenceService
from app.services.webhooks.webhook_manager import WebhookManager
from app.services.webhooks.webhook_events import WebhookEventService

logger = logging.getLogger(__name__)

class NotificationManager:
    """Central coordination service for all notification types"""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService(db)
        self.sms_service = SMSService(db)
        self.push_service = PushService(db)
        self.preference_service = NotificationPreferenceService(db)
        self.webhook_manager = WebhookManager(db)
        self.webhook_events = WebhookEventService(db)
        
        # Notification queue for async processing
        self.notification_queue = asyncio.Queue(maxsize=1000)
        self.processing_tasks = []
        
        # Start background processing
        self._start_background_processing()
    
    def _start_background_processing(self):
        """Start background notification processing tasks"""
        
        # Start notification processing workers
        for i in range(3):  # 3 worker processes
            task = asyncio.create_task(self._process_notification_queue())
            self.processing_tasks.append(task)
        
        logger.info("Started background notification processing workers")
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None,
        template_id: Optional[str] = None,
        priority: str = "normal",
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Send notification through specified channels"""
        
        notification_id = str(uuid.uuid4())
        
        # Create notification record
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
            status="pending",
            priority=priority,
            created_at=datetime.utcnow(),
            scheduled_at=scheduled_at,
            expires_at=expires_at
        )
        
        self.db.add(notification)
        self.db.commit()
        
        # Get user's notification preferences
        preferences = await self.preference_service.get_user_preferences(user_id)
        
        # Determine channels to use
        if not channels:
            channels = self._determine_default_channels(notification_type, preferences)
        
        # Add to processing queue
        await self.notification_queue.put({
            "notification_id": notification_id,
            "user_id": user_id,
            "channels": channels,
            "preferences": preferences,
            "template_id": template_id,
            "scheduled_at": scheduled_at,
            "expires_at": expires_at
        })
        
        logger.info(f"Queued notification {notification_id} for user {user_id}")
        return notification_id
    
    async def send_bulk_notification(
        self,
        user_ids: List[str],
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> List[str]:
        """Send notification to multiple users"""
        
        notification_ids = []
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = [
                self.send_notification(
                    user_id,
                    notification_type,
                    title,
                    message,
                    data,
                    channels
                )
                for user_id in batch
            ]
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful results
            for result in batch_results:
                if isinstance(result, str):  # Notification ID
                    notification_ids.append(result)
                else:
                    logger.error(f"Bulk notification error: {result}")
        
        return notification_ids
    
    async def send_event_notification(
        self,
        user_id: str,
        event_name: str,
        event_data: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> str:
        """Send notification based on a system event"""
        
        # Map events to notification content
        event_mapping = await self._get_event_notification_mapping(event_name, event_data)
        
        if not event_mapping:
            logger.warning(f"No notification mapping found for event {event_name}")
            return ""
        
        return await self.send_notification(
            user_id=user_id,
            notification_type=event_mapping["type"],
            title=event_mapping["title"],
            message=event_mapping["message"],
            data={**event_data, "event_name": event_name},
            channels=channels
        )
    
    async def _process_notification_queue(self):
        """Process notification queue in background"""
        
        while True:
            try:
                # Get notification from queue with timeout
                queue_item = await asyncio.wait_for(
                    self.notification_queue.get(),
                    timeout=30
                )
                
                # Process notification
                await self._process_notification(queue_item)
                
                # Mark queue task as done
                self.notification_queue.task_done()
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_notification(self, queue_item: Dict[str, Any]):
        """Process a single notification"""
        
        notification_id = queue_item["notification_id"]
        user_id = queue_item["user_id"]
        channels = queue_item["channels"]
        preferences = queue_item["preferences"]
        
        try:
            # Get notification record
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id
            ).first()
            
            if not notification:
                logger.error(f"Notification {notification_id} not found")
                return
            
            # Check if notification is scheduled
            if notification.scheduled_at and notification.scheduled_at > datetime.utcnow():
                # Reschedule for later
                await self.notification_queue.put(queue_item)
                return
            
            # Check if notification has expired
            if notification.expires_at and notification.expires_at <= datetime.utcnow():
                notification.status = "expired"
                self.db.commit()
                return
            
            # Process each channel
            delivery_results = []
            
            for channel in channels:
                # Check user preferences for this channel
                if not self._should_send_to_channel(channel, preferences):
                    logger.debug(f"Skipping channel {channel} for user {user_id} based on preferences")
                    continue
                
                try:
                    result = await self._deliver_via_channel(
                        notification,
                        channel,
                        queue_item.get("template_id")
                    )
                    delivery_results.append({"channel": channel, "result": result})
                    
                except Exception as e:
                    logger.error(f"Error delivering notification via {channel}: {e}")
                    delivery_results.append({"channel": channel, "error": str(e)})
            
            # Update notification status
            successful_deliveries = len([r for r in delivery_results if r.get("result")])
            failed_deliveries = len([r for r in delivery_results if "error" in r])
            
            if successful_deliveries > 0 and failed_deliveries == 0:
                notification.status = "delivered"
            elif successful_deliveries > 0:
                notification.status = "partially_delivered"
            else:
                notification.status = "failed"
            
            notification.delivered_at = datetime.utcnow()
            notification.delivery_results = delivery_results
            self.db.commit()
            
            logger.info(f"Processed notification {notification_id}: {successful_deliveries} successful, {failed_deliveries} failed")
            
        except Exception as e:
            logger.error(f"Error processing notification {notification_id}: {e}")
            
            # Mark as failed
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id
            ).first()
            
            if notification:
                notification.status = "failed"
                notification.error_message = str(e)
                self.db.commit()
    
    async def _deliver_via_channel(
        self,
        notification: Notification,
        channel: str,
        template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deliver notification via specific channel"""
        
        if channel == "email":
            return await self.email_service.send_email(
                notification.user_id,
                notification.title,
                notification.message,
                notification.data,
                template_id
            )
        
        elif channel == "sms":
            return await self.sms_service.send_sms(
                notification.user_id,
                notification.message,
                notification.data,
                template_id
            )
        
        elif channel == "push":
            return await self.push_service.send_push(
                notification.user_id,
                notification.title,
                notification.message,
                notification.data,
                template_id
            )
        
        elif channel == "webhook":
            return await self._deliver_via_webhook(notification)
        
        else:
            raise ValueError(f"Unknown channel: {channel}")
    
    async def _deliver_via_webhook(self, notification: Notification) -> Dict[str, Any]:
        """Deliver notification via webhook"""
        
        # Create webhook event
        webhook_data = {
            "event": f"notification.{notification.type}",
            "data": {
                "notification_id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "priority": notification.priority
            }
        }
        
        # Find endpoints registered for this notification type
        event_name = f"notification.{notification.type}"
        endpoints = await self.webhook_manager.get_endpoints_by_event(event_name)
        
        if not endpoints:
            return {"delivered": False, "reason": "No webhook endpoints registered"}
        
        # Deliver to all endpoints
        from app.services.webhooks.webhook_delivery import WebhookDeliveryService
        delivery_service = WebhookDeliveryService(self.db)
        
        deliveries = await delivery_service.deliver_batch(
            endpoints,
            webhook_data,
            event_name
        )
        
        successful = len([d for d in deliveries if d.status == 'delivered'])
        failed = len([d for d in deliveries if d.status == 'failed'])
        
        return {
            "delivered": True,
            "successful_endpoints": successful,
            "failed_endpoints": failed,
            "total_endpoints": len(endpoints)
        }
    
    def _determine_default_channels(
        self,
        notification_type: str,
        preferences: Dict[str, Any]
    ) -> List[str]:
        """Determine default channels based on notification type and preferences"""
        
        # ============================================================================
    # CREDIT NOTIFICATION METHODS
    # ============================================================================
    
    async def send_credit_alert(
        self,
        user_id: str,
        alert_type: str,
        current_balance: float,
        projected_runout_date: Optional[datetime] = None,
        recommended_amount: Optional[float] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send credit-related alerts to users
        
        Args:
            user_id: User ID
            alert_type: Type of credit alert (low_balance, critical, runout_warning)
            current_balance: Current credit balance
            projected_runout_date: When credits are projected to run out
            recommended_amount: Recommended purchase amount
            channels: Notification channels to use
        
        Returns:
            Delivery status by channel
        """
        channels = channels or ["email", "push"]
        
        # Define alert templates
        alert_templates = {
            "low_balance": {
                "title": "Credit Balance Running Low",
                "message": f"Your credit balance is running low ({current_balance:.0f} credits remaining). Consider purchasing more credits to avoid service interruption.",
                "urgency": "medium"
            },
            "critical": {
                "title": "Critical Credit Balance",
                "message": f"Your credit balance is critically low ({current_balance:.0f} credits). Please purchase credits immediately to continue using LLM services.",
                "urgency": "high"
            },
            "runout_warning": {
                "title": "Credits Will Run Out Soon",
                "message": f"Based on your usage, credits will run out on {projected_runout_date.strftime('%Y-%m-%d')} if no action is taken. Recommended purchase: {recommended_amount:.0f} credits.",
                "urgency": "high"
            }
        }
        
        if alert_type not in alert_templates:
            raise ValueError(f"Unknown alert type: {alert_type}")
        
        template = alert_templates[alert_type]
        
        # Prepare notification data
        notification_data = {
            "alert_type": alert_type,
            "current_balance": current_balance,
            "projected_runout_date": projected_runout_date.isoformat() if projected_runout_date else None,
            "recommended_purchase_amount": recommended_amount,
            "urgency": template["urgency"],
            "credit_purchase_url": "/dashboard/credits/purchase"
        }
        
        # Send notification
        notification_id = await self.send_notification(
            user_id=user_id,
            notification_type="credit_alert",
            title=template["title"],
            message=template["message"],
            data=notification_data,
            channels=channels,
            priority=template["urgency"]
        )
        
        # Log alert sent for tracking
        if notification_id:
            from app.models.user_management import UserActivity
            
            activity = UserActivity(
                user_id=user_id,
                action="credit_alert_sent",
                resource_type="notification",
                resource_id=notification_id,
                details={
                    "alert_type": alert_type,
                    "current_balance": current_balance,
                    "projected_runout_date": projected_runout_date.isoformat() if projected_runout_date else None,
                    "recommended_amount": recommended_amount
                },
                success=True
            )
            self.db.add(activity)
            self.db.commit()
        
        return {"notification_id": notification_id}
    
    async def send_credit_purchase_confirmation(
        self,
        user_id: str,
        purchase_amount: float,
        new_balance: float,
        payment_method: Optional[str] = None,
        channels: Optional[List[str]] = None
    ) -> str:
        """
        Send confirmation when credits are successfully purchased
        
        Args:
            user_id: User ID
            purchase_amount: Amount of credits purchased
            new_balance: New credit balance after purchase
            payment_method: Payment method used
            channels: Notification channels to use
        
        Returns:
            Notification ID
        """
        channels = channels or ["email", "push"]
        
        title = "Credit Purchase Confirmed"
        message = f"Your credit purchase of {purchase_amount:.0f} credits has been completed. New balance: {new_balance:.0f} credits."
        
        if payment_method:
            message += f" Payment method: {payment_method}."
        
        notification_data = {
            "purchase_amount": purchase_amount,
            "new_balance": new_balance,
            "payment_method": payment_method,
            "transaction_date": datetime.utcnow().isoformat()
        }
        
        return await self.send_notification(
            user_id=user_id,
            notification_type="credit_purchase_confirmation",
            title=title,
            message=message,
            data=notification_data,
            channels=channels,
            priority="high"
        )
    
    async def send_credit_usage_report(
        self,
        user_id: str,
        report_type: str,
        period_days: int = 30,
        channels: Optional[List[str]] = None
    ) -> str:
        """
        Send credit usage report to user
        
        Args:
            user_id: User ID
            report_type: Type of report (usage_summary, cost_analysis, forecast)
            period_days: Report period in days
            channels: Notification channels to use
        
        Returns:
            Notification ID
        """
        channels = channels or ["email"]
        
        from app.services.credit_service import CreditService
        from app.services.usage_tracking.usage_analytics import UsageAnalytics
        
        credit_service = CreditService(self.db)
        usage_analytics = UsageAnalytics(self.db)
        
        # Generate report data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        usage_summary = credit_service.get_usage_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        usage_patterns = usage_analytics.analyze_user_behavior(
            user_id=user_id,
            days_back=period_days
        )
        
        # Format report based on type
        if report_type == "usage_summary":
            title = f"Credit Usage Summary - Last {period_days} Days"
            message = f"Total cost: {usage_summary.total_cost:.2f} credits\nTransactions: {usage_summary.total_transactions}\nAvg cost per transaction: {usage_summary.avg_cost_per_transaction:.4f}"
        
        elif report_type == "cost_analysis":
            title = f"Credit Cost Analysis - Last {period_days} Days"
            message = f"Cost breakdown:\n"
            for service, cost in usage_summary.cost_by_service.items():
                message += f"- {service}: {cost:.2f} credits\n"
        
        elif report_type == "forecast":
            title = f"Credit Usage Forecast"
            balance_projection = credit_service.get_balance_projection(
                user_id=user_id,
                days_ahead=30
            )
            message = f"Projected runout date: {balance_projection.projected_runout_date.strftime('%Y-%m-%d') if balance_projection.projected_runout_date else 'Unknown'}\nRecommended purchase: {balance_projection.recommended_purchase_amount:.0f} credits"
        
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        notification_data = {
            "report_type": report_type,
            "period_days": period_days,
            "usage_summary": usage_summary.__dict__ if hasattr(usage_summary, '__dict__') else usage_summary,
            "usage_patterns": usage_patterns,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return await self.send_notification(
            user_id=user_id,
            notification_type="credit_usage_report",
            title=title,
            message=message,
            data=notification_data,
            channels=channels,
            priority="normal"
        )
    
    async def check_and_send_low_balance_alerts(
        self,
        alert_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Check all users for low credit balance and send alerts
        
        Args:
            alert_thresholds: Custom alert thresholds (e.g., {"low": 500, "critical": 100})
        
        Returns:
            Alert processing results
        """
        if not alert_thresholds:
            alert_thresholds = {
                "low": 500.0,
                "critical": 100.0
            }
        
        from app.services.credit_service import CreditService
        credit_service = CreditService(self.db)
        
        # Get credit accounts with low balances
        low_balance_accounts = credit_service.get_low_balance_accounts(
            threshold=alert_thresholds["low"],
            limit=100
        )
        
        users_processed = 0
        alerts_sent = 0
        
        for account in low_balance_accounts:
            try:
                user_id = account.user_id  # Assuming this is the user identifier
                current_balance = account.current_balance
                
                # Determine alert type
                if current_balance <= alert_thresholds["critical"]:
                    alert_type = "critical"
                else:
                    alert_type = "low_balance"
                
                # Check if alert was already sent recently
                recent_alert = self.db.query(UserActivity).filter(
                    UserActivity.user_id == user_id,
                    UserActivity.action == "credit_alert_sent",
                    UserActivity.created_at >= datetime.utcnow() - timedelta(hours=24)
                ).first()
                
                if not recent_alert:
                    # Get usage forecast
                    balance_projection = credit_service.get_balance_projection(
                        user_id=user_id,
                        days_ahead=14
                    )
                    
                    # Send alert
                    alert_result = await self.send_credit_alert(
                        user_id=str(user_id),
                        alert_type=alert_type,
                        current_balance=current_balance,
                        projected_runout_date=balance_projection.projected_runout_date,
                        recommended_amount=balance_projection.recommended_purchase_amount
                    )
                    
                    if alert_result.get("notification_id"):
                        alerts_sent += 1
                
                users_processed += 1
            
            except Exception as e:
                logger.error(f"Error processing credit alert for user {user_id}: {e}")
                continue
        
        return {
            "success": True,
            "users_processed": users_processed,
            "alerts_sent": alerts_sent,
            "alert_thresholds": alert_thresholds,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    # Default channel mapping by type
        default_channels = {
            "document_processing": ["push"],
            "verification": ["email", "push"],
            "billing": ["email", "push"],
            "security": ["email", "sms"],
            "system": ["push"],
            "user": ["email"],
            "credit_alert": ["email", "push"],
            "credit_purchase_confirmation": ["email", "push"],
            "credit_usage_report": ["email"]
        }
        
        channels = default_channels.get(notification_type, ["push"])
        
        # Filter by user preferences
        filtered_channels = []
        for channel in channels:
            if channel in preferences.get("enabled_channels", []):
                filtered_channels.append(channel)
        
        # If no channels enabled, use push as fallback
        if not filtered_channels:
            filtered_channels = ["push"]
        
        return filtered_channels
    
    def _should_send_to_channel(self, channel: str, preferences: Dict[str, Any]) -> bool:
        """Check if user allows notifications via specific channel"""
        
        enabled_channels = preferences.get("enabled_channels", [])
        return channel in enabled_channels
    
    async def _get_event_notification_mapping(
        self,
        event_name: str,
        event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Map system events to notification content"""
        
        # Document processing events
        if event_name == "document.processing.completed":
            return {
                "type": "document_processing",
                "title": "Document Processing Complete",
                "message": f"Document {event_data.get('document_id', '')} processing completed"
            }
        
        elif event_name == "document.processing.failed":
            return {
                "type": "document_processing",
                "title": "Document Processing Failed",
                "message": f"Document {event_data.get('document_id', '')} processing failed: {event_data.get('error_message', '')}"
            }
        
        # Verification events
        elif event_name == "verification.assigned":
            return {
                "type": "verification",
                "title": "Verification Assigned",
                "message": f"New document assigned for verification: {event_data.get('document_id', '')}"
            }
        
        elif event_name == "verification.completed":
            return {
                "type": "verification",
                "title": "Verification Complete",
                "message": f"Verification {event_data.get('verification_id', '')} completed with status: {event_data.get('status', '')}"
            }
        
        # User events
        elif event_name == "user.created":
            return {
                "type": "user",
                "title": "Welcome to Fernando Platform",
                "message": f"Welcome! Your account has been successfully created"
            }
        
        # Billing events
        elif event_name == "billing.payment_failed":
            return {
                "type": "billing",
                "title": "Payment Failed",
                "message": f"Payment failed: {event_data.get('failure_reason', 'Unknown error')}"
            }
        
        # Security events
        elif event_name == "security.login_failure":
            return {
                "type": "security",
                "title": "Login Failed",
                "message": f"Failed login attempt from {event_data.get('ip_address', 'unknown IP')}"
            }
        
        elif event_name == "security.suspicious_activity":
            return {
                "type": "security",
                "title": "Suspicious Activity Detected",
                "message": f"High-risk activity detected: {event_data.get('description', 'Unknown activity')}"
            }
        
        # System events
        elif event_name == "system.status_changed":
            return {
                "type": "system",
                "title": "System Status Changed",
                "message": f"System status changed to {event_data.get('status', 'unknown')}"
            }
        
        return None
    
    async def get_notification_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get notification delivery status"""
        
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if not notification:
            return None
        
        return {
            "id": notification.id,
            "user_id": notification.user_id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "status": notification.status,
            "priority": notification.priority,
            "created_at": notification.created_at,
            "delivered_at": notification.delivered_at,
            "delivery_results": notification.delivery_results,
            "error_message": notification.error_message
        }
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's notification history"""
        
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if status_filter:
            query = query.filter(Notification.status == status_filter)
        
        if type_filter:
            query = query.filter(Notification.type == type_filter)
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [
            {
                "id": notification.id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "status": notification.status,
                "priority": notification.priority,
                "created_at": notification.created_at,
                "delivered_at": notification.delivered_at,
                "read_at": notification.read_at
            }
            for notification in notifications
        ]
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        
        notification = self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if not notification:
            return False
        
        notification.read_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def get_notification_analytics(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification analytics"""
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build query conditions
        conditions = [
            Notification.created_at >= start_date,
            Notification.created_at <= end_date
        ]
        
        if user_id:
            conditions.append(Notification.user_id == user_id)
        
        # Basic counts
        total_notifications = self.db.query(func.count(Notification.id)).filter(
            and_(*conditions)
        ).scalar() or 0
        
        delivered_notifications = self.db.query(func.count(Notification.id)).filter(
            and_(*conditions, Notification.status == 'delivered')
        ).scalar() or 0
        
        failed_notifications = self.db.query(func.count(Notification.id)).filter(
            and_(*conditions, Notification.status == 'failed')
        ).scalar() or 0
        
        read_notifications = self.db.query(func.count(Notification.id)).filter(
            and_(*conditions, Notification.read_at.isnot(None))
        ).scalar() or 0
        
        # Calculate rates
        delivery_rate = (delivered_notifications / total_notifications * 100) if total_notifications > 0 else 0
        read_rate = (read_notifications / delivered_notifications * 100) if delivered_notifications > 0 else 0
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_notifications": total_notifications,
                "delivered_notifications": delivered_notifications,
                "failed_notifications": failed_notifications,
                "read_notifications": read_notifications,
                "delivery_rate": round(delivery_rate, 2),
                "read_rate": round(read_rate, 2)
            }
        }
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30) -> int:
        """Clean up old notification records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old notifications that have been read
        deleted_count = self.db.query(Notification).filter(
            and_(
                Notification.created_at < cutoff_date,
                Notification.read_at.isnot(None)
            )
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count
    
    async def shutdown(self):
        """Gracefully shutdown notification manager"""
        
        # Cancel background tasks
        for task in self.processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        # Shutdown services
        await self.email_service.shutdown()
        await self.sms_service.shutdown()
        await self.push_service.shutdown()
        
        logger.info("Notification manager shutdown complete")