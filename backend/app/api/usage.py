"""
Usage Tracking & Metering API Endpoints

Provides REST API for usage tracking, quota management, analytics,
forecasting, and reporting.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.usage_tracking_service import UsageTrackingService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.usage_reporting_service import UsageReportingService
from app.models.user import User
from app.models.usage import UsageMetricType

router = APIRouter(prefix="/usage", tags=["usage"])


# Pydantic Schemas
class UsageTrackRequest(BaseModel):
    metric_type: str = Field(..., description="Type of metric to track")
    metric_value: float = Field(..., description="Quantitative value")
    resource_id: Optional[str] = Field(None, description="Reference to resource")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    operation: Optional[str] = Field(None, description="Operation performed")
    metadata: Optional[dict] = Field(default_factory=dict)


class UsageQuotaResponse(BaseModel):
    metric_type: str
    quota_limit: float
    current_usage: float
    usage_percentage: float
    available: float
    unit: str
    is_exceeded: bool
    overage: float
    overage_cost: float
    period_end: str
    next_reset: Optional[str]


class UsageSummaryResponse(BaseModel):
    user_id: int
    subscription_id: Optional[int]
    quotas: List[UsageQuotaResponse]
    total_overage_cost: float
    alerts_count: int


class ForecastRequest(BaseModel):
    metric_type: str
    forecast_horizon_days: int = Field(30, ge=1, le=365)
    model_type: str = Field("linear_regression", description="Forecasting model")


class ForecastResponse(BaseModel):
    metric_type: str
    forecast_date: str
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: float
    model_type: str
    model_accuracy: float
    will_exceed_quota: bool
    expected_overage: float
    estimated_overage_cost: float


class AnomalyResponse(BaseModel):
    id: int
    anomaly_type: str
    severity: str
    confidence_score: float
    detected_at: str
    metric_type: str
    observed_value: float
    expected_value: float
    deviation_percentage: float
    pattern_description: str
    risk_score: int
    is_fraud_suspect: bool
    status: str


class ReportRequest(BaseModel):
    report_type: str = Field("summary", description="Type: summary, detailed, forecast, anomaly")
    report_format: str = Field("pdf", description="Format: pdf, csv, json, excel")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    metric_types: Optional[List[str]] = None
    filters: Optional[dict] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    id: int
    report_type: str
    report_format: str
    period_start: str
    period_end: str
    file_url: str
    file_size_bytes: int
    status: str
    generated_at: Optional[str]
    expires_at: Optional[str]


class UsageTrendsResponse(BaseModel):
    metric_type: str
    period_days: int
    data_points: int
    total: float
    average: float
    median: float
    min: float
    max: float
    std_dev: float
    trend: str
    change_percentage: float
    dates: List[str]
    values: List[float]


# API Endpoints

@router.post("/track", status_code=201)
async def track_usage(
    request: UsageTrackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually track a usage event
    
    This endpoint allows manual tracking of usage events.
    Most usage is tracked automatically via middleware.
    """
    service = UsageTrackingService(db)
    
    # Get subscription ID from user
    subscription_id = getattr(current_user, "active_subscription_id", None)
    
    usage_metric = await service.track_usage(
        user_id=current_user.user_id,
        metric_type=request.metric_type,
        metric_value=request.metric_value,
        subscription_id=subscription_id,
        resource_id=request.resource_id,
        endpoint=request.endpoint,
        operation=request.operation,
        metadata=request.metadata
    )
    
    return {
        "message": "Usage tracked successfully",
        "usage_id": usage_metric.id,
        "metric_type": usage_metric.metric_type,
        "metric_value": usage_metric.metric_value,
        "unit": usage_metric.unit
    }


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current usage summary for the user
    
    Returns quota information, current usage, and alert counts.
    """
    service = UsageTrackingService(db)
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    summary = service.get_current_usage_summary(
        user_id=current_user.user_id,
        subscription_id=subscription_id
    )
    
    return summary


@router.get("/quotas")
async def get_quotas(
    metric_type: Optional[str] = Query(None),
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get quota information for specific metrics
    """
    from app.models.usage import UsageQuota
    from sqlalchemy import and_
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    query = db.query(UsageQuota).filter(
        and_(
            UsageQuota.user_id == current_user.user_id,
            UsageQuota.is_active == True
        )
    )
    
    if subscription_id:
        query = query.filter(UsageQuota.subscription_id == subscription_id)
    
    if metric_type:
        query = query.filter(UsageQuota.metric_type == metric_type)
    
    quotas = query.all()
    
    return {
        "quotas": [
            {
                "id": q.id,
                "metric_type": q.metric_type,
                "quota_limit": q.quota_limit,
                "current_usage": q.current_usage,
                "usage_percentage": q.usage_percentage,
                "available": max(0, q.quota_limit - q.current_usage),
                "unit": q.unit,
                "is_exceeded": q.is_exceeded,
                "overage": q.current_overage,
                "overage_rate": q.overage_rate,
                "period_start": q.period_start.isoformat(),
                "period_end": q.period_end.isoformat(),
                "next_reset": q.next_reset_at.isoformat() if q.next_reset_at else None
            }
            for q in quotas
        ]
    }


@router.get("/check-quota/{metric_type}")
async def check_quota_availability(
    metric_type: str = Path(...),
    required_quantity: float = Query(1.0),
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if sufficient quota is available for a resource
    
    This endpoint should be called before initiating resource-intensive operations.
    """
    service = UsageTrackingService(db)
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    if not subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    is_available, error_message, quota_info = service.check_quota_available(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        metric_type=metric_type,
        required_quantity=required_quantity
    )
    
    return {
        "is_available": is_available,
        "error_message": error_message,
        "quota_info": quota_info
    }


@router.get("/trends/{metric_type}", response_model=UsageTrendsResponse)
async def get_usage_trends(
    metric_type: str = Path(...),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage trends and statistics for a metric
    
    Returns historical data, averages, and trend analysis.
    """
    service = UsageAnalyticsService(db)
    
    trends = service.get_usage_trends(
        user_id=current_user.user_id,
        metric_type=metric_type,
        days=days
    )
    
    return trends


@router.post("/forecast", response_model=ForecastResponse)
async def generate_forecast(
    request: ForecastRequest,
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate usage forecast for a metric
    
    Uses historical data to predict future usage and quota exceedance.
    """
    service = UsageAnalyticsService(db)
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    if not subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    forecast = await service.generate_forecast(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        metric_type=request.metric_type,
        forecast_horizon_days=request.forecast_horizon_days,
        model_type=request.model_type
    )
    
    if not forecast:
        raise HTTPException(
            status_code=400,
            detail="Insufficient historical data for forecasting. Need at least 7 days of data."
        )
    
    return {
        "metric_type": forecast.metric_type,
        "forecast_date": forecast.forecast_date.isoformat(),
        "predicted_value": forecast.predicted_value,
        "confidence_lower": forecast.confidence_lower,
        "confidence_upper": forecast.confidence_upper,
        "confidence_level": forecast.confidence_level,
        "model_type": forecast.model_type,
        "model_accuracy": forecast.model_accuracy,
        "will_exceed_quota": forecast.will_exceed_quota,
        "expected_overage": forecast.expected_overage,
        "estimated_overage_cost": forecast.estimated_overage_cost
    }


@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_anomalies(
    metric_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detected usage anomalies
    
    Returns anomalies detected by the fraud detection system.
    """
    from app.models.usage import UsageAnomaly
    from sqlalchemy import and_
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(UsageAnomaly).filter(
        and_(
            UsageAnomaly.user_id == current_user.user_id,
            UsageAnomaly.detected_at >= start_date
        )
    )
    
    if subscription_id:
        query = query.filter(UsageAnomaly.subscription_id == subscription_id)
    
    if metric_type:
        query = query.filter(UsageAnomaly.metric_type == metric_type)
    
    if severity:
        query = query.filter(UsageAnomaly.severity == severity)
    
    if status:
        query = query.filter(UsageAnomaly.status == status)
    
    anomalies = query.order_by(UsageAnomaly.detected_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "confidence_score": a.confidence_score,
            "detected_at": a.detected_at.isoformat(),
            "metric_type": a.metric_type,
            "observed_value": a.observed_value,
            "expected_value": a.expected_value,
            "deviation_percentage": a.deviation_percentage,
            "pattern_description": a.pattern_description,
            "risk_score": a.risk_score,
            "is_fraud_suspect": a.is_fraud_suspect,
            "status": a.status
        }
        for a in anomalies
    ]


@router.post("/anomalies/detect")
async def detect_anomalies(
    metric_type: str = Query(...),
    detection_method: str = Query("statistical", description="Method: statistical, velocity, pattern"),
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger anomaly detection for a metric
    
    Runs fraud detection algorithms on recent usage data.
    """
    service = UsageAnalyticsService(db)
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    if not subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    anomalies = await service.detect_anomalies(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        metric_type=metric_type,
        detection_method=detection_method
    )
    
    return {
        "message": f"Anomaly detection completed",
        "anomalies_detected": len(anomalies),
        "anomalies": [
            {
                "id": a.id,
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "risk_score": a.risk_score,
                "is_fraud_suspect": a.is_fraud_suspect
            }
            for a in anomalies
        ]
    }


@router.get("/alerts")
async def get_usage_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage alerts for the user
    
    Returns quota limit alerts and notifications.
    """
    from app.models.usage import UsageAlert
    from sqlalchemy import and_
    
    query = db.query(UsageAlert).filter(
        UsageAlert.user_id == current_user.user_id
    )
    
    if status:
        query = query.filter(UsageAlert.status == status)
    
    if severity:
        query = query.filter(UsageAlert.severity == severity)
    
    alerts = query.order_by(UsageAlert.triggered_at.desc()).limit(limit).all()
    
    return {
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "metric_type": a.metric_type,
                "current_value": a.current_value,
                "threshold_value": a.threshold_value,
                "quota_percentage": a.quota_percentage,
                "status": a.status,
                "triggered_at": a.triggered_at.isoformat(),
                "action_taken": a.action_taken
            }
            for a in alerts
        ],
        "total_count": len(alerts)
    }


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acknowledge a usage alert
    """
    from app.models.usage import UsageAlert, UsageAlertStatus
    
    alert = db.query(UsageAlert).filter(
        and_(
            UsageAlert.id == alert_id,
            UsageAlert.user_id == current_user.user_id
        )
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = UsageAlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = current_user.user_id
    
    db.commit()
    
    return {
        "message": "Alert acknowledged successfully",
        "alert_id": alert_id
    }


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_usage_report(
    request: ReportRequest,
    subscription_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a usage report
    
    Creates a downloadable report in the requested format.
    """
    service = UsageReportingService(db)
    
    if not subscription_id:
        subscription_id = getattr(current_user, "active_subscription_id", None)
    
    report = await service.generate_usage_report(
        user_id=current_user.user_id,
        subscription_id=subscription_id,
        generated_by=current_user.user_id,
        report_type=request.report_type,
        report_format=request.report_format,
        period_start=request.period_start,
        period_end=request.period_end,
        metric_types=request.metric_types,
        filters=request.filters
    )
    
    return {
        "id": report.id,
        "report_type": report.report_type,
        "report_format": report.report_format,
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "file_url": report.file_url,
        "file_size_bytes": report.file_size_bytes,
        "status": report.status,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "expires_at": report.expires_at.isoformat() if report.expires_at else None
    }


@router.get("/reports")
async def list_usage_reports(
    report_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List generated usage reports
    """
    from app.models.usage import UsageReport
    from sqlalchemy import and_
    
    query = db.query(UsageReport).filter(
        UsageReport.user_id == current_user.user_id
    )
    
    if report_type:
        query = query.filter(UsageReport.report_type == report_type)
    
    reports = query.order_by(UsageReport.created_at.desc()).limit(limit).all()
    
    return {
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "report_format": r.report_format,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "file_url": r.file_url,
                "file_size_bytes": r.file_size_bytes,
                "status": r.status,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "download_count": r.download_count
            }
            for r in reports
        ]
    }


# Admin Endpoints

@router.get("/admin/metrics", tags=["admin"])
async def get_all_usage_metrics(
    user_id: Optional[int] = Query(None),
    metric_type: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get usage metrics for all users or specific user
    """
    # Check admin permissions
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models.usage import UsageMetric
    from sqlalchemy import and_
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    query = db.query(UsageMetric).filter(
        UsageMetric.timestamp >= start_date
    )
    
    if user_id:
        query = query.filter(UsageMetric.user_id == user_id)
    
    if metric_type:
        query = query.filter(UsageMetric.metric_type == metric_type)
    
    metrics = query.order_by(UsageMetric.timestamp.desc()).limit(1000).all()
    
    return {
        "metrics": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "metric_type": m.metric_type,
                "metric_value": m.metric_value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "endpoint": m.endpoint,
                "response_time_ms": m.response_time_ms,
                "error_occurred": m.error_occurred
            }
            for m in metrics
        ],
        "total_count": len(metrics)
    }


@router.post("/admin/quotas/reset", tags=["admin"])
async def reset_user_quota(
    user_id: int = Query(...),
    subscription_id: int = Query(...),
    metric_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Reset quota for a user
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = UsageTrackingService(db)
    
    await service.reset_quota(
        user_id=user_id,
        subscription_id=subscription_id,
        metric_type=metric_type
    )
    
    return {
        "message": "Quota reset successfully",
        "user_id": user_id,
        "subscription_id": subscription_id,
        "metric_type": metric_type or "all"
    }
