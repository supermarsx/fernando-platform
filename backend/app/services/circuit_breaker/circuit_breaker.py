"""
Circuit Breaker Service

Implements the circuit breaker pattern for external service calls to prevent
cascading failures. Provides configurable failure thresholds, automatic recovery,
and multiple failure detection strategies with comprehensive monitoring.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from collections import deque, defaultdict
from enum import Enum
from dataclasses import dataclass, field
import json
import statistics

from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open" # Testing if service recovered

class FailureType(Enum):
    """Types of failures"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_5XX = "http_5xx"
    HTTP_4XX = "http_4xx"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMITED = "rate_limited"
    CUSTOM = "custom"

class RecoveryStrategy(Enum):
    """Recovery strategies"""
    IMMEDIATE = "immediate"      # Open -> Half-open immediately
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Increasing wait times
    FIXED_TIMEOUT = "fixed_timeout"  # Fixed timeout before trying
    ADAPTIVE = "adaptive"        # Based on service health

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Number of failures to open circuit
    success_threshold: int = 3          # Number of successes to close circuit from half-open
    timeout_seconds: float = 60.0       # Timeout for requests
    recovery_timeout_seconds: float = 60.0  # Time to wait before trying half-open
    rolling_window_seconds: int = 60    # Time window for failure counting
    max_concurrent_requests: int = 100  # Maximum concurrent requests
    failure_rate_threshold: float = 0.5  # Failure rate threshold (50%)
    avg_response_time_threshold: float = 5000.0  # Average response time threshold (ms)
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
    min_recovery_timeout: float = 10.0   # Minimum recovery timeout
    max_recovery_timeout: float = 300.0  # Maximum recovery timeout
    backoff_multiplier: float = 1.5      # Exponential backoff multiplier
    health_check_enabled: bool = True    # Enable health checks
    custom_failure_detector: Optional[Callable] = None  # Custom failure detection
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RequestMetrics:
    """Request metrics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    total_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    service_name: str
    current_state: CircuitBreakerState
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time: float
    current_concurrent_requests: int
    last_failure_time: Optional[datetime]
    next_recovery_attempt: Optional[datetime]
    state_duration_seconds: float

class ServiceEndpoint:
    """Represents a service endpoint for circuit breaking"""
    
    def __init__(self, name: str, url: str, config: CircuitBreakerConfig):
        self.name = name
        self.url = url
        self.config = config
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.state_change_time = datetime.now(timezone.utc)
        self.failure_count = 0
        self.success_count = 0
        self.recovery_attempt_count = 0
        
        # Metrics tracking
        self.metrics = RequestMetrics()
        
        # Request tracking for sliding window
        self.request_history = deque(maxlen=1000)  # Keep last 1000 requests
        
        # Recent failures for analysis
        self.recent_failures = deque(maxlen=100)  # Keep last 100 failures
        
        # Concurrency tracking
        self.current_concurrent = 0
        self.max_concurrent_reached = 0
        
        logger.info(f"Created circuit breaker for service: {name}")

class CircuitBreaker:
    """
    Comprehensive Circuit Breaker Service
    
    Implements the circuit breaker pattern with:
    - Multiple failure detection strategies
    - Configurable recovery mechanisms
    - Real-time monitoring and metrics
    - Health-based adaptive thresholds
    - Request timeout and concurrency control
    - Automatic and manual state management
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Service endpoints
        self._endpoints: Dict[str, ServiceEndpoint] = {}
        
        # Global statistics
        self._global_stats = {
            'total_services': 0,
            'services_by_state': defaultdict(int),
            'total_requests': 0,
            'total_failures': 0,
            'circuit_activations': 0
        }
        
        # Configuration
        self.config = {
            'default_config': CircuitBreakerConfig(),
            'health_check_interval': 30,  # seconds
            'stats_collection_interval': 60,  # seconds
            'cleanup_interval': 300,  # 5 minutes
            'redis_namespace': 'circuit_breaker',
            'max_state_history': 100
        }
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._stats_collection_task: Optional[asyncio.Task] = None
        
        logger.info("CircuitBreaker initialized")
    
    async def register_service(
        self,
        service_name: str,
        service_url: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> bool:
        """Register a service for circuit breaking"""
        try:
            if config is None:
                config = self.config['default_config']
            
            endpoint = ServiceEndpoint(service_name, service_url, config)
            self._endpoints[service_name] = endpoint
            
            # Update global statistics
            self._global_stats['total_services'] += 1
            self._global_stats['services_by_state'][endpoint.state.value] += 1
            
            logger.info(f"Registered service: {service_name} with circuit breaker")
            
            # Track registration
            await self.event_tracker.track_event(
                "circuit_breaker_service_registered",
                {
                    "service_name": service_name,
                    "service_url": service_url,
                    "failure_threshold": config.failure_threshold,
                    "timeout_seconds": config.timeout_seconds
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    async def unregister_service(self, service_name: str) -> bool:
        """Unregister a service from circuit breaking"""
        try:
            if service_name not in self._endpoints:
                return False
            
            endpoint = self._endpoints[service_name]
            del self._endpoints[service_name]
            
            # Update global statistics
            self._global_stats['total_services'] -= 1
            self._global_stats['services_by_state'][endpoint.state.value] -= 1
            
            logger.info(f"Unregistered service: {service_name}")
            
            # Track unregistration
            await self.event_tracker.track_event(
                "circuit_breaker_service_unregistered",
                {"service_name": service_name}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister service {service_name}: {e}")
            return False
    
    async def call_service(
        self,
        service_name: str,
        operation: Callable,
        *args,
        fallback: Optional[Callable] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Execute service operation with circuit breaker protection
        
        Args:
            service_name: Name of registered service
            operation: Function to execute
            *args: Arguments for operation
            fallback: Fallback function if operation fails
            timeout: Custom timeout for this call
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result from operation or fallback
        """
        if service_name not in self._endpoints:
            logger.warning(f"Service {service_name} not registered, executing without circuit breaker")
            return await operation(*args, **kwargs)
        
        endpoint = self._endpoints[service_name]
        
        # Check if circuit is open
        if endpoint.state == CircuitBreakerState.OPEN:
            # Check if we should attempt recovery
            if await self._should_attempt_recovery(endpoint):
                await self._transition_to_half_open(endpoint)
            else:
                return await self._handle_open_circuit(endpoint, operation, args, kwargs)
        
        # Execute operation with circuit breaker protection
        return await self._execute_with_protection(endpoint, operation, args, kwargs, timeout, fallback)
    
    async def _execute_with_protection(
        self,
        endpoint: ServiceEndpoint,
        operation: Callable,
        args: Tuple,
        kwargs: Dict,
        timeout: Optional[float],
        fallback: Optional[Callable]
    ) -> Any:
        """Execute operation with circuit breaker protection"""
        start_time = time.time()
        request_timeout = timeout or endpoint.config.timeout_seconds
        
        try:
            # Check concurrency limit
            if endpoint.current_concurrent >= endpoint.config.max_concurrent_requests:
                logger.warning(f"Concurrency limit reached for {endpoint.name}")
                await self._record_failure(endpoint, FailureType.SERVICE_UNAVAILABLE, "Concurrency limit exceeded")
                
                if fallback:
                    return await self._execute_fallback(fallback, args, kwargs)
                else:
                    raise Exception("Service concurrency limit exceeded")
            
            # Increment concurrent request counter
            endpoint.current_concurrent += 1
            endpoint.max_concurrent_reached = max(endpoint.max_concurrent_reached, endpoint.current_concurrent)
            
            try:
                # Execute operation with timeout
                result = await asyncio.wait_for(operation(*args, **kwargs), timeout=request_timeout)
                
                # Record success
                await self._record_success(endpoint, time.time() - start_time)
                
                return result
                
            except asyncio.TimeoutError:
                # Handle timeout
                await self._record_failure(endpoint, FailureType.TIMEOUT, f"Request timeout after {request_timeout}s")
                
                if fallback:
                    return await self._execute_fallback(fallback, args, kwargs)
                else:
                    raise
                    
            except Exception as e:
                # Determine failure type
                failure_type = await self._classify_failure(e, endpoint)
                await self._record_failure(endpoint, failure_type, str(e))
                
                if fallback:
                    return await self._execute_fallback(fallback, args, kwargs)
                else:
                    raise
                    
        finally:
            # Decrement concurrent request counter
            endpoint.current_concurrent = max(0, endpoint.current_concurrent - 1)
    
    async def _handle_open_circuit(
        self,
        endpoint: ServiceEndpoint,
        operation: Callable,
        args: Tuple,
        kwargs: Dict
    ) -> Any:
        """Handle requests when circuit is open"""
        # Check if we have a fallback
        # In a real implementation, this might check for cached responses or fallback services
        
        logger.warning(f"Circuit is open for service {endpoint.name}, rejecting request")
        
        # Record the attempt to call an open circuit
        await self.event_tracker.track_event(
            "circuit_breaker_request_rejected",
            {
                "service_name": endpoint.name,
                "current_state": endpoint.state.value,
                "failure_count": endpoint.failure_count
            }
        )
        
        raise Exception(f"Circuit breaker is open for service {endpoint.name}")
    
    async def _should_attempt_recovery(self, endpoint: ServiceEndpoint) -> bool:
        """Determine if we should attempt to recover the circuit"""
        time_since_open = (datetime.now(timezone.utc) - endpoint.state_change_time).total_seconds()
        
        if endpoint.config.recovery_strategy == RecoveryStrategy.IMMEDIATE:
            return time_since_open > 1  # Small delay to avoid thrashing
        
        elif endpoint.config.recovery_strategy == RecoveryStrategy.FIXED_TIMEOUT:
            return time_since_open >= endpoint.config.recovery_timeout_seconds
        
        elif endpoint.config.recovery_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            # Calculate exponential backoff
            backoff_time = endpoint.config.min_recovery_timeout * (
                endpoint.config.backoff_multiplier ** endpoint.recovery_attempt_count
            )
            backoff_time = min(backoff_time, endpoint.config.max_recovery_timeout)
            
            return time_since_open >= backoff_time
        
        elif endpoint.config.recovery_strategy == RecoveryStrategy.ADAPTIVE:
            # Adaptive recovery based on service health
            health_score = await self._calculate_service_health(endpoint)
            return health_score > 0.7 and time_since_open > endpoint.config.min_recovery_timeout
        
        return False
    
    async def _transition_to_half_open(self, endpoint: ServiceEndpoint) -> None:
        """Transition circuit from open to half-open state"""
        old_state = endpoint.state
        endpoint.state = CircuitBreakerState.HALF_OPEN
        endpoint.state_change_time = datetime.now(timezone.utc)
        endpoint.recovery_attempt_count += 1
        
        # Record state change
        state_change = {
            'from_state': old_state.value,
            'to_state': endpoint.state.value,
            'timestamp': endpoint.state_change_time.isoformat(),
            'reason': 'recovery_attempt'
        }
        endpoint.metrics.state_changes.append(state_change)
        
        # Update global statistics
        self._global_stats['services_by_state'][old_state.value] -= 1
        self._global_stats['services_by_state'][endpoint.state.value] += 1
        
        # Reset counters for half-open state
        endpoint.success_count = 0
        endpoint.failure_count = 0
        
        logger.info(f"Circuit transitioned from {old_state.value} to {endpoint.state.value} for service {endpoint.name}")
        
        await self.event_tracker.track_event(
            "circuit_breaker_state_change",
            {
                "service_name": endpoint.name,
                "from_state": old_state.value,
                "to_state": endpoint.state.value,
                "recovery_attempt": endpoint.recovery_attempt_count
            }
        )
    
    async def _record_success(self, endpoint: ServiceEndpoint, response_time: float) -> None:
        """Record successful request"""
        current_time = datetime.now(timezone.utc)
        
        # Update metrics
        endpoint.metrics.total_requests += 1
        endpoint.metrics.successful_requests += 1
        endpoint.metrics.total_response_time += response_time
        endpoint.metrics.last_request_time = current_time
        endpoint.metrics.last_success_time = current_time
        endpoint.metrics.consecutive_failures = 0
        endpoint.metrics.consecutive_successes += 1
        
        # Update endpoint-level counters
        endpoint.success_count += 1
        endpoint.failure_count = 0  # Reset failure count on success
        
        # Add to request history
        endpoint.request_history.append({
            'timestamp': current_time,
            'success': True,
            'response_time': response_time
        })
        
        # Check state transitions
        if endpoint.state == CircuitBreakerState.HALF_OPEN:
            if endpoint.success_count >= endpoint.config.success_threshold:
                await self._transition_to_closed(endpoint)
        elif endpoint.state == CircuitBreakerState.CLOSED:
            # In closed state, reset failure tracking based on rolling window
            await self._update_failure_window(endpoint, current_time)
        
        # Track success
        await self.event_tracker.track_event(
            "circuit_breaker_request_success",
            {
                "service_name": endpoint.name,
                "response_time": response_time,
                "current_state": endpoint.state.value
            }
        )
    
    async def _record_failure(
        self,
        endpoint: ServiceEndpoint,
        failure_type: FailureType,
        error_message: str
    ) -> None:
        """Record failed request"""
        current_time = datetime.now(timezone.utc)
        
        # Update metrics
        endpoint.metrics.total_requests += 1
        endpoint.metrics.failed_requests += 1
        endpoint.metrics.last_request_time = current_time
        endpoint.metrics.last_failure_time = current_time
        endpoint.metrics.consecutive_failures += 1
        endpoint.metrics.consecutive_successes = 0
        
        # Update endpoint-level counters
        endpoint.failure_count += 1
        endpoint.success_count = 0  # Reset success count on failure
        
        # Add to request history and failure tracking
        endpoint.request_history.append({
            'timestamp': current_time,
            'success': False,
            'failure_type': failure_type.value,
            'error_message': error_message[:200]  # Truncate long error messages
        })
        
        endpoint.recent_failures.append({
            'timestamp': current_time,
            'failure_type': failure_type.value,
            'error_message': error_message
        })
        
        # Check if circuit should open
        should_open = await self._should_open_circuit(endpoint, current_time)
        
        if should_open and endpoint.state != CircuitBreakerState.OPEN:
            await self._transition_to_open(endpoint, failure_type, error_message)
        
        # Track failure
        await self.event_tracker.track_event(
            "circuit_breaker_request_failure",
            {
                "service_name": endpoint.name,
                "failure_type": failure_type.value,
                "error_message": error_message[:100],
                "current_state": endpoint.state.value,
                "consecutive_failures": endpoint.metrics.consecutive_failures
            }
        )
    
    async def _should_open_circuit(self, endpoint: ServiceEndpoint, current_time: datetime) -> bool:
        """Determine if circuit should be opened based on failures"""
        # Check consecutive failure threshold
        if endpoint.metrics.consecutive_failures >= endpoint.config.failure_threshold:
            logger.info(f"Opening circuit for {endpoint.name} due to consecutive failures: {endpoint.metrics.consecutive_failures}")
            return True
        
        # Check failure rate in rolling window
        failures_in_window = await self._count_failures_in_window(endpoint, current_time)
        requests_in_window = await self._count_requests_in_window(endpoint, current_time)
        
        if requests_in_window >= 5:  # Need minimum sample size
            failure_rate = failures_in_window / requests_in_window
            if failure_rate >= endpoint.config.failure_rate_threshold:
                logger.info(f"Opening circuit for {endpoint.name} due to high failure rate: {failure_rate:.2%}")
                return True
        
        # Check average response time threshold
        if endpoint.metrics.total_requests > 0:
            avg_response_time = endpoint.metrics.total_response_time / endpoint.metrics.total_requests
            if avg_response_time >= endpoint.config.avg_response_time_threshold:
                logger.info(f"Opening circuit for {endpoint.name} due to slow response time: {avg_response_time:.2f}ms")
                return True
        
        return False
    
    async def _transition_to_open(
        self,
        endpoint: ServiceEndpoint,
        failure_type: FailureType,
        error_message: str
    ) -> None:
        """Transition circuit to open state"""
        old_state = endpoint.state
        endpoint.state = CircuitBreakerState.OPEN
        endpoint.state_change_time = datetime.now(timezone.utc)
        
        # Record state change
        state_change = {
            'from_state': old_state.value,
            'to_state': endpoint.state.value,
            'timestamp': endpoint.state_change_time.isoformat(),
            'reason': f'failure_threshold_exceeded_{failure_type.value}',
            'failure_message': error_message[:200]
        }
        endpoint.metrics.state_changes.append(state_change)
        
        # Update global statistics
        self._global_stats['services_by_state'][old_state.value] -= 1
        self._global_stats['services_by_state'][endpoint.state.value] += 1
        self._global_stats['circuit_activations'] += 1
        
        # Calculate next recovery attempt time
        if endpoint.config.recovery_strategy == RecoveryStrategy.FIXED_TIMEOUT:
            next_attempt = endpoint.state_change_time + timedelta(seconds=endpoint.config.recovery_timeout_seconds)
        else:
            # For other strategies, calculate based on exponential backoff
            backoff_time = endpoint.config.min_recovery_timeout * (
                endpoint.config.backoff_multiplier ** endpoint.recovery_attempt_count
            )
            backoff_time = min(backoff_time, endpoint.config.max_recovery_timeout)
            next_attempt = endpoint.state_change_time + timedelta(seconds=backoff_time)
        
        endpoint.recovery_attempt_count = 0  # Reset for next cycle
        
        logger.warning(f"Circuit opened for service {endpoint.name} due to {failure_type.value}: {error_message}")
        
        await self.event_tracker.track_event(
            "circuit_breaker_state_change",
            {
                "service_name": endpoint.name,
                "from_state": old_state.value,
                "to_state": endpoint.state.value,
                "trigger": f"{failure_type.value}: {error_message[:100]}",
                "failure_count": endpoint.metrics.consecutive_failures
            }
        )
    
    async def _transition_to_closed(self, endpoint: ServiceEndpoint) -> None:
        """Transition circuit to closed state"""
        old_state = endpoint.state
        endpoint.state = CircuitBreakerState.CLOSED
        endpoint.state_change_time = datetime.now(timezone.utc)
        
        # Record state change
        state_change = {
            'from_state': old_state.value,
            'to_state': endpoint.state.value,
            'timestamp': endpoint.state_change_time.isoformat(),
            'reason': 'success_threshold_recovered'
        }
        endpoint.metrics.state_changes.append(state_change)
        
        # Update global statistics
        self._global_stats['services_by_state'][old_state.value] -= 1
        self._global_stats['services_by_state'][endpoint.state.value] += 1
        
        # Reset failure tracking
        endpoint.metrics.consecutive_failures = 0
        endpoint.metrics.consecutive_successes = 0
        
        logger.info(f"Circuit closed for service {endpoint.name} - service recovered")
        
        await self.event_tracker.track_event(
            "circuit_breaker_state_change",
            {
                "service_name": endpoint.name,
                "from_state": old_state.value,
                "to_state": endpoint.state.value,
                "recovery_successful": True
            }
        )
    
    async def _calculate_service_health(self, endpoint: ServiceEndpoint) -> float:
        """Calculate service health score (0.0 to 1.0)"""
        try:
            # Check recent performance
            recent_requests = list(endpoint.request_history)[-20:]  # Last 20 requests
            if not recent_requests:
                return 0.5
            
            # Calculate success rate
            recent_successes = sum(1 for req in recent_requests if req.get('success', False))
            success_rate = recent_successes / len(recent_requests)
            
            # Calculate average response time
            response_times = [req.get('response_time', 0) for req in recent_requests if req.get('response_time')]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Health score components
            success_score = success_rate
            response_time_score = max(0, 1 - (avg_response_time / (endpoint.config.avg_response_time_threshold * 2)))
            
            # Weighted health score
            health_score = (success_score * 0.7) + (response_time_score * 0.3)
            
            return max(0, min(1, health_score))
            
        except Exception as e:
            logger.error(f"Error calculating service health for {endpoint.name}: {e}")
            return 0.0
    
    async def _count_failures_in_window(
        self,
        endpoint: ServiceEndpoint,
        current_time: datetime
    ) -> int:
        """Count failures within the rolling window"""
        window_start = current_time - timedelta(seconds=endpoint.config.rolling_window_seconds)
        
        failures = 0
        for req in endpoint.request_history:
            req_time = req.get('timestamp')
            if req_time and req_time >= window_start:
                if not req.get('success', True):  # Default to True for backward compatibility
                    failures += 1
        
        return failures
    
    async def _count_requests_in_window(
        self,
        endpoint: ServiceEndpoint,
        current_time: datetime
    ) -> int:
        """Count total requests within the rolling window"""
        window_start = current_time - timedelta(seconds=endpoint.config.rolling_window_seconds)
        
        count = 0
        for req in endpoint.request_history:
            req_time = req.get('timestamp')
            if req_time and req_time >= window_start:
                count += 1
        
        return count
    
    async def _update_failure_window(
        self,
        endpoint: ServiceEndpoint,
        current_time: datetime
    ) -> None:
        """Update failure tracking for closed state"""
        # Remove old requests outside the rolling window
        window_start = current_time - timedelta(seconds=endpoint.config.rolling_window_seconds)
        
        # Keep only recent requests
        recent_requests = [
            req for req in endpoint.request_history
            if req.get('timestamp', current_time) >= window_start
        ]
        
        # Update request history
        endpoint.request_history.clear()
        endpoint.request_history.extend(recent_requests)
        
        # Update failure metrics based on window
        failures_in_window = await self._count_failures_in_window(endpoint, current_time)
        requests_in_window = await self._count_requests_in_window(endpoint, current_time)
        
        # Reset failure count if within threshold
        if requests_in_window > 0:
            failure_rate = failures_in_window / requests_in_window
            if failure_rate < endpoint.config.failure_rate_threshold * 0.5:  # Recovery threshold
                endpoint.metrics.consecutive_failures = max(0, endpoint.metrics.consecutive_failures - 1)
    
    async def _classify_failure(self, error: Exception, endpoint: ServiceEndpoint) -> FailureType:
        """Classify the type of failure"""
        error_message = str(error).lower()
        
        # Custom failure detector
        if endpoint.config.custom_failure_detector:
            try:
                custom_result = endpoint.config.custom_failure_detector(error, endpoint)
                if custom_result:
                    return custom_result
            except Exception as e:
                logger.error(f"Custom failure detector failed for {endpoint.name}: {e}")
        
        # Standard failure classification
        if "timeout" in error_message:
            return FailureType.TIMEOUT
        elif "connection" in error_message or "network" in error_message:
            return FailureType.CONNECTION_ERROR
        elif "500" in error_message or "502" in error_message or "503" in error_message:
            return FailureType.HTTP_5XX
        elif "429" in error_message or "rate limit" in error_message:
            return FailureType.RATE_LIMITED
        elif "404" in error_message or "400" in error_message or "403" in error_message:
            return FailureType.HTTP_4XX
        elif "unavailable" in error_message or "unreachable" in error_message:
            return FailureType.SERVICE_UNAVAILABLE
        else:
            return FailureType.CUSTOM
    
    async def _execute_fallback(self, fallback: Callable, args: Tuple, kwargs: Dict) -> Any:
        """Execute fallback function"""
        try:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback(*args, **kwargs)
            else:
                return fallback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            raise
    
    async def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed status for a service"""
        if service_name not in self._endpoints:
            return {'error': f'Service {service_name} not registered'}
        
        endpoint = self._endpoints[service_name]
        current_time = datetime.now(timezone.utc)
        
        # Calculate metrics
        total_requests = endpoint.metrics.total_requests
        success_rate = (endpoint.metrics.successful_requests / max(1, total_requests)) * 100
        avg_response_time = endpoint.metrics.total_response_time / max(1, total_requests)
        
        # Get health score
        health_score = await self._calculate_service_health(endpoint)
        
        # Calculate state duration
        state_duration = (current_time - endpoint.state_change_time).total_seconds()
        
        # Get recent failure analysis
        recent_failures = list(endpoint.recent_failures)[-10:]  # Last 10 failures
        failure_types = defaultdict(int)
        for failure in recent_failures:
            failure_types[failure.get('failure_type', 'unknown')] += 1
        
        status = {
            'service_name': service_name,
            'service_url': endpoint.url,
            'timestamp': current_time.isoformat(),
            'circuit_state': {
                'current_state': endpoint.state.value,
                'state_duration_seconds': round(state_duration, 2),
                'state_changes_count': len(endpoint.metrics.state_changes),
                'recent_state_changes': endpoint.metrics.state_changes[-5:] if endpoint.metrics.state_changes else []
            },
            'metrics': {
                'total_requests': total_requests,
                'successful_requests': endpoint.metrics.successful_requests,
                'failed_requests': endpoint.metrics.failed_requests,
                'success_rate_percent': round(success_rate, 2),
                'avg_response_time_ms': round(avg_response_time * 1000, 2),
                'concurrent_requests': endpoint.current_concurrent,
                'max_concurrent_reached': endpoint.max_concurrent_reached,
                'consecutive_failures': endpoint.metrics.consecutive_failures,
                'consecutive_successes': endpoint.metrics.consecutive_successes
            },
            'health': {
                'health_score': round(health_score, 3),
                'health_status': 'healthy' if health_score > 0.7 else 'degraded' if health_score > 0.4 else 'unhealthy',
                'last_success': endpoint.metrics.last_success_time.isoformat() if endpoint.metrics.last_success_time else None,
                'last_failure': endpoint.metrics.last_failure_time.isoformat() if endpoint.metrics.last_failure_time else None
            },
            'configuration': {
                'failure_threshold': endpoint.config.failure_threshold,
                'success_threshold': endpoint.config.success_threshold,
                'timeout_seconds': endpoint.config.timeout_seconds,
                'failure_rate_threshold': endpoint.config.failure_rate_threshold,
                'max_concurrent_requests': endpoint.config.max_concurrent_requests,
                'recovery_strategy': endpoint.config.recovery_strategy.value
            },
            'failure_analysis': {
                'failure_types_distribution': dict(failure_types),
                'recent_failures_count': len(recent_failures)
            }
        }
        
        return status
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global circuit breaker statistics"""
        current_time = datetime.now(timezone.utc)
        
        # Aggregate statistics
        total_requests = sum(endpoint.metrics.total_requests for endpoint in self._endpoints.values())
        total_failures = sum(endpoint.metrics.failed_requests for endpoint in self._endpoints.values())
        total_services = len(self._endpoints)
        
        # Service distribution by state
        services_by_state = defaultdict(int)
        for endpoint in self._endpoints.values():
            services_by_state[endpoint.state.value] += 1
        
        # Calculate averages
        avg_success_rate = 0
        avg_response_time = 0
        healthy_services = 0
        
        if self._endpoints:
            success_rates = []
            response_times = []
            
            for endpoint in self._endpoints.values():
                if endpoint.metrics.total_requests > 0:
                    success_rate = (endpoint.metrics.successful_requests / endpoint.metrics.total_requests) * 100
                    success_rates.append(success_rate)
                    
                    avg_resp_time = endpoint.metrics.total_response_time / endpoint.metrics.total_requests * 1000
                    response_times.append(avg_resp_time)
                
                # Count healthy services
                health_score = await self._calculate_service_health(endpoint)
                if health_score > 0.7:
                    healthy_services += 1
            
            if success_rates:
                avg_success_rate = statistics.mean(success_rates)
            if response_times:
                avg_response_time = statistics.mean(response_times)
        
        return {
            'timestamp': current_time.isoformat(),
            'overview': {
                'total_services': total_services,
                'healthy_services': healthy_services,
                'services_by_state': dict(services_by_state),
                'total_requests': total_requests,
                'total_failures': total_failures,
                'overall_success_rate_percent': round((total_requests - total_failures) / max(1, total_requests) * 100, 2),
                'circuit_activations': self._global_stats['circuit_activations']
            },
            'performance': {
                'avg_success_rate_percent': round(avg_success_rate, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'healthy_services_ratio': round(healthy_services / max(1, total_services), 3)
            },
            'services': [
                {
                    'name': endpoint.name,
                    'state': endpoint.state.value,
                    'total_requests': endpoint.metrics.total_requests,
                    'success_rate_percent': round((endpoint.metrics.successful_requests / max(1, endpoint.metrics.total_requests)) * 100, 2),
                    'concurrent_requests': endpoint.current_concurrent
                }
                for endpoint in self._endpoints.values()
            ]
        }
    
    async def manual_state_change(
        self,
        service_name: str,
        new_state: CircuitBreakerState,
        reason: str = "manual_change"
    ) -> bool:
        """Manually change circuit breaker state"""
        if service_name not in self._endpoints:
            return False
        
        endpoint = self._endpoints[service_name]
        old_state = endpoint.state
        
        if old_state == new_state:
            return True
        
        # Apply state change
        if new_state == CircuitBreakerState.OPEN:
            await self._transition_to_open(endpoint, FailureType.CUSTOM, f"Manual: {reason}")
        elif new_state == CircuitBreakerState.CLOSED:
            await self._transition_to_closed(endpoint)
        elif new_state == CircuitBreakerState.HALF_OPEN:
            endpoint.state = CircuitBreakerState.HALF_OPEN
            endpoint.state_change_time = datetime.now(timezone.utc)
        
        logger.info(f"Manually changed circuit state for {service_name} from {old_state.value} to {new_state.value}: {reason}")
        
        await self.event_tracker.track_event(
            "circuit_breaker_manual_state_change",
            {
                "service_name": service_name,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "reason": reason
            }
        )
        
        return True
    
    async def reset_service(self, service_name: str) -> bool:
        """Reset all counters and state for a service"""
        if service_name not in self._endpoints:
            return False
        
        endpoint = self._endpoints[service_name]
        
        # Reset all metrics and counters
        endpoint.state = CircuitBreakerState.CLOSED
        endpoint.state_change_time = datetime.now(timezone.utc)
        endpoint.failure_count = 0
        endpoint.success_count = 0
        endpoint.recovery_attempt_count = 0
        
        # Reset metrics
        endpoint.metrics = RequestMetrics()
        endpoint.request_history.clear()
        endpoint.recent_failures.clear()
        endpoint.current_concurrent = 0
        endpoint.max_concurrent_reached = 0
        
        logger.info(f"Reset circuit breaker for service: {service_name}")
        
        await self.event_tracker.track_event(
            "circuit_breaker_service_reset",
            {"service_name": service_name}
        )
        
        return True
    
    async def start_background_tasks(self) -> None:
        """Start background health check and stats collection tasks"""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._stats_collection_task = asyncio.create_task(self._stats_collection_loop())
        
        logger.info("Started background circuit breaker tasks")
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._stats_collection_task:
            self._stats_collection_task.cancel()
            try:
                await self._stats_collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped background circuit breaker tasks")
    
    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.config['health_check_interval'])
                
                for endpoint in self._endpoints.values():
                    if endpoint.config.health_check_enabled and endpoint.state != CircuitBreakerState.OPEN:
                        await self._perform_health_check(endpoint)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _stats_collection_loop(self) -> None:
        """Background statistics collection loop"""
        while True:
            try:
                await asyncio.sleep(self.config['stats_collection_interval'])
                
                # Update global statistics
                total_requests = sum(endpoint.metrics.total_requests for endpoint in self._endpoints.values())
                total_failures = sum(endpoint.metrics.failed_requests for endpoint in self._endpoints.values())
                
                self._global_stats['total_requests'] = total_requests
                self._global_stats['total_failures'] = total_failures
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stats collection loop: {e}")
    
    async def _perform_health_check(self, endpoint: ServiceEndpoint) -> None:
        """Perform health check on service endpoint"""
        try:
            # Simple health check - make a lightweight request
            # In real implementation, this would make an actual health check request
            
            # For now, just log the health check
            health_score = await self._calculate_service_health(endpoint)
            
            if endpoint.state == CircuitBreakerState.HALF_OPEN and health_score > 0.8:
                # In half-open state, successful health checks help close the circuit
                endpoint.success_count += 1
                if endpoint.success_count >= endpoint.config.success_threshold:
                    await self._transition_to_closed(endpoint)
            
        except Exception as e:
            logger.error(f"Health check failed for {endpoint.name}: {e}")
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired data"""
        try:
            cleanup_count = 0
            current_time = datetime.now(timezone.utc)
            
            for endpoint in self._endpoints.values():
                # Clean up old state changes
                if len(endpoint.metrics.state_changes) > self.config['max_state_history']:
                    endpoint.metrics.state_changes = endpoint.metrics.state_changes[-self.config['max_state_history']:]
                    cleanup_count += 1
                
                # Clean up old request history (keep recent)
                cutoff_time = current_time - timedelta(hours=24)  # Keep 24 hours
                endpoint.request_history = deque([
                    req for req in endpoint.request_history
                    if req.get('timestamp', current_time) >= cutoff_time
                ], maxlen=1000)
                
                # Clean up old failure records
                if len(endpoint.recent_failures) > 50:
                    endpoint.recent_failures = deque(
                        list(endpoint.recent_failures)[-50:],
                        maxlen=100
                    )
                    cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired circuit breaker entries")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        await self.stop_background_tasks()
        
        # Clear all data
        self._endpoints.clear()
        
        logger.info("CircuitBreaker closed")