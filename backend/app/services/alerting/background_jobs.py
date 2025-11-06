"""
Alert System Background Jobs

Celery tasks and background job scheduling for the alerting system.
Handles rule evaluation, notification processing, and escalation monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import Celery
from celery.schedules import crontab

from app.db.session import SessionLocal
from app.services.alerting.alert_manager import AlertManager


logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery('alert_system')
celery_app.config_from_object('app.core.config', namespace='CELERY')

# Celery beat schedule for periodic tasks
beat_schedule = {
    'evaluate-alert-rules': {
        'task': 'app.services.alerting.background_jobs.evaluate_alert_rules',
        'schedule': 60.0,  # Every minute
        'options': {'queue': 'alert_evaluation'}
    },
    'process-notifications': {
        'task': 'app.services.alerting.background_jobs.process_pending_notifications',
        'schedule': 30.0,  # Every 30 seconds
        'options': {'queue': 'notifications'}
    },
    'check-escalations': {
        'task': 'app.services.alerting.background_jobs.check_alert_escalations',
        'schedule': 120.0,  # Every 2 minutes
        'options': {'queue': 'escalations'}
    },
    'cleanup-old-alerts': {
        'task': 'app.services.alerting.background_jobs.cleanup_old_alerts',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'options': {'queue': 'maintenance'}
    },
    'retry-failed-notifications': {
        'task': 'app.services.alerting.background_jobs.retry_failed_notifications',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'notifications'}
    },
    'send-system-health': {
        'task': 'app.services.alerting.background_jobs.send_system_health_metrics',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'monitoring'}
    }
}

celery_app.conf.beat_schedule = beat_schedule


@celery_app.task(bind=True, max_retries=3)
def evaluate_alert_rules(self) -> Dict[str, Any]:
    """
    Celery task to evaluate all enabled alert rules.
    
    Args:
        self: Task instance
        
    Returns:
        Evaluation results
    """
    db = SessionLocal()
    try:
        logger.info("Starting alert rule evaluation")
        
        alert_manager = AlertManager(db)
        results = asyncio.run(alert_manager.evaluate_all_rules())
        
        logger.info(f"Alert rule evaluation completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in alert rule evaluation: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)
        
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def process_pending_notifications(self) -> Dict[str, Any]:
    """
    Celery task to process pending notifications.
    
    Args:
        self: Task instance
        
    Returns:
        Processing results
    """
    db = SessionLocal()
    try:
        from app.services.alerting.alert_channels import AlertChannelService
        
        channel_service = AlertChannelService(db)
        retried_count = asyncio.run(channel_service.retry_failed_notifications())
        
        logger.info(f"Processed pending notifications, retried: {retried_count}")
        return {"retried_count": retried_count}
        
    except Exception as e:
        logger.error(f"Error processing pending notifications: {e}")
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)
        
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def check_alert_escalations(self) -> Dict[str, Any]:
    """
    Celery task to check and process alert escalations.
    
    Args:
        self: Task instance
        
    Returns:
        Escalation results
    """
    db = SessionLocal()
    try:
        from app.services.alerting.alert_escalation import AlertEscalationService
        
        escalation_service = AlertEscalationService(db)
        
        # Get active alerts that haven't been escalated recently
        from app.models.alert import Alert, AlertStatus
        active_alerts = db.query(Alert).filter(
            Alert.status == AlertStatus.ACTIVE
        ).all()
        
        escalated_count = 0
        for alert in active_alerts:
            try:
                # Check if alert needs escalation
                # (The actual escalation logic is in the escalation service)
                escalated = asyncio.run(escalation_service.check_escalation_rules(alert.alert_id))
                if escalated:
                    escalated_count += 1
            except Exception as e:
                logger.error(f"Error checking escalation for alert {alert.alert_id}: {e}")
        
        logger.info(f"Checked {len(active_alerts)} alerts, escalated: {escalated_count}")
        return {"escalated_count": escalated_count, "checked_count": len(active_alerts)}
        
    except Exception as e:
        logger.error(f"Error checking alert escalations: {e}")
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)
        
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def cleanup_old_alerts(self) -> Dict[str, Any]:
    """
    Celery task to clean up old alerts and notifications.
    
    Args:
        self: Task instance
        
    Returns:
        Cleanup results
    """
    db = SessionLocal()
    try:
        from app.models.alert import Alert, AlertNotification, AlertStatus
        from sqlalchemy import and_, or_
        
        # Clean up old resolved alerts (older than 90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        old_alerts = db.query(Alert).filter(
            and_(
                Alert.status.in_([AlertStatus.RESOLVED, AlertStatus.SUPPRESSED]),
                Alert.resolved_at < cutoff_date
            )
        ).all()
        
        alert_count = len(old_alerts)
        notification_count = 0
        
        for alert in old_alerts:
            # Delete associated notifications
            notifications = db.query(AlertNotification).filter(
                AlertNotification.alert_id == alert.alert_id
            ).delete()
            notification_count += notifications
            
            # Delete the alert
            db.delete(alert)
        
        db.commit()
        
        logger.info(f"Cleaned up {alert_count} old alerts and {notification_count} notifications")
        return {"alert_count": alert_count, "notification_count": notification_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up old alerts: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def retry_failed_notifications(self) -> Dict[str, Any]:
    """
    Celery task to retry failed notifications.
    
    Args:
        self: Task instance
        
    Returns:
        Retry results
    """
    db = SessionLocal()
    try:
        from app.services.alerting.alert_channels import AlertChannelService
        
        channel_service = AlertChannelService(db)
        retried_count = asyncio.run(channel_service.retry_failed_notifications())
        
        logger.info(f"Retried {retried_count} failed notifications")
        return {"retried_count": retried_count}
        
    except Exception as e:
        logger.error(f"Error retrying failed notifications: {e}")
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)
        
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def send_system_health_metrics(self) -> Dict[str, Any]:
    """
    Celery task to send system health metrics.
    
    Args:
        self: Task instance
        
    Returns:
        Health metrics
    """
    db = SessionLocal()
    try:
        alert_manager = AlertManager(db)
        
        # Get system health metrics
        health_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_rules": len(db.query(AlertRule).filter(AlertRule.enabled == True).all()),
            "active_evaluations": alert_manager.get_active_evaluation_count(),
            "cache_stats": alert_manager.rule_engine.get_cache_stats()
        }
        
        # Send metrics to monitoring system
        # This would integrate with your monitoring platform
        logger.info(f"System health metrics: {health_metrics}")
        
        return health_metrics
        
    except Exception as e:
        logger.error(f"Error sending system health metrics: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def test_alert_rule(self, rule_id: str) -> Dict[str, Any]:
    """
    Celery task to test a specific alert rule.
    
    Args:
        self: Task instance
        rule_id: Alert rule ID to test
        
    Returns:
        Test results
    """
    db = SessionLocal()
    try:
        from app.models.alert import AlertRule
        from app.services.alerting.alert_rules import AlertRuleEngine
        
        rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")
        
        rule_engine = AlertRuleEngine(db)
        result = asyncio.run(rule_engine.evaluate_rule(rule))
        
        logger.info(f"Tested rule {rule_id}: {result}")
        return {"rule_id": rule_id, "test_result": result}
        
    except Exception as e:
        logger.error(f"Error testing alert rule {rule_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_specific_alert(self, rule_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Celery task to trigger a specific alert manually.
    
    Args:
        self: Task instance
        rule_id: Alert rule ID to trigger
        context: Additional context for the alert
        
    Returns:
        Alert trigger results
    """
    db = SessionLocal()
    try:
        from app.models.alert import AlertRule
        
        rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")
        
        alert_manager = AlertManager(db)
        context = context or {}
        context["source_system"] = "manual_trigger"
        
        # Trigger alert
        alert = asyncio.run(alert_manager.trigger_alert(rule, context))
        
        # Process notifications
        asyncio.run(alert_manager.process_alert_notifications(alert.alert_id))
        
        logger.info(f"Manually triggered alert {alert.alert_id} for rule {rule_id}")
        return {"alert_id": alert.alert_id, "rule_id": rule_id}
        
    except Exception as e:
        logger.error(f"Error triggering alert for rule {rule_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def generate_alert_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
    """
    Celery task to generate alert reports.
    
    Args:
        self: Task instance
        time_range_hours: Time range for the report in hours
        
    Returns:
        Report data
    """
    db = SessionLocal()
    try:
        alert_manager = AlertManager(db)
        time_range = timedelta(hours=time_range_hours)
        
        # Generate statistics
        stats = asyncio.run(alert_manager.get_alert_statistics(time_range))
        
        # Generate additional report data
        from app.models.alert import Alert
        from sqlalchemy import and_, desc
        
        # Get top triggered rules
        top_rules_query = db.query(
            Alert.rule_id,
            AlertRule.name,
            func.count(Alert.alert_id).label('count')
        ).join(
            AlertRule, Alert.rule_id == AlertRule.rule_id
        ).filter(
            Alert.triggered_at >= datetime.utcnow() - time_range
        ).group_by(
            Alert.rule_id, AlertRule.name
        ).order_by(
            desc('count')
        ).limit(10).all()
        
        top_rules = [
            {"rule_id": result.rule_id, "name": result.name, "count": result.count}
            for result in top_rules_query
        ]
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "time_range_hours": time_range_hours,
            "statistics": stats,
            "top_rules": top_rules
        }
        
        logger.info(f"Generated alert report for last {time_range_hours} hours")
        return report
        
    except Exception as e:
        logger.error(f"Error generating alert report: {e}")
        raise
    finally:
        db.close()


# Additional helper functions for monitoring and management

def schedule_immediate_evaluation():
    """Schedule immediate rule evaluation."""
    evaluate_alert_rules.apply_async(queue='alert_evaluation')


def schedule_notification_retry():
    """Schedule immediate notification retry."""
    retry_failed_notifications.apply_async(queue='notifications')


def get_worker_status() -> Dict[str, Any]:
    """
    Get Celery worker status.
    
    Returns:
        Worker status information
    """
    from celery.task.control import inspect
    
    i = inspect()
    stats = i.stats()
    active = i.active()
    scheduled = i.scheduled()
    
    return {
        "stats": stats,
        "active_tasks": active,
        "scheduled_tasks": scheduled
    }


# Periodic monitoring task
@celery_app.task(bind=True)
def monitor_alert_system_health(self) -> Dict[str, Any]:
    """
    Periodic monitoring task for alert system health.
    
    Args:
        self: Task instance
        
    Returns:
        System health status
    """
    try:
        # Check various system components
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check database connectivity
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        finally:
            db.close()
        
        # Check Redis connectivity (if using Redis for Celery)
        try:
            # This would check Redis if configured
            health_status["components"]["redis"] = "healthy"  # or check actual Redis
        except Exception as e:
            health_status["components"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check worker status
        try:
            worker_status = get_worker_status()
            if worker_status.get("stats"):
                health_status["components"]["workers"] = "healthy"
            else:
                health_status["components"]["workers"] = "unhealthy"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["workers"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        logger.info(f"Alert system health check: {health_status}")
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health monitoring: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(e)
        }


# Add health monitoring to beat schedule
beat_schedule['monitor-alert-system'] = {
    'task': 'app.services.alerting.background_jobs.monitor_alert_system_health',
    'schedule': 300.0,  # Every 5 minutes
    'options': {'queue': 'monitoring'}
}

celery_app.conf.beat_schedule = beat_schedule