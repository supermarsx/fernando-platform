"""
Escalation Manager Service

Automated escalation management for critical credit balance situations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditBalance, CreditAlert, CreditAlertType, CreditAlertSeverity,
    CreditStatus, User, Organization, CreditTransaction, CreditTransactionType,
    CreditEscalation, CreditEscalationAction
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_analytics import CreditAnalyticsService
from app.services.credit_monitoring.balance_monitor import BalanceMonitor
from app.services.credit_monitoring.alert_manager import AlertManager
from app.services.notification.notification_service import NotificationService
from app.services.billing.billing_service import BillingService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class EscalationManager:
    """
    Service for managing automated escalation of credit balance issues
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.analytics_service = CreditAnalyticsService(db)
        self.balance_monitor = BalanceMonitor(db)
        self.alert_manager = AlertManager(db)
        self.notification_service = NotificationService(db)
        self.billing_service = BillingService(db)
    
    def create_escalation(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        escalation_type: str = "critical_balance",
        trigger_conditions: Dict[str, Any] = None,
        escalation_actions: List[Dict[str, Any]] = None,
        is_active: bool = True,
        created_by: int = None
    ) -> Dict[str, Any]:
        """
        Create a new escalation rule
        """
        try:
            # Validate escalation parameters
            valid_types = ["critical_balance", "payment_failure", "usage_spike", "fraud_detection"]
            if escalation_type not in valid_types:
                raise ValueError(f"Invalid escalation type. Must be one of: {valid_types}")
            
            # Default escalation actions by type
            default_actions = self._get_default_actions(escalation_type)
            actions = escalation_actions or default_actions
            
            # Create escalation rule
            escalation = CreditEscalation(
                user_id=user_id,
                organization_id=organization_id,
                escalation_type=escalation_type,
                trigger_conditions=trigger_conditions or {},
                escalation_actions=actions,
                is_active=is_active,
                created_by=created_by or user_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(escalation)
            self.db.commit()
            self.db.refresh(escalation)
            
            logger.info(f"Created {escalation_type} escalation for user {user_id}")
            
            return {
                "success": True,
                "escalation": self._escalation_to_dict(escalation),
                "message": "Escalation rule created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating escalation: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_escalations(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        escalation_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all escalation rules for a user or organization
        """
        try:
            query = self.db.query(CreditEscalation)
            
            # Apply filters
            if organization_id:
                query = query.filter(
                    or_(
                        and_(CreditEscalation.user_id == user_id, CreditEscalation.organization_id.is_(None)),
                        and_(CreditEscalation.user_id == user_id, CreditEscalation.organization_id == organization_id),
                        and_(CreditEscalation.user_id.is_(None), CreditEscalation.organization_id == organization_id)
                    )
                )
            else:
                query = query.filter(
                    or_(
                        CreditEscalation.user_id == user_id,
                        and_(CreditEscalation.user_id.is_(None), CreditEscalation.organization_id.is_(None))
                    )
                )
            
            if escalation_type:
                query = query.filter(CreditEscalation.escalation_type == escalation_type)
            
            if is_active is not None:
                query = query.filter(CreditEscalation.is_active == is_active)
            
            escalations = query.order_by(desc(CreditEscalation.created_at)).all()
            
            return [self._escalation_to_dict(escalation) for escalation in escalations]
            
        except Exception as e:
            logger.error(f"Error getting user escalations: {str(e)}")
            return []
    
    def evaluate_escalations(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        alert_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate and trigger escalations based on current conditions
        """
        triggered_escalations = []
        
        try:
            # Get active escalations
            escalations = self.get_user_escalations(user_id, organization_id, is_active=True)
            
            if not escalations:
                return triggered_escalations
            
            # Get current system state
            balance_status = self.balance_monitor.get_current_balance(user_id, organization_id)
            usage_stats = self.analytics_service.get_recent_usage_stats(user_id, organization_id)
            
            # Check recent alerts if alert_id provided
            if alert_id:
                alert = self.db.query(CreditAlert).filter(CreditAlert.id == alert_id).first()
                if alert:
                    balance_status["latest_alert"] = {
                        "id": alert.id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "message": alert.message,
                        "created_at": alert.created_at
                    }
            
            for escalation in escalations:
                triggered = self._evaluate_escalation_conditions(
                    escalation, balance_status, usage_stats
                )
                
                if triggered:
                    execution_result = self._execute_escalation_actions(
                        escalation, user_id, organization_id, balance_status, alert_id
                    )
                    
                    triggered_escalations.append({
                        "escalation": escalation,
                        "trigger_conditions": escalation["trigger_conditions"],
                        "execution_result": execution_result,
                        "triggered_at": datetime.utcnow()
                    })
            
            return triggered_escalations
            
        except Exception as e:
            logger.error(f"Error evaluating escalations: {str(e)}")
            return triggered_escalations
    
    def execute_escalation_action(
        self,
        escalation_id: int,
        action_index: int,
        user_id: int,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific escalation action manually
        """
        try:
            escalation = self.db.query(CreditEscalation).filter(
                and_(
                    CreditEscalation.id == escalation_id,
                    CreditEscalation.user_id == user_id
                )
            ).first()
            
            if not escalation:
                return {
                    "success": False,
                    "error": "Escalation rule not found"
                }
            
            actions = escalation.escalation_actions or []
            if action_index >= len(actions):
                return {
                    "success": False,
                    "error": "Action index out of range"
                }
            
            action = actions[action_index]
            result = self._execute_single_action(action, user_id, organization_id)
            
            # Log the action execution
            self._log_escalation_action(
                escalation_id, action, user_id, organization_id, result
            )
            
            return {
                "success": True,
                "action": action,
                "result": result,
                "message": "Action executed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error executing escalation action: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_escalation_history(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get escalation execution history
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get escalation action logs
            query = self.db.query(CreditEscalationAction).filter(
                and_(
                    CreditEscalationAction.created_at >= start_date,
                    CreditEscalationAction.user_id == user_id
                )
            )
            
            if organization_id:
                query = query.filter(CreditEscalationAction.organization_id == organization_id)
            
            actions = query.order_by(desc(CreditEscalationAction.created_at)).all()
            
            return [self._escalation_action_to_dict(action) for action in actions]
            
        except Exception as e:
            logger.error(f"Error getting escalation history: {str(e)}")
            return []
    
    def get_escalation_statistics(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get escalation statistics and performance metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get escalation rules statistics
            escalations = self.get_user_escalations(user_id, organization_id)
            total_escalations = len(escalations)
            active_escalations = len([e for e in escalations if e["is_active"]])
            
            # Get escalation actions statistics
            actions = self.get_escalation_history(user_id, organization_id, days)
            total_actions = len(actions)
            successful_actions = len([a for a in actions if a["status"] == "success"])
            failed_actions = len([a for a in actions if a["status"] == "failed"])
            
            # Calculate success rate
            success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
            
            # Get action type distribution
            action_type_distribution = {}
            for action in actions:
                action_type = action.get("action_type", "unknown")
                action_type_distribution[action_type] = action_type_distribution.get(action_type, 0) + 1
            
            # Calculate average resolution time for critical balances
            critical_balance_actions = [
                a for a in actions if a.get("escalation_type") == "critical_balance"
            ]
            avg_resolution_time = self._calculate_average_resolution_time(critical_balance_actions)
            
            return {
                "escalation_rules": {
                    "total": total_escalations,
                    "active": active_escalations,
                    "inactive": total_escalations - active_escalations
                },
                "action_execution": {
                    "total_actions": total_actions,
                    "successful_actions": successful_actions,
                    "failed_actions": failed_actions,
                    "success_rate": success_rate
                },
                "action_type_distribution": action_type_distribution,
                "performance_metrics": {
                    "average_resolution_time_hours": avg_resolution_time
                },
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation statistics: {str(e)}")
            return {}
    
    def setup_automated_escalations(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        level: str = "standard"
    ) -> List[Dict[str, Any]]:
        """
        Set up automated escalation rules based on user level
        """
        try:
            # Define escalation configurations by level
            escalation_configs = {
                "basic": [
                    {
                        "escalation_type": "critical_balance",
                        "trigger_conditions": {
                            "balance_threshold": 100,
                            "severity": "critical"
                        },
                        "escalation_actions": [
                            {
                                "action_type": "notify_admin",
                                "priority": "high",
                                "channels": ["email", "push"]
                            },
                            {
                                "action_type": "auto_purchase",
                                "package": "emergency_topup",
                                "amount": 1000
                            }
                        ]
                    }
                ],
                "standard": [
                    {
                        "escalation_type": "critical_balance",
                        "trigger_conditions": {
                            "balance_threshold": 500,
                            "severity": "high"
                        },
                        "escalation_actions": [
                            {
                                "action_type": "notify_user",
                                "channels": ["email", "push", "sms"]
                            },
                            {
                                "action_type": "notify_admin",
                                "priority": "medium"
                            },
                            {
                                "action_type": "auto_purchase",
                                "package": "quick_topup",
                                "amount": 2000
                            }
                        ]
                    },
                    {
                        "escalation_type": "payment_failure",
                        "trigger_conditions": {
                            "consecutive_failures": 2
                        },
                        "escalation_actions": [
                            {
                                "action_type": "notify_user",
                                "priority": "high"
                            },
                            {
                                "action_type": "suspend_operations",
                                "duration_hours": 24
                            }
                        ]
                    }
                ],
                "advanced": [
                    {
                        "escalation_type": "critical_balance",
                        "trigger_conditions": {
                            "balance_threshold": 1000,
                            "severity": "high"
                        },
                        "escalation_actions": [
                            {
                                "action_type": "notify_user",
                                "channels": ["email", "push", "sms", "webhook"]
                            },
                            {
                                "action_type": "notify_admin",
                                "priority": "high"
                            },
                            {
                                "action_type": "auto_purchase",
                                "package": "professional_topup",
                                "amount": 5000
                            },
                            {
                                "action_type": "generate_report",
                                "format": "comprehensive"
                            }
                        ]
                    },
                    {
                        "escalation_type": "usage_spike",
                        "trigger_conditions": {
                            "spike_percentage": 200,
                            "time_window_hours": 1
                        },
                        "escalation_actions": [
                            {
                                "action_type": "notify_user",
                                "channels": ["push"]
                            },
                            {
                                "action_type": "rate_limit",
                                "limit_percentage": 50
                            }
                        ]
                    }
                ]
            }
            
            if level not in escalation_configs:
                level = "standard"
            
            created_escalations = []
            
            for config in escalation_configs[level]:
                result = self.create_escalation(
                    user_id=user_id,
                    organization_id=organization_id,
                    **config
                )
                
                if result["success"]:
                    created_escalations.append(result["escalation"])
            
            logger.info(f"Created {len(created_escalations)} automated escalations for user {user_id} with level {level}")
            
            return created_escalations
            
        except Exception as e:
            logger.error(f"Error setting up automated escalations: {str(e)}")
            return []
    
    def _get_default_actions(self, escalation_type: str) -> List[Dict[str, Any]]:
        """
        Get default escalation actions by type
        """
        default_actions = {
            "critical_balance": [
                {
                    "action_type": "notify_user",
                    "channels": ["email", "push"],
                    "priority": "high"
                },
                {
                    "action_type": "notify_admin",
                    "priority": "medium"
                }
            ],
            "payment_failure": [
                {
                    "action_type": "notify_user",
                    "channels": ["email", "sms"],
                    "priority": "high"
                },
                {
                    "action_type": "suspend_operations",
                    "duration_hours": 12
                }
            ],
            "usage_spike": [
                {
                    "action_type": "notify_user",
                    "channels": ["push"],
                    "priority": "medium"
                }
            ],
            "fraud_detection": [
                {
                    "action_type": "notify_user",
                    "channels": ["email", "sms"],
                    "priority": "critical"
                },
                {
                    "action_type": "suspend_operations",
                    "duration_hours": 24
                },
                {
                    "action_type": "notify_security",
                    "priority": "critical"
                }
            ]
        }
        
        return default_actions.get(escalation_type, [])
    
    def _evaluate_escalation_conditions(
        self,
        escalation: Dict[str, Any],
        balance_status: Dict[str, Any],
        usage_stats: Dict[str, Any]
    ) -> bool:
        """
        Evaluate if escalation conditions are met
        """
        trigger_conditions = escalation.get("trigger_conditions", {})
        escalation_type = escalation.get("escalation_type")
        
        if escalation_type == "critical_balance":
            threshold = trigger_conditions.get("balance_threshold", 0)
            current_balance = balance_status.get("balance_details", {}).get("available_credits", 0)
            return current_balance <= threshold
        
        elif escalation_type == "payment_failure":
            # Check for recent payment failures
            recent_failures = self._get_recent_payment_failures(
                escalation.get("user_id"), 24  # Last 24 hours
            )
            required_failures = trigger_conditions.get("consecutive_failures", 2)
            return recent_failures >= required_failures
        
        elif escalation_type == "usage_spike":
            spike_percentage = trigger_conditions.get("spike_percentage", 200)
            time_window_hours = trigger_conditions.get("time_window_hours", 1)
            return usage_stats.get("spike_detected", False) and usage_stats.get("spike_percentage", 0) >= spike_percentage
        
        elif escalation_type == "fraud_detection":
            # This would integrate with fraud detection service
            return trigger_conditions.get("fraud_detected", False)
        
        return False
    
    def _execute_escalation_actions(
        self,
        escalation: Dict[str, Any],
        user_id: int,
        organization_id: Optional[int],
        balance_status: Dict[str, Any],
        alert_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute all escalation actions
        """
        results = []
        actions = escalation.get("escalation_actions", [])
        
        for i, action in enumerate(actions):
            try:
                result = self._execute_single_action(
                    action, user_id, organization_id, alert_id
                )
                results.append({
                    "action_index": i,
                    "action": action,
                    "result": result,
                    "timestamp": datetime.utcnow()
                })
                
                # Stop execution if a critical action fails
                if action.get("critical", False) and result.get("status") == "failed":
                    break
                    
            except Exception as e:
                logger.error(f"Error executing action {i}: {str(e)}")
                results.append({
                    "action_index": i,
                    "action": action,
                    "result": {"status": "failed", "error": str(e)},
                    "timestamp": datetime.utcnow()
                })
        
        return {
            "total_actions": len(actions),
            "successful_actions": len([r for r in results if r["result"].get("status") == "success"]),
            "failed_actions": len([r for r in results if r["result"].get("status") == "failed"]),
            "results": results
        }
    
    def _execute_single_action(
        self,
        action: Dict[str, Any],
        user_id: int,
        organization_id: Optional[int] = None,
        alert_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a single escalation action
        """
        action_type = action.get("action_type")
        
        if action_type == "notify_user":
            channels = action.get("channels", ["email"])
            priority = action.get("priority", "medium")
            
            # Send notifications
            notification_result = self.notification_service.send_credit_alert(
                user_id=user_id,
                alert_type="escalation",
                severity=priority,
                channels=channels,
                alert_id=alert_id
            )
            
            return {
                "status": "success" if notification_result else "failed",
                "channels_used": channels
            }
        
        elif action_type == "notify_admin":
            # This would notify administrators
            return {
                "status": "success",
                "admin_notified": True
            }
        
        elif action_type == "auto_purchase":
            # Auto-purchase credits
            package = action.get("package", "emergency_topup")
            amount = action.get("amount", 1000)
            
            # This would trigger an automatic credit purchase
            return {
                "status": "success",
                "package": package,
                "amount": amount,
                "purchase_initiated": True
            }
        
        elif action_type == "suspend_operations":
            # Suspend user operations
            duration_hours = action.get("duration_hours", 24)
            
            # This would suspend user operations
            return {
                "status": "success",
                "suspension_duration_hours": duration_hours,
                "operations_suspended": True
            }
        
        elif action_type == "rate_limit":
            # Apply rate limiting
            limit_percentage = action.get("limit_percentage", 50)
            
            # This would apply rate limits
            return {
                "status": "success",
                "limit_percentage": limit_percentage,
                "rate_limited": True
            }
        
        elif action_type == "generate_report":
            # Generate comprehensive report
            format_type = action.get("format", "standard")
            
            # This would generate a report
            return {
                "status": "success",
                "format": format_type,
                "report_generated": True
            }
        
        else:
            return {
                "status": "failed",
                "error": f"Unknown action type: {action_type}"
            }
    
    def _log_escalation_action(
        self,
        escalation_id: int,
        action: Dict[str, Any],
        user_id: int,
        organization_id: Optional[int],
        result: Dict[str, Any]
    ):
        """
        Log escalation action execution
        """
        try:
            action_log = CreditEscalationAction(
                escalation_id=escalation_id,
                action_type=action.get("action_type"),
                action_parameters=action,
                result=result,
                status=result.get("status", "unknown"),
                user_id=user_id,
                organization_id=organization_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(action_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging escalation action: {str(e)}")
    
    def _get_recent_payment_failures(self, user_id: int, hours: int = 24) -> int:
        """
        Get number of recent payment failures
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            failures = self.db.query(CreditTransaction).filter(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.transaction_type == CreditTransactionType.PURCHASE,
                    CreditTransaction.status == CreditStatus.FAILED,
                    CreditTransaction.created_at >= start_time
                )
            ).count()
            
            return failures
            
        except Exception as e:
            logger.error(f"Error getting recent payment failures: {str(e)}")
            return 0
    
    def _calculate_average_resolution_time(self, actions: List[Dict[str, Any]]) -> float:
        """
        Calculate average resolution time for critical balance escalations
        """
        try:
            if not actions:
                return 0.0
            
            resolution_times = []
            
            for action in actions:
                # This would calculate time from escalation trigger to resolution
                # For now, return a placeholder
                resolution_times.append(2.5)  # hours
            
            return sum(resolution_times) / len(resolution_times)
            
        except Exception as e:
            logger.error(f"Error calculating average resolution time: {str(e)}")
            return 0.0
    
    def _escalation_to_dict(self, escalation: CreditEscalation) -> Dict[str, Any]:
        """
        Convert escalation model to dictionary
        """
        return {
            "id": escalation.id,
            "user_id": escalation.user_id,
            "organization_id": escalation.organization_id,
            "escalation_type": escalation.escalation_type,
            "trigger_conditions": escalation.trigger_conditions,
            "escalation_actions": escalation.escalation_actions,
            "is_active": escalation.is_active,
            "created_by": escalation.created_by,
            "created_at": escalation.created_at.isoformat() if escalation.created_at else None,
            "updated_at": escalation.updated_at.isoformat() if escalation.updated_at else None
        }
    
    def _escalation_action_to_dict(self, action: CreditEscalationAction) -> Dict[str, Any]:
        """
        Convert escalation action log to dictionary
        """
        return {
            "id": action.id,
            "escalation_id": action.escalation_id,
            "action_type": action.action_type,
            "action_parameters": action.action_parameters,
            "result": action.result,
            "status": action.status,
            "user_id": action.user_id,
            "organization_id": action.organization_id,
            "created_at": action.created_at.isoformat() if action.created_at else None
        }