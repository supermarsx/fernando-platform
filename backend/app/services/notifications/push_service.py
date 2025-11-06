"""
Push Notification Service
Handles push notifications for mobile and web platforms
"""

import asyncio
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from app.models.notifications import (
    PushNotification, 
    DeviceToken, 
    PushSubscription,
    PushProvider
)
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class PushConfiguration:
    """Push notification service configuration"""
    service_worker_path: str
    vapid_public_key: str
    vapid_private_key: str
    vapid_subject: str
    default_icon: str
    badge_icon: str
    fcm_server_key: Optional[str] = None
    apns_cert_path: Optional[str] = None
    apns_key_id: Optional[str] = None
    apns_team_id: Optional[str] = None
    enable_web_push: bool = True
    enable_fcm: bool = False
    enable_apns: bool = False

class PushService:
    """Handles push notification delivery and management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = self._load_push_configuration()
        self.subscription_cache = {}  # Simple in-memory cache
        self.push_queue = asyncio.Queue(maxsize=1000)
        self.processing_task = None
        self.start_processing()
    
    def _load_push_configuration(self) -> PushConfiguration:
        """Load push notification service configuration"""
        
        # Generate VAPID keys if not provided
        vapid_public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
        
        if not vapid_public_key or not vapid_private_key:
            vapid_public_key, vapid_private_key = self._generate_vapid_keys()
        
        return PushConfiguration(
            service_worker_path=getattr(settings, 'PUSH_SERVICE_WORKER_PATH', '/static/sw.js'),
            vapid_public_key=vapid_public_key,
            vapid_private_key=vapid_private_key,
            vapid_subject=getattr(settings, 'VAPID_SUBJECT', 'mailto:support@fernandoplatform.com'),
            default_icon=getattr(settings, 'PUSH_DEFAULT_ICON', '/static/icons/icon-192x192.png'),
            badge_icon=getattr(settings, 'PUSH_BADGE_ICON', '/static/icons/badge-72x72.png'),
            fcm_server_key=getattr(settings, 'FCM_SERVER_KEY', None),
            apns_cert_path=getattr(settings, 'APNS_CERT_PATH', None),
            apns_key_id=getattr(settings, 'APNS_KEY_ID', None),
            apns_team_id=getattr(settings, 'APNS_TEAM_ID', None),
            enable_web_push=getattr(settings, 'ENABLE_WEB_PUSH', True),
            enable_fcm=getattr(settings, 'ENABLE_FCM', False),
            enable_apns=getattr(settings, 'ENABLE_APNS', False)
        )
    
    def _generate_vapid_keys(self) -> Tuple[str, str]:
        """Generate VAPID key pair for web push"""
        
        try:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            public_key = private_key.public_key()
            
            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Serialize public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            # Convert to base64 URL-safe
            public_b64 = base64.urlsafe_b64encode(
                public_pem.encode('utf-8')
            ).decode('utf-8').rstrip('=')
            
            logger.info("Generated new VAPID keys for web push")
            
            return public_b64, private_pem
            
        except Exception as e:
            logger.error(f"Error generating VAPID keys: {e}")
            # Return placeholder keys (should be configured in production)
            return "placeholder_public_key", "placeholder_private_key"
    
    def start_processing(self):
        """Start background push notification processing"""
        
        if not self.processing_task:
            self.processing_task = asyncio.create_task(self._process_push_queue())
            logger.info("Started push notification processing")
    
    async def send_push(
        self,
        user_id: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        sound: str = "default",
        badge_count: Optional[int] = None,
        action_buttons: Optional[List[Dict[str, str]]] = None,
        link: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Send push notification to user"""
        
        try:
            # Prepare notification data
            notification_data = {
                "title": title,
                "body": message,
                "icon": icon or self.config.default_icon,
                "badge": badge or self.config.badge_icon,
                "sound": sound,
                "data": data or {},
                "actions": action_buttons or [],
                "link": link,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if badge_count is not None:
                notification_data["badge"] = badge_count
            
            # Get user's push subscriptions
            subscriptions = await self._get_user_push_subscriptions(user_id)
            
            if not subscriptions:
                return {
                    "success": False,
                    "error": "No push subscriptions found for user",
                    "delivered_count": 0
                }
            
            # Create notification records
            notification_records = []
            for subscription in subscriptions:
                record = PushNotification(
                    id=f"push_{user_id}_{int(datetime.utcnow().timestamp())}_{len(notification_records)}",
                    user_id=user_id,
                    device_token_id=subscription.device_token_id,
                    title=title,
                    body=message,
                    data=notification_data["data"],
                    status="pending",
                    created_at=datetime.utcnow(),
                    priority=priority
                )
                self.db.add(record)
                notification_records.append(record)
            
            self.db.commit()
            
            # Send to each subscription
            results = {"success": 0, "failed": 0, "total": len(subscriptions)}
            
            for subscription, record in zip(subscriptions, notification_records):
                try:
                    result = await self._send_push_to_subscription(
                        subscription, notification_data
                    )
                    
                    if result["success"]:
                        record.status = "sent"
                        record.sent_at = datetime.utcnow()
                        record.provider_message_id = result.get("provider_message_id")
                        results["success"] += 1
                    else:
                        record.status = "failed"
                        record.error_message = result["error"]
                        results["failed"] += 1
                    
                except Exception as e:
                    record.status = "failed"
                    record.error_message = str(e)
                    results["failed"] += 1
                    logger.error(f"Error sending push notification: {e}")
            
            self.db.commit()
            
            logger.info(f"Push notification sent: {results['success']} success, {results['failed']} failed")
            return {
                "success": results["failed"] == 0,
                "delivered_count": results["success"],
                "failed_count": results["failed"],
                "total_attempted": results["total"]
            }
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_push_queue(self):
        """Process push notification queue"""
        
        while True:
            try:
                # Get notification from queue with timeout
                notification_data = await asyncio.wait_for(
                    self.push_queue.get(),
                    timeout=30
                )
                
                # Process notification
                result = await self.send_push(**notification_data)
                
                # Mark queue task as done
                self.push_queue.task_done()
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing push queue: {e}")
                await asyncio.sleep(1)
    
    async def _send_push_to_subscription(
        self,
        subscription: PushSubscription,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification to specific subscription"""
        
        if subscription.provider == "web":
            return await self._send_web_push(subscription, notification_data)
        elif subscription.provider == "fcm":
            return await self._send_fcm_push(subscription, notification_data)
        elif subscription.provider == "apns":
            return await self._send_apns_push(subscription, notification_data)
        else:
            return {
                "success": False,
                "error": f"Unknown push provider: {subscription.provider}"
            }
    
    async def _send_web_push(
        self,
        subscription: PushSubscription,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send web push notification using VAPID"""
        
        try:
            import pywebpush
            from webpush import send_notification
            
            # Prepare notification payload
            payload = {
                "title": notification_data["title"],
                "body": notification_data["body"],
                "icon": notification_data["icon"],
                "badge": notification_data["badge"],
                "data": notification_data["data"],
                "actions": notification_data["actions"]
            }
            
            if notification_data.get("link"):
                payload["click_action"] = notification_data["link"]
            
            # Get subscription info from database
            endpoint_info = json.loads(subscription.endpoint_info)
            
            # Send push notification
            result = pywebpush.defer_to_thread(
                send_notification,
                endpoint_info,
                json.dumps(payload),
                vapid_private_key=self.config.vapid_private_key,
                vapid_claims={
                    "aud": subscription.endpoint.split('//')[1].split('/')[0],
                    "sub": self.config.vapid_subject
                }
            )
            
            return {
                "success": True,
                "provider_message_id": f"web_push_{int(datetime.utcnow().timestamp())}",
                "status": "sent"
            }
            
        except ImportError:
            # Fallback to HTTP request if pywebpush not available
            return await self._send_web_push_http(subscription, notification_data)
        except Exception as e:
            return {
                "success": False,
                "error": f"Web push error: {str(e)}"
            }
    
    async def _send_web_push_http(
        self,
        subscription: PushSubscription,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send web push notification via HTTP (fallback)"""
        
        try:
            # This is a simplified implementation
            # In production, you'd use a proper push notification service
            
            headers = {
                "Authorization": f"vapid t={self.config.vapid_public_key},k={self.config.vapid_public_key}",
                "Content-Type": "application/json",
                "TTL": "86400"
            }
            
            payload = {
                "title": notification_data["title"],
                "body": notification_data["body"],
                "icon": notification_data["icon"],
                "badge": notification_data["badge"],
                "data": notification_data["data"]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    subscription.endpoint,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "provider_message_id": f"web_http_{int(datetime.utcnow().timestamp())}",
                        "status": "sent"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP error: {response.status_code} - {response.text}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Web push HTTP error: {str(e)}"
            }
    
    async def _send_fcm_push(
        self,
        subscription: PushSubscription,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification via Firebase Cloud Messaging"""
        
        if not self.config.fcm_server_key:
            return {
                "success": False,
                "error": "FCM server key not configured"
            }
        
        try:
            endpoint_info = json.loads(subscription.endpoint_info)
            device_token = endpoint_info.get("keys", {}).get("p256dh")
            
            if not device_token:
                return {
                    "success": False,
                    "error": "Invalid FCM device token"
                }
            
            # Prepare FCM payload
            payload = {
                "to": device_token,
                "notification": {
                    "title": notification_data["title"],
                    "body": notification_data["body"],
                    "icon": notification_data["icon"],
                    "sound": notification_data.get("sound", "default"),
                    "badge": notification_data.get("badge", 0)
                },
                "data": notification_data["data"]
            }
            
            headers = {
                "Authorization": f"key={self.config.fcm_server_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("success", 0) == 1:
                        return {
                            "success": True,
                            "provider_message_id": result.get("message_id", ""),
                            "status": "sent"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"FCM error: {result.get('results', [{}])[0].get('error', 'Unknown error')}"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"FCM HTTP error: {response.status_code} - {response.text}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"FCM send error: {str(e)}"
            }
    
    async def _send_apns_push(
        self,
        subscription: PushSubscription,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification via Apple Push Notification Service"""
        
        try:
            endpoint_info = json.loads(subscription.endpoint_info)
            device_token = endpoint_info.get("device_token")
            
            if not device_token:
                return {
                    "success": False,
                    "error": "Invalid APNS device token"
                }
            
            # Prepare APNS payload
            payload = {
                "aps": {
                    "alert": {
                        "title": notification_data["title"],
                        "body": notification_data["body"]
                    },
                    "badge": notification_data.get("badge", 1),
                    "sound": notification_data.get("sound", "default"),
                    "content-available": 1
                },
                "data": notification_data["data"]
            }
            
            headers = {
                "apns-id": f"fernando-{int(datetime.utcnow().timestamp())}",
                "apns-push-type": "alert",
                "apns-priority": "10",
                "apns-topic": self.config.apns_team_id or "com.fernandoplatform.app"
            }
            
            # Send to APNS sandbox
            url = "https://api.push-sandbox.push.apple.com/3/device/" + device_token
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_message_id": headers["apns-id"],
                        "status": "sent"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"APNS error: {response.status_code} - {response.text}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"APNS send error: {str(e)}"
            }
    
    async def _get_user_push_subscriptions(self, user_id: str) -> List[PushSubscription]:
        """Get user's push notification subscriptions"""
        
        return self.db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id
        ).all()
    
    async def register_push_subscription(
        self,
        user_id: str,
        subscription_data: Dict[str, Any],
        provider: str = "web"
    ) -> PushSubscription:
        """Register a push subscription for a user"""
        
        try:
            # Generate device token ID
            import uuid
            device_token_id = str(uuid.uuid4())
            
            # Check if subscription already exists
            existing = self.db.query(PushSubscription).filter(
                and_(
                    PushSubscription.user_id == user_id,
                    PushSubscription.endpoint == subscription_data["endpoint"]
                )
            ).first()
            
            if existing:
                # Update existing subscription
                existing.endpoint_info = json.dumps(subscription_data)
                existing.updated_at = datetime.utcnow()
                existing.active = True
                self.db.commit()
                return existing
            
            # Create new subscription
            subscription = PushSubscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider=provider,
                endpoint=subscription_data["endpoint"],
                endpoint_info=json.dumps(subscription_data),
                device_token_id=device_token_id,
                active=True,
                created_at=datetime.utcnow()
            )
            
            self.db.add(subscription)
            self.db.commit()
            
            logger.info(f"Registered push subscription for user {user_id}: {provider}")
            return subscription
            
        except Exception as e:
            logger.error(f"Error registering push subscription: {e}")
            raise
    
    async def send_bulk_push(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, int]:
        """Send push notification to multiple users"""
        
        results = {"success": 0, "failed": 0, "total": len(user_ids)}
        
        # Process users concurrently with limited concurrency
        semaphore = asyncio.Semaphore(10)
        
        async def send_to_user(user_id: str):
            async with semaphore:
                result = await self.send_push(
                    user_id=user_id,
                    title=title,
                    message=message,
                    data=data or {},
                    **kwargs
                )
                return result.get("delivered_count", 0) > 0
        
        # Create tasks for all users
        tasks = [send_to_user(user_id) for user_id in user_ids]
        
        # Wait for all to complete
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results_list:
            if isinstance(result, Exception):
                results["failed"] += 1
            elif result:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    async def get_push_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get push notification statistics"""
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query conditions
        conditions = [
            PushNotification.created_at >= start_date,
            PushNotification.created_at <= end_date
        ]
        
        # Basic counts
        total_push = self.db.query(func.count(PushNotification.id)).filter(
            and_(*conditions)
        ).scalar() or 0
        
        sent_push = self.db.query(func.count(PushNotification.id)).filter(
            and_(*conditions, PushNotification.status == 'sent')
        ).scalar() or 0
        
        failed_push = self.db.query(func.count(PushNotification.id)).filter(
            and_(*conditions, PushNotification.status == 'failed')
        ).scalar() or 0
        
        # Provider usage
        provider_usage = self.db.query(
            PushSubscription.provider,
            func.count(PushSubscription.id).label('count')
        ).filter(
            PushSubscription.active == True
        ).group_by(
            PushSubscription.provider
        ).all()
        
        provider_stats = {usage.provider: usage.count for usage in provider_usage}
        
        # Active subscriptions
        active_subscriptions = self.db.query(func.count(PushSubscription.id)).filter(
            PushSubscription.active == True
        ).scalar() or 0
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_push_notifications": total_push,
            "sent_push_notifications": sent_push,
            "failed_push_notifications": failed_push,
            "success_rate": round((sent_push / total_push * 100), 2) if total_push > 0 else 0,
            "provider_distribution": provider_stats,
            "active_subscriptions": active_subscriptions
        }
    
    async def cleanup_old_push_notifications(self, days_to_keep: int = 30) -> int:
        """Clean up old push notification records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(PushNotification).filter(
            PushNotification.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old push notification records")
        return deleted_count
    
    async def deactivate_subscription(self, endpoint: str) -> bool:
        """Deactivate a push subscription"""
        
        subscription = self.db.query(PushSubscription).filter(
            PushSubscription.endpoint == endpoint
        ).first()
        
        if subscription:
            subscription.active = False
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def get_vapid_public_key(self) -> str:
        """Get VAPID public key for web push registration"""
        return self.config.vapid_public_key
    
    async def shutdown(self):
        """Shutdown push notification service"""
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Push notification service shutdown complete")