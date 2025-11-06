"""
Cache Invalidation System

Smart cache invalidation strategies for proxy responses:
- Pattern-based invalidation
- Tag-based invalidation
- Time-based invalidation
- Event-driven invalidation
- Intelligent cache cleanup

Features:
- Flexible invalidation patterns
- Event-driven invalidation triggers
- Selective invalidation based on content changes
- Performance optimization
- Analytics and monitoring
"""

import asyncio
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from app.models.proxy import ProxyCacheEntry, CacheInvalidationLog
from app.services.proxy_caching.response_cache import ResponseCache
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class InvalidationType(Enum):
    """Types of cache invalidation."""
    MANUAL = "manual"
    PATTERN = "pattern"
    TAG = "tag"
    TIME_BASED = "time_based"
    EVENT_DRIVEN = "event_driven"
    DEPENDENCY = "dependency"
    TTL = "ttl"


class InvalidationScope(Enum):
    """Scope of cache invalidation."""
    SINGLE = "single"  # Specific cache entry
    PATTERN = "pattern"  # Entries matching pattern
    TAGGED = "tagged"  # Entries with specific tags
    ENDPOINT = "endpoint"  # All entries for endpoint
    GLOBAL = "global"  # All cache entries


@dataclass
class InvalidationRule:
    """Cache invalidation rule."""
    rule_id: str
    name: str
    description: str
    
    # Trigger conditions
    trigger_type: InvalidationType
    trigger_pattern: str
    trigger_tags: List[str] = field(default_factory=list)
    trigger_events: List[str] = field(default_factory=list)
    
    # Invalidation scope
    scope: InvalidationScope
    scope_pattern: str = "*"
    
    # Timing
    delay_seconds: int = 0
    batch_size: int = 100
    
    # Status
    is_active: bool = True
    priority: int = 0
    
    # Statistics
    execution_count: int = 0
    success_count: int = 0
    last_executed: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InvalidationEvent:
    """Cache invalidation event."""
    event_id: str
    event_type: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    
    # Context
    endpoint_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Related data
    related_cache_keys: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class InvalidationResult:
    """Result of cache invalidation operation."""
    success: bool
    entries_invalidated: int
    entries_failed: int
    execution_time_ms: float
    error_message: Optional[str] = None
    
    # Details
    invalidated_keys: List[str] = field(default_factory=list)
    failed_keys: List[str] = field(default_factory=list)
    
    # Statistics
    pattern_matched: int = 0
    tags_matched: int = 0
    time_based_expired: int = 0


class CacheInvalidationManager:
    """
    Smart cache invalidation manager.
    
    Features:
    - Multiple invalidation strategies
    - Event-driven invalidation
    - Pattern-based selection
    - Tag-based grouping
    - Performance optimization
    """
    
    def __init__(self, response_cache: ResponseCache):
        """Initialize cache invalidation manager."""
        self.response_cache = response_cache
        self.invalidation_rules: Dict[str, InvalidationRule] = {}
        self.event_listeners: Dict[str, List[Callable]] = defaultdict(list)
        
        # Event queue for processing
        self.event_queue = deque(maxlen=10000)
        self.processing_queue = asyncio.Queue(maxsize=1000)
        
        # Background tasks
        self.event_processor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_invalidations": 0,
            "successful_invalidations": 0,
            "failed_invalidations": 0,
            "events_processed": 0,
            "patterns_matched": 0,
            "avg_execution_time_ms": 0.0
        }
        
        # Cache tracking
        self.cache_key_patterns: Dict[str, Set[str]] = defaultdict(set)  # pattern -> keys
        self.cache_key_tags: Dict[str, Set[str]] = defaultdict(set)  # key -> tags
        self.cache_key_timestamps: Dict[str, datetime] = {}  # key -> creation time
        
        logger.info("Cache invalidation manager initialized")
    
    async def initialize(self):
        """Initialize cache invalidation manager."""
        try:
            # Load invalidation rules from database
            await self._load_invalidation_rules()
            
            # Start background tasks
            self.event_processor_task = asyncio.create_task(self._event_processor_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Cache invalidation manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache invalidation manager: {e}")
            raise
    
    async def _load_invalidation_rules(self):
        """Load invalidation rules from database."""
        # This would load rules from database
        # For now, create default rules
        
        default_rules = [
            InvalidationRule(
                rule_id="default_ttl",
                name="Default TTL Invalidator",
                description="Invalidate expired cache entries",
                trigger_type=InvalidationType.TTL,
                trigger_pattern="*",
                scope=InvalidationScope.GLOBAL,
                is_active=True
            ),
            InvalidationRule(
                rule_id="endpoint_pattern",
                name="Endpoint Pattern Invalidator",
                description="Invalidate cache based on endpoint patterns",
                trigger_type=InvalidationType.PATTERN,
                trigger_pattern="*",
                scope=InvalidationScope.PATTERN,
                is_active=True
            ),
            InvalidationRule(
                rule_id="event_driven",
                name="Event Driven Invalidator",
                description="Invalidate cache based on system events",
                trigger_type=InvalidationType.EVENT_DRIVEN,
                trigger_pattern="*",
                scope=InvalidationScope.ENDPOINT,
                is_active=True
            )
        ]
        
        for rule in default_rules:
            self.invalidation_rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default invalidation rules")
    
    async def _event_processor_loop(self):
        """Background loop for processing invalidation events."""
        try:
            while True:
                try:
                    # Get event from queue with timeout
                    event = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                    
                    # Process event
                    await self._process_invalidation_event(event)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing invalidation event: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Event processor loop cancelled")
        except Exception as e:
            logger.error(f"Error in event processor loop: {e}")
    
    async def _cleanup_loop(self):
        """Background loop for cleanup operations."""
        try:
            while True:
                await self._perform_cleanup()
                await asyncio.sleep(300)  # Every 5 minutes
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    async def _process_invalidation_event(self, event: InvalidationEvent):
        """Process a single invalidation event."""
        start_time = time.time()
        
        try:
            logger.debug(f"Processing invalidation event: {event.event_type}")
            
            # Find matching rules
            matching_rules = self._find_matching_rules(event)
            
            # Process each matching rule
            total_invalidated = 0
            total_failed = 0
            
            for rule in matching_rules:
                if not rule.is_active:
                    continue
                
                result = await self._execute_invalidation_rule(rule, event)
                
                if result.success:
                    total_invalidated += result.entries_invalidated
                    total_success = result.entries_invalidated
                else:
                    total_failed += result.entries_failed
                
                # Update rule statistics
                rule.execution_count += 1
                if result.success:
                    rule.success_count += 1
                rule.last_executed = datetime.utcnow()
            
            # Update statistics
            execution_time = (time.time() - start_time) * 1000
            self.stats["events_processed"] += 1
            self.stats["total_invalidations"] += total_invalidated
            
            if total_invalidated > 0:
                self.stats["successful_invalidations"] += 1
            else:
                self.stats["failed_invalidations"] += 1
            
            # Update average execution time
            total_ops = self.stats["total_invalidations"] + self.stats["failed_invalidations"]
            if total_ops > 0:
                self.stats["avg_execution_time_ms"] = (
                    (self.stats["avg_execution_time_ms"] * (total_ops - 1) + execution_time) / total_ops
                )
            
            # Track event processing
            event_tracker.track_performance_event(
                "cache_invalidation_processing",
                execution_time,
                {
                    "event_type": event.event_type,
                    "source": event.source,
                    "rules_matched": len(matching_rules),
                    "entries_invalidated": total_invalidated
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process invalidation event: {e}")
    
    def _find_matching_rules(self, event: InvalidationEvent) -> List[InvalidationRule]:
        """Find invalidation rules that match the event."""
        matching_rules = []
        
        for rule in self.invalidation_rules.values():
            if self._rule_matches_event(rule, event):
                matching_rules.append(rule)
        
        # Sort by priority
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        
        return matching_rules
    
    def _rule_matches_event(self, rule: InvalidationRule, event: InvalidationEvent) -> bool:
        """Check if rule matches the event."""
        
        # Check trigger type
        if rule.trigger_type == InvalidationType.EVENT_DRIVEN:
            if event.event_type not in rule.trigger_events:
                return False
        
        # Check trigger pattern
        if rule.trigger_pattern != "*":
            if not re.match(rule.trigger_pattern, event.event_type):
                return False
        
        # Check endpoint scope
        if rule.scope in [InvalidationScope.ENDPOINT, InvalidationScope.PATTERN]:
            if event.endpoint_id:
                if rule.scope_pattern != "*":
                    if not re.match(rule.scope_pattern, event.endpoint_id):
                        return False
        
        # Check tags
        if rule.trigger_tags:
            if not any(tag in event.tags for tag in rule.trigger_tags):
                return False
        
        return True
    
    async def _execute_invalidation_rule(
        self,
        rule: InvalidationRule,
        event: InvalidationEvent
    ) -> InvalidationResult:
        """Execute invalidation rule."""
        
        start_time = time.time()
        
        try:
            invalidated_keys = []
            failed_keys = []
            
            # Execute based on scope
            if rule.scope == InvalidationScope.SINGLE:
                result = await self._invalidate_single(event.related_cache_keys[0] if event.related_cache_keys else "")
                if result:
                    invalidated_keys = event.related_cache_keys
                else:
                    failed_keys = event.related_cache_keys
            
            elif rule.scope == InvalidationScope.PATTERN:
                keys_to_invalidate = await self._find_keys_by_pattern(rule.scope_pattern)
                result = await self._invalidate_keys(keys_to_invalidate)
                invalidated_keys, failed_keys = result
            
            elif rule.scope == InvalidationScope.TAGGED:
                keys_to_invalidate = await self._find_keys_by_tags(rule.trigger_tags)
                result = await self._invalidate_keys(keys_to_invalidate)
                invalidated_keys, failed_keys = result
            
            elif rule.scope == InvalidationScope.ENDPOINT:
                if event.endpoint_id:
                    keys_to_invalidate = await self._find_keys_by_endpoint(event.endpoint_id)
                    result = await self._invalidate_keys(keys_to_invalidate)
                    invalidated_keys, failed_keys = result
            
            elif rule.scope == InvalidationScope.GLOBAL:
                keys_to_invalidate = await self._find_all_cache_keys()
                result = await self._invalidate_keys(keys_to_invalidate)
                invalidated_keys, failed_keys = result
            
            # Handle delay if specified
            if rule.delay_seconds > 0:
                await asyncio.sleep(rule.delay_seconds)
            
            execution_time = (time.time() - start_time) * 1000
            
            return InvalidationResult(
                success=len(failed_keys) == 0,
                entries_invalidated=len(invalidated_keys),
                entries_failed=len(failed_keys),
                execution_time_ms=execution_time,
                invalidated_keys=invalidated_keys,
                failed_keys=failed_keys
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return InvalidationResult(
                success=False,
                entries_invalidated=0,
                entries_failed=0,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def _invalidate_single(self, cache_key: str) -> bool:
        """Invalidate single cache entry."""
        
        if not cache_key:
            return False
        
        try:
            # Delete from cache
            success = await self.response_cache.cache_service.delete(cache_key, "proxy_cache", None)
            
            if success:
                # Remove from tracking
                self.cache_key_patterns.pop(cache_key, None)
                self.cache_key_tags.pop(cache_key, None)
                self.cache_key_timestamps.pop(cache_key, None)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to invalidate single cache key {cache_key}: {e}")
            return False
    
    async def _invalidate_keys(self, cache_keys: List[str]) -> Tuple[List[str], List[str]]:
        """Invalidate multiple cache keys."""
        
        invalidated_keys = []
        failed_keys = []
        
        # Process in batches
        for i in range(0, len(cache_keys), 100):  # Batch size of 100
            batch = cache_keys[i:i + 100]
            
            # Delete batch
            for cache_key in batch:
                success = await self._invalidate_single(cache_key)
                
                if success:
                    invalidated_keys.append(cache_key)
                else:
                    failed_keys.append(cache_key)
        
        return invalidated_keys, failed_keys
    
    async def _find_keys_by_pattern(self, pattern: str) -> List[str]:
        """Find cache keys matching pattern."""
        
        matched_keys = []
        
        for cache_key in self.cache_key_timestamps.keys():
            if re.match(pattern.replace("*", ".*"), cache_key):
                matched_keys.append(cache_key)
        
        return matched_keys
    
    async def _find_keys_by_tags(self, tags: List[str]) -> List[str]:
        """Find cache keys with specific tags."""
        
        matched_keys = []
        
        for cache_key, key_tags in self.cache_key_tags.items():
            if any(tag in key_tags for tag in tags):
                matched_keys.append(cache_key)
        
        return matched_keys
    
    async def _find_keys_by_endpoint(self, endpoint_id: str) -> List[str]:
        """Find cache keys for specific endpoint."""
        
        endpoint_pattern = f"*{endpoint_id}*"
        return await self._find_keys_by_pattern(endpoint_pattern)
    
    async def _find_all_cache_keys(self) -> List[str]:
        """Get all cache keys."""
        
        return list(self.cache_key_timestamps.keys())
    
    async def _perform_cleanup(self):
        """Perform cleanup operations."""
        
        try:
            # Clean up expired cache entries
            expired_count = await self._cleanup_expired_cache()
            
            # Clean up tracking data
            await self._cleanup_tracking_data()
            
            # Log cleanup
            if expired_count > 0:
                logger.info(f"Cache cleanup: removed {expired_count} expired entries")
                
                event_tracker.track_system_event(
                    "cache_cleanup",
                    EventLevel.INFO,
                    {"expired_entries": expired_count}
                )
                
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
    
    async def _cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries."""
        
        expired_keys = []
        current_time = datetime.utcnow()
        
        # Find expired keys
        for cache_key, timestamp in self.cache_key_timestamps.items():
            if (current_time - timestamp).total_seconds() > 3600:  # 1 hour default TTL
                expired_keys.append(cache_key)
        
        # Delete expired keys
        if expired_keys:
            await self._invalidate_keys(expired_keys)
        
        return len(expired_keys)
    
    async def _cleanup_tracking_data(self):
        """Clean up tracking data for removed cache entries."""
        
        # This would clean up tracking data for cache entries that no longer exist
        # For now, just ensure data consistency
        
        # Remove patterns that have no corresponding keys
        patterns_to_remove = []
        for pattern, keys in self.cache_key_patterns.items():
            if not any(key in self.cache_key_timestamps for key in keys):
                patterns_to_remove.append(pattern)
        
        for pattern in patterns_to_remove:
            self.cache_key_patterns.pop(pattern, None)
        
        # Remove tags that have no corresponding keys
        tags_to_remove = []
        for key, tags in self.cache_key_tags.items():
            if key not in self.cache_key_timestamps:
                tags_to_remove.append(key)
        
        for key in tags_to_remove:
            self.cache_key_tags.pop(key, None)
    
    async def invalidate_by_pattern(
        self,
        pattern: str,
        endpoint_id: Optional[str] = None,
        reason: str = "manual"
    ) -> InvalidationResult:
        """Manually invalidate cache by pattern."""
        
        start_time = time.time()
        
        try:
            # Build full pattern
            if endpoint_id:
                full_pattern = f"*{endpoint_id}*{pattern}*"
            else:
                full_pattern = f"*{pattern}*"
            
            # Find matching keys
            matching_keys = await self._find_keys_by_pattern(full_pattern)
            
            # Invalidate keys
            invalidated_keys, failed_keys = await self._invalidate_keys(matching_keys)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Log invalidation
            event_tracker.track_system_event(
                "cache_invalidation_manual",
                EventLevel.INFO,
                {
                    "pattern": pattern,
                    "endpoint_id": endpoint_id,
                    "reason": reason,
                    "keys_invalidated": len(invalidated_keys),
                    "keys_failed": len(failed_keys)
                }
            )
            
            return InvalidationResult(
                success=len(failed_keys) == 0,
                entries_invalidated=len(invalidated_keys),
                entries_failed=len(failed_keys),
                execution_time_ms=execution_time,
                invalidated_keys=invalidated_keys,
                failed_keys=failed_keys
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return InvalidationResult(
                success=False,
                entries_invalidated=0,
                entries_failed=0,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def invalidate_by_endpoint(self, endpoint_id: str, reason: str = "manual") -> InvalidationResult:
        """Invalidate all cache for endpoint."""
        
        return await self.invalidate_by_pattern("*", endpoint_id, reason)
    
    async def invalidate_by_tags(
        self,
        tags: List[str],
        endpoint_id: Optional[str] = None,
        reason: str = "manual"
    ) -> InvalidationResult:
        """Invalidate cache by tags."""
        
        start_time = time.time()
        
        try:
            # Find keys with specified tags
            matching_keys = await self._find_keys_by_tags(tags)
            
            # Filter by endpoint if specified
            if endpoint_id:
                endpoint_pattern = f"*{endpoint_id}*"
                matching_keys = [key for key in matching_keys if re.match(endpoint_pattern.replace("*", ".*"), key)]
            
            # Invalidate keys
            invalidated_keys, failed_keys = await self._invalidate_keys(matching_keys)
            
            execution_time = (time.time() - start_time) * 1000
            
            return InvalidationResult(
                success=len(failed_keys) == 0,
                entries_invalidated=len(invalidated_keys),
                entries_failed=len(failed_keys),
                execution_time_ms=execution_time,
                invalidated_keys=invalidated_keys,
                failed_keys=failed_keys
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return InvalidationResult(
                success=False,
                entries_invalidated=0,
                entries_failed=0,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def trigger_invalidation_event(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        **kwargs
    ):
        """Trigger invalidation event."""
        
        event = InvalidationEvent(
            event_id=f"evt_{int(time.time() * 1000000)}",
            event_type=event_type,
            source=source,
            timestamp=datetime.utcnow(),
            data=data,
            **kwargs
        )
        
        # Add to event queue
        try:
            await asyncio.wait_for(self.processing_queue.put(event), timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning("Event queue full, dropping invalidation event")
    
    def add_invalidation_rule(self, rule: InvalidationRule):
        """Add invalidation rule."""
        
        self.invalidation_rules[rule.rule_id] = rule
        
        logger.info(f"Added invalidation rule: {rule.name}")
        
        event_tracker.track_system_event(
            "cache_invalidation_rule_added",
            EventLevel.INFO,
            {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "trigger_type": rule.trigger_type.value,
                "scope": rule.scope.value
            }
        )
    
    def remove_invalidation_rule(self, rule_id: str) -> bool:
        """Remove invalidation rule."""
        
        if rule_id in self.invalidation_rules:
            rule = self.invalidation_rules.pop(rule_id)
            
            logger.info(f"Removed invalidation rule: {rule.name}")
            
            event_tracker.track_system_event(
                "cache_invalidation_rule_removed",
                EventLevel.INFO,
                {"rule_id": rule_id, "rule_name": rule.name}
            )
            
            return True
        
        return False
    
    def register_cache_entry(
        self,
        cache_key: str,
        tags: List[str] = None,
        pattern: str = None
    ):
        """Register cache entry for tracking."""
        
        self.cache_key_timestamps[cache_key] = datetime.utcnow()
        
        if tags:
            self.cache_key_tags[cache_key] = set(tags)
        
        if pattern:
            self.cache_key_patterns[pattern].add(cache_key)
    
    def unregister_cache_entry(self, cache_key: str):
        """Unregister cache entry."""
        
        self.cache_key_timestamps.pop(cache_key, None)
        self.cache_key_tags.pop(cache_key, None)
        
        # Remove from pattern tracking
        for pattern, keys in self.cache_key_patterns.items():
            keys.discard(cache_key)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get invalidation statistics."""
        
        return {
            "statistics": self.stats.copy(),
            "active_rules": len([r for r in self.invalidation_rules.values() if r.is_active]),
            "total_rules": len(self.invalidation_rules),
            "tracked_cache_keys": len(self.cache_key_timestamps),
            "rule_breakdown": {
                rule_id: {
                    "name": rule.name,
                    "trigger_type": rule.trigger_type.value,
                    "scope": rule.scope.value,
                    "execution_count": rule.execution_count,
                    "success_count": rule.success_count,
                    "last_executed": rule.last_executed.isoformat() if rule.last_executed else None
                }
                for rule_id, rule in self.invalidation_rules.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown cache invalidation manager."""
        logger.info("Shutting down cache invalidation manager...")
        
        try:
            # Cancel background tasks
            tasks = [self.event_processor_task, self.cleanup_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[task for task in tasks if task], return_exceptions=True)
            
            logger.info("Cache invalidation manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during cache invalidation manager shutdown: {e}")
