"""
Response Caching System

Intelligent response caching with TTL for proxy requests:
- Smart cache key generation
- TTL management and auto-expiration
- Cache invalidation strategies
- Performance optimization
- Cache analytics and monitoring

Features:
- Request/response caching with compression
- Intelligent cache key generation
- TTL-based expiration with refresh strategies
- Cache warming and preloading
- Analytics and performance monitoring
- Integration with Redis cache service
"""

import asyncio
import time
import hashlib
import json
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from app.models.proxy import ProxyCacheEntry, ProxyEndpoint, CacheInvalidationLog
from app.services.cache.redis_cache import cache_service
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies."""
    NONE = "none"
    BASIC = "basic"
    SMART = "smart"
    AGGRESSIVE = "aggressive"
    PREDICTIVE = "predictive"


class CacheTier(Enum):
    """Cache storage tiers."""
    MEMORY = "memory"
    DISK = "disk"
    DISTRIBUTED = "distributed"


class CachePriority(Enum):
    """Cache entry priority."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CacheKey:
    """Cache key with metadata."""
    key: str
    hash_key: str
    namespace: str
    created_at: datetime
    ttl_seconds: int
    priority: CachePriority = CachePriority.MEDIUM


@dataclass
class CacheRequest:
    """Request for cache operations."""
    endpoint_id: str
    method: str
    path: str
    query_params: Dict[str, Any]
    headers: Dict[str, str]
    request_hash: str
    cache_strategy: CacheStrategy
    ttl_seconds: int
    priority: CachePriority


@dataclass
class CacheResponse:
    """Cached response data."""
    status_code: int
    headers: Dict[str, str]
    content: Union[bytes, str]
    content_type: str
    cached_at: datetime
    expires_at: datetime
    cache_hit: bool
    cache_tier: CacheTier
    compression_ratio: float = 1.0
    size_bytes: int = 0


class CacheKeyGenerator:
    """Generates intelligent cache keys based on request characteristics."""
    
    def __init__(self):
        self.namespace_prefix = "proxy:cache:"
        
    def generate_cache_key(self, cache_request: CacheRequest) -> CacheKey:
        """Generate comprehensive cache key."""
        
        # Create base components for hashing
        components = {
            "endpoint": cache_request.endpoint_id,
            "method": cache_request.method.upper(),
            "path": cache_request.path,
            "query": self._normalize_query_params(cache_request.query_params),
            "headers": self._normalize_headers(cache_request.headers),
            "strategy": cache_request.cache_strategy.value
        }
        
        # Generate hash
        key_string = json.dumps(components, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        # Create human-readable key
        readable_key = f"{cache_request.endpoint_id}:{cache_request.method}:{cache_request.path}"
        
        # Add TTL and priority
        cache_key = CacheKey(
            key=f"{self.namespace_prefix}{readable_key}",
            hash_key=f"{self.namespace_prefix}h:{key_hash}",
            namespace=cache_request.endpoint_id,
            created_at=datetime.utcnow(),
            ttl_seconds=cache_request.ttl_seconds,
            priority=cache_request.priority
        )
        
        return cache_key
    
    def _normalize_query_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Normalize query parameters for consistent caching."""
        normalized = {}
        
        for key, value in params.items():
            # Convert to strings and sort
            if isinstance(value, list):
                normalized[key] = ",".join(sorted(str(v) for v in value))
            else:
                normalized[key] = str(value)
        
        # Sort by key for consistency
        return dict(sorted(normalized.items()))
    
    def _normalize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Normalize headers for consistent caching."""
        normalized = {}
        
        # Only include relevant headers for caching
        cache_headers = {
            "accept", "accept-encoding", "accept-language",
            "user-agent", "authorization"
        }
        
        for key, value in headers.items():
            header_key = key.lower()
            if header_key in cache_headers:
                normalized[header_key] = value
        
        return dict(sorted(normalized.items()))
    
    def generate_pattern_key(self, pattern: str, endpoint_id: str) -> str:
        """Generate pattern-based cache key for invalidation."""
        return f"{self.namespace_prefix}pattern:{endpoint_id}:{pattern}"


class CacheCompression:
    """Handles compression and decompression of cached content."""
    
    def __init__(self):
        self.compression_threshold = 1024  # 1KB
        self.compression_algorithms = ["gzip", "deflate"]
    
    def compress_content(self, content: Union[bytes, str]) -> Tuple[bytes, float]:
        """Compress content if beneficial."""
        
        # Convert to bytes if string
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        content_size = len(content)
        
        # Don't compress if too small
        if content_size < self.compression_threshold:
            return content, 1.0
        
        # Try compression
        compressed_data = zlib.compress(content, level=6)
        compression_ratio = len(compressed_data) / content_size
        
        # Only use compression if it saves at least 10%
        if compression_ratio < 0.9:
            return compressed_data, compression_ratio
        else:
            return content, 1.0
    
    def decompress_content(self, content: bytes, original_size: int) -> bytes:
        """Decompress content."""
        
        try:
            # Try to decompress
            decompressed = zlib.decompress(content)
            return decompressed
        except zlib.error:
            # If decompression fails, assume it's not compressed
            return content


class CacheInvalidation:
    """Handles cache invalidation strategies."""
    
    def __init__(self, cache_service):
        self.cache_service = cache_service
        self.invalidation_rules: Dict[str, List[str]] = {}  # endpoint -> patterns
        self.invalidation_history: List[CacheInvalidationLog] = []
    
    def add_invalidation_rule(self, endpoint_id: str, pattern: str):
        """Add invalidation rule for endpoint."""
        if endpoint_id not in self.invalidation_rules:
            self.invalidation_rules[endpoint_id] = []
        
        self.invalidation_rules[endpoint_id].append(pattern)
        logger.info(f"Added invalidation rule for {endpoint_id}: {pattern}")
    
    async def invalidate_by_pattern(self, endpoint_id: str, pattern: str, triggered_by: str = "manual") -> int:
        """Invalidate cache entries matching pattern."""
        
        try:
            # Generate pattern key
            pattern_key = f"*{pattern}*"
            
            # Find matching cache entries
            matching_keys = await self._find_matching_cache_entries(endpoint_id, pattern_key)
            
            # Delete matching entries
            deleted_count = 0
            for cache_key in matching_keys:
                if await self.cache_service.delete(cache_key):
                    deleted_count += 1
            
            # Log invalidation
            invalidation_log = CacheInvalidationLog(
                cache_entry_id="",  # This would be filled based on actual cache entries
                invalidation_type="pattern",
                trigger_reason=triggered_by,
                invalidation_method="delete",
                pattern_matched=pattern,
                cache_entries_affected=deleted_count,
                triggered_by=triggered_by
            )
            
            self.invalidation_history.append(invalidation_log)
            
            logger.info(f"Invalidated {deleted_count} cache entries for pattern {pattern}")
            
            # Track invalidation event
            event_tracker.track_system_event(
                "cache_invalidation",
                EventLevel.INFO,
                {
                    "endpoint_id": endpoint_id,
                    "pattern": pattern,
                    "deleted_count": deleted_count,
                    "triggered_by": triggered_by
                }
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0
    
    async def _find_matching_cache_entries(self, endpoint_id: str, pattern: str) -> List[str]:
        """Find cache entries matching pattern."""
        
        # This would query the cache for entries matching the pattern
        # For now, return empty list as placeholder
        
        return []
    
    async def invalidate_by_tags(self, endpoint_id: str, tags: List[str]) -> int:
        """Invalidate cache entries by tags."""
        
        # Implementation would find and delete cache entries with specified tags
        return 0
    
    async def invalidate_by_time(self, endpoint_id: str, older_than: timedelta) -> int:
        """Invalidate cache entries older than specified time."""
        
        # Implementation would find and delete cache entries older than specified time
        return 0


class ResponseCache:
    """
    Intelligent response caching system for proxy requests.
    
    Features:
    - Smart cache key generation
    - TTL-based expiration with auto-refresh
    - Multiple cache strategies
    - Compression for storage optimization
    - Intelligent invalidation
    - Analytics and monitoring
    """
    
    def __init__(self):
        """Initialize response cache."""
        self.cache_service = cache_service
        self.key_generator = CacheKeyGenerator()
        self.compression = CacheCompression()
        self.invalidation = CacheInvalidation(cache_service)
        
        # Cache configuration
        self.config = {
            "default_ttl": 300,  # 5 minutes
            "max_cache_size": 100 * 1024 * 1024,  # 100MB
            "compression_enabled": True,
            "cache_warming_enabled": True,
            "analytics_enabled": True
        }
        
        # Statistics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "cache_deletes": 0,
            "total_size_bytes": 0,
            "avg_response_time_ms": 0.0
        }
        
        # Cache metrics
        self.metrics = {
            "hit_rate": 0.0,
            "avg_cache_size": 0.0,
            "most_cached_endpoints": {},
            "cache_strategy_usage": {}
        }
        
        logger.info("Response cache initialized")
    
    async def initialize(self):
        """Initialize response cache."""
        try:
            # Initialize cache service
            await self.cache_service.initialize()
            
            logger.info("Response cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize response cache: {e}")
            raise
    
    async def get_cached_response(
        self,
        proxy_request: Any,
        endpoint: ProxyEndpoint
    ) -> Optional[CacheResponse]:
        """Get cached response for request."""
        
        start_time = time.time()
        
        try:
            # Check if caching is enabled
            if not endpoint.cache_enabled or endpoint.cache_strategy == CacheStrategy.NONE:
                return None
            
            # Create cache request
            cache_request = CacheRequest(
                endpoint_id=endpoint.id,
                method=proxy_request.method,
                path=proxy_request.path,
                query_params=proxy_request.query_params,
                headers=proxy_request.headers,
                request_hash=hashlib.sha256(f"{proxy_request.path}:{proxy_request.query_params}".encode()).hexdigest(),
                cache_strategy=endpoint.cache_strategy,
                ttl_seconds=endpoint.cache_ttl_seconds,
                priority=CachePriority.MEDIUM
            )
            
            # Generate cache key
            cache_key = self.key_generator.generate_cache_key(cache_request)
            
            # Get from cache
            cached_data = await self.cache_service.get(cache_key.hash_key, "proxy_cache", None)
            
            if cached_data is None:
                # Cache miss
                self.stats["cache_misses"] += 1
                
                # Log cache miss
                event_tracker.track_performance_event(
                    "cache_miss",
                    (time.time() - start_time) * 1000,
                    {
                        "endpoint_id": endpoint.id,
                        "path": proxy_request.path,
                        "strategy": endpoint.cache_strategy.value
                    }
                )
                
                return None
            
            # Cache hit - deserialize response
            try:
                response_data = cached_data
                
                # Decompress if needed
                if response_data.get("compressed", False):
                    content = self.compression.decompress_content(
                        response_data["content"], response_data["original_size"]
                    )
                else:
                    content = response_data["content"]
                
                cache_response = CacheResponse(
                    status_code=response_data["status_code"],
                    headers=response_data["headers"],
                    content=content,
                    content_type=response_data["content_type"],
                    cached_at=response_data["cached_at"],
                    expires_at=response_data["expires_at"],
                    cache_hit=True,
                    cache_tier=CacheTier.MEMORY,  # Currently using memory cache
                    compression_ratio=response_data.get("compression_ratio", 1.0),
                    size_bytes=response_data.get("size_bytes", 0)
                )
                
                # Update statistics
                self.stats["cache_hits"] += 1
                self.stats["total_size_bytes"] += cache_response.size_bytes
                
                # Log cache hit
                event_tracker.track_performance_event(
                    "cache_hit",
                    (time.time() - start_time) * 1000,
                    {
                        "endpoint_id": endpoint.id,
                        "path": proxy_request.path,
                        "size_bytes": cache_response.size_bytes,
                        "compression_ratio": cache_response.compression_ratio
                    }
                )
                
                return cache_response
                
            except Exception as e:
                logger.error(f"Failed to deserialize cached response: {e}")
                self.stats["cache_misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Cache get operation failed: {e}")
            self.stats["cache_misses"] += 1
            return None
    
    async def cache_response(
        self,
        proxy_request: Any,
        proxy_response: Any,
        endpoint: ProxyEndpoint
    ) -> bool:
        """Cache response for future requests."""
        
        try:
            # Check if caching is enabled
            if not endpoint.cache_enabled or endpoint.cache_strategy == CacheStrategy.NONE:
                return False
            
            # Check response status (only cache successful responses)
            if proxy_response.status_code >= 400:
                return False
            
            # Check content type
            content_type = proxy_response.headers.get("content-type", "")
            if not self._should_cache_content_type(content_type):
                return False
            
            # Check response size (don't cache very large responses)
            if isinstance(proxy_response.content, bytes):
                content_size = len(proxy_response.content)
                if content_size > 10 * 1024 * 1024:  # 10MB
                    return False
            
            # Create cache request
            cache_request = CacheRequest(
                endpoint_id=endpoint.id,
                method=proxy_request.method,
                path=proxy_request.path,
                query_params=proxy_request.query_params,
                headers=proxy_request.headers,
                request_hash=hashlib.sha256(f"{proxy_request.path}:{proxy_request.query_params}".encode()).hexdigest(),
                cache_strategy=endpoint.cache_strategy,
                ttl_seconds=endpoint.cache_ttl_seconds,
                priority=CachePriority.MEDIUM
            )
            
            # Generate cache key
            cache_key = self.key_generator.generate_cache_key(cache_request)
            
            # Prepare response data for caching
            response_data = {
                "status_code": proxy_response.status_code,
                "headers": dict(proxy_response.headers),
                "content": proxy_response.content,
                "content_type": content_type,
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=cache_key.ttl_seconds)).isoformat(),
                "original_size": len(proxy_response.content) if isinstance(proxy_response.content, bytes) else 0,
                "compression_ratio": 1.0,
                "compressed": False
            }
            
            # Compress content if beneficial
            if self.config["compression_enabled"]:
                compressed_content, compression_ratio = self.compression.compress_content(proxy_response.content)
                
                if compression_ratio < 1.0:  # Compression saved space
                    response_data["content"] = compressed_content
                    response_data["compression_ratio"] = compression_ratio
                    response_data["compressed"] = True
                    response_data["original_size"] = len(proxy_response.content)
            
            # Store in cache
            success = await self.cache_service.set(
                cache_key.hash_key,
                response_data,
                "proxy_cache",
                None,
                cache_key.ttl_seconds
            )
            
            if success:
                # Update statistics
                self.stats["cache_sets"] += 1
                self.stats["total_size_bytes"] += len(str(response_data))
                
                # Log cache set
                event_tracker.track_performance_event(
                    "cache_set",
                    0.0,  # Cache set is fast
                    {
                        "endpoint_id": endpoint.id,
                        "path": proxy_request.path,
                        "ttl_seconds": cache_key.ttl_seconds,
                        "compressed": response_data["compressed"],
                        "size_bytes": response_data.get("original_size", 0)
                    }
                )
                
                return True
            else:
                logger.warning(f"Failed to cache response for {proxy_request.path}")
                return False
                
        except Exception as e:
            logger.error(f"Cache set operation failed: {e}")
            return False
    
    def _should_cache_content_type(self, content_type: str) -> bool:
        """Determine if content type should be cached."""
        
        cacheable_types = {
            "application/json",
            "application/xml",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "text/plain",
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp"
        }
        
        base_type = content_type.split(";")[0].strip().lower()
        return base_type in cacheable_types
    
    async def invalidate_cache(self, endpoint_id: str, pattern: str = "*") -> int:
        """Invalidate cache for endpoint or pattern."""
        
        try:
            if pattern == "*":
                # Invalidate all cache for endpoint
                deleted_count = await self.cache_service.delete_pattern(
                    f"*{endpoint_id}*", None
                )
            else:
                # Invalidate by specific pattern
                deleted_count = await self.invalidation.invalidate_by_pattern(
                    endpoint_id, pattern
                )
            
            self.stats["cache_deletes"] += deleted_count
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0
    
    async def warm_cache(self, endpoint_id: str) -> int:
        """Warm cache with frequently accessed content."""
        
        try:
            # This would implement cache warming based on access patterns
            # For now, return 0
            
            logger.info(f"Cache warming requested for endpoint {endpoint_id}")
            return 0
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        
        # Calculate derived metrics
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "statistics": self.stats.copy(),
            "derived_metrics": {
                "hit_rate_percent": hit_rate,
                "total_requests": total_requests,
                "avg_cache_size_bytes": self.stats["total_size_bytes"] / max(self.stats["cache_sets"], 1)
            },
            "configuration": self.config,
            "performance": self.metrics
        }
    
    async def clear_cache(self, endpoint_id: Optional[str] = None) -> int:
        """Clear cache entries."""
        
        try:
            if endpoint_id:
                # Clear cache for specific endpoint
                deleted_count = await self.cache_service.delete_pattern(f"*{endpoint_id}*", None)
            else:
                # Clear all cache
                deleted_count = await self.cache_service.clear_cache("proxy_cache", None)
            
            # Reset statistics
            self.stats = {
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_sets": 0,
                "cache_deletes": deleted_count,
                "total_size_bytes": 0,
                "avg_response_time_ms": 0.0
            }
            
            logger.info(f"Cleared {deleted_count} cache entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return 0
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance."""
        
        optimization_results = {
            "items_removed": 0,
            "space_freed_bytes": 0,
            "optimizations_applied": []
        }
        
        try:
            # Remove expired entries
            expired_count = await self._cleanup_expired_entries()
            optimization_results["items_removed"] += expired_count
            
            # Optimize compression
            compression_optimized = await self._optimize_compression()
            if compression_optimized:
                optimization_results["optimizations_applied"].append("compression_optimization")
            
            # Update cache metrics
            await self._update_cache_metrics()
            
            logger.info(f"Cache optimization completed: {optimization_results}")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return optimization_results
    
    async def _cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries."""
        
        # This would implement cleanup of expired cache entries
        # For now, return 0
        
        return 0
    
    async def _optimize_compression(self) -> bool:
        """Optimize compression settings."""
        
        # This would analyze compression ratios and adjust settings
        # For now, return False
        
        return False
    
    async def _update_cache_metrics(self):
        """Update cache performance metrics."""
        
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_requests > 0:
            self.metrics["hit_rate"] = self.stats["cache_hits"] / total_requests
        
        # Update strategy usage
        # This would track usage of different cache strategies
    
    async def shutdown(self):
        """Shutdown response cache."""
        logger.info("Shutting down response cache...")
        
        # Close cache service connection
        if hasattr(self.cache_service, 'close'):
            await self.cache_service.close()
        
        logger.info("Response cache shutdown complete")
