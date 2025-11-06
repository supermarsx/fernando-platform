"""
Usage Analytics Service

Provides usage analytics, forecasting, and anomaly detection
for predictive insights and fraud prevention.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging
import statistics
from collections import defaultdict

from app.models.usage import (
    UsageMetric, UsageAggregation, UsageForecast, UsageAnomaly,
    UsageQuota
)

logger = logging.getLogger(__name__)


class UsageAnalyticsService:
    """
    Service for usage analytics, forecasting, and trend analysis
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_forecast(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        forecast_horizon_days: int = 30,
        model_type: str = "linear_regression"
    ) -> UsageForecast:
        """
        Generate usage forecast using historical data
        
        Args:
            user_id: User ID
            subscription_id: Subscription ID
            metric_type: Type of metric to forecast
            forecast_horizon_days: Days to forecast ahead
            model_type: Forecasting model to use
        
        Returns:
            UsageForecast instance
        """
        try:
            # Get historical data (last 90 days)
            lookback_days = 90
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get daily aggregations
            aggregations = self.db.query(UsageAggregation).filter(
                and_(
                    UsageAggregation.user_id == user_id,
                    UsageAggregation.metric_type == metric_type,
                    UsageAggregation.aggregation_type == "daily",
                    UsageAggregation.aggregation_date >= start_date,
                    UsageAggregation.aggregation_date <= end_date
                )
            ).order_by(UsageAggregation.aggregation_date).all()
            
            if not aggregations or len(aggregations) < 7:
                logger.warning(f"Insufficient data for forecasting. Need at least 7 days, got {len(aggregations)}")
                return None
            
            # Extract values and dates
            dates = [a.aggregation_date for a in aggregations]
            values = [a.total_value for a in aggregations]
            
            # Apply forecasting model
            if model_type == "linear_regression":
                predicted_value, confidence_lower, confidence_upper, accuracy = self._linear_forecast(
                    values, forecast_horizon_days
                )
            elif model_type == "moving_average":
                predicted_value, confidence_lower, confidence_upper, accuracy = self._moving_average_forecast(
                    values, forecast_horizon_days
                )
            elif model_type == "exponential_smoothing":
                predicted_value, confidence_lower, confidence_upper, accuracy = self._exponential_smoothing_forecast(
                    values, forecast_horizon_days
                )
            else:
                # Default to linear regression
                predicted_value, confidence_lower, confidence_upper, accuracy = self._linear_forecast(
                    values, forecast_horizon_days
                )
            
            # Check if forecast predicts quota exceedance
            quota = self.db.query(UsageQuota).filter(
                and_(
                    UsageQuota.user_id == user_id,
                    UsageQuota.subscription_id == subscription_id,
                    UsageQuota.metric_type == metric_type,
                    UsageQuota.is_active == True
                )
            ).first()
            
            will_exceed_quota = False
            expected_overage = 0
            estimated_overage_cost = 0
            
            if quota:
                # Get current usage in this period
                current_usage = quota.current_usage
                
                # Estimate end-of-period usage
                days_remaining = (quota.period_end - datetime.utcnow()).days
                if days_remaining > 0:
                    daily_average = current_usage / ((datetime.utcnow() - quota.period_start).days or 1)
                    estimated_end_usage = current_usage + (daily_average * days_remaining)
                    
                    if estimated_end_usage > quota.quota_limit:
                        will_exceed_quota = True
                        expected_overage = estimated_end_usage - quota.quota_limit
                        estimated_overage_cost = expected_overage * (quota.overage_rate or 0)
            
            # Create forecast record
            forecast_date = end_date + timedelta(days=forecast_horizon_days)
            
            forecast = UsageForecast(
                user_id=user_id,
                subscription_id=subscription_id,
                metric_type=metric_type,
                forecast_date=forecast_date,
                forecast_horizon_days=forecast_horizon_days,
                predicted_value=predicted_value,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                confidence_level=0.95,
                model_type=model_type,
                model_accuracy=accuracy,
                training_data_points=len(values),
                training_period_start=start_date,
                training_period_end=end_date,
                will_exceed_quota=will_exceed_quota,
                expected_overage=expected_overage,
                estimated_overage_cost=estimated_overage_cost
            )
            
            self.db.add(forecast)
            self.db.commit()
            self.db.refresh(forecast)
            
            logger.info(
                f"Generated forecast for user {user_id}: "
                f"predicted {predicted_value:.2f} in {forecast_horizon_days} days"
            )
            
            return forecast
            
        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            self.db.rollback()
            raise
    
    def _linear_forecast(
        self,
        values: List[float],
        horizon: int
    ) -> tuple:
        """Simple linear regression forecast"""
        n = len(values)
        if n < 2:
            return values[-1], values[-1] * 0.9, values[-1] * 1.1, 0.5
        
        # Calculate linear regression
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        intercept = y_mean - slope * x_mean
        
        # Predict future value
        future_x = n + horizon - 1
        predicted_value = slope * future_x + intercept
        
        # Calculate confidence interval (simplified)
        residuals = [values[i] - (slope * x[i] + intercept) for i in range(n)]
        std_dev = statistics.stdev(residuals) if len(residuals) > 1 else abs(predicted_value * 0.1)
        
        confidence_lower = max(0, predicted_value - 1.96 * std_dev)
        confidence_upper = predicted_value + 1.96 * std_dev
        
        # Calculate R-squared
        ss_res = sum(r ** 2 for r in residuals)
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        accuracy = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.5
        
        return predicted_value, confidence_lower, confidence_upper, max(0, min(1, accuracy))
    
    def _moving_average_forecast(
        self,
        values: List[float],
        horizon: int,
        window: int = 7
    ) -> tuple:
        """Moving average forecast"""
        if len(values) < window:
            window = len(values)
        
        recent_values = values[-window:]
        predicted_value = sum(recent_values) / len(recent_values)
        
        # Confidence interval based on variance
        std_dev = statistics.stdev(recent_values) if len(recent_values) > 1 else predicted_value * 0.1
        confidence_lower = max(0, predicted_value - 1.96 * std_dev)
        confidence_upper = predicted_value + 1.96 * std_dev
        
        # Accuracy based on recent stability
        if len(values) > window:
            predictions = []
            for i in range(window, len(values)):
                pred = sum(values[i-window:i]) / window
                predictions.append(pred)
            
            actual = values[window:]
            errors = [(actual[i] - predictions[i]) ** 2 for i in range(len(predictions))]
            mse = sum(errors) / len(errors) if errors else 0
            accuracy = max(0, 1 - (mse / (statistics.variance(values) or 1)))
        else:
            accuracy = 0.5
        
        return predicted_value, confidence_lower, confidence_upper, accuracy
    
    def _exponential_smoothing_forecast(
        self,
        values: List[float],
        horizon: int,
        alpha: float = 0.3
    ) -> tuple:
        """Exponential smoothing forecast"""
        if not values:
            return 0, 0, 0, 0
        
        # Apply exponential smoothing
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[i-1])
        
        predicted_value = smoothed[-1]
        
        # Confidence interval
        errors = [values[i] - smoothed[i] for i in range(len(values))]
        std_dev = statistics.stdev(errors) if len(errors) > 1 else predicted_value * 0.1
        confidence_lower = max(0, predicted_value - 1.96 * std_dev)
        confidence_upper = predicted_value + 1.96 * std_dev
        
        # Accuracy
        mse = sum(e ** 2 for e in errors) / len(errors)
        variance = statistics.variance(values) if len(values) > 1 else 1
        accuracy = max(0, 1 - (mse / variance)) if variance > 0 else 0.5
        
        return predicted_value, confidence_lower, confidence_upper, accuracy
    
    async def detect_anomalies(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        detection_method: str = "statistical"
    ) -> List[UsageAnomaly]:
        """
        Detect anomalous usage patterns
        
        Args:
            user_id: User ID
            subscription_id: Subscription ID
            metric_type: Type of metric to analyze
            detection_method: Method to use for detection
        
        Returns:
            List of detected anomalies
        """
        try:
            # Get recent usage data (last 30 days)
            lookback_days = 30
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get hourly metrics for fine-grained analysis
            metrics = self.db.query(UsageMetric).filter(
                and_(
                    UsageMetric.user_id == user_id,
                    UsageMetric.metric_type == metric_type,
                    UsageMetric.timestamp >= start_date,
                    UsageMetric.timestamp <= end_date
                )
            ).order_by(UsageMetric.timestamp).all()
            
            if len(metrics) < 10:
                logger.warning(f"Insufficient data for anomaly detection: {len(metrics)} metrics")
                return []
            
            anomalies = []
            
            if detection_method == "statistical":
                anomalies = await self._statistical_anomaly_detection(
                    user_id, subscription_id, metric_type, metrics
                )
            elif detection_method == "velocity":
                anomalies = await self._velocity_anomaly_detection(
                    user_id, subscription_id, metric_type, metrics
                )
            elif detection_method == "pattern":
                anomalies = await self._pattern_anomaly_detection(
                    user_id, subscription_id, metric_type, metrics
                )
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []
    
    async def _statistical_anomaly_detection(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        metrics: List[UsageMetric]
    ) -> List[UsageAnomaly]:
        """Detect anomalies using statistical methods (Z-score)"""
        values = [m.metric_value for m in metrics]
        
        if len(values) < 3:
            return []
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        if std_dev == 0:
            return []
        
        anomalies = []
        threshold = 3.0  # 3 standard deviations
        
        for metric in metrics:
            z_score = abs((metric.metric_value - mean) / std_dev)
            
            if z_score > threshold:
                # This is an anomaly
                confidence_score = min(1.0, z_score / (threshold * 2))
                deviation_percentage = ((metric.metric_value - mean) / mean * 100) if mean > 0 else 0
                
                severity = "critical" if z_score > 4 else "high" if z_score > 3.5 else "medium"
                
                anomaly = UsageAnomaly(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    anomaly_type="statistical_outlier",
                    severity=severity,
                    confidence_score=confidence_score,
                    detection_method="statistical",
                    metric_type=metric_type,
                    observed_value=metric.metric_value,
                    expected_value=mean,
                    deviation_percentage=deviation_percentage,
                    pattern_description=f"Value {metric.metric_value:.2f} is {z_score:.2f} standard deviations from mean {mean:.2f}",
                    time_window_start=metric.timestamp,
                    time_window_end=metric.timestamp,
                    risk_score=int(min(100, z_score * 20)),
                    is_fraud_suspect=z_score > 4,
                    requires_review=z_score > 3.5,
                    status="detected"
                )
                
                self.db.add(anomaly)
                anomalies.append(anomaly)
        
        if anomalies:
            self.db.commit()
            logger.info(f"Detected {len(anomalies)} statistical anomalies for user {user_id}")
        
        return anomalies
    
    async def _velocity_anomaly_detection(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        metrics: List[UsageMetric]
    ) -> List[UsageAnomaly]:
        """Detect anomalies based on rapid changes (velocity)"""
        if len(metrics) < 2:
            return []
        
        anomalies = []
        
        # Group by hour
        hourly_usage = defaultdict(float)
        for metric in metrics:
            hour_key = metric.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_usage[hour_key] += metric.metric_value
        
        # Sort by time
        sorted_hours = sorted(hourly_usage.items())
        
        # Calculate hourly changes
        for i in range(1, len(sorted_hours)):
            prev_hour, prev_value = sorted_hours[i-1]
            curr_hour, curr_value = sorted_hours[i]
            
            if prev_value == 0:
                continue
            
            change_percentage = ((curr_value - prev_value) / prev_value * 100)
            
            # Flag rapid increases (>500% in one hour)
            if change_percentage > 500:
                confidence_score = min(1.0, change_percentage / 1000)
                
                anomaly = UsageAnomaly(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    anomaly_type="velocity_spike",
                    severity="high",
                    confidence_score=confidence_score,
                    detection_method="velocity",
                    metric_type=metric_type,
                    observed_value=curr_value,
                    expected_value=prev_value,
                    deviation_percentage=change_percentage,
                    pattern_description=f"Usage increased by {change_percentage:.1f}% in one hour (from {prev_value:.2f} to {curr_value:.2f})",
                    time_window_start=prev_hour,
                    time_window_end=curr_hour,
                    risk_score=int(min(100, change_percentage / 10)),
                    is_fraud_suspect=change_percentage > 1000,
                    requires_review=True,
                    status="detected"
                )
                
                self.db.add(anomaly)
                anomalies.append(anomaly)
        
        if anomalies:
            self.db.commit()
            logger.info(f"Detected {len(anomalies)} velocity anomalies for user {user_id}")
        
        return anomalies
    
    async def _pattern_anomaly_detection(
        self,
        user_id: int,
        subscription_id: int,
        metric_type: str,
        metrics: List[UsageMetric]
    ) -> List[UsageAnomaly]:
        """Detect anomalies based on unusual patterns"""
        # Implementation for pattern-based detection
        # This could include things like:
        # - Usage at unusual times (e.g., 3 AM for a business user)
        # - Consistent automated patterns (potential bot)
        # - Geographic anomalies (if we track that)
        
        # For now, return empty list (can be enhanced)
        return []
    
    def get_usage_trends(
        self,
        user_id: int,
        metric_type: str,
        days: int = 30
    ) -> Dict:
        """
        Get usage trends and statistics
        
        Returns:
            Dictionary with trend analysis
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily aggregations
        aggregations = self.db.query(UsageAggregation).filter(
            and_(
                UsageAggregation.user_id == user_id,
                UsageAggregation.metric_type == metric_type,
                UsageAggregation.aggregation_type == "daily",
                UsageAggregation.aggregation_date >= start_date,
                UsageAggregation.aggregation_date <= end_date
            )
        ).order_by(UsageAggregation.aggregation_date).all()
        
        if not aggregations:
            return {
                "metric_type": metric_type,
                "period_days": days,
                "data_points": 0,
                "trend": "no_data"
            }
        
        values = [a.total_value for a in aggregations]
        dates = [a.aggregation_date.isoformat() for a in aggregations]
        
        return {
            "metric_type": metric_type,
            "period_days": days,
            "data_points": len(values),
            "total": sum(values),
            "average": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "trend": aggregations[-1].trend if aggregations else "unknown",
            "change_percentage": aggregations[-1].change_percentage if aggregations else 0,
            "dates": dates,
            "values": values
        }
