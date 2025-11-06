"""
Threshold Manager Service

Configurable alert thresholds and threshold management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from app.models.credits import (
    CreditThreshold, CreditBalance, CreditAlert, CreditAlertType,
    CreditAlertSeverity, CreditStatus, User, Organization
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_analytics import CreditAnalyticsService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class ThresholdManager:
    """
    Service for managing configurable credit balance thresholds
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.analytics_service = CreditAnalyticsService(db)
    
    def create_threshold(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        threshold_type: str = "low_balance",
        threshold_value: Optional[Decimal] = None,
        percentage: Optional[Decimal] = None,
        severity: str = "medium",
        notification_channels: Optional[List[str]] = None,
        is_active: bool = True,
        created_by: int = None
    ) -> Dict[str, Any]:
        """
        Create a new credit threshold
        """
        try:
            # Validate threshold parameters
            if not threshold_value and not percentage:
                raise ValueError("Either threshold_value or percentage must be specified")
            
            if threshold_value and threshold_value <= 0:
                raise ValueError("Threshold value must be positive")
            
            if percentage and (percentage <= 0 or percentage > 100):
                raise ValueError("Percentage must be between 0 and 100")
            
            # Validate threshold type
            valid_types = ["low_balance", "high_spend", "usage_spike", "expiration_warning"]
            if threshold_type not in valid_types:
                raise ValueError(f"Invalid threshold type. Must be one of: {valid_types}")
            
            # Validate severity
            valid_severities = ["low", "medium", "high", "critical"]
            if severity not in valid_severities:
                raise ValueError(f"Invalid severity. Must be one of: {valid_severities}")
            
            # Get current balance for percentage-based thresholds
            balance_value = None
            if percentage:
                balance_status = self.credit_manager.get_balance(user_id, organization_id)
                if balance_status:
                    balance_value = balance_status.total_credits
                    threshold_value = balance_value * (percentage / 100)
                else:
                    raise ValueError("Cannot create percentage-based threshold without existing balance")
            
            # Create threshold
            threshold = CreditThreshold(
                user_id=user_id,
                organization_id=organization_id,
                threshold_type=threshold_type,
                threshold_value=threshold_value,
                percentage=percentage,
                severity=severity,
                notification_channels=notification_channels or ["email"],
                is_active=is_active,
                created_by=created_by or user_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(threshold)
            self.db.commit()
            self.db.refresh(threshold)
            
            logger.info(f"Created {threshold_type} threshold for user {user_id}: {threshold_value}")
            
            return {
                "success": True,
                "threshold": self._threshold_to_dict(threshold),
                "message": f"Threshold created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating threshold: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_thresholds(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        threshold_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all thresholds for a user or organization
        """
        try:
            query = self.db.query(CreditThreshold)
            
            # Apply filters
            if organization_id:
                query = query.filter(
                    or_(
                        and_(CreditThreshold.user_id == user_id, CreditThreshold.organization_id.is_(None)),
                        and_(CreditThreshold.user_id == user_id, CreditThreshold.organization_id == organization_id),
                        and_(CreditThreshold.user_id.is_(None), CreditThreshold.organization_id == organization_id)
                    )
                )
            else:
                query = query.filter(
                    or_(
                        CreditThreshold.user_id == user_id,
                        and_(CreditThreshold.user_id.is_(None), CreditThreshold.organization_id.is_(None))
                    )
                )
            
            if threshold_type:
                query = query.filter(CreditThreshold.threshold_type == threshold_type)
            
            if is_active is not None:
                query = query.filter(CreditThreshold.is_active == is_active)
            
            thresholds = query.order_by(desc(CreditThreshold.created_at)).all()
            
            return [self._threshold_to_dict(threshold) for threshold in thresholds]
            
        except Exception as e:
            logger.error(f"Error getting user thresholds: {str(e)}")
            return []
    
    def update_threshold(
        self,
        threshold_id: int,
        user_id: int,
        **updates
    ) -> Dict[str, Any]:
        """
        Update an existing threshold
        """
        try:
            threshold = self.db.query(CreditThreshold).filter(
                and_(
                    CreditThreshold.id == threshold_id,
                    CreditThreshold.user_id == user_id
                )
            ).first()
            
            if not threshold:
                return {
                    "success": False,
                    "error": "Threshold not found"
                }
            
            # Validate updates
            if "threshold_value" in updates:
                if not updates["threshold_value"] or updates["threshold_value"] <= 0:
                    raise ValueError("Threshold value must be positive")
            
            if "percentage" in updates:
                if updates["percentage"] and (updates["percentage"] <= 0 or updates["percentage"] > 100):
                    raise ValueError("Percentage must be between 0 and 100")
            
            # Update allowed fields
            allowed_fields = [
                "threshold_value", "percentage", "severity", "notification_channels", "is_active"
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(threshold, field, value)
            
            threshold.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(threshold)
            
            logger.info(f"Updated threshold {threshold_id} for user {user_id}")
            
            return {
                "success": True,
                "threshold": self._threshold_to_dict(threshold),
                "message": "Threshold updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating threshold: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_threshold(self, threshold_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete a threshold
        """
        try:
            threshold = self.db.query(CreditThreshold).filter(
                and_(
                    CreditThreshold.id == threshold_id,
                    CreditThreshold.user_id == user_id
                )
            ).first()
            
            if not threshold:
                return {
                    "success": False,
                    "error": "Threshold not found"
                }
            
            self.db.delete(threshold)
            self.db.commit()
            
            logger.info(f"Deleted threshold {threshold_id} for user {user_id}")
            
            return {
                "success": True,
                "message": "Threshold deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting threshold: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_thresholds(
        self,
        user_id: int,
        organization_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Check all thresholds for a user and return triggered ones
        """
        triggered_thresholds = []
        
        try:
            # Get active thresholds
            thresholds = self.get_user_thresholds(user_id, organization_id, is_active=True)
            
            if not thresholds:
                return triggered_thresholds
            
            # Get current balance information
            balance_status = self.credit_manager.get_balance(user_id, organization_id)
            
            if not balance_status or not balance_status.get("has_balance"):
                return triggered_thresholds
            
            balance = balance_status["balance_details"]
            available_credits = balance["available_credits"]
            total_credits = balance["total_credits"]
            
            # Get recent usage for spike detection
            usage_stats = self.analytics_service.get_recent_usage_stats(
                user_id, organization_id, days=7
            )
            
            for threshold in thresholds:
                is_triggered = False
                trigger_reason = None
                
                if threshold["threshold_type"] == "low_balance":
                    if available_credits <= threshold["threshold_value"]:
                        is_triggered = True
                        trigger_reason = f"Balance ({available_credits}) below threshold ({threshold['threshold_value']})"
                
                elif threshold["threshold_type"] == "high_spend":
                    # Check daily/weekly/monthly spending
                    daily_spend = usage_stats.get("daily_average", 0)
                    if daily_spend >= threshold["threshold_value"]:
                        is_triggered = True
                        trigger_reason = f"Daily spend ({daily_spend}) above threshold ({threshold['threshold_value']})"
                
                elif threshold["threshold_type"] == "usage_spike":
                    # Check for unusual usage patterns
                    if "spike_detected" in usage_stats and usage_stats["spike_detected"]:
                        is_triggered = True
                        trigger_reason = "Usage spike detected"
                
                elif threshold["threshold_type"] == "expiration_warning":
                    # Check for expiring credits
                    if "expiring_credits" in usage_stats and usage_stats["expiring_credits"] > 0:
                        if available_credits <= threshold["threshold_value"]:
                            is_triggered = True
                            trigger_reason = f"Credits expiring soon with low balance"
                
                if is_triggered:
                    triggered_thresholds.append({
                        "threshold": threshold,
                        "trigger_reason": trigger_reason,
                        "current_value": available_credits,
                        "triggered_at": datetime.utcnow()
                    })
            
            return triggered_thresholds
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}")
            return triggered_thresholds
    
    def get_threshold_statistics(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get threshold usage statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get threshold creation stats
            thresholds = self.get_user_thresholds(user_id, organization_id)
            total_thresholds = len(thresholds)
            active_thresholds = len([t for t in thresholds if t["is_active"]])
            
            # Get threshold type distribution
            type_distribution = {}
            severity_distribution = {}
            
            for threshold in thresholds:
                t_type = threshold["threshold_type"]
                severity = threshold["severity"]
                
                type_distribution[t_type] = type_distribution.get(t_type, 0) + 1
                severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            
            # Get alert statistics
            alert_stats = self.db.query(CreditAlert).filter(
                and_(
                    CreditAlert.user_id == user_id,
                    CreditAlert.created_at >= start_date
                )
            ).all()
            
            total_alerts = len(alert_stats)
            resolved_alerts = len([a for a in alert_stats if a.resolved_at is not None])
            
            return {
                "total_thresholds": total_thresholds,
                "active_thresholds": active_thresholds,
                "type_distribution": type_distribution,
                "severity_distribution": severity_distribution,
                "alert_statistics": {
                    "total_alerts": total_alerts,
                    "resolved_alerts": resolved_alerts,
                    "resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
                },
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting threshold statistics: {str(e)}")
            return {}
    
    def setup_default_thresholds(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        profile: str = "conservative"
    ) -> List[Dict[str, Any]]:
        """
        Set up default thresholds based on user profile
        """
        try:
            # Define default thresholds by profile
            default_thresholds = {
                "conservative": [
                    {
                        "threshold_type": "low_balance",
                        "threshold_value": Decimal("1000"),
                        "severity": "high",
                        "notification_channels": ["email", "push"]
                    },
                    {
                        "threshold_type": "high_spend",
                        "threshold_value": Decimal("500"),
                        "severity": "medium",
                        "notification_channels": ["email"]
                    }
                ],
                "moderate": [
                    {
                        "threshold_type": "low_balance",
                        "threshold_value": Decimal("500"),
                        "severity": "medium",
                        "notification_channels": ["email"]
                    },
                    {
                        "threshold_type": "usage_spike",
                        "severity": "medium",
                        "notification_channels": ["push"]
                    }
                ],
                "aggressive": [
                    {
                        "threshold_type": "low_balance",
                        "threshold_value": Decimal("100"),
                        "severity": "critical",
                        "notification_channels": ["email", "sms", "push"]
                    }
                ]
            }
            
            if profile not in default_thresholds:
                profile = "moderate"
            
            created_thresholds = []
            
            for threshold_config in default_thresholds[profile]:
                result = self.create_threshold(
                    user_id=user_id,
                    organization_id=organization_id,
                    **threshold_config
                )
                
                if result["success"]:
                    created_thresholds.append(result["threshold"])
            
            logger.info(f"Created {len(created_thresholds)} default thresholds for user {user_id} with profile {profile}")
            
            return created_thresholds
            
        except Exception as e:
            logger.error(f"Error setting up default thresholds: {str(e)}")
            return []
    
    def _threshold_to_dict(self, threshold: CreditThreshold) -> Dict[str, Any]:
        """
        Convert threshold model to dictionary
        """
        return {
            "id": threshold.id,
            "user_id": threshold.user_id,
            "organization_id": threshold.organization_id,
            "threshold_type": threshold.threshold_type,
            "threshold_value": float(threshold.threshold_value) if threshold.threshold_value else None,
            "percentage": float(threshold.percentage) if threshold.percentage else None,
            "severity": threshold.severity,
            "notification_channels": threshold.notification_channels,
            "is_active": threshold.is_active,
            "created_by": threshold.created_by,
            "created_at": threshold.created_at.isoformat() if threshold.created_at else None,
            "updated_at": threshold.updated_at.isoformat() if threshold.updated_at else None
        }