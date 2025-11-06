"""
API Key Analytics and Cost Tracking Service

Provides comprehensive analytics for API key usage patterns, cost tracking,
usage forecasting, and anomaly detection. Integrates with telemetry system
for real-time monitoring and provides detailed reporting capabilities.
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

from app.models.proxy import APIKey, ProxyRequestCache
from app.core.database import get_database_url
from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

Base = declarative_base()

class APIKeyUsageRecord(Base):
    """Track detailed API key usage patterns"""
    __tablename__ = "api_key_usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, index=True, nullable=False)
    endpoint_path = Column(String(512), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)
    request_size = Column(Integer, default=0)
    response_size = Column(Integer, default=0)
    user_id = Column(Integer, index=True, nullable=True)
    organization_id = Column(Integer, index=True, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    cost_estimate = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_usage_key_timestamp', 'api_key_id', 'timestamp'),
        Index('idx_usage_endpoint_timestamp', 'endpoint_path', 'timestamp'),
        Index('idx_usage_org_timestamp', 'organization_id', 'timestamp'),
    )

class APIKeyCostRecord(Base):
    """Track costs per API key"""
    __tablename__ = "api_key_cost_records"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, index=True, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    request_count = Column(Integer, default=0)
    data_transfer_gb = Column(Float, default=0.0)
    compute_time_seconds = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, nullable=True)  # Detailed cost breakdown
    timestamp = Column(DateTime(timezone=True), default=func.now())

class UsageAnomaly(Base):
    """Detect usage anomalies"""
    __tablename__ = "usage_anomalies"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, index=True, nullable=False)
    anomaly_type = Column(String(50), nullable=False)  # usage_spike, unusual_endpoint, cost_anomaly
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    baseline_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    deviation_percentage = Column(Float, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

class UsageForecast(Base):
    """Store usage forecasts"""
    __tablename__ = "usage_forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, index=True, nullable=False)
    forecast_period = Column(String(20), nullable=False)  # daily, weekly, monthly
    forecast_date = Column(DateTime(timezone=True), nullable=False)
    predicted_requests = Column(Float, nullable=False)
    predicted_cost = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)
    factors = Column(JSON, nullable=True)  # Factors influencing forecast
    created_at = Column(DateTime(timezone=True), default=func.now())

class KeyAnalytics:
    """
    API Key Analytics and Cost Tracking Manager
    
    Features:
    - Usage pattern analysis
    - Cost tracking and allocation
    - Usage forecasting
    - Anomaly detection
    - Performance metrics
    - Integration with telemetry system
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
            'anomaly_detection_window': 24,  # hours
            'anomaly_threshold': 2.5,  # standard deviations
            'forecast_horizon_days': 30,
            'cost_per_request': 0.001,  # base cost per request
            'cost_per_mb': 0.05,  # cost per MB transferred
            'cost_per_second': 0.001,  # cost per second compute time
            'cache_ttl': 300,  # 5 minutes
        }
        
        # Usage tracking for real-time analytics
        self._usage_buffer = deque(maxlen=1000)
        self._last_cleanup = datetime.now(timezone.utc)
        
        logger.info("KeyAnalytics initialized")
    
    async def record_usage(
        self,
        api_key_id: int,
        endpoint_path: str,
        method: str,
        status_code: int,
        response_time: float,
        request_size: int = 0,
        response_size: int = 0,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Record API key usage for analytics"""
        try:
            # Calculate cost estimate
            cost_estimate = self._calculate_cost_estimate(
                response_time, request_size, response_size
            )
            
            # Store in database
            session = self.SessionLocal()
            try:
                usage_record = APIKeyUsageRecord(
                    api_key_id=api_key_id,
                    endpoint_path=endpoint_path,
                    method=method.upper(),
                    status_code=status_code,
                    response_time=response_time,
                    request_size=request_size,
                    response_size=response_size,
                    user_id=user_id,
                    organization_id=organization_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    cost_estimate=cost_estimate,
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(usage_record)
                
                # Update cached counters
                await self._update_usage_cache(api_key_id, cost_estimate)
                
                session.commit()
                
                # Add to real-time buffer
                self._usage_buffer.append({
                    'api_key_id': api_key_id,
                    'cost': cost_estimate,
                    'timestamp': datetime.now(timezone.utc)
                })
                
                # Track analytics event
                await self.event_tracker.track_event(
                    "api_key_usage_recorded",
                    {
                        "api_key_id": api_key_id,
                        "endpoint": endpoint_path,
                        "cost_estimate": cost_estimate,
                        "response_time": response_time
                    }
                )
                
                # Trigger anomaly detection
                asyncio.create_task(self._check_anomalies(api_key_id))
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
    
    async def get_usage_analytics(
        self,
        api_key_id: int,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "hour"
    ) -> Dict[str, Any]:
        """Get comprehensive usage analytics for API key"""
        cache_key = f"analytics:{api_key_id}:{start_date.isoformat()}:{end_date.isoformat()}:{group_by}"
        
        # Check cache
        cached_result = await self.redis_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        session = self.SessionLocal()
        try:
            # Base query
            query = session.query(APIKeyUsageRecord).filter(
                APIKeyUsageRecord.api_key_id == api_key_id,
                APIKeyUsageRecord.timestamp >= start_date,
                APIKeyUsageRecord.timestamp <= end_date
            )
            
            # Group by time period
            if group_by == "hour":
                time_group = func.date_trunc('hour', APIKeyUsageRecord.timestamp)
            elif group_by == "day":
                time_group = func.date_trunc('day', APIKeyUsageRecord.timestamp)
            elif group_by == "week":
                time_group = func.date_trunc('week', APIKeyUsageRecord.timestamp)
            else:
                time_group = func.date_trunc('day', APIKeyUsageRecord.timestamp)
            
            # Time series data
            time_series = query.with_entities(
                time_group.label('period'),
                func.count(APIKeyUsageRecord.id).label('request_count'),
                func.sum(APIKeyUsageRecord.cost_estimate).label('total_cost'),
                func.avg(APIKeyUsageRecord.response_time).label('avg_response_time'),
                func.sum(APIKeyUsageRecord.response_size).label('total_response_size')
            ).group_by(time_group).order_by('period').all()
            
            # Endpoint breakdown
            endpoint_breakdown = query.with_entities(
                APIKeyUsageRecord.endpoint_path,
                func.count(APIKeyUsageRecord.id).label('request_count'),
                func.sum(APIKeyUsageRecord.cost_estimate).label('total_cost'),
                func.avg(APIKeyUsageRecord.response_time).label('avg_response_time')
            ).group_by(APIKeyUsageRecord.endpoint_path).order_by(desc('request_count')).all()
            
            # Status code breakdown
            status_breakdown = query.with_entities(
                APIKeyUsageRecord.status_code,
                func.count(APIKeyUsageRecord.id).label('request_count'),
                func.sum(APIKeyUsageRecord.cost_estimate).label('total_cost')
            ).group_by(APIKeyUsageRecord.status_code).all()
            
            # Compute derived metrics
            total_requests = sum(row.request_count for row in time_series)
            total_cost = sum(row.total_cost for row in time_series)
            avg_response_time = statistics.mean([row.avg_response_time for row in time_series if row.avg_response_time]) if time_series else 0
            
            # Peak usage analysis
            peak_hour = max(time_series, key=lambda x: x.request_count) if time_series else None
            peak_cost = max(time_series, key=lambda x: x.total_cost) if time_series else None
            
            # Performance metrics
            performance_metrics = {
                'avg_response_time': avg_response_time,
                'p95_response_time': self._calculate_percentile([row.avg_response_time for row in time_series if row.avg_response_time], 95),
                'p99_response_time': self._calculate_percentile([row.avg_response_time for row in time_series if row.avg_response_time], 99),
                'error_rate': self._calculate_error_rate(query),
                'throughput_rps': total_requests / max(1, (end_date - start_date).total_seconds()),
            }
            
            analytics = {
                'api_key_id': api_key_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'group_by': group_by
                },
                'summary': {
                    'total_requests': total_requests,
                    'total_cost': total_cost,
                    'unique_endpoints': len(endpoint_breakdown),
                    'average_cost_per_request': total_cost / max(1, total_requests)
                },
                'time_series': [
                    {
                        'period': row.period.isoformat() if row.period else None,
                        'requests': row.request_count,
                        'cost': float(row.total_cost or 0),
                        'avg_response_time': float(row.avg_response_time or 0),
                        'data_transferred_mb': float(row.total_response_size or 0) / (1024 * 1024)
                    }
                    for row in time_series
                ],
                'endpoint_breakdown': [
                    {
                        'endpoint': row.endpoint_path,
                        'requests': row.request_count,
                        'cost': float(row.total_cost or 0),
                        'avg_response_time': float(row.avg_response_time or 0)
                    }
                    for row in endpoint_breakdown
                ],
                'status_breakdown': [
                    {
                        'status_code': row.status_code,
                        'requests': row.request_count,
                        'cost': float(row.total_cost or 0)
                    }
                    for row in status_breakdown
                ],
                'performance_metrics': performance_metrics,
                'peak_usage': {
                    'peak_hour': peak_hour.period.isoformat() if peak_hour else None,
                    'peak_requests': peak_hour.request_count if peak_hour else 0,
                    'peak_cost_period': peak_cost.period.isoformat() if peak_cost else None,
                    'peak_cost_value': float(peak_cost.total_cost or 0) if peak_cost else 0
                }
            }
            
            # Cache result
            await self.redis_cache.set(cache_key, analytics, ttl=self.config['cache_ttl'])
            
            return analytics
            
        finally:
            session.close()
    
    async def get_cost_breakdown(
        self,
        api_key_id: int,
        start_date: datetime,
        end_date: datetime,
        breakdown_type: str = "daily"
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown"""
        cache_key = f"cost_breakdown:{api_key_id}:{start_date.isoformat()}:{end_date.isoformat()}:{breakdown_type}"
        
        cached_result = await self.redis_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        session = self.SessionLocal()
        try:
            # Get cost records
            query = session.query(APIKeyCostRecord).filter(
                APIKeyCostRecord.api_key_id == api_key_id,
                APIKeyCostRecord.period_start >= start_date,
                APIKeyCostRecord.period_end <= end_date,
                APIKeyCostRecord.period_type == breakdown_type
            ).order_by(APIKeyCostRecord.period_start)
            
            cost_records = query.all()
            
            # Aggregate data
            total_cost = sum(record.total_cost for record in cost_records)
            total_requests = sum(record.request_count for record in cost_records)
            total_data_gb = sum(record.data_transfer_gb for record in cost_records)
            total_compute_time = sum(record.compute_time_seconds for record in cost_records)
            
            # Cost component breakdown
            component_costs = defaultdict(float)
            for record in cost_records:
                if record.cost_breakdown:
                    for component, cost in record.cost_breakdown.items():
                        component_costs[component] += cost
            
            cost_breakdown = {
                'total_cost': total_cost,
                'cost_per_request': total_cost / max(1, total_requests),
                'cost_per_gb': total_cost / max(0.001, total_data_gb),
                'cost_per_compute_hour': total_cost / max(0.001, total_compute_time / 3600),
                'components': dict(component_costs),
                'period_breakdown': [
                    {
                        'period': f"{record.period_start.isoformat()}-{record.period_end.isoformat()}",
                        'cost': record.total_cost,
                        'requests': record.request_count,
                        'data_gb': record.data_transfer_gb,
                        'compute_time_seconds': record.compute_time_seconds
                    }
                    for record in cost_records
                ]
            }
            
            # Cache result
            await self.redis_cache.set(cache_key, cost_breakdown, ttl=self.config['cache_ttl'])
            
            return cost_breakdown
            
        finally:
            session.close()
    
    async def detect_anomalies(
        self,
        api_key_id: Optional[int] = None,
        severity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Detect usage anomalies"""
        session = self.SessionLocal()
        try:
            query = session.query(UsageAnomaly).filter(
                UsageAnomaly.is_resolved == False
            )
            
            if api_key_id:
                query = query.filter(UsageAnomaly.api_key_id == api_key_id)
            
            if severity_filter:
                query = query.filter(UsageAnomaly.severity == severity_filter)
            
            anomalies = query.order_by(desc(UsageAnomaly.created_at)).limit(100).all()
            
            return [
                {
                    'id': anomaly.id,
                    'api_key_id': anomaly.api_key_id,
                    'anomaly_type': anomaly.anomaly_type,
                    'severity': anomaly.severity,
                    'description': anomaly.description,
                    'baseline_value': anomaly.baseline_value,
                    'current_value': anomaly.current_value,
                    'deviation_percentage': anomaly.deviation_percentage,
                    'created_at': anomaly.created_at.isoformat(),
                    'metadata': anomaly.metadata
                }
                for anomaly in anomalies
            ]
            
        finally:
            session.close()
    
    async def generate_forecast(
        self,
        api_key_id: int,
        forecast_horizon_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate usage forecast for API key"""
        if forecast_horizon_days is None:
            forecast_horizon_days = self.config['forecast_horizon_days']
        
        session = self.SessionLocal()
        try:
            # Get historical data (last 90 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=90)
            
            historical_data = session.query(APIKeyUsageRecord).filter(
                APIKeyUsageRecord.api_key_id == api_key_id,
                APIKeyUsageRecord.timestamp >= start_date,
                APIKeyUsageRecord.timestamp <= end_date
            ).with_entities(
                func.date_trunc('day', APIKeyUsageRecord.timestamp).label('day'),
                func.count(APIKeyUsageRecord.id).label('requests'),
                func.sum(APIKeyUsageRecord.cost_estimate).label('cost')
            ).group_by(func.date_trunc('day', APIKeyUsageRecord.timestamp)).all()
            
            if len(historical_data) < 7:
                return {'error': 'Insufficient historical data for forecasting'}
            
            # Simple forecasting using moving averages and trend analysis
            daily_requests = [row.requests for row in historical_data]
            daily_costs = [row.cost for row in historical_data]
            
            # Calculate trend
            trend_slope_requests = self._calculate_trend(daily_requests)
            trend_slope_costs = self._calculate_trend(daily_costs)
            
            # Calculate seasonal factors (day of week)
            seasonal_factors = self._calculate_seasonal_factors(historical_data)
            
            # Generate forecast
            forecasts = []
            base_requests = statistics.mean(daily_requests[-7:])  # Last 7 days average
            base_costs = statistics.mean(daily_costs[-7:])
            
            for i in range(1, forecast_horizon_days + 1):
                forecast_date = end_date + timedelta(days=i)
                day_of_week = forecast_date.weekday()
                
                # Apply trend and seasonal adjustments
                trend_adjusted_requests = base_requests + (trend_slope_requests * i)
                seasonal_adjusted_requests = trend_adjusted_requests * seasonal_factors.get(day_of_week, 1.0)
                
                trend_adjusted_costs = base_costs + (trend_slope_costs * i)
                seasonal_adjusted_costs = trend_adjusted_costs * seasonal_factors.get(day_of_week, 1.0)
                
                # Ensure non-negative values
                predicted_requests = max(0, seasonal_adjusted_requests)
                predicted_cost = max(0, seasonal_adjusted_costs)
                
                # Calculate confidence (decreases with forecast horizon)
                confidence = max(0.5, 0.95 - (i * 0.01))
                
                forecasts.append({
                    'forecast_date': forecast_date.date().isoformat(),
                    'predicted_requests': round(predicted_requests, 2),
                    'predicted_cost': round(predicted_cost, 4),
                    'confidence_level': confidence
                })
            
            # Store forecast in database
            for forecast in forecasts:
                forecast_record = UsageForecast(
                    api_key_id=api_key_id,
                    forecast_period="daily",
                    forecast_date=datetime.fromisoformat(forecast['forecast_date']),
                    predicted_requests=forecast['predicted_requests'],
                    predicted_cost=forecast['predicted_cost'],
                    confidence_level=forecast['confidence_level'],
                    model_version="v1.0",
                    factors={
                        'trend_slope_requests': trend_slope_requests,
                        'trend_slope_costs': trend_slope_costs,
                        'seasonal_factors': seasonal_factors,
                        'historical_days': len(historical_data)
                    }
                )
                session.add(forecast_record)
            
            session.commit()
            
            return {
                'api_key_id': api_key_id,
                'forecast_horizon_days': forecast_horizon_days,
                'historical_period': f"{start_date.date().isoformat()} to {end_date.date().isoformat()}",
                'model_info': {
                    'version': 'v1.0',
                    'historical_data_points': len(historical_data),
                    'trend_slope_requests': trend_slope_requests,
                    'trend_slope_costs': trend_slope_costs,
                    'seasonal_factors': seasonal_factors
                },
                'forecasts': forecasts
            }
            
        finally:
            session.close()
    
    async def get_realtime_metrics(self, api_key_id: int) -> Dict[str, Any]:
        """Get real-time usage metrics"""
        current_time = datetime.now(timezone.utc)
        
        # Filter recent usage from buffer
        recent_usage = [
            record for record in self._usage_buffer
            if record['api_key_id'] == api_key_id and 
            (current_time - record['timestamp']).total_seconds() < 3600  # Last hour
        ]
        
        if not recent_usage:
            # Get from cache or database
            cache_key = f"realtime:{api_key_id}"
            cached_metrics = await self.redis_cache.get(cache_key)
            if cached_metrics:
                return cached_metrics
        
        # Calculate real-time metrics
        total_requests = len(recent_usage)
        total_cost = sum(record['cost'] for record in recent_usage)
        
        # Calculate requests per minute
        minute_ago = current_time - timedelta(minutes=1)
        recent_minute = [
            record for record in recent_usage 
            if record['timestamp'] >= minute_ago
        ]
        rps = len(recent_minute) / 60.0 if recent_minute else 0
        
        metrics = {
            'api_key_id': api_key_id,
            'timestamp': current_time.isoformat(),
            'last_hour': {
                'total_requests': total_requests,
                'total_cost': round(total_cost, 4),
                'avg_cost_per_request': round(total_cost / max(1, total_requests), 6)
            },
            'realtime': {
                'requests_per_second': round(rps, 2),
                'requests_last_minute': len(recent_minute),
                'estimated_hourly_requests': round(rps * 3600, 0)
            }
        }
        
        # Cache for 30 seconds
        cache_key = f"realtime:{api_key_id}"
        await self.redis_cache.set(cache_key, metrics, ttl=30)
        
        return metrics
    
    async def generate_usage_report(
        self,
        api_key_id: int,
        report_type: str = "monthly",
        include_forecasts: bool = True,
        include_anomalies: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive usage report"""
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        if report_type == "daily":
            start_date = end_date - timedelta(days=1)
        elif report_type == "weekly":
            start_date = end_date - timedelta(weeks=1)
        else:  # monthly
            start_date = end_date - timedelta(days=30)
        
        # Get analytics data
        analytics = await self.get_usage_analytics(api_key_id, start_date, end_date, "daily")
        cost_breakdown = await self.get_cost_breakdown(api_key_id, start_date, end_date, "daily")
        
        report = {
            'report_info': {
                'api_key_id': api_key_id,
                'report_type': report_type,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'generated_at': datetime.now(timezone.utc).isoformat()
            },
            'summary': analytics['summary'],
            'usage_analytics': analytics,
            'cost_analysis': cost_breakdown,
        }
        
        # Include forecasts if requested
        if include_forecasts:
            forecast = await self.generate_forecast(api_key_id)
            if 'error' not in forecast:
                report['forecast'] = forecast
        
        # Include anomalies if requested
        if include_anomalies:
            anomalies = await self.detect_anomalies(api_key_id=api_key_id)
            if anomalies:
                report['anomalies'] = anomalies
        
        # Track report generation
        await self.event_tracker.track_event(
            "usage_report_generated",
            {
                "api_key_id": api_key_id,
                "report_type": report_type,
                "total_requests": analytics['summary']['total_requests'],
                "total_cost": analytics['summary']['total_cost']
            }
        )
        
        return report
    
    def _calculate_cost_estimate(
        self,
        response_time: float,
        request_size: int,
        response_size: int
    ) -> float:
        """Calculate cost estimate for a request"""
        # Base cost per request
        base_cost = self.config['cost_per_request']
        
        # Data transfer cost
        total_data_mb = (request_size + response_size) / (1024 * 1024)
        data_cost = total_data_mb * self.config['cost_per_mb']
        
        # Compute time cost
        compute_cost = response_time * self.config['cost_per_second']
        
        return base_cost + data_cost + compute_cost
    
    async def _update_usage_cache(self, api_key_id: int, cost_estimate: float) -> None:
        """Update usage counters in cache"""
        current_time = datetime.now(timezone.utc)
        
        # Daily counters
        day_key = f"usage:daily:{api_key_id}:{current_time.date().isoformat()}"
        await self.redis_cache.incr(day_key)
        await self.redis_cache.expire(day_key, 86400 * 2)  # 2 days
        
        # Cost counters
        cost_key = f"cost:daily:{api_key_id}:{current_time.date().isoformat()}"
        await self.redis_cache.incrbyfloat(cost_key, cost_estimate)
        await self.redis_cache.expire(cost_key, 86400 * 2)
        
        # Hourly counters
        hour_key = f"usage:hourly:{api_key_id}:{current_time.strftime('%Y-%m-%d-%H')}"
        await self.redis_cache.incr(hour_key)
        await self.redis_cache.expire(hour_key, 86400)
    
    async def _check_anomalies(self, api_key_id: int) -> None:
        """Check for usage anomalies"""
        try:
            current_time = datetime.now(timezone.utc)
            window_start = current_time - timedelta(hours=self.config['anomaly_detection_window'])
            
            session = self.SessionLocal()
            try:
                # Get usage for anomaly detection window
                recent_usage = session.query(APIKeyUsageRecord).filter(
                    APIKeyUsageRecord.api_key_id == api_key_id,
                    APIKeyUsageRecord.timestamp >= window_start,
                    APIKeyUsageRecord.timestamp <= current_time
                ).all()
                
                if len(recent_usage) < 10:  # Need minimum data points
                    return
                
                # Get historical baseline (previous period)
                baseline_start = window_start - timedelta(hours=self.config['anomaly_detection_window'])
                baseline_usage = session.query(APIKeyUsageRecord).filter(
                    APIKeyUsageRecord.api_key_id == api_key_id,
                    APIKeyUsageRecord.timestamp >= baseline_start,
                    APIKeyUsageRecord.timestamp < window_start
                ).all()
                
                if len(baseline_usage) < 10:
                    return
                
                # Calculate baseline metrics
                baseline_requests = len(baseline_usage)
                baseline_cost = sum(record.cost_estimate for record in baseline_usage)
                baseline_avg_response_time = statistics.mean([record.response_time for record in baseline_usage])
                
                # Calculate current metrics
                current_requests = len(recent_usage)
                current_cost = sum(record.cost_estimate for record in recent_usage)
                current_avg_response_time = statistics.mean([record.response_time for record in recent_usage])
                
                # Check for anomalies
                threshold = self.config['anomaly_threshold']
                
                # Usage spike detection
                if baseline_requests > 0:
                    usage_ratio = current_requests / baseline_requests
                    if usage_ratio > (1 + threshold):
                        await self._create_anomaly(
                            api_key_id,
                            "usage_spike",
                            "medium" if usage_ratio < 3.0 else "high",
                            f"Usage increased by {(usage_ratio - 1) * 100:.1f}%",
                            baseline_requests,
                            current_requests,
                            ((current_requests - baseline_requests) / baseline_requests) * 100
                        )
                
                # Cost anomaly detection
                if baseline_cost > 0:
                    cost_ratio = current_cost / baseline_cost
                    if cost_ratio > (1 + threshold):
                        await self._create_anomaly(
                            api_key_id,
                            "cost_anomaly",
                            "medium" if cost_ratio < 3.0 else "high",
                            f"Cost increased by {(cost_ratio - 1) * 100:.1f}%",
                            baseline_cost,
                            current_cost,
                            ((current_cost - baseline_cost) / baseline_cost) * 100
                        )
                
                # Response time anomaly
                if baseline_avg_response_time > 0:
                    response_time_ratio = current_avg_response_time / baseline_avg_response_time
                    if response_time_ratio > (1 + threshold * 0.5):  # More sensitive for performance
                        await self._create_anomaly(
                            api_key_id,
                            "performance_degradation",
                            "low" if response_time_ratio < 2.0 else "medium",
                            f"Response time increased by {(response_time_ratio - 1) * 100:.1f}%",
                            baseline_avg_response_time,
                            current_avg_response_time,
                            ((current_avg_response_time - baseline_avg_response_time) / baseline_avg_response_time) * 100
                        )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to check anomalies: {e}")
    
    async def _create_anomaly(
        self,
        api_key_id: int,
        anomaly_type: str,
        severity: str,
        description: str,
        baseline_value: float,
        current_value: float,
        deviation_percentage: float
    ) -> None:
        """Create anomaly record"""
        session = self.SessionLocal()
        try:
            anomaly = UsageAnomaly(
                api_key_id=api_key_id,
                anomaly_type=anomaly_type,
                severity=severity,
                description=description,
                baseline_value=baseline_value,
                current_value=current_value,
                deviation_percentage=deviation_percentage,
                metadata={
                    'detection_time': datetime.now(timezone.utc).isoformat(),
                    'window_hours': self.config['anomaly_detection_window']
                }
            )
            session.add(anomaly)
            session.commit()
            
            # Track anomaly event
            await self.event_tracker.track_event(
                "anomaly_detected",
                {
                    "api_key_id": api_key_id,
                    "anomaly_type": anomaly_type,
                    "severity": severity,
                    "deviation_percentage": deviation_percentage
                }
            )
            
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
    
    def _calculate_error_rate(self, query) -> float:
        """Calculate error rate from query"""
        try:
            total_requests = query.count()
            error_requests = query.filter(
                APIKeyUsageRecord.status_code >= 400
            ).count()
            
            return (error_requests / max(1, total_requests)) * 100
        except Exception:
            return 0.0
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope using linear regression"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / max(denominator, 1e-6)
    
    def _calculate_seasonal_factors(self, historical_data: List) -> Dict[int, float]:
        """Calculate seasonal factors for day of week"""
        day_totals = defaultdict(list)
        
        for record in historical_data:
            day_of_week = record.day.weekday()
            day_totals[day_of_week].append(record.requests)
        
        # Calculate average for each day of week
        day_averages = {}
        overall_average = statistics.mean([record.requests for record in historical_data])
        
        for day in range(7):
            if day in day_totals:
                day_averages[day] = statistics.mean(day_totals[day]) / overall_average
            else:
                day_averages[day] = 1.0
        
        return day_averages
    
    async def cleanup_old_data(self, retention_days: int = 90) -> int:
        """Clean up old analytics data"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        session = self.SessionLocal()
        try:
            # Delete old usage records
            deleted_usage = session.query(APIKeyUsageRecord).filter(
                APIKeyUsageRecord.timestamp < cutoff_date
            ).count()
            
            session.query(APIKeyUsageRecord).filter(
                APIKeyUsageRecord.timestamp < cutoff_date
            ).delete()
            
            # Delete old cost records
            deleted_cost = session.query(APIKeyCostRecord).filter(
                APIKeyCostRecord.period_end < cutoff_date
            ).count()
            
            session.query(APIKeyCostRecord).filter(
                APIKeyCostRecord.period_end < cutoff_date
            ).delete()
            
            # Delete resolved anomalies older than 30 days
            anomaly_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            deleted_anomalies = session.query(UsageAnomaly).filter(
                UsageAnomaly.is_resolved == True,
                UsageAnomaly.resolved_at < anomaly_cutoff
            ).count()
            
            session.query(UsageAnomaly).filter(
                UsageAnomaly.is_resolved == True,
                UsageAnomaly.resolved_at < anomaly_cutoff
            ).delete()
            
            # Delete old forecasts
            deleted_forecasts = session.query(UsageForecast).filter(
                UsageForecast.forecast_date < cutoff_date
            ).count()
            
            session.query(UsageForecast).filter(
                UsageForecast.forecast_date < cutoff_date
            ).delete()
            
            session.commit()
            
            total_deleted = deleted_usage + deleted_cost + deleted_anomalies + deleted_forecasts
            
            logger.info(f"Cleaned up {total_deleted} old analytics records")
            
            return total_deleted
            
        finally:
            session.close()
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
        
        logger.info("KeyAnalytics closed")