"""
Usage Analytics

Advanced usage pattern analysis and insights:
- Usage trend analysis
- User behavior patterns
- Cost analysis and optimization
- Performance metrics
- Predictive analytics
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc
from dataclasses import dataclass
from enum import Enum
import statistics
import numpy as np
from collections import defaultdict, Counter

from app.models.credit import (
    CreditUsageRecord, LLMUsageMetrics, CreditAccount, LLMModelType
)
from app.models.user import User


class AnalyticsPeriod(Enum):
    """Analytics periods"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AnalyticsMetric(Enum):
    """Analytics metrics"""
    COST = "cost"
    TOKENS = "tokens"
    REQUESTS = "requests"
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"


@dataclass
class UsagePattern:
    """Usage pattern analysis result"""
    pattern_type: str
    description: str
    confidence: float
    trend: str  # increasing, decreasing, stable
    impact_score: float
    insights: List[str]
    recommendations: List[str]


@dataclass
class AnalyticsSummary:
    """Comprehensive analytics summary"""
    period: str
    start_date: datetime
    end_date: datetime
    total_requests: int
    total_cost: float
    total_tokens: int
    avg_response_time: float
    success_rate: float
    top_models: List[Dict[str, Any]]
    usage_trends: List[Dict[str, Any]]
    cost_analysis: Dict[str, Any]
    patterns: List[UsagePattern]


class UsageAnalytics:
    """
    Advanced usage analytics and pattern recognition
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_usage_trends(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: AnalyticsPeriod = AnalyticsPeriod.DAILY
    ) -> Dict[str, Any]:
        """
        Analyze usage trends over time
        
        Args:
            user_id: Specific user to analyze
            organization_id: Organization to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            period: Time period for aggregation
        
        Returns:
            Trend analysis data
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Build query
        query = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date,
                CreditUsageRecord.service_type == "llm"
            )
        )
        
        # Filter by user or organization
        if user_id:
            query = query.join(CreditAccount).filter(CreditAccount.user_id == user_id)
        elif organization_id:
            query = query.join(CreditAccount).filter(CreditAccount.organization_id == organization_id)
        
        usage_records = query.all()
        
        if not usage_records:
            return {"error": "No usage data found for the specified criteria"}
        
        # Aggregate by time periods
        period_data = self._aggregate_by_period(usage_records, period)
        
        # Calculate trend metrics
        trends = self._calculate_trends(period_data)
        
        # Identify patterns
        patterns = self._identify_patterns(period_data, usage_records)
        
        return {
            "period": period.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_points": len(period_data),
            "trends": trends,
            "period_data": period_data,
            "patterns": [self._pattern_to_dict(p) for p in patterns],
            "summary": self._generate_trend_summary(period_data, trends)
        }
    
    def analyze_user_behavior(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user behavior patterns
        
        Args:
            user_id: User to analyze
            days_back: Number of days to look back
        
        Returns:
            User behavior analysis
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Get user's usage records
        usage_records = self.db.query(CreditUsageRecord).join(
            CreditAccount, CreditUsageRecord.account_id == CreditAccount.id
        ).filter(
            and_(
                CreditAccount.user_id == user_id,
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date,
                CreditUsageRecord.service_type == "llm"
            )
        ).all()
        
        if not usage_records:
            return {"error": "No usage data found for user"}
        
        # Analyze behavior patterns
        usage_frequency = self._analyze_usage_frequency(usage_records)
        usage_timing = self._analyze_usage_timing(usage_records)
        usage_volume = self._analyze_usage_volume(usage_records)
        request_patterns = self._analyze_request_patterns(usage_records)
        model_preferences = self._analyze_model_preferences(usage_records)
        
        # Calculate behavior metrics
        total_sessions = len(set(record.resource_id for record in usage_records if record.resource_id))
        avg_session_length = self._calculate_avg_session_length(usage_records)
        peak_usage_hours = self._find_peak_usage_hours(usage_records)
        
        # Generate insights
        insights = self._generate_user_insights(
            usage_records, usage_frequency, usage_timing, usage_volume
        )
        
        # Calculate user score (engagement, efficiency, etc.)
        user_score = self._calculate_user_score(
            usage_records, usage_frequency, usage_volume, request_patterns
        )
        
        return {
            "user_id": user_id,
            "analysis_period_days": days_back,
            "total_usage_records": len(usage_records),
            "usage_frequency": usage_frequency,
            "usage_timing": usage_timing,
            "usage_volume": usage_volume,
            "request_patterns": request_patterns,
            "model_preferences": model_preferences,
            "total_sessions": total_sessions,
            "avg_session_length_minutes": avg_session_length,
            "peak_usage_hours": peak_usage_hours,
            "user_score": user_score,
            "insights": insights,
            "recommendations": self._generate_user_recommendations(
                usage_records, usage_frequency, usage_volume, model_preferences
            )
        }
    
    def analyze_cost_patterns(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze cost patterns and optimization opportunities
        
        Args:
            user_id: User to analyze
            organization_id: Organization to analyze
            days_back: Analysis period
        
        Returns:
            Cost analysis data
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Get usage records
        query = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date,
                CreditUsageRecord.service_type == "llm"
            )
        )
        
        if user_id:
            query = query.join(CreditAccount).filter(CreditAccount.user_id == user_id)
        elif organization_id:
            query = query.join(CreditAccount).filter(CreditAccount.organization_id == organization_id)
        
        usage_records = query.all()
        
        if not usage_records:
            return {"error": "No cost data found"}
        
        # Cost breakdown analysis
        cost_breakdown = self._analyze_cost_breakdown(usage_records)
        
        # Cost trends over time
        cost_trends = self._analyze_cost_trends(usage_records)
        
        # Model cost efficiency
        model_efficiency = self._analyze_model_efficiency(usage_records)
        
        # Cost anomalies detection
        cost_anomalies = self._detect_cost_anomalies(usage_records)
        
        # Optimization opportunities
        optimization_opportunities = self._identify_cost_optimization(usage_records)
        
        # Calculate cost metrics
        total_cost = sum(record.total_cost for record in usage_records)
        avg_cost_per_request = total_cost / len(usage_records)
        cost_per_token = total_cost / sum(record.total_cost / record.cost_per_unit for record in usage_records if record.cost_per_unit > 0)
        
        # Cost prediction
        cost_prediction = self._predict_future_costs(usage_records)
        
        return {
            "analysis_period_days": days_back,
            "total_cost": round(total_cost, 6),
            "avg_cost_per_request": round(avg_cost_per_request, 6),
            "cost_per_token": round(cost_per_token, 6),
            "total_requests": len(usage_records),
            "cost_breakdown": cost_breakdown,
            "cost_trends": cost_trends,
            "model_efficiency": model_efficiency,
            "cost_anomalies": cost_anomalies,
            "optimization_opportunities": optimization_opportunities,
            "cost_prediction": cost_prediction,
            "cost_distribution": self._analyze_cost_distribution(usage_records)
        }
    
    def generate_comprehensive_report(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days_back: int = 30
    ) -> AnalyticsSummary:
        """
        Generate comprehensive usage analytics report
        
        Args:
            user_id: User for report
            organization_id: Organization for report
            days_back: Report period
        
        Returns:
            Comprehensive analytics summary
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Get usage data
        query = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date,
                CreditUsageRecord.service_type == "llm"
            )
        )
        
        if user_id:
            query = query.join(CreditAccount).filter(CreditAccount.user_id == user_id)
        elif organization_id:
            query = query.join(CreditAccount).filter(CreditAccount.organization_id == organization_id)
        
        usage_records = query.all()
        
        if not usage_records:
            return AnalyticsSummary(
                period=f"{days_back} days",
                start_date=start_date,
                end_date=end_date,
                total_requests=0,
                total_cost=0.0,
                total_tokens=0,
                avg_response_time=0.0,
                success_rate=0.0,
                top_models=[],
                usage_trends=[],
                cost_analysis={},
                patterns=[]
            )
        
        # Calculate summary metrics
        total_requests = len(usage_records)
        total_cost = sum(record.total_cost for record in usage_records)
        total_tokens = sum(record.total_cost / record.cost_per_unit for record in usage_records if record.cost_per_unit > 0)
        
        response_times = [record.response_time_ms for record in usage_records if record.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        successful_requests = sum(1 for record in usage_records if record.success)
        success_rate = successful_requests / total_requests
        
        # Top models analysis
        top_models = self._get_top_models(usage_records)
        
        # Usage trends
        usage_trends = self._analyze_usage_trends(user_id, organization_id, start_date, end_date)
        
        # Cost analysis
        cost_analysis = self._analyze_cost_patterns(user_id, organization_id, days_back)
        
        # Usage patterns
        patterns = self._identify_patterns(
            self._aggregate_by_period(usage_records, AnalyticsPeriod.DAILY),
            usage_records
        )
        
        return AnalyticsSummary(
            period=f"{days_back} days",
            start_date=start_date,
            end_date=end_date,
            total_requests=total_requests,
            total_cost=total_cost,
            total_tokens=int(total_tokens),
            avg_response_time=avg_response_time,
            success_rate=success_rate,
            top_models=top_models,
            usage_trends=usage_trends.get("trends", []),
            cost_analysis=cost_analysis,
            patterns=patterns
        )
    
    # Analysis helper methods
    
    def _aggregate_by_period(self, usage_records: List[CreditUsageRecord], period: AnalyticsPeriod) -> List[Dict[str, Any]]:
        """Aggregate usage data by time period"""
        if period == AnalyticsPeriod.HOURLY:
            return self._aggregate_hourly(usage_records)
        elif period == AnalyticsPeriod.DAILY:
            return self._aggregate_daily(usage_records)
        elif period == AnalyticsPeriod.WEEKLY:
            return self._aggregate_weekly(usage_records)
        else:  # MONTHLY
            return self._aggregate_monthly(usage_records)
    
    def _aggregate_hourly(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Aggregate by hour"""
        hourly_data = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "response_times": [], "successes": 0
        })
        
        for record in usage_records:
            hour_key = record.created_at.replace(minute=0, second=0, microsecond=0).isoformat()
            data = hourly_data[hour_key]
            data["requests"] += 1
            data["cost"] += record.total_cost
            data["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
            if record.response_time_ms:
                data["response_times"].append(record.response_time_ms)
            if record.success:
                data["successes"] += 1
        
        return [
            {
                "period": period_key,
                **{
                    k: v for k, v in data.items() 
                    if k != "response_times"
                },
                "avg_response_time": sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0,
                "success_rate": data["successes"] / data["requests"] if data["requests"] > 0 else 0
            }
            for period_key, data in sorted(hourly_data.items())
        ]
    
    def _aggregate_daily(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Aggregate by day"""
        daily_data = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "response_times": [], "successes": 0
        })
        
        for record in usage_records:
            day_key = record.created_at.date().isoformat()
            data = daily_data[day_key]
            data["requests"] += 1
            data["cost"] += record.total_cost
            data["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
            if record.response_time_ms:
                data["response_times"].append(record.response_time_ms)
            if record.success:
                data["successes"] += 1
        
        return [
            {
                "period": period_key,
                **{
                    k: v for k, v in data.items() 
                    if k != "response_times"
                },
                "avg_response_time": sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0,
                "success_rate": data["successes"] / data["requests"] if data["requests"] > 0 else 0
            }
            for period_key, data in sorted(daily_data.items())
        ]
    
    def _aggregate_weekly(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Aggregate by week"""
        weekly_data = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "response_times": [], "successes": 0
        })
        
        for record in usage_records:
            # Get week start (Monday)
            week_start = record.created_at.date() - timedelta(days=record.created_at.weekday())
            week_key = week_start.isoformat()
            data = weekly_data[week_key]
            data["requests"] += 1
            data["cost"] += record.total_cost
            data["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
            if record.response_time_ms:
                data["response_times"].append(record.response_time_ms)
            if record.success:
                data["successes"] += 1
        
        return [
            {
                "period": period_key,
                **{
                    k: v for k, v in data.items() 
                    if k != "response_times"
                },
                "avg_response_time": sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0,
                "success_rate": data["successes"] / data["requests"] if data["requests"] > 0 else 0
            }
            for period_key, data in sorted(weekly_data.items())
        ]
    
    def _aggregate_monthly(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Aggregate by month"""
        monthly_data = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "response_times": [], "successes": 0
        })
        
        for record in usage_records:
            month_key = record.created_at.strftime("%Y-%m")
            data = monthly_data[month_key]
            data["requests"] += 1
            data["cost"] += record.total_cost
            data["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
            if record.response_time_ms:
                data["response_times"].append(record.response_time_ms)
            if record.success:
                data["successes"] += 1
        
        return [
            {
                "period": period_key,
                **{
                    k: v for k, v in data.items() 
                    if k != "response_times"
                },
                "avg_response_time": sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0,
                "success_rate": data["successes"] / data["requests"] if data["requests"] > 0 else 0
            }
            for period_key, data in sorted(monthly_data.items())
        ]
    
    def _calculate_trends(self, period_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend metrics from period data"""
        if len(period_data) < 2:
            return {"trend": "insufficient_data", "confidence": 0.0}
        
        # Extract cost values for trend analysis
        costs = [data["cost"] for data in period_data]
        requests = [data["requests"] for data in period_data]
        
        # Calculate trend using simple linear regression
        def calculate_slope(values):
            if len(values) < 2:
                return 0
            n = len(values)
            x = list(range(n))
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            return slope
        
        cost_slope = calculate_slope(costs)
        request_slope = calculate_slope(requests)
        
        # Determine overall trend
        if cost_slope > 0.01:
            cost_trend = "increasing"
        elif cost_slope < -0.01:
            cost_trend = "decreasing"
        else:
            cost_trend = "stable"
        
        if request_slope > 0.01:
            request_trend = "increasing"
        elif request_slope < -0.01:
            request_trend = "decreasing"
        else:
            request_trend = "stable"
        
        # Calculate confidence based on variance
        cost_variance = statistics.variance(costs) if len(costs) > 1 else 0
        confidence = 1.0 / (1.0 + cost_variance)
        
        return {
            "cost_trend": cost_trend,
            "request_trend": request_trend,
            "cost_slope": cost_slope,
            "request_slope": request_slope,
            "confidence": min(1.0, confidence)
        }
    
    def _identify_patterns(
        self,
        period_data: List[Dict[str, Any]],
        usage_records: List[CreditUsageRecord]
    ) -> List[UsagePattern]:
        """Identify usage patterns"""
        patterns = []
        
        # Pattern 1: Weekend usage drop
        weekend_pattern = self._detect_weekend_pattern(usage_records)
        if weekend_pattern:
            patterns.append(weekend_pattern)
        
        # Pattern 2: Peak usage hours
        peak_hours_pattern = self._detect_peak_hours_pattern(usage_records)
        if peak_hours_pattern:
            patterns.append(peak_hours_pattern)
        
        # Pattern 3: Cost spikes
        cost_spike_pattern = self._detect_cost_spikes(period_data)
        if cost_spike_pattern:
            patterns.append(cost_spike_pattern)
        
        # Pattern 4: Model usage concentration
        model_concentration_pattern = self._detect_model_concentration(usage_records)
        if model_concentration_pattern:
            patterns.append(model_concentration_pattern)
        
        # Pattern 5: Batch processing behavior
        batch_pattern = self._detect_batch_processing(usage_records)
        if batch_pattern:
            patterns.append(batch_pattern)
        
        return patterns
    
    def _detect_weekend_pattern(self, usage_records: List[CreditUsageRecord]) -> Optional[UsagePattern]:
        """Detect weekend usage patterns"""
        weekday_usage = defaultdict(int)
        weekend_usage = defaultdict(int)
        
        for record in usage_records:
            day_of_week = record.created_at.weekday()
            usage_amount = record.total_cost
            
            if day_of_week < 5:  # Monday to Friday
                weekday_usage[day_of_week] += usage_amount
            else:  # Weekend
                weekend_usage[day_of_week] += usage_amount
        
        if not weekday_usage or not weekend_usage:
            return None
        
        avg_weekday = sum(weekday_usage.values()) / len(weekday_usage)
        avg_weekend = sum(weekend_usage.values()) / len(weekend_usage)
        
        if avg_weekday > avg_weekend * 1.5:  # Significant difference
            return UsagePattern(
                pattern_type="weekend_drop",
                description="Usage drops significantly on weekends",
                confidence=0.8,
                trend="stable",
                impact_score=0.6,
                insights=[
                    f"Weekday usage is {avg_weekday/avg_weekend:.1f}x higher than weekend usage",
                    "Opportunity to optimize weekend costs"
                ],
                recommendations=[
                    "Consider reducing weekend processing capacity",
                    "Schedule non-critical processing for weekdays"
                ]
            )
        
        return None
    
    def _detect_peak_hours_pattern(self, usage_records: List[CreditUsageRecord]) -> Optional[UsagePattern]:
        """Detect peak usage hours"""
        hourly_usage = defaultdict(float)
        
        for record in usage_records:
            hour = record.created_at.hour
            hourly_usage[hour] += record.total_cost
        
        if not hourly_usage:
            return None
        
        peak_hour = max(hourly_usage, key=hourly_usage.get)
        peak_usage = hourly_usage[peak_hour]
        avg_usage = sum(hourly_usage.values()) / len(hourly_usage)
        
        if peak_usage > avg_usage * 2:  # Significant peak
            return UsagePattern(
                pattern_type="peak_hours",
                description=f"Peak usage occurs at {peak_hour}:00",
                confidence=0.9,
                trend="stable",
                impact_score=0.7,
                insights=[
                    f"Peak hour usage is {peak_usage/avg_usage:.1f}x the average",
                    "Consider load balancing during peak hours"
                ],
                recommendations=[
                    "Implement request queuing during peak hours",
                    "Consider upgrading service tier during peak periods"
                ]
            )
        
        return None
    
    def _detect_cost_spikes(self, period_data: List[Dict[str, Any]]) -> Optional[UsagePattern]:
        """Detect cost spikes in the data"""
        if len(period_data) < 3:
            return None
        
        costs = [data["cost"] for data in period_data]
        avg_cost = sum(costs) / len(costs)
        std_dev = statistics.stdev(costs) if len(costs) > 1 else 0
        
        spike_threshold = avg_cost + 2 * std_dev
        spike_periods = [data for data in period_data if data["cost"] > spike_threshold]
        
        if spike_periods:
            spike_rate = len(spike_periods) / len(period_data)
            return UsagePattern(
                pattern_type="cost_spikes",
                description=f"Cost spikes detected in {len(spike_periods)} periods",
                confidence=0.8,
                trend="variable",
                impact_score=0.8,
                insights=[
                    f"{len(spike_periods)} cost spikes detected",
                    f"Spike rate: {spike_rate:.1%} of periods"
                ],
                recommendations=[
                    "Implement cost alerts for sudden increases",
                    "Review spike periods for optimization opportunities"
                ]
            )
        
        return None
    
    def _detect_model_concentration(self, usage_records: List[CreditUsageRecord]) -> Optional[UsagePattern]:
        """Detect concentration on specific models"""
        model_usage = Counter(record.model_used for record in usage_records if record.model_used)
        
        if not model_usage:
            return None
        
        total_usage = sum(model_usage.values())
        max_model = model_usage.most_common(1)[0]
        concentration_ratio = max_model[1] / total_usage
        
        if concentration_ratio > 0.8:  # 80% concentration
            return UsagePattern(
                pattern_type="model_concentration",
                description=f"Heavy concentration on {max_model[0]} model",
                confidence=0.9,
                trend="stable",
                impact_score=0.6,
                insights=[
                    f"{max_model[0]} model used for {concentration_ratio:.1%} of requests",
                    "Consider model diversification for cost optimization"
                ],
                recommendations=[
                    "Evaluate cheaper alternatives for simple tasks",
                    "Implement model routing based on task complexity"
                ]
            )
        
        return None
    
    def _detect_batch_processing(self, usage_records: List[CreditUsageRecord]) -> Optional[UsagePattern]:
        """Detect batch processing patterns"""
        # Group by resource_id to find batch operations
        resource_batches = defaultdict(list)
        
        for record in usage_records:
            if record.resource_id:
                resource_batches[record.resource_id].append(record)
        
        batch_sizes = [len(batch) for batch in resource_batches.values() if len(batch) > 1]
        
        if batch_sizes:
            avg_batch_size = sum(batch_sizes) / len(batch_sizes)
            max_batch_size = max(batch_sizes)
            
            if avg_batch_size > 10 or max_batch_size > 50:
                return UsagePattern(
                    pattern_type="batch_processing",
                    description="Large batch operations detected",
                    confidence=0.8,
                    trend="increasing",
                    impact_score=0.7,
                    insights=[
                        f"Average batch size: {avg_batch_size:.1f}",
                        f"Maximum batch size: {max_batch_size}"
                    ],
                    recommendations=[
                        "Consider batch processing discounts",
                        "Optimize batch size for cost efficiency"
                    ]
                )
        
        return None
    
    def _analyze_usage_frequency(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze usage frequency patterns"""
        # Group by date to find daily usage patterns
        daily_usage = defaultdict(int)
        
        for record in usage_records:
            date_key = record.created_at.date().isoformat()
            daily_usage[date_key] += record.total_cost
        
        if not daily_usage:
            return {}
        
        # Calculate frequency metrics
        total_days = len(daily_usage)
        active_days = len([cost for cost in daily_usage.values() if cost > 0])
        usage_rate = active_days / total_days if total_days > 0 else 0
        
        # Calculate daily cost statistics
        daily_costs = list(daily_usage.values())
        avg_daily_cost = sum(daily_costs) / len(daily_costs)
        
        # Find most active days
        sorted_days = sorted(daily_usage.items(), key=lambda x: x[1], reverse=True)
        top_days = [{"date": date, "cost": cost} for date, cost in sorted_days[:5]]
        
        return {
            "total_days": total_days,
            "active_days": active_days,
            "usage_rate": usage_rate,
            "avg_daily_cost": avg_daily_cost,
            "top_active_days": top_days,
            "inactive_days": total_days - active_days
        }
    
    def _analyze_usage_timing(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze usage timing patterns"""
        hourly_usage = defaultdict(float)
        daily_usage = defaultdict(float)
        
        for record in usage_records:
            hour = record.created_at.hour
            day = record.created weekday()
            
            hourly_usage[hour] += record.total_cost
            daily_usage[day] += record.total_cost
        
        # Find peak hours
        peak_hour = max(hourly_usage, key=hourly_usage.get) if hourly_usage else None
        peak_day = max(daily_usage, key=daily_usage.get) if daily_usage else None
        
        # Calculate distribution
        total_usage = sum(hourly_usage.values())
        hourly_distribution = {
            hour: (usage / total_usage * 100) if total_usage > 0 else 0
            for hour, usage in hourly_usage.items()
        }
        
        return {
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "hourly_distribution": hourly_distribution,
            "total_hours_active": len([h for h in hourly_usage.values() if h > 0]),
            "most_inactive_hour": min(hourly_usage, key=hourly_usage.get) if hourly_usage else None
        }
    
    def _analyze_usage_volume(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze usage volume patterns"""
        costs = [record.total_cost for record in usage_records]
        
        if not costs:
            return {}
        
        # Calculate volume statistics
        total_volume = sum(costs)
        avg_volume = total_volume / len(costs)
        
        # Find volume outliers
        if len(costs) > 1:
            std_dev = statistics.stdev(costs)
            outliers = [cost for cost in costs if abs(cost - avg_volume) > 2 * std_dev]
        else:
            outliers = []
        
        # Calculate usage concentration (Pareto analysis)
        sorted_costs = sorted(costs, reverse=True)
        cumulative_costs = []
        running_sum = 0
        total = sum(sorted_costs)
        
        for cost in sorted_costs:
            running_sum += cost
            cumulative_costs.append(running_sum / total * 100)
        
        # Find 80th percentile point (Pareto principle)
        pareto_point = next((i for i, pct in enumerate(cumulative_costs) if pct >= 80), len(cumulative_costs))
        
        return {
            "total_volume": total_volume,
            "avg_volume_per_request": avg_volume,
            "max_volume": max(costs),
            "min_volume": min(costs),
            "volume_variance": statistics.variance(costs) if len(costs) > 1 else 0,
            "outlier_count": len(outliers),
            "pareto_concentration": {
                "requests_in_80_percent": pareto_point + 1,
                "percentage_of_requests": ((pareto_point + 1) / len(costs)) * 100
            }
        }
    
    def _analyze_request_patterns(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze request patterns and behavior"""
        # Success rate analysis
        total_requests = len(usage_records)
        successful_requests = sum(1 for record in usage_records if record.success)
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        # Response time analysis
        response_times = [record.response_time_ms for record in usage_records if record.response_time_ms]
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
            p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
        
        # Session analysis
        session_lengths = []
        current_session = []
        
        # Group records by resource_id (session identifier)
        sessions = defaultdict(list)
        for record in usage_records:
            if record.resource_id:
                sessions[record.resource_id].append(record)
        
        for session_records in sessions.values():
            session_cost = sum(record.total_cost for record in session_records)
            session_lengths.append(session_cost)
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": success_rate,
            "response_time_metrics": {
                "avg_response_time_ms": avg_response_time,
                "p95_response_time_ms": p95_response_time,
                "p99_response_time_ms": p99_response_time
            },
            "session_metrics": {
                "total_sessions": len(sessions),
                "avg_session_cost": sum(session_lengths) / len(session_lengths) if session_lengths else 0,
                "max_session_cost": max(session_lengths) if session_lengths else 0
            }
        }
    
    def _analyze_model_preferences(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze model usage preferences"""
        model_usage = Counter(record.model_used for record in usage_records if record.model_used)
        model_costs = defaultdict(float)
        model_tokens = defaultdict(int)
        model_success_rates = defaultdict(lambda: {"success": 0, "total": 0})
        
        for record in usage_records:
            if record.model_used:
                model_costs[record.model_used] += record.total_cost
                model_tokens[record.model_used] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
                model_success_rates[record.model_used]["total"] += 1
                if record.success:
                    model_success_rates[record.model_used]["success"] += 1
        
        # Calculate success rates
        model_analysis = {}
        for model, cost in model_costs.items():
            success_data = model_success_rates[model]
            success_rate = success_data["success"] / success_data["total"] if success_data["total"] > 0 else 0
            
            model_analysis[model] = {
                "cost": cost,
                "requests": model_usage.get(model, 0),
                "tokens": model_tokens[model],
                "success_rate": success_rate,
                "avg_cost_per_request": cost / model_usage.get(model, 1)
            }
        
        # Find preferred model
        preferred_model = max(model_analysis, key=lambda x: model_analysis[x]["cost"]) if model_analysis else None
        
        return {
            "preferred_model": preferred_model,
            "model_distribution": model_analysis,
            "total_models_used": len(model_analysis),
            "model_diversity_index": len(model_analysis) / len(usage_records) if usage_records else 0
        }
    
    def _calculate_avg_session_length(self, usage_records: List[CreditUsageRecord]) -> float:
        """Calculate average session length in minutes"""
        # This is a simplified calculation
        # In production, you'd want proper session tracking
        session_costs = []
        
        sessions = defaultdict(list)
        for record in usage_records:
            if record.resource_id:
                sessions[record.resource_id].append(record)
        
        for session_records in sessions.values():
            session_cost = sum(record.total_cost for record in session_records)
            session_costs.append(session_cost)
        
        return sum(session_costs) / len(session_costs) if session_costs else 0
    
    def _find_peak_usage_hours(self, usage_records: List[CreditUsageRecord]) -> List[int]:
        """Find peak usage hours"""
        hourly_usage = defaultdict(float)
        
        for record in usage_records:
            hourly_usage[record.created_at.hour] += record.total_cost
        
        if not hourly_usage:
            return []
        
        # Find hours with above-average usage
        avg_usage = sum(hourly_usage.values()) / len(hourly_usage)
        peak_hours = [hour for hour, usage in hourly_usage.items() if usage > avg_usage * 1.2]
        
        return sorted(peak_hours)
    
    def _generate_user_insights(
        self,
        usage_records: List[CreditUsageRecord],
        usage_frequency: Dict[str, Any],
        usage_timing: Dict[str, Any],
        usage_volume: Dict[str, Any]
    ) -> List[str]:
        """Generate insights about user behavior"""
        insights = []
        
        # Frequency insights
        if usage_frequency.get("usage_rate", 0) < 0.5:
            insights.append("User shows intermittent usage patterns")
        elif usage_frequency.get("usage_rate", 0) > 0.8:
            insights.append("User demonstrates consistent daily usage")
        
        # Timing insights
        if usage_timing.get("peak_hour") is not None:
            peak_hour = usage_timing["peak_hour"]
            if 9 <= peak_hour <= 17:
                insights.append("Usage peaks during business hours")
            elif 18 <= peak_hour <= 22:
                insights.append("Usage peaks during evening hours")
        
        # Volume insights
        if usage_volume.get("outlier_count", 0) > 0:
            insights.append("User occasionally makes high-volume requests")
        
        # Success rate insights
        success_rate = sum(1 for record in usage_records if record.success) / len(usage_records)
        if success_rate > 0.95:
            insights.append("User shows excellent request success rate")
        elif success_rate < 0.8:
            insights.append("User experiences frequent request failures")
        
        return insights
    
    def _calculate_user_score(
        self,
        usage_records: List[CreditUsageRecord],
        usage_frequency: Dict[str, Any],
        usage_volume: Dict[str, Any],
        request_patterns: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate overall user score"""
        score_components = {}
        
        # Engagement score (based on usage frequency)
        usage_rate = usage_frequency.get("usage_rate", 0)
        score_components["engagement"] = min(1.0, usage_rate * 2)  # Scale to 1.0
        
        # Efficiency score (based on cost per token/result)
        avg_cost_per_token = sum(record.cost_per_unit for record in usage_records) / len(usage_records)
        score_components["efficiency"] = max(0, 1.0 - min(1.0, avg_cost_per_token / 0.01))  # Lower cost is better
        
        # Success score (based on success rate)
        success_rate = request_patterns.get("success_rate", 0)
        score_components["success"] = success_rate
        
        # Consistency score (based on variance in usage)
        costs = [record.total_cost for record in usage_records]
        if len(costs) > 1:
            cv = statistics.stdev(costs) / (sum(costs) / len(costs))  # Coefficient of variation
            score_components["consistency"] = max(0, 1.0 - min(1.0, cv))
        else:
            score_components["consistency"] = 0.5
        
        # Overall score (weighted average)
        weights = {"engagement": 0.3, "efficiency": 0.3, "success": 0.3, "consistency": 0.1}
        overall_score = sum(score_components[key] * weights[key] for key in weights)
        
        return {
            "overall_score": overall_score,
            **score_components
        }
    
    def _generate_user_recommendations(
        self,
        usage_records: List[CreditUsageRecord],
        usage_frequency: Dict[str, Any],
        usage_volume: Dict[str, Any],
        model_preferences: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized recommendations for users"""
        recommendations = []
        
        # Model recommendations
        preferred_model = model_preferences.get("preferred_model")
        if preferred_model == "gpt-4":
            recommendations.append("Consider using GPT-3.5-Turbo for simpler tasks to reduce costs")
        
        # Volume recommendations
        avg_volume = usage_volume.get("avg_volume_per_request", 0)
        if avg_volume > 0.1:  # High cost per request
            recommendations.append("Optimize prompts to reduce token usage and costs")
        
        # Timing recommendations
        peak_hour = usage_frequency.get("peak_hour")
        if peak_hour and 9 <= peak_hour <= 17:
            recommendations.append("Schedule batch processing during off-peak hours to improve performance")
        
        # Success rate recommendations
        success_rate = sum(1 for record in usage_records if record.success) / len(usage_records)
        if success_rate < 0.9:
            recommendations.append("Review failed requests to identify improvement opportunities")
        
        return recommendations
    
    def _pattern_to_dict(self, pattern: UsagePattern) -> Dict[str, Any]:
        """Convert UsagePattern to dictionary"""
        return {
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "confidence": pattern.confidence,
            "trend": pattern.trend,
            "impact_score": pattern.impact_score,
            "insights": pattern.insights,
            "recommendations": pattern.recommendations
        }
    
    def _generate_trend_summary(self, period_data: List[Dict[str, Any]], trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of trends"""
        if not period_data:
            return {}
        
        total_cost = sum(data["cost"] for data in period_data)
        total_requests = sum(data["requests"] for data in period_data)
        
        return {
            "total_cost": total_cost,
            "total_requests": total_requests,
            "avg_cost_per_period": total_cost / len(period_data),
            "avg_requests_per_period": total_requests / len(period_data),
            "cost_trend": trends.get("cost_trend", "unknown"),
            "request_trend": trends.get("request_trend", "unknown"),
            "trend_confidence": trends.get("confidence", 0)
        }
    
    # Additional helper methods would continue here...
    # For brevity, implementing the key ones
    
    def _analyze_cost_breakdown(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze cost breakdown by various dimensions"""
        total_cost = sum(record.total_cost for record in usage_records)
        
        # By model
        model_costs = defaultdict(float)
        for record in usage_records:
            if record.model_used:
                model_costs[record.model_used] += record.total_cost
        
        # By day of week
        daily_costs = defaultdict(float)
        for record in usage_records:
            day_name = record.created_at.strftime("%A")
            daily_costs[day_name] += record.total_cost
        
        return {
            "total_cost": total_cost,
            "by_model": dict(model_costs),
            "by_day_of_week": dict(daily_costs),
            "cost_distribution": {
                "min": min(record.total_cost for record in usage_records),
                "max": max(record.total_cost for record in usage_records),
                "median": sorted([record.total_cost for record in usage_records])[len(usage_records)//2]
            }
        }
    
    def _analyze_cost_trends(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze cost trends over time"""
        # Group by day
        daily_costs = defaultdict(float)
        for record in usage_records:
            day_key = record.created_at.date().isoformat()
            daily_costs[day_key] += record.total_cost
        
        if len(daily_costs) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate trend
        costs = list(daily_costs.values())
        if len(costs) >= 2:
            # Simple slope calculation
            n = len(costs)
            sum_x = sum(range(n))
            sum_y = sum(costs)
            sum_xy = sum(i * costs[i] for i in range(n))
            sum_x2 = sum(i * i for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            if slope > 0.01:
                trend = "increasing"
            elif slope < -0.01:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
            slope = 0
        
        return {
            "trend": trend,
            "slope": slope,
            "daily_costs": dict(daily_costs)
        }
    
    def _analyze_model_efficiency(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze model efficiency metrics"""
        model_metrics = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "success_rate": 0, "success_count": 0
        })
        
        for record in usage_records:
            if record.model_used:
                model = record.model_used
                model_metrics[model]["requests"] += 1
                model_metrics[model]["cost"] += record.total_cost
                model_metrics[model]["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
                if record.success:
                    model_metrics[model]["success_count"] += 1
        
        # Calculate efficiency metrics
        for model, metrics in model_metrics.items():
            metrics["success_rate"] = metrics["success_count"] / metrics["requests"]
            metrics["cost_per_token"] = metrics["cost"] / max(1, metrics["tokens"])
            metrics["cost_per_request"] = metrics["cost"] / metrics["requests"]
        
        return dict(model_metrics)
    
    def _detect_cost_anomalies(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Detect cost anomalies in usage data"""
        if len(usage_records) < 10:
            return []
        
        costs = [record.total_cost for record in usage_records]
        avg_cost = sum(costs) / len(costs)
        std_dev = statistics.stdev(costs)
        
        anomalies = []
        for i, record in enumerate(usage_records):
            if abs(record.total_cost - avg_cost) > 2 * std_dev:
                anomalies.append({
                    "index": i,
                    "date": record.created_at.isoformat(),
                    "cost": record.total_cost,
                    "anomaly_type": "high_cost" if record.total_cost > avg_cost else "low_cost",
                    "deviation": abs(record.total_cost - avg_cost) / std_dev
                })
        
        return anomalies
    
    def _identify_cost_optimization(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities"""
        opportunities = []
        
        # Check for expensive models with low success rates
        model_success_rates = defaultdict(lambda: {"success": 0, "total": 0, "cost": 0})
        
        for record in usage_records:
            if record.model_used:
                model = record.model_used
                model_success_rates[model]["total"] += 1
                model_success_rates[model]["cost"] += record.total_cost
                if record.success:
                    model_success_rates[model]["success"] += 1
        
        for model, data in model_success_rates.items():
            if data["total"] > 0:
                success_rate = data["success"] / data["total"]
                avg_cost = data["cost"] / data["total"]
                
                if success_rate < 0.8 and avg_cost > 0.05:  # Low success, high cost
                    opportunities.append({
                        "type": "model_replacement",
                        "description": f"Consider replacing {model} - low success rate ({success_rate:.2f}) with high cost",
                        "potential_savings": "20-40%",
                        "affected_requests": data["total"]
                    })
        
        return opportunities
    
    def _predict_future_costs(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Predict future costs based on historical data"""
        if len(usage_records) < 5:
            return {"prediction": "insufficient_data"}
        
        # Simple linear regression for cost prediction
        daily_costs = defaultdict(float)
        for record in usage_records:
            day_key = record.created_at.date().isoformat()
            daily_costs[day_key] += record.total_cost
        
        costs = list(daily_costs.values())
        if len(costs) < 2:
            return {"prediction": "insufficient_data"}
        
        # Calculate trend
        n = len(costs)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(costs)
        sum_xy = sum(x[i] * costs[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict next 7 days
        future_predictions = []
        for i in range(1, 8):
            future_day = n + i
            predicted_cost = slope * future_day + intercept
            future_predictions.append(max(0, predicted_cost))  # Cost can't be negative
        
        return {
            "trend_slope": slope,
            "avg_daily_cost": sum(costs) / len(costs),
            "next_7_days_total": sum(future_predictions),
            "confidence": min(0.8, len(costs) / 30),  # Higher confidence with more data
            "daily_predictions": future_predictions
        }
    
    def _analyze_cost_distribution(self, usage_records: List[CreditUsageRecord]) -> Dict[str, Any]:
        """Analyze cost distribution patterns"""
        costs = [record.total_cost for record in usage_records]
        costs.sort()
        
        n = len(costs)
        if n == 0:
            return {}
        
        # Calculate percentiles
        percentiles = {
            "p10": costs[int(n * 0.1)],
            "p25": costs[int(n * 0.25)],
            "p50": costs[int(n * 0.5)],
            "p75": costs[int(n * 0.75)],
            "p90": costs[int(n * 0.9)],
            "p99": costs[int(n * 0.99)]
        }
        
        return {
            "percentiles": percentiles,
            "quartile_coefficient": (percentiles["p75"] - percentiles["p25"]) / (percentiles["p75"] + percentiles["p25"]) if percentiles["p75"] + percentiles["p25"] > 0 else 0,
            "cost_concentration": {
                "top_10_percent_requests": costs[int(n * 0.9):],
                "percentage_of_total_cost": sum(costs[int(n * 0.9):]) / sum(costs) * 100 if sum(costs) > 0 else 0
            }
        }
    
    def _get_top_models(self, usage_records: List[CreditUsageRecord]) -> List[Dict[str, Any]]:
        """Get top models by usage"""
        model_stats = defaultdict(lambda: {
            "requests": 0, "cost": 0, "tokens": 0, "success_rate": 0, "success_count": 0
        })
        
        for record in usage_records:
            if record.model_used:
                model = record.model_used
                stats = model_stats[model]
                stats["requests"] += 1
                stats["cost"] += record.total_cost
                stats["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
                if record.success:
                    stats["success_count"] += 1
        
        # Calculate success rates and sort
        for model, stats in model_stats.items():
            stats["success_rate"] = stats["success_count"] / stats["requests"] if stats["requests"] > 0 else 0
            stats["avg_cost_per_request"] = stats["cost"] / stats["requests"]
        
        # Sort by cost and return top 5
        top_models = sorted(
            model_stats.items(),
            key=lambda x: x[1]["cost"],
            reverse=True
        )[:5]
        
        return [
            {
                "model": model,
                **stats
            }
            for model, stats in top_models
        ]