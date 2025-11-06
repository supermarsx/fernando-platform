"""
Alert Manager Service

Credit balance alerts and notification management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditAlert, CreditBalance, CreditThreshold, CreditTransaction,
    CreditTransactionType, CreditStatus
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_monitoring.balance_monitor import BalanceMonitor
from app.db.session import get_db

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Service for managing credit balance alerts and notifications
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.balance_monitor = BalanceMonitor(db)
    
    def check_balance_alerts(self, user_id: int, organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check and trigger balance alerts for user
        """
        triggered_alerts = []
        
        try:
            # Get current balance status
            balance_status = self.balance_monitor.get_current_balance(user_id, organization_id)
            
            if not balance_status["has_balance"]:
                return triggered_alerts
            
            balance = balance_status["balance_details"]
            available_credits = balance["available_credits"]
            total_credits = balance["total_credits"]
            
            # Define alert thresholds
            thresholds = [
                {"type": "critical", "percentage": 5, "min_credits": 100},
                {"type": "low", "percentage": 10, "min_credits": 500},
                {"type": "warning", "percentage": 20, "min_credits": 1000},
                {"type": "expiration_warning", "percentage": None, "min_credits": 0}
            ]
            
            for threshold in thresholds:
                alert_triggered = False
                alert_message = ""
                
                if threshold["type"] == "expiration_warning":
                    # Check for expiring credits
                    expiring_alerts = self._check_expiring_credits(user_id, organization_id)
                    for alert in expiring_alerts:
                        triggered_alerts.append(alert)
                    continue
                
                # Calculate threshold value
                if threshold["percentage"]:
                    threshold_value = max(total_credits * (threshold["percentage"] / 100), threshold["min_credits"])
                else:
                    threshold_value = threshold["min_credits"]
                
                # Check if alert should be triggered
                if available_credits <= threshold_value:
                    # Check if similar alert already exists and is recent
                    recent_alert = self._get_recent_alert(
                        user_id, organization_id, threshold["type"], hours=24
                    )
                    
                    if not recent_alert:
                        # Create new alert
                        alert = self._create_balance_alert(
                            user_id, organization_id, threshold["type"], 
                            available_credits, threshold_value, balance_status
                        )
                        triggered_alerts.append(alert)
                        
                        # Send notifications
                        self._send_alert_notifications(alert)
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Error checking balance alerts for user {user_id}: {e}")
            return []
    
    def _check_expiring_credits(self, user_id: int, organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Check for credits expiring soon
        """
        expiring_alerts = []
        
        # Get transactions with expiration dates
        expiring_transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.expires_at.isnot(None),
            CreditTransaction.expires_at >= datetime.utcnow(),
            CreditTransaction.status == CreditStatus.COMPLETED,
            CreditTransaction.is_expired == False
        )
        
        if organization_id:
            expiring_transactions = expiring_transactions.filter(
                CreditTransaction.organization_id == organization_id
            )
        
        expiring_transactions = expiring_transactions.all()
        
        # Check different expiration windows
        for days_ahead in [7, 3, 1]:
            cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
            
            expiring_soon = [
                t for t in expiring_transactions 
                if t.expires_at <= cutoff_date and t.expires_at >= datetime.utcnow()
            ]
            
            if expiring_soon:
                total_expiring = sum(t.credit_amount for t in expiring_soon)
                
                # Check if alert already exists for this window
                recent_alert = self._get_recent_alert(
                    user_id, organization_id, "expiration_warning", hours=48
                )
                
                if not recent_alert:
                    alert = self._create_expiration_alert(
                        user_id, organization_id, days_ahead, 
                        total_expiring, expiring_soon
                    )
                    expiring_alerts.append(alert)
                    
                    # Send notifications
                    self._send_alert_notifications(alert)
        
        return expiring_alerts
    
    def _get_recent_alert(self, user_id: int, organization_id: Optional[int], 
                        alert_type: str, hours: int = 24) -> Optional[CreditAlert]:
        """
        Check if a recent alert of the same type exists
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(CreditAlert).filter(
            CreditAlert.user_id == user_id,
            CreditAlert.alert_type == alert_type,
            CreditAlert.triggered_at >= cutoff_time,
            CreditAlert.status == "active"
        )
        
        if organization_id:
            query = query.filter(CreditAlert.organization_id == organization_id)
        
        return query.first()
    
    def _create_balance_alert(self, user_id: int, organization_id: Optional[int],
                            alert_type: str, current_balance: float, 
                            threshold_balance: float, balance_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a balance alert
        """
        # Get balance record
        balance_query = self.db.query(CreditBalance).filter(
            CreditBalance.user_id == user_id,
            CreditBalance.is_active == True
        )
        
        if organization_id:
            balance_query = balance_query.filter(CreditBalance.organization_id == organization_id)
        
        balance = balance_query.first()
        
        if not balance:
            raise ValueError("Balance record not found")
        
        # Calculate percentage
        total_credits = balance.total_credits
        threshold_percentage = (threshold_balance / max(total_credits, 1)) * 100
        
        # Determine severity
        severity_map = {
            "critical": "critical",
            "low": "high", 
            "warning": "medium"
        }
        severity = severity_map.get(alert_type, "medium")
        
        # Create message
        messages = {
            "critical": f"CRITICAL: Your credit balance is critically low ({current_balance:.0f} credits remaining)",
            "low": f"Low balance warning: {current_balance:.0f} credits remaining",
            "warning": f"Balance warning: {current_balance:.0f} credits remaining"
        }
        
        # Create alert record
        alert = CreditAlert(
            user_id=user_id,
            organization_id=organization_id,
            balance_id=balance.id,
            alert_type=alert_type,
            severity=severity,
            current_balance=current_balance,
            threshold_balance=threshold_balance,
            threshold_percentage=threshold_percentage,
            message=messages.get(alert_type, f"Balance alert: {current_balance:.0f} credits remaining"),
            suggested_action=self._get_alert_action(alert_type, current_balance)
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Created {alert_type} alert for user {user_id}")
        
        return {
            "alert_id": alert.id,
            "alert_type": alert_type,
            "severity": severity,
            "message": alert.message,
            "current_balance": current_balance,
            "threshold_balance": threshold_balance,
            "threshold_percentage": round(threshold_percentage, 2),
            "triggered_at": alert.triggered_at.isoformat()
        }
    
    def _create_expiration_alert(self, user_id: int, organization_id: Optional[int],
                               days_ahead: int, total_expiring: float, 
                               expiring_transactions: List[CreditTransaction]) -> Dict[str, Any]:
        """
        Create an expiration alert
        """
        # Get balance record
        balance_query = self.db.query(CreditBalance).filter(
            CreditBalance.user_id == user_id,
            CreditBalance.is_active == True
        )
        
        if organization_id:
            balance_query = balance_query.filter(CreditBalance.organization_id == organization_id)
        
        balance = balance_query.first()
        
        if not balance:
            raise ValueError("Balance record not found")
        
        # Create alert
        alert = CreditAlert(
            user_id=user_id,
            organization_id=organization_id,
            balance_id=balance.id,
            alert_type="expiration_warning",
            severity="medium",
            current_balance=balance.available_credits,
            threshold_balance=total_expiring,
            message=f"{total_expiring:.0f} credits will expire in {days_ahead} days",
            suggested_action="Use or roll over expiring credits before they expire"
        )
        
        # Store transaction details in metadata
        transaction_details = [
            {
                "transaction_id": t.transaction_id,
                "credit_amount": t.credit_amount,
                "expires_at": t.expires_at.isoformat()
            }
            for t in expiring_transactions
        ]
        
        alert.meta_data = {"expiring_transactions": transaction_details}
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Created expiration alert for user {user_id}: {total_expiring:.0f} credits expiring in {days_ahead} days")
        
        return {
            "alert_id": alert.id,
            "alert_type": "expiration_warning",
            "severity": "medium",
            "message": alert.message,
            "current_balance": balance.available_credits,
            "threshold_balance": total_expiring,
            "days_ahead": days_ahead,
            "expiring_transactions": len(expiring_transactions),
            "triggered_at": alert.triggered_at.isoformat()
        }
    
    def _get_alert_action(self, alert_type: str, current_balance: float) -> str:
        """
        Get suggested action for alert type
        """
        actions = {
            "critical": "Immediate credit top-up required to maintain service",
            "low": "Consider purchasing additional credits soon",
            "warning": "Monitor usage and plan for credit replenishment",
            "expiration_warning": "Use credits before expiration or arrange rollover"
        }
        
        return actions.get(alert_type, "Monitor credit usage")
    
    def _send_alert_notifications(self, alert_data: Dict[str, Any]):
        """
        Send notifications for alert
        """
        try:
            # In a real implementation, this would integrate with notification services
            # For now, we'll log the notification
            logger.info(f"ALERT NOTIFICATION: {alert_data['message']}")
            
            # Mark notifications as sent in the alert record
            if "alert_id" in alert_data:
                alert = self.db.query(CreditAlert).filter(
                    CreditAlert.id == alert_data["alert_id"]
                ).first()
                
                if alert:
                    alert.notification_sent = True
                    alert.email_sent = True  # Assume email sent
                    self.db.commit()
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    def get_user_alerts(self, user_id: int, organization_id: Optional[int] = None,
                       status: str = "active", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get alerts for user
        """
        query = self.db.query(CreditAlert).filter(
            CreditAlert.user_id == user_id
        )
        
        if organization_id:
            query = query.filter(CreditAlert.organization_id == organization_id)
        
        if status != "all":
            query = query.filter(CreditAlert.status == status)
        
        alerts = query.order_by(desc(CreditAlert.triggered_at)).limit(limit).all()
        
        return [
            {
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "suggested_action": alert.suggested_action,
                "current_balance": alert.current_balance,
                "threshold_balance": alert.threshold_balance,
                "threshold_percentage": alert.threshold_percentage,
                "status": alert.status,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "escalation_level": alert.escalation_level,
                "notification_sent": alert.notification_sent
            }
            for alert in alerts
        ]
    
    def acknowledge_alert(self, alert_id: int, user_id: int) -> Dict[str, Any]:
        """
        Acknowledge an alert
        """
        try:
            alert = self.db.query(CreditAlert).filter(
                CreditAlert.id == alert_id,
                CreditAlert.user_id == user_id
            ).first()
            
            if not alert:
                return {"success": False, "error": "Alert not found"}
            
            if alert.status != "active":
                return {"success": False, "error": "Alert is not active"}
            
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = user_id
            
            self.db.commit()
            
            logger.info(f"Alert {alert_id} acknowledged by user {user_id}")
            
            return {
                "success": True,
                "alert_id": alert_id,
                "acknowledged_at": alert.acknowledged_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def resolve_alert(self, alert_id: int, user_id: int) -> Dict[str, Any]:
        """
        Resolve an alert
        """
        try:
            alert = self.db.query(CreditAlert).filter(
                CreditAlert.id == alert_id,
                CreditAlert.user_id == user_id
            ).first()
            
            if not alert:
                return {"success": False, "error": "Alert not found"}
            
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Alert {alert_id} resolved by user {user_id}")
            
            return {
                "success": True,
                "alert_id": alert_id,
                "resolved_at": alert.resolved_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def escalate_alert(self, alert_id: int, escalated_to: int) -> Dict[str, Any]:
        """
        Escalate an alert to another user
        """
        try:
            alert = self.db.query(CreditAlert).filter(
                CreditAlert.id == alert_id
            ).first()
            
            if not alert:
                return {"success": False, "error": "Alert not found"}
            
            alert.escalation_level += 1
            alert.escalated_at = datetime.utcnow()
            alert.escalated_to = escalated_to
            
            # Send notification to escalated user
            logger.info(f"Alert {alert_id} escalated to user {escalated_to}")
            
            self.db.commit()
            
            return {
                "success": True,
                "alert_id": alert_id,
                "escalation_level": alert.escalation_level,
                "escalated_to": escalated_to,
                "escalated_at": alert.escalated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error escalating alert {alert_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_custom_threshold(self, user_id: int, threshold_type: str,
                              threshold_value: float, alert_enabled: bool = True,
                              organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create custom alert threshold
        """
        try:
            # Get user's balance
            balance_query = self.db.query(CreditBalance).filter(
                CreditBalance.user_id == user_id,
                CreditBalance.is_active == True
            )
            
            if organization_id:
                balance_query = balance_query.filter(CreditBalance.organization_id == organization_id)
            
            balance = balance_query.first()
            
            if not balance:
                return {"success": False, "error": "Balance not found"}
            
            # Create threshold
            threshold = CreditThreshold(
                user_id=user_id,
                organization_id=organization_id,
                metric_type="credit_balance",
                threshold_type="absolute",
                threshold_value=threshold_value,
                alert_enabled=alert_enabled,
                alert_severity="medium",
                notification_channels=["email", "push"]
            )
            
            self.db.add(threshold)
            self.db.commit()
            self.db.refresh(threshold)
            
            logger.info(f"Created custom threshold for user {user_id}: {threshold_value}")
            
            return {
                "success": True,
                "threshold_id": threshold.id,
                "threshold_value": threshold_value,
                "alert_enabled": alert_enabled
            }
            
        except Exception as e:
            logger.error(f"Error creating custom threshold: {e}")
            return {"success": False, "error": str(e)}
    
    def get_alert_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics on alert activity
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get alert data
        alerts = self.db.query(CreditAlert).filter(
            CreditAlert.triggered_at >= start_date,
            CreditAlert.triggered_at <= end_date
        ).all()
        
        if not alerts:
            return {
                "period_days": days,
                "total_alerts": 0,
                "alert_types": {},
                "severity_distribution": {},
                "resolution_rate": 0
            }
        
        # Analyze alerts
        total_alerts = len(alerts)
        alert_types = {}
        severity_distribution = {}
        resolution_stats = {"resolved": 0, "acknowledged": 0, "active": 0}
        
        for alert in alerts:
            # Count by type
            alert_type = alert.alert_type
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            
            # Count by severity
            severity = alert.severity
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            
            # Count resolution status
            status = alert.status
            if status in resolution_stats:
                resolution_stats[status] += 1
        
        # Calculate resolution rate
        resolved_count = resolution_stats.get("resolved", 0)
        resolution_rate = (resolved_count / total_alerts * 100) if total_alerts > 0 else 0
        
        # Get most common alert type
        most_common_alert = max(alert_types.items(), key=lambda x: x[1]) if alert_types else None
        
        # Get peak alert day
        daily_alerts = {}
        for alert in alerts:
            day = alert.triggered_at.date().isoformat()
            daily_alerts[day] = daily_alerts.get(day, 0) + 1
        
        peak_day = max(daily_alerts.items(), key=lambda x: x[1]) if daily_alerts else None
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_alerts": total_alerts,
            "alert_types": alert_types,
            "severity_distribution": severity_distribution,
            "resolution_stats": resolution_stats,
            "resolution_rate": round(resolution_rate, 2),
            "most_common_alert": most_common_alert[0] if most_common_alert else None,
            "peak_alert_day": {
                "date": peak_day[0],
                "count": peak_day[1]
            } if peak_day else None,
            "daily_breakdown": daily_alerts
        }
    
    def cleanup_resolved_alerts(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old resolved alerts
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find resolved alerts older than cutoff
            old_alerts = self.db.query(CreditAlert).filter(
                CreditAlert.status == "resolved",
                CreditAlert.resolved_at <= cutoff_date
            ).all()
            
            deleted_count = len(old_alerts)
            
            # Delete old alerts
            for alert in old_alerts:
                self.db.delete(alert)
            
            self.db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old resolved alerts")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up resolved alerts: {e}")
            return {"success": False, "error": str(e)}


# Utility functions
def get_alert_manager(db: Session = None) -> AlertManager:
    """
    Get AlertManager instance
    """
    if db is None:
        db = next(get_db())
    return AlertManager(db)


def check_user_alerts(user_id: int, organization_id: Optional[int] = None, 
                     db: Session = None) -> List[Dict[str, Any]]:
    """
    Quick function to check user alerts
    """
    manager = get_alert_manager(db)
    return manager.check_balance_alerts(user_id, organization_id)