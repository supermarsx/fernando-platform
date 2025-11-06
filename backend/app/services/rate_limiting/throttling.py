"""
Dynamic Throttling Service

Implements intelligent throttling that adapts based on usage patterns,
system load, performance metrics, and user behavior analysis.
Provides real-time throttling decisions with machine learning-inspired
pattern recognition and predictive throttling.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
import statistics
import math
import json

from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class ThrottlingStrategy(Enum):
    """Throttling strategies"""
    ADAPTIVE = "adaptive"
    PREDICTIVE = "predictive"
    BEHAVIOR_BASED = "behavior_based"
    LOAD_BASED = "load_based"
    COST_AWARE = "cost_aware"
    HYBRID = "hybrid"

class ThrottlingLevel(Enum):
    """Throttling intensity levels"""
    NONE = "none"
    LIGHT = "light"      # 25% reduction
    MODERATE = "moderate" # 50% reduction
    HEAVY = "heavy"      # 75% reduction
    EMERGENCY = "emergency" # 90% reduction

class ThrottlingTrigger(Enum):
    """What triggers throttling"""
    HIGH_LOAD = "high_load"
    USAGE_SPIKE = "usage_spike"
    COST_THRESHOLD = "cost_threshold"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    BEHAVIOR_ANOMALY = "behavior_anomaly"

@dataclass
class ThrottlingRule:
    """Dynamic throttling rule configuration"""
    id: str
    name: str
    strategy: ThrottlingStrategy
    trigger: ThrottlingTrigger
    threshold_value: float
    throttling_level: ThrottlingLevel
    scope_type: str  # 'global', 'user', 'organization', 'endpoint'
    scope_id: Optional[str] = None  # Specific ID or pattern
    duration_seconds: int = 300  # How long to throttle
    cooldown_seconds: int = 600  # Cooldown before re-triggering
    max_violations: int = 3  # Max violations before permanent throttling
    priority: int = 0
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)  # Additional conditions
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ThrottlingDecision:
    """Throttling decision result"""
    should_throttle: bool
    throttling_level: ThrottlingLevel
    throttle_rate: float  # 0.0 to 1.0 (percentage reduction)
    duration_seconds: int
    reason: str
    confidence: float  # 0.0 to 1.0
    triggered_rules: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)  # Alternative actions

@dataclass
class UsagePattern:
    """Usage pattern analysis result"""
    scope_type: str
    scope_id: str
    pattern_type: str  # 'spiky', 'consistent', 'burst', 'gradual'
    predictability_score: float
    peak_hours: List[int]
    typical_usage_volume: float
    anomaly_score: float
    seasonality_factor: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'

class AdaptiveThrottler:
    """Adaptive throttling based on real-time system metrics"""
    
    def __init__(self, base_limit: int, adaptation_factor: float = 0.1):
        self.base_limit = base_limit
        self.adaptation_factor = adaptation_factor
        self.current_limit = base_limit
        self.metrics_buffer = deque(maxlen=100)
        self.performance_baseline = {
            'response_time': 200,  # ms
            'throughput': 1000,   # requests/second
            'error_rate': 0.01,   # 1%
            'resource_usage': 0.7  # 70%
        }
    
    async def should_throttle(self, current_metrics: Dict[str, float]) -> ThrottlingDecision:
        """Determine if throttling is needed based on current metrics"""
        # Update metrics buffer
        self.metrics_buffer.append(current_metrics)
        
        # Calculate current performance score
        performance_score = self._calculate_performance_score(current_metrics)
        
        # Determine throttling level
        if performance_score >= 0.9:
            return ThrottlingDecision(False, ThrottlingLevel.NONE, 0.0, 0, "System performance optimal")
        elif performance_score >= 0.7:
            level = ThrottlingLevel.LIGHT
            rate = 0.25
        elif performance_score >= 0.5:
            level = ThrottlingLevel.MODERATE
            rate = 0.50
        elif performance_score >= 0.3:
            level = ThrottlingLevel.HEAVY
            rate = 0.75
        else:
            level = ThrottlingLevel.EMERGENCY
            rate = 0.90
        
        # Calculate adjusted limit
        self.current_limit = int(self.base_limit * (1 - rate))
        
        return ThrottlingDecision(
            performance_score < 0.7,
            level,
            rate,
            300,  # 5 minutes
            f"Performance score: {performance_score:.2f}",
            1.0 - performance_score
        )
    
    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall performance score (0.0 to 1.0)"""
        try:
            # Response time component
            response_time = metrics.get('response_time_ms', self.performance_baseline['response_time'])
            response_score = max(0, 1 - (response_time / (self.performance_baseline['response_time'] * 2)))
            
            # Throughput component
            throughput = metrics.get('requests_per_second', self.performance_baseline['throughput'])
            throughput_score = min(1, throughput / self.performance_baseline['throughput'])
            
            # Error rate component
            error_rate = metrics.get('error_rate', self.performance_baseline['error_rate'])
            error_score = max(0, 1 - (error_rate / (self.performance_baseline['error_rate'] * 5)))
            
            # Resource usage component
            resource_usage = metrics.get('resource_usage', self.performance_baseline['resource_usage'])
            resource_score = max(0, 1 - (resource_usage - 0.7) / 0.3)
            
            # Weighted average
            weights = {'response': 0.3, 'throughput': 0.3, 'error': 0.2, 'resource': 0.2}
            total_score = (
                response_score * weights['response'] +
                throughput_score * weights['throughput'] +
                error_score * weights['error'] +
                resource_score * weights['resource']
            )
            
            return max(0, min(1, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 0.5  # Default to moderate performance

class PredictiveThrottler:
    """Predictive throttling based on usage patterns and trends"""
    
    def __init__(self):
        self.usage_history = defaultdict(deque)
        self.pattern_cache = {}
        self.prediction_models = {}
    
    async def should_throttle(
        self,
        scope_type: str,
        scope_id: str,
        current_time: datetime,
        projected_load: Optional[float] = None
    ) -> ThrottlingDecision:
        """Predictive throttling decision"""
        # Get usage pattern for scope
        pattern = await self._analyze_usage_pattern(scope_type, scope_id, current_time)
        
        # Predict future load
        predicted_load = await self._predict_future_load(
            scope_type, scope_id, current_time, pattern
        )
        
        # Calculate throttling recommendation
        if predicted_load > pattern.typical_usage_volume * 1.5:
            return ThrottlingDecision(
                True,
                ThrottlingLevel.MODERATE,
                0.4,
                900,  # 15 minutes
                f"Predicted load spike: {predicted_load:.1f} > {pattern.typical_usage_volume * 1.5:.1f}",
                min(1.0, predicted_load / (pattern.typical_usage_volume * 2))
            )
        elif predicted_load > pattern.typical_usage_volume:
            return ThrottlingDecision(
                True,
                ThrottlingLevel.LIGHT,
                0.2,
                600,  # 10 minutes
                f"Moderate load increase predicted: {predicted_load:.1f}",
                0.6
            )
        else:
            return ThrottlingDecision(
                False,
                ThrottlingLevel.NONE,
                0.0,
                0,
                "Load within normal range",
                0.9
            )
    
    async def _analyze_usage_pattern(
        self,
        scope_type: str,
        scope_id: str,
        current_time: datetime
    ) -> UsagePattern:
        """Analyze usage pattern for scope"""
        scope_key = f"{scope_type}:{scope_id}"
        
        # Check cache first
        if scope_key in self.pattern_cache:
            pattern = self.pattern_cache[scope_key]
            # Check if pattern is still valid (refresh every hour)
            if current_time < pattern.get('last_updated', current_time) + timedelta(hours=1):
                return self._pattern_from_cache(pattern)
        
        # Get usage history
        history_key = f"{scope_key}:history"
        usage_data = self.usage_history[history_key]
        
        if len(usage_data) < 24:  # Need at least 24 data points
            return self._create_default_pattern(scope_type, scope_id)
        
        # Analyze pattern
        pattern = self._calculate_usage_pattern(list(usage_data))
        
        # Cache pattern
        self.pattern_cache[scope_key] = {
            'pattern': pattern.__dict__,
            'last_updated': current_time
        }
        
        return pattern
    
    def _calculate_usage_pattern(self, usage_data: List[Dict[str, Any]]) -> UsagePattern:
        """Calculate usage pattern from historical data"""
        # Extract hourly usage
        hourly_usage = defaultdict(list)
        daily_totals = []
        
        for data_point in usage_data:
            hour = data_point.get('hour', 0)
            usage = data_point.get('usage', 0)
            hourly_usage[hour].append(usage)
            daily_totals.append(usage)
        
        # Calculate peak hours
        hour_averages = {}
        for hour in range(24):
            if hourly_usage[hour]:
                hour_averages[hour] = statistics.mean(hourly_usage[hour])
        
        peak_hours = sorted(hour_averages.keys(), key=lambda h: hour_averages[h], reverse=True)[:3]
        typical_usage = statistics.mean(daily_totals) if daily_totals else 0
        
        # Determine pattern type
        usage_volatility = statistics.stdev(daily_totals) / max(1, typical_usage) if daily_totals else 0
        
        if usage_volatility > 1.0:
            pattern_type = "spiky"
        elif usage_volatility > 0.5:
            pattern_type = "burst"
        elif usage_volatility > 0.2:
            pattern_type = "gradual"
        else:
            pattern_type = "consistent"
        
        # Calculate predictability score
        if len(daily_totals) >= 7:
            # Check for repeating patterns
            correlation = self._calculate_autocorrelation(daily_totals)
            predictability = max(0, min(1, correlation))
        else:
            predictability = 0.5
        
        # Calculate trend
        if len(daily_totals) >= 3:
            recent_avg = statistics.mean(daily_totals[-7:]) if len(daily_totals) >= 7 else statistics.mean(daily_totals)
            early_avg = statistics.mean(daily_totals[:7]) if len(daily_totas) >= 7 else daily_totals[0]
            
            if recent_avg > early_avg * 1.1:
                trend_direction = "increasing"
            elif recent_avg < early_avg * 0.9:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
        
        return UsagePattern(
            scope_type="",
            scope_id="",
            pattern_type=pattern_type,
            predictability_score=predictability,
            peak_hours=peak_hours,
            typical_usage_volume=typical_usage,
            anomaly_score=0.0,
            seasonality_factor=1.0,
            trend_direction=trend_direction
        )
    
    def _calculate_autocorrelation(self, data: List[float]) -> float:
        """Calculate autocorrelation for pattern detection"""
        if len(data) < 2:
            return 0.0
        
        n = len(data)
        mean = statistics.mean(data)
        
        numerator = sum((data[i] - mean) * (data[i-1] - mean) for i in range(1, n))
        denominator = sum((x - mean) ** 2 for x in data)
        
        return numerator / max(denominator, 1e-6)
    
    def _create_default_pattern(self, scope_type: str, scope_id: str) -> UsagePattern:
        """Create default usage pattern"""
        return UsagePattern(
            scope_type=scope_type,
            scope_id=scope_id,
            pattern_type="consistent",
            predictability_score=0.5,
            peak_hours=[9, 14, 18],  # Default business hours
            typical_usage_volume=100.0,
            anomaly_score=0.0,
            seasonality_factor=1.0,
            trend_direction="stable"
        )
    
    def _pattern_from_cache(self, cached_data: Dict[str, Any]) -> UsagePattern:
        """Create pattern object from cached data"""
        pattern_data = cached_data['pattern']
        return UsagePattern(**pattern_data)
    
    async def _predict_future_load(
        self,
        scope_type: str,
        scope_id: str,
        current_time: datetime,
        pattern: UsagePattern
    ) -> float:
        """Predict future load based on pattern and trend"""
        base_load = pattern.typical_usage_volume
        
        # Apply time-based factors
        current_hour = current_time.hour
        if current_hour in pattern.peak_hours:
            time_factor = 1.5
        else:
            time_factor = 0.7
        
        # Apply trend factor
        if pattern.trend_direction == "increasing":
            trend_factor = 1.2
        elif pattern.trend_direction == "decreasing":
            trend_factor = 0.8
        else:
            trend_factor = 1.0
        
        # Apply seasonality
        seasonality_factor = pattern.seasonality_factor
        
        predicted_load = base_load * time_factor * trend_factor * seasonality_factor
        
        return predicted_load

class BehaviorBasedThrottler:
    """Throttling based on user behavior analysis"""
    
    def __init__(self):
        self.behavior_profiles = {}
        self.anomaly_detector = AnomalyDetector()
    
    async def should_throttle(
        self,
        user_id: str,
        current_behavior: Dict[str, Any],
        historical_behavior: Optional[Dict[str, Any]] = None
    ) -> ThrottlingDecision:
        """Behavior-based throttling decision"""
        # Get or create behavior profile
        profile = await self._get_behavior_profile(user_id, current_behavior)
        
        # Detect anomalies
        anomaly_score = await self.anomaly_detector.detect_anomaly(profile, current_behavior)
        
        # Determine throttling based on anomaly score
        if anomaly_score > 0.8:
            return ThrottlingDecision(
                True,
                ThrottlingLevel.EMERGENCY,
                0.9,
                1800,  # 30 minutes
                f"High anomaly score: {anomaly_score:.2f}",
                anomaly_score
            )
        elif anomaly_score > 0.6:
            return ThrottlingDecision(
                True,
                ThrottlingLevel.HEAVY,
                0.7,
                1200,  # 20 minutes
                f"Anomalous behavior detected: {anomaly_score:.2f}",
                anomaly_score
            )
        elif anomaly_score > 0.3:
            return ThrottlingDecision(
                True,
                ThrottlingLevel.MODERATE,
                0.4,
                600,  # 10 minutes
                f"Unusual behavior pattern: {anomaly_score:.2f}",
                anomaly_score
            )
        else:
            return ThrottlingDecision(
                False,
                ThrottlingLevel.NONE,
                0.0,
                0,
                "Behavior within normal parameters",
                1.0 - anomaly_score
            )
    
    async def _get_behavior_profile(
        self,
        user_id: str,
        current_behavior: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get or create user behavior profile"""
        if user_id not in self.behavior_profiles:
            self.behavior_profiles[user_id] = {
                'typical_request_rate': current_behavior.get('request_rate', 1.0),
                'typical_endpoint_preferences': current_behavior.get('endpoints', []),
                'typical_session_duration': current_behavior.get('session_duration', 300),
                'typical_time_patterns': current_behavior.get('time_patterns', []),
                'typical_data_volume': current_behavior.get('data_volume', 1024),
                'interaction_patterns': current_behavior.get('interaction_pattern', 'normal'),
                'risk_profile': current_behavior.get('risk_score', 0.1),
                'last_updated': datetime.now(timezone.utc)
            }
        
        profile = self.behavior_profiles[user_id]
        
        # Update profile with new data (exponential moving average)
        alpha = 0.1
        profile['typical_request_rate'] = (1 - alpha) * profile['typical_request_rate'] + alpha * current_behavior.get('request_rate', 1.0)
        profile['typical_data_volume'] = (1 - alpha) * profile['typical_data_volume'] + alpha * current_behavior.get('data_volume', 1024)
        profile['risk_profile'] = (1 - alpha) * profile['risk_profile'] + alpha * current_behavior.get('risk_score', 0.1)
        profile['last_updated'] = datetime.now(timezone.utc)
        
        return profile

class AnomalyDetector:
    """Detects behavioral anomalies for throttling"""
    
    def __init__(self):
        self.thresholds = {
            'request_rate_multiplier': 3.0,  # 3x normal rate
            'data_volume_multiplier': 5.0,  # 5x normal volume
            'new_endpoint_ratio': 0.7,      # 70% new endpoints
            'unusual_time_score': 0.6,      # Unusual time access
            'rapid_succession': 0.8         # Very rapid requests
        }
    
    async def detect_anomaly(self, profile: Dict[str, Any], current_behavior: Dict[str, Any]) -> float:
        """Detect anomaly score (0.0 to 1.0)"""
        anomaly_score = 0.0
        factors = []
        
        # Request rate anomaly
        current_rate = current_behavior.get('request_rate', 1.0)
        typical_rate = profile.get('typical_request_rate', 1.0)
        rate_multiplier = current_rate / max(1, typical_rate)
        
        if rate_multiplier > self.thresholds['request_rate_multiplier']:
            rate_anomaly = min(1.0, (rate_multiplier - 1) / 2)
            anomaly_score += rate_anomaly * 0.3
            factors.append(f"High request rate: {rate_multiplier:.1f}x")
        
        # Data volume anomaly
        current_volume = current_behavior.get('data_volume', 1024)
        typical_volume = profile.get('typical_data_volume', 1024)
        volume_multiplier = current_volume / max(1024, typical_volume)
        
        if volume_multiplier > self.thresholds['data_volume_multiplier']:
            volume_anomaly = min(1.0, (volume_multiplier - 1) / 4)
            anomaly_score += volume_anomaly * 0.2
            factors.append(f"High data volume: {volume_multiplier:.1f}x")
        
        # New endpoint access
        current_endpoints = set(current_behavior.get('endpoints', []))
        typical_endpoints = set(profile.get('typical_endpoint_preferences', []))
        
        if current_endpoints:
            new_endpoint_ratio = len(current_endpoints - typical_endpoints) / len(current_endpoints)
            if new_endpoint_ratio > self.thresholds['new_endpoint_ratio']:
                endpoint_anomaly = (new_endpoint_ratio - 0.3) / 0.4  # Normalize
                anomaly_score += endpoint_anomaly * 0.2
                factors.append(f"High new endpoint ratio: {new_endpoint_ratio:.1%}")
        
        # Time pattern anomaly
        current_hour = current_behavior.get('current_hour', 12)
        typical_hours = profile.get('typical_time_patterns', [])
        
        if typical_hours:
            # Check if current hour is outside typical patterns
            hour_anomaly = 0.0
            for hour_range in typical_hours:
                if isinstance(hour_range, (list, tuple)) and len(hour_range) == 2:
                    if hour_range[0] <= current_hour <= hour_range[1]:
                        hour_anomaly = 0.0
                        break
                elif current_hour in typical_hours:
                    hour_anomaly = 0.0
                    break
            else:
                hour_anomaly = self.thresholds['unusual_time_score']
            
            anomaly_score += hour_anomaly * 0.15
            if hour_anomaly > 0:
                factors.append(f"Unusual access time: {current_hour}:00")
        
        # Rapid succession anomaly
        time_gap = current_behavior.get('time_since_last_request', 60)
        if time_gap < 1:  # Less than 1 second
            rapid_anomaly = self.thresholds['rapid_succession']
            anomaly_score += rapid_anomaly * 0.15
            factors.append(f"Rapid requests: {time_gap:.1f}s gap")
        
        return min(1.0, anomaly_score)

class DynamicThrottler:
    """
    Comprehensive Dynamic Throttling Service
    
    Combines multiple throttling strategies:
    - Adaptive: Based on real-time system performance
    - Predictive: Based on usage patterns and trends
    - Behavior-based: Based on user behavior analysis
    - Load-based: Based on system resource utilization
    - Cost-aware: Based on cost thresholds
    - Hybrid: Combines multiple strategies
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Initialize throttling components
        self.adaptive_throttler = AdaptiveThrottler(1000)  # Base limit: 1000 req/sec
        self.predictive_throttler = PredictiveThrottler()
        self.behavior_throttler = BehaviorBasedThrottler()
        
        # Throttling rules
        self._throttling_rules: Dict[str, ThrottlingRule] = {}
        
        # Active throttling states
        self._active_throttling: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._throttling_stats = {
            'total_decisions': 0,
            'throttling_activations': 0,
            'strategy_breakdown': defaultdict(int),
            'trigger_breakdown': defaultdict(int)
        }
        
        # Configuration
        self.config = {
            'decision_cache_ttl': 30,  # Cache decisions for 30 seconds
            'max_throttling_duration': 3600,  # 1 hour max
            'cleanup_interval_seconds': 300,  # 5 minutes
            'redis_namespace': 'throttle',
        }
        
        logger.info("DynamicThrottler initialized")
    
    async def add_throttling_rule(self, rule: ThrottlingRule) -> bool:
        """Add throttling rule"""
        try:
            self._throttling_rules[rule.id] = rule
            
            logger.info(f"Added throttling rule: {rule.name} ({rule.strategy.value})")
            
            await self.event_tracker.track_event(
                "throttling_rule_added",
                {
                    "rule_id": rule.id,
                    "strategy": rule.strategy.value,
                    "trigger": rule.trigger.value,
                    "throttling_level": rule.throttling_level.value
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add throttling rule: {e}")
            return False
    
    async def remove_throttling_rule(self, rule_id: str) -> bool:
        """Remove throttling rule"""
        if rule_id in self._throttling_rules:
            del self._throttling_rules[rule_id]
            
            await self.event_tracker.track_event(
                "throttling_rule_removed",
                {"rule_id": rule_id}
            )
            
            return True
        return False
    
    async def make_throttling_decision(
        self,
        scope_type: str,
        scope_id: str,
        context: Dict[str, Any]
    ) -> ThrottlingDecision:
        """
        Make comprehensive throttling decision
        
        Args:
            scope_type: Type of scope (global, user, organization, endpoint)
            scope_id: Scope identifier
            context: Context information for decision
            
        Returns:
            ThrottlingDecision with throttle recommendation
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{self.config['redis_namespace']}:decision:{scope_type}:{scope_id}:{hash(str(sorted(context.items())))}"
        cached_decision = await self.redis_cache.get(cache_key)
        
        if cached_decision:
            try:
                return ThrottlingDecision(**json.loads(cached_decision))
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Collect input data
        current_metrics = context.get('system_metrics', {})
        user_behavior = context.get('user_behavior', {})
        usage_patterns = context.get('usage_patterns', {})
        current_time = context.get('timestamp', datetime.now(timezone.utc))
        
        # Get decisions from different strategies
        decisions = []
        
        # Adaptive throttling
        if current_metrics:
            adaptive_decision = await self.adaptive_throttler.should_throttle(current_metrics)
            if adaptive_decision.should_throttle:
                decisions.append(('adaptive', adaptive_decision))
        
        # Predictive throttling
        if scope_type in ['user', 'organization']:
            predictive_decision = await self.predictive_throttler.should_throttle(
                scope_type, scope_id, current_time, usage_patterns.get('projected_load')
            )
            if predictive_decision.should_throttle:
                decisions.append(('predictive', predictive_decision))
        
        # Behavior-based throttling
        if scope_type == 'user' and user_behavior:
            behavior_decision = await self.behavior_throttler.should_throttle(
                scope_id, user_behavior, context.get('historical_behavior')
            )
            if behavior_decision.should_throttle:
                decisions.append(('behavior', behavior_decision))
        
        # Check global rules
        rule_decisions = await self._check_global_rules(scope_type, scope_id, context)
        decisions.extend(rule_decisions)
        
        # Combine decisions (use most restrictive)
        final_decision = self._combine_decisions(decisions)
        
        # Store decision in cache
        if final_decision.should_throttle:
            await self.redis_cache.set(
                cache_key,
                json.dumps(final_decision.__dict__, default=str),
                ttl=self.config['decision_cache_ttl']
            )
        
        # Update statistics
        processing_time = time.time() - start_time
        await self._update_statistics(final_decision, processing_time)
        
        return final_decision
    
    async def _check_global_rules(
        self,
        scope_type: str,
        scope_id: str,
        context: Dict[str, Any]
    ) -> List[Tuple[str, ThrottlingDecision]]:
        """Check global throttling rules"""
        rule_decisions = []
        
        for rule in self._throttling_rules.values():
            if not rule.enabled:
                continue
            
            # Check scope match
            if (rule.scope_type != scope_type or 
                (rule.scope_id and rule.scope_id != scope_id)):
                continue
            
            # Check rule conditions
            if not self._check_rule_conditions(rule, context):
                continue
            
            # Evaluate rule trigger
            trigger_decision = await self._evaluate_rule_trigger(rule, context)
            if trigger_decision and trigger_decision.should_throttle:
                rule_decisions.append((f"rule_{rule.id}", trigger_decision))
        
        return rule_decisions
    
    def _check_rule_conditions(self, rule: ThrottlingRule, context: Dict[str, Any]) -> bool:
        """Check if rule conditions are met"""
        conditions = rule.conditions
        
        # Time-based conditions
        if 'time_range' in conditions:
            current_hour = context.get('timestamp', datetime.now(timezone.utc)).hour
            time_range = conditions['time_range']
            if isinstance(time_range, list) and len(time_range) == 2:
                if not (time_range[0] <= current_hour <= time_range[1]):
                    return False
        
        # System load conditions
        if 'min_response_time' in conditions:
            current_response_time = context.get('system_metrics', {}).get('response_time_ms', 0)
            if current_response_time < conditions['min_response_time']:
                return False
        
        # Usage volume conditions
        if 'min_usage_rate' in conditions:
            current_usage_rate = context.get('usage_patterns', {}).get('current_rate', 0)
            if current_usage_rate < conditions['min_usage_rate']:
                return False
        
        return True
    
    async def _evaluate_rule_trigger(
        self,
        rule: ThrottlingRule,
        context: Dict[str, Any]
    ) -> Optional[ThrottlingDecision]:
        """Evaluate rule trigger conditions"""
        try:
            system_metrics = context.get('system_metrics', {})
            usage_patterns = context.get('usage_patterns', {})
            
            if rule.trigger == ThrottlingTrigger.HIGH_LOAD:
                # Check system load
                response_time = system_metrics.get('response_time_ms', 0)
                if response_time > rule.threshold_value:
                    return ThrottlingDecision(
                        True, rule.throttling_level,
                        self._level_to_rate(rule.throttling_level),
                        rule.duration_seconds,
                        f"High load: {response_time}ms > {rule.threshold_value}ms",
                        0.8
                    )
            
            elif rule.trigger == ThrottlingTrigger.USAGE_SPIKE:
                # Check usage spike
                current_rate = usage_patterns.get('current_rate', 0)
                if current_rate > rule.threshold_value:
                    return ThrottlingDecision(
                        True, rule.throttling_level,
                        self._level_to_rate(rule.throttling_level),
                        rule.duration_seconds,
                        f"Usage spike: {current_rate} > {rule.threshold_value}",
                        0.7
                    )
            
            elif rule.trigger == ThrottlingTrigger.PERFORMANCE_DEGRADATION:
                # Check performance degradation
                error_rate = system_metrics.get('error_rate', 0)
                if error_rate > rule.threshold_value:
                    return ThrottlingDecision(
                        True, rule.throttling_level,
                        self._level_to_rate(rule.throttling_level),
                        rule.duration_seconds,
                        f"High error rate: {error_rate:.1%} > {rule.threshold_value:.1%}",
                        0.9
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating rule trigger {rule.id}: {e}")
            return None
    
    def _combine_decisions(self, decisions: List[Tuple[str, ThrottlingDecision]]) -> ThrottlingDecision:
        """Combine multiple throttling decisions (use most restrictive)"""
        if not decisions:
            return ThrottlingDecision(
                False, ThrottlingLevel.NONE, 0.0, 0,
                "No throttling needed", 1.0
            )
        
        # Find most restrictive decision
        max_throttle_rate = 0.0
        max_level = ThrottlingLevel.NONE
        max_duration = 0
        all_reasons = []
        all_rule_ids = []
        
        for strategy, decision in decisions:
            if decision.throttle_rate > max_throttle_rate:
                max_throttle_rate = decision.throttle_rate
                max_level = decision.throttling_level
                max_duration = max(max_duration, decision.duration_seconds)
            
            all_reasons.append(f"{strategy}: {decision.reason}")
            all_rule_ids.extend(decision.triggered_rules)
        
        # Combine alternatives
        all_alternatives = []
        for strategy, decision in decisions:
            all_alternatives.extend(decision.alternatives)
        
        return ThrottlingDecision(
            max_throttle_rate > 0,
            max_level,
            max_throttle_rate,
            max_duration,
            "; ".join(all_reasons),
            0.8,  # High confidence when multiple strategies agree
            all_rule_ids,
            all_alternatives
        )
    
    def _level_to_rate(self, level: ThrottlingLevel) -> float:
        """Convert throttling level to rate"""
        rates = {
            ThrottlingLevel.NONE: 0.0,
            ThrottlingLevel.LIGHT: 0.25,
            ThrottlingLevel.MODERATE: 0.5,
            ThrottlingLevel.HEAVY: 0.75,
            ThrottlingLevel.EMERGENCY: 0.9
        }
        return rates.get(level, 0.0)
    
    async def _update_statistics(
        self,
        decision: ThrottlingDecision,
        processing_time: float
    ) -> None:
        """Update throttling statistics"""
        self._throttling_stats['total_decisions'] += 1
        
        if decision.should_throttle:
            self._throttling_stats['throttling_activations'] += 1
        
        # Track strategy usage
        # This would be updated based on actual strategy used
        self._throttling_stats['strategy_breakdown']['hybrid'] += 1
    
    async def get_throttling_status(
        self,
        scope_type: str,
        scope_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current throttling status"""
        try:
            # Get active throttling for scope
            if scope_id:
                throttle_key = f"{scope_type}:{scope_id}"
                active_throttling = self._active_throttling.get(throttle_key, {})
            else:
                # Get global throttling status
                active_throttling = self._active_throttling
            
            # Get statistics
            stats = await self.get_throttling_statistics()
            
            # Get active rules
            active_rules = [
                rule for rule in self._throttling_rules.values()
                if rule.enabled
            ]
            
            status = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'scope': {
                    'type': scope_type,
                    'id': scope_id
                },
                'active_throttling': active_throttling,
                'statistics': stats,
                'active_rules_count': len(active_rules),
                'rules': [
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'strategy': rule.strategy.value,
                        'trigger': rule.trigger.value,
                        'enabled': rule.enabled
                    }
                    for rule in active_rules
                ]
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get throttling status: {e}")
            return {'error': str(e)}
    
    async def get_throttling_statistics(self) -> Dict[str, Any]:
        """Get comprehensive throttling statistics"""
        # Get Redis statistics
        redis_stats = await self._get_redis_statistics()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overview': self._throttling_stats,
            'strategy_breakdown': dict(self._throttling_stats['strategy_breakdown']),
            'trigger_breakdown': dict(self._throttling_stats['trigger_breakdown']),
            'redis_statistics': redis_stats,
            'active_rules': len([r for r in self._throttling_rules.values() if r.enabled]),
            'total_rules': len(self._throttling_rules)
        }
    
    async def _get_redis_statistics(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        try:
            redis_info = await self.redis_cache.info()
            return {
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', '0B')
            }
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {'error': str(e)}
    
    async def reset_throttling(
        self,
        scope_type: str,
        scope_id: Optional[str] = None
    ) -> bool:
        """Reset throttling for scope"""
        try:
            if scope_id:
                throttle_key = f"{scope_type}:{scope_id}"
                if throttle_key in self._active_throttling:
                    del self._active_throttling[throttle_key]
                    logger.info(f"Reset throttling for {scope_type} {scope_id}")
                    return True
            else:
                # Reset all throttling
                self._active_throttling.clear()
                logger.info("Reset all throttling")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to reset throttling: {e}")
            return False
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired throttling data"""
        try:
            current_time = datetime.now(timezone.utc)
            cleanup_count = 0
            
            # Clean up expired throttling states
            expired_keys = []
            for key, throttling_data in self._active_throttling.items():
                if 'expires_at' in throttling_data:
                    expires_at = datetime.fromisoformat(throttling_data['expires_at'])
                    if current_time > expires_at:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self._active_throttling[key]
                cleanup_count += 1
            
            # Clean up old behavior profiles (keep only recent)
            expired_profiles = []
            for user_id, profile in self.behavior_throttler.behavior_profiles.items():
                if 'last_updated' in profile:
                    last_updated = profile['last_updated']
                    if current_time > last_updated + timedelta(days=30):  # 30 days
                        expired_profiles.append(user_id)
            
            for user_id in expired_profiles:
                del self.behavior_throttler.behavior_profiles[user_id]
                cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired throttling entries")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        # Clear all data structures
        self._throttling_rules.clear()
        self._active_throttling.clear()
        self.behavior_throttler.behavior_profiles.clear()
        self.predictive_throttler.usage_history.clear()
        self.predictive_throttler.pattern_cache.clear()
        
        logger.info("DynamicThrottler closed")