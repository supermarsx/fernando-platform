"""
Alert API Endpoints

REST API for managing alerts, alert rules, notifications, and escalation.
Provides comprehensive CRUD operations and real-time capabilities.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.alert import Alert, AlertRule, AlertStatus, AlertSeverity, AlertType, AlertTemplate
from app.models.user import User
from app.schemas.alert_schemas import (
    AlertResponse, AlertCreate, AlertUpdate,
    AlertRuleResponse, AlertRuleCreate, AlertRuleUpdate,
    AlertTemplateResponse, AlertTemplateCreate, AlertTemplateUpdate,
    AlertAcknowledgment, AlertResolution,
    AlertStatistics, AlertRuleStatistics, AlertSystemHealth,
    AlertFilter, AlertRuleFilter, BulkAlertAction
)
from app.services.alerting.alert_manager import AlertManager


router = APIRouter()


# Alert Management Endpoints

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of alerts to return"),
    status_filter: Optional[List[AlertStatus]] = Query(None, description="Filter by status"),
    severity_filter: Optional[List[AlertSeverity]] = Query(None, description="Filter by severity"),
    alert_type_filter: Optional[List[AlertType]] = Query(None, description="Filter by type"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    triggered_after: Optional[datetime] = Query(None, description="Filter by trigger time (after)"),
    triggered_before: Optional[datetime] = Query(None, description="Filter by trigger time (before)"),
    search: Optional[str] = Query(None, description="Search in title and message"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AlertResponse]:
    """
    Get alerts with optional filtering and pagination.
    """
    try:
        query = db.query(Alert)
        
        # Apply filters
        if status_filter:
            query = query.filter(Alert.status.in_(status_filter))
        
        if severity_filter:
            query = query.filter(Alert.severity.in_(severity_filter))
        
        if alert_type_filter:
            query = query.filter(Alert.alert_type.in_(alert_type_filter))
        
        if rule_id:
            query = query.filter(Alert.rule_id == rule_id)
        
        if triggered_after:
            query = query.filter(Alert.triggered_at >= triggered_after)
        
        if triggered_before:
            query = query.filter(Alert.triggered_at <= triggered_before)
        
        if search:
            search_filter = or_(
                Alert.title.ilike(f"%{search}%"),
                Alert.message.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Apply pagination
        alerts = query.order_by(desc(Alert.triggered_at)).offset(skip).limit(limit).all()
        
        return [AlertResponse.model_validate(alert) for alert in alerts]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alerts: {str(e)}"
        )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertResponse:
    """
    Get a specific alert by ID.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertResponse.model_validate(alert)


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertResponse:
    """
    Create a new alert manually.
    """
    try:
        # Create alert manually (not from rule)
        alert = Alert(
            rule_id=alert_data.rule_id,
            status=AlertStatus.ACTIVE,
            severity=alert_data.severity,
            alert_type=alert_data.alert_type,
            title=alert_data.title,
            description=alert_data.description,
            message=alert_data.message,
            context=alert_data.context,
            metric_value=alert_data.metric_value,
            threshold_value=alert_data.threshold_value,
            labels=alert_data.labels,
            dedup_key=alert_data.dedup_key,
            runbook_url=alert_data.runbook_url,
            source_system=alert_data.source_system or "manual"
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        # Process notifications in background
        if alert.rule_id:
            background_tasks.add_task(
                process_alert_notifications_background,
                alert.alert_id
            )
        
        return AlertResponse.model_validate(alert)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating alert: {str(e)}"
        )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertResponse:
    """
    Update an existing alert.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    try:
        # Update allowed fields
        update_data = alert_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(alert, field):
                setattr(alert, field, value)
        
        alert.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        
        return AlertResponse.model_validate(alert)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating alert: {str(e)}"
        )


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledgment: AlertAcknowledgment,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Acknowledge an alert.
    """
    alert_manager = AlertManager(db)
    
    success = await alert_manager.acknowledge_alert(
        alert_id=alert_id,
        user_id=current_user.user_id,
        note=acknowledgment.note
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to acknowledge alert. It may not be active or may not exist."
        )
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution: AlertResolution,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Resolve an alert.
    """
    alert_manager = AlertManager(db)
    
    success = await alert_manager.resolve_alert(
        alert_id=alert_id,
        user_id=current_user.user_id,
        resolution_notes=resolution.resolution_notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve alert. It may already be resolved or may not exist."
        )
    
    return {"message": "Alert resolved successfully"}


@router.post("/{alert_id}/suppress")
async def suppress_alert(
    alert_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Suppress an alert temporarily.
    """
    alert_manager = AlertManager(db)
    
    success = await alert_manager.suppress_alert(alert_id, "Manually suppressed")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to suppress alert. It may already be suppressed or may not exist."
        )
    
    return {"message": "Alert suppressed successfully"}


@router.post("/bulk_action")
async def bulk_alert_action(
    bulk_action: BulkAlertAction,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform bulk actions on multiple alerts.
    """
    alert_manager = AlertManager(db)
    
    # Get all alerts
    alerts = db.query(Alert).filter(Alert.alert_id.in_(bulk_action.alert_ids)).all()
    
    if len(alerts) != len(bulk_action.alert_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some alerts not found"
        )
    
    results = {"successful": [], "failed": []}
    
    for alert in alerts:
        try:
            if bulk_action.action == "acknowledge":
                success = await alert_manager.acknowledge_alert(
                    alert.alert_id, current_user.user_id, bulk_action.notes
                )
            elif bulk_action.action == "resolve":
                success = await alert_manager.resolve_alert(
                    alert.alert_id, current_user.user_id, bulk_action.notes
                )
            elif bulk_action.action == "suppress":
                success = await alert_manager.suppress_alert(alert.alert_id, bulk_action.notes)
            else:
                results["failed"].append({"alert_id": alert.alert_id, "error": "Unknown action"})
                continue
            
            if success:
                results["successful"].append(alert.alert_id)
            else:
                results["failed"].append({"alert_id": alert.alert_id, "error": "Action failed"})
                
        except Exception as e:
            results["failed"].append({"alert_id": alert.alert_id, "error": str(e)})
    
    return {
        "message": f"Bulk {bulk_action.action} completed",
        "results": results,
        "total_processed": len(bulk_action.alert_ids)
    }


# Alert Rules Endpoints

@router.get("/rules/", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    alert_type_filter: Optional[List[AlertType]] = Query(None),
    severity_filter: Optional[List[AlertSeverity]] = Query(None),
    enabled_filter: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AlertRuleResponse]:
    """
    Get alert rules with optional filtering.
    """
    try:
        query = db.query(AlertRule)
        
        # Apply filters
        if alert_type_filter:
            query = query.filter(AlertRule.alert_type.in_(alert_type_filter))
        
        if severity_filter:
            query = query.filter(AlertRule.severity.in_(severity_filter))
        
        if enabled_filter is not None:
            query = query.filter(AlertRule.enabled == enabled_filter)
        
        if search:
            search_filter = or_(
                AlertRule.name.ilike(f"%{search}%"),
                AlertRule.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Apply pagination
        rules = query.order_by(desc(AlertRule.created_at)).offset(skip).limit(limit).all()
        
        # Add alert count to each rule
        rule_responses = []
        for rule in rules:
            alert_count = db.query(Alert).filter(Alert.rule_id == rule.rule_id).count()
            rule_dict = AlertRuleResponse.model_validate(rule).model_dump()
            rule_dict["alert_count"] = alert_count
            rule_responses.append(AlertRuleResponse(**rule_dict))
        
        return rule_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert rules: {str(e)}"
        )


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertRuleResponse:
    """
    Get a specific alert rule by ID.
    """
    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    return AlertRuleResponse.model_validate(rule)


@router.post("/rules/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertRuleResponse:
    """
    Create a new alert rule.
    """
    try:
        rule = AlertRule(
            name=rule_data.name,
            description=rule_data.description,
            alert_type=rule_data.alert_type,
            severity=rule_data.severity,
            condition=rule_data.condition,
            threshold_config=rule_data.threshold_config,
            query_config=rule_data.query_config,
            channels=rule_data.channels,
            recipients=rule_data.recipients,
            enabled=rule_data.enabled,
            evaluation_frequency=rule_data.evaluation_frequency,
            sustained_duration=rule_data.sustained_duration,
            cooldown_period=rule_data.cooldown_period,
            escalation_rules=rule_data.escalation_rules,
            tags=rule_data.tags,
            metadata=rule_data.metadata,
            created_by=current_user.user_id
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return AlertRuleResponse.model_validate(rule)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating alert rule: {str(e)}"
        )


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    rule_update: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertRuleResponse:
    """
    Update an existing alert rule.
    """
    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    try:
        # Update allowed fields
        update_data = rule_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(rule, field):
                setattr(rule, field, value)
        
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        
        return AlertRuleResponse.model_validate(rule)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating alert rule: {str(e)}"
        )


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Delete an alert rule.
    """
    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    try:
        # Check if rule has active alerts
        active_alerts = db.query(Alert).filter(
            and_(
                Alert.rule_id == rule_id,
                Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
            )
        ).count()
        
        if active_alerts > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete rule with {active_alerts} active alerts"
            )
        
        db.delete(rule)
        db.commit()
        
        return {"message": "Alert rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting alert rule: {str(e)}"
        )


@router.post("/rules/{rule_id}/test")
async def test_alert_rule(
    rule_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test an alert rule evaluation.
    """
    rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    try:
        from app.services.alerting.alert_rules import AlertRuleEngine
        
        rule_engine = AlertRuleEngine(db)
        result = await rule_engine.evaluate_rule(rule)
        
        return {
            "rule_id": rule_id,
            "test_result": result,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing alert rule: {str(e)}"
        )


# Statistics and Analytics Endpoints

@router.get("/statistics", response_model=AlertStatistics)
async def get_alert_statistics(
    time_range_hours: int = Query(24, ge=1, le=720, description="Time range in hours"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertStatistics:
    """
    Get alert statistics for the specified time range.
    """
    try:
        time_range = timedelta(hours=time_range_hours)
        alert_manager = AlertManager(db)
        stats = await alert_manager.get_alert_statistics(time_range)
        
        return AlertStatistics(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert statistics: {str(e)}"
        )


@router.get("/rules/statistics", response_model=AlertRuleStatistics)
async def get_alert_rule_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertRuleStatistics:
    """
    Get alert rule statistics.
    """
    try:
        total_rules = db.query(AlertRule).count()
        enabled_rules = db.query(AlertRule).filter(AlertRule.enabled == True).count()
        disabled_rules = total_rules - enabled_rules
        
        # Group by type
        rules_by_type = {}
        for alert_type in AlertType:
            count = db.query(AlertRule).filter(AlertRule.alert_type == alert_type).count()
            rules_by_type[alert_type.value] = count
        
        # Group by severity
        rules_by_severity = {}
        for severity in AlertSeverity:
            count = db.query(AlertRule).filter(AlertRule.severity == severity).count()
            rules_by_severity[severity.value] = count
        
        # Most triggered rules
        most_triggered_query = db.query(
            AlertRule.rule_id,
            AlertRule.name,
            func.count(Alert.alert_id).label('alert_count')
        ).join(Alert).filter(
            Alert.triggered_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by(AlertRule.rule_id, AlertRule.name).order_by(
            desc('alert_count')
        ).limit(10).all()
        
        most_triggered_rules = [
            {
                "rule_id": result.rule_id,
                "name": result.name,
                "alert_count": result.alert_count
            }
            for result in most_triggered_query
        ]
        
        return AlertRuleStatistics(
            total_rules=total_rules,
            enabled_rules=enabled_rules,
            disabled_rules=disabled_rules,
            rules_by_type=rules_by_type,
            rules_by_severity=rules_by_severity,
            most_triggered_rules=most_triggered_rules
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert rule statistics: {str(e)}"
        )


# System Health and Monitoring

@router.get("/health", response_model=AlertSystemHealth)
async def get_alert_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AlertSystemHealth:
    """
    Get alerting system health status.
    """
    try:
        alert_manager = AlertManager(db)
        
        # Get basic health metrics
        active_rules = db.query(AlertRule).filter(AlertRule.enabled == True).count()
        
        pending_notifications = db.query(AlertNotification).filter(
            AlertNotification.status == "pending"
        ).count()
        
        # Component health
        components = {
            "alert_manager": "healthy",
            "rule_engine": "healthy",
            "channel_service": "healthy",
            "escalation_service": "healthy",
            "database": "healthy"
        }
        
        return AlertSystemHealth(
            status="healthy",
            last_evaluation=None,  # Would be populated from actual monitoring
            active_rules=active_rules,
            pending_notifications=pending_notifications,
            system_metrics={},
            components=components
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking alert system health: {str(e)}"
        )


# Rule Evaluation and Management

@router.post("/evaluate")
async def evaluate_all_rules(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger evaluation of all enabled alert rules.
    """
    try:
        alert_manager = AlertManager(db)
        results = await alert_manager.evaluate_all_rules()
        
        return {
            "evaluation_started": True,
            "results": results,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating rules: {str(e)}"
        )


@router.get("/evaluation/status")
async def get_evaluation_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get status of rule evaluations.
    """
    try:
        alert_manager = AlertManager(db)
        active_evaluations = alert_manager.get_active_evaluation_count()
        
        return {
            "active_evaluations": active_evaluations,
            "last_evaluation": None,  # Would be populated from actual monitoring
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting evaluation status: {str(e)}"
        )


# Background Task Functions

async def process_alert_notifications_background(alert_id: str) -> None:
    """
    Background task to process alert notifications.
    """
    import logging
    from app.db.session import SessionLocal
    
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        alert_manager = AlertManager(db)
        await alert_manager.process_alert_notifications(alert_id)
        await alert_manager.check_escalation(alert_id)
    except Exception as e:
        logger.error(f"Error in background notification processing: {e}")
    finally:
        db.close()