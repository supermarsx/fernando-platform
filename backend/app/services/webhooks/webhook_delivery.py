"""
Webhook Delivery Service
Handles webhook payload delivery with retry mechanisms and error handling
"""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.notifications import WebhookEndpoint, WebhookDelivery, WebhookEvent
from app.services.webhooks.webhook_security import WebhookSecurityService
from app.services.webhooks.webhook_analytics import WebhookAnalyticsService

logger = logging.getLogger(__name__)

class WebhookDeliveryService:
    """Handles webhook delivery with retry mechanisms"""
    
    def __init__(self, db: Session):
        self.db = db
        self.security_service = WebhookSecurityService()
        self.analytics_service = WebhookAnalyticsService(db)
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
        )
        
        # Retry configuration
        self.max_retries = 5
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff in seconds
    
    async def deliver_event(
        self,
        endpoint: WebhookEndpoint,
        event_data: Dict[str, Any],
        event_name: str,
        retry_count: int = 0
    ) -> WebhookDelivery:
        """Deliver an event to a webhook endpoint"""
        
        # Create delivery record
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_endpoint_id=endpoint.id,
            event_name=event_name,
            status='pending',
            payload=event_data,
            created_at=datetime.utcnow(),
            retry_count=retry_count
        )
        
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        
        try:
            # Generate signed payload
            signed_payload = self.security_service.sign_payload(
                event_data, 
                endpoint.secret
            )
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Fernando-Platform-Webhook/1.0',
                'X-Webhook-Event': event_name,
                'X-Webhook-Delivery': delivery.id,
                'X-Webhook-Signature': self.security_service.generate_signature(
                    signed_payload, 
                    endpoint.secret
                ),
                'X-Webhook-Timestamp': str(int(time.time()))
            }
            
            # Send webhook
            start_time = time.time()
            response = await self.http_client.post(
                endpoint.url,
                json=signed_payload,
                headers=headers,
                follow_redirects=False
            )
            response_time = int((time.time() - start_time) * 1000)
            
            # Update delivery record
            delivery.status = 'delivered' if 200 <= response.status_code < 300 else 'failed'
            delivery.response_status_code = response.status_code
            delivery.response_headers = dict(response.headers)
            delivery.response_body = response.text[:1000] if response.text else None
            delivery.delivered_at = datetime.utcnow()
            delivery.response_time_ms = response_time
            
            # Parse response for additional status info
            if response.text and 'webhook_id' in response.text.lower():
                try:
                    response_data = response.json()
                    delivery.webhook_response_id = response_data.get('webhook_id')
                except:
                    pass
            
            # Record analytics
            await self.analytics_service.record_delivery(delivery)
            
            logger.info(
                f"Webhook delivery {delivery.id} to {endpoint.url} "
                f"completed with status {response.status_code}"
            )
            
        except httpx.TimeoutException:
            delivery.status = 'timeout'
            delivery.error_message = 'Request timeout'
            logger.warning(f"Webhook delivery {delivery.id} timed out")
            
        except httpx.ConnectError as e:
            delivery.status = 'connection_error'
            delivery.error_message = f'Connection failed: {str(e)}'
            logger.warning(f"Webhook delivery {delivery.id} connection failed: {e}")
            
        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = f'Delivery failed: {str(e)}'
            logger.error(f"Webhook delivery {delivery.id} failed: {e}")
        
        self.db.commit()
        
        # Retry logic for failed deliveries
        if delivery.status in ['failed', 'timeout', 'connection_error'] and retry_count < self.max_retries:
            await self._schedule_retry(delivery, retry_count + 1)
        
        return delivery
    
    async def deliver_batch(
        self,
        endpoints: List[WebhookEndpoint],
        event_data: Dict[str, Any],
        event_name: str
    ) -> List[WebhookDelivery]:
        """Deliver an event to multiple endpoints concurrently"""
        
        tasks = [
            self.deliver_event(endpoint, event_data, event_name)
            for endpoint in endpoints
        ]
        
        # Limit concurrency to prevent overwhelming endpoints
        semaphore = asyncio.Semaphore(10)
        
        async def bounded_delivery(endpoint):
            async with semaphore:
                return await self.deliver_event(endpoint, event_data, event_name)
        
        bounded_tasks = [bounded_delivery(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful deliveries
        deliveries = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch delivery error: {result}")
            else:
                deliveries.append(result)
        
        return deliveries
    
    async def _schedule_retry(self, delivery: WebhookDelivery, retry_count: int):
        """Schedule a retry for failed delivery"""
        
        if retry_count <= len(self.retry_delays):
            retry_delay = self.retry_delays[retry_count - 1]
            retry_time = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            # Create retry task (in production, use a task queue like Celery or RQ)
            asyncio.create_task(
                self._delayed_retry(delivery.id, retry_delay)
            )
    
    async def _delayed_retry(self, delivery_id: str, delay_seconds: int):
        """Delayed retry implementation"""
        
        await asyncio.sleep(delay_seconds)
        
        # Get original delivery data
        original_delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not original_delivery:
            return
        
        # Get endpoint
        endpoint = self.db.query(WebhookEndpoint).filter(
            WebhookEndpoint.id == original_delivery.webhook_endpoint_id
        ).first()
        
        if not endpoint:
            return
        
        # Retry delivery
        await self.deliver_event(
            endpoint,
            original_delivery.payload,
            original_delivery.event_name,
            original_delivery.retry_count
        )
    
    async def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get delivery status by ID"""
        
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not delivery:
            return None
        
        return {
            "id": delivery.id,
            "endpoint_id": delivery.webhook_endpoint_id,
            "event_name": delivery.event_name,
            "status": delivery.status,
            "retry_count": delivery.retry_count,
            "created_at": delivery.created_at,
            "delivered_at": delivery.delivered_at,
            "response_status_code": delivery.response_status_code,
            "response_time_ms": delivery.response_time_ms,
            "error_message": delivery.error_message,
            "webhook_response_id": delivery.webhook_response_id
        }
    
    async def get_endpoint_deliveries(
        self,
        endpoint_id: str,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get delivery history for an endpoint"""
        
        query = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_endpoint_id == endpoint_id
        )
        
        if status_filter:
            query = query.filter(WebhookDelivery.status == status_filter)
        
        deliveries = query.order_by(
            WebhookDelivery.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [
            {
                "id": delivery.id,
                "event_name": delivery.event_name,
                "status": delivery.status,
                "retry_count": delivery.retry_count,
                "created_at": delivery.created_at,
                "delivered_at": delivery.delivered_at,
                "response_status_code": delivery.response_status_code,
                "response_time_ms": delivery.response_time_ms,
                "error_message": delivery.error_message
            }
            for delivery in deliveries
        ]
    
    async def resend_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Manually resend a failed delivery"""
        
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not delivery:
            return None
        
        endpoint = self.db.query(WebhookEndpoint).filter(
            WebhookEndpoint.id == delivery.webhook_endpoint_id
        ).first()
        
        if not endpoint:
            return None
        
        return await self.deliver_event(
            endpoint,
            delivery.payload,
            delivery.event_name,
            retry_count=delivery.retry_count + 1
        )
    
    async def cancel_delivery(self, delivery_id: str) -> bool:
        """Cancel a pending delivery"""
        
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not delivery or delivery.status != 'pending':
            return False
        
        delivery.status = 'cancelled'
        delivery.cancelled_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def get_pending_deliveries(self) -> List[WebhookDelivery]:
        """Get all pending deliveries that haven't been processed"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        return self.db.query(WebhookDelivery).filter(
            and_(
                WebhookDelivery.status == 'pending',
                WebhookDelivery.created_at < cutoff_time
            )
        ).all()
    
    async def cleanup_old_deliveries(self, days_to_keep: int = 30) -> int:
        """Clean up old delivery records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        result = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return result
    
    async def validate_endpoint_response(self, endpoint_url: str) -> Dict[str, Any]:
        """Validate an endpoint's ability to receive webhooks"""
        
        test_payload = {
            "event": "webhook.validation",
            "data": {
                "message": "Endpoint validation test",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        try:
            response = await self.http_client.post(
                endpoint_url,
                json=test_payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Fernando-Platform-Webhook/1.0',
                    'X-Webhook-Validation': 'true'
                },
                timeout=10.0
            )
            
            return {
                "valid": 200 <= response.status_code < 400,
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "supports_json": response.headers.get('content-type', '').startswith('application/json'),
                "error": None if 200 <= response.status_code < 400 else f"HTTP {response.status_code}"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "status_code": None,
                "response_time_ms": None,
                "supports_json": False,
                "error": str(e)
            }
    
    async def batch_retry_failed_deliveries(
        self,
        endpoint_id: Optional[str] = None,
        min_age_minutes: int = 10
    ) -> int:
        """Retry failed deliveries for endpoints"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=min_age_minutes)
        
        query = self.db.query(WebhookDelivery).filter(
            and_(
                WebhookDelivery.status.in_(['failed', 'timeout', 'connection_error']),
                WebhookDelivery.created_at < cutoff_time,
                WebhookDelivery.retry_count < self.max_retries
            )
        )
        
        if endpoint_id:
            query = query.filter(WebhookDelivery.webhook_endpoint_id == endpoint_id)
        
        failed_deliveries = query.all()
        
        retried_count = 0
        for delivery in failed_deliveries:
            endpoint = self.db.query(WebhookEndpoint).filter(
                WebhookEndpoint.id == delivery.webhook_endpoint_id
            ).first()
            
            if endpoint and endpoint.active:
                await self.deliver_event(
                    endpoint,
                    delivery.payload,
                    delivery.event_name,
                    retry_count=delivery.retry_count + 1
                )
                retried_count += 1
        
        return retried_count
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()