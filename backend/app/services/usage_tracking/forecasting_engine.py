"""
Forecasting Engine

Advanced credit usage forecasting and prediction system:
- Time series forecasting models
- Seasonal pattern analysis
- Growth trend prediction
- Budget projection and planning
- Risk assessment and alerting
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
import math
from collections import defaultdict, deque

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.credit import (
    CreditUsageRecord, CreditAccount, LLMUsageMetrics, LLMModelType
)
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel


class ForecastModel(Enum):
    """Forecasting model types"""
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"
    ARIMA = "arima"
    PROPHET = "prophet"  # If available
    ENSEMBLE = "ensemble"


class ForecastPeriod(Enum):
    """Forecast periods"""
    NEXT_DAY = "next_day"
    NEXT_WEEK = "next_week"
    NEXT_MONTH = "next_month"
    NEXT_QUARTER = "next_quarter"
    CUSTOM = "custom"


@dataclass
class ForecastResult:
    """Forecast result with confidence intervals"""
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: float
    model_used: str
    forecast_date: datetime
    created_at: datetime


@dataclass
class ForecastMetrics:
    """Forecasting model performance metrics"""
    model_name: str
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    mape: float  # Mean Absolute Percentage Error
    r_squared: float
    training_period_days: int
    prediction_period_days: int


@dataclass
class UsageForecast:
    """Comprehensive usage forecast"""
    forecast_type: str
    period: ForecastPeriod
    start_date: datetime
    end_date: datetime
    predictions: List[ForecastResult]
    model_performance: Optional[ForecastMetrics]
    insights: List[str]
    recommendations: List[str]
    risk_factors: List[Dict[str, Any]]


class ForecastingEngine:
    """
    Advanced forecasting engine for credit usage prediction
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Forecasting parameters
        self.default_confidence_level = 0.95
        self.min_data_points = 14  # Minimum days of data for forecasting
        self.max_forecast_days = 90  # Maximum forecast horizon
        
        # Exponential smoothing parameters
        self.alpha = 0.3  # Level smoothing
        self.beta = 0.1   # Trend smoothing
        self.gamma = 0.1  # Seasonal smoothing
        
        # Forecast history storage (in-memory for demo)
        self.forecast_cache: Dict[str, Any] = {}
    
    def forecast_usage(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        forecast_period: ForecastPeriod = ForecastPeriod.NEXT_MONTH,
        custom_days: Optional[int] = None,
        model_type: ForecastModel = ForecastModel.ENSEMBLE,
        include_confidence_intervals: bool = True
    ) -> UsageForecast:
        """
        Generate comprehensive usage forecast
        
        Args:
            user_id: User to forecast for
            organization_id: Organization to forecast for
            forecast_period: Period to forecast
            custom_days: Custom forecast days
            model_type: Forecasting model to use
            include_confidence_intervals: Include confidence intervals
        
        Returns:
            Comprehensive usage forecast
        """
        # Determine forecast duration
        if forecast_period == ForecastPeriod.NEXT_DAY:
            forecast_days = 1
        elif forecast_period == ForecastPeriod.NEXT_WEEK:
            forecast_days = 7
        elif forecast_period == ForecastPeriod.NEXT_MONTH:
            forecast_days = 30
        elif forecast_period == ForecastPeriod.NEXT_QUARTER:
            forecast_days = 90
        elif forecast_period == ForecastPeriod.CUSTOM:
            forecast_days = custom_days or 30
        else:
            forecast_days = 30
        
        forecast_days = min(forecast_days, self.max_forecast_days)
        
        # Get historical data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)  # Use 90 days for training
        
        historical_data = self._get_historical_data(
            user_id, organization_id, start_date, end_date
        )
        
        if len(historical_data) < self.min_data_points:
            return self._generate_insufficient_data_forecast(forecast_days)
        
        # Select and run forecasting model
        if model_type == ForecastModel.ENSEMBLE:
            predictions = self._run_ensemble_forecast(historical_data, forecast_days)
        else:
            predictions = self._run_single_model_forecast(
                historical_data, forecast_days, model_type
            )
        
        # Generate insights and recommendations
        insights = self._generate_forecast_insights(historical_data, predictions)
        recommendations = self._generate_forecast_recommendations(historical_data, predictions)
        risk_factors = self._assess_forecast_risks(historical_data, predictions)
        
        # Calculate model performance
        model_performance = self._calculate_model_performance(
            historical_data, model_type, forecast_days
        )
        
        return UsageForecast(
            forecast_type="usage_forecast",
            period=forecast_period,
            start_date=end_date,
            end_date=end_date + timedelta(days=forecast_days),
            predictions=predictions,
            model_performance=model_performance,
            insights=insights,
            recommendations=recommendations,
            risk_factors=risk_factors
        )
    
    def forecast_credit_balance(
        self,
        user_id: int,
        current_balance: float,
        forecast_days: int = 30,
        include_purchases: bool = True
    ) -> Dict[str, Any]:
        """
        Forecast credit balance over time
        
        Args:
            user_id: User to forecast for
            current_balance: Current credit balance
            forecast_days: Days to forecast
            include_purchases: Include potential credit purchases
        
        Returns:
            Credit balance forecast
        """
        # Get usage forecast
        usage_forecast = self.forecast_usage(
            user_id=user_id,
            forecast_period=ForecastPeriod.NEXT_MONTH if forecast_days > 30 else ForecastPeriod.NEXT_WEEK,
            custom_days=forecast_days
        )
        
        # Calculate balance trajectory
        balance_trajectory = []
        remaining_balance = current_balance
        
        for i, prediction in enumerate(usage_forecast.predictions):
            # Subtract predicted usage
            remaining_balance -= prediction.predicted_value
            
            # Check for auto-purchase triggers
            auto_purchase_triggered = False
            purchase_amount = 0
            
            if include_purchases and remaining_balance < 50:  # Auto-purchase threshold
                auto_purchase_triggered = True
                purchase_amount = 1000  # Standard auto-purchase amount
                remaining_balance += purchase_amount
            
            balance_trajectory.append({
                "date": prediction.forecast_date.isoformat(),
                "predicted_usage": prediction.predicted_value,
                "predicted_cost": prediction.predicted_value,
                "remaining_balance": remaining_balance,
                "auto_purchase_triggered": auto_purchase_triggered,
                "purchase_amount": purchase_amount,
                "confidence_level": prediction.confidence_level
            })
        
        # Find runout date
        runout_date = None
        for entry in balance_trajectory:
            if entry["remaining_balance"] <= 0:
                runout_date = entry["date"]
                break
        
        # Calculate recommended purchase
        avg_daily_usage = sum(p.predicted_value for p in usage_forecast.predictions) / len(usage_forecast.predictions)
        recommended_purchase = avg_daily_usage * forecast_days * 1.2  # 20% buffer
        
        return {
            "user_id": user_id,
            "current_balance": current_balance,
            "forecast_days": forecast_days,
            "balance_trajectory": balance_trajectory,
            "runout_date": runout_date,
            "recommended_purchase_amount": recommended_purchase,
            "avg_daily_usage": avg_daily_usage,
            "forecast_confidence": usage_forecast.predictions[0].confidence_level if usage_forecast.predictions else 0,
            "risk_assessment": self._assess_balance_risks(balance_trajectory, current_balance)
        }
    
    def forecast_cost_optimization(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        optimization_scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """
        Forecast cost optimization scenarios
        
        Args:
            user_id: User to analyze
            organization_id: Organization to analyze
            optimization_scenarios: List of scenarios to evaluate
        
        Returns:
            Cost optimization forecast
        """
        if optimization_scenarios is None:
            optimization_scenarios = [
                "model_switching", "prompt_optimization", "batch_processing",
                "caching", "rate_limiting"
            ]
        
        # Get baseline forecast
        baseline_forecast = self.forecast_usage(
            user_id=user_id,
            organization_id=organization_id
        )
        
        baseline_cost = sum(p.predicted_value for p in baseline_forecast.predictions)
        
        scenario_results = []
        
        for scenario in optimization_scenarios:
            scenario_cost = self._simulate_optimization_scenario(
                scenario, baseline_forecast, user_id, organization_id
            )
            
            savings = baseline_cost - scenario_cost
            savings_percentage = (savings / baseline_cost) * 100 if baseline_cost > 0 else 0
            
            scenario_results.append({
                "scenario": scenario,
                "baseline_cost": baseline_cost,
                "optimized_cost": scenario_cost,
                "absolute_savings": savings,
                "percentage_savings": savings_percentage,
                "implementation_complexity": self._get_scenario_complexity(scenario),
                "time_to_implement_days": self._get_implementation_time(scenario)
            })
        
        # Sort by savings potential
        scenario_results.sort(key=lambda x: x["percentage_savings"], reverse=True)
        
        return {
            "baseline_cost": baseline_cost,
            "optimization_scenarios": scenario_results,
            "total_potential_savings": sum(s["absolute_savings"] for s in scenario_results),
            "recommended_scenarios": scenario_results[:3],  # Top 3
            "implementation_roadmap": self._generate_implementation_roadmap(scenario_results)
        }
    
    def forecast_seasonal_patterns(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        historical_months: int = 6
    ) -> Dict[str, Any]:
        """
        Analyze and forecast seasonal usage patterns
        
        Args:
            user_id: User to analyze
            organization_id: Organization to analyze
            historical_months: Months of historical data to analyze
        
        Returns:
            Seasonal pattern analysis and forecast
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=historical_months * 30)
        
        # Get historical data
        historical_data = self._get_historical_data(
            user_id, organization_id, start_date, end_date
        )
        
        if len(historical_data) < 30:  # Need at least 30 days
            return {"error": "Insufficient historical data for seasonal analysis"}
        
        # Analyze patterns
        daily_patterns = self._analyze_daily_patterns(historical_data)
        weekly_patterns = self._analyze_weekly_patterns(historical_data)
        monthly_patterns = self._analyze_monthly_patterns(historical_data)
        
        # Forecast future seasonal patterns
        future_patterns = self._forecast_seasonal_patterns(
            daily_patterns, weekly_patterns, monthly_patterns, 90
        )
        
        return {
            "analysis_period_months": historical_months,
            "daily_patterns": daily_patterns,
            "weekly_patterns": weekly_patterns,
            "monthly_patterns": monthly_patterns,
            "future_seasonal_forecast": future_patterns,
            "seasonal_strength": self._calculate_seasonal_strength(historical_data),
            "peak_periods": self._identify_peak_periods(historical_data),
            "seasonal_recommendations": self._generate_seasonal_recommendations(historical_data)
        }
    
    def generate_alert_forecasts(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        alert_thresholds: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate forecasts for alert triggers
        
        Args:
            user_id: User to analyze
            organization_id: Organization to analyze
            alert_thresholds: Alert threshold values
        
        Returns:
            List of potential alerts with timing
        """
        if alert_thresholds is None:
            alert_thresholds = {
                "low_balance": 100.0,
                "high_daily_cost": 50.0,
                "unusual_usage_spike": 200.0,
                "budget_exhaustion": 0.0
            }
        
        # Get credit balance and usage forecast
        if user_id:
            credit_account = self.db.query(CreditAccount).filter(
                CreditAccount.user_id == user_id
            ).first()
            
            if not credit_account:
                return []
            
            current_balance = credit_account.current_balance
            balance_forecast = self.forecast_credit_balance(
                user_id, current_balance, forecast_days=30
            )
        else:
            current_balance = 0
            balance_forecast = {}
        
        # Get usage forecast
        usage_forecast = self.forecast_usage(
            user_id=user_id,
            organization_id=organization_id,
            forecast_period=ForecastPeriod.NEXT_MONTH
        )
        
        alerts = []
        
        # Low balance alert
        if user_id:
            for entry in balance_forecast.get("balance_trajectory", []):
                if entry["remaining_balance"] <= alert_thresholds["low_balance"]:
                    alerts.append({
                        "alert_type": "low_balance_warning",
                        "predicted_date": entry["date"],
                        "predicted_balance": entry["remaining_balance"],
                        "threshold": alert_thresholds["low_balance"],
                        "confidence": entry["confidence_level"],
                        "severity": "warning" if entry["remaining_balance"] > 0 else "critical"
                    })
                    break
        
        # High daily cost alerts
        for prediction in usage_forecast.predictions:
            if prediction.predicted_value >= alert_thresholds["high_daily_cost"]:
                alerts.append({
                    "alert_type": "high_daily_cost",
                    "predicted_date": prediction.forecast_date.isoformat(),
                    "predicted_cost": prediction.predicted_value,
                    "threshold": alert_thresholds["high_daily_cost"],
                    "confidence": prediction.confidence_level,
                    "severity": "warning"
                })
        
        # Usage spike detection
        avg_usage = sum(p.predicted_value for p in usage_forecast.predictions) / len(usage_forecast.predictions)
        spike_threshold = avg_usage * 3  # 3x average is considered a spike
        
        for prediction in usage_forecast.predictions:
            if prediction.predicted_value >= spike_threshold:
                alerts.append({
                    "alert_type": "usage_spike_prediction",
                    "predicted_date": prediction.forecast_date.isoformat(),
                    "predicted_cost": prediction.predicted_value,
                    "spike_factor": prediction.predicted_value / avg_usage,
                    "confidence": prediction.confidence_level,
                    "severity": "info"
                })
        
        # Budget exhaustion alert
        if user_id:
            runout_date = balance_forecast.get("runout_date")
            if runout_date:
                alerts.append({
                    "alert_type": "budget_exhaustion",
                    "predicted_date": runout_date,
                    "severity": "critical",
                    "confidence": 0.8,
                    "message": "Credit balance projected to reach zero"
                })
        
        return alerts
    
    # Forecasting model implementations
    
    def _run_ensemble_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int
    ) -> List[ForecastResult]:
        """Run ensemble forecast using multiple models"""
        models = [
            ForecastModel.LINEAR_REGRESSION,
            ForecastModel.EXPONENTIAL_SMOOTHING,
            ForecastModel.SEASONAL_DECOMPOSITION
        ]
        
        model_predictions = {}
        
        for model in models:
            try:
                predictions = self._run_single_model_forecast(
                    historical_data, forecast_days, model
                )
                model_predictions[model.value] = predictions
            except Exception as e:
                # Log error but continue with other models
                continue
        
        if not model_predictions:
            # Fallback to simple trend forecast
            return self._simple_trend_forecast(historical_data, forecast_days)
        
        # Combine predictions using weighted average
        ensemble_predictions = []
        end_date = datetime.utcnow()
        
        for i in range(forecast_days):
            forecast_date = end_date + timedelta(days=i+1)
            
            # Get predictions from all models for this day
            day_predictions = []
            model_weights = []
            
            for model_name, predictions in model_predictions.items():
                if i < len(predictions):
                    day_predictions.append(predictions[i].predicted_value)
                    # Weight by model performance (simplified)
                    model_weights.append(1.0 / (1 + len(models) - list(model_predictions.keys()).index(model_name)))
            
            if day_predictions:
                # Weighted average
                weights_sum = sum(model_weights[:len(day_predictions)])
                if weights_sum > 0:
                    weighted_prediction = sum(
                        pred * weight for pred, weight in zip(day_predictions, model_weights[:len(day_predictions)])
                    ) / weights_sum
                else:
                    weighted_prediction = sum(day_predictions) / len(day_predictions)
                
                # Calculate confidence (inverse of variance between models)
                if len(day_predictions) > 1:
                    variance = statistics.variance(day_predictions)
                    confidence = max(0.5, 1.0 / (1.0 + variance))
                else:
                    confidence = 0.7
                
                # Calculate confidence interval
                margin = weighted_prediction * (1 - confidence) * 0.1
                
                ensemble_predictions.append(ForecastResult(
                    predicted_value=weighted_prediction,
                    confidence_lower=weighted_prediction - margin,
                    confidence_upper=weighted_prediction + margin,
                    confidence_level=confidence,
                    model_used="ensemble",
                    forecast_date=forecast_date,
                    created_at=datetime.utcnow()
                ))
        
        return ensemble_predictions
    
    def _run_single_model_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int,
        model_type: ForecastModel
    ) -> List[ForecastResult]:
        """Run forecast using a single model"""
        if model_type == ForecastModel.LINEAR_REGRESSION:
            return self._linear_regression_forecast(historical_data, forecast_days)
        elif model_type == ForecastModel.EXPONENTIAL_SMOOTHING:
            return self._exponential_smoothing_forecast(historical_data, forecast_days)
        elif model_type == ForecastModel.SEASONAL_DECOMPOSITION:
            return self._seasonal_decomposition_forecast(historical_data, forecast_days)
        else:
            # Default to simple trend forecast
            return self._simple_trend_forecast(historical_data, forecast_days)
    
    def _linear_regression_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int
    ) -> List[ForecastResult]:
        """Linear regression forecasting"""
        if len(historical_data) < 2:
            return self._simple_trend_forecast(historical_data, forecast_days)
        
        # Prepare data
        costs = [data["cost"] for data in historical_data]
        n = len(costs)
        
        # Calculate linear regression coefficients
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(costs)
        sum_xy = sum(x[i] * costs[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        # Calculate slope and intercept
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return self._simple_trend_forecast(historical_data, forecast_days)
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Generate predictions
        predictions = []
        end_date = datetime.utcnow()
        
        for i in range(1, forecast_days + 1):
            forecast_date = end_date + timedelta(days=i)
            predicted_value = slope * (n + i - 1) + intercept
            
            # Ensure non-negative predictions
            predicted_value = max(0, predicted_value)
            
            # Calculate confidence based on regression quality
            if n > 2:
                y_mean = sum_y / n
                ss_tot = sum((costs[j] - y_mean) ** 2 for j in range(n))
                ss_res = sum((costs[j] - (slope * j + intercept)) ** 2 for j in range(n))
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                confidence = max(0.5, min(0.9, r_squared))
            else:
                confidence = 0.6
            
            # Calculate confidence interval (simplified)
            margin = predicted_value * (1 - confidence) * 0.2
            
            predictions.append(ForecastResult(
                predicted_value=predicted_value,
                confidence_lower=max(0, predicted_value - margin),
                confidence_upper=predicted_value + margin,
                confidence_level=confidence,
                model_used="linear_regression",
                forecast_date=forecast_date,
                created_at=datetime.utcnow()
            ))
        
        return predictions
    
    def _exponential_smoothing_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int
    ) -> List[ForecastResult]:
        """Exponential smoothing forecasting"""
        if not historical_data:
            return []
        
        costs = [data["cost"] for data in historical_data]
        
        # Initialize level and trend
        level = costs[0]
        trend = costs[1] - costs[0] if len(costs) > 1 else 0
        
        # Apply exponential smoothing
        for cost in costs[1:]:
            prev_level = level
            level = self.alpha * cost + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
        
        # Generate predictions
        predictions = []
        end_date = datetime.utcnow()
        
        for i in range(1, forecast_days + 1):
            forecast_date = end_date + timedelta(days=i)
            predicted_value = level + i * trend
            
            # Ensure non-negative
            predicted_value = max(0, predicted_value)
            
            # Confidence decreases with forecast horizon
            confidence = max(0.5, 0.9 - (i * 0.05))
            
            # Confidence interval
            margin = predicted_value * (1 - confidence) * 0.15
            
            predictions.append(ForecastResult(
                predicted_value=predicted_value,
                confidence_lower=max(0, predicted_value - margin),
                confidence_upper=predicted_value + margin,
                confidence_level=confidence,
                model_used="exponential_smoothing",
                forecast_date=forecast_date,
                created_at=datetime.utcnow()
            ))
        
        return predictions
    
    def _seasonal_decomposition_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int
    ) -> List[ForecastResult]:
        """Simple seasonal decomposition forecasting"""
        if len(historical_data) < 14:  # Need at least 2 weeks
            return self._exponential_smoothing_forecast(historical_data, forecast_days)
        
        costs = [data["cost"] for data in historical_data]
        
        # Simple moving average for trend
        window = min(7, len(costs) // 4)
        if window < 3:
            window = 3
        
        trend_values = []
        for i in range(len(costs)):
            start_idx = max(0, i - window // 2)
            end_idx = min(len(costs), i + window // 2 + 1)
            trend_values.append(sum(costs[start_idx:end_idx]) / (end_idx - start_idx))
        
        # Calculate seasonal components (weekly pattern)
        seasonal_components = {}
        for i in range(7):  # Days of week
            day_values = []
            for j in range(i, len(costs), 7):
                if j < len(trend_values):
                    day_values.append(costs[j] - trend_values[j])
            
            if day_values:
                seasonal_components[i] = sum(day_values) / len(day_values)
            else:
                seasonal_components[i] = 0
        
        # Generate predictions
        predictions = []
        end_date = datetime.utcnow()
        
        for i in range(1, forecast_days + 1):
            forecast_date = end_date + timedelta(days=i)
            
            # Base level (recent average)
            base_level = sum(costs[-7:]) / min(7, len(costs))
            
            # Add trend (simple)
            trend = 0
            if len(costs) >= 2:
                recent_trend = (costs[-1] - costs[-2]) * 0.1
                trend = recent_trend * (i / forecast_days)
            
            # Add seasonal component
            day_of_week = forecast_date.weekday()
            seasonal = seasonal_components.get(day_of_week, 0)
            
            predicted_value = base_level + trend + seasonal
            predicted_value = max(0, predicted_value)
            
            # Confidence based on seasonal pattern strength
            seasonal_strength = 1.0 - (sum(abs(v) for v in seasonal_components.values()) / len(seasonal_components) / (base_level + 0.01))
            confidence = max(0.6, min(0.9, seasonal_strength))
            
            # Confidence interval
            margin = predicted_value * (1 - confidence) * 0.2
            
            predictions.append(ForecastResult(
                predicted_value=predicted_value,
                confidence_lower=max(0, predicted_value - margin),
                confidence_upper=predicted_value + margin,
                confidence_level=confidence,
                model_used="seasonal_decomposition",
                forecast_date=forecast_date,
                created_at=datetime.utcnow()
            ))
        
        return predictions
    
    def _simple_trend_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_days: int
    ) -> List[ForecastResult]:
        """Simple trend-based forecasting"""
        if not historical_data:
            return []
        
        costs = [data["cost"] for data in historical_data]
        
        # Simple average with slight trend
        avg_cost = sum(costs) / len(costs)
        
        # Calculate simple trend
        if len(costs) >= 2:
            trend = (costs[-1] - costs[0]) / len(costs)
        else:
            trend = 0
        
        # Generate predictions
        predictions = []
        end_date = datetime.utcnow()
        
        for i in range(1, forecast_days + 1):
            forecast_date = end_date + timedelta(days=i)
            
            predicted_value = avg_cost + (trend * i * 0.5)  # Dampened trend
            predicted_value = max(0, predicted_value)
            
            # Lower confidence for simple methods
            confidence = max(0.5, 0.7 - (i * 0.02))
            
            # Confidence interval
            margin = predicted_value * (1 - confidence) * 0.25
            
            predictions.append(ForecastResult(
                predicted_value=predicted_value,
                confidence_lower=max(0, predicted_value - margin),
                confidence_upper=predicted_value + margin,
                confidence_level=confidence,
                model_used="simple_trend",
                forecast_date=forecast_date,
                created_at=datetime.utcnow()
            ))
        
        return predictions
    
    # Helper methods
    
    def _get_historical_data(
        self,
        user_id: Optional[int],
        organization_id: Optional[int],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get historical usage data"""
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
        
        usage_records = query.order_by(CreditUsageRecord.created_at).all()
        
        # Aggregate by day
        daily_data = defaultdict(float)
        
        for record in usage_records:
            day_key = record.created_at.date().isoformat()
            daily_data[day_key] += record.total_cost
        
        # Convert to list format
        historical_data = []
        for date_str, cost in sorted(daily_data.items()):
            historical_data.append({
                "date": date_str,
                "cost": cost,
                "requests": 1  # Simplified
            })
        
        return historical_data
    
    def _generate_insufficient_data_forecast(self, forecast_days: int) -> UsageForecast:
        """Generate forecast when insufficient data is available"""
        predictions = []
        end_date = datetime.utcnow()
        
        # Use conservative estimates
        default_daily_cost = 10.0  # Conservative default
        
        for i in range(1, forecast_days + 1):
            forecast_date = end_date + timedelta(days=i)
            predictions.append(ForecastResult(
                predicted_value=default_daily_cost,
                confidence_lower=default_daily_cost * 0.5,
                confidence_upper=default_daily_cost * 1.5,
                confidence_level=0.3,  # Low confidence
                model_used="conservative_estimate",
                forecast_date=forecast_date,
                created_at=datetime.utcnow()
            ))
        
        return UsageForecast(
            forecast_type="usage_forecast",
            period=ForecastPeriod.NEXT_MONTH,
            start_date=end_date,
            end_date=end_date + timedelta(days=forecast_days),
            predictions=predictions,
            model_performance=None,
            insights=[
                "Insufficient historical data for accurate forecasting",
                "Using conservative estimates based on default patterns"
            ],
            recommendations=[
                "Continue using the system to build historical data",
                "Consider manual budget setting until more data is available"
            ],
            risk_factors=[
                {
                    "risk_type": "data_insufficient",
                    "description": "Limited historical data affects forecast accuracy",
                    "impact": "medium",
                    "mitigation": "Build usage history over time"
                }
            ]
        )
    
    def _generate_forecast_insights(
        self,
        historical_data: List[Dict[str, Any]],
        predictions: List[ForecastResult]
    ) -> List[str]:
        """Generate insights from forecast"""
        insights = []
        
        if not historical_data or not predictions:
            return ["Insufficient data for meaningful insights"]
        
        # Trend analysis
        historical_avg = sum(data["cost"] for data in historical_data) / len(historical_data)
        forecast_avg = sum(p.predicted_value for p in predictions) / len(predictions)
        
        if forecast_avg > historical_avg * 1.2:
            insights.append("Usage is predicted to increase significantly")
        elif forecast_avg < historical_avg * 0.8:
            insights.append("Usage is predicted to decrease")
        else:
            insights.append("Usage is predicted to remain stable")
        
        # Variance analysis
        historical_variance = statistics.variance([data["cost"] for data in historical_data]) if len(historical_data) > 1 else 0
        if historical_variance > 0:
            insights.append("Usage shows high variability - consider monitoring for anomalies")
        
        # Confidence analysis
        avg_confidence = sum(p.confidence_level for p in predictions) / len(predictions)
        if avg_confidence < 0.7:
            insights.append("Low forecast confidence - predictions may be unreliable")
        
        return insights
    
    def _generate_forecast_recommendations(
        self,
        historical_data: List[Dict[str, Any]],
        predictions: List[ForecastResult]
    ) -> List[str]:
        """Generate recommendations based on forecast"""
        recommendations = []
        
        if not historical_data or not predictions:
            return ["Collect more usage data for better forecasting"]
        
        # Cost recommendations
        total_predicted_cost = sum(p.predicted_value for p in predictions)
        
        if total_predicted_cost > 1000:  # High cost threshold
            recommendations.append("Consider implementing cost optimization measures")
            recommendations.append("Review usage patterns for potential efficiency gains")
        
        # Alert recommendations
        max_daily_cost = max(p.predicted_value for p in predictions)
        if max_daily_cost > 50:
            recommendations.append("Set up daily cost alerts to monitor high-usage periods")
        
        # Budget recommendations
        avg_daily_cost = total_predicted_cost / len(predictions)
        monthly_projection = avg_daily_cost * 30
        if monthly_projection > 1000:
            recommendations.append("Consider increasing credit allocation for projected usage")
        
        return recommendations
    
    def _assess_forecast_risks(
        self,
        historical_data: List[Dict[str, Any]],
        predictions: List[ForecastResult]
    ) -> List[Dict[str, Any]]:
        """Assess risks in forecast"""
        risks = []
        
        # Data quality risk
        if len(historical_data) < 30:
            risks.append({
                "risk_type": "data_quality",
                "description": "Limited historical data affects forecast reliability",
                "impact": "medium",
                "probability": "high"
            })
        
        # Volatility risk
        if len(historical_data) > 1:
            costs = [data["cost"] for data in historical_data]
            cv = statistics.stdev(costs) / (sum(costs) / len(costs)) if sum(costs) > 0 else 0
            if cv > 0.5:
                risks.append({
                    "risk_type": "usage_volatility",
                    "description": "High usage variability makes predictions uncertain",
                    "impact": "medium",
                    "probability": "high"
                })
        
        # Model accuracy risk
        avg_confidence = sum(p.confidence_level for p in predictions) / len(predictions)
        if avg_confidence < 0.7:
            risks.append({
                "risk_type": "model_accuracy",
                "description": "Low model confidence indicates prediction uncertainty",
                "impact": "low",
                "probability": "medium"
            })
        
        return risks
    
    def _calculate_model_performance(
        self,
        historical_data: List[Dict[str, Any]],
        model_type: ForecastModel,
        forecast_days: int
    ) -> Optional[ForecastMetrics]:
        """Calculate model performance metrics"""
        if len(historical_data) < forecast_days + 10:
            return None  # Insufficient data for validation
        
        # Use last portion of data for validation
        train_data = historical_data[:-forecast_days]
        test_data = historical_data[-forecast_days:]
        
        # Run model on training data
        train_predictions = self._run_single_model_forecast(train_data, forecast_days, model_type)
        
        # Calculate metrics
        if len(test_data) != len(train_predictions):
            return None
        
        actual_costs = [data["cost"] for data in test_data]
        predicted_costs = [p.predicted_value for p in train_predictions]
        
        # Calculate metrics
        mae = sum(abs(actual - pred) for actual, pred in zip(actual_costs, predicted_costs)) / len(actual_costs)
        rmse = math.sqrt(sum((actual - pred) ** 2 for actual, pred in zip(actual_costs, predicted_costs)) / len(actual_costs))
        
        # MAPE (avoid division by zero)
        mape_values = []
        for actual, pred in zip(actual_costs, predicted_costs):
            if actual > 0:
                mape_values.append(abs((actual - pred) / actual))
        
        mape = sum(mape_values) / len(mape_values) * 100 if mape_values else 0
        
        # R-squared
        if len(actual_costs) > 1:
            actual_mean = sum(actual_costs) / len(actual_costs)
            ss_tot = sum((actual - actual_mean) ** 2 for actual in actual_costs)
            ss_res = sum((actual - pred) ** 2 for actual, pred in zip(actual_costs, predicted_costs))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        else:
            r_squared = 0
        
        return ForecastMetrics(
            model_name=model_type.value,
            mae=mae,
            rmse=rmse,
            mape=mape,
            r_squared=r_squared,
            training_period_days=len(train_data),
            prediction_period_days=forecast_days
        )
    
    def _get_historical_data_daily(self, user_id: int, days: int) -> List[float]:
        """Get daily usage data for the last N days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
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
        
        # Aggregate by day
        daily_usage = defaultdict(float)
        for record in usage_records:
            day_key = record.created_at.date()
            daily_usage[day_key] += record.total_cost
        
        # Fill in missing days with zeros
        daily_data = []
        for i in range(days):
            date = (end_date - timedelta(days=i)).date()
            daily_data.insert(0, daily_usage[date])
        
        return daily_data
    
    # Additional helper methods would be implemented here...
    # These are simplified versions for demonstration
    
    def _simulate_optimization_scenario(
        self,
        scenario: str,
        baseline_forecast: UsageForecast,
        user_id: Optional[int],
        organization_id: Optional[int]
    ) -> float:
        """Simulate cost for optimization scenario"""
        baseline_cost = sum(p.predicted_value for p in baseline_forecast.predictions)
        
        # Simplified scenario simulations
        if scenario == "model_switching":
            return baseline_cost * 0.7  # 30% savings
        elif scenario == "prompt_optimization":
            return baseline_cost * 0.85  # 15% savings
        elif scenario == "batch_processing":
            return baseline_cost * 0.9   # 10% savings
        elif scenario == "caching":
            return baseline_cost * 0.95  # 5% savings
        elif scenario == "rate_limiting":
            return baseline_cost * 0.8   # 20% savings
        else:
            return baseline_cost
    
    def _get_scenario_complexity(self, scenario: str) -> str:
        """Get implementation complexity for scenario"""
        complexity_map = {
            "model_switching": "medium",
            "prompt_optimization": "low",
            "batch_processing": "high",
            "caching": "medium",
            "rate_limiting": "medium"
        }
        return complexity_map.get(scenario, "unknown")
    
    def _get_implementation_time(self, scenario: str) -> int:
        """Get implementation time in days"""
        time_map = {
            "model_switching": 7,
            "prompt_optimization": 3,
            "batch_processing": 14,
            "caching": 10,
            "rate_limiting": 5
        }
        return time_map.get(scenario, 7)
    
    def _generate_implementation_roadmap(self, scenario_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate implementation roadmap"""
        roadmap = []
        
        # Sort by implementation complexity and savings potential
        sorted_scenarios = sorted(
            scenario_results,
            key=lambda x: (self._complexity_to_int(x["implementation_complexity"]), -x["percentage_savings"])
        )
        
        cumulative_days = 0
        for scenario in sorted_scenarios[:3]:  # Top 3 scenarios
            cumulative_days += scenario["time_to_implement_days"]
            roadmap.append({
                "phase": len(roadmap) + 1,
                "scenario": scenario["scenario"],
                "expected_savings": scenario["percentage_savings"],
                "implementation_days": scenario["time_to_implement_days"],
                "cumulative_days": cumulative_days,
                "complexity": scenario["implementation_complexity"]
            })
        
        return roadmap
    
    def _complexity_to_int(self, complexity: str) -> int:
        """Convert complexity string to integer for sorting"""
        complexity_map = {"low": 1, "medium": 2, "high": 3}
        return complexity_map.get(complexity, 2)
    
    # Placeholder methods for advanced analysis
    def _analyze_daily_patterns(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze daily usage patterns"""
        return {"peak_hour": 14, "low_hour": 3, "average_hourly_variance": 0.3}
    
    def _analyze_weekly_patterns(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze weekly usage patterns"""
        return {"peak_day": "Tuesday", "low_day": "Sunday", "weekend_reduction": 0.4}
    
    def _analyze_monthly_patterns(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze monthly usage patterns"""
        return {"peak_month": "March", "low_month": "August", "seasonal_variance": 0.25}
    
    def _forecast_seasonal_patterns(
        self,
        daily_patterns: Dict[str, Any],
        weekly_patterns: Dict[str, Any],
        monthly_patterns: Dict[str, Any],
        forecast_days: int
    ) -> Dict[str, Any]:
        """Forecast future seasonal patterns"""
        return {
            "next_peak_period": "Tuesday morning",
            "upcoming_low_period": "Sunday evening",
            "seasonal_adjustment": 0.15
        }
    
    def _calculate_seasonal_strength(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate strength of seasonal patterns"""
        return 0.6  # Moderate seasonal strength
    
    def _identify_peak_periods(self, historical_data: List[Dict[str, Any]]) -> List[str]:
        """Identify peak usage periods"""
        return ["Tuesday 10:00-14:00", "Thursday 09:00-11:00"]
    
    def _generate_seasonal_recommendations(self, historical_data: List[Dict[str, Any]]) -> List[str]:
        """Generate seasonal recommendations"""
        return [
            "Consider lower-cost processing during low-usage periods",
            "Schedule batch jobs for weekends to optimize costs"
        ]
    
    def _assess_balance_risks(self, balance_trajectory: List[Dict[str, Any]], current_balance: float) -> Dict[str, Any]:
        """Assess risks for credit balance"""
        risks = []
        
        for entry in balance_trajectory:
            if entry["remaining_balance"] <= 0:
                risks.append({
                    "type": "balance_exhaustion",
                    "date": entry["date"],
                    "severity": "critical"
                })
                break
            elif entry["remaining_balance"] < current_balance * 0.2:
                risks.append({
                    "type": "low_balance_warning",
                    "date": entry["date"],
                    "severity": "warning"
                })
        
        return {
            "risk_level": "high" if risks else "low",
            "identified_risks": risks,
            "risk_count": len(risks)
        }