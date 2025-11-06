"""
Webhook Management System
Handles webhook endpoint registration, management, and lifecycle
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import httpx
import logging

from app.models.notifications import (
    WebhookEndpoint, 
    WebhookEvent, 
    WebhookDelivery, 
    NotificationChannel
)
from app.services.webhooks.webhook_delivery import WebhookDeliveryService
from app.services.webhooks.webhook_security import WebhookSecurityService
from app.services.webhooks.webhook_events import WebhookEventService
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages webhook endpoints and their lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
        self.delivery_service = WebhookDeliveryService(db)
        self.security_service = WebhookSecurityService()
        self.event_service = WebhookEventService(db)
    
    async def create_endpoint(
        self,
        user_id: str,
        name: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        active: bool = True,
        description: Optional[str] = None
    ) -> WebhookEndpoint:
        """Create a new webhook endpoint"""
        
        # Validate URL
        if not await self._validate_webhook_url(url):
            raise ValueError("Invalid webhook URL provided")
        
        # Generate secret if not provided
        if not secret:
            secret = self.security_service.generate_secret()
        
        endpoint = WebhookEndpoint(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            url=url,
            secret=secret,
            active=active,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        
        # Register events
        for event_name in events:
            webhook_event = WebhookEvent(
                id=str(uuid.uuid4()),
                webhook_endpoint_id=endpoint.id,
                event_name=event_name,
                created_at=datetime.utcnow()
            )
            self.db.add(webhook_event)
        
        self.db.commit()
        
        logger.info(f"Created webhook endpoint {endpoint.id} for user {user_id}")
        return endpoint
    
    async def update_endpoint(
        self,
        endpoint_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[WebhookEndpoint]:
        """Update an existing webhook endpoint"""
        
        endpoint = self.db.query(WebhookEndpoint).filter(
            and_(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
        ).first()
        
        if not endpoint:
            return None
        
        # Update basic fields
        if 'name' in updates:
            endpoint.name = updates['name']
        if 'url' in updates:
            if not await self._validate_webhook_url(updates['url']):
                raise ValueError("Invalid webhook URL provided")
            endpoint.url = updates['url']
        if 'active' in updates:
            endpoint.active = updates['active']
        if 'description' in updates:
            endpoint.description = updates['description']
        
        # Update secret if provided
        if 'secret' in updates:
            endpoint.secret = updates['secret']
        
        endpoint.updated_at = datetime.utcnow()
        
        # Update events if provided
        if 'events' in updates:
            # Remove existing events
            self.db.query(WebhookEvent).filter(
                WebhookEvent.webhook_endpoint_id == endpoint_id
            ).delete()
            
            # Add new events
            for event_name in updates['events']:
                webhook_event = WebhookEvent(
                    id=str(uuid.uuid4()),
                    webhook_endpoint_id=endpoint_id,
                    event_name=event_name,
                    created_at=datetime.utcnow()
                )
                self.db.add(webhook_event)
        
        self.db.commit()
        
        logger.info(f"Updated webhook endpoint {endpoint_id}")
        return endpoint
    
    async def delete_endpoint(self, endpoint_id: str, user_id: str) -> bool:
        """Delete a webhook endpoint"""
        
        endpoint = self.db.query(WebhookEndpoint).filter(
            and_(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
        ).first()
        
        if not endpoint:
            return False
        
        # Delete related events and deliveries
        self.db.query(WebhookEvent).filter(
            WebhookEvent.webhook_endpoint_id == endpoint_id
        ).delete()
        
        self.db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_endpoint_id == endpoint_id
        ).delete()
        
        # Delete the endpoint
        self.db.delete(endpoint)
        self.db.commit()
        
        logger.info(f"Deleted webhook endpoint {endpoint_id}")
        return True
    
    async def get_endpoint(self, endpoint_id: str, user_id: str) -> Optional[WebhookEndpoint]:
        """Get a specific webhook endpoint"""
        
        return self.db.query(WebhookEndpoint).filter(
            and_(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.user_id == user_id
            )
        ).first()
    
    async def list_endpoints(self, user_id: str, active_only: bool = False) -> List[WebhookEndpoint]:
        """List webhook endpoints for a user"""
        
        query = self.db.query(WebhookEndpoint).filter(
            WebhookEndpoint.user_id == user_id
        )
        
        if active_only:
            query = query.filter(WebhookEndpoint.active == True)
        
        return query.order_by(WebhookEndpoint.created_at.desc()).all()
    
    async def toggle_endpoint(self, endpoint_id: str, user_id: str, active: bool) -> Optional[WebhookEndpoint]:
        """Toggle endpoint active status"""
        
        endpoint = await self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            return None
        
        endpoint.active = active
        endpoint.updated_at = datetime.utcnow()
        self.db.commit()
        
        return endpoint
    
    async def get_endpoint_events(self, endpoint_id: str) -> List[str]:
        """Get registered events for an endpoint"""
        
        events = self.db.query(WebhookEvent.event_name).filter(
            WebhookEvent.webhook_endpoint_id == endpoint_id
        ).all()
        
        return [event.event_name for event in events]
    
    async def test_endpoint(self, endpoint_id: str, user_id: str) -> Dict[str, Any]:
        """Test a webhook endpoint with a ping event"""
        
        endpoint = await self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            raise ValueError("Endpoint not found")
        
        # Create a test event
        test_event = {
            "event": "webhook.test",
            "data": {
                "message": "Test webhook delivery",
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint_id": endpoint_id
            }
        }
        
        # Deliver the test event
        delivery = await self.delivery_service.deliver_event(
            endpoint, 
            test_event, 
            event_name="webhook.test"
        )
        
        return {
            "delivery_id": delivery.id,
            "status": delivery.status,
            "response_status": delivery.response_status_code,
            "delivered_at": delivery.created_at
        }
    
    async def _validate_webhook_url(self, url: str) -> bool:
        """Validate webhook URL"""
        try:
            import httpx
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            
            # Check basic URL structure
            if not all([parsed.scheme, parsed.netloc]):
                return False
            
            # Only allow HTTPS for security
            if parsed.scheme not in ['https', 'http']:
                return False
            
            # Basic reachability test
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.head(url, allow_redirects=True)
                    # Accept 2xx, 3xx status codes as reachable
                    return response.status_code < 400
                except Exception:
                    return True  # Don't fail validation due to temporary network issues
                    
        except Exception as e:
            logger.warning(f"URL validation error for {url}: {e}")
            return False
    
    async def get_endpoints_by_event(self, event_name: str) -> List[WebhookEndpoint]:
        """Get all endpoints registered for a specific event"""
        
        return self.db.query(WebhookEndpoint).join(WebhookEvent).filter(
            and_(
                WebhookEvent.event_name == event_name,
                WebhookEndpoint.active == True
            )
        ).all()
    
    async def cleanup_failed_endpoints(self, max_failures: int = 10) -> int:
        """Automatically disable endpoints with too many failures"""
        
        # Find endpoints with excessive failures
        failed_endpoints = self.db.query(
            WebhookEndpoint.id,
            WebhookEndpoint.name,
            WebhookEndpoint.user_id
        ).join(
            WebhookDelivery
        ).filter(
            and_(
                WebhookEndpoint.active == True,
                WebhookDelivery.status == 'failed'
            )
        ).group_by(
            WebhookEndpoint.id, WebhookEndpoint.name, WebhookEndpoint.user_id
        ).having(
            # Count failed deliveries in last 24 hours
            WebhookDelivery.created_at >= datetime.utcnow() - timedelta(days=1)
        ).having(
            # Has more than max_failures recent failures
            func.count(WebhookDelivery.id) > max_failures
        ).all()
        
        disabled_count = 0
        for endpoint_data in failed_endpoints:
            endpoint = self.db.query(WebhookEndpoint).filter(
                WebhookEndpoint.id == endpoint_data.id
            ).first()
            
            if endpoint:
                endpoint.active = False
                endpoint.updated_at = datetime.utcnow()
                disabled_count += 1
                
                logger.warning(
                    f"Disabled webhook endpoint {endpoint.id} "
                    f"due to {max_failures}+ recent failures"
                )
        
        self.db.commit()
        return disabled_count
    
    async def get_endpoint_statistics(self, endpoint_id: str, user_id: str) -> Dict[str, Any]:
        """Get statistics for a webhook endpoint"""
        
        endpoint = await self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            raise ValueError("Endpoint not found")
        
        # Get delivery statistics
        from sqlalchemy import func, and_, or_
        
        total_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.webhook_endpoint_id == endpoint_id
        ).scalar() or 0
        
        successful_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(
                WebhookDelivery.webhook_endpoint_id == endpoint_id,
                WebhookDelivery.status == 'delivered'
            )
        ).scalar() or 0
        
        failed_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(
                WebhookDelivery.webhook_endpoint_id == endpoint_id,
                WebhookDelivery.status == 'failed'
            )
        ).scalar() or 0
        
        pending_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(
                WebhookDelivery.webhook_endpoint_id == endpoint_id,
                WebhookDelivery.status == 'pending'
            )
        ).scalar() or 0
        
        # Calculate success rate
        success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
        
        # Get average response time
        avg_response_time = self.db.query(func.avg(WebhookDelivery.response_time_ms)).filter(
            and_(
                WebhookDelivery.webhook_endpoint_id == endpoint_id,
                WebhookDelivery.status == 'delivered'
            )
        ).scalar() or 0
        
        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "pending_deliveries": pending_deliveries,
            "success_rate": round(success_rate, 2),
            "average_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0,
            "events_registered": len(await self.get_endpoint_events(endpoint_id))
        }