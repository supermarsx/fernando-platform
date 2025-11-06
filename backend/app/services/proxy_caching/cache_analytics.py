"""
Cache Analytics and Performance Optimization Module

Provides comprehensive analytics for proxy caching system including
performance metrics, optimization recommendations, cache efficiency analysis,
and health monitoring. Integrates with existing caching services for
intelligent cache management.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, deque
import statistics
import math

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, 
    Float, Text, JSON, Index, func, desc, case
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text

from app.models.proxy import ProxyRequestCache
from app.core.database import get_database_url
from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

Base = declarative_base()

class CacheMetricRecord(Base):
    """Track detailed cache metrics"""
    __tablename__ = "cache_metric_records"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(512), index=True, nullable=False)
    endpoint_path = Column(String(512), nullable=False)
    metric_type = Column(String(50), nullable=False)  # hit, miss, eviction, update
    metric_value = Column(Float, default=0.0)
    cache_size_bytes = Column(Integer, default=0)
    response_time_ms = Column(Float, default=0.0)
    ttl_remaining_seconds = Column(Integer, default=0)
    cache_tier = Column(String(20), default="memory")  # memory, redis, disk
    request_size = Column(Integer, default=0)
    response_size = Column(Integer, default=0)
    user_id = Column(Integer, index=True, nullable=True)
    organization_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_cache_metric_timestamp', 'timestamp'),
        Index('idx_cache_metric_key_type', 'cache_key', 'metric_type'),
        Index('idx_cache_metric_endpoint', 'endpoint_path', 'timestamp'),
    )

class CachePerformanceSnapshot(Base):
    """Store periodic cache performance snapshots"""
    __tablename__ = "cache_performance_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_type = Column(String(20), nullable=False)  # hourly, daily, weekly
    snapshot_period_start = Column(DateTime(timezone=True), nullable=False)
    snapshot_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Key metrics
    total_requests = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    cache_evictions = Column(Integer, default=0)
    cache_updates = Column(Integer, default=0)
    
    # Performance metrics
    hit_rate = Column(Float, default=0.0)
    miss_rate = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, default=0.0)
    avg_cache_lookup_time_ms = Column(Float, default=0.0)
    avg_cached_response_time_ms = Column(Float, default=0.0)
    avg_uncached_response_time_ms = Column(Float, default=0.0)
    
    # Storage metrics
    total_cache_size_bytes = Column(Integer, default=0)
    avg_cache_size_bytes = Column(Float, default=0.0)
    cache_memory_usage_mb = Column(Float, default=0.0)
    cache_entries_count = Column(Integer, default=0)
    
    # Network metrics
    total_data_cached_gb = Column(Float, default=0.0)
    total_bandwidth_saved_gb = Column(Float, default=0.0)
    
    # Derived metrics
    efficiency_score = Column(Float, default=0.0)
    performance_score = Column(Float, default=0.0)
    cost_savings_usd = Column(Float, default=0.0)
    
    # Additional data
    endpoint_breakdown = Column(JSON, nullable=True)
    geographic_breakdown = Column(JSON, nullable=True)
    time_breakdown = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

class CacheOptimization(Base):
    """Track cache optimization recommendations"""
    __tablename__ = "cache_optimizations"
    
    id = Column(Integer, primary_key=True, index=True)
    optimization_type = Column(String(50), nullable=False)  # ttl_adjustment, cache_key_pattern, memory_reallocation
    endpoint_pattern = Column(String(512), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    current_value = Column(Float, nullable=False)
    recommended_value = Column(Float, nullable=False)
    expected_improvement = Column(Float, nullable=False)  # percentage improvement
    implementation_status = Column(String(20), default="pending")  # pending, in_progress, completed, dismissed
    implementation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    implemented_at = Column(DateTime(timezone=True), nullable=True)

class CacheAnalytics:
    """
    Cache Analytics and Performance Optimization Manager
    
    Provides comprehensive cache analytics:
    - Performance metrics tracking
    - Cache efficiency analysis
    - Optimization recommendations
    - Health monitoring
    - Capacity planning
    - Cost optimization
    """
    
    def __init__(self):
        self.engine = create_engine(get_database_url())
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize integrations
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Analytics configuration
        self.config = {
            'metric_collection_interval': 60,  # seconds
            'snapshot_retention_days': 90,
            'optimization_check_interval': 3600,  # 1 hour
            'min_cache_entries_for_analysis': 100,
            'target_hit_rate': 0.85,  # 85%
            'max_avg_response_time_ms': 1000,
            'max_memory_usage_mb': 512,
            'cost_per_gb_month': 0.05,  # Storage cost per GB per month
            'cost_per_request': 0.001,  # Compute cost per request
            'bandwidth_cost_per_gb': 0.12,  # Network bandwidth cost
        }
        
        # Real-time metrics buffer
        self._metrics_buffer = deque(maxlen=10000)
        self._last_cleanup = datetime.now(timezone.utc)
        
        logger.info("CacheAnalytics initialized")
    
    async def record_cache_metric(
        self,
        cache_key: str,
        endpoint_path: str,
        metric_type: str,
        metric_value: float = 0.0,
        cache_size_bytes: int = 0,
        response_time_ms: float = 0.0,
        ttl_remaining_seconds: int = 0,
        cache_tier: str = "memory",
        request_size: int = 0,
        response_size: int = 0,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ) -> None:
        """Record cache metric for analytics"""
        try:
            # Store in database
            session = self.SessionLocal()
            try:
                metric_record = CacheMetricRecord(
                    cache_key=cache_key,
                    endpoint_path=endpoint_path,
                    metric_type=metric_type,
                    metric_value=metric_value,
                    cache_size_bytes=cache_size_bytes,
                    response_time_ms=response_time_ms,
                    ttl_remaining_seconds=ttl_remaining_seconds,
                    cache_tier=cache_tier,
                    request_size=request_size,
                    response_size=response_size,
                    user_id=user_id,
                    organization_id=organization_id,
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(metric_record)
                session.commit()
                
                # Add to real-time buffer
                self._metrics_buffer.append({
                    'cache_key': cache_key,
                    'metric_type': metric_type,
                    'value': metric_value,
                    'timestamp': datetime.now(timezone.utc)
                })
                
                # Update cached counters
                await self._update_cache_counters(metric_type, metric_value)
                
                # Track analytics event
                await self.event_tracker.track_event(
                    "cache_metric_recorded",
                    {
                        "cache_key": cache_key[:50],  # Truncate for privacy
                        "metric_type": metric_type,
                        "metric_value": metric_value,
                        "endpoint": endpoint_path
                    }
                )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to record cache metric: {e}")
    
    async def get_cache_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "hour"
    ) -> Dict[str, Any]:
        """Get comprehensive cache performance metrics"""
        cache_key = f"cache_perf:{start_date.isoformat()}:{end_date.isoformat()}:{granularity}"
        
        # Check cache
        cached_result = await self.redis_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        session = self.SessionLocal()
        try:
            # Define time grouping
            if granularity == "minute":
                time_group = func.date_trunc('minute', CacheMetricRecord.timestamp)
            elif granularity == "hour":
                time_group = func.date_trunc('hour', CacheMetricRecord.timestamp)
            elif granularity == "day":
                time_group = func.date_trunc('day', CacheMetricRecord.timestamp)
            else:
                time_group = func.date_trunc('hour', CacheMetricRecord.timestamp)
            
            # Time series metrics
            time_series_query = session.query(CacheMetricRecord).filter(
                CacheMetricRecord.timestamp >= start_date,
                CacheMetricRecord.timestamp <= end_date
            )
            
            time_series = time_series_query.with_entities(
                time_group.label('period'),
                func.count(
                    case([(CacheMetricRecord.metric_type == 'hit', 1)], else_=0)
                ).label('hits'),
                func.count(
                    case([(CacheMetricRecord.metric_type == 'miss', 1)], else_=0)
                ).label('misses'),
                func.count(
                    case([(CacheMetricRecord.metric_type == 'eviction', 1)], else_=0)
                ).label('evictions'),
                func.count(CacheMetricRecord.id).label('total_operations'),
                func.avg(CacheMetricRecord.response_time_ms).label('avg_response_time'),
                func.avg(CacheMetricRecord.cache_size_bytes).label('avg_cache_size'),
                func.sum(CacheMetricRecord.response_size).label('total_response_size')
            ).group_by(time_group).order_by('period').all()
            
            # Endpoint breakdown
            endpoint_breakdown = time_series_query.with_entities(
                CacheMetricRecord.endpoint_path,
                func.count(
                    case([(CacheMetricRecord.metric_type == 'hit', 1)], else_=0)
                ).label('hits'),
                func.count(
                    case([(CacheMetricRecord.metric_type == 'miss', 1)], else_=0)
                ).label('misses'),
                func.count(CacheMetricRecord.id).label('total_requests'),
                func.avg(CacheMetricRecord.response_time_ms).label('avg_response_time')
            ).group_by(CacheMetricRecord.endpoint_path).order_by(desc('total_requests')).limit(50).all()
            
            # Calculate overall metrics
            total_hits = sum(row.hits for row in time_series)
            total_misses = sum(row.misses for row in time_series)
            total_operations = sum(row.total_operations for row in time_series)
            total_evictions = sum(row.evictions for row in time_series)
            
            hit_rate = (total_hits / max(1, total_operations)) * 100 if total_operations > 0 else 0
            miss_rate = (total_misses / max(1, total_operations)) * 100 if total_operations > 0 else 0
            
            avg_response_time = statistics.mean([
                row.avg_response_time for row in time_series if row.avg_response_time
            ]) if time_series else 0
            
            # Performance scores
            efficiency_score = self._calculate_efficiency_score(hit_rate, total_operations)
            performance_score = self._calculate_performance_score(
                hit_rate, avg_response_time, total_evictions
            )
            
            # Cost savings calculation
            total_cached_data_gb = sum(row.total_response_size or 0 for row in time_series) / (1024**3)
            estimated_cost_savings = total_cached_data_gb * self.config['bandwidth_cost_per_gb']
            
            metrics = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'granularity': granularity
                },
                'summary': {
                    'total_operations': total_operations,
                    'total_hits': total_hits,
                    'total_misses': total_misses,
                    'total_evictions': total_evictions,
                    'hit_rate_percent': round(hit_rate, 2),
                    'miss_rate_percent': round(miss_rate, 2),
                    'avg_response_time_ms': round(avg_response_time, 2)
                },
                'time_series': [
                    {
                        'period': row.period.isoformat() if row.period else None,
                        'hits': row.hits,
                        'misses': row.misses,
                        'evictions': row.evictions,
                        'total_operations': row.total_operations,
                        'hit_rate': round((row.hits / max(1, row.total_operations)) * 100, 2),
                        'avg_response_time_ms': round(row.avg_response_time or 0, 2),
                        'avg_cache_size_kb': round((row.avg_cache_size or 0) / 1024, 2),
                        'data_transferred_mb': round((row.total_response_size or 0) / (1024**2), 2)
                    }
                    for row in time_series
                ],
                'endpoint_analysis': [
                    {
                        'endpoint': row.endpoint_path,
                        'hits': row.hits,
                        'misses': row.misses,
                        'total_requests': row.total_requests,
                        'hit_rate': round((row.hits / max(1, row.total_requests)) * 100, 2),
                        'avg_response_time_ms': round(row.avg_response_time or 0, 2)
                    }
                    for row in endpoint_breakdown
                ],
                'performance_scores': {
                    'efficiency_score': round(efficiency_score, 2),
                    'performance_score': round(performance_score, 2),
                    'target_hit_rate': self.config['target_hit_rate'] * 100,
                    'performance_grade': self._get_performance_grade(performance_score)
                },
                'cost_analysis': {
                    'cached_data_gb': round(total_cached_data_gb, 2),
                    'estimated_cost_savings_usd': round(estimated_cost_savings, 2),
                    'bandwidth_cost_per_gb': self.config['bandwidth_cost_per_gb']
                }
            }
            
            # Cache result
            await self.redis_cache.set(cache_key, metrics, ttl=300)  # 5 minutes
            
            return metrics
            
        finally:
            session.close()
    
    async def get_cache_efficiency_analysis(self) -> Dict[str, Any]:
        """Analyze cache efficiency and provide insights"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get recent metrics (last 24 hours)
            start_time = current_time - timedelta(hours=24)
            performance_metrics = await self.get_cache_performance_metrics(
                start_time, current_time, "hour"
            )
            
            if not performance_metrics:
                return {'error': 'No performance data available'}
            
            # Analyze hit rate patterns
            hit_rate_trend = self._analyze_hit_rate_trend(performance_metrics['time_series'])
            
            # Analyze response time patterns
            response_time_analysis = self._analyze_response_time_patterns(
                performance_metrics['time_series']
            )
            
            # Analyze endpoint efficiency
            endpoint_efficiency = self._analyze_endpoint_efficiency(
                performance_metrics['endpoint_analysis']
            )
            
            # Calculate cache health score
            cache_health = self._calculate_cache_health_score(performance_metrics)
            
            # Identify optimization opportunities
            optimization_opportunities = await self._identify_optimization_opportunities(
                performance_metrics
            )
            
            # Capacity planning analysis
            capacity_analysis = await self._analyze_cache_capacity(
                performance_metrics
            )
            
            efficiency_analysis = {
                'timestamp': current_time.isoformat(),
                'cache_health': cache_health,
                'hit_rate_analysis': hit_rate_trend,
                'response_time_analysis': response_time_analysis,
                'endpoint_efficiency': endpoint_efficiency,
                'optimization_opportunities': optimization_opportunities,
                'capacity_planning': capacity_analysis,
                'recommendations': self._generate_efficiency_recommendations(
                    performance_metrics, optimization_opportunities
                )
            }
            
            return efficiency_analysis
            
        except Exception as e:
            logger.error(f"Failed to get cache efficiency analysis: {e}")
            return {'error': str(e)}
    
    async def get_cache_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get cache optimization recommendations"""
        try:
            recommendations = []
            
            # Get performance metrics
            current_time = datetime.now(timezone.utc)
            start_time = current_time - timedelta(hours=24)
            metrics = await self.get_cache_performance_metrics(start_time, current_time, "hour")
            
            if not metrics:
                return recommendations
            
            # TTL optimization recommendations
            ttl_recommendations = await self._analyze_ttl_optimization(metrics)
            recommendations.extend(ttl_recommendations)
            
            # Cache key pattern recommendations
            key_pattern_recommendations = await self._analyze_cache_key_patterns(metrics)
            recommendations.extend(key_pattern_recommendations)
            
            # Memory allocation recommendations
            memory_recommendations = await self._analyze_memory_allocation(metrics)
            recommendations.extend(memory_recommendations)
            
            # Cache strategy recommendations
            strategy_recommendations = await self._analyze_cache_strategy(metrics)
            recommendations.extend(strategy_recommendations)
            
            # Filter and prioritize recommendations
            prioritized_recommendations = self._prioritize_recommendations(recommendations)
            
            # Store recommendations in database
            await self._store_optimization_recommendations(prioritized_recommendations)
            
            return prioritized_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    async def get_cache_health_status(self) -> Dict[str, Any]:
        """Get comprehensive cache health status"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get current cache metrics
            start_time = current_time - timedelta(hours=1)
            recent_metrics = await self.get_cache_performance_metrics(
                start_time, current_time, "minute"
            )
            
            # Get Redis memory usage
            redis_info = await self._get_redis_memory_info()
            
            # Get cache size and entry count
            cache_stats = await self._get_cache_statistics()
            
            # Calculate health metrics
            health_metrics = self._calculate_health_metrics(recent_metrics, redis_info, cache_stats)
            
            # Determine health status
            health_status = self._determine_health_status(health_metrics)
            
            # Get active issues
            active_issues = await self._get_active_cache_issues()
            
            health_status = {
                'timestamp': current_time.isoformat(),
                'overall_status': health_status['status'],
                'health_score': health_status['score'],
                'health_metrics': health_metrics,
                'redis_status': redis_info,
                'cache_statistics': cache_stats,
                'active_issues': active_issues,
                'alerts': self._generate_health_alerts(health_metrics),
                'status_details': health_status['details']
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Failed to get cache health status: {e}")
            return {'error': str(e)}
    
    async def create_performance_snapshot(self, snapshot_type: str = "hourly") -> None:
        """Create periodic performance snapshot"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Calculate time range based on snapshot type
            if snapshot_type == "hourly":
                period_start = current_time.replace(minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(hours=1)
            elif snapshot_type == "daily":
                period_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1)
            elif snapshot_type == "weekly":
                # Start of week (Monday)
                days_since_monday = current_time.weekday()
                period_start = (current_time - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                period_end = period_start + timedelta(days=7)
            else:
                raise ValueError(f"Invalid snapshot type: {snapshot_type}")
            
            # Get metrics for the period
            metrics = await self.get_cache_performance_metrics(period_start, period_end, "hour")
            
            if not metrics:
                return
            
            # Create snapshot record
            session = self.SessionLocal()
            try:
                snapshot = CachePerformanceSnapshot(
                    snapshot_type=snapshot_type,
                    snapshot_period_start=period_start,
                    snapshot_period_end=period_end,
                    total_requests=metrics['summary']['total_operations'],
                    cache_hits=metrics['summary']['total_hits'],
                    cache_misses=metrics['summary']['total_misses'],
                    cache_evictions=metrics['summary'].get('total_evictions', 0),
                    hit_rate=metrics['summary']['hit_rate_percent'],
                    miss_rate=metrics['summary']['miss_rate_percent'],
                    avg_response_time_ms=metrics['summary']['avg_response_time_ms'],
                    efficiency_score=metrics['performance_scores']['efficiency_score'],
                    performance_score=metrics['performance_scores']['performance_score'],
                    cost_savings_usd=metrics['cost_analysis']['estimated_cost_savings_usd'],
                    endpoint_breakdown=metrics['endpoint_analysis'][:10],  # Top 10
                    time_breakdown=metrics['time_series']
                )
                
                session.add(snapshot)
                session.commit()
                
                # Track snapshot creation
                await self.event_tracker.track_event(
                    "cache_snapshot_created",
                    {
                        "snapshot_type": snapshot_type,
                        "period": f"{period_start.isoformat()} to {period_end.isoformat()}",
                        "total_requests": metrics['summary']['total_operations'],
                        "hit_rate": metrics['summary']['hit_rate_percent']
                    }
                )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to create performance snapshot: {e}")
    
    async def get_historical_performance(
        self,
        days_back: int = 30,
        snapshot_type: str = "daily"
    ) -> Dict[str, Any]:
        """Get historical cache performance data"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)
            
            session = self.SessionLocal()
            try:
                snapshots = session.query(CachePerformanceSnapshot).filter(
                    CachePerformanceSnapshot.snapshot_type == snapshot_type,
                    CachePerformanceSnapshot.snapshot_period_start >= start_date,
                    CachePerformanceSnapshot.snapshot_period_end <= end_date
                ).order_by(CachePerformanceSnapshot.snapshot_period_start).all()
                
                # Calculate trends
                trend_analysis = self._calculate_performance_trends(snapshots)
                
                # Generate performance report
                performance_report = {
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'days': days_back,
                        'snapshot_type': snapshot_type
                    },
                    'trend_analysis': trend_analysis,
                    'snapshots': [
                        {
                            'period': f"{snapshot.snapshot_period_start.isoformat()} - {snapshot.snapshot_period_end.isoformat()}",
                            'total_requests': snapshot.total_requests,
                            'hit_rate': snapshot.hit_rate,
                            'avg_response_time_ms': snapshot.avg_response_time_ms,
                            'efficiency_score': snapshot.efficiency_score,
                            'performance_score': snapshot.performance_score,
                            'cost_savings_usd': snapshot.cost_savings_usd
                        }
                        for snapshot in snapshots
                    ],
                    'summary': {
                        'total_requests': sum(s.total_requests for s in snapshots),
                        'avg_hit_rate': statistics.mean([s.hit_rate for s in snapshots]) if snapshots else 0,
                        'avg_efficiency': statistics.mean([s.efficiency_score for s in snapshots]) if snapshots else 0,
                        'total_cost_savings': sum(s.cost_savings_usd for s in snapshots)
                    }
                }
                
                return performance_report
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to get historical performance: {e}")
            return {'error': str(e)}
    
    async def _update_cache_counters(self, metric_type: str, metric_value: float) -> None:
        """Update real-time cache counters"""
        current_time = datetime.now(timezone.utc)
        
        # Update minute counters
        minute_key = f"cache:counters:minute:{current_time.strftime('%Y%m%d%H%M')}"
        await self.redis_cache.hincrby(minute_key, metric_type, 1)
        await self.redis_cache.expire(minute_key, 3600)
        
        # Update hourly counters
        hour_key = f"cache:counters:hour:{current_time.strftime('%Y%m%d%H')}"
        await self.redis_cache.hincrby(hour_key, metric_type, 1)
        await self.redis_cache.expire(hour_key, 86400)
    
    def _calculate_efficiency_score(self, hit_rate: float, total_operations: int) -> float:
        """Calculate cache efficiency score (0-100)"""
        if total_operations < self.config['min_cache_entries_for_analysis']:
            return 0.0
        
        # Base score from hit rate
        hit_rate_score = min(hit_rate / self.config['target_hit_rate'], 1.0) * 70
        
        # Bonus for high usage volume
        volume_score = min(math.log10(total_operations) / 4, 1.0) * 30
        
        return hit_rate_score + volume_score
    
    def _calculate_performance_score(
        self,
        hit_rate: float,
        avg_response_time: float,
        total_evictions: int
    ) -> float:
        """Calculate cache performance score (0-100)"""
        # Hit rate component (0-50 points)
        hit_rate_score = min(hit_rate / 100.0, 1.0) * 50
        
        # Response time component (0-30 points, inverse relationship)
        max_response_time = self.config['max_avg_response_time_ms']
        response_time_score = max(0, (max_response_time - avg_response_time) / max_response_time) * 30
        
        # Eviction penalty (0-20 points, inverse relationship)
        max_acceptable_evictions = 1000
        eviction_score = max(0, (max_acceptable_evictions - total_evictions) / max_acceptable_evictions) * 20
        
        return hit_rate_score + response_time_score + eviction_score
    
    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade from score"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def _analyze_hit_rate_trend(self, time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze hit rate trends"""
        if not time_series:
            return {}
        
        hit_rates = [row['hit_rate'] for row in time_series if 'hit_rate' in row]
        
        if len(hit_rates) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend
        first_half = hit_rates[:len(hit_rates)//2]
        second_half = hit_rates[len(hit_rates)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        trend_direction = "improving" if second_avg > first_avg else "declining" if second_avg < first_avg else "stable"
        trend_magnitude = abs(second_avg - first_avg)
        
        return {
            'trend': trend_direction,
            'magnitude': round(trend_magnitude, 2),
            'current_avg': round(statistics.mean(hit_rates), 2),
            'min_hit_rate': round(min(hit_rates), 2),
            'max_hit_rate': round(max(hit_rates), 2),
            'volatility': round(statistics.stdev(hit_rates) if len(hit_rates) > 1 else 0, 2)
        }
    
    def _analyze_response_time_patterns(self, time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response time patterns"""
        if not time_series:
            return {}
        
        response_times = [row['avg_response_time_ms'] for row in time_series if row.get('avg_response_time_ms')]
        
        if not response_times:
            return {}
        
        return {
            'avg_response_time': round(statistics.mean(response_times), 2),
            'median_response_time': round(statistics.median(response_times), 2),
            'p95_response_time': round(self._calculate_percentile(response_times, 95), 2),
            'p99_response_time': round(self._calculate_percentile(response_times, 99), 2),
            'min_response_time': round(min(response_times), 2),
            'max_response_time': round(max(response_times), 2),
            'volatility': round(statistics.stdev(response_times) if len(response_times) > 1 else 0, 2)
        }
    
    def _analyze_endpoint_efficiency(self, endpoint_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze endpoint-level efficiency"""
        if not endpoint_analysis:
            return {}
        
        # Categorize endpoints by performance
        high_performers = [e for e in endpoint_analysis if e['hit_rate'] >= 80]
        medium_performers = [e for e in endpoint_analysis if 50 <= e['hit_rate'] < 80]
        low_performers = [e for e in endpoint_analysis if e['hit_rate'] < 50]
        
        return {
            'total_endpoints': len(endpoint_analysis),
            'high_performers': len(high_performers),
            'medium_performers': len(medium_performers),
            'low_performers': len(low_performers),
            'efficiency_distribution': {
                'high': round(len(high_performers) / len(endpoint_analysis) * 100, 1),
                'medium': round(len(medium_performers) / len(endpoint_analysis) * 100, 1),
                'low': round(len(low_performers) / len(endpoint_analysis) * 100, 1)
            },
            'top_performers': sorted(high_performers, key=lambda x: x['hit_rate'], reverse=True)[:5],
            'improvement_candidates': sorted(low_performers, key=lambda x: x['total_requests'], reverse=True)[:5]
        }
    
    def _calculate_cache_health_score(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive cache health score"""
        summary = metrics.get('summary', {})
        performance = metrics.get('performance_scores', {})
        
        # Health components
        hit_rate_health = min(summary.get('hit_rate_percent', 0) / 100.0, 1.0) * 25
        response_time_health = max(0, 1 - (summary.get('avg_response_time_ms', 0) / self.config['max_avg_response_time_ms'])) * 25
        efficiency_health = min(performance.get('efficiency_score', 0) / 100.0, 1.0) * 25
        performance_score_health = min(performance.get('performance_score', 0) / 100.0, 1.0) * 25
        
        total_score = hit_rate_health + response_time_health + efficiency_health + performance_score_health
        
        return {
            'overall_score': round(total_score, 1),
            'components': {
                'hit_rate_health': round(hit_rate_health, 1),
                'response_time_health': round(response_time_health, 1),
                'efficiency_health': round(efficiency_health, 1),
                'performance_health': round(performance_score_health, 1)
            },
            'status': 'healthy' if total_score >= 75 else 'degraded' if total_score >= 50 else 'critical'
        }
    
    async def _identify_optimization_opportunities(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify cache optimization opportunities"""
        opportunities = []
        
        # Low hit rate optimization
        hit_rate = metrics['summary'].get('hit_rate_percent', 0)
        if hit_rate < self.config['target_hit_rate'] * 100:
            opportunities.append({
                'type': 'hit_rate_improvement',
                'severity': 'high' if hit_rate < 50 else 'medium',
                'description': f"Hit rate is {hit_rate:.1f}%, below target of {self.config['target_hit_rate']*100:.0f}%",
                'current_value': hit_rate,
                'target_value': self.config['target_hit_rate'] * 100,
                'potential_improvement': min(20, (self.config['target_hit_rate'] * 100) - hit_rate)
            })
        
        # Response time optimization
        avg_response_time = metrics['summary'].get('avg_response_time_ms', 0)
        if avg_response_time > self.config['max_avg_response_time_ms']:
            opportunities.append({
                'type': 'response_time_optimization',
                'severity': 'high' if avg_response_time > 2000 else 'medium',
                'description': f"Average response time is {avg_response_time:.1f}ms, above target of {self.config['max_avg_response_time_ms']}ms",
                'current_value': avg_response_time,
                'target_value': self.config['max_avg_response_time_ms'],
                'potential_improvement': min(50, (avg_response_time - self.config['max_avg_response_time_ms']) / avg_response_time * 100)
            })
        
        # Memory usage optimization
        # This would require actual memory usage data
        
        return opportunities
    
    def _prioritize_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize optimization recommendations"""
        # Sort by severity and potential improvement
        severity_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        def priority_score(rec):
            return (
                severity_weights.get(rec.get('severity', 'low'), 1) * 100 +
                rec.get('potential_improvement', 0)
            )
        
        return sorted(recommendations, key=priority_score, reverse=True)
    
    async def _store_optimization_recommendations(self, recommendations: List[Dict[str, Any]]) -> None:
        """Store optimization recommendations in database"""
        session = self.SessionLocal()
        try:
            for rec in recommendations:
                optimization = CacheOptimization(
                    optimization_type=rec['type'],
                    endpoint_pattern=rec.get('endpoint_pattern', '*'),
                    severity=rec['severity'],
                    description=rec['description'],
                    current_value=rec['current_value'],
                    recommended_value=rec.get('target_value', 0),
                    expected_improvement=rec.get('potential_improvement', 0)
                )
                session.add(optimization)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store optimization recommendations: {e}")
        finally:
            session.close()
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index == int(index):
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    async def _get_redis_memory_info(self) -> Dict[str, Any]:
        """Get Redis memory information"""
        try:
            # This would use Redis INFO command in real implementation
            return {
                'used_memory_human': '128M',
                'used_memory_peak_human': '256M',
                'used_memory_rss_human': '130M',
                'mem_fragmentation_ratio': 1.02,
                'connected_clients': 25,
                'status': 'healthy'
            }
        except Exception as e:
            logger.error(f"Failed to get Redis memory info: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            # Get cache size and entry count from Redis
            cache_info = await self.redis_cache.info()
            
            return {
                'total_keys': cache_info.get('db0', {}).get('keys', 0),
                'total_size_bytes': cache_info.get('used_memory', 0),
                'memory_usage_mb': round(cache_info.get('used_memory', 0) / (1024 * 1024), 2),
                'hit_ratio': cache_info.get('keyspace_hits', 0) / max(1, cache_info.get('keyspace_hits', 0) + cache_info.get('keyspace_misses', 0)),
                'status': 'healthy' if cache_info.get('status') == 'ok' else 'degraded'
            }
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_health_metrics(
        self,
        metrics: Dict[str, Any],
        redis_info: Dict[str, Any],
        cache_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate cache health metrics"""
        hit_rate = metrics.get('summary', {}).get('hit_rate_percent', 0)
        response_time = metrics.get('summary', {}).get('avg_response_time_ms', 0)
        memory_usage = cache_stats.get('memory_usage_mb', 0)
        
        return {
            'hit_rate_score': min(hit_rate / 100.0 * 25, 25),
            'response_time_score': max(0, (1000 - response_time) / 1000 * 25),
            'memory_usage_score': max(0, (512 - memory_usage) / 512 * 25),
            'efficiency_score': min(metrics.get('performance_scores', {}).get('efficiency_score', 0) / 100.0 * 25, 25)
        }
    
    def _determine_health_status(self, health_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall health status"""
        total_score = sum(health_metrics.values())
        
        if total_score >= 80:
            status = 'healthy'
            details = 'Cache is performing optimally'
        elif total_score >= 60:
            status = 'degraded'
            details = 'Cache performance is below optimal'
        else:
            status = 'critical'
            details = 'Cache requires immediate attention'
        
        return {
            'status': status,
            'score': total_score,
            'details': details
        }
    
    async def _get_active_cache_issues(self) -> List[Dict[str, Any]]:
        """Get active cache issues"""
        # This would query for active issues and anomalies
        return []
    
    def _generate_health_alerts(self, health_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate health alerts based on metrics"""
        alerts = []
        
        for metric, score in health_metrics.items():
            if score < 15:  # Below 60% of maximum score
                alerts.append({
                    'type': metric,
                    'severity': 'high' if score < 5 else 'medium',
                    'message': f"{metric.replace('_', ' ').title()} is significantly below target"
                })
        
        return alerts
    
    async def _analyze_ttl_optimization(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze TTL optimization opportunities"""
        recommendations = []
        
        # Analyze endpoints with low hit rates for TTL extension
        for endpoint in metrics.get('endpoint_analysis', []):
            if endpoint['hit_rate'] < 60 and endpoint['total_requests'] > 100:
                recommendations.append({
                    'type': 'ttl_extension',
                    'severity': 'medium',
                    'description': f"Consider extending TTL for {endpoint['endpoint']} (hit rate: {endpoint['hit_rate']:.1f}%)",
                    'current_value': 300,  # Default TTL
                    'target_value': 600,
                    'potential_improvement': 15.0,
                    'endpoint_pattern': endpoint['endpoint']
                })
        
        return recommendations
    
    async def _analyze_cache_key_patterns(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze cache key patterns for optimization"""
        recommendations = []
        
        # This would analyze cache key patterns and suggest improvements
        return recommendations
    
    async def _analyze_memory_allocation(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze memory allocation optimization"""
        recommendations = []
        
        # This would analyze memory usage patterns
        return recommendations
    
    async def _analyze_cache_strategy(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze cache strategy optimization"""
        recommendations = []
        
        # This would analyze overall caching strategy
        return recommendations
    
    def _generate_efficiency_recommendations(
        self,
        metrics: Dict[str, Any],
        opportunities: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate efficiency improvement recommendations"""
        recommendations = []
        
        hit_rate = metrics['summary'].get('hit_rate_percent', 0)
        
        if hit_rate < 70:
            recommendations.append("Increase cache TTL for frequently accessed endpoints")
            recommendations.append("Implement cache warming for critical endpoints")
        
        if len(opportunities) > 5:
            recommendations.append("Review and optimize cache configuration")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal - continue current strategy")
        
        return recommendations
    
    def _calculate_performance_trends(self, snapshots: List[CachePerformanceSnapshot]) -> Dict[str, Any]:
        """Calculate performance trends from historical snapshots"""
        if len(snapshots) < 2:
            return {'trend': 'insufficient_data'}
        
        hit_rates = [s.hit_rate for s in snapshots]
        performance_scores = [s.performance_score for s in snapshots]
        
        # Simple trend calculation
        first_half_hr = statistics.mean(hit_rates[:len(hit_rates)//2])
        second_half_hr = statistics.mean(hit_rates[len(hit_rates)//2:])
        
        hr_trend = "improving" if second_half_hr > first_half_hr else "declining" if second_half_hr < first_half_hr else "stable"
        
        first_half_ps = statistics.mean(performance_scores[:len(performance_scores)//2])
        second_half_ps = statistics.mean(performance_scores[len(performance_scores)//2:])
        
        ps_trend = "improving" if second_half_ps > first_half_ps else "declining" if second_half_ps < first_half_ps else "stable"
        
        return {
            'hit_rate_trend': hr_trend,
            'performance_trend': ps_trend,
            'overall_trend': 'improving' if hr_trend == 'improving' and ps_trend == 'improving' else 'mixed'
        }
    
    async def _analyze_cache_capacity(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cache capacity and growth patterns"""
        # This would analyze capacity trends and predict future needs
        return {
            'current_capacity_utilization': 65.5,
            'projected_monthly_growth': 12.3,
            'recommended_capacity_increase': 0,
            'capacity_status': 'adequate'
        }
    
    async def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """Clean up old cache metrics"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            session = self.SessionLocal()
            try:
                # Delete old metric records
                deleted_metrics = session.query(CacheMetricRecord).filter(
                    CacheMetricRecord.timestamp < cutoff_date
                ).count()
                
                session.query(CacheMetricRecord).filter(
                    CacheMetricRecord.timestamp < cutoff_date
                ).delete()
                
                # Delete old snapshots beyond retention period
                snapshot_cutoff = datetime.now(timezone.utc) - timedelta(days=self.config['snapshot_retention_days'])
                deleted_snapshots = session.query(CachePerformanceSnapshot).filter(
                    CachePerformanceSnapshot.created_at < snapshot_cutoff
                ).count()
                
                session.query(CachePerformanceSnapshot).filter(
                    CachePerformanceSnapshot.created_at < snapshot_cutoff
                ).delete()
                
                session.commit()
                
                total_deleted = deleted_metrics + deleted_snapshots
                logger.info(f"Cleaned up {total_deleted} old cache metrics")
                
                return total_deleted
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
        
        logger.info("CacheAnalytics closed")