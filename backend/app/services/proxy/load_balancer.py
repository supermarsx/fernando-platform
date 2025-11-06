"""
Load Balancer Implementation

Multiple load balancing algorithms for proxy endpoints:
- Round Robin
- Least Connections
- Weighted Round Robin
- Weighted Least Connections
- IP Hash
- Random
- Health-based

Features:
- Dynamic endpoint weight adjustment
- Health-aware load balancing
- Performance-based routing
- Failover handling
"""

import asyncio
import hashlib
import random
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

from app.models.proxy import ProxyEndpoint
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class LoadBalancingAlgorithm(Enum):
    """Available load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    WEIGHTED_LEAST_CONNECTIONS = "weighted_least_connections"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    HEALTH_BASED = "health_based"


@dataclass
class EndpointLoad:
    """Represents load information for an endpoint."""
    endpoint: ProxyEndpoint
    current_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    last_accessed: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    health_score: float = 100.0
    active: bool = True


@dataclass
class LoadBalancingRequest:
    """Request context for load balancing decision."""
    client_ip: str
    endpoint_group: str
    request_time: datetime
    method: str
    path: str
    weight_preference: float = 1.0


@dataclass
class LoadBalancingResult:
    """Result of load balancing decision."""
    selected_endpoint: ProxyEndpoint
    algorithm_used: LoadBalancingAlgorithm
    confidence_score: float
    reasoning: str
    estimated_load: float


class RoundRobinBalancer:
    """Round Robin load balancer."""
    
    def __init__(self):
        self.current_index = 0
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint using round robin algorithm."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Round robin selection
        selected = active_endpoints[self.current_index % len(active_endpoints)]
        self.current_index += 1
        
        return selected.endpoint


class LeastConnectionsBalancer:
    """Least Connections load balancer."""
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint with least connections."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Select endpoint with minimum connections
        selected = min(active_endpoints, key=lambda ep: ep.current_connections)
        
        return selected.endpoint


class WeightedRoundRobinBalancer:
    """Weighted Round Robin load balancer."""
    
    def __init__(self):
        self.current_weights: Dict[str, float] = {}
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint using weighted round robin algorithm."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Calculate total weight
        total_weight = sum(ep.endpoint.weight for ep in active_endpoints)
        
        if total_weight == 0:
            # Fallback to round robin if no weights
            return active_endpoints[0].endpoint
        
        # Initialize current weights if needed
        for ep in active_endpoints:
            endpoint_id = ep.endpoint.id
            if endpoint_id not in self.current_weights:
                self.current_weights[endpoint_id] = ep.endpoint.weight
        
        # Select endpoint based on weighted round robin
        selected_endpoint = None
        max_current_weight = -1
        
        for ep in active_endpoints:
            endpoint_id = ep.endpoint.id
            self.current_weights[endpoint_id] += ep.endpoint.weight
            
            if self.current_weights[endpoint_id] > max_current_weight:
                max_current_weight = self.current_weights[endpoint_id]
                selected_endpoint = ep
        
        if selected_endpoint:
            self.current_weights[selected_endpoint.endpoint.id] -= total_weight
        
        return selected_endpoint.endpoint


class WeightedLeastConnectionsBalancer:
    """Weighted Least Connections load balancer."""
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint using weighted least connections algorithm."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Calculate effective load for each endpoint
        endpoint_loads = []
        for ep in active_endpoints:
            weight = ep.endpoint.weight if ep.endpoint.weight > 0 else 1
            effective_load = ep.current_connections / weight
            endpoint_loads.append((ep, effective_load))
        
        # Select endpoint with minimum effective load
        selected_ep = min(endpoint_loads, key=lambda x: x[1])[0]
        
        return selected_ep.endpoint


class IPHashBalancer:
    """IP Hash load balancer for session affinity."""
    
    def __init__(self):
        self.hash_ring: Dict[int, ProxyEndpoint] = {}
        self.sorted_keys: List[int] = []
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint using IP hash algorithm."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Build hash ring if needed
        if not self.hash_ring:
            await self._build_hash_ring(active_endpoints)
        
        # Calculate hash for client IP
        client_hash = self._calculate_ip_hash(request.client_ip)
        
        # Find endpoint in hash ring
        return self._find_endpoint_in_ring(client_hash, active_endpoints)
    
    def _calculate_ip_hash(self, client_ip: str) -> int:
        """Calculate hash for client IP."""
        return int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
    
    async def _build_hash_ring(self, endpoints: List[EndpointLoad]):
        """Build consistent hash ring."""
        self.hash_ring.clear()
        self.sorted_keys.clear()
        
        for ep in endpoints:
            # Create virtual nodes for better distribution
            for i in range(ep.endpoint.weight if ep.endpoint.weight > 0 else 1):
                key = self._calculate_ip_hash(f"{ep.endpoint.id}:{i}")
                self.hash_ring[key] = ep.endpoint
        
        self.sorted_keys = sorted(self.hash_ring.keys())
    
    def _find_endpoint_in_ring(self, client_hash: int, endpoints: List[EndpointLoad]) -> ProxyEndpoint:
        """Find endpoint in hash ring."""
        if not self.sorted_keys:
            return endpoints[0].endpoint
        
        # Find the first key greater than or equal to client hash
        for key in self.sorted_keys:
            if key >= client_hash:
                return self.hash_ring[key]
        
        # Wrap around to the first key
        return self.hash_ring[self.sorted_keys[0]]


class RandomBalancer:
    """Random load balancer."""
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint randomly."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Select random endpoint
        selected = random.choice(active_endpoints)
        
        return selected.endpoint


class HealthBasedBalancer:
    """Health-based load balancer."""
    
    def __init__(self):
        self.health_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    async def select_endpoint(
        self,
        endpoints: List[EndpointLoad],
        request: LoadBalancingRequest
    ) -> Optional[ProxyEndpoint]:
        """Select endpoint based on health metrics."""
        if not endpoints:
            return None
        
        # Filter active endpoints
        active_endpoints = [ep for ep in endpoints if ep.active]
        
        if not active_endpoints:
            return None
        
        # Score endpoints based on health
        scored_endpoints = []
        
        for ep in active_endpoints:
            health_score = self._calculate_health_score(ep)
            scored_endpoints.append((ep, health_score))
        
        # Sort by health score (highest first)
        scored_endpoints.sort(key=lambda x: x[1], reverse=True)
        
        # Select best endpoint
        selected_ep = scored_endpoints[0][0]
        
        return selected_ep.endpoint
    
    def _calculate_health_score(self, endpoint_load: EndpointLoad) -> float:
        """Calculate health score for endpoint."""
        score = 100.0
        
        # Consider current connections
        if endpoint_load.current_connections > 100:
            score -= 20
        elif endpoint_load.current_connections > 50:
            score -= 10
        
        # Consider response time
        if endpoint_load.avg_response_time > 2000:  # 2 seconds
            score -= 30
        elif endpoint_load.avg_response_time > 1000:  # 1 second
            score -= 15
        
        # Consider error rate
        if endpoint_load.total_requests > 0:
            error_rate = endpoint_load.failed_requests / endpoint_load.total_requests
            score -= error_rate * 50
        
        # Consider recent failures
        if endpoint_load.last_failure:
            time_since_failure = (datetime.utcnow() - endpoint_load.last_failure).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                score -= 25
        
        # Consider endpoint weight
        if endpoint_load.endpoint.weight > 1:
            score += (endpoint_load.endpoint.weight - 1) * 5
        
        return max(0.0, score)
    
    def update_health_metrics(self, endpoint_id: str, response_time: float, success: bool):
        """Update health metrics for endpoint."""
        self.health_history[endpoint_id].append({
            "timestamp": datetime.utcnow(),
            "response_time": response_time,
            "success": success
        })


class LoadBalancer:
    """
    Main load balancer orchestrator.
    
    Provides various load balancing algorithms with health awareness,
    performance monitoring, and dynamic adjustment.
    """
    
    def __init__(self):
        """Initialize the load balancer."""
        self.algorithm = LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN
        self.endpoint_loads: Dict[str, EndpointLoad] = {}
        
        # Initialize algorithm instances
        self.balancers = {
            LoadBalancingAlgorithm.ROUND_ROBIN: RoundRobinBalancer(),
            LoadBalancingAlgorithm.LEAST_CONNECTIONS: LeastConnectionsBalancer(),
            LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinBalancer(),
            LoadBalancingAlgorithm.WEIGHTED_LEAST_CONNECTIONS: WeightedLeastConnectionsBalancer(),
            LoadBalancingAlgorithm.IP_HASH: IPHashBalancer(),
            LoadBalancingAlgorithm.RANDOM: RandomBalancer(),
            LoadBalancingAlgorithm.HEALTH_BASED: HealthBasedBalancer()
        }
        
        # Current algorithm instance
        self.current_balancer = self.balancers[self.algorithm]
        
        # Statistics
        self.statistics = {
            "total_requests": 0,
            "algorithm_usage": defaultdict(int),
            "endpoint_distribution": defaultdict(int),
            "last_update": datetime.utcnow()
        }
        
        logger.info(f"Load balancer initialized with algorithm: {self.algorithm.value}")
    
    async def initialize(self):
        """Initialize the load balancer."""
        try:
            # Load endpoint configurations
            await self._load_endpoint_configs()
            
            logger.info("Load balancer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize load balancer: {e}")
            raise
    
    async def _load_endpoint_configs(self):
        """Load endpoint configurations from database."""
        # This would load proxy endpoints from database
        # For now, create placeholder endpoints
        pass
    
    async def select_endpoint(
        self,
        endpoint_group: str,
        client_ip: str,
        method: str,
        path: str
    ) -> Optional[LoadBalancingResult]:
        """
        Select best endpoint for request using load balancing algorithm.
        
        Args:
            endpoint_group: Group/category of endpoints
            client_ip: Client IP address
            method: HTTP method
            path: Request path
            
        Returns:
            LoadBalancingResult with selected endpoint and reasoning
        """
        start_time = time.time()
        
        try:
            # Get endpoints for this group
            endpoints = await self._get_endpoints_for_group(endpoint_group)
            
            if not endpoints:
                logger.warning(f"No endpoints available for group: {endpoint_group}")
                return None
            
            # Create load balancing request
            request = LoadBalancingRequest(
                client_ip=client_ip,
                endpoint_group=endpoint_group,
                request_time=datetime.utcnow(),
                method=method,
                path=path
            )
            
            # Select endpoint using current algorithm
            selected_endpoint = await self.current_balancer.select_endpoint(
                endpoints, request
            )
            
            if not selected_endpoint:
                return None
            
            # Calculate reasoning and confidence
            reasoning = self._build_selection_reasoning(selected_endpoint, endpoints)
            confidence_score = self._calculate_confidence_score(selected_endpoint, endpoints)
            
            # Update statistics
            await self._update_statistics(selected_endpoint, reasoning)
            
            # Record load balancing decision
            decision_time = (time.time() - start_time) * 1000
            
            event_tracker.track_performance_event(
                "load_balancer_selection",
                decision_time,
                {
                    "algorithm": self.algorithm.value,
                    "endpoint_group": endpoint_group,
                    "selected_endpoint": selected_endpoint.id,
                    "confidence_score": confidence_score
                }
            )
            
            return LoadBalancingResult(
                selected_endpoint=selected_endpoint,
                algorithm_used=self.algorithm,
                confidence_score=confidence_score,
                reasoning=reasoning,
                estimated_load=0.0  # Would calculate actual load
            )
            
        except Exception as e:
            logger.error(f"Load balancing selection failed: {e}")
            return None
    
    async def _get_endpoints_for_group(self, group: str) -> List[EndpointLoad]:
        """Get endpoints for a specific group."""
        # This would query endpoints by group/category
        # For now, return all endpoints
        
        endpoints = []
        for endpoint_load in self.endpoint_loads.values():
            if endpoint_load.active:
                endpoints.append(endpoint_load)
        
        return endpoints
    
    def _build_selection_reasoning(self, selected_endpoint: ProxyEndpoint, all_endpoints: List[EndpointLoad]) -> str:
        """Build human-readable reasoning for selection."""
        reasons = []
        
        # Algorithm-specific reasoning
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            reasons.append("Round robin rotation")
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            reasons.append("Least connections load")
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            reasons.append("Weighted round robin")
            reasons.append(f"Weight: {selected_endpoint.weight}")
        elif self.algorithm == LoadBalancingAlgorithm.HEALTH_BASED:
            reasons.append("Health-based selection")
        
        # Endpoint-specific reasoning
        if selected_endpoint.priority > 0:
            reasons.append(f"High priority ({selected_endpoint.priority})")
        
        return "; ".join(reasons)
    
    def _calculate_confidence_score(self, selected_endpoint: ProxyEndpoint, all_endpoints: List[EndpointLoad]) -> float:
        """Calculate confidence score for selection."""
        score = 80.0  # Base score
        
        # Adjust based on endpoint health
        endpoint_load = self.endpoint_loads.get(selected_endpoint.id)
        if endpoint_load:
            score += endpoint_load.health_score * 0.2  # Max 20 points
            
            # Adjust based on current load
            if endpoint_load.current_connections < 10:
                score += 10
            elif endpoint_load.current_connections > 50:
                score -= 10
        
        # Adjust based on algorithm reliability
        if self.algorithm in [LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN, LoadBalancingAlgorithm.LEAST_CONNECTIONS]:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    async def _update_statistics(self, selected_endpoint: ProxyEndpoint, reasoning: str):
        """Update load balancer statistics."""
        self.statistics["total_requests"] += 1
        self.statistics["algorithm_usage"][self.algorithm.value] += 1
        self.statistics["endpoint_distribution"][selected_endpoint.id] += 1
        self.statistics["last_update"] = datetime.utcnow()
    
    async def update_endpoint_load(
        self,
        endpoint_id: str,
        connections_delta: int = 0,
        response_time_ms: float = 0.0,
        success: bool = True
    ):
        """Update load metrics for endpoint."""
        endpoint_load = self.endpoint_loads.get(endpoint_id)
        
        if endpoint_load:
            # Update connection count
            endpoint_load.current_connections = max(0, endpoint_load.current_connections + connections_delta)
            
            # Update response time metrics
            endpoint_load.total_requests += 1
            endpoint_load.total_response_time += response_time_ms
            endpoint_load.avg_response_time = endpoint_load.total_response_time / endpoint_load.total_requests
            
            # Update success/failure counts
            if success:
                endpoint_load.successful_requests += 1
                endpoint_load.last_success = datetime.utcnow()
            else:
                endpoint_load.failed_requests += 1
                endpoint_load.last_failure = datetime.utcnow()
            
            # Update last accessed
            endpoint_load.last_accessed = datetime.utcnow()
            
            # Update health score
            await self._calculate_endpoint_health(endpoint_load)
        else:
            logger.warning(f"Unknown endpoint ID: {endpoint_id}")
    
    async def _calculate_endpoint_health(self, endpoint_load: EndpointLoad):
        """Calculate health score for endpoint."""
        health_score = 100.0
        
        # Connection-based metrics
        if endpoint_load.current_connections > 100:
            health_score -= 30
        elif endpoint_load.current_connections > 50:
            health_score -= 15
        
        # Response time-based metrics
        if endpoint_load.avg_response_time > 5000:  # 5 seconds
            health_score -= 40
        elif endpoint_load.avg_response_time > 2000:  # 2 seconds
            health_score -= 20
        elif endpoint_load.avg_response_time > 1000:  # 1 second
            health_score -= 10
        
        # Error rate-based metrics
        if endpoint_load.total_requests > 0:
            error_rate = endpoint_load.failed_requests / endpoint_load.total_requests
            health_score -= error_rate * 50
        
        # Recency of failures
        if endpoint_load.last_failure:
            time_since_failure = (datetime.utcnow() - endpoint_load.last_failure).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                health_score -= 20
        
        endpoint_load.health_score = max(0.0, min(100.0, health_score))
        
        # Mark endpoint as inactive if health is too low
        endpoint_load.active = endpoint_load.health_score > 20.0
    
    async def set_algorithm(self, algorithm: LoadBalancingAlgorithm):
        """Set load balancing algorithm."""
        if algorithm in self.balancers:
            self.algorithm = algorithm
            self.current_balancer = self.balancers[algorithm]
            
            logger.info(f"Load balancing algorithm changed to: {algorithm.value}")
            
            event_tracker.track_system_event(
                "load_balancer_algorithm_changed",
                EventLevel.INFO,
                {"new_algorithm": algorithm.value}
            )
        else:
            raise ValueError(f"Unknown load balancing algorithm: {algorithm}")
    
    async def add_endpoint(self, endpoint: ProxyEndpoint):
        """Add endpoint to load balancer."""
        endpoint_load = EndpointLoad(endpoint=endpoint)
        self.endpoint_loads[endpoint.id] = endpoint_load
        
        logger.info(f"Added endpoint to load balancer: {endpoint.id}")
    
    async def remove_endpoint(self, endpoint_id: str):
        """Remove endpoint from load balancer."""
        endpoint_load = self.endpoint_loads.pop(endpoint_id, None)
        
        if endpoint_load:
            logger.info(f"Removed endpoint from load balancer: {endpoint_id}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        # Calculate endpoint distribution percentages
        total_requests = self.statistics["total_requests"]
        endpoint_distribution = {}
        
        for endpoint_id, count in self.statistics["endpoint_distribution"].items():
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            endpoint_distribution[endpoint_id] = {
                "requests": count,
                "percentage": percentage
            }
        
        return {
            "total_requests": total_requests,
            "algorithm": self.algorithm.value,
            "algorithm_usage": dict(self.statistics["algorithm_usage"]),
            "endpoint_distribution": endpoint_distribution,
            "endpoint_health": {
                endpoint_id: {
                    "health_score": ep.health_score,
                    "active": ep.active,
                    "current_connections": ep.current_connections,
                    "avg_response_time_ms": ep.avg_response_time
                }
                for endpoint_id, ep in self.endpoint_loads.items()
            },
            "last_update": self.statistics["last_update"].isoformat()
        }
    
    async def get_endpoint_loads(self) -> List[EndpointLoad]:
        """Get current endpoint loads."""
        return list(self.endpoint_loads.values())
    
    async def shutdown(self):
        """Shutdown load balancer."""
        logger.info("Shutting down load balancer...")
        
        # Reset statistics
        self.statistics.clear()
        
        # Clear endpoint loads
        self.endpoint_loads.clear()
        
        logger.info("Load balancer shutdown complete")


class AdaptiveLoadBalancer(LoadBalancer):
    """
    Adaptive load balancer that automatically adjusts algorithm based on
    performance metrics and system conditions.
    """
    
    def __init__(self):
        super().__init__()
        self.adaptation_threshold = 100  # Number of requests before checking adaptation
        self.min_requests_for_adaptation = 1000
        self.performance_window = 300  # 5 minutes
    
    async def should_adapt_algorithm(self) -> bool:
        """Check if load balancing algorithm should be adapted."""
        # This would analyze performance metrics and decide if algorithm change is needed
        # For now, return False
        
        return False
    
    async def adapt_algorithm(self):
        """Adapt load balancing algorithm based on performance."""
        # This would implement logic to switch algorithms based on:
        # - Average response times
        # - Error rates
        # - Connection distribution
        # - Throughput metrics
        
        pass
