"""
Credit Analytics Service

Usage forecasting and credit recommendations service.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import math
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text

from app.models.credits import (
    CreditBalance, CreditTransaction, CreditTransactionType, CreditAnalytics,
    LLMUsageRecord, LLMProvider
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.usage_tracker import UsageTracker
from app.services.credits.llm_pricing import LlmPricingService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CreditAnalyticsService:
    """
    Service for usage forecasting and credit recommendations
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.usage_tracker = UsageTracker(db)
        self.pricing_service = LlmPricingService(db)
    
    def generate_daily_forecast(self, user_id: int, days_ahead: int = 30,
                              organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate daily usage forecast for next N days
        """
        try:
            # Get historical usage data (last 90 days for better forecasting)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)
            
            # Get usage records
            query = self.db.query(LLMUsageRecord).filter(
                LLMUsageRecord.user_id == user_id,
                LLMUsageRecord.timestamp >= start_date,
                LLMUsageRecord.timestamp <= end_date,
                LLMUsageRecord.error_occurred == False
            )
            
            if organization_id:
                query = query.filter(LLMUsageRecord.organization_id == organization_id)
            
            usage_records = query.all()
            
            if not usage_records:
                return {
                    "forecast_days": days_ahead,
                    "total_predicted_credits": 0,
                    "daily_forecasts": [],
                    "confidence": 0,
                    "method": "insufficient_data"
                }
            
            # Group by date and calculate daily usage
            daily_usage = {}
            for record in usage_records:
                date_key = record.timestamp.date().isoformat()
                if date_key not in daily_usage:
                    daily_usage[date_key] = {"credits": 0, "requests": 0, "tokens": 0}
                
                daily_usage[date_key]["credits"] += record.total_cost_credits
                daily_usage[date_key]["requests"] += 1
                daily_usage[date_key]["tokens"] += record.total_tokens
            
            # Convert to sorted list
            sorted_days = sorted(daily_usage.items())
            
            # Calculate forecast using multiple methods
            forecast_data = self._calculate_forecast(sorted_days, days_ahead)
            
            # Generate daily predictions
            daily_forecasts = []
            for i in range(days_ahead):
                forecast_date = (datetime.utcnow() + timedelta(days=i+1)).date()
                predicted_credits = forecast_data["daily_predictions"][i]
                
                daily_forecasts.append({
                    "date": forecast_date.isoformat(),
                    "predicted_credits": round(predicted_credits, 2),
                    "predicted_requests": round(predicted_credits / 20),  # Estimate ~20 credits per request
                    "predicted_tokens": round(predicted_credits * 50)  # Estimate ~50 tokens per credit
                })
            
            total_predicted = sum(d["predicted_credits"] for d in daily_forecasts)
            
            return {
                "forecast_days": days_ahead,
                "total_predicted_credits": round(total_predicted, 2),
                "daily_forecasts": daily_forecasts,
                "confidence": forecast_data["confidence"],
                "method": forecast_data["method"],
                "historical_avg_daily": forecast_data["historical_avg"],
                "trend": forecast_data["trend"],
                "seasonality_detected": forecast_data["seasonality"]
            }
            
        except Exception as e:
            logger.error(f"Error generating forecast for user {user_id}: {e}")
            return {
                "forecast_days": days_ahead,
                "total_predicted_credits": 0,
                "daily_forecasts": [],
                "confidence": 0,
                "error": str(e)
            }
    
    def recommend_credit_topup(self, user_id: int, buffer_days: int = 7,
                             organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Recommend credit top-up amount based on usage patterns
        """
        try:
            # Get current balance
            balance = self.credit_manager.get_balance(user_id, organization_id)
            if not balance:
                return {"recommendation": 0, "reason": "No credit balance found"}
            
            # Generate forecast
            forecast = self.generate_daily_forecast(user_id, 30, organization_id)
            
            if not forecast["daily_forecasts"]:
                return {
                    "recommendation": 0,
                    "reason": "Insufficient usage data for recommendation"
                }
            
            # Calculate monthly forecast
            monthly_forecast = sum(d["predicted_credits"] for d in forecast["daily_forecasts"])
            
            # Add buffer
            buffer_credits = sum(d["predicted_credits"] for d in forecast["daily_forecasts"][:buffer_days])
            
            # Consider current balance
            available_credits = balance.available_credits
            reserved_credits = balance.reserved_credits
            
            # Calculate recommendation
            total_needed = monthly_forecast + buffer_credits
            current_coverage = available_credits + reserved_credits
            recommendation = max(0, total_needed - current_coverage)
            
            # Round to reasonable amounts
            if recommendation > 0:
                if recommendation < 1000:
                    recommendation = math.ceil(recommendation / 100) * 100
                elif recommendation < 10000:
                    recommendation = math.ceil(recommendation / 500) * 500
                else:
                    recommendation = math.ceil(recommendation / 1000) * 1000
            
            # Generate reasoning
            reasoning = []
            if monthly_forecast > 0:
                reasoning.append(f"Monthly forecast: {monthly_forecast:.0f} credits")
            if buffer_credits > 0:
                reasoning.append(f"{buffer_days}-day buffer: {buffer_credits:.0f} credits")
            if current_coverage < total_needed:
                reasoning.append(f"Current coverage insufficient by {total_needed - current_coverage:.0f} credits")
            
            return {
                "recommended_topup": recommendation,
                "reasoning": reasoning,
                "monthly_forecast": round(monthly_forecast, 2),
                "buffer_days": buffer_days,
                "buffer_credits": round(buffer_credits, 2),
                "current_balance": available_credits,
                "current_reserved": reserved_credits,
                "total_needed": round(total_needed, 2),
                "confidence": forecast["confidence"]
            }
            
        except Exception as e:
            logger.error(f"Error recommending credit topup for user {user_id}: {e}")
            return {
                "recommended_topup": 0,
                "error": str(e)
            }
    
    def analyze_credit_efficiency(self, user_id: int, days: int = 30,
                                organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze credit efficiency and provide optimization recommendations
        """
        try:
            # Get usage summary
            usage_summary = self.usage_tracker.get_usage_summary(user_id, days, organization_id)
            
            # Get top models
            top_models = self.usage_tracker.get_top_models(user_id, 10, days, organization_id)
            
            # Calculate efficiency metrics
            efficiency_score = self._calculate_efficiency_score(usage_summary)
            
            # Analyze model usage patterns
            model_analysis = self._analyze_model_usage(top_models)
            
            # Generate recommendations
            recommendations = self._generate_optimization_recommendations(
                usage_summary, top_models, efficiency_score
            )
            
            return {
                "analysis_period_days": days,
                "efficiency_score": efficiency_score,
                "efficiency_rating": self._get_efficiency_rating(efficiency_score),
                "metrics": {
                    "total_credits_used": usage_summary["total_credits_used"],
                    "total_requests": usage_summary["total_requests"],
                    "credits_per_request": usage_summary["average_cost_per_request"],
                    "tokens_per_credit": usage_summary["average_tokens_per_request"] / usage_summary["average_cost_per_request"] if usage_summary["average_cost_per_request"] > 0 else 0,
                    "model_diversity": len(usage_summary["model_breakdown"]),
                    "error_rate": usage_summary["error_rate"]
                },
                "model_analysis": model_analysis,
                "recommendations": recommendations,
                "cost_breakdown": self._analyze_cost_breakdown(usage_summary),
                "usage_patterns": self._analyze_usage_patterns(usage_summary)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing credit efficiency for user {user_id}: {e}")
            return {"error": str(e)}
    
    def _calculate_forecast(self, historical_data: List[Tuple[str, Dict]], 
                          days_ahead: int) -> Dict[str, Any]:
        """
        Calculate forecast using multiple methods and choose the best
        """
        if len(historical_data) < 7:
            # Not enough data for forecasting
            return {
                "daily_predictions": [0] * days_ahead,
                "confidence": 0,
                "method": "insufficient_data",
                "historical_avg": 0,
                "trend": 0,
                "seasonality": False
            }
        
        # Extract credit usage values
        credits_values = [data[1]["credits"] for data in historical_data]
        
        # Method 1: Moving Average
        recent_values = credits_values[-14:]  # Last 2 weeks
        moving_avg = sum(recent_values) / len(recent_values)
        
        # Method 2: Linear Trend
        trend = self._calculate_linear_trend(credits_values)
        
        # Method 3: Seasonal Adjustment (if enough data)
        seasonality_score = self._detect_seasonality(credits_values)
        
        # Combine methods based on data quality
        if len(credits_values) >= 30:
            method = "seasonal_trend"
            daily_predictions = []
            for i in range(days_ahead):
                base_value = moving_avg
                trend_adjustment = trend * (i + 1)
                seasonal_adjustment = seasonality_score * math.sin(2 * math.pi * (i + 1) / 7)  # Weekly seasonality
                predicted_value = max(0, base_value + trend_adjustment + seasonal_adjustment)
                daily_predictions.append(predicted_value)
            confidence = 0.8
        else:
            method = "moving_average"
            daily_predictions = [moving_avg] * days_ahead
            confidence = 0.6 if len(credits_values) >= 14 else 0.4
        
        return {
            "daily_predictions": daily_predictions,
            "confidence": confidence,
            "method": method,
            "historical_avg": moving_avg,
            "trend": trend,
            "seasonality": seasonality_score > 0.1
        }
    
    def _calculate_linear_trend(self, values: List[float]) -> float:
        """
        Calculate linear trend slope
        """
        if len(values) < 2:
            return 0
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _detect_seasonality(self, values: List[float], period: int = 7) -> float:
        """
        Detect seasonality in the data
        """
        if len(values) < period * 2:
            return 0
        
        # Simple autocorrelation method
        correlations = []
        for lag in range(1, min(8, len(values) // period)):
            if len(values) > lag:
                series1 = values[:-lag]
                series2 = values[lag:]
                if len(series1) > 0:
                    correlation = self._calculate_correlation(series1, series2)
                    correlations.append(abs(correlation))
        
        return max(correlations) if correlations else 0
    
    def _calculate_correlation(self, series1: List[float], series2: List[float]) -> float:
        """
        Calculate correlation between two series
        """
        if len(series1) != len(series2) or len(series1) == 0:
            return 0
        
        n = len(series1)
        mean1 = sum(series1) / n
        mean2 = sum(series2) / n
        
        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(series1, series2))
        sum_sq1 = sum((x - mean1) ** 2 for x in series1)
        sum_sq2 = sum((y - mean2) ** 2 for y in series2)
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        return numerator / denominator if denominator > 0 else 0
    
    def _calculate_efficiency_score(self, usage_summary: Dict[str, Any]) -> float:
        """
        Calculate overall efficiency score (0-100)
        """
        score = 100
        
        # Penalize high error rate
        error_penalty = min(usage_summary["error_rate"] * 2, 30)
        score -= error_penalty
        
        # Penalize very high cost per request (inefficient models)
        if usage_summary["average_cost_per_request"] > 100:
            score -= 20
        elif usage_summary["average_cost_per_request"] > 50:
            score -= 10
        
        # Reward model diversity (up to a point)
        model_count = len(usage_summary["model_breakdown"])
        if model_count >= 3 and model_count <= 10:
            score += 10
        elif model_count > 15:
            score -= 10  # Too much diversity can be inefficient
        
        # Reward consistent usage (no extreme spikes)
        daily_usage = usage_summary["daily_usage"]
        if daily_usage:
            daily_values = [d["credits"] for d in daily_usage if "credits" in d]
            if daily_values:
                avg_daily = sum(daily_values) / len(daily_values)
                max_daily = max(daily_values)
                if max_daily > avg_daily * 5:  # Very spikey usage
                    score -= 15
        
        return max(0, min(100, score))
    
    def _get_efficiency_rating(self, score: float) -> str:
        """
        Convert efficiency score to rating
        """
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Very Poor"
    
    def _analyze_model_usage(self, top_models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze model usage patterns
        """
        if not top_models:
            return {"message": "No model usage data available"}
        
        total_credits = sum(model["total_credits_used"] for model in top_models)
        
        # Identify dominant model
        dominant_model = top_models[0]
        dominant_percentage = (dominant_model["total_credits_used"] / total_credits * 100) if total_credits > 0 else 0
        
        # Analyze cost efficiency by model
        cost_efficient_models = []
        high_cost_models = []
        
        for model in top_models:
            avg_cost = model["average_cost_per_request"]
            if avg_cost < 10:
                cost_efficient_models.append(f"{model['full_model']} ({avg_cost:.1f} credits/request)")
            elif avg_cost > 50:
                high_cost_models.append(f"{model['full_model']} ({avg_cost:.1f} credits/request)")
        
        return {
            "total_models_used": len(top_models),
            "dominant_model": {
                "name": dominant_model["full_model"],
                "usage_percentage": round(dominant_percentage, 1),
                "total_credits": dominant_model["total_credits_used"]
            },
            "cost_efficient_models": cost_efficient_models[:3],
            "high_cost_models": high_cost_models[:3],
            "avg_cost_range": {
                "min": min(model["average_cost_per_request"] for model in top_models),
                "max": max(model["average_cost_per_request"] for model in top_models)
            }
        }
    
    def _generate_optimization_recommendations(self, usage_summary: Dict[str, Any],
                                             top_models: List[Dict[str, Any]],
                                             efficiency_score: float) -> List[str]:
        """
        Generate optimization recommendations
        """
        recommendations = []
        
        # Error rate recommendations
        if usage_summary["error_rate"] > 10:
            recommendations.append("High error rate detected. Check input format and model compatibility.")
        
        # Cost optimization recommendations
        if usage_summary["average_cost_per_request"] > 50:
            recommendations.append("Consider using more cost-effective models for routine tasks.")
        
        # Model diversity recommendations
        if len(top_models) == 1:
            recommendations.append("Explore different models for specialized tasks to improve efficiency.")
        elif len(top_models) > 10:
            recommendations.append("Consider standardizing on fewer models to reduce complexity.")
        
        # Usage pattern recommendations
        daily_usage = usage_summary.get("daily_usage", [])
        if daily_usage:
            credits_by_day = [d.get("credits", 0) for d in daily_usage if "credits" in d]
            if credits_by_day:
                avg_daily = sum(credits_by_day) / len(credits_by_day)
                if max(credits_by_day) > avg_daily * 5:
                    recommendations.append("Highly variable usage detected. Consider implementing usage quotas.")
        
        # Efficiency-based recommendations
        if efficiency_score < 60:
            recommendations.append("Overall efficiency is low. Review usage patterns and optimize model selection.")
        
        # Credit management recommendations
        if usage_summary["total_credits_used"] > 50000:
            recommendations.append("High credit usage. Consider implementing usage monitoring and alerts.")
        
        return recommendations
    
    def _analyze_cost_breakdown(self, usage_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze cost breakdown by provider and model
        """
        provider_breakdown = usage_summary.get("provider_breakdown", {})
        model_breakdown = usage_summary.get("model_breakdown", {})
        
        if not provider_breakdown or not model_breakdown:
            return {"message": "Insufficient data for cost breakdown analysis"}
        
        # Calculate provider percentages
        total_cost = sum(provider_data["credits"] for provider_data in provider_breakdown.values())
        
        provider_percentages = {}
        for provider, data in provider_breakdown.items():
            percentage = (data["credits"] / total_cost * 100) if total_cost > 0 else 0
            provider_percentages[provider] = {
                "percentage": round(percentage, 1),
                "credits": data["credits"],
                "requests": data["requests"]
            }
        
        # Identify most expensive model
        most_expensive_model = max(
            model_breakdown.items(),
            key=lambda x: x[1]["credits"] / x[1]["requests"] if x[1]["requests"] > 0 else 0
        )
        
        return {
            "total_cost": total_cost,
            "provider_distribution": provider_percentages,
            "most_expensive_model": {
                "name": most_expensive_model[0],
                "avg_cost_per_request": most_expensive_model[1]["credits"] / most_expensive_model[1]["requests"]
            },
            "cost_optimization_potential": self._estimate_optimization_potential(provider_breakdown)
        }
    
    def _estimate_optimization_potential(self, provider_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate potential cost optimization
        """
        total_cost = sum(data["credits"] for data in provider_breakdown.values())
        
        # Simple heuristic: if one provider dominates cost (>70%), suggest diversification
        max_provider_cost = max(data["credits"] for data in provider_breakdown.values())
        max_percentage = (max_provider_cost / total_cost * 100) if total_cost > 0 else 0
        
        potential_savings = 0
        if max_percentage > 70:
            # Assume 20% savings possible through optimization
            potential_savings = total_cost * 0.2
        
        return {
            "potential_monthly_savings": potential_savings,
            "optimization_opportunity": "high" if max_percentage > 70 else "low",
            "recommendation": "Diversify model usage" if max_percentage > 70 else "Current usage appears optimized"
        }
    
    def _analyze_usage_patterns(self, usage_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze usage patterns for insights
        """
        daily_usage = usage_summary.get("daily_usage", [])
        
        if not daily_usage:
            return {"message": "No usage pattern data available"}
        
        # Analyze usage patterns
        credits_by_day = [d.get("credits", 0) for d in daily_usage if "credits" in d]
        
        if not credits_by_day:
            return {"message": "No valid usage data"}
        
        avg_daily = sum(credits_by_day) / len(credits_by_day)
        max_daily = max(credits_by_day)
        min_daily = min(credits_by_day)
        
        # Calculate variance
        variance = sum((x - avg_daily) ** 2 for x in credits_by_day) / len(credits_by_day)
        std_dev = math.sqrt(variance)
        
        # Determine pattern type
        if std_dev / avg_daily < 0.3:
            pattern_type = "consistent"
        elif std_dev / avg_daily < 0.7:
            pattern_type = "variable"
        else:
            pattern_type = "highly_variable"
        
        return {
            "pattern_type": pattern_type,
            "average_daily_usage": avg_daily,
            "peak_daily_usage": max_daily,
            "low_daily_usage": min_daily,
            "usage_variance": std_dev,
            "consistency_score": max(0, 100 - (std_dev / avg_daily * 100)) if avg_daily > 0 else 0
        }
    
    def save_analytics_snapshot(self, user_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Save analytics snapshot to database for reporting
        """
        try:
            # Generate comprehensive analytics
            analytics_data = self.usage_tracker.get_usage_analytics(user_id, organization_id)
            forecast = self.generate_daily_forecast(user_id, 30, organization_id)
            recommendations = self.recommend_credit_topup(user_id, organization_id=organization_id)
            
            # Create analytics record
            now = datetime.utcnow()
            end_date = now
            start_date = now - timedelta(days=30)
            
            analytics = CreditAnalytics(
                user_id=user_id,
                organization_id=organization_id,
                analysis_type="monthly",
                analysis_date=now,
                period_start=start_date,
                period_end=end_date,
                total_credits_used=analytics_data["summary"]["last_30_days"]["total_credits_used"],
                total_credits_purchased=0,  # Would need to be calculated from purchase data
                net_credit_flow=analytics_data["summary"]["last_30_days"]["total_credits_used"],  # Negative flow for usage
                avg_daily_usage=analytics_data["summary"]["last_30_days"]["average_cost_per_request"],
                peak_daily_usage=max((d.get("credits", 0) for d in analytics_data["summary"]["last_30_days"]["daily_usage"]), default=0),
                usage_trend=forecast["trend_direction"],
                provider_usage=analytics_data["summary"]["last_30_days"]["provider_breakdown"],
                model_usage=analytics_data["summary"]["last_30_days"]["model_breakdown"],
                predicted_usage=forecast["total_predicted_credits"],
                confidence_level=forecast["confidence"],
                recommended_top_up=recommendations.get("recommended_topup", 0)
            )
            
            self.db.add(analytics)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving analytics snapshot for user {user_id}: {e}")
            self.db.rollback()
            return False


# Utility functions
def get_credit_analytics_service(db: Session = None) -> CreditAnalyticsService:
    """
    Get CreditAnalyticsService instance
    """
    if db is None:
        db = next(get_db())
    return CreditAnalyticsService(db)


def generate_forecast(user_id: int, days_ahead: int = 30, db: Session = None) -> Dict[str, Any]:
    """
    Quick function to generate usage forecast
    """
    service = get_credit_analytics_service(db)
    return service.generate_daily_forecast(user_id, days_ahead)


def recommend_topup(user_id: int, buffer_days: int = 7, db: Session = None) -> Dict[str, Any]:
    """
    Quick function to recommend credit top-up
    """
    service = get_credit_analytics_service(db)
    return service.recommend_credit_topup(user_id, buffer_days)