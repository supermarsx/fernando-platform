"""
Intelligent Request Router

Routes incoming requests to appropriate proxy endpoints based on:
- Path patterns
- HTTP methods
- Load balancing strategies
- Health status
- Priority and weight

Features:
- Pattern matching with wildcards
- Priority-based routing
- Health-aware routing
- Load balancing integration
- Dynamic route updates
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from app.models.proxy import ProxyEndpoint
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


@dataclass
class RouteMatch:
    """Result of route matching."""
    endpoint: ProxyEndpoint
    match_score: float
    matched_pattern: str
    wildcard_values: Dict[str, str] = field(default_factory=dict)


@dataclass
class RouteStats:
    """Statistics for route performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    last_accessed: Optional[datetime] = None
    weight_adjusted_score: float = 1.0


class RoutePattern:
    """Represents a route pattern with compiled regex."""
    
    def __init__(self, pattern: str):
        """Initialize route pattern."""
        self.pattern = pattern
        self.regex = self._compile_pattern(pattern)
        self.wildcard_names = self._extract_wildcard_names(pattern)
    
    @staticmethod
    def _compile_pattern(pattern: str) -> re.Pattern:
        """Convert path pattern to regex."""
        # Convert path pattern to regex
        # Examples:
        # "/api/llm/*" -> r"^/api/llm/.*$"
        # "/api/documents/{id}" -> r"^/api/documents/([^/]+)$"
        # "/api/*/items/{type}" -> r"^/api/([^/]+)/items/([^/]+)$"
        
        regex_pattern = pattern
        regex_pattern = regex_pattern.replace(".", "\\.")
        regex_pattern = regex_pattern.replace("*", ".*")
        regex_pattern = regex_pattern.replace("{", "(")
        regex_pattern = regex_pattern.replace("}", ")")
        
        return re.compile(f"^{regex_pattern}$")
    
    @staticmethod
    def _extract_wildcard_names(pattern: str) -> List[str]:
        """Extract wildcard variable names from pattern."""
        names = []
        in_wildcard = False
        current_name = ""
        
        for char in pattern:
            if char == "{":
                in_wildcard = True
                current_name = ""
            elif char == "}":
                if current_name:
                    names.append(current_name)
                in_wildcard = False
                current_name = ""
            elif in_wildcard:
                current_name += char
        
        return names
    
    def matches(self, path: str) -> Tuple[bool, Dict[str, str]]:
        """Check if path matches this pattern and return wildcard values."""
        match = self.regex.match(path)
        if not match:
            return False, {}
        
        # Extract wildcard values
        wildcard_values = {}
        for i, group in enumerate(match.groups()):
            if i < len(self.wildcard_names):
                wildcard_values[self.wildcard_names[i]] = group
        
        return True, wildcard_values
    
    def __repr__(self):
        return f"RoutePattern('{self.pattern}')"


class RequestRouter:
    """
    Intelligent request router for proxy endpoints.
    
    Handles:
    - Route pattern matching
    - Priority-based routing
    - Health-aware routing
    - Load balancing integration
    """
    
    def __init__(self):
        """Initialize the request router."""
        self.routes: List[Tuple[RoutePattern, ProxyEndpoint]] = []
        self.route_stats: Dict[str, RouteStats] = defaultdict(RouteStats)
        self.health_cache: Dict[str, datetime] = {}
        self.health_cache_ttl = 30  # seconds
        
        # Route categorization
        self.exact_routes: List[Tuple[RoutePattern, ProxyEndpoint]] = []
        self.prefix_routes: List[Tuple[RoutePattern, ProxyEndpoint]] = []
        self.regex_routes: List[Tuple[RoutePattern, ProxyEndpoint]] = []
        
        logger.info("Request router initialized")
    
    async def initialize(self):
        """Initialize the router by loading routes from database."""
        try:
            # Load all active proxy endpoints from database
            # This would typically use a database session
            endpoints = await self._load_endpoints_from_db()
            
            # Build route patterns
            for endpoint in endpoints:
                if endpoint.is_active:
                    await self.add_route(endpoint)
            
            logger.info(f"Loaded {len(self.routes)} routes")
            
        except Exception as e:
            logger.error(f"Failed to initialize request router: {e}")
            raise
    
    async def _load_endpoints_from_db(self) -> List[ProxyEndpoint]:
        """Load proxy endpoints from database."""
        # This would typically use SQLAlchemy to query the database
        # For now, return empty list as placeholder
        return []
    
    async def add_route(self, endpoint: ProxyEndpoint):
        """Add a new route."""
        try:
            pattern = RoutePattern(endpoint.path_pattern)
            route = (pattern, endpoint)
            
            self.routes.append(route)
            
            # Categorize route for optimization
            if endpoint.path_pattern.endswith("/*"):
                self.prefix_routes.append(route)
            elif "{" in endpoint.path_pattern:
                self.regex_routes.append(route)
            else:
                self.exact_routes.append(route)
            
            logger.debug(f"Added route: {endpoint.path_pattern} -> {endpoint.upstream_url}")
            
        except Exception as e:
            logger.error(f"Failed to add route {endpoint.path_pattern}: {e}")
            raise
    
    async def remove_route(self, endpoint_id: str):
        """Remove a route by endpoint ID."""
        # Find and remove route
        self.routes = [
            (pattern, endpoint) for pattern, endpoint in self.routes
            if endpoint.id != endpoint_id
        ]
        
        # Update categorized lists
        self.exact_routes = [
            (pattern, endpoint) for pattern, endpoint in self.exact_routes
            if endpoint.id != endpoint_id
        ]
        self.prefix_routes = [
            (pattern, endpoint) for pattern, endpoint in self.prefix_routes
            if endpoint.id != endpoint_id
        ]
        self.regex_routes = [
            (pattern, endpoint) for pattern, endpoint in self.regex_routes
            if endpoint.id != endpoint_id
        ]
        
        # Remove from cache
        self.health_cache.pop(endpoint_id, None)
        self.route_stats.pop(endpoint_id, None)
    
    async def route_request(self, request) -> Optional[ProxyEndpoint]:
        """
        Route request to appropriate endpoint.
        
        This method:
        1. Matches request path against route patterns
        2. Filters by HTTP method
        3. Considers health status
        4. Applies load balancing strategy
        5. Returns best matching endpoint
        """
        try:
            path = request.path
            method = request.method
            
            # Find matching routes
            matches = await self._find_matching_routes(path, method)
            
            if not matches:
                logger.debug(f"No matching route found for {method} {path}")
                return None
            
            # Filter by health and priority
            healthy_matches = await self._filter_healthy_routes(matches)
            
            if not healthy_matches:
                logger.warning(f"No healthy routes found for {method} {path}")
                return matches[0].endpoint  # Fall back to any match
            
            # Select best route based on load balancing
            selected_match = await self._select_best_route(healthy_matches, request)
            
            if selected_match:
                # Update route statistics
                await self._update_route_stats(selected_match.endpoint.id)
                
                # Track routing event
                event_tracker.track_performance_event(
                    "request_routing",
                    0.0,  # Routing is very fast
                    {
                        "endpoint": selected_match.endpoint.id,
                        "path": path,
                        "method": method,
                        "match_score": selected_match.match_score
                    }
                )
                
                return selected_match.endpoint
            else:
                logger.warning(f"Failed to select route for {method} {path}")
                return matches[0].endpoint  # Fallback
                
        except Exception as e:
            logger.error(f"Error routing request: {e}")
            return None
    
    async def _find_matching_routes(self, path: str, method: str) -> List[RouteMatch]:
        """Find all routes that match the request path and method."""
        matches = []
        
        # Try exact matches first
        for pattern, endpoint in self.exact_routes:
            if self._method_matches(endpoint.method, method):
                matches.extend(await self._evaluate_match(pattern, endpoint, path))
        
        # Try prefix matches
        for pattern, endpoint in self.prefix_routes:
            if self._method_matches(endpoint.method, method):
                matches.extend(await self._evaluate_match(pattern, endpoint, path))
        
        # Try regex matches
        for pattern, endpoint in self.regex_routes:
            if self._method_matches(endpoint.method, method):
                matches.extend(await self._evaluate_match(pattern, endpoint, path))
        
        # Sort by match score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        
        return matches
    
    def _method_matches(self, endpoint_method: str, request_method: str) -> bool:
        """Check if endpoint method matches request method."""
        if endpoint_method.upper() == "ANY":
            return True
        return endpoint_method.upper() == request_method.upper()
    
    async def _evaluate_match(self, pattern: RoutePattern, endpoint: ProxyEndpoint, path: str) -> List[RouteMatch]:
        """Evaluate a single route pattern match."""
        try:
            matches, wildcard_values = pattern.matches(path)
            if not matches:
                return []
            
            # Calculate match score
            match_score = await self._calculate_match_score(endpoint, pattern, path, wildcard_values)
            
            return [RouteMatch(
                endpoint=endpoint,
                match_score=match_score,
                matched_pattern=pattern.pattern,
                wildcard_values=wildcard_values
            )]
            
        except Exception as e:
            logger.error(f"Error evaluating match for {pattern.pattern}: {e}")
            return []
    
    async def _calculate_match_score(
        self,
        endpoint: ProxyEndpoint,
        pattern: RoutePattern,
        path: str,
        wildcard_values: Dict[str, str]
    ) -> float:
        """Calculate match score for a route."""
        score = 0.0
        
        # Base score from endpoint priority
        score += endpoint.priority * 10
        
        # Prefer exact matches over wildcard matches
        if not wildcard_values:
            score += 100
        else:
            score += len(wildcard_values) * 10
        
        # Consider endpoint weight
        score += endpoint.weight
        
        # Consider recent activity (prefer active endpoints)
        stats = self.route_stats.get(endpoint.id)
        if stats and stats.last_accessed:
            time_since_access = (datetime.utcnow() - stats.last_accessed).total_seconds()
            if time_since_access < 300:  # 5 minutes
                score += 20
        
        return score
    
    async def _filter_healthy_routes(self, matches: List[RouteMatch]) -> List[RouteMatch]:
        """Filter matches by health status."""
        healthy_matches = []
        
        for match in matches:
            endpoint = match.endpoint
            
            # Check if endpoint is healthy
            is_healthy = await self._check_endpoint_health(endpoint)
            
            if is_healthy:
                healthy_matches.append(match)
            else:
                logger.debug(f"Endpoint {endpoint.id} is unhealthy, skipping")
        
        return healthy_matches
    
    async def _check_endpoint_health(self, endpoint: ProxyEndpoint) -> bool:
        """Check if endpoint is healthy."""
        try:
            # Use cached health status if available and recent
            cache_key = endpoint.id
            last_check = self.health_cache.get(cache_key)
            
            if last_check:
                if (datetime.utcnow() - last_check).total_seconds() < self.health_cache_ttl:
                    # Use cached health status
                    return True  # Assume healthy if cached
            
            # Perform health check
            is_healthy = await self._perform_health_check(endpoint)
            
            # Update cache
            self.health_cache[cache_key] = datetime.utcnow()
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for endpoint {endpoint.id}: {e}")
            return False
    
    async def _perform_health_check(self, endpoint: ProxyEndpoint) -> bool:
        """Perform health check for endpoint."""
        try:
            # This would typically make a lightweight request to the endpoint
            # For now, return True as placeholder
            # In production, this would:
            # 1. Make HTTP HEAD request to endpoint upstream_url
            # 2. Check response status and timing
            # 3. Verify endpoint-specific health criteria
            
            return True
            
        except Exception as e:
            logger.error(f"Health check error for {endpoint.id}: {e}")
            return False
    
    async def _select_best_route(self, matches: List[RouteMatch], request) -> Optional[RouteMatch]:
        """Select best route from healthy matches using load balancing."""
        if not matches:
            return None
        
        if len(matches) == 1:
            return matches[0]
        
        # Apply load balancing strategy
        # This would integrate with the load balancer component
        # For now, select based on score and weight
        
        weighted_matches = []
        total_weight = sum(match.endpoint.weight for match in matches)
        
        for match in matches:
            # Calculate selection probability based on weight and score
            weight_factor = match.endpoint.weight / total_weight if total_weight > 0 else 0
            score_factor = match.match_score / 1000  # Normalize score
            
            selection_score = weight_factor + score_factor
            weighted_matches.append((match, selection_score))
        
        # Sort by selection score and pick the best
        weighted_matches.sort(key=lambda x: x[1], reverse=True)
        
        return weighted_matches[0][0]
    
    async def _update_route_stats(self, endpoint_id: str):
        """Update route usage statistics."""
        stats = self.route_stats.get(endpoint_id)
        if stats:
            stats.total_requests += 1
            stats.last_accessed = datetime.utcnow()
    
    async def get_route_statistics(self) -> Dict[str, Any]:
        """Get route usage statistics."""
        stats = {}
        
        for endpoint_id, route_stats in self.route_stats.items():
            stats[endpoint_id] = {
                "total_requests": route_stats.total_requests,
                "successful_requests": route_stats.successful_requests,
                "failed_requests": route_stats.failed_requests,
                "success_rate": (
                    route_stats.successful_requests / route_stats.total_requests
                    if route_stats.total_requests > 0 else 0.0
                ) * 100,
                "avg_response_time_ms": route_stats.avg_response_time_ms,
                "last_accessed": route_stats.last_accessed.isoformat() if route_stats.last_accessed else None
            }
        
        return stats
    
    async def reload_routes(self):
        """Reload all routes from database."""
        logger.info("Reloading route configuration...")
        
        try:
            # Clear existing routes
            self.routes.clear()
            self.exact_routes.clear()
            self.prefix_routes.clear()
            self.regex_routes.clear()
            
            # Reload endpoints
            endpoints = await self._load_endpoints_from_db()
            
            # Add active routes
            for endpoint in endpoints:
                if endpoint.is_active:
                    await self.add_route(endpoint)
            
            # Clear caches
            self.health_cache.clear()
            
            logger.info(f"Route configuration reloaded: {len(self.routes)} routes active")
            
            # Track reload event
            event_tracker.track_system_event(
                "proxy_routes_reloaded",
                EventLevel.INFO,
                {"active_routes": len(self.routes)}
            )
            
        except Exception as e:
            logger.error(f"Failed to reload routes: {e}")
            raise
    
    async def get_route_summary(self) -> Dict[str, Any]:
        """Get summary of all routes."""
        summary = {
            "total_routes": len(self.routes),
            "exact_routes": len(self.exact_routes),
            "prefix_routes": len(self.prefix_routes),
            "regex_routes": len(self.regex_routes),
            "healthy_endpoints": 0,
            "unhealthy_endpoints": 0
        }
        
        # Check health status
        for _, endpoint in self.routes:
            if endpoint.is_active:
                try:
                    is_healthy = await self._check_endpoint_health(endpoint)
                    if is_healthy:
                        summary["healthy_endpoints"] += 1
                    else:
                        summary["unhealthy_endpoints"] += 1
                except:
                    summary["unhealthy_endpoints"] += 1
        
        return summary


class RouteCache:
    """Cache for route matching results."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """Initialize route cache."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[RouteMatch, datetime]] = {}
        self.access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[RouteMatch]:
        """Get cached route match."""
        if key not in self.cache:
            return None
        
        match, timestamp = self.cache[key]
        
        # Check if cache entry has expired
        if (datetime.utcnow() - timestamp).total_seconds() > self.ttl_seconds:
            self._remove_from_cache(key)
            return None
        
        # Update access time
        self.access_times[key] = datetime.utcnow()
        
        return match
    
    def set(self, key: str, match: RouteMatch):
        """Cache route match."""
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest_entries()
        
        self.cache[key] = (match, datetime.utcnow())
        self.access_times[key] = datetime.utcnow()
    
    def _remove_from_cache(self, key: str):
        """Remove entry from cache."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def _evict_oldest_entries(self):
        """Evict oldest cache entries."""
        # Sort by access time and remove oldest entries
        sorted_entries = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        # Remove oldest 10% of entries
        to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:to_remove]:
            self._remove_from_cache(key)
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.access_times.clear()
