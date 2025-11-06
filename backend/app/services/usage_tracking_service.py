"""
Usage Tracking Service

Provides real-time usage tracking, quota enforcement, and usage aggregation
for the Fernando platform.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from app.models.usage import (
    UsageMetric, UsageQuota, UsageAggregation, UsageAlert,
    UsageMetricType, UsageAlertType, UsageAlertStatus
)
from app.models.billing import Subscription
from app.models.license import License

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """
    Core service for tracking and managing resource usage
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def track_usage(
        self,
        user_id: int,
        metric_type: str,
        metric_value: float,
        subscription_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        operation: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        error_occurred: bool = False,
        error_code: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> UsageMetric:
        """
        Track a usage event in real-time
        
        Args:
            user_id: User performing the action
            metric_type: Type of metric (document_processing, api_calls, etc.)
            metric_value: Quantitative value (1 document, 100 API calls, etc.)
            subscription_id: Associated subscription
            resource_id: Reference to specific resource
            endpoint: API endpoint if applicable
            operation: Specific operation performed
            response_time_ms: Response time for performance tracking
            error_occurred: Whether an error occurred
            error_code: Error code if applicable
            metadata: Additional context
        
        Returns:
            Created UsageMetric instance
        """
        try:
            # Determine time window
            now = datetime.utcnow()
            window_start = now.replace(minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(hours=1)
            
            # Determine unit based on metric type
            unit = self._get_unit_for_metric(metric_type)
            
            # Create usage metric
            usage_metric = UsageMetric(
                user_id=user_id,
                subscription_id=subscription_id,
                metric_type=metric_type,
                metric_value=metric_value,
                unit=unit,
                timestamp=now,
                window_start=window_start,
                window_end=window_end,
                window_type="hourly",
                resource_id=resource_id,
                endpoint=endpoint,
                operation=operation,
                response_time_ms=response_time_ms,
                error_occurred=error_occurred,
                error_code=error_code,
                metadata=metadata or {}
            )
            
            self.db.add(usage_metric)
            self.db.commit()
            self.db.refresh(usage_metric)
            
            # Update quota in real-time
            await self._update_quota_usage(user_id, subscription_id, metric_type, metric_value)
            
            # Check for quota limits
            await self._check_quota_limits(user_id, subscription_id, metric_type)
            
            logger.info(
                f"Tracked usage for user {user_id}: {metric_type}={metric_value} {unit}"
            )
            
            return usage_metric
            
        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")
            self.db.rollback()
            raise
    
    async def _update_quota_usage(
        self,
        user_id: int,
        subscription_id: Optional[int],
        metric_type: str,
        metric_value: float
    ):
        """Update current usage in quota"""
        if not subscription_id:
            return
        
        # Find active quota for this metric
        quota = self.db.query(UsageQuota).filter(
            and_(
                UsageQuota.user_id == user_id,
                UsageQuota.subscription_id == subscription_id,
                UsageQuota.metric_type == metric_type,
                UsageQuota.is_active == True,
                UsageQuota.period_end > datetime.utcnow()
            )
        ).first()
        
        if quota:
            # Update usage
            quota.current_usage += metric_value
            
            # Calculate percentage
            if quota.quota_limit > 0:
                quota.usage_percentage = (quota.current_usage / quota.quota_limit) * 100
            
            # Check if exceeded
            if quota.current_usage > quota.quota_limit:
                quota.is_exceeded = True
                if not quota.exceeded_at:
                    quota.exceeded_at = datetime.utcnow()
                
                # Calculate overage
                quota.current_overage = quota.current_usage - quota.quota_limit
            
            quota.updated_at = datetime.utcnow()
            self.db.commit()
    
    async def _check_quota_limits(
        self,
        user_id: int,
        subscription_id: Optional[int],
        metric_type: str
    ):
        """Check if quota limits are reached and trigger alerts"""
        if not subscription_id:
            return
        
        quota = self.db.query(UsageQuota).filter(
            and_(
                UsageQuota.user_id == user_id,
                UsageQuota.subscription_id == subscription_id,
                UsageQuota.metric_type == metric_type,
                UsageQuota.is_active == True
            )
        ).first()
        
        if not quota:
            return
        
        percentage = quota.usage_percentage
        
        # Check thresholds and create alerts
        if percentage >= 100:
            await self._create_alert(
                user_id=user_id,
                subscription_id=subscription_id,
                quota_id=quota.id,
                alert_type=UsageAlertType.HARD_LIMIT_REACHED,
                severity="critical",
                title=f"{metric_type} Quota Limit Reached",
                message=f"You have reached 100% of your {metric_type} quota ({quota.current_usage}/{quota.quota_limit} {quota.unit})",
                metric_type=metric_type,
                current_value=quota.current_usage,
                threshold_value=quota.quota_limit,
                quota_percentage=percentage,
                action_taken="throttled" if not quota.allow_overage else "charged_overage"
            )
        elif percentage >= 90:
            await self._create_alert(
                user_id=user_id,
                subscription_id=subscription_id,
                quota_id=quota.id,
                alert_type=UsageAlertType.SOFT_LIMIT_REACHED,
                severity="high",
                title=f"{metric_type} Quota at 90%",
                message=f"You have used 90% of your {metric_type} quota ({quota.current_usage}/{quota.quota_limit} {quota.unit})",
                metric_type=metric_type,
                current_value=quota.current_usage,
                threshold_value=quota.quota_limit * 0.9,
                quota_percentage=percentage
            )
        elif percentage >= 80:
            await self._create_alert(
                user_id=user_id,
                subscription_id=subscription_id,
                quota_id=quota.id,
                alert_type=UsageAlertType.APPROACHING_LIMIT,
                severity="medium",
                title=f"{metric_type} Quota at 80%",
                message=f"You have used 80% of your {metric_type} quota ({quota.current_usage}/{quota.quota_limit} {quota.unit})",
                metric_type=metric_type,
                current_value=quota.current_usage,
                threshold_value=quota.quota_limit * 0.8,
                quota_percentage=percentage
            )
    
    async def _create_alert(
        self,
        user_id: int,
        subscription_id: int,
        quota_id: int,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        metric_type: str,
        current_value: float,
        threshold_value: float,
        quota_percentage: float,
        action_taken: Optional[str] = None
    ):
        """Create a usage alert"""
        # Check if similar alert already exists (prevent duplicates)
        existing_alert = self.db.query(UsageAlert).filter(
            and_(
                UsageAlert.user_id == user_id,
                UsageAlert.quota_id == quota_id,
                UsageAlert.alert_type == alert_type,
                UsageAlert.status == UsageAlertStatus.PENDING,
                UsageAlert.triggered_at > datetime.utcnow() - timedelta(hours=1)
            )
        ).first()
        
        if existing_alert:
            return  # Don't create duplicate alert
        
        alert = UsageAlert(
            user_id=user_id,
            subscription_id=subscription_id,
            quota_id=quota_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metric_type=metric_type,
            current_value=current_value,
            threshold_value=threshold_value,
            quota_percentage=quota_percentage,
            status=UsageAlertStatus.PENDING,
            action_taken=action_taken
        )
        
        self.db.add(alert)
        self.db.commit()
        
        logger.info(f"Created {severity} alert for user {user_id}: {title}")
    
    def check_quota_available(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        required_quantity: float = 1.0
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Check if user has available quota for a resource
        
        Returns:
            Tuple of (is_available, error_message, quota_info)
        """
        quota = self.db.query(UsageQuota).filter(
            and_(
                UsageQuota.user_id == user_id,
                UsageQuota.subscription_id == subscription_id,
                UsageQuota.metric_type == metric_type,
                UsageQuota.is_active == True,
                UsageQuota.period_end > datetime.utcnow()
            )
        ).first()
        
        if not quota:
            return False, "No active quota found for this metric", None
        
        available = quota.quota_limit - quota.current_usage
        
        quota_info = {
            "quota_limit": quota.quota_limit,
            "current_usage": quota.current_usage,
            "available": available,
            "usage_percentage": quota.usage_percentage,
            "allow_overage": quota.allow_overage,
            "overage_limit": quota.overage_limit,
            "overage_rate": quota.overage_rate
        }
        
        # Check if enough quota available
        if available >= required_quantity:
            return True, None, quota_info
        
        # Check if overage is allowed
        if quota.allow_overage:
            total_overage = quota.current_overage + (required_quantity - available)
            if quota.overage_limit and total_overage > quota.overage_limit:
                return False, f"Overage limit exceeded. Maximum overage: {quota.overage_limit} {quota.unit}", quota_info
            
            # Calculate overage cost
            overage_cost = (required_quantity - available) * quota.overage_rate
            quota_info["overage_cost"] = overage_cost
            quota_info["message"] = f"Quota exceeded. Overage charge: €{overage_cost:.2f}"
            
            return True, None, quota_info
        
        return False, f"Quota limit reached. Used {quota.current_usage}/{quota.quota_limit} {quota.unit}", quota_info
    
    def get_current_usage_summary(
        self,
        user_id: int,
        subscription_id: Optional[int] = None
    ) -> Dict:
        """Get current usage summary for a user"""
        quotas = self.db.query(UsageQuota).filter(
            UsageQuota.user_id == user_id,
            UsageQuota.is_active == True,
            UsageQuota.period_end > datetime.utcnow()
        )
        
        if subscription_id:
            quotas = quotas.filter(UsageQuota.subscription_id == subscription_id)
        
        quotas = quotas.all()
        
        summary = {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "quotas": [],
            "total_overage_cost": 0,
            "alerts_count": 0
        }
        
        for quota in quotas:
            quota_data = {
                "metric_type": quota.metric_type,
                "quota_limit": quota.quota_limit,
                "current_usage": quota.current_usage,
                "usage_percentage": quota.usage_percentage,
                "available": max(0, quota.quota_limit - quota.current_usage),
                "unit": quota.unit,
                "is_exceeded": quota.is_exceeded,
                "overage": quota.current_overage,
                "overage_cost": quota.current_overage * quota.overage_rate if quota.overage_rate else 0,
                "period_end": quota.period_end.isoformat(),
                "next_reset": quota.next_reset_at.isoformat() if quota.next_reset_at else None
            }
            
            summary["quotas"].append(quota_data)
            summary["total_overage_cost"] += quota_data["overage_cost"]
        
        # Count pending alerts
        alerts_count = self.db.query(func.count(UsageAlert.id)).filter(
            UsageAlert.user_id == user_id,
            UsageAlert.status == UsageAlertStatus.PENDING
        ).scalar()
        
        summary["alerts_count"] = alerts_count
        
        return summary
    
    async def aggregate_usage(
        self,
        user_id: int,
        metric_type: str,
        aggregation_type: str = "daily",
        date: Optional[datetime] = None
    ) -> UsageAggregation:
        """
        Aggregate usage data for a specific time period
        
        Args:
            user_id: User ID
            metric_type: Type of metric to aggregate
            aggregation_type: hourly, daily, weekly, monthly
            date: Date for the aggregation
        
        Returns:
            UsageAggregation instance
        """
        if not date:
            date = datetime.utcnow()
        
        # Determine time range based on aggregation type
        if aggregation_type == "hourly":
            start_time = date.replace(minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(hours=1)
        elif aggregation_type == "daily":
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        elif aggregation_type == "weekly":
            start_time = date - timedelta(days=date.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=7)
        elif aggregation_type == "monthly":
            start_time = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end_time = start_time.replace(year=date.year + 1, month=1)
            else:
                end_time = start_time.replace(month=date.month + 1)
        else:
            raise ValueError(f"Invalid aggregation type: {aggregation_type}")
        
        # Query usage metrics for the time range
        metrics = self.db.query(UsageMetric).filter(
            and_(
                UsageMetric.user_id == user_id,
                UsageMetric.metric_type == metric_type,
                UsageMetric.timestamp >= start_time,
                UsageMetric.timestamp < end_time
            )
        ).all()
        
        if not metrics:
            return None
        
        # Calculate aggregations
        values = [m.metric_value for m in metrics]
        total_value = sum(values)
        average_value = total_value / len(values) if values else 0
        min_value = min(values) if values else 0
        max_value = max(values) if values else 0
        count = len(values)
        
        # Get previous period for trend
        previous_agg = self.db.query(UsageAggregation).filter(
            and_(
                UsageAggregation.user_id == user_id,
                UsageAggregation.metric_type == metric_type,
                UsageAggregation.aggregation_type == aggregation_type,
                UsageAggregation.aggregation_date < start_time
            )
        ).order_by(UsageAggregation.aggregation_date.desc()).first()
        
        previous_value = previous_agg.total_value if previous_agg else 0
        change_percentage = ((total_value - previous_value) / previous_value * 100) if previous_value > 0 else 0
        
        # Determine trend
        if abs(change_percentage) < 5:
            trend = "stable"
        elif change_percentage > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Create or update aggregation
        existing_agg = self.db.query(UsageAggregation).filter(
            and_(
                UsageAggregation.user_id == user_id,
                UsageAggregation.metric_type == metric_type,
                UsageAggregation.aggregation_type == aggregation_type,
                UsageAggregation.aggregation_date == start_time
            )
        ).first()
        
        if existing_agg:
            existing_agg.total_value = total_value
            existing_agg.average_value = average_value
            existing_agg.min_value = min_value
            existing_agg.max_value = max_value
            existing_agg.count = count
            existing_agg.previous_period_value = previous_value
            existing_agg.change_percentage = change_percentage
            existing_agg.trend = trend
            aggregation = existing_agg
        else:
            aggregation = UsageAggregation(
                user_id=user_id,
                metric_type=metric_type,
                aggregation_type=aggregation_type,
                aggregation_date=start_time,
                total_value=total_value,
                average_value=average_value,
                min_value=min_value,
                max_value=max_value,
                count=count,
                unit=self._get_unit_for_metric(metric_type),
                previous_period_value=previous_value,
                change_percentage=change_percentage,
                trend=trend
            )
            self.db.add(aggregation)
        
        self.db.commit()
        self.db.refresh(aggregation)
        
        return aggregation
    
    def _get_unit_for_metric(self, metric_type: str) -> str:
        """Get the unit for a metric type"""
        units = {
            UsageMetricType.DOCUMENT_PROCESSING: "documents",
            UsageMetricType.DOCUMENT_PAGES: "pages",
            UsageMetricType.API_CALLS: "calls",
            UsageMetricType.STORAGE_USAGE: "GB",
            UsageMetricType.USER_SESSIONS: "sessions",
            UsageMetricType.BATCH_OPERATIONS: "batches",
            UsageMetricType.EXPORT_OPERATIONS: "exports",
            UsageMetricType.OCR_OPERATIONS: "operations",
            UsageMetricType.LLM_OPERATIONS: "operations",
            UsageMetricType.DATABASE_QUERIES: "queries",
            UsageMetricType.BANDWIDTH_USAGE: "GB"
        }
        return units.get(metric_type, "units")
    
    async def reset_quota(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: Optional[str] = None
    ):
        """Reset quota usage for a new billing period"""
        quotas = self.db.query(UsageQuota).filter(
            and_(
                UsageQuota.user_id == user_id,
                UsageQuota.subscription_id == subscription_id,
                UsageQuota.is_active == True
            )
        )
        
        if metric_type:
            quotas = quotas.filter(UsageQuota.metric_type == metric_type)
        
        for quota in quotas.all():
            quota.current_usage = 0
            quota.usage_percentage = 0
            quota.current_overage = 0
            quota.is_exceeded = False
            quota.exceeded_at = None
            quota.last_reset_at = datetime.utcnow()
            
            # Set next reset date
            if quota.reset_schedule == "monthly":
                quota.next_reset_at = datetime.utcnow() + timedelta(days=30)
            elif quota.reset_schedule == "quarterly":
                quota.next_reset_at = datetime.utcnow() + timedelta(days=90)
            elif quota.reset_schedule == "annually":
                quota.next_reset_at = datetime.utcnow() + timedelta(days=365)
            
            quota.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Reset quotas for user {user_id}, subscription {subscription_id}")
