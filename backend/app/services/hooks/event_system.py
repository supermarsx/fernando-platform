"""
Event System
Core event publishing and subscription system
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict

from app.models.notifications import EventHook, EventSubscription
from app.services.hooks.hook_registries import HookRegistry
from app.services.hooks.event_filters import EventFilterService

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class EventStatus(Enum):
    """Event processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Event:
    """Event data structure"""
    id: str
    name: str
    category: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class EventSubscription:
    """Event subscription definition"""
    id: str
    name: str
    event_pattern: str  # Supports wildcards like "document.*"
    callback_function: Callable
    filter_conditions: Optional[Dict[str, Any]] = None
    priority: EventPriority = EventPriority.NORMAL
    max_concurrent: int = 10
    retry_enabled: bool = True
    timeout_seconds: int = 300
    active: bool = True
    created_at: Optional[datetime] = None

class EventSystem:
    """Core event publishing and subscription system"""
    
    def __init__(self, db):
        self.db = db
        self.subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.processing_tasks = []
        self.hook_registry = HookRegistry()
        self.filter_service = EventFilterService()
        
        # Start processing workers
        self._start_processing_workers()
        
        # Register built-in event handlers
        self._register_built_in_handlers()
    
    def _start_processing_workers(self):
        """Start background event processing workers"""
        
        # Start event processing workers
        for i in range(5):  # 5 workers for concurrent processing
            task = asyncio.create_task(self._process_event_queue())
            self.processing_tasks.append(task)
        
        logger.info("Started event system processing workers")
    
    def _register_built_in_handlers(self):
        """Register built-in event handlers"""
        
        # Register webhook handler
        async def webhook_handler(event: Event):
            # Find matching webhook endpoints
            endpoints = await self.hook_registry.find_endpoints_for_event(event.name)
            
            for endpoint in endpoints:
                try:
                    await self._deliver_to_webhook(event, endpoint)
                except Exception as e:
                    logger.error(f"Webhook delivery error: {e}")
        
        self.subscribe("webhook.*", webhook_handler, priority=EventPriority.NORMAL)
        
        # Register notification handler
        async def notification_handler(event: Event):
            try:
                from app.services.notifications.notification_manager import NotificationManager
                notification_manager = NotificationManager(self.db)
                
                # Map event to notification
                notification_type = self._map_event_to_notification_type(event.name)
                
                if notification_type:
                    await notification_manager.send_event_notification(
                        event.user_id or "",  # Get user_id from event data
                        event.name,
                        event.data
                    )
                    
            except Exception as e:
                logger.error(f"Notification delivery error: {e}")
        
        self.subscribe("notification.*", notification_handler, priority=EventPriority.NORMAL)
        
        # Register analytics handler
        async def analytics_handler(event: Event):
            try:
                from app.core.telemetry import telemetry_tracker
                
                # Track event in telemetry
                telemetry_tracker.track_event(
                    event.name,
                    properties={
                        "category": event.category,
                        "source": event.source,
                        "priority": event.priority.value,
                        "user_id": event.user_id
                    },
                    tags=["event", event.category]
                )
                
            except Exception as e:
                logger.error(f"Analytics tracking error: {e}")
        
        self.subscribe("analytics.*", analytics_handler, priority=EventPriority.LOW)
    
    def subscribe(
        self,
        event_pattern: str,
        callback_function: Callable,
        filter_conditions: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        max_concurrent: int = 10,
        retry_enabled: bool = True,
        timeout_seconds: int = 300,
        subscription_name: Optional[str] = None
    ) -> str:
        """Subscribe to events matching a pattern"""
        
        import uuid
        
        subscription_id = str(uuid.uuid4())
        subscription = EventSubscription(
            id=subscription_id,
            name=subscription_name or f"subscription_{subscription_id[:8]}",
            event_pattern=event_pattern,
            callback_function=callback_function,
            filter_conditions=filter_conditions,
            priority=priority,
            max_concurrent=max_concurrent,
            retry_enabled=retry_enabled,
            timeout_seconds=timeout_seconds,
            active=True,
            created_at=datetime.utcnow()
        )
        
        # Store subscription
        self.subscriptions[event_pattern].append(subscription)
        
        # Save to database
        try:
            db_subscription = EventSubscription(
                id=subscription_id,
                name=subscription.name,
                event_pattern=event_pattern,
                callback_function_name=callback_function.__name__ if hasattr(callback_function, '__name__') else str(callback_function),
                filter_conditions=json.dumps(filter_conditions) if filter_conditions else None,
                priority=priority.value,
                max_concurrent=max_concurrent,
                retry_enabled=retry_enabled,
                timeout_seconds=timeout_seconds,
                active=True,
                created_at=datetime.utcnow()
            )
            
            self.db.add(db_subscription)
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Could not save subscription to database: {e}")
        
        logger.info(f"Registered subscription {subscription_id} for pattern {event_pattern}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        
        # Remove from memory
        for pattern, subscriptions in self.subscriptions.items():
            for subscription in subscriptions[:]:  # Use slice to avoid modification during iteration
                if subscription.id == subscription_id:
                    subscriptions.remove(subscription)
                    # Remove from database
                    try:
                        self.db.query(EventSubscription).filter(
                            EventSubscription.id == subscription_id
                        ).delete()
                        self.db.commit()
                    except Exception as e:
                        logger.warning(f"Could not remove subscription from database: {e}")
                    
                    logger.info(f"Unsubscribed {subscription_id} from pattern {pattern}")
                    return True
        
        return False
    
    async def publish_event(
        self,
        event_name: str,
        data: Dict[str, Any],
        source: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publish an event"""
        
        import uuid
        
        # Create event
        event = Event(
            id=str(uuid.uuid4()),
            name=event_name,
            category=category or self._infer_category(event_name),
            data=data,
            source=source,
            timestamp=datetime.utcnow(),
            priority=priority,
            correlation_id=correlation_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=metadata or {}
        )
        
        # Add to queue for processing
        await self.event_queue.put(event)
        
        logger.debug(f"Published event {event_name} with ID {event.id}")
        return event.id
    
    async def publish_batch_events(
        self,
        events: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[str]:
        """Publish multiple events efficiently"""
        
        event_ids = []
        
        # Process in batches
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = []
            for event_data in batch:
                task = asyncio.create_task(self.publish_event(**event_data))
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in batch_results:
                if isinstance(result, str):  # Event ID
                    event_ids.append(result)
                else:
                    logger.error(f"Batch event publishing error: {result}")
        
        return event_ids
    
    async def _process_event_queue(self):
        """Process events from the queue"""
        
        while True:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=30
                )
                
                # Find matching subscriptions
                matching_subscriptions = self._find_matching_subscriptions(event)
                
                if matching_subscriptions:
                    # Process event with subscriptions
                    await self._process_event_with_subscriptions(event, matching_subscriptions)
                else:
                    # No subscribers, log and continue
                    logger.debug(f"No subscribers for event {event.name}")
                
                # Mark queue task as done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                await asyncio.sleep(1)
    
    def _find_matching_subscriptions(self, event: Event) -> List[EventSubscription]:
        """Find subscriptions matching an event"""
        
        matching_subscriptions = []
        
        # Find subscriptions that match the event pattern
        for pattern, subscriptions in self.subscriptions.items():
            if self._pattern_matches(pattern, event.name):
                for subscription in subscriptions:
                    if subscription.active:
                        # Check filter conditions
                        if self.filter_service.matches_conditions(event, subscription.filter_conditions):
                            matching_subscriptions.append(subscription)
        
        # Sort by priority (highest first)
        priority_order = {EventPriority.CRITICAL: 0, EventPriority.HIGH: 1, EventPriority.NORMAL: 2, EventPriority.LOW: 3}
        matching_subscriptions.sort(key=lambda x: priority_order.get(x.priority, 2))
        
        return matching_subscriptions
    
    def _pattern_matches(self, pattern: str, event_name: str) -> bool:
        """Check if event name matches pattern (supports wildcards)"""
        
        import fnmatch
        
        # Convert pattern to regex-like format for fnmatch
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
        
        try:
            import re
            regex = re.compile(f"^{regex_pattern}$")
            return regex.match(event_name) is not None
        except re.error:
            # Fallback to simple fnmatch
            return fnmatch.fnmatch(event_name, pattern)
    
    async def _process_event_with_subscriptions(
        self,
        event: Event,
        subscriptions: List[EventSubscription]
    ):
        """Process event with multiple subscriptions"""
        
        # Group subscriptions by concurrency limits
        groups = []
        current_group = []
        current_concurrent = 0
        
        for subscription in subscriptions:
            if current_concurrent + 1 <= subscription.max_concurrent:
                current_group.append(subscription)
                current_concurrent += 1
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [subscription]
                current_concurrent = 1
        
        if current_group:
            groups.append(current_group)
        
        # Process each group sequentially (but subscribers within group concurrently)
        for group in groups:
            group_tasks = []
            
            for subscription in group:
                task = asyncio.create_task(
                    self._process_subscription(event, subscription)
                )
                group_tasks.append(task)
            
            # Wait for group to complete
            await asyncio.gather(*group_tasks, return_exceptions=True)
    
    async def _process_subscription(self, event: Event, subscription: EventSubscription):
        """Process event with a single subscription"""
        
        try:
            # Execute callback with timeout
            if subscription.timeout_seconds:
                result = await asyncio.wait_for(
                    subscription.callback_function(event),
                    timeout=subscription.timeout_seconds
                )
            else:
                result = await subscription.callback_function(event)
            
            logger.debug(f"Processed event {event.id} with subscription {subscription.id}")
            
        except asyncio.TimeoutError:
            logger.warning(f"Subscription {subscription.id} timed out processing event {event.id}")
        except Exception as e:
            logger.error(f"Subscription {subscription.id} error processing event {event.id}: {e}")
            
            # Retry if enabled
            if subscription.retry_enabled and event.retry_count < event.max_retries:
                event.retry_count += 1
                await asyncio.sleep(2 ** event.retry_count)  # Exponential backoff
                await self.event_queue.put(event)
    
    async def _deliver_to_webhook(self, event: Event, endpoint: Any):
        """Deliver event to webhook endpoint"""
        
        try:
            from app.services.webhooks.webhook_delivery import WebhookDeliveryService
            
            webhook_data = {
                "event": event.name,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "priority": event.priority.value,
                "correlation_id": event.correlation_id
            }
            
            delivery_service = WebhookDeliveryService(self.db)
            await delivery_service.deliver_event(endpoint, webhook_data, event.name)
            
        except Exception as e:
            logger.error(f"Webhook delivery error: {e}")
    
    def _map_event_to_notification_type(self, event_name: str) -> Optional[str]:
        """Map event name to notification type"""
        
        # Map events to notification types
        if event_name.startswith("document."):
            return "document_processing"
        elif event_name.startswith("verification."):
            return "verification"
        elif event_name.startswith("user."):
            return "user"
        elif event_name.startswith("billing."):
            return "billing"
        elif event_name.startswith("security."):
            return "security"
        elif event_name.startswith("system."):
            return "system"
        
        return None
    
    def _infer_category(self, event_name: str) -> str:
        """Infer event category from name"""
        
        if event_name.startswith("document."):
            return "document"
        elif event_name.startswith("verification."):
            return "verification"
        elif event_name.startswith("user."):
            return "user"
        elif event_name.startswith("billing."):
            return "billing"
        elif event_name.startswith("security."):
            return "security"
        elif event_name.startswith("system."):
            return "system"
        else:
            return "general"
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event system statistics"""
        
        # Count subscriptions
        total_subscriptions = sum(len(subs) for subs in self.subscriptions.values())
        active_subscriptions = sum(
            1 for subs in self.subscriptions.values() 
            for sub in subs if sub.active
        )
        
        # Count events by pattern
        event_patterns = {}
        for pattern in self.subscriptions.keys():
            event_patterns[pattern] = len(self.subscriptions[pattern])
        
        # Get queue size
        queue_size = self.event_queue.qsize()
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "subscription_patterns": event_patterns,
            "event_queue_size": queue_size,
            "processing_workers": len(self.processing_tasks)
        }
    
    async def cleanup_old_events(self, days_to_keep: int = 7) -> int:
        """Clean up old event records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # This would clean up any stored event records
        # For now, just log that cleanup was attempted
        logger.info(f"Event cleanup completed for events older than {days_to_keep} days")
        return 0
    
    async def pause_subscription(self, subscription_id: str) -> bool:
        """Pause a subscription temporarily"""
        
        # Find and deactivate subscription
        for pattern, subscriptions in self.subscriptions.items():
            for subscription in subscriptions:
                if subscription.id == subscription_id:
                    subscription.active = False
                    logger.info(f"Paused subscription {subscription_id}")
                    return True
        
        return False
    
    async def resume_subscription(self, subscription_id: str) -> bool:
        """Resume a paused subscription"""
        
        # Find and activate subscription
        for pattern, subscriptions in self.subscriptions.items():
            for subscription in subscriptions:
                if subscription.id == subscription_id:
                    subscription.active = True
                    logger.info(f"Resumed subscription {subscription_id}")
                    return True
        
        return False
    
    async def shutdown(self):
        """Shutdown event system"""
        
        # Cancel processing tasks
        for task in self.processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        logger.info("Event system shutdown complete")