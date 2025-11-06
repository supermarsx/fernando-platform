"""
Purchase Analytics Service

Purchase pattern analysis and recommendations for credit purchases.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.credits import (
    CreditPurchaseTransaction, CreditPackage, CreditBalance, CreditTransaction,
    CreditTransactionType
)
from app.services.credits.credit_purchase.purchase_manager import CreditPurchaseManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class PurchaseAnalyticsService:
    """
    Service for analyzing purchase patterns and providing recommendations
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.purchase_manager = CreditPurchaseManager(db)
    
    def analyze_purchase_patterns(self, user_id: int, days: int = 90,
                                organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze user's purchase patterns
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get purchase history
        query = self.db.query(CreditPurchaseTransaction).filter(
            CreditPurchaseTransaction.user_id == user_id,
            CreditPurchaseTransaction.created_at >= start_date,
            CreditPurchaseTransaction.created_at <= end_date,
            CreditPurchaseTransaction.status == "completed"
        )
        
        if organization_id:
            query = query.filter(CreditPurchaseTransaction.organization_id == organization_id)
        
        purchases = query.order_by(CreditPurchaseTransaction.created_at.asc()).all()
        
        if not purchases:
            return {
                "period_days": days,
                "total_purchases": 0,
                "purchase_frequency": "none",
                "total_spent": 0,
                "total_credits_purchased": 0,
                "recommendations": ["No purchase history found. Consider starting with a starter package."],
                "insights": []
            }
        
        # Calculate basic metrics
        total_purchases = len(purchases)
        total_spent = sum(p.total_amount for p in purchases)
        total_credits_purchased = sum(p.total_credits for p in purchases)
        
        # Calculate purchase frequency
        if total_purchases == 0:
            frequency = "none"
        else:
            days_between_purchases = days / total_purchases
            if days_between_purchases <= 7:
                frequency = "weekly"
            elif days_between_purchases <= 30:
                frequency = "monthly"
            elif days_between_purchases <= 90:
                frequency = "quarterly"
            else:
                frequency = "irregular"
        
        # Calculate purchase amounts
        purchase_amounts = [p.total_amount for p in purchases]
        average_purchase = statistics.mean(purchase_amounts)
        median_purchase = statistics.median(purchase_amounts)
        
        # Calculate credits patterns
        credit_amounts = [p.total_credits for p in purchases]
        average_credits = statistics.mean(credit_amounts)
        
        # Analyze package preferences
        package_preferences = {}
        for purchase in purchases:
            package_name = purchase.package.name if purchase.package else "Unknown"
            if package_name not in package_preferences:
                package_preferences[package_name] = {
                    "count": 0,
                    "total_amount": 0,
                    "total_credits": 0
                }
            
            package_preferences[package_name]["count"] += 1
            package_preferences[package_name]["total_amount"] += purchase.total_amount
            package_preferences[package_name]["total_credits"] += purchase.total_credits
        
        # Identify primary package
        primary_package = max(package_preferences.items(), key=lambda x: x[1]["count"])
        
        # Calculate spending trends
        spending_trend = self._calculate_spending_trend(purchases)
        
        # Generate insights
        insights = self._generate_purchase_insights(
            purchases, frequency, total_spent, average_purchase, package_preferences
        )
        
        # Generate recommendations
        recommendations = self._generate_purchase_recommendations(
            purchases, frequency, average_purchase, total_credits_purchased
        )
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "summary": {
                "total_purchases": total_purchases,
                "total_spent": total_spent,
                "total_credits_purchased": total_credits_purchased,
                "average_purchase_value": average_purchase,
                "median_purchase_value": median_purchase,
                "average_credits_per_purchase": average_credits,
                "purchase_frequency": frequency,
                "primary_package": primary_package[0],
                "package_diversity": len(package_preferences)
            },
            "spending_analysis": {
                "trend": spending_trend,
                "spending_distribution": self._analyze_spending_distribution(purchase_amounts),
                "value_optimization": self._analyze_value_optimization(purchases)
            },
            "package_preferences": package_preferences,
            "temporal_patterns": self._analyze_temporal_patterns(purchases),
            "insights": insights,
            "recommendations": recommendations
        }
    
    def _calculate_spending_trend(self, purchases: List[CreditPurchaseTransaction]) -> Dict[str, Any]:
        """
        Calculate spending trend over time
        """
        if len(purchases) < 2:
            return {"trend": "insufficient_data", "change_percentage": 0}
        
        # Split purchases into first half and second half
        midpoint = len(purchases) // 2
        first_half = purchases[:midpoint]
        second_half = purchases[midpoint:]
        
        first_half_avg = sum(p.total_amount for p in first_half) / len(first_half)
        second_half_avg = sum(p.total_amount for p in second_half) / len(second_half)
        
        if first_half_avg == 0:
            change_percentage = 0
        else:
            change_percentage = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if change_percentage > 10:
            trend = "increasing"
        elif change_percentage < -10:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change_percentage": round(change_percentage, 2),
            "first_half_average": round(first_half_avg, 2),
            "second_half_average": round(second_half_avg, 2)
        }
    
    def _analyze_spending_distribution(self, purchase_amounts: List[float]) -> Dict[str, Any]:
        """
        Analyze distribution of spending amounts
        """
        if not purchase_amounts:
            return {"distribution": "no_data"}
        
        min_amount = min(purchase_amounts)
        max_amount = max(purchase_amounts)
        avg_amount = statistics.mean(purchase_amounts)
        
        # Define spending tiers
        small_purchases = [amount for amount in purchase_amounts if amount < avg_amount * 0.5]
        medium_purchases = [amount for amount in purchase_amounts if avg_amount * 0.5 <= amount <= avg_amount * 1.5]
        large_purchases = [amount for amount in purchase_amounts if amount > avg_amount * 1.5]
        
        return {
            "min_amount": min_amount,
            "max_amount": max_amount,
            "average_amount": avg_amount,
            "tier_distribution": {
                "small_purchases": {
                    "count": len(small_purchases),
                    "percentage": len(small_purchases) / len(purchase_amounts) * 100
                },
                "medium_purchases": {
                    "count": len(medium_purchases),
                    "percentage": len(medium_purchases) / len(purchase_amounts) * 100
                },
                "large_purchases": {
                    "count": len(large_purchases),
                    "percentage": len(large_purchases) / len(purchase_amounts) * 100
                }
            }
        }
    
    def _analyze_value_optimization(self, purchases: List[CreditPurchaseTransaction]) -> Dict[str, Any]:
        """
        Analyze value optimization in purchases
        """
        value_scores = []
        
        for purchase in purchases:
            if purchase.total_credits > 0:
                cost_per_credit = purchase.total_amount / purchase.total_credits
                value_score = 100 - (cost_per_credit * 10)  # Simple value scoring
                value_scores.append(max(0, min(100, value_score)))
        
        if not value_scores:
            return {"average_value_score": 0, "optimization_opportunities": []}
        
        avg_value_score = statistics.mean(value_scores)
        
        # Identify optimization opportunities
        opportunities = []
        
        low_value_purchases = [p for p, score in zip(purchases, value_scores) if score < 60]
        if low_value_purchases:
            opportunities.append("Some purchases had low value per credit. Consider bulk packages for better rates.")
        
        high_value_purchases = [p for p, score in zip(purchases, value_scores) if score > 80]
        if high_value_purchases:
            opportunities.append("Several high-value purchases detected. Consider similar packages for future needs.")
        
        return {
            "average_value_score": round(avg_value_score, 2),
            "optimization_opportunities": opportunities,
            "best_value_purchase": {
                "purchase_id": purchases[value_scores.index(max(value_scores))].purchase_id if value_scores else None,
                "value_score": max(value_scores) if value_scores else 0
            }
        }
    
    def _analyze_temporal_patterns(self, purchases: List[CreditPurchaseTransaction]) -> Dict[str, Any]:
        """
        Analyze temporal purchase patterns
        """
        if not purchases:
            return {"pattern": "no_data"}
        
        # Analyze by day of week
        day_of_week_counts = {}
        for purchase in purchases:
            day_name = purchase.created_at.strftime("%A")
            day_of_week_counts[day_name] = day_of_week_counts.get(day_name, 0) + 1
        
        # Analyze by hour of day
        hour_counts = {}
        for purchase in purchases:
            hour = purchase.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Identify patterns
        most_common_day = max(day_of_week_counts.items(), key=lambda x: x[1]) if day_of_week_counts else None
        most_common_hour = max(hour_counts.items(), key=lambda x: x[1]) if hour_counts else None
        
        return {
            "most_common_day": most_common_day[0] if most_common_day else None,
            "most_common_hour": most_common_hour[0] if most_common_hour else None,
            "day_distribution": day_of_week_counts,
            "hour_distribution": hour_counts,
            "pattern_summary": self._summarize_temporal_pattern(day_of_week_counts, hour_counts)
        }
    
    def _summarize_temporal_pattern(self, day_counts: Dict[str, int], hour_counts: Dict[int, int]) -> str:
        """
        Summarize temporal purchase patterns
        """
        if not day_counts and not hour_counts:
            return "No clear temporal pattern"
        
        patterns = []
        
        if day_counts:
            most_popular_day = max(day_counts.items(), key=lambda x: x[1])[0]
            patterns.append(f"Most purchases on {most_popular_day}")
        
        if hour_counts:
            working_hours_purchases = sum(count for hour, count in hour_counts.items() if 9 <= hour <= 17)
            total_purchases = sum(hour_counts.values())
            if working_hours_purchases / total_purchases > 0.6:
                patterns.append("Primarily during business hours")
        
        return "; ".join(patterns) if patterns else "Mixed temporal distribution"
    
    def _generate_purchase_insights(self, purchases: List[CreditPurchaseTransaction],
                                  frequency: str, total_spent: float, avg_purchase: float,
                                  package_preferences: Dict[str, Any]) -> List[str]:
        """
        Generate insights from purchase analysis
        """
        insights = []
        
        # Frequency insights
        if frequency == "weekly":
            insights.append("High purchase frequency indicates heavy usage - consider larger packages")
        elif frequency == "monthly":
            insights.append("Regular monthly purchase pattern - good for budgeting")
        elif frequency == "irregular":
            insights.append("Irregular purchase pattern - consider auto-reload features")
        
        # Spending insights
        if total_spent > 1000:
            insights.append("High total spending - eligible for enterprise pricing")
        
        # Package preference insights
        if len(package_preferences) == 1:
            insights.append("Consistent package preference - good for loyalty discounts")
        elif len(package_preferences) > 5:
            insights.append("Diverse package usage - consider standardizing for better rates")
        
        # Value insights
        if len(purchases) > 0:
            avg_credits = sum(p.total_credits for p in purchases) / len(purchases)
            if avg_credits > 10000:
                insights.append("High average purchase size - consider bulk discounts")
        
        return insights
    
    def _generate_purchase_recommendations(self, purchases: List[CreditPurchaseTransaction],
                                         frequency: str, avg_purchase: float,
                                         total_credits_purchased: float) -> List[str]:
        """
        Generate purchase recommendations
        """
        recommendations = []
        
        # Frequency-based recommendations
        if frequency == "weekly" and avg_purchase < 100:
            recommendations.append("Consider upgrading to Professional package for better value")
        elif frequency == "monthly" and avg_purchase < 50:
            recommendations.append("Starter package might be sufficient for your usage pattern")
        elif frequency == "irregular":
            recommendations.append("Setup automatic credit top-up to avoid service interruptions")
        
        # Volume-based recommendations
        if total_credits_purchased > 50000:
            recommendations.append("High usage detected - consider Enterprise package for volume discounts")
        
        # Package size recommendations
        if len(purchases) > 0:
            avg_credits = total_credits_purchased / len(purchases)
            if avg_credits < 5000:
                recommendations.append("Small purchases - consider bulk packages for cost savings")
            elif avg_credits > 20000:
                recommendations.append("Large purchases - look for enterprise pricing options")
        
        # Timing recommendations
        if frequency == "weekly":
            recommendations.append("High-frequency usage - enable auto-renewal to avoid manual purchases")
        
        return recommendations
    
    def recommend_package_upgrade(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Recommend package upgrade based on usage patterns
        """
        try:
            # Get user's credit balance and usage
            balance_query = self.db.query(CreditBalance).filter(CreditBalance.user_id == user_id)
            if organization_id:
                balance_query = balance_query.filter(CreditBalance.organization_id == organization_id)
            
            balance = balance_query.first()
            
            if not balance:
                return {"recommendation": "starter", "reason": "No usage history found"}
            
            # Get recent purchase history (last 3 months)
            three_months_ago = datetime.utcnow() - timedelta(days=90)
            recent_purchases = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.user_id == user_id,
                CreditPurchaseTransaction.created_at >= three_months_ago,
                CreditPurchaseTransaction.status == "completed"
            )
            
            if organization_id:
                recent_purchases = recent_purchases.filter(
                    CreditPurchaseTransaction.organization_id == organization_id
                )
            
            recent_purchases = recent_purchases.all()
            
            # Get current package usage
            total_recent_spent = sum(p.total_amount for p in recent_purchases)
            total_recent_credits = sum(p.total_credits for p in recent_purchases)
            
            # Analyze patterns
            usage_intensity = "low"
            if total_recent_credits > 50000:
                usage_intensity = "high"
            elif total_recent_credits > 10000:
                usage_intensity = "medium"
            
            # Generate recommendation
            if usage_intensity == "high":
                recommendation = {
                    "suggested_package": "enterprise",
                    "reason": "High usage pattern detected",
                    "potential_monthly_savings": total_recent_spent * 0.2,  # 20% savings estimate
                    "benefits": [
                        "Volume discounts",
                        "Priority support",
                        "Advanced analytics",
                        "Custom credit allocation"
                    ]
                }
            elif usage_intensity == "medium":
                recommendation = {
                    "suggested_package": "professional",
                    "reason": "Medium usage pattern - Professional package offers better value",
                    "potential_monthly_savings": total_recent_spent * 0.15,  # 15% savings estimate
                    "benefits": [
                        "Bulk discounts",
                        "Priority support",
                        "Advanced analytics"
                    ]
                }
            else:
                recommendation = {
                    "suggested_package": "starter",
                    "reason": "Current usage is well-suited for Starter package",
                    "potential_monthly_savings": 0,
                    "benefits": [
                        "Cost-effective for current usage level",
                        "Flexible credit allocation"
                    ]
                }
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating package upgrade recommendation: {e}")
            return {"error": str(e)}
    
    def generate_purchase_forecast(self, user_id: int, days_ahead: int = 30,
                                 organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate purchase forecast based on historical patterns
        """
        try:
            # Get historical purchase data (last 6 months)
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            query = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.user_id == user_id,
                CreditPurchaseTransaction.created_at >= six_months_ago,
                CreditPurchaseTransaction.status == "completed"
            )
            
            if organization_id:
                query = query.filter(CreditPurchaseTransaction.organization_id == organization_id)
            
            purchases = query.order_by(CreditPurchaseTransaction.created_at.asc()).all()
            
            if not purchases:
                return {
                    "forecast_days": days_ahead,
                    "predicted_purchases": 0,
                    "predicted_spend": 0,
                    "confidence": 0,
                    "reason": "Insufficient purchase history"
                }
            
            # Analyze purchase frequency
            purchase_dates = [p.created_at.date() for p in purchases]
            unique_dates = list(set(purchase_dates))
            
            if len(unique_dates) <= 1:
                frequency_days = 30  # Default to monthly
            else:
                date_diffs = [(unique_dates[i+1] - unique_dates[i]).days for i in range(len(unique_dates)-1)]
                frequency_days = statistics.mean(date_diffs) if date_diffs else 30
            
            # Calculate average purchase value
            avg_purchase_value = statistics.mean([p.total_amount for p in purchases])
            avg_credits = statistics.mean([p.total_credits for p in purchases])
            
            # Forecast future purchases
            predicted_purchases = max(1, days_ahead // int(frequency_days))
            predicted_spend = predicted_purchases * avg_purchase_value
            predicted_credits = predicted_purchases * avg_credits
            
            # Calculate confidence based on data quality
            confidence = min(90, len(purchases) * 10)  # More data = higher confidence
            
            return {
                "forecast_days": days_ahead,
                "predicted_purchases": predicted_purchases,
                "predicted_spend": round(predicted_spend, 2),
                "predicted_credits": int(predicted_credits),
                "average_purchase_value": round(avg_purchase_value, 2),
                "average_credits_per_purchase": int(avg_credits),
                "historical_frequency_days": round(frequency_days, 1),
                "confidence": confidence,
                "analysis_period_days": (datetime.utcnow() - six_months_ago).days,
                "historical_purchases": len(purchases)
            }
            
        except Exception as e:
            logger.error(f"Error generating purchase forecast: {e}")
            return {"error": str(e)}
    
    def get_market_insights(self) -> Dict[str, Any]:
        """
        Get market-wide purchase insights
        """
        try:
            # Get recent market data (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            purchases = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.created_at >= thirty_days_ago,
                CreditPurchaseTransaction.status == "completed"
            ).all()
            
            if not purchases:
                return {"message": "No recent market data available"}
            
            # Calculate market metrics
            total_market_value = sum(p.total_amount for p in purchases)
            total_market_credits = sum(p.total_credits for p in purchases)
            total_purchases = len(purchases)
            
            # Package popularity
            package_popularity = {}
            for purchase in purchases:
                package_name = purchase.package.name if purchase.package else "Unknown"
                if package_name not in package_popularity:
                    package_popularity[package_name] = {
                        "purchase_count": 0,
                        "total_value": 0,
                        "total_credits": 0
                    }
                
                package_popularity[package_name]["purchase_count"] += 1
                package_popularity[package_name]["total_value"] += purchase.total_amount
                package_popularity[package_name]["total_credits"] += purchase.total_credits
            
            # Sort by popularity
            popular_packages = sorted(package_popularity.items(), 
                                    key=lambda x: x[1]["purchase_count"], 
                                    reverse=True)[:5]
            
            return {
                "period_days": 30,
                "market_summary": {
                    "total_purchases": total_purchases,
                    "total_market_value": total_market_value,
                    "total_market_credits": total_market_credits,
                    "average_purchase_value": total_market_value / total_purchases if total_purchases > 0 else 0,
                    "average_credits_per_purchase": total_market_credits / total_purchases if total_purchases > 0 else 0
                },
                "popular_packages": [
                    {
                        "package_name": package_name,
                        **metrics
                    }
                    for package_name, metrics in popular_packages
                ],
                "price_trends": self._analyze_price_trends(purchases),
                "market_size": self._estimate_market_size(total_market_value)
            }
            
        except Exception as e:
            logger.error(f"Error generating market insights: {e}")
            return {"error": str(e)}
    
    def _analyze_price_trends(self, purchases: List[CreditPurchaseTransaction]) -> Dict[str, Any]:
        """
        Analyze price trends in purchases
        """
        # Group purchases by week
        weekly_spending = {}
        for purchase in purchases:
            week_start = purchase.created_at.date().replace(day=1)  # Simplified week grouping
            week_start = week_start.replace(day=purchase.created_at.day - purchase.created_at.weekday())
            
            if week_start not in weekly_spending:
                weekly_spending[week_start] = {
                    "total_spent": 0,
                    "purchase_count": 0
                }
            
            weekly_spending[week_start]["total_spent"] += purchase.total_amount
            weekly_spending[week_start]["purchase_count"] += 1
        
        # Calculate trend
        if len(weekly_spending) < 2:
            return {"trend": "insufficient_data"}
        
        spending_values = [week["total_spent"] for week in weekly_spending.values()]
        if len(spending_values) >= 2:
            recent_avg = statistics.mean(spending_values[-2:])
            earlier_avg = statistics.mean(spending_values[:-2]) if len(spending_values) > 2 else spending_values[0]
            
            change = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
            
            trend = "increasing" if change > 5 else "decreasing" if change < -5 else "stable"
        else:
            trend = "stable"
            change = 0
        
        return {
            "trend": trend,
            "change_percentage": round(change, 2),
            "weekly_breakdown": {
                week.isoformat(): metrics 
                for week, metrics in sorted(weekly_spending.items())
            }
        }
    
    def _estimate_market_size(self, thirty_day_value: float) -> Dict[str, Any]:
        """
        Estimate total market size based on recent activity
        """
        # Simple market size estimation
        monthly_value = thirty_day_value
        annual_estimate = monthly_value * 12
        
        return {
            "monthly_market_value": round(monthly_value, 2),
            "annual_market_estimate": round(annual_estimate, 2),
            "growth_potential": "high" if monthly_value > 10000 else "medium" if monthly_value > 1000 else "low"
        }


# Utility functions
def get_purchase_analytics_service(db: Session = None) -> PurchaseAnalyticsService:
    """
    Get PurchaseAnalyticsService instance
    """
    if db is None:
        db = next(get_db())
    return PurchaseAnalyticsService(db)


def analyze_purchases(user_id: int, days: int = 90, db: Session = None) -> Dict[str, Any]:
    """
    Quick function to analyze user purchase patterns
    """
    service = get_purchase_analytics_service(db)
    return service.analyze_purchase_patterns(user_id, days)