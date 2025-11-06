"""
Usage Tracking Initialization Script

Initializes default usage quotas for subscriptions based on subscription plans.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List
import logging

from app.models.usage import UsageQuota, UsageMetricType, UsageThreshold
from app.models.billing import Subscription, SubscriptionPlan
from app.models.license import LicenseTier

logger = logging.getLogger(__name__)


def initialize_usage_quotas_for_subscription(
    db: Session,
    subscription_id: int
) -> List[UsageQuota]:
    """
    Initialize usage quotas when a subscription is created
    
    Args:
        db: Database session
        subscription_id: ID of the new subscription
    
    Returns:
        List of created UsageQuota objects
    """
    # Get subscription and plan details
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()
    
    if not subscription:
        logger.error(f"Subscription {subscription_id} not found")
        return []
    
    plan = subscription.plan
    if not plan:
        logger.error(f"Plan not found for subscription {subscription_id}")
        return []
    
    # Define quota mappings based on subscription plan
    quotas_config = {
        "Basic": {
            UsageMetricType.DOCUMENT_PROCESSING: {
                "limit": plan.max_documents_per_month or 100,
                "allow_overage": True,
                "overage_limit": 50,
                "overage_rate": 0.50  # €0.50 per document
            },
            UsageMetricType.API_CALLS: {
                "limit": plan.max_api_calls_per_month or 1000,
                "allow_overage": True,
                "overage_limit": 500,
                "overage_rate": 0.01  # €0.01 per 10 calls
            },
            UsageMetricType.STORAGE_USAGE: {
                "limit": 5.0,  # 5 GB
                "allow_overage": True,
                "overage_limit": 2.0,
                "overage_rate": 2.00  # €2.00 per GB
            },
            UsageMetricType.USER_SESSIONS: {
                "limit": plan.max_users or 3,
                "allow_overage": False,
                "overage_limit": 0,
                "overage_rate": 0
            }
        },
        "Professional": {
            UsageMetricType.DOCUMENT_PROCESSING: {
                "limit": plan.max_documents_per_month or 500,
                "allow_overage": True,
                "overage_limit": 200,
                "overage_rate": 0.40
            },
            UsageMetricType.API_CALLS: {
                "limit": plan.max_api_calls_per_month or 10000,
                "allow_overage": True,
                "overage_limit": 5000,
                "overage_rate": 0.008
            },
            UsageMetricType.STORAGE_USAGE: {
                "limit": 50.0,  # 50 GB
                "allow_overage": True,
                "overage_limit": 20.0,
                "overage_rate": 1.50
            },
            UsageMetricType.USER_SESSIONS: {
                "limit": plan.max_users or 10,
                "allow_overage": True,
                "overage_limit": 5,
                "overage_rate": 5.00  # €5.00 per user
            }
        },
        "Enterprise": {
            UsageMetricType.DOCUMENT_PROCESSING: {
                "limit": plan.max_documents_per_month or 5000,
                "allow_overage": True,
                "overage_limit": 2000,
                "overage_rate": 0.30
            },
            UsageMetricType.API_CALLS: {
                "limit": plan.max_api_calls_per_month or 100000,
                "allow_overage": True,
                "overage_limit": 50000,
                "overage_rate": 0.005
            },
            UsageMetricType.STORAGE_USAGE: {
                "limit": 500.0,  # 500 GB
                "allow_overage": True,
                "overage_limit": 200.0,
                "overage_rate": 1.00
            },
            UsageMetricType.USER_SESSIONS: {
                "limit": plan.max_users or 100,
                "allow_overage": True,
                "overage_limit": 50,
                "overage_rate": 4.00
            }
        }
    }
    
    # Determine plan tier
    plan_tier = plan.name
    if plan_tier not in quotas_config:
        # Default to Basic if plan not recognized
        plan_tier = "Basic"
        logger.warning(f"Unknown plan '{plan.name}', using Basic tier defaults")
    
    created_quotas = []
    
    # Create quotas for each metric
    for metric_type, config in quotas_config[plan_tier].items():
        quota = UsageQuota(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            metric_type=metric_type,
            quota_limit=config["limit"],
            unit=_get_unit_for_metric(metric_type),
            current_usage=0,
            usage_percentage=0,
            allow_overage=config["allow_overage"],
            overage_limit=config["overage_limit"],
            overage_rate=config["overage_rate"],
            current_overage=0,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            reset_schedule="monthly",
            last_reset_at=datetime.utcnow(),
            next_reset_at=subscription.current_period_end,
            is_active=True,
            is_exceeded=False
        )
        
        db.add(quota)
        created_quotas.append(quota)
    
    db.commit()
    
    logger.info(
        f"Created {len(created_quotas)} usage quotas for subscription {subscription_id} "
        f"(Plan: {plan_tier})"
    )
    
    # Create default usage thresholds for alerts
    _create_default_thresholds(db, subscription, created_quotas)
    
    return created_quotas


def _create_default_thresholds(
    db: Session,
    subscription: Subscription,
    quotas: List[UsageQuota]
):
    """Create default alert thresholds for quotas"""
    
    default_thresholds = [
        {"percentage": 80, "severity": "medium"},
        {"percentage": 90, "severity": "high"},
        {"percentage": 100, "severity": "critical"}
    ]
    
    for quota in quotas:
        for threshold_config in default_thresholds:
            threshold = UsageThreshold(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                metric_type=quota.metric_type,
                threshold_type="percentage",
                threshold_value=threshold_config["percentage"],
                alert_enabled=True,
                alert_severity=threshold_config["severity"],
                notification_channels=["email"],  # Default to email notifications
                cooldown_minutes=60,  # Don't send duplicate alerts within 1 hour
                auto_action=None,
                is_active=True
            )
            
            db.add(threshold)
    
    db.commit()
    
    logger.info(
        f"Created default alert thresholds for subscription {subscription.id}"
    )


def _get_unit_for_metric(metric_type: str) -> str:
    """Get the unit for a metric type"""
    units = {
        UsageMetricType.DOCUMENT_PROCESSING: "documents",
        UsageMetricType.DOCUMENT_PAGES: "pages",
        UsageMetricType.API_CALLS: "calls",
        UsageMetricType.STORAGE_USAGE: "GB",
        UsageMetricType.USER_SESSIONS: "users",
        UsageMetricType.BATCH_OPERATIONS: "batches",
        UsageMetricType.EXPORT_OPERATIONS: "exports",
        UsageMetricType.OCR_OPERATIONS: "operations",
        UsageMetricType.LLM_OPERATIONS: "operations",
        UsageMetricType.DATABASE_QUERIES: "queries",
        UsageMetricType.BANDWIDTH_USAGE: "GB"
    }
    return units.get(metric_type, "units")


def update_quotas_for_subscription_renewal(
    db: Session,
    subscription_id: int
):
    """
    Update quotas when a subscription renews
    
    Resets usage and extends the period
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()
    
    if not subscription:
        logger.error(f"Subscription {subscription_id} not found")
        return
    
    # Get existing quotas
    quotas = db.query(UsageQuota).filter(
        UsageQuota.subscription_id == subscription_id,
        UsageQuota.is_active == True
    ).all()
    
    if not quotas:
        # No quotas exist, create them
        logger.info(f"No quotas found for subscription {subscription_id}, creating...")
        initialize_usage_quotas_for_subscription(db, subscription_id)
        return
    
    # Reset all quotas
    for quota in quotas:
        quota.current_usage = 0
        quota.usage_percentage = 0
        quota.current_overage = 0
        quota.is_exceeded = False
        quota.exceeded_at = None
        quota.period_start = subscription.current_period_start
        quota.period_end = subscription.current_period_end
        quota.last_reset_at = datetime.utcnow()
        quota.next_reset_at = subscription.current_period_end
    
    db.commit()
    
    logger.info(f"Reset {len(quotas)} quotas for subscription {subscription_id} renewal")


def cleanup_expired_quotas(db: Session):
    """
    Cleanup quotas for expired or cancelled subscriptions
    """
    # Deactivate quotas for expired subscriptions
    from sqlalchemy import and_
    
    quotas = db.query(UsageQuota).join(Subscription).filter(
        and_(
            UsageQuota.is_active == True,
            Subscription.status.in_(["canceled", "expired"])
        )
    ).all()
    
    for quota in quotas:
        quota.is_active = False
    
    db.commit()
    
    logger.info(f"Deactivated {len(quotas)} quotas for expired subscriptions")


if __name__ == "__main__":
    from app.db.session import SessionLocal
    
    print("=" * 60)
    print("Usage Tracking Initialization")
    print("=" * 60)
    print()
    
    db = SessionLocal()
    
    try:
        # Example: Initialize quotas for all active subscriptions without quotas
        subscriptions = db.query(Subscription).filter(
            Subscription.status == "active"
        ).all()
        
        print(f"Found {len(subscriptions)} active subscriptions")
        print()
        
        for subscription in subscriptions:
            # Check if quotas already exist
            existing_quotas = db.query(UsageQuota).filter(
                UsageQuota.subscription_id == subscription.id,
                UsageQuota.is_active == True
            ).count()
            
            if existing_quotas == 0:
                print(f"Creating quotas for subscription {subscription.id}...")
                quotas = initialize_usage_quotas_for_subscription(db, subscription.id)
                print(f"  Created {len(quotas)} quotas")
            else:
                print(f"Subscription {subscription.id} already has {existing_quotas} quotas")
        
        print()
        print("=" * 60)
        print("Initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()
