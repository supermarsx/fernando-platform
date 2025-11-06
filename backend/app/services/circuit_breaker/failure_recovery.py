"""
Failure Recovery Service

Provides automatic failure recovery and fallback strategies for the proxy system.
Implements intelligent service restoration, failover mechanisms, degraded mode
operation, and comprehensive recovery workflows.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
import json
import random
import statistics

from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Recovery strategies"""
    IMMEDIATE = "immediate"
    GRADUAL = "gradual"
    CANARY = "canary"
    LOAD_BALANCED = "load_balanced"
    ADAPTIVE = "adaptive"
    ROLLING = "rolling"

class FailureLevel(Enum):
    """Failure severity levels"""
    LOW = "low"         # Minor issues, minor impact
    MEDIUM = "medium"   # Significant issues, moderate impact
    HIGH = "high"       # Major issues, high impact
    CRITICAL = "critical"  # Complete failure, severe impact

class RecoveryStatus(Enum):
    """Recovery process status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    TIMEOUT = "timeout"

class FallbackType(Enum):
    """Types of fallback mechanisms"""
    CACHE = "cache"
    CACHED_RESPONSE = "cached_response"
    ALTERNATIVE_SERVICE = "alternative_service"
    DEGRADED_MODE = "degraded_mode"
    STATIC_RESPONSE = "static_response"
    QUEUE_REQUEST = "queue_request"

@dataclass
class RecoveryConfig:
    """Recovery configuration"""
    max_recovery_attempts: int = 3
    recovery_timeout_seconds: float = 300.0
    gradual_recovery_interval: float = 10.0
    canary_traffic_percentage: float = 0.05  # 5%
    success_threshold_percentage: float = 0.95  # 95%
    failure_threshold_percentage: float = 0.10  # 10%
    circuit_breaker_reset_delay: float = 30.0
    health_check_interval: float = 5.0
    max_concurrent_recoveries: int = 5
    retry_backoff_factor: float = 2.0
    enable_canary_recovery: bool = True
    enable_gradual_recovery: bool = True
    enable_fallback: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FallbackConfig:
    """Fallback mechanism configuration"""
    fallback_type: FallbackType
    priority: int  # Lower numbers = higher priority
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000
    alternative_service_urls: List[str] = field(default_factory=list)
    static_response_data: Optional[str] = None
    failure_level_threshold: FailureLevel = FailureLevel.MEDIUM
    cooldown_seconds: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RecoveryAttempt:
    """Recovery attempt tracking"""
    id: str
    service_name: str
    strategy: RecoveryStrategy
    start_time: datetime
    end_time: Optional[datetime] = None
    status: RecoveryStatus = RecoveryStatus.NOT_STARTED
    attempts_made: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_operations: int = 0
    recovery_percentage: float = 0.0
    error_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceRecoveryState:
    """Service recovery state management"""
    service_name: str
    current_recovery: Optional[RecoveryAttempt] = None
    last_recovery_time: Optional[datetime] = None
    recovery_history: List[RecoveryAttempt] = field(default_factory=list)
    active_fallbacks: Dict[str, FallbackConfig] = field(default_factory=dict)
    service_health_score: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FailureEvent:
    """Failure event tracking"""
    id: str
    service_name: str
    failure_level: FailureLevel
    failure_type: str
    error_message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempt_id: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class FallbackHandler:
    """Handles fallback mechanisms for failed operations"""
    
    def __init__(self, service_name: str, configs: List[FallbackConfig]):
        self.service_name = service_name
        self.configs = sorted(configs, key=lambda x: x.priority)
        self.fallback_cache = {}
        self.last_fallback_usage = defaultdict(datetime)
        
    async def execute_fallback(
        self,
        failure_context: Dict[str, Any],
        operation_type: str,
        original_request: Any
    ) -> Any:
        """Execute appropriate fallback mechanism"""
        for config in self.configs:
            if not config.enabled:
                continue
            
            # Check cooldown
            if self._is_in_cooldown(config):
                continue
            
            # Check conditions
            if not self._check_conditions(config, failure_context):
                continue
            
            try:
                if config.fallback_type == FallbackType.CACHE:
                    return await self._handle_cache_fallback(config, operation_type, original_request)
                elif config.fallback_type == FallbackType.CACHED_RESPONSE:
                    return await self._handle_cached_response_fallback(config, operation_type)
                elif config.fallback_type == FallbackType.ALTERNATIVE_SERVICE:
                    return await self._handle_alternative_service_fallback(config, original_request)
                elif config.fallback_type == FallbackType.DEGRADED_MODE:
                    return await self._handle_degraded_mode_fallback(config, operation_type, original_request)
                elif config.fallback_type == FallbackType.STATIC_RESPONSE:
                    return await self._handle_static_response_fallback(config, operation_type)
                elif config.fallback_type == FallbackType.QUEUE_REQUEST:
                    return await self._handle_queued_request_fallback(config, operation_type, original_request)
                    
            except Exception as e:
                logger.error(f"Fallback execution failed for {config.fallback_type.value}: {e}")
                continue
        
        # No fallback succeeded
        raise Exception(f"No fallback available for {self.service_name}")
    
    def _is_in_cooldown(self, config: FallbackConfig) -> bool:
        """Check if fallback is in cooldown period"""
        last_usage = self.last_fallback_usage.get(config.fallback_type.value)
        if last_usage:
            cooldown_elapsed = (datetime.now(timezone.utc) - last_usage).total_seconds()
            return cooldown_elapsed < config.cooldown_seconds
        return False
    
    def _check_conditions(self, config: FallbackConfig, context: Dict[str, Any]) -> bool:
        """Check if fallback conditions are met"""
        conditions = config.conditions
        
        # Check failure level threshold
        failure_level = context.get('failure_level', FailureLevel.MEDIUM)
        if hasattr(failure_level, 'value'):
            failure_level = failure_level.value
        
        level_hierarchy = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        required_level = level_hierarchy.get(config.failure_level_threshold.value, 2)
        current_level = level_hierarchy.get(failure_level, 1)
        
        if current_level < required_level:
            return False
        
        # Check custom conditions
        for condition_key, condition_value in conditions.items():
            if condition_key == 'max_failures':
                if context.get('consecutive_failures', 0) < condition_value:
                    return False
            elif condition_key == 'response_time_threshold':
                if context.get('response_time_ms', 0) < condition_value:
                    return False
            elif condition_key == 'error_rate_threshold':
                if context.get('error_rate_percent', 0) < condition_value * 100:
                    return False
        
        return True
    
    async def _handle_cache_fallback(
        self,
        config: FallbackConfig,
        operation_type: str,
        request: Any
    ) -> Any:
        """Handle cache-based fallback"""
        cache_key = f"fallback:{self.service_name}:{operation_type}:{hash(str(request))}"
        
        # Try to get from fallback cache
        cached_result = self.fallback_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Check Redis cache
        redis_cache = RedisCache()
        redis_result = await redis_cache.get(cache_key)
        
        if redis_result:
            # Store in local cache
            self.fallback_cache[cache_key] = redis_result
            self.last_fallback_usage[FallbackType.CACHE.value] = datetime.now(timezone.utc)
            return redis_result
        
        raise Exception("Cache fallback: No cached data available")
    
    async def _handle_cached_response_fallback(
        self,
        config: FallbackConfig,
        operation_type: str
    ) -> Any:
        """Handle cached response fallback"""
        # This would return a pre-defined cached response
        # In a real implementation, this would have specific response data
        return {
            'status': 'cached',
            'service': self.service_name,
            'operation': operation_type,
            'data': 'This is a cached fallback response',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _handle_alternative_service_fallback(
        self,
        config: FallbackConfig,
        request: Any
    ) -> Any:
        """Handle alternative service fallback"""
        if not config.alternative_service_urls:
            raise Exception("Alternative service fallback: No alternative services configured")
        
        # Try alternative services
        for service_url in config.alternative_service_urls:
            try:
                # In a real implementation, this would make HTTP request to alternative service
                logger.info(f"Attempting fallback to alternative service: {service_url}")
                
                # Simulate service call
                await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate network delay
                
                # Success (for demo)
                return {
                    'status': 'fallback_success',
                    'service': self.service_name,
                    'alternative_service': service_url,
                    'data': 'Response from alternative service',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                logger.warning(f"Alternative service {service_url} failed: {e}")
                continue
        
        raise Exception("Alternative service fallback: All alternative services failed")
    
    async def _handle_degraded_mode_fallback(
        self,
        config: FallbackConfig,
        operation_type: str,
        request: Any
    ) -> Any:
        """Handle degraded mode fallback"""
        # Return limited functionality response
        return {
            'status': 'degraded_mode',
            'service': self.service_name,
            'operation': operation_type,
            'message': 'Service operating in degraded mode with limited functionality',
            'available_features': ['read', 'basic_query'],
            'unavailable_features': ['write', 'complex_queries', 'bulk_operations'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _handle_static_response_fallback(
        self,
        config: FallbackConfig,
        operation_type: str
    ) -> Any:
        """Handle static response fallback"""
        if config.static_response_data:
            return {
                'status': 'static_response',
                'service': self.service_name,
                'operation': operation_type,
                'data': config.static_response_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        return {
            'status': 'static_response',
            'service': self.service_name,
            'operation': operation_type,
            'message': 'Service temporarily unavailable',
            'retry_after': config.cooldown_seconds,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _handle_queued_request_fallback(
        self,
        config: FallbackConfig,
        operation_type: str,
        request: Any
    ) -> Any:
        """Handle queued request fallback"""
        # Queue the request for later processing
        queue_data = {
            'service': self.service_name,
            'operation': operation_type,
            'request': request,
            'queued_at': datetime.now(timezone.utc).isoformat(),
            'estimated_processing_time': '5-15 minutes'
        }
        
        # In real implementation, this would add to a message queue
        logger.info(f"Queued request for {self.service_name}: {operation_type}")
        
        return {
            'status': 'queued',
            'service': self.service_name,
            'operation': operation_type,
            'message': 'Request queued for processing when service recovers',
            'queue_id': f"{self.service_name}:{int(time.time())}:{random.randint(1000, 9999)}",
            'estimated_wait_time': '5-15 minutes',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

class RecoveryManager:
    """Manages service recovery processes"""
    
    def __init__(self, service_name: str, config: RecoveryConfig):
        self.service_name = service_name
        self.config = config
        
        # Recovery state
        self.current_recovery: Optional[RecoveryAttempt] = None
        self.recovery_history = deque(maxlen=50)
        
        # Health tracking
        self.health_metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0
        }
        
        logger.info(f"Created recovery manager for service: {service_name}")
    
    async def start_recovery(
        self,
        strategy: RecoveryStrategy,
        failure_context: Dict[str, Any]
    ) -> str:
        """Start recovery process"""
        recovery_id = f"{self.service_name}:{strategy.value}:{int(time.time())}"
        
        recovery = RecoveryAttempt(
            id=recovery_id,
            service_name=self.service_name,
            strategy=strategy,
            start_time=datetime.now(timezone.utc),
            metadata={'failure_context': failure_context}
        )
        
        self.current_recovery = recovery
        
        logger.info(f"Started recovery for {self.service_name} using {strategy.value} strategy")
        
        return recovery_id
    
    async def execute_recovery(
        self,
        recovery_id: str,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute recovery process"""
        if not self.current_recovery or self.current_recovery.id != recovery_id:
            logger.error(f"Recovery {recovery_id} not found or not current")
            return False
        
        recovery = self.current_recovery
        recovery.status = RecoveryStatus.IN_PROGRESS
        start_time = time.time()
        
        try:
            if recovery.strategy == RecoveryStrategy.IMMEDIATE:
                success = await self._execute_immediate_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            elif recovery.strategy == RecoveryStrategy.GRADUAL:
                success = await self._execute_gradual_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            elif recovery.strategy == RecoveryStrategy.CANARY:
                success = await self._execute_canary_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            elif recovery.strategy == RecoveryStrategy.LOAD_BALANCED:
                success = await self._execute_load_balanced_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            elif recovery.strategy == RecoveryStrategy.ADAPTIVE:
                success = await self._execute_adaptive_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            elif recovery.strategy == RecoveryStrategy.ROLLING:
                success = await self._execute_rolling_recovery(
                    health_check_function, operation_function, *args, **kwargs
                )
            else:
                raise ValueError(f"Unsupported recovery strategy: {recovery.strategy}")
            
            recovery.end_time = datetime.now(timezone.utc)
            
            if success:
                recovery.status = RecoveryStatus.SUCCESSFUL
                recovery.recovery_percentage = 100.0
                self.health_metrics['recovery_successes'] += 1
            else:
                recovery.status = RecoveryStatus.FAILED
                recovery.recovery_percentage = 0.0
            
            # Add to history
            self.recovery_history.append(recovery)
            self.health_metrics['recovery_attempts'] += 1
            
            return success
            
        except Exception as e:
            recovery.end_time = datetime.now(timezone.utc)
            recovery.status = RecoveryStatus.FAILED
            recovery.error_messages.append(str(e))
            recovery.recovery_percentage = 0.0
            
            logger.error(f"Recovery {recovery_id} failed: {e}")
            return False
        
        finally:
            execution_time = time.time() - start_time
            recovery.metadata['execution_time_seconds'] = execution_time
    
    async def _execute_immediate_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute immediate recovery (all at once)"""
        max_attempts = self.config.max_recovery_attempts
        
        for attempt in range(max_attempts):
            try:
                # Wait before attempt
                if attempt > 0:
                    wait_time = self.config.recovery_timeout_seconds / max_attempts
                    await asyncio.sleep(wait_time)
                
                # Perform health check
                is_healthy = await self._check_health(health_check_function)
                
                if is_healthy:
                    # Test operation
                    result = await self._test_operation(operation_function, *args, **kwargs)
                    
                    if result:
                        logger.info(f"Immediate recovery successful for {self.service_name}")
                        return True
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                self.current_recovery.error_messages.append(f"Attempt {attempt + 1}: {str(e)}")
                continue
        
        return False
    
    async def _execute_gradual_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute gradual recovery (increase traffic gradually)"""
        max_attempts = self.config.max_recovery_attempts
        traffic_increments = [0.1, 0.3, 0.5, 0.7, 1.0]  # 10%, 30%, 50%, 70%, 100%
        
        for attempt in range(max_attempts):
            try:
                # Wait before attempt
                await asyncio.sleep(self.config.gradual_recovery_interval)
                
                # Get traffic percentage for this attempt
                traffic_percentage = traffic_increments[min(attempt, len(traffic_increments) - 1)]
                
                # Check health
                is_healthy = await self._check_health(health_check_function)
                
                if not is_healthy:
                    continue
                
                # Test with percentage of traffic
                success_count = 0
                test_count = max(1, int(10 * traffic_percentage))  # Test with up to 10 operations
                
                for _ in range(test_count):
                    try:
                        result = await self._test_operation(operation_function, *args, **kwargs)
                        if result:
                            success_count += 1
                    except Exception:
                        pass
                
                # Check success rate
                success_rate = success_count / test_count
                recovery.recovery_percentage = traffic_percentage * 100
                
                if success_rate >= self.config.success_threshold_percentage:
                    logger.info(f"Gradual recovery successful for {self.service_name} at {traffic_percentage*100:.0f}% traffic")
                    return True
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                self.current_recovery.error_messages.append(f"Gradual attempt {attempt + 1}: {str(e)}")
                continue
        
        return False
    
    async def _execute_canary_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute canary recovery (small percentage of traffic)"""
        canary_percentage = self.config.canary_traffic_percentage
        max_attempts = self.config.max_recovery_attempts
        
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(self.config.gradual_recovery_interval)
                
                # Check health
                is_healthy = await self._check_health(health_check_function)
                
                if not is_healthy:
                    continue
                
                # Send canary traffic (small percentage)
                canary_requests = max(1, int(100 * canary_percentage))  # 1-5 requests
                success_count = 0
                
                for _ in range(canary_requests):
                    try:
                        result = await self._test_operation(operation_function, *args, **kwargs)
                        if result:
                            success_count += 1
                    except Exception:
                        pass
                
                # Check success rate
                success_rate = success_count / canary_requests
                recovery.recovery_percentage = canary_percentage * 100
                
                if success_rate >= self.config.success_threshold_percentage:
                    logger.info(f"Canary recovery successful for {self.service_name}")
                    return True
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                self.current_recovery.error_messages.append(f"Canary attempt {attempt + 1}: {str(e)}")
                continue
        
        return False
    
    async def _execute_load_balanced_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute load balanced recovery (distribute across instances)"""
        # This would involve checking multiple service instances
        # and gradually increasing traffic to healthy instances
        
        max_attempts = self.config.max_recovery_attempts
        instances = kwargs.get('service_instances', ['instance1', 'instance2'])  # Simplified
        
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(self.config.gradual_recovery_interval)
                
                # Check health of all instances
                healthy_instances = []
                for instance in instances:
                    try:
                        is_healthy = await self._check_instance_health(health_check_function, instance)
                        if is_healthy:
                            healthy_instances.append(instance)
                    except Exception:
                        continue
                
                if not healthy_instances:
                    continue
                
                # Test operations on healthy instances
                success_count = 0
                total_tests = len(healthy_instances)
                
                for instance in healthy_instances:
                    try:
                        result = await self._test_instance_operation(
                            operation_function, instance, *args, **kwargs
                        )
                        if result:
                            success_count += 1
                    except Exception:
                        pass
                
                # Check success rate
                success_rate = success_count / max(1, total_tests)
                recovery.recovery_percentage = (len(healthy_instances) / len(instances)) * 100
                
                if success_rate >= self.config.success_threshold_percentage:
                    logger.info(f"Load balanced recovery successful for {self.service_name}")
                    return True
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                self.current_recovery.error_messages.append(f"Load balanced attempt {attempt + 1}: {str(e)}")
                continue
        
        return False
    
    async def _execute_adaptive_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute adaptive recovery (adjust based on real-time metrics)"""
        max_attempts = self.config.max_recovery_attempts
        backoff_factor = self.config.retry_backoff_factor
        
        for attempt in range(max_attempts):
            try:
                # Adaptive wait time
                wait_time = min(
                    self.config.recovery_timeout_seconds,
                    self.config.gradual_recovery_interval * (backoff_factor ** attempt)
                )
                await asyncio.sleep(wait_time)
                
                # Get adaptive parameters
                adaptive_params = await self._get_adaptive_parameters()
                
                # Check health with adaptive thresholds
                is_healthy = await self._check_health_adaptive(health_check_function, adaptive_params)
                
                if not is_healthy:
                    continue
                
                # Adaptive traffic testing
                traffic_percentage = min(1.0, (attempt + 1) / max_attempts)
                
                # Test operations with adaptive parameters
                success_count = 0
                test_operations = max(1, int(10 * traffic_percentage))
                
                for _ in range(test_operations):
                    try:
                        result = await self._test_operation_adaptive(
                            operation_function, adaptive_params, *args, **kwargs
                        )
                        if result:
                            success_count += 1
                    except Exception:
                        pass
                
                # Check success rate
                success_rate = success_count / test_operations
                recovery.recovery_percentage = traffic_percentage * 100
                
                if success_rate >= self.config.success_threshold_percentage:
                    logger.info(f"Adaptive recovery successful for {self.service_name}")
                    return True
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                self.current_recovery.error_messages.append(f"Adaptive attempt {attempt + 1}: {str(e)}")
                continue
        
        return False
    
    async def _execute_rolling_recovery(
        self,
        health_check_function: Callable,
        operation_function: Callable,
        *args,
        **kwargs
    ) -> bool:
        """Execute rolling recovery (update instances one by one)"""
        # This would involve updating service instances one at a time
        # and verifying each one before proceeding to the next
        
        instances = kwargs.get('service_instances', ['instance1', 'instance2'])
        max_attempts = min(self.config.max_recovery_attempts, len(instances))
        
        for i, instance in enumerate(instances[:max_attempts]):
            try:
                await asyncio.sleep(self.config.gradual_recovery_interval)
                
                # Update/check this instance
                is_healthy = await self._update_instance(instance, health_check_function, operation_function, *args, **kwargs)
                
                if is_healthy:
                    recovery.successful_operations += 1
                    recovery.recovery_percentage = ((i + 1) / len(instances)) * 100
                    logger.info(f"Rolling recovery: {instance} recovered successfully")
                else:
                    recovery.failed_operations += 1
                    recovery.error_messages.append(f"Instance {instance} failed to recover")
                
                self.current_recovery.attempts_made += 1
                
            except Exception as e:
                recovery.failed_operations += 1
                recovery.error_messages.append(f"Rolling recovery attempt {i + 1}: {str(e)}")
                continue
        
        # Recovery successful if all instances are healthy
        return recovery.successful_operations == len(instances[:max_attempts])
    
    async def _check_health(self, health_check_function: Callable) -> bool:
        """Perform health check"""
        try:
            if asyncio.iscoroutinefunction(health_check_function):
                result = await health_check_function()
            else:
                result = health_check_function()
            
            return bool(result)
        except Exception as e:
            logger.error(f"Health check failed for {self.service_name}: {e}")
            return False
    
    async def _check_health_adaptive(self, health_check_function: Callable, params: Dict[str, Any]) -> bool:
        """Perform adaptive health check"""
        try:
            # Modify health check based on adaptive parameters
            timeout = params.get('timeout', 5.0)
            threshold = params.get('success_threshold', 0.8)
            
            # Execute with adaptive timeout
            start_time = time.time()
            result = await asyncio.wait_for(self._check_health(health_check_function), timeout=timeout)
            
            # Record metrics
            execution_time = time.time() - start_time
            self.health_metrics['total_operations'] += 1
            
            if result:
                self.health_metrics['successful_operations'] += 1
            else:
                self.health_metrics['failed_operations'] += 1
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Adaptive health check timeout for {self.service_name}")
            return False
        except Exception as e:
            logger.error(f"Adaptive health check failed for {self.service_name}: {e}")
            return False
    
    async def _test_operation(self, operation_function: Callable, *args, **kwargs) -> bool:
        """Test if operation can be executed successfully"""
        try:
            if asyncio.iscoroutinefunction(operation_function):
                result = await operation_function(*args, **kwargs)
            else:
                result = operation_function(*args, **kwargs)
            
            self.health_metrics['total_operations'] += 1
            self.health_metrics['successful_operations'] += 1
            
            return bool(result)
            
        except Exception as e:
            self.health_metrics['failed_operations'] += 1
            logger.debug(f"Test operation failed for {self.service_name}: {e}")
            return False
    
    async def _test_operation_adaptive(self, operation_function: Callable, params: Dict[str, Any], *args, **kwargs) -> bool:
        """Test operation with adaptive parameters"""
        try:
            # Add adaptive parameters to operation
            adaptive_kwargs = kwargs.copy()
            adaptive_kwargs.update(params)
            
            return await self._test_operation(operation_function, *args, **adaptive_kwargs)
            
        except Exception as e:
            logger.debug(f"Adaptive test operation failed for {self.service_name}: {e}")
            return False
    
    async def _check_instance_health(self, health_check_function: Callable, instance: str) -> bool:
        """Check health of specific instance"""
        # Modify health check for specific instance
        return await self._check_health(lambda: health_check_function(instance))
    
    async def _test_instance_operation(self, operation_function: Callable, instance: str, *args, **kwargs) -> bool:
        """Test operation on specific instance"""
        # Add instance to kwargs
        instance_kwargs = kwargs.copy()
        instance_kwargs['instance'] = instance
        
        return await self._test_operation(operation_function, *args, **instance_kwargs)
    
    async def _update_instance(self, instance: str, health_check_function: Callable, operation_function: Callable, *args, **kwargs) -> bool:
        """Update/recover specific instance"""
        # This would involve updating the instance
        # For demo purposes, just check health and test operation
        
        is_healthy = await self._check_instance_health(health_check_function, instance)
        
        if is_healthy:
            test_result = await self._test_instance_operation(operation_function, instance, *args, **kwargs)
            return test_result
        
        return False
    
    async def _get_adaptive_parameters(self) -> Dict[str, Any]:
        """Get adaptive recovery parameters based on service history"""
        # Calculate adaptive parameters based on service performance history
        total_ops = self.health_metrics['total_operations']
        
        if total_ops == 0:
            return {
                'timeout': 5.0,
                'success_threshold': 0.8,
                'traffic_percentage': 0.1
            }
        
        success_rate = self.health_metrics['successful_operations'] / total_ops
        failure_rate = self.health_metrics['failed_operations'] / total_ops
        
        # Adjust parameters based on success rate
        adaptive_params = {
            'timeout': max(1.0, min(10.0, 5.0 * success_rate)),
            'success_threshold': max(0.5, min(1.0, success_rate * 0.9)),
            'traffic_percentage': max(0.05, min(1.0, success_rate))
        }
        
        return adaptive_params

class FailureRecovery:
    """
    Comprehensive Failure Recovery Service
    
    Provides intelligent failure recovery with:
    - Multiple recovery strategies (immediate, gradual, canary, etc.)
    - Automated fallback mechanisms
    - Service health monitoring during recovery
    - Adaptive recovery parameters
    - Comprehensive failure tracking
    - Recovery analytics and reporting
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Recovery managers
        self._recovery_managers: Dict[str, RecoveryManager] = {}
        
        # Service recovery states
        self._service_states: Dict[str, ServiceRecoveryState] = {}
        
        # Fallback handlers
        self._fallback_handlers: Dict[str, FallbackHandler] = {}
        
        # Failure events
        self._failure_events: Dict[str, FailureEvent] = {}
        
        # Global statistics
        self._global_stats = {
            'total_failures': 0,
            'total_recovery_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'total_fallback_executions': 0,
            'services_in_recovery': 0
        }
        
        # Configuration
        self.config = {
            'default_recovery_config': RecoveryConfig(),
            'default_fallback_configs': [
                FallbackConfig(
                    fallback_type=FallbackType.CACHE,
                    priority=1,
                    conditions={'max_failures': 3}
                ),
                FallbackConfig(
                    fallback_type=FallbackType.CACHED_RESPONSE,
                    priority=2
                ),
                FallbackConfig(
                    fallback_type=FallbackType.DEGRADED_MODE,
                    priority=3,
                    failure_level_threshold=FailureLevel.HIGH
                )
            ],
            'monitoring_interval': 30,
            'cleanup_interval': 3600,
            'redis_namespace': 'failure_recovery'
        }
        
        logger.info("FailureRecovery initialized")
    
    async def register_service(
        self,
        service_name: str,
        recovery_config: Optional[RecoveryConfig] = None,
        fallback_configs: Optional[List[FallbackConfig]] = None
    ) -> bool:
        """Register a service for failure recovery"""
        try:
            if recovery_config is None:
                recovery_config = self.config['default_recovery_config']
            
            if fallback_configs is None:
                fallback_configs = self.config['default_fallback_configs']
            
            # Create recovery manager
            recovery_manager = RecoveryManager(service_name, recovery_config)
            self._recovery_managers[service_name] = recovery_manager
            
            # Create service recovery state
            service_state = ServiceRecoveryState(service_name=service_name)
            self._service_states[service_name] = service_state
            
            # Create fallback handler
            fallback_handler = FallbackHandler(service_name, fallback_configs)
            self._fallback_handlers[service_name] = fallback_handler
            
            logger.info(f"Registered service for failure recovery: {service_name}")
            
            await self.event_tracker.track_event(
                "service_registered_for_recovery",
                {
                    "service_name": service_name,
                    "recovery_strategy": list(RecoveryStrategy),
                    "fallback_types": [config.fallback_type.value for config in fallback_configs]
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    async def unregister_service(self, service_name: str) -> bool:
        """Unregister service from failure recovery"""
        try:
            # Remove from all tracking structures
            self._recovery_managers.pop(service_name, None)
            self._service_states.pop(service_name, None)
            self._fallback_handlers.pop(service_name, None)
            
            logger.info(f"Unregistered service from failure recovery: {service_name}")
            
            await self.event_tracker.track_event(
                "service_unregistered_from_recovery",
                {"service_name": service_name}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister service {service_name}: {e}")
            return False
    
    async def handle_failure(
        self,
        service_name: str,
        failure_level: FailureLevel,
        failure_type: str,
        error_message: str,
        context: Dict[str, Any],
        operation_function: Optional[Callable] = None,
        health_check_function: Optional[Callable] = None,
        *operation_args,
        **operation_kwargs
    ) -> Dict[str, Any]:
        """Handle service failure and execute recovery/fallback"""
        failure_id = f"{service_name}:{int(time.time())}:{random.randint(1000, 9999)}"
        
        # Create failure event
        failure_event = FailureEvent(
            id=failure_id,
            service_name=service_name,
            failure_level=failure_level,
            failure_type=failure_type,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            context=context
        )
        
        self._failure_events[failure_id] = failure_event
        self._global_stats['total_failures'] += 1
        
        logger.warning(f"Handling failure for {service_name}: {error_message}")
        
        try:
            # Update service state
            service_state = self._service_states.get(service_name)
            if service_state:
                service_state.consecutive_failures += 1
                service_state.consecutive_successes = 0
            
            # Check if recovery is needed
            if failure_level in [FailureLevel.HIGH, FailureLevel.CRITICAL]:
                recovery_result = await self._initiate_recovery(
                    service_name, failure_event, health_check_function, operation_function,
                    *operation_args, **operation_kwargs
                )
                
                if recovery_result['success']:
                    failure_event.resolved = True
                    failure_event.resolution_time = datetime.now(timezone.utc)
                    failure_event.recovery_attempt_id = recovery_result['recovery_id']
                    
                    return {
                        'status': 'recovery_successful',
                        'recovery_id': recovery_result['recovery_id'],
                        'recovery_strategy': recovery_result['strategy'],
                        'message': 'Service recovered successfully'
                    }
                else:
                    logger.warning(f"Recovery failed for {service_name}, attempting fallback")
            
            # Execute fallback
            fallback_result = await self._execute_fallback(
                service_name, failure_event, context, operation_function,
                *operation_args, **operation_kwargs
            )
            
            return {
                'status': 'fallback_executed',
                'fallback_type': fallback_result['fallback_type'],
                'fallback_data': fallback_result['data'],
                'message': 'Fallback mechanism executed successfully'
            }
            
        except Exception as e:
            logger.error(f"Failure handling failed for {service_name}: {e}")
            
            return {
                'status': 'handling_failed',
                'error': str(e),
                'message': 'Both recovery and fallback failed'
            }
        
        finally:
            # Track final statistics
            await self._update_recovery_statistics(service_name, failure_event)
    
    async def _initiate_recovery(
        self,
        service_name: str,
        failure_event: FailureEvent,
        health_check_function: Optional[Callable],
        operation_function: Optional[Callable],
        *operation_args,
        **operation_kwargs
    ) -> Dict[str, Any]:
        """Initiate recovery process"""
        try:
            recovery_manager = self._recovery_managers.get(service_name)
            service_state = self._service_states.get(service_name)
            
            if not recovery_manager or not service_state:
                raise Exception("Recovery manager or service state not found")
            
            # Determine recovery strategy based on failure and service state
            strategy = self._determine_recovery_strategy(failure_event, service_state)
            
            # Start recovery
            recovery_id = await recovery_manager.start_recovery(strategy, failure_event.context)
            service_state.current_recovery = recovery_manager.current_recovery
            
            # Execute recovery
            recovery_success = await recovery_manager.execute_recovery(
                recovery_id, health_check_function, operation_function,
                *operation_args, **operation_kwargs
            )
            
            # Update global statistics
            self._global_stats['total_recovery_attempts'] += 1
            
            if recovery_success:
                self._global_stats['successful_recoveries'] += 1
                service_state.consecutive_failures = 0
                service_state.last_recovery_time = datetime.now(timezone.utc)
                
                await self.event_tracker.track_event(
                    "recovery_successful",
                    {
                        "service_name": service_name,
                        "recovery_id": recovery_id,
                        "strategy": strategy.value,
                        "recovery_time": (datetime.now(timezone.utc) - failure_event.timestamp).total_seconds()
                    }
                )
            else:
                self._global_stats['failed_recoveries'] += 1
                
                await self.event_tracker.track_event(
                    "recovery_failed",
                    {
                        "service_name": service_name,
                        "recovery_id": recovery_id,
                        "strategy": strategy.value,
                        "error_count": len(recovery_manager.current_recovery.error_messages) if recovery_manager.current_recovery else 0
                    }
                )
            
            return {
                'success': recovery_success,
                'recovery_id': recovery_id,
                'strategy': strategy.value
            }
            
        except Exception as e:
            logger.error(f"Recovery initiation failed for {service_name}: {e}")
            return {
                'success': False,
                'recovery_id': None,
                'strategy': 'unknown'
            }
    
    async def _execute_fallback(
        self,
        service_name: str,
        failure_event: FailureEvent,
        context: Dict[str, Any],
        operation_function: Optional[Callable],
        *operation_args,
        **operation_kwargs
    ) -> Dict[str, Any]:
        """Execute fallback mechanism"""
        try:
            fallback_handler = self._fallback_handlers.get(service_name)
            
            if not fallback_handler:
                raise Exception("Fallback handler not found")
            
            # Add failure context
            enhanced_context = context.copy()
            enhanced_context.update({
                'failure_level': failure_event.failure_level,
                'failure_type': failure_event.failure_type,
                'error_message': failure_event.error_message,
                'service_name': service_name,
                'timestamp': failure_event.timestamp.isoformat()
            })
            
            # Execute fallback
            result = await fallback_handler.execute_fallback(
                enhanced_context,
                operation_function.__name__ if operation_function else 'unknown',
                operation_args if operation_args else None
            )
            
            # Update statistics
            self._global_stats['total_fallback_executions'] += 1
            
            await self.event_tracker.track_event(
                "fallback_executed",
                {
                    "service_name": service_name,
                    "fallback_type": enhanced_context.get('fallback_type', 'unknown'),
                    "failure_level": failure_event.failure_level.value
                }
            )
            
            return {
                'fallback_type': enhanced_context.get('fallback_type', 'unknown'),
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Fallback execution failed for {service_name}: {e}")
            raise
    
    def _determine_recovery_strategy(
        self,
        failure_event: FailureEvent,
        service_state: ServiceRecoveryState
    ) -> RecoveryStrategy:
        """Determine appropriate recovery strategy"""
        # Consider failure level
        if failure_event.failure_level == FailureLevel.CRITICAL:
            return RecoveryStrategy.IMMEDIATE
        
        # Consider failure history
        if service_state.consecutive_failures >= 5:
            return RecoveryStrategy.CANARY
        elif service_state.consecutive_failures >= 3:
            return RecoveryStrategy.GRADUAL
        
        # Consider current health score
        if service_state.service_health_score > 0.7:
            return RecoveryStrategy.IMMEDIATE
        elif service_state.service_health_score > 0.4:
            return RecoveryStrategy.GRADUAL
        else:
            return RecoveryStrategy.ADAPTIVE
    
    async def _update_recovery_statistics(self, service_name: str, failure_event: FailureEvent) -> None:
        """Update recovery statistics"""
        service_state = self._service_states.get(service_name)
        if service_state:
            # Update health score based on recent performance
            if failure_event.resolved:
                service_state.service_health_score = min(1.0, service_state.service_health_score + 0.1)
            else:
                service_state.service_health_score = max(0.0, service_state.service_health_score - 0.1)
    
    async def get_recovery_status(self, service_name: str) -> Dict[str, Any]:
        """Get recovery status for a service"""
        if service_name not in self._service_states:
            return {'error': f'Service {service_name} not registered'}
        
        service_state = self._service_states[service_name]
        recovery_manager = self._recovery_managers.get(service_name)
        
        current_recovery = None
        if recovery_manager and recovery_manager.current_recovery:
            current_recovery = {
                'id': recovery_manager.current_recovery.id,
                'strategy': recovery_manager.current_recovery.strategy.value,
                'status': recovery_manager.current_recovery.status.value,
                'attempts_made': recovery_manager.current_recovery.attempts_made,
                'recovery_percentage': recovery_manager.current_recovery.recovery_percentage,
                'start_time': recovery_manager.current_recovery.start_time.isoformat(),
                'error_messages': recovery_manager.current_recovery.error_messages
            }
        
        return {
            'service_name': service_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_recovery': current_recovery,
            'service_health_score': service_state.service_health_score,
            'consecutive_failures': service_state.consecutive_failures,
            'consecutive_successes': service_state.consecutive_successes,
            'last_recovery_time': service_state.last_recovery_time.isoformat() if service_state.last_recovery_time else None,
            'recovery_history_count': len(service_state.recovery_history),
            'active_fallbacks': list(service_state.active_fallbacks.keys())
        }
    
    async def get_global_recovery_status(self) -> Dict[str, Any]:
        """Get global recovery status"""
        current_time = datetime.now(timezone.utc)
        
        # Calculate services in recovery
        services_in_recovery = len([
            state for state in self._service_states.values()
            if state.current_recovery is not None
        ])
        
        self._global_stats['services_in_recovery'] = services_in_recovery
        
        # Calculate success rates
        recovery_success_rate = (
            self._global_stats['successful_recoveries'] / 
            max(1, self._global_stats['total_recovery_attempts'])
        ) * 100
        
        return {
            'timestamp': current_time.isoformat(),
            'overview': {
                'total_services': len(self._service_states),
                'services_in_recovery': services_in_recovery,
                'total_failures': self._global_stats['total_failures'],
                'total_recovery_attempts': self._global_stats['total_recovery_attempts'],
                'recovery_success_rate_percent': round(recovery_success_rate, 2),
                'fallback_execution_rate': self._global_stats['total_fallback_executions']
            },
            'service_statuses': {
                service_name: {
                    'health_score': state.service_health_score,
                    'consecutive_failures': state.consecutive_failures,
                    'current_recovery': state.current_recovery is not None
                }
                for service_name, state in self._service_states.items()
            },
            'failure_events': {
                'total_events': len(self._failure_events),
                'unresolved_events': len([e for e in self._failure_events.values() if not e.resolved]),
                'recent_events': [
                    {
                        'id': event.id,
                        'service_name': event.service_name,
                        'failure_level': event.failure_level.value,
                        'timestamp': event.timestamp.isoformat(),
                        'resolved': event.resolved
                    }
                    for event in list(self._failure_events.values())[-10:]  # Last 10 events
                ]
            }
        }
    
    async def get_recovery_analytics(
        self,
        service_name: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get recovery analytics and trends"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
            
            if service_name:
                return await self._get_service_recovery_analytics(service_name, start_time, end_time)
            else:
                return await self._get_global_recovery_analytics(start_time, end_time)
                
        except Exception as e:
            logger.error(f"Failed to get recovery analytics: {e}")
            return {'error': str(e)}
    
    async def _get_service_recovery_analytics(self, service_name: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get recovery analytics for specific service"""
        recovery_manager = self._recovery_managers.get(service_name)
        if not recovery_manager:
            return {'error': f'Recovery manager not found for {service_name}'}
        
        # Filter recovery history
        filtered_recoveries = [
            recovery for recovery in recovery_manager.recovery_history
            if start_time <= recovery.start_time <= end_time
        ]
        
        # Calculate analytics
        total_recoveries = len(filtered_recoveries)
        successful_recoveries = sum(1 for r in recovery in filtered_recoveries if recovery.status == RecoveryStatus.SUCCESSFUL)
        failed_recoveries = sum(1 for recovery in filtered_recoveries if recovery.status == RecoveryStatus.FAILED)
        
        avg_recovery_time = 0
        if total_recoveries > 0:
            recovery_times = []
            for recovery in filtered_recoveries:
                if recovery.end_time:
                    recovery_time = (recovery.end_time - recovery.start_time).total_seconds()
                    recovery_times.append(recovery_time)
            avg_recovery_time = statistics.mean(recovery_times) if recovery_times else 0
        
        # Strategy distribution
        strategy_distribution = defaultdict(int)
        for recovery in filtered_recoveries:
            strategy_distribution[recovery.strategy.value] += 1
        
        return {
            'service_name': service_name,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'recovery_summary': {
                'total_recovery_attempts': total_recoveries,
                'successful_recoveries': successful_recoveries,
                'failed_recoveries': failed_recoveries,
                'success_rate_percent': round((successful_recoveries / max(1, total_recoveries)) * 100, 2),
                'avg_recovery_time_seconds': round(avg_recovery_time, 2)
            },
            'strategy_analysis': {
                'strategy_distribution': dict(strategy_distribution),
                'most_successful_strategy': max(strategy_distribution.items(), key=lambda x: x[1])[0] if strategy_distribution else 'none'
            },
            'performance_trends': {
                'recovery_frequency': total_recoveries / max(1, (end_time - start_time).total_seconds() / 3600),
                'improvement_trend': 'stable'  # Would calculate based on time series
            }
        }
    
    async def _get_global_recovery_analytics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get global recovery analytics"""
        # Aggregate analytics across all services
        all_recoveries = []
        all_failures = []
        
        for recovery_manager in self._recovery_managers.values():
            all_recoveries.extend([
                recovery for recovery in recovery_manager.recovery_history
                if start_time <= recovery.start_time <= end_time
            ])
        
        all_failures = [
            failure for failure in self._failure_events.values()
            if start_time <= failure.timestamp <= end_time
        ]
        
        # Global statistics
        total_recoveries = len(all_recoveries)
        successful_recoveries = sum(1 for recovery in all_recoveries if recovery.status == RecoveryStatus.SUCCESSFUL)
        total_failures = len(all_failures)
        resolved_failures = sum(1 for failure in all_failures if failure.resolved)
        
        # Service performance ranking
        service_performance = []
        for service_name in self._service_states.keys():
            recovery_manager = self._recovery_managers.get(service_name)
            if recovery_manager:
                service_recoveries = [r for r in recovery_manager.recovery_history if start_time <= r.start_time <= end_time]
                service_success_rate = (sum(1 for r in service_recoveries if r.status == RecoveryStatus.SUCCESSFUL) / max(1, len(service_recoveries))) * 100
                
                service_performance.append({
                    'service_name': service_name,
                    'recovery_attempts': len(service_recoveries),
                    'success_rate_percent': round(service_success_rate, 2),
                    'health_score': self._service_states[service_name].service_health_score
                })
        
        # Sort by success rate
        service_performance.sort(key=lambda x: x['success_rate_percent'], reverse=True)
        
        return {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'global_summary': {
                'total_services': len(self._service_states),
                'total_failures': total_failures,
                'resolved_failures': resolved_failures,
                'resolution_rate_percent': round((resolved_failures / max(1, total_failures)) * 100, 2),
                'total_recovery_attempts': total_recoveries,
                'successful_recoveries': successful_recoveries,
                'recovery_success_rate_percent': round((successful_recoveries / max(1, total_recoveries)) * 100, 2)
            },
            'service_performance': {
                'top_performers': service_performance[:5],
                'worst_performers': service_performance[-5:],
                'total_services_analyzed': len(service_performance)
            },
            'system_resilience': {
                'failure_frequency': total_failures / max(1, (end_time - start_time).total_seconds() / 3600),
                'recovery_effectiveness': 'high' if successful_recoveries / max(1, total_recoveries) > 0.8 else 'medium',
                'overall_health_score': statistics.mean([state.service_health_score for state in self._service_states.values()])
            }
        }
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired recovery data"""
        try:
            cleanup_count = 0
            current_time = datetime.now(timezone.utc)
            retention_cutoff = current_time - timedelta(days=7)  # 7 days retention
            
            # Clean up old failure events
            expired_events = [
                event_id for event_id, event in self._failure_events.items()
                if event.timestamp < retention_cutoff
            ]
            
            for event_id in expired_events:
                del self._failure_events[event_id]
                cleanup_count += 1
            
            # Clean up old recovery history
            for recovery_manager in self._recovery_managers.values():
                old_recoveries = [
                    recovery for recovery in recovery_manager.recovery_history
                    if recovery.start_time < retention_cutoff
                ]
                
                for old_recovery in old_recoveries:
                    if old_recovery in recovery_manager.recovery_history:
                        recovery_manager.recovery_history.remove(old_recovery)
                        cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired recovery entries")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        # Clear all data structures
        self._recovery_managers.clear()
        self._service_states.clear()
        self._fallback_handlers.clear()
        self._failure_events.clear()
        
        logger.info("FailureRecovery closed")