"""
Failover Manager

Automatic failover and health checking for proxy endpoints:
- Health monitoring and alerting
- Automatic endpoint failover
- Circuit breaker integration
- Recovery detection
- Service degradation handling

Features:
- Multi-level health checks
- Graceful degradation
- Failover chain management
- Recovery strategies
- Health-based routing decisions
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque

import httpx

from app.models.proxy import ProxyEndpoint, CircuitBreakerState
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class FailoverEvent(Enum):
    """Failover event types."""
    HEALTH_CHECK_FAILED = "health_check_failed"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"
    FAILOVER_TRIGGERED = "failover_triggered"
    RECOVERY_DETECTED = "recovery_detected"
    SERVICE_DEGRADED = "service_degraded"
    SERVICE_RESTORED = "service_restored"


@dataclass
class HealthCheck:
    """Health check configuration and results."""
    name: str
    endpoint_id: str
    url: str
    method: str = "GET"
    timeout_seconds: float = 5.0
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    expected_response_time_ms: float = 1000.0
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    
    # Results
    last_check_time: Optional[datetime] = None
    last_result: bool = False
    last_response_time_ms: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    successful_checks: int = 0


@dataclass
class FailoverState:
    """State information for failover management."""
    endpoint_id: str
    current_status: HealthStatus
    previous_status: HealthStatus
    status_change_time: datetime
    failover_count: int = 0
    recovery_count: int = 0
    last_failover_time: Optional[datetime] = None
    last_recovery_time: Optional[datetime] = None
    
    # Health check information
    health_check: HealthCheck
    check_interval_seconds: int = 30
    failure_threshold: int = 3
    recovery_threshold: int = 2
    
    # Circuit breaker information
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_breaker_failures: int = 0
    
    # Metrics
    avg_response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    availability_percent: float = 100.0


@dataclass
class FailoverChain:
    """Failover chain for endpoints."""
    primary_endpoint_id: str
    fallback_endpoints: List[str]
    failover_strategy: str = "sequential"  # "sequential", "parallel", "priority"
    max_failover_depth: int = 3
    current_index: int = 0
    
    # Statistics
    total_failovers: int = 0
    successful_failovers: int = 0
    avg_failover_time_ms: float = 0.0


class HealthChecker:
    """Performs health checks on endpoints."""
    
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.health_check_results: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
    
    async def perform_health_check(self, health_check: HealthCheck) -> Tuple[bool, float, Optional[str]]:
        """
        Perform health check on endpoint.
        
        Returns:
            Tuple of (success, response_time_ms, error_message)
        """
        start_time = time.time()
        
        try:
            # Perform HTTP request
            response = await self.http_client.request(
                method=health_check.method,
                url=health_check.url,
                headers=health_check.headers,
                content=health_check.body,
                timeout=httpx.Timeout(health_check.timeout_seconds)
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Update check results
            health_check.total_checks += 1
            health_check.last_check_time = datetime.utcnow()
            health_check.last_result = True
            health_check.last_response_time_ms = response_time_ms
            health_check.last_error = None
            
            # Check status code
            if response.status_code not in health_check.expected_status_codes:
                success = False
                error = f"Unexpected status code: {response.status_code}"
            else:
                success = True
                error = None
            
            # Check response time
            if response_time_ms > health_check.expected_response_time_ms:
                success = False
                error = f"Response time too slow: {response_time_ms}ms"
            
            if success:
                health_check.successful_checks += 1
            else:
                health_check.consecutive_failures += 1
            
            # Store result
            self.health_check_results[health_check.endpoint_id].append({
                "timestamp": datetime.utcnow(),
                "success": success,
                "response_time_ms": response_time_ms,
                "status_code": response.status_code,
                "error": error
            })
            
            return success, response_time_ms, error
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            # Update check results
            health_check.total_checks += 1
            health_check.last_check_time = datetime.utcnow()
            health_check.last_result = False
            health_check.last_response_time_ms = response_time_ms
            health_check.last_error = str(e)
            health_check.consecutive_failures += 1
            
            # Store result
            self.health_check_results[health_check.endpoint_id].append({
                "timestamp": datetime.utcnow(),
                "success": False,
                "response_time_ms": response_time_ms,
                "error": str(e)
            })
            
            return False, response_time_ms, str(e)
    
    def get_health_history(self, endpoint_id: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get health check history for endpoint."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        return [
            result for result in self.health_check_results[endpoint_id]
            if result["timestamp"] >= cutoff_time
        ]


class FailoverManager:
    """
    Manages automatic failover and health monitoring for proxy endpoints.
    
    Features:
    - Continuous health monitoring
    - Automatic failover when primary endpoints fail
    - Circuit breaker integration
    - Recovery detection and restoration
    - Graceful degradation
    - Service mesh integration
    """
    
    def __init__(self):
        """Initialize the failover manager."""
        self.failover_states: Dict[str, FailoverState] = {}
        self.failover_chains: Dict[str, FailoverChain] = {}
        self.health_checker: Optional[HealthChecker] = None
        
        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.recovery_check_task: Optional[asyncio.Task] = None
        self.statistics_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = {
            "health_check_interval": 30,
            "recovery_check_interval": 60,
            "statistics_interval": 300,
            "concurrent_health_checks": 10
        }
        
        # Statistics
        self.statistics = {
            "total_failovers": 0,
            "successful_recoveries": 0,
            "avg_failover_time_ms": 0.0,
            "endpoint_availability": {},
            "last_updated": datetime.utcnow()
        }
        
        # Event callbacks
        self.event_callbacks: Dict[FailoverEvent, List[Callable]] = defaultdict(list)
        
        logger.info("Failover manager initialized")
    
    async def initialize(self):
        """Initialize the failover manager."""
        try:
            # Initialize HTTP client for health checks
            self.health_checker = HealthChecker(httpx.AsyncClient())
            
            # Load failover configurations
            await self._load_failover_configs()
            
            # Start background tasks
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.recovery_check_task = asyncio.create_task(self._recovery_check_loop())
            self.statistics_task = asyncio.create_task(self._statistics_loop())
            
            logger.info("Failover manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize failover manager: {e}")
            raise
    
    async def _load_failover_configs(self):
        """Load failover configurations from database."""
        # This would load failover configurations from database
        # For now, create placeholder configurations
        pass
    
    async def _health_check_loop(self):
        """Background loop for performing health checks."""
        try:
            while True:
                await self._perform_health_checks()
                await asyncio.sleep(self.config["health_check_interval"])
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
    
    async def _recovery_check_loop(self):
        """Background loop for checking endpoint recovery."""
        try:
            while True:
                await self._check_recoveries()
                await asyncio.sleep(self.config["recovery_check_interval"])
        except asyncio.CancelledError:
            logger.info("Recovery check loop cancelled")
        except Exception as e:
            logger.error(f"Error in recovery check loop: {e}")
    
    async def _statistics_loop(self):
        """Background loop for updating statistics."""
        try:
            while True:
                await self._update_statistics()
                await asyncio.sleep(self.config["statistics_interval"])
        except asyncio.CancelledError:
            logger.info("Statistics loop cancelled")
        except Exception as e:
            logger.error(f"Error in statistics loop: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all endpoints."""
        if not self.health_checker:
            return
        
        # Get all endpoints that need health checks
        endpoints_to_check = [
            state for state in self.failover_states.values()
            if state.current_status != HealthStatus.OFFLINE
        ]
        
        # Perform health checks concurrently
        semaphore = asyncio.Semaphore(self.config["concurrent_health_checks"])
        
        async def check_endpoint(state: FailoverState):
            async with semaphore:
                await self._perform_endpoint_health_check(state)
        
        if endpoints_to_check:
            await asyncio.gather(*[check_endpoint(state) for state in endpoints_to_check])
    
    async def _perform_endpoint_health_check(self, state: FailoverState):
        """Perform health check for a single endpoint."""
        try:
            health_check = state.health_check
            
            # Perform health check
            success, response_time_ms, error = await self.health_checker.perform_health_check(
                health_check
            )
            
            # Update state metrics
            state.avg_response_time_ms = (
                (state.avg_response_time_ms * 0.8) + (response_time_ms * 0.2)
            )
            
            # Update availability
            if health_check.total_checks > 0:
                state.availability_percent = (health_check.successful_checks / health_check.total_checks) * 100
            
            # Check for status changes
            await self._evaluate_health_status(state, success, error)
            
        except Exception as e:
            logger.error(f"Health check failed for endpoint {state.endpoint_id}: {e}")
    
    async def _evaluate_health_status(self, state: FailoverState, success: bool, error: Optional[str]):
        """Evaluate and update health status based on check results."""
        previous_status = state.current_status
        status_changed = False
        
        # Determine new status
        if success:
            if state.consecutive_failures > 0:
                state.consecutive_failures -= 1
            
            # Check for recovery
            if (state.current_status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED] and
                state.consecutive_failures <= state.recovery_threshold):
                
                if state.current_status == HealthStatus.UNHEALTHY:
                    state.current_status = HealthStatus.DEGRADED
                    await self._handle_status_change(state, HealthStatus.DEGRADED, previous_status, error)
                elif state.current_status == HealthStatus.DEGRADED:
                    state.current_status = HealthStatus.HEALTHY
                    await self._handle_status_change(state, HealthStatus.HEALTHY, previous_status, error)
        else:
            state.consecutive_failures += 1
            
            # Check for degradation/unhealthiness
            if (state.consecutive_failures >= state.failure_threshold and
                state.current_status == HealthStatus.HEALTHY):
                
                if state.consecutive_failures >= state.failure_threshold * 2:
                    state.current_status = HealthStatus.UNHEALTHY
                    await self._handle_status_change(state, HealthStatus.UNHEALTHY, previous_status, error)
                else:
                    state.current_status = HealthStatus.DEGRADED
                    await self._handle_status_change(state, HealthStatus.DEGRADED, previous_status, error)
            
            # Check for offline status
            elif state.consecutive_failures >= state.failure_threshold * 3:
                state.current_status = HealthStatus.OFFLINE
                await self._handle_status_change(state, HealthStatus.OFFLINE, previous_status, error)
    
    async def _handle_status_change(self, state: FailoverState, new_status: HealthStatus, previous_status: HealthStatus, error: Optional[str]):
        """Handle health status changes."""
        state.previous_status = previous_status
        state.status_change_time = datetime.utcnow()
        
        logger.info(
            f"Endpoint {state.endpoint_id} status changed: {previous_status.value} -> {new_status.value}"
        )
        
        # Trigger failover if needed
        if new_status in [HealthStatus.UNHEALTHY, HealthStatus.OFFLINE]:
            await self._trigger_failover(state, error)
        elif new_status == HealthStatus.HEALTHY:
            await self._handle_recovery(state)
        
        # Track event
        event_type = FailoverEvent.SERVICE_RESTORED if new_status == HealthStatus.HEALTHY else FailoverEvent.SERVICE_DEGRADED
        
        event_tracker.track_system_event(
            f"failover_{event_type.value}",
            EventLevel.WARNING if new_status != HealthStatus.HEALTHY else EventLevel.INFO,
            {
                "endpoint_id": state.endpoint_id,
                "previous_status": previous_status.value,
                "new_status": new_status.value,
                "error": error
            }
        )
    
    async def _trigger_failover(self, failed_state: FailoverState, error: Optional[str]):
        """Trigger failover for failed endpoint."""
        try:
            failover_chain = self.failover_chains.get(failed_state.endpoint_id)
            
            if not failover_chain:
                logger.warning(f"No failover chain defined for endpoint {failed_state.endpoint_id}")
                return
            
            # Find next available endpoint
            next_endpoint = await self._find_next_available_endpoint(failover_chain)
            
            if next_endpoint:
                failover_state = self.failover_states.get(next_endpoint)
                if failover_state and failover_state.current_status == HealthStatus.HEALTHY:
                    
                    logger.info(f"Failover triggered: {failed_state.endpoint_id} -> {next_endpoint}")
                    
                    # Update statistics
                    self.statistics["total_failovers"] += 1
                    failed_state.failover_count += 1
                    failed_state.last_failover_time = datetime.utcnow()
                    
                    # Track failover event
                    event_tracker.track_system_event(
                        "failover_triggered",
                        EventLevel.WARNING,
                        {
                            "failed_endpoint": failed_state.endpoint_id,
                            "fallback_endpoint": next_endpoint,
                            "reason": error
                        }
                    )
                else:
                    logger.warning(f"Fallback endpoint {next_endpoint} is not healthy")
            else:
                logger.error(f"No healthy fallback endpoints available for {failed_state.endpoint_id}")
                
                # Track complete failure
                event_tracker.track_system_event(
                    "failover_failed",
                    EventLevel.CRITICAL,
                    {
                        "failed_endpoint": failed_state.endpoint_id,
                        "reason": "no_healthy_fallbacks"
                    }
                )
            
        except Exception as e:
            logger.error(f"Failover trigger failed: {e}")
    
    async def _find_next_available_endpoint(self, failover_chain: FailoverChain) -> Optional[str]:
        """Find next available endpoint in failover chain."""
        # Try sequential failover
        for i in range(failover_chain.current_index + 1, len(failover_chain.fallback_endpoints)):
            candidate_endpoint = failover_chain.fallback_endpoints[i]
            failover_state = self.failover_states.get(candidate_endpoint)
            
            if failover_state and failover_state.current_status == HealthStatus.HEALTHY:
                failover_chain.current_index = i
                return candidate_endpoint
        
        # Reset to beginning if no healthy endpoint found
        failover_chain.current_index = 0
        return None
    
    async def _check_recoveries(self):
        """Check for endpoint recoveries and restore service."""
        for state in self.failover_states.values():
            if state.current_status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                # Perform immediate health check
                if self.health_checker:
                    success, _, error = await self.health_checker.perform_health_check(state.health_check)
                    
                    if success and state.consecutive_failures <= state.recovery_threshold:
                        await self._handle_recovery(state)
    
    async def _handle_recovery(self, state: FailoverState):
        """Handle endpoint recovery."""
        logger.info(f"Endpoint {state.endpoint_id} has recovered")
        
        state.recovery_count += 1
        state.last_recovery_time = datetime.utcnow()
        
        # Update statistics
        if state.failover_count > 0:
            self.statistics["successful_recoveries"] += 1
        
        # Track recovery event
        event_tracker.track_system_event(
            "endpoint_recovered",
            EventLevel.INFO,
            {
                "endpoint_id": state.endpoint_id,
                "failover_count": state.failover_count,
                "recovery_count": state.recovery_count
            }
        )
    
    async def _update_statistics(self):
        """Update failover statistics."""
        # Calculate overall availability
        total_endpoints = len(self.failover_states)
        if total_endpoints > 0:
            healthy_endpoints = sum(
                1 for state in self.failover_states.values()
                if state.current_status == HealthStatus.HEALTHY
            )
            
            overall_availability = (healthy_endpoints / total_endpoints) * 100
            self.statistics["overall_availability"] = overall_availability
        
        self.statistics["last_updated"] = datetime.utcnow()
    
    async def add_endpoint(self, endpoint: ProxyEndpoint):
        """Add endpoint to failover management."""
        try:
            # Create health check
            health_check = HealthCheck(
                name=f"health_check_{endpoint.id}",
                endpoint_id=endpoint.id,
                url=f"{endpoint.upstream_url}/health",
                timeout_seconds=min(10.0, endpoint.health_check_interval_seconds),
                check_interval_seconds=endpoint.health_check_interval_seconds,
                failure_threshold=max(1, endpoint.failure_threshold // 10),  # Convert to health check threshold
                expected_status_codes=[200, 204]  # Accept health endpoints
            )
            
            # Create failover state
            failover_state = FailoverState(
                endpoint_id=endpoint.id,
                current_status=HealthStatus.UNKNOWN,
                previous_status=HealthStatus.UNKNOWN,
                status_change_time=datetime.utcnow(),
                health_check=health_check
            )
            
            self.failover_states[endpoint.id] = failover_state
            
            logger.info(f"Added endpoint to failover management: {endpoint.id}")
            
        except Exception as e:
            logger.error(f"Failed to add endpoint {endpoint.id}: {e}")
            raise
    
    async def remove_endpoint(self, endpoint_id: str):
        """Remove endpoint from failover management."""
        if endpoint_id in self.failover_states:
            del self.failover_states[endpoint_id]
            
        if endpoint_id in self.failover_chains:
            del self.failover_chains[endpoint_id]
        
        logger.info(f"Removed endpoint from failover management: {endpoint_id}")
    
    async def set_failover_chain(self, primary_endpoint_id: str, fallback_endpoints: List[str]):
        """Set failover chain for endpoint."""
        failover_chain = FailoverChain(
            primary_endpoint_id=primary_endpoint_id,
            fallback_endpoints=fallback_endpoints
        )
        
        self.failover_chains[primary_endpoint_id] = failover_chain
        
        logger.info(
            f"Set failover chain for {primary_endpoint_id}: {' -> '.join([primary_endpoint_id] + fallback_endpoints)}"
        )
    
    def get_endpoint_status(self, endpoint_id: str) -> Optional[HealthStatus]:
        """Get current status of endpoint."""
        state = self.failover_states.get(endpoint_id)
        return state.current_status if state else None
    
    def get_all_endpoint_statuses(self) -> Dict[str, HealthStatus]:
        """Get status of all endpoints."""
        return {
            endpoint_id: state.current_status
            for endpoint_id, state in self.failover_states.items()
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get failover manager statistics."""
        return {
            "total_endpoints": len(self.failover_states),
            "healthy_endpoints": sum(
                1 for state in self.failover_states.values()
                if state.current_status == HealthStatus.HEALTHY
            ),
            "degraded_endpoints": sum(
                1 for state in self.failover_states.values()
                if state.current_status == HealthStatus.DEGRADED
            ),
            "unhealthy_endpoints": sum(
                1 for state in self.failover_states.values()
                if state.current_status == HealthStatus.UNHEALTHY
            ),
            "offline_endpoints": sum(
                1 for state in self.failover_states.values()
                if state.current_status == HealthStatus.OFFLINE
            ),
            "total_failovers": self.statistics["total_failovers"],
            "successful_recoveries": self.statistics["successful_recoveries"],
            "overall_availability": self.statistics.get("overall_availability", 0.0),
            "endpoint_details": {
                endpoint_id: {
                    "status": state.current_status.value,
                    "availability_percent": state.availability_percent,
                    "avg_response_time_ms": state.avg_response_time_ms,
                    "consecutive_failures": state.consecutive_failures,
                    "last_check": state.health_check.last_check_time.isoformat() if state.health_check.last_check_time else None
                }
                for endpoint_id, state in self.failover_states.items()
            },
            "last_updated": self.statistics["last_updated"].isoformat()
        }
    
    async def trigger_manual_failover(self, endpoint_id: str, reason: str = "manual") -> bool:
        """Manually trigger failover for endpoint."""
        state = self.failover_states.get(endpoint_id)
        
        if state:
            await self._trigger_failover(state, reason)
            return True
        
        return False
    
    async def force_health_check(self, endpoint_id: str) -> bool:
        """Force immediate health check for endpoint."""
        state = self.failover_states.get(endpoint_id)
        
        if state and self.health_checker:
            try:
                success, _, error = await self.health_checker.perform_health_check(state.health_check)
                await self._evaluate_health_status(state, success, error)
                return True
            except Exception as e:
                logger.error(f"Force health check failed for {endpoint_id}: {e}")
        
        return False
    
    async def shutdown(self):
        """Shutdown failover manager and cleanup resources."""
        logger.info("Shutting down failover manager...")
        
        try:
            # Cancel background tasks
            tasks = [self.health_check_task, self.recovery_check_task, self.statistics_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[task for task in tasks if task], return_exceptions=True)
            
            # Close HTTP client
            if self.health_checker:
                await self.health_checker.http_client.aclose()
            
            logger.info("Failover manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during failover manager shutdown: {e}")
