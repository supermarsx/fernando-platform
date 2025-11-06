"""
Rate Limiting Service

Implements multiple rate limiting algorithms for the proxy server including
token bucket, sliding window, fixed window, and leaky bucket algorithms.
Provides flexible rate limiting with support for different scopes, policies,
and real-time monitoring.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
import json

from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithm types"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"

class RateLimitScope(Enum):
    """Rate limiting scope levels"""
    GLOBAL = "global"
    IP = "ip"
    USER = "user"
    ORGANIZATION = "organization"
    ENDPOINT = "endpoint"
    API_KEY = "api_key"

class RateLimitAction(Enum):
    """Rate limit violation actions"""
    BLOCK = "block"
    THROTTLE = "throttle"
    WARN = "warn"
    LOG_ONLY = "log_only"

@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""
    id: str
    name: str
    algorithm: RateLimitAlgorithm
    scope: RateLimitScope
    scope_value: str  # IP address, user ID, org ID, endpoint pattern, etc.
    max_requests: int
    window_seconds: int
    burst_multiplier: float = 1.0  # Allow burst above max_requests
    block_duration_seconds: int = 60  # How long to block if violated
    action: RateLimitAction = RateLimitAction.BLOCK
    endpoint_patterns: List[str] = field(default_factory=list)
    priority: int = 0  # Higher priority rules are applied first
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RateLimitResult:
    """Rate limiting check result"""
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    headers: Dict[str, str] = field(default_factory=dict)
    retry_after_seconds: Optional[int] = None
    violation_detected: bool = False
    rate_limited_count: int = 0

class TokenBucket:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket"""
        now = time.time()
        
        # Calculate tokens to add based on time passed
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate
        
        # Refill bucket (cap at capacity)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Check if we can consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_remaining_tokens(self) -> float:
        """Get remaining tokens in bucket"""
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate
        return min(self.capacity, self.tokens + tokens_to_add)

class SlidingWindow:
    """Sliding window rate limiter implementation"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed under sliding window"""
        now = time.time()
        
        # Remove expired requests
        cutoff = now - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_remaining_requests(self) -> int:
        """Get remaining requests in current window"""
        now = time.time()
        
        # Remove expired requests
        cutoff = now - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        return max(0, self.max_requests - len(self.requests))

class FixedWindow:
    """Fixed window rate limiter implementation"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.window_start = self._get_window_start()
        self.request_count = 0
    
    def _get_window_start(self) -> float:
        """Get current window start time"""
        return int(time.time() / self.window_seconds) * self.window_seconds
    
    def is_allowed(self) -> bool:
        """Check if request is allowed under fixed window"""
        now = time.time()
        current_window = self._get_window_start()
        
        # Reset if new window
        if current_window != self.window_start:
            self.window_start = current_window
            self.request_count = 0
        
        # Check if under limit
        if self.request_count < self.max_requests:
            self.request_count += 1
            return True
        
        return False
    
    def get_remaining_requests(self) -> int:
        """Get remaining requests in current window"""
        now = time.time()
        current_window = self._get_window_start()
        
        # Reset if new window
        if current_window != self.window_start:
            self.window_start = current_window
            self.request_count = 0
        
        return max(0, self.max_requests - self.request_count)
    
    def get_window_reset_time(self) -> datetime:
        """Get time when current window resets"""
        return datetime.fromtimestamp(self.window_start + self.window_seconds, tz=timezone.utc)

class LeakyBucket:
    """Leaky bucket rate limiter implementation"""
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate  # requests per second
        self.water_level = 0  # Current water level (requests)
        self.last_leak = time.time()
    
    def process_request(self) -> bool:
        """Process a request through the bucket"""
        now = time.time()
        
        # Calculate water leaked since last check
        time_passed = now - self.last_leak
        water_leaked = time_passed * self.leak_rate
        
        # Reduce water level
        self.water_level = max(0, self.water_level - water_leaked)
        self.last_leak = now
        
        # Check if we can accept request
        if self.water_level < self.capacity:
            self.water_level += 1
            return True
        
        return False
    
    def get_water_level(self) -> float:
        """Get current water level"""
        now = time.time()
        time_passed = now - self.last_leak
        water_leaked = time_passed * self.leak_rate
        return max(0, self.water_level - water_leaked)

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load"""
    
    def __init__(
        self,
        base_max_requests: int,
        window_seconds: int,
        adaptation_factor: float = 0.1
    ):
        self.base_max_requests = base_max_requests
        self.window_seconds = window_seconds
        self.adaptation_factor = adaptation_factor
        self.sliding_window = SlidingWindow(base_max_requests, window_seconds)
        self.current_limit = base_max_requests
        self.system_load = 0.5  # 0.0 = no load, 1.0 = max load
        self.performance_score = 1.0
    
    def is_allowed(self, response_time: Optional[float] = None) -> bool:
        """Check if request is allowed with adaptive limits"""
        # Update system load if response time provided
        if response_time is not None:
            self._update_system_load(response_time)
        
        # Adjust current limit based on system load
        self._adjust_limit()
        
        # Update sliding window with current limit
        self.sliding_window.max_requests = int(self.current_limit)
        
        return self.sliding_window.is_allowed()
    
    def _update_system_load(self, response_time: float) -> None:
        """Update system load based on response time"""
        # Normalize response time to 0-1 scale (assuming 1000ms = full load)
        load_increase = response_time / 1000.0
        
        # Exponential moving average for smooth adaptation
        alpha = 0.1
        self.system_load = (1 - alpha) * self.system_load + alpha * load_increase
        
        # Update performance score (inverse of system load)
        self.performance_score = max(0.1, 1.0 - self.system_load)
    
    def _adjust_limit(self) -> None:
        """Adjust rate limit based on system load"""
        # If system is under heavy load, reduce limit
        # If system is performing well, increase limit
        target_limit = self.base_max_requests * self.performance_score
        
        # Smooth adjustment
        alpha = 0.05  # Smoother adaptation
        self.current_limit = (1 - alpha) * self.current_limit + alpha * target_limit
        
        # Ensure limits are reasonable
        self.current_limit = max(
            self.base_max_requests * 0.1,  # Minimum 10% of base
            min(self.current_limit, self.base_max_requests * 2.0)  # Maximum 200% of base
        )

class RateLimiter:
    """
    Comprehensive Rate Limiting Service
    
    Supports multiple algorithms and scopes:
    - Token Bucket: Allows bursts with controlled refill
    - Sliding Window: Precise rate limiting with time windows
    - Fixed Window: Simple and predictable rate limiting
    - Leaky Bucket: Smooths out traffic bursts
    - Adaptive: Automatically adjusts based on system load
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Rate limiting algorithms
        self._token_buckets = {}  # scope_key -> TokenBucket
        self._sliding_windows = {}  # scope_key -> SlidingWindow
        self._fixed_windows = {}  # scope_key -> FixedWindow
        self._leaky_buckets = {}  # scope_key -> LeakyBucket
        self._adaptive_limiters = {}  # scope_key -> AdaptiveRateLimiter
        
        # Rate limit rules
        self._rules: List[RateLimitRule] = []
        self._rules_by_priority = []
        
        # Real-time statistics
        self._rate_limit_stats = {
            'total_checks': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'rule_violations': defaultdict(int)
        }
        
        # Configuration
        self.config = {
            'default_max_requests': 100,
            'default_window_seconds': 60,
            'max_burst_multiplier': 5.0,
            'cleanup_interval_seconds': 3600,
            'stats_retention_hours': 24,
            'redis_namespace': 'rate_limit',
        }
        
        logger.info("RateLimiter initialized")
    
    async def add_rule(self, rule: RateLimitRule) -> None:
        """Add a rate limit rule"""
        self._rules.append(rule)
        
        # Sort rules by priority (higher priority first)
        self._rules_by_priority = sorted(
            self._rules,
            key=lambda r: r.priority,
            reverse=True
        )
        
        logger.info(f"Added rate limit rule: {rule.name} ({rule.algorithm.value})")
        
        # Track rule addition
        await self.event_tracker.track_event(
            "rate_limit_rule_added",
            {
                "rule_id": rule.id,
                "algorithm": rule.algorithm.value,
                "scope": rule.scope.value,
                "max_requests": rule.max_requests,
                "window_seconds": rule.window_seconds
            }
        )
    
    async def remove_rule(self, rule_id: str) -> bool:
        """Remove a rate limit rule"""
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        
        if len(self._rules) < original_count:
            # Resort rules
            self._rules_by_priority = sorted(
                self._rules,
                key=lambda r: r.priority,
                reverse=True
            )
            
            logger.info(f"Removed rate limit rule: {rule_id}")
            
            await self.event_tracker.track_event(
                "rate_limit_rule_removed",
                {"rule_id": rule_id}
            )
            
            return True
        
        return False
    
    async def check_rate_limit(
        self,
        identifier: str,  # IP, user_id, api_key_id, etc.
        scope: RateLimitScope,
        endpoint: str = "",
        response_time: Optional[float] = None,
        request_size: int = 0
    ) -> RateLimitResult:
        """
        Check if request is allowed under rate limits
        
        Args:
            identifier: Scope identifier (IP, user ID, etc.)
            scope: Rate limiting scope
            endpoint: Requested endpoint
            response_time: Response time for adaptive limiting
            request_size: Size of request for weighting
            
        Returns:
            RateLimitResult with allowance and limit information
        """
        start_time = time.time()
        
        # Default result
        result = RateLimitResult(
            allowed=True,
            remaining_requests=self.config['default_max_requests'],
            reset_time=datetime.now(timezone.utc) + timedelta(seconds=self.config['default_window_seconds'])
        )
        
        applicable_rules = await self._find_applicable_rules(identifier, scope, endpoint)
        
        # Check each applicable rule
        for rule in applicable_rules:
            rule_result = await self._check_rule(rule, identifier, response_time, request_size)
            
            # Update overall result
            if not rule_result.allowed:
                result.allowed = False
                result.violation_detected = True
                result.rate_limited_count += 1
                
                # Update headers for client
                result.headers.update(rule_result.headers)
                result.retry_after_seconds = rule_result.retry_after_seconds
                
                # Break on first violation (most restrictive)
                break
            else:
                # Update remaining requests if this rule is more restrictive
                result.remaining_requests = min(
                    result.remaining_requests,
                    rule_result.remaining_requests
                )
        
        # Update statistics
        processing_time = time.time() - start_time
        await self._update_statistics(result, processing_time)
        
        # Add rate limit headers
        self._add_rate_limit_headers(result)
        
        return result
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        scope: RateLimitScope,
        endpoint: str = ""
    ) -> Dict[str, Any]:
        """Get current rate limit status for identifier"""
        status = {
            'identifier': identifier,
            'scope': scope.value,
            'endpoint': endpoint,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'rules': []
        }
        
        applicable_rules = await self._find_applicable_rules(identifier, scope, endpoint)
        
        for rule in applicable_rules:
            rule_status = await self._get_rule_status(rule, identifier)
            status['rules'].append(rule_status)
        
        return status
    
    async def get_rate_limit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting statistics"""
        # Get real-time stats from Redis
        redis_stats = await self._get_redis_statistics()
        
        # Calculate derived metrics
        total_requests = self._rate_limit_stats['total_checks']
        allowed_rate = (
            self._rate_limit_stats['allowed_requests'] / max(1, total_requests)
        ) * 100
        blocked_rate = (
            self._rate_limit_stats['blocked_requests'] / max(1, total_requests)
        ) * 100
        
        statistics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overview': {
                'total_checks': total_requests,
                'allowed_requests': self._rate_limit_stats['allowed_requests'],
                'blocked_requests': self._rate_limit_stats['blocked_requests'],
                'allowance_rate_percent': round(allowed_rate, 2),
                'block_rate_percent': round(blocked_rate, 2)
            },
            'algorithm_breakdown': await self._get_algorithm_statistics(),
            'scope_breakdown': await self._get_scope_statistics(),
            'rule_violations': dict(self._rate_limit_stats['rule_violations']),
            'redis_statistics': redis_stats,
            'active_rules': len([r for r in self._rules if r.enabled]),
            'total_rules': len(self._rules)
        }
        
        return statistics
    
    async def reset_rate_limit(
        self,
        identifier: str,
        scope: RateLimitScope,
        endpoint: str = ""
    ) -> bool:
        """Reset rate limit for identifier"""
        try:
            # Find all applicable rules
            applicable_rules = await self._find_applicable_rules(identifier, scope, endpoint)
            
            reset_count = 0
            for rule in applicable_rules:
                scope_key = self._get_scope_key(rule, identifier)
                
                # Clear algorithm-specific data
                if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                    self._token_buckets.pop(scope_key, None)
                elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                    self._sliding_windows.pop(scope_key, None)
                elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                    self._fixed_windows.pop(scope_key, None)
                elif rule.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
                    self._leaky_buckets.pop(scope_key, None)
                elif rule.algorithm == RateLimitAlgorithm.ADAPTIVE:
                    self._adaptive_limiters.pop(scope_key, None)
                
                reset_count += 1
            
            logger.info(f"Reset rate limits for {identifier} ({reset_count} rules)")
            
            await self.event_tracker.track_event(
                "rate_limit_reset",
                {
                    "identifier": identifier,
                    "scope": scope.value,
                    "endpoint": endpoint,
                    "rules_reset": reset_count
                }
            )
            
            return reset_count > 0
            
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
            return False
    
    async def get_usage_statistics(
        self,
        identifier: str,
        scope: RateLimitScope,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get usage statistics for identifier"""
        try:
            # Get usage data from Redis
            cache_key = f"{self.config['redis_namespace']}:usage:{identifier}:{scope.value}"
            
            usage_data = await self.redis_cache.hgetall(cache_key) or {}
            
            # Parse usage data
            parsed_usage = {}
            for hour, data in usage_data.items():
                try:
                    parsed_usage[hour] = json.loads(data)
                except json.JSONDecodeError:
                    continue
            
            # Calculate statistics
            total_requests = sum(
                data.get('requests', 0) for data in parsed_usage.values()
            )
            total_blocked = sum(
                data.get('blocked', 0) for data in parsed_usage.values()
            )
            
            return {
                'identifier': identifier,
                'scope': scope.value,
                'period_hours': hours_back,
                'total_requests': total_requests,
                'total_blocked': total_blocked,
                'block_rate_percent': round(
                    (total_blocked / max(1, total_requests)) * 100, 2
                ) if total_requests > 0 else 0,
                'hourly_breakdown': parsed_usage,
                'peak_usage_hour': self._find_peak_usage_hour(parsed_usage) if parsed_usage else None,
                'usage_pattern': self._analyze_usage_pattern(parsed_usage)
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {'error': str(e)}
    
    async def _find_applicable_rules(
        self,
        identifier: str,
        scope: RateLimitScope,
        endpoint: str
    ) -> List[RateLimitRule]:
        """Find rules applicable to the request"""
        applicable_rules = []
        
        for rule in self._rules_by_priority:
            if not rule.enabled:
                continue
            
            # Check scope match
            if rule.scope != scope:
                continue
            
            # Check scope value match
            if rule.scope_value != "*" and rule.scope_value != identifier:
                continue
            
            # Check endpoint pattern match
            if rule.endpoint_patterns and not self._matches_endpoint_patterns(endpoint, rule.endpoint_patterns):
                continue
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    def _matches_endpoint_patterns(self, endpoint: str, patterns: List[str]) -> bool:
        """Check if endpoint matches any of the patterns"""
        import fnmatch
        
        return any(fnmatch.fnmatch(endpoint, pattern) for pattern in patterns)
    
    async def _check_rule(
        self,
        rule: RateLimitRule,
        identifier: str,
        response_time: Optional[float],
        request_size: int
    ) -> RateLimitResult:
        """Check a specific rate limit rule"""
        scope_key = self._get_scope_key(rule, identifier)
        result = RateLimitResult(
            allowed=True,
            remaining_requests=rule.max_requests,
            reset_time=datetime.now(timezone.utc) + timedelta(seconds=rule.window_seconds)
        )
        
        try:
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                result = await self._check_token_bucket(rule, scope_key, result, request_size)
            elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                result = await self._check_sliding_window(rule, scope_key, result)
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                result = await self._check_fixed_window(rule, scope_key, result)
            elif rule.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
                result = await self._check_leaky_bucket(rule, scope_key, result)
            elif rule.algorithm == RateLimitAlgorithm.ADAPTIVE:
                result = await self._check_adaptive(rule, scope_key, result, response_time)
            
            # Handle violation
            if not result.allowed:
                result.violation_detected = True
                self._rate_limit_stats['rule_violations'][rule.id] += 1
                
                # Store violation for tracking
                await self._track_violation(rule, identifier)
                
                # Add Retry-After header
                if result.retry_after_seconds:
                    result.headers['Retry-After'] = str(result.retry_after_seconds)
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking rate limit rule {rule.id}: {e}")
            # Fail open (allow request) on error
            return result
    
    async def _check_token_bucket(
        self,
        rule: RateLimitRule,
        scope_key: str,
        result: RateLimitResult,
        request_size: int
    ) -> RateLimitResult:
        """Check token bucket rate limit"""
        # Get or create token bucket
        if scope_key not in self._token_buckets:
            capacity = int(rule.max_requests * rule.burst_multiplier)
            refill_rate = rule.max_requests / rule.window_seconds
            self._token_buckets[scope_key] = TokenBucket(capacity, refill_rate)
        
        bucket = self._token_buckets[scope_key]
        
        # Calculate tokens needed (weight by request size)
        tokens_needed = max(1, request_size // 1024)  # 1 token per KB
        
        if bucket.consume(tokens_needed):
            result.remaining_requests = int(bucket.get_remaining_tokens())
            result.reset_time = datetime.fromtimestamp(
                time.time() + (bucket.capacity - bucket.tokens) / bucket.refill_rate,
                tz=timezone.utc
            )
        else:
            result.allowed = False
            result.retry_after_seconds = int(1 / bucket.refill_rate)  # Time until next token
        
        return result
    
    async def _check_sliding_window(
        self,
        rule: RateLimitRule,
        scope_key: str,
        result: RateLimitResult
    ) -> RateLimitResult:
        """Check sliding window rate limit"""
        # Get or create sliding window
        if scope_key not in self._sliding_windows:
            self._sliding_windows[scope_key] = SlidingWindow(rule.max_requests, rule.window_seconds)
        
        window = self._sliding_windows[scope_key]
        
        if window.is_allowed():
            result.remaining_requests = window.get_remaining_requests()
        else:
            result.allowed = False
            # Calculate time until oldest request expires
            result.retry_after_seconds = rule.window_seconds
        
        return result
    
    async def _check_fixed_window(
        self,
        rule: RateLimitRule,
        scope_key: str,
        result: RateLimitResult
    ) -> RateLimitResult:
        """Check fixed window rate limit"""
        # Get or create fixed window
        if scope_key not in self._fixed_windows:
            self._fixed_windows[scope_key] = FixedWindow(rule.max_requests, rule.window_seconds)
        
        window = self._fixed_windows[scope_key]
        
        if window.is_allowed():
            result.remaining_requests = window.get_remaining_requests()
            result.reset_time = window.get_window_reset_time()
        else:
            result.allowed = False
            # Time until current window ends
            time_until_reset = window.get_window_reset_time() - datetime.now(timezone.utc)
            result.retry_after_seconds = int(time_until_reset.total_seconds())
        
        return result
    
    async def _check_leaky_bucket(
        self,
        rule: RateLimitRule,
        scope_key: str,
        result: RateLimitResult
    ) -> RateLimitResult:
        """Check leaky bucket rate limit"""
        # Get or create leaky bucket
        if scope_key not in self._leaky_buckets:
            capacity = int(rule.max_requests * rule.burst_multiplier)
            leak_rate = rule.max_requests / rule.window_seconds
            self._leaky_buckets[scope_key] = LeakyBucket(capacity, leak_rate)
        
        bucket = self._leaky_buckets[scope_key]
        
        if bucket.process_request():
            result.remaining_requests = int(bucket.capacity - bucket.get_water_level())
        else:
            result.allowed = False
            # Time to leak one request
            result.retry_after_seconds = int(1 / bucket.leak_rate)
        
        return result
    
    async def _check_adaptive(
        self,
        rule: RateLimitRule,
        scope_key: str,
        result: RateLimitResult,
        response_time: Optional[float]
    ) -> RateLimitResult:
        """Check adaptive rate limit"""
        # Get or create adaptive limiter
        if scope_key not in self._adaptive_limiters:
            self._adaptive_limiters[scope_key] = AdaptiveRateLimiter(
                rule.max_requests,
                rule.window_seconds,
                rule.metadata.get('adaptation_factor', 0.1)
            )
        
        limiter = self._adaptive_limiters[scope_key]
        
        if limiter.is_allowed(response_time):
            result.remaining_requests = int(limiter.current_limit)
            # Adaptive limiters use sliding window for timing
            if scope_key in self._sliding_windows:
                result.reset_time = datetime.fromtimestamp(
                    time.time() + self._sliding_windows[scope_key].window_seconds,
                    tz=timezone.utc
                )
        else:
            result.allowed = False
            result.retry_after_seconds = rule.window_seconds
        
        return result
    
    def _get_scope_key(self, rule: RateLimitRule, identifier: str) -> str:
        """Generate unique scope key for algorithm storage"""
        return f"{rule.scope.value}:{rule.scope_value}:{identifier}"
    
    async def _get_rule_status(self, rule: RateLimitRule, identifier: str) -> Dict[str, Any]:
        """Get status for a specific rule"""
        scope_key = self._get_scope_key(rule, identifier)
        status = {
            'rule_id': rule.id,
            'rule_name': rule.name,
            'algorithm': rule.algorithm.value,
            'max_requests': rule.max_requests,
            'window_seconds': rule.window_seconds,
            'enabled': rule.enabled
        }
        
        try:
            # Get algorithm-specific status
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET and scope_key in self._token_buckets:
                bucket = self._token_buckets[scope_key]
                status['remaining_tokens'] = round(bucket.get_remaining_tokens(), 2)
                status['capacity'] = bucket.capacity
                
            elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW and scope_key in self._sliding_windows:
                window = self._sliding_windows[scope_key]
                status['remaining_requests'] = window.get_remaining_requests()
                
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW and scope_key in self._fixed_windows:
                window = self._fixed_windows[scope_key]
                status['remaining_requests'] = window.get_remaining_requests()
                status['window_reset_time'] = window.get_window_reset_time().isoformat()
                
            elif rule.algorithm == RateLimitAlgorithm.ADAPTIVE and scope_key in self._adaptive_limiters:
                limiter = self._adaptive_limiters[scope_key]
                status['current_limit'] = round(limiter.current_limit, 2)
                status['system_load'] = round(limiter.system_load, 3)
                status['performance_score'] = round(limiter.performance_score, 3)
        
        except Exception as e:
            logger.error(f"Failed to get rule status for {rule.id}: {e}")
            status['error'] = str(e)
        
        return status
    
    async def _track_violation(self, rule: RateLimitRule, identifier: str) -> None:
        """Track rate limit violation"""
        try:
            violation_data = {
                'rule_id': rule.id,
                'identifier': identifier,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'algorithm': rule.algorithm.value,
                'max_requests': rule.max_requests,
                'window_seconds': rule.window_seconds
            }
            
            # Store in Redis for tracking
            cache_key = f"{self.config['redis_namespace']}:violations:{rule.id}"
            await self.redis_cache.lpush(cache_key, json.dumps(violation_data))
            await self.redis_cache.ltrim(cache_key, 0, 99)  # Keep last 100 violations
            await self.redis_cache.expire(cache_key, 86400)  # 24 hours
            
            # Track in telemetry
            await self.event_tracker.track_event(
                "rate_limit_violation",
                {
                    "rule_id": rule.id,
                    "identifier": identifier,
                    "algorithm": rule.algorithm.value
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to track rate limit violation: {e}")
    
    async def _update_statistics(self, result: RateLimitResult, processing_time: float) -> None:
        """Update rate limiting statistics"""
        self._rate_limit_stats['total_checks'] += 1
        
        if result.allowed:
            self._rate_limit_stats['allowed_requests'] += 1
        else:
            self._rate_limit_stats['blocked_requests'] += 1
    
    def _add_rate_limit_headers(self, result: RateLimitResult) -> None:
        """Add standard rate limit headers to result"""
        # Standard rate limit headers
        result.headers.update({
            'X-RateLimit-Limit': str(result.remaining_requests),
            'X-RateLimit-Remaining': str(result.remaining_requests),
            'X-RateLimit-Reset': str(int(result.reset_time.timestamp()))
        })
        
        if result.violation_detected:
            result.headers['X-RateLimit-Violation'] = 'true'
            result.headers['X-RateLimit-Count'] = str(result.rate_limited_count)
    
    async def _get_redis_statistics(self) -> Dict[str, Any]:
        """Get Redis statistics for rate limiting"""
        try:
            redis_info = await self.redis_cache.info()
            return {
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', '0B'),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {'error': str(e)}
    
    async def _get_algorithm_statistics(self) -> Dict[str, Any]:
        """Get statistics by algorithm type"""
        stats = defaultdict(int)
        
        for rule in self._rules:
            if rule.enabled:
                stats[rule.algorithm.value] += 1
        
        return dict(stats)
    
    async def _get_scope_statistics(self) -> Dict[str, Any]:
        """Get statistics by scope type"""
        stats = defaultdict(int)
        
        for rule in self._rules:
            if rule.enabled:
                stats[rule.scope.value] += 1
        
        return dict(stats)
    
    def _find_peak_usage_hour(self, usage_data: Dict[str, Any]) -> Optional[str]:
        """Find hour with peak usage"""
        if not usage_data:
            return None
        
        return max(usage_data.keys(), key=lambda hour: usage_data[hour].get('requests', 0))
    
    def _analyze_usage_pattern(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze usage patterns"""
        if not usage_data:
            return {'pattern': 'no_data'}
        
        # Calculate usage distribution
        usage_values = [data.get('requests', 0) for data in usage_data.values()]
        
        if not usage_values:
            return {'pattern': 'no_usage'}
        
        avg_usage = statistics.mean(usage_values)
        peak_usage = max(usage_values)
        peak_ratio = peak_usage / max(1, avg_usage)
        
        # Determine pattern
        if peak_ratio > 3.0:
            pattern = 'spiky'
        elif peak_ratio > 1.5:
            pattern = 'variable'
        else:
            pattern = 'consistent'
        
        return {
            'pattern': pattern,
            'average_requests_per_hour': round(avg_usage, 2),
            'peak_hourly_requests': peak_usage,
            'peak_to_avg_ratio': round(peak_ratio, 2)
        }
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired rate limiting data"""
        try:
            current_time = time.time()
            cleanup_count = 0
            
            # Clean up expired sliding windows
            expired_keys = []
            for key, window in self._sliding_windows.items():
                # Remove windows older than their window size
                if hasattr(window, 'requests') and window.requests:
                    oldest_request = window.requests[0]
                    if current_time - oldest_request > window.window_seconds * 2:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self._sliding_windows[key]
                cleanup_count += 1
            
            # Clean up old violation logs
            violation_pattern = f"{self.config['redis_namespace']}:violations:*"
            # This would need to be implemented with SCAN command in real Redis
            
            logger.info(f"Cleaned up {cleanup_count} expired rate limiting entries")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        # Clear all algorithm instances
        self._token_buckets.clear()
        self._sliding_windows.clear()
        self._fixed_windows.clear()
        self._leaky_buckets.clear()
        self._adaptive_limiters.clear()
        
        logger.info("RateLimiter closed")