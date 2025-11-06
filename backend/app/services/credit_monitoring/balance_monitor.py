"""
Balance Monitor Service

Real-time balance monitoring and tracking service.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditBalance, CreditTransaction, CreditTransactionType, CreditStatus,
    CreditAlert, CreditThreshold
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_analytics import CreditAnalyticsService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class BalanceMonitor:
    """
    Real-time credit balance monitoring service
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.analytics_service = CreditAnalyticsService(db)
    
    def get_current_balance(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get current balance status for user
        """
        balance = self.credit_manager.get_balance(user_id, organization_id)
        
        if not balance:
            return {
                "has_balance": False,
                "total_credits": 0,
                "available_credits": 0,
                "reserved_credits": 0,
                "pending_credits": 0,
                "status": "no_balance"
            }
        
        # Calculate balance health metrics
        total_active_credits = balance.total_credits
        utilization_rate = (balance.total_credits_used / max(balance.total_credits_earned, 1)) * 100
        
        # Determine status
        if balance.is_suspended:
            status = "suspended"
        elif balance.available_credits <= 0:
            status = "depleted"
        elif balance.available_credits < balance.total_credits * 0.1:  # Less than 10%
            status = "critical"
        elif balance.available_credits < balance.total_credits * 0.25:  # Less than 25%
            status = "low"
        elif balance.available_credits < balance.total_credits * 0.5:  # Less than 50%
            status = "moderate"
        else:
            status = "healthy"
        
        # Get recent activity
        recent_transactions = self.credit_manager.get_transaction_history(
            user_id, limit=5, organization_id=organization_id
        )
        
        # Get usage forecast
        forecast = self.analytics_service.generate_daily_forecast(user_id, 7, organization_id)
        
        # Estimate days until depletion
        if balance.available_credits > 0 and forecast["total_predicted_credits"] > 0:
            daily_usage_forecast = forecast["total_predicted_credits"] / 7
            days_until_depletion = balance.available_credits / max(daily_usage_forecast, 0.1)
        else:
            days_until_depletion = float('inf')
        
        return {
            "has_balance": True,
            "user_id": user_id,
            "organization_id": organization_id,
            "balance_details": {
                "total_credits": balance.total_credits,
                "available_credits": balance.available_credits,
                "reserved_credits": balance.reserved_credits,
                "pending_credits": balance.pending_credits,
                "credits_used_today": balance.credits_used_today,
                "credits_used_this_month": balance.credits_used_this_month,
                "credits_used_this_year": balance.credits_used_this_year,
                "total_credits_earned": balance.total_credits_earned,
                "total_credits_used": balance.total_credits_used,
                "expired_credits_this_month": balance.expired_credits_this_month
            },
            "status": {
                "overall_status": status,
                "utilization_rate": round(utilization_rate, 2),
                "is_suspended": balance.is_suspended,
                "suspension_reason": balance.suspension_reason,
                "last_activity_at": balance.last_activity_at.isoformat() if balance.last_activity_at else None
            },
            "health_metrics": {
                "utilization_percentage": round(utilization_rate, 2),
                "days_until_depletion": round(days_until_depletion, 1) if days_until_depletion != float('inf') else None,
                "daily_usage_average": round(balance.credits_used_this_month / 30, 2) if balance.credits_used_this_month > 0 else 0,
                "monthly_burn_rate": balance.credits_used_this_month
            },
            "recent_activity": [
                {
                    "transaction_id": t.transaction_id,
                    "type": t.transaction_type,
                    "amount": t.credit_amount,
                    "description": t.description,
                    "created_at": t.created_at.isoformat()
                }
                for t in recent_transactions[:3]
            ],
            "forecast": {
                "next_7_days_estimated_usage": forecast["total_predicted_credits"],
                "confidence": forecast["confidence"],
                "method": forecast["method"]
            },
            "alerts": self._get_active_alerts(user_id, organization_id),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def monitor_balance_changes(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Monitor and analyze balance changes
        """
        try:
            # Get current and historical balance data
            current_balance = self.get_current_balance(user_id, organization_id)
            
            # Get balance changes for last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_transactions = self.credit_manager.get_transaction_history(
                user_id, limit=100, organization_id=organization_id
            )
            
            # Filter transactions from last 24 hours
            recent_transactions = [
                t for t in recent_transactions 
                if t.created_at >= yesterday
            ]
            
            # Calculate 24-hour changes
            net_change_24h = sum(t.credit_amount for t in recent_transactions)
            transactions_count_24h = len(recent_transactions)
            
            # Usage analysis
            usage_transactions = [
                t for t in recent_transactions 
                if t.transaction_type == CreditTransactionType.USAGE
            ]
            total_usage_24h = sum(abs(t.credit_amount) for t in usage_transactions)
            
            # Purchase analysis
            purchase_transactions = [
                t for t in recent_transactions 
                if t.transaction_type == CreditTransactionType.PURCHASE
            ]
            total_purchases_24h = sum(t.credit_amount for t in purchase_transactions)
            
            # Analyze change pattern
            change_pattern = "stable"
            if net_change_24h > current_balance["balance_details"]["total_credits"] * 0.1:
                change_pattern = "significant_increase"
            elif net_change_24h < -current_balance["balance_details"]["total_credits"] * 0.1:
                change_pattern = "significant_decrease"
            elif total_usage_24h > 0 and total_purchases_24h == 0:
                change_pattern = "usage_only"
            elif total_purchases_24h > 0 and total_usage_24h == 0:
                change_pattern = "purchase_only"
            
            # Detect unusual activity
            unusual_activity = self._detect_unusual_activity(
                user_id, recent_transactions, organization_id
            )
            
            return {
                "monitoring_period": "24_hours",
                "period_start": yesterday.isoformat(),
                "period_end": datetime.utcnow().isoformat(),
                "balance_changes": {
                    "net_change": net_change_24h,
                    "transactions_count": transactions_count_24h,
                    "change_pattern": change_pattern,
                    "usage_amount": total_usage_24h,
                    "purchase_amount": total_purchases_24h
                },
                "activity_analysis": {
                    "usage_transactions": len(usage_transactions),
                    "purchase_transactions": len(purchase_transactions),
                    "other_transactions": transactions_count_24h - len(usage_transactions) - len(purchase_transactions),
                    "most_active_transaction_type": self._get_most_common_transaction_type(recent_transactions)
                },
                "unusual_activity": unusual_activity,
                "current_balance_snapshot": current_balance,
                "recommendations": self._generate_balance_recommendations(
                    current_balance, net_change_24h, unusual_activity
                )
            }
            
        except Exception as e:
            logger.error(f"Error monitoring balance changes: {e}")
            return {"error": str(e)}
    
    def _detect_unusual_activity(self, user_id: int, transactions: List[CreditTransaction],
                               organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Detect unusual balance activity
        """
        unusual_activity = {
            "detected": False,
            "types": [],
            "details": []
        }
        
        if not transactions:
            return unusual_activity
        
        # Get historical baseline for this user
        baseline_period_start = datetime.utcnow() - timedelta(days=30)
        baseline_transactions = [
            t for t in self.credit_manager.get_transaction_history(user_id, limit=1000, organization_id=organization_id)
            if t.created_at >= baseline_period_start
        ]
        
        if not baseline_transactions:
            return unusual_activity
        
        # Calculate baseline metrics
        baseline_daily_avg = len(baseline_transactions) / 30
        baseline_usage_avg = sum(abs(t.credit_amount) for t in baseline_transactions 
                               if t.transaction_type == CreditTransactionType.USAGE) / 30
        
        # Check for transaction volume spike
        today_transactions = len(transactions)
        if today_transactions > baseline_daily_avg * 3:  # 3x normal volume
            unusual_activity["detected"] = True
            unusual_activity["types"].append("high_volume")
            unusual_activity["details"].append(
                f"Transaction volume {today_transactions} is {today_transactions/baseline_daily_avg:.1f}x normal"
            )
        
        # Check for unusual usage patterns
        today_usage = sum(abs(t.credit_amount) for t in transactions 
                         if t.transaction_type == CreditTransactionType.USAGE)
        
        if today_usage > baseline_usage_avg * 5:  # 5x normal usage
            unusual_activity["detected"] = True
            unusual_activity["types"].append("high_usage")
            unusual_activity["details"].append(
                f"Usage {today_usage:.1f} is {today_usage/baseline_usage_avg:.1f}x normal"
            )
        
        # Check for large single transactions
        large_transactions = [t for t in transactions if abs(t.credit_amount) > 1000]
        if large_transactions:
            unusual_activity["detected"] = True
            unusual_activity["types"].append("large_transactions")
            unusual_activity["details"].append(
                f"{len(large_transactions)} large transactions detected"
            )
        
        # Check for rapid succession of transactions
        transactions_per_hour = self._calculate_transactions_per_hour(transactions)
        if transactions_per_hour > baseline_daily_avg / 24 * 10:  # 10x normal hourly rate
            unusual_activity["detected"] = True
            unusual_activity["types"].append("rapid_transactions")
            unusual_activity["details"].append(
                f"High transaction frequency: {transactions_per_hour:.1f} per hour"
            )
        
        return unusual_activity
    
    def _calculate_transactions_per_hour(self, transactions: List[CreditTransaction]) -> float:
        """
        Calculate transactions per hour for the given transactions
        """
        if not transactions:
            return 0
        
        # Sort transactions by time
        sorted_transactions = sorted(transactions, key=lambda t: t.created_at)
        
        # Calculate time span
        time_span = (sorted_transactions[-1].created_at - sorted_transactions[0].created_at).total_seconds() / 3600
        
        if time_span <= 0:
            return len(transactions)
        
        return len(transactions) / time_span
    
    def _get_most_common_transaction_type(self, transactions: List[CreditTransaction]) -> str:
        """
        Get the most common transaction type in the list
        """
        if not transactions:
            return "none"
        
        type_counts = {}
        for transaction in transactions:
            t_type = transaction.transaction_type
            type_counts[t_type] = type_counts.get(t_type, 0) + 1
        
        return max(type_counts.items(), key=lambda x: x[1])[0]
    
    def _generate_balance_recommendations(self, current_balance: Dict[str, Any], 
                                        net_change_24h: float, unusual_activity: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on balance analysis
        """
        recommendations = []
        
        status = current_balance["status"]["overall_status"]
        available_credits = current_balance["balance_details"]["available_credits"]
        days_until_depletion = current_balance["health_metrics"]["days_until_depletion"]
        
        # Status-based recommendations
        if status == "critical":
            recommendations.append("Critical balance level - immediate top-up recommended")
        elif status == "low":
            recommendations.append("Low balance - consider planning top-up soon")
        elif status == "depleted":
            recommendations.append("Balance depleted - top-up required to continue service")
        
        # Usage-based recommendations
        if days_until_depletion and days_until_depletion < 7:
            recommendations.append(f"Current usage suggests depletion in {days_until_depletion:.1f} days")
        elif days_until_depletion and days_until_depletion < 30:
            recommendations.append(f"Consider top-up within {days_until_depletion:.1f} days")
        
        # Activity-based recommendations
        if unusual_activity["detected"]:
            if "high_usage" in unusual_activity["types"]:
                recommendations.append("Unusual high usage detected - review application settings")
            if "rapid_transactions" in unusual_activity["types"]:
                recommendations.append("High transaction frequency - check for automated processes")
            if "large_transactions" in unusual_activity["types"]:
                recommendations.append("Large transactions detected - verify transaction legitimacy")
        
        # Optimization recommendations
        if current_balance["status"]["utilization_rate"] > 80:
            recommendations.append("High utilization rate - consider larger packages for better value")
        
        return recommendations
    
    def _get_active_alerts(self, user_id: int, organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get active alerts for user
        """
        alerts = self.db.query(CreditAlert).filter(
            CreditAlert.user_id == user_id,
            CreditAlert.status == "active"
        ).order_by(desc(CreditAlert.triggered_at)).limit(5).all()
        
        return [
            {
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "current_balance": alert.current_balance,
                "threshold_balance": alert.threshold_balance,
                "triggered_at": alert.triggered_at.isoformat(),
                "escalation_level": alert.escalation_level
            }
            for alert in alerts
        ]
    
    def generate_balance_report(self, user_id: int, days: int = 30,
                              organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate comprehensive balance report
        """
        try:
            # Get current balance status
            current_status = self.get_current_balance(user_id, organization_id)
            
            # Get balance changes analysis
            changes_analysis = self.monitor_balance_changes(user_id, organization_id)
            
            # Get usage analytics
            usage_analytics = self.analytics_service.usage_tracker.get_usage_summary(
                user_id, days, organization_id
            )
            
            # Get transaction history
            transactions = self.credit_manager.get_transaction_history(
                user_id, limit=1000, organization_id=organization_id
            )
            
            # Filter transactions for the report period
            start_date = datetime.utcnow() - timedelta(days=days)
            report_transactions = [
                t for t in transactions 
                if t.created_at >= start_date
            ]
            
            # Calculate period statistics
            period_stats = {
                "total_transactions": len(report_transactions),
                "total_credits_used": sum(abs(t.credit_amount) for t in report_transactions 
                                        if t.transaction_type == CreditTransactionType.USAGE),
                "total_credits_purchased": sum(t.credit_amount for t in report_transactions 
                                             if t.transaction_type == CreditTransactionType.PURCHASE),
                "net_balance_change": sum(t.credit_amount for t in report_transactions),
                "transaction_types": {}
            }
            
            # Count transaction types
            for transaction in report_transactions:
                t_type = transaction.transaction_type
                if t_type not in period_stats["transaction_types"]:
                    period_stats["transaction_types"][t_type] = 0
                period_stats["transaction_types"][t_type] += 1
            
            # Generate insights
            insights = self._generate_balance_insights(
                current_status, period_stats, usage_analytics
            )
            
            return {
                "report_period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "generated_at": datetime.utcnow().isoformat()
                },
                "executive_summary": {
                    "current_status": current_status["status"]["overall_status"],
                    "available_credits": current_status["balance_details"]["available_credits"],
                    "days_until_depletion": current_status["health_metrics"]["days_until_depletion"],
                    "monthly_usage": current_status["balance_details"]["credits_used_this_month"],
                    "monthly_burn_rate": current_status["health_metrics"]["monthly_burn_rate"]
                },
                "current_balance": current_status,
                "period_analysis": {
                    "transactions": period_stats,
                    "usage_patterns": usage_analytics,
                    "balance_changes": changes_analysis
                },
                "insights": insights,
                "recommendations": self._generate_balance_recommendations(
                    current_status, period_stats.get("net_balance_change", 0), {"detected": False}
                ),
                "trend_analysis": self._analyze_balance_trend(report_transactions, current_status)
            }
            
        except Exception as e:
            logger.error(f"Error generating balance report: {e}")
            return {"error": str(e)}
    
    def _generate_balance_insights(self, current_status: Dict[str, Any], 
                                 period_stats: Dict[str, Any], 
                                 usage_analytics: Dict[str, Any]) -> List[str]:
        """
        Generate insights from balance analysis
        """
        insights = []
        
        # Current status insights
        status = current_status["status"]["overall_status"]
        if status == "critical":
            insights.append("Balance is critically low - immediate action required")
        elif status == "healthy":
            insights.append("Balance is healthy with good availability")
        
        # Usage pattern insights
        if usage_analytics["total_requests"] == 0:
            insights.append("No usage activity in the current period")
        else:
            if usage_analytics["error_rate"] > 10:
                insights.append(f"High error rate ({usage_analytics['error_rate']:.1f}%) - may indicate technical issues")
            
            # Provider insights
            provider_count = len(usage_analytics["provider_breakdown"])
            if provider_count > 3:
                insights.append("Diverse provider usage detected")
            elif provider_count == 1:
                insights.append("Single provider usage - consider diversification")
        
        # Financial insights
        utilization_rate = current_status["status"]["utilization_rate"]
        if utilization_rate > 90:
            insights.append("Very high utilization - consider upgrading package")
        elif utilization_rate < 10:
            insights.append("Low utilization - current package may be oversized")
        
        return insights
    
    def _analyze_balance_trend(self, transactions: List[CreditTransaction], 
                             current_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze balance trend over time
        """
        if not transactions:
            return {"trend": "insufficient_data"}
        
        # Group transactions by day
        daily_changes = {}
        for transaction in transactions:
            day = transaction.created_at.date().isoformat()
            if day not in daily_changes:
                daily_changes[day] = 0
            daily_changes[day] += transaction.credit_amount
        
        # Calculate trend
        if len(daily_changes) < 2:
            return {"trend": "insufficient_data"}
        
        daily_values = list(daily_changes.values())
        recent_avg = sum(daily_values[-7:]) / min(7, len(daily_values))
        earlier_avg = sum(daily_values[:-7]) / max(1, len(daily_values) - 7)
        
        if earlier_avg == 0:
            trend_direction = "stable"
            trend_strength = 0
        else:
            trend_strength = abs((recent_avg - earlier_avg) / earlier_avg) * 100
            if trend_strength < 5:
                trend_direction = "stable"
            elif recent_avg > earlier_avg:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
        
        return {
            "trend_direction": trend_direction,
            "trend_strength": round(trend_strength, 2),
            "recent_7_day_average": round(recent_avg, 2),
            "previous_period_average": round(earlier_avg, 2),
            "daily_changes": daily_changes
        }
    
    def get_organization_balance_summary(self, organization_id: int) -> Dict[str, Any]:
        """
        Get balance summary for entire organization
        """
        try:
            # Get all organization members
            organization_balances = self.db.query(CreditBalance).filter(
                CreditBalance.organization_id == organization_id,
                CreditBalance.is_active == True
            ).all()
            
            if not organization_balances:
                return {"organization_id": organization_id, "message": "No organization members found"}
            
            # Calculate organization totals
            total_available = sum(b.available_credits for b in organization_balances)
            total_reserved = sum(b.reserved_credits for b in organization_balances)
            total_usage = sum(b.credits_used_this_month for b in organization_balances)
            member_count = len(organization_balances)
            
            # Calculate member distribution
            member_distribution = {
                "healthy": len([b for b in organization_balances if b.available_credits > b.total_credits * 0.5]),
                "low": len([b for b in organization_balances if b.available_credits <= b.total_credits * 0.25 and b.available_credits > b.total_credits * 0.1]),
                "critical": len([b for b in organization_balances if b.available_credits <= b.total_credits * 0.1]),
                "depleted": len([b for b in organization_balances if b.available_credits <= 0])
            }
            
            # Get top users by usage
            top_users = sorted(organization_balances, 
                             key=lambda b: b.credits_used_this_month, 
                             reverse=True)[:5]
            
            return {
                "organization_id": organization_id,
                "summary": {
                    "total_members": member_count,
                    "total_available_credits": total_available,
                    "total_reserved_credits": total_reserved,
                    "total_monthly_usage": total_usage,
                    "average_credits_per_member": total_available / member_count if member_count > 0 else 0,
                    "organization_utilization": (total_usage / max(total_usage + total_available, 1)) * 100
                },
                "member_distribution": member_distribution,
                "top_users_by_usage": [
                    {
                        "user_id": user.user_id,
                        "available_credits": user.available_credits,
                        "monthly_usage": user.credits_used_this_month,
                        "status": "healthy" if user.available_credits > user.total_credits * 0.5 else "low" if user.available_credits > user.total_credits * 0.1 else "critical"
                    }
                    for user in top_users
                ],
                "alerts": self._get_organization_alerts(organization_id),
                "recommendations": self._generate_organization_recommendations(
                    total_available, total_usage, member_distribution
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting organization balance summary: {e}")
            return {"error": str(e)}
    
    def _get_organization_alerts(self, organization_id: int) -> List[Dict[str, Any]]:
        """
        Get alerts for organization members
        """
        org_alerts = self.db.query(CreditAlert).join(CreditBalance).filter(
            CreditBalance.organization_id == organization_id,
            CreditAlert.status == "active"
        ).order_by(desc(CreditAlert.triggered_at)).limit(10).all()
        
        return [
            {
                "alert_id": alert.id,
                "user_id": alert.user_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in org_alerts
        ]
    
    def _generate_organization_recommendations(self, total_available: float, 
                                             total_usage: float, 
                                             member_distribution: Dict[str, int]) -> List[str]:
        """
        Generate recommendations for organization
        """
        recommendations = []
        
        total_members = sum(member_distribution.values())
        
        if total_members > 0:
            critical_percentage = (member_distribution["critical"] / total_members) * 100
            if critical_percentage > 20:
                recommendations.append("High percentage of members with critical balances - consider organization-wide top-up")
        
        if total_usage > total_available * 2:
            recommendations.append("Monthly usage exceeds available credits - budget adjustment needed")
        
        utilization_rate = (total_usage / max(total_usage + total_available, 1)) * 100
        if utilization_rate > 80:
            recommendations.append("High organizational utilization - consider upgrading organization plan")
        elif utilization_rate < 20:
            recommendations.append("Low organizational utilization - consider right-sizing plans")
        
        return recommendations


# Utility functions
def get_balance_monitor(db: Session = None) -> BalanceMonitor:
    """
    Get BalanceMonitor instance
    """
    if db is None:
        db = next(get_db())
    return BalanceMonitor(db)


def get_current_balance(user_id: int, organization_id: Optional[int] = None, 
                       db: Session = None) -> Dict[str, Any]:
    """
    Quick function to get current balance
    """
    monitor = get_balance_monitor(db)
    return monitor.get_current_balance(user_id, organization_id)