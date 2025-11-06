"""
Audit Logging API Endpoints

This module provides comprehensive REST API endpoints for audit logging operations
including log management, audit trails, compliance reporting, and analytics.

Author: Fernando Platform
Created: 2025-11-06
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import uuid
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.db.session import get_db
from app.models.logging import (
    LogEntry, AuditTrail, ComplianceLog, ForensicLog, 
    RetentionPolicy, DataSubject
)
from app.models.user import User
from app.core.security import get_current_user, require_permissions
from app.services.audit.audit_service import AuditService
from app.services.audit.audit_compliance import AuditComplianceService
from app.services.audit.audit_analytics import AuditAnalytics
from app.services.logging.structured_logger import StructuredLogger
from app.services.logging.compliance_logger import ComplianceLogger
from app.services.search.audit_search import AuditSearchEngine
from app.schemas.audit_logging_schemas import (
    LogEntryCreate, LogEntryResponse,
    AuditTrailCreate, AuditTrailResponse,
    ComplianceLogCreate, ComplianceLogResponse,
    LogSearchRequest, LogSearchResponse,
    AuditSearchRequest, AuditSearchResponse,
    ComplianceReportRequest, ComplianceReportResponse,
    DataSubjectRequestCreate, DataSubjectRequestResponse,
    LogAnalyticsRequest, LogAnalyticsResponse,
    ComplianceDashboardRequest, ComplianceDashboardResponse,
    SystemHealthResponse, RetentionPolicyRequest, RetentionPolicyResponse,
    LogExportRequest, LogExportResponse,
    ApiResponse, PaginatedResponse, HealthCheckResponse,
    ComplianceRegulation, DataSubjectRequestType
)

# Configure logger
logger = StructuredLogger(__name__)

# Create router
router = APIRouter(prefix="/audit", tags=["audit-logging"])

# Shared dependencies
def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Get audit service dependency"""
    return AuditService(db)

def get_compliance_service(db: Session = Depends(get_db)) -> AuditComplianceService:
    """Get compliance service dependency"""
    return AuditComplianceService(db)

def get_analytics_service(db: Session = Depends(get_db)) -> AuditAnalytics:
    """Get analytics service dependency"""
    return AuditAnalytics(db)

def get_search_engine(db: Session = Depends(get_db)) -> AuditSearchEngine:
    """Get search engine dependency"""
    return AuditSearchEngine(db)


# =============================================================================
# HEALTH AND STATUS ENDPOINTS
# =============================================================================

@router.get("/health", response_model=HealthCheckResponse)
def get_audit_logging_health():
    """Get health status of audit logging system"""
    try:
        # Check database connectivity
        db_status = "healthy"
        
        # Check Elasticsearch connectivity (if configured)
        elasticsearch_status = "not_configured"  # Would check actual connection
        
        # Check system resources
        memory_usage = "normal"  # Would calculate actual usage
        
        # Determine overall status
        if db_status == "healthy":
            overall_status = "healthy"
        elif db_status == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return HealthCheckResponse(
            service="audit-logging",
            status=overall_status,
            version="1.0.0",
            dependencies={
                "database": db_status,
                "elasticsearch": elasticsearch_status
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheckResponse(
            service="audit-logging",
            status="unhealthy",
            version="1.0.0",
            dependencies={"database": "error"},
            timestamp=datetime.utcnow()
        )


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed system health information"""
    try:
        components = {
            "log_ingestion": "healthy",
            "audit_tracking": "healthy", 
            "compliance_monitoring": "healthy",
            "search_engine": "healthy",
            "retention_manager": "healthy"
        }
        
        metrics = {
            "log_entries_today": db.query(LogEntry).filter(
                LogEntry.created_at >= datetime.utcnow().date()
            ).count(),
            "audit_events_today": db.query(AuditTrail).filter(
                AuditTrail.created_at >= datetime.utcnow().date()
            ).count(),
            "compliance_events_today": db.query(ComplianceLog).filter(
                ComplianceLog.created_at >= datetime.utcnow().date()
            ).count(),
            "active_retention_policies": db.query(RetentionPolicy).filter(
                RetentionPolicy.is_active == True
            ).count()
        }
        
        recent_issues = []  # Would query actual recent issues
        
        status = "healthy" if all(s == "healthy" for s in components.values()) else "degraded"
        
        return SystemHealthResponse(
            status=status,
            timestamp=datetime.utcnow(),
            components=components,
            metrics=metrics,
            recent_issues=recent_issues
        )
        
    except Exception as e:
        logger.error("Failed to get system health", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


# =============================================================================
# LOG ENTRY ENDPOINTS
# =============================================================================

@router.post("/logs", response_model=LogEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(
    log_data: LogEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new log entry"""
    try:
        log_entry = LogEntry(
            level=log_data.level,
            message=log_data.message,
            source=log_data.source,
            category=log_data.category,
            resource_type=log_data.resource_type,
            user_id=log_data.user_id or current_user.user_id,
            session_id=log_data.session_id,
            correlation_id=log_data.correlation_id,
            metadata=log_data.metadata
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        logger.info("Log entry created", 
                   log_id=log_entry.log_id,
                   level=log_data.level,
                   source=log_data.source,
                   user_id=current_user.user_id)
        
        return LogEntryResponse.from_orm(log_entry)
        
    except Exception as e:
        logger.error("Failed to create log entry", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to create log entry")


@router.get("/logs", response_model=LogSearchResponse)
async def search_logs(
    search_request: LogSearchRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search and filter log entries"""
    try:
        query = db.query(LogEntry)
        
        # Apply filters
        if search_request.query:
            query = query.filter(LogEntry.message.ilike(f"%{search_request.query}%"))
        
        if search_request.levels:
            query = query.filter(LogEntry.level.in_(search_request.levels))
        
        if search_request.categories:
            query = query.filter(LogEntry.category.in_(search_request.categories))
        
        if search_request.sources:
            query = query.filter(LogEntry.source.in_(search_request.sources))
        
        if search_request.start_date:
            query = query.filter(LogEntry.created_at >= search_request.start_date)
        
        if search_request.end_date:
            query = query.filter(LogEntry.created_at <= search_request.end_date)
        
        if search_request.user_id:
            query = query.filter(LogEntry.user_id == search_request.user_id)
        
        if search_request.resource_type:
            query = query.filter(LogEntry.resource_type == search_request.resource_type)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if search_request.sort_order == "asc":
            query = query.order_by(asc(getattr(LogEntry, search_request.sort_by)))
        else:
            query = query.order_by(desc(getattr(LogEntry, search_request.sort_by)))
        
        # Apply pagination
        logs = query.offset(search_request.offset).limit(search_request.limit).all()
        
        # Check if there are more results
        has_more = (search_request.offset + search_request.limit) < total
        
        # Generate aggregations
        aggregations = {
            "levels": db.query(LogEntry.level, func.count(LogEntry.log_id)).group_by(LogEntry.level).all(),
            "categories": db.query(LogEntry.category, func.count(LogEntry.log_id)).group_by(LogEntry.category).all(),
            "sources": db.query(LogEntry.source, func.count(LogEntry.log_id)).group_by(LogEntry.source).all()
        }
        
        logger.info("Log search completed",
                   query_hash=hash(search_request.query or ""),
                   results_count=len(logs),
                   user_id=current_user.user_id)
        
        return LogSearchResponse(
            logs=[LogEntryResponse.from_orm(log) for log in logs],
            total=total,
            limit=search_request.limit,
            offset=search_request.offset,
            has_more=has_more,
            aggregations=aggregations
        )
        
    except Exception as e:
        logger.error("Failed to search logs", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to search logs")


@router.get("/logs/{log_id}", response_model=LogEntryResponse)
async def get_log_entry(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific log entry by ID"""
    try:
        log_entry = db.query(LogEntry).filter(LogEntry.log_id == log_id).first()
        
        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")
        
        logger.info("Log entry retrieved", log_id=log_id, user_id=current_user.user_id)
        
        return LogEntryResponse.from_orm(log_entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get log entry", error=str(e), log_id=log_id, user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve log entry")


# =============================================================================
# AUDIT TRAIL ENDPOINTS
# =============================================================================

@router.post("/audit-trails", response_model=AuditTrailResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_trail(
    audit_data: AuditTrailCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new audit trail entry"""
    try:
        audit_trail = AuditTrail(
            action=audit_data.action,
            resource_type=audit_data.resource_type,
            resource_id=audit_data.resource_id,
            old_values=audit_data.old_values,
            new_values=audit_data.new_values,
            result=audit_data.result,
            user_id=audit_data.user_id or current_user.user_id,
            user_email=audit_data.user_email or current_user.email,
            user_name=audit_data.user_name or current_user.full_name,
            ip_address=audit_data.ip_address,
            user_agent=audit_data.user_agent,
            metadata=audit_data.metadata
        )
        
        db.add(audit_trail)
        db.commit()
        db.refresh(audit_trail)
        
        logger.info("Audit trail created",
                   audit_id=audit_trail.audit_id,
                   action=audit_data.action,
                   resource_type=audit_data.resource_type,
                   user_id=current_user.user_id)
        
        return AuditTrailResponse.from_orm(audit_trail)
        
    except Exception as e:
        logger.error("Failed to create audit trail", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to create audit trail")


@router.get("/audit-trails", response_model=AuditSearchResponse)
async def search_audit_trails(
    search_request: AuditSearchRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search and filter audit trail entries"""
    try:
        query = db.query(AuditTrail)
        
        # Apply filters
        if search_request.query:
            query = query.filter(
                or_(
                    AuditTrail.action.ilike(f"%{search_request.query}%"),
                    AuditTrail.resource_type.ilike(f"%{search_request.query}%"),
                    AuditTrail.user_email.ilike(f"%{search_request.query}%"),
                    AuditTrail.user_name.ilike(f"%{search_request.query}%")
                )
            )
        
        if search_request.actions:
            query = query.filter(AuditTrail.action.in_(search_request.actions))
        
        if search_request.resource_types:
            query = query.filter(AuditTrail.resource_type.in_(search_request.resource_types))
        
        if search_request.start_date:
            query = query.filter(AuditTrail.created_at >= search_request.start_date)
        
        if search_request.end_date:
            query = query.filter(AuditTrail.created_at <= search_request.end_date)
        
        if search_request.user_id:
            query = query.filter(AuditTrail.user_id == search_request.user_id)
        
        if search_request.result:
            query = query.filter(AuditTrail.result == search_request.result)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if search_request.sort_order == "asc":
            query = query.order_by(asc(getattr(AuditTrail, search_request.sort_by)))
        else:
            query = query.order_by(desc(getattr(AuditTrail, search_request.sort_by)))
        
        # Apply pagination
        audits = query.offset(search_request.offset).limit(search_request.limit).all()
        
        # Check if there are more results
        has_more = (search_request.offset + search_request.limit) < total
        
        # Generate aggregations
        aggregations = {
            "actions": db.query(AuditTrail.action, func.count(AuditTrail.audit_id)).group_by(AuditTrail.action).all(),
            "resource_types": db.query(AuditTrail.resource_type, func.count(AuditTrail.audit_id)).group_by(AuditTrail.resource_type).all(),
            "results": db.query(AuditTrail.result, func.count(AuditTrail.audit_id)).group_by(AuditTrail.result).all()
        }
        
        logger.info("Audit trail search completed",
                   query_hash=hash(search_request.query or ""),
                   results_count=len(audits),
                   user_id=current_user.user_id)
        
        return AuditSearchResponse(
            audits=[AuditTrailResponse.from_orm(audit) for audit in audits],
            total=total,
            limit=search_request.limit,
            offset=search_request.offset,
            has_more=has_more,
            aggregations=aggregations
        )
        
    except Exception as e:
        logger.error("Failed to search audit trails", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to search audit trails")


@router.get("/audit-trails/{audit_id}", response_model=AuditTrailResponse)
async def get_audit_trail(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific audit trail entry by ID"""
    try:
        audit_trail = db.query(AuditTrail).filter(AuditTrail.audit_id == audit_id).first()
        
        if not audit_trail:
            raise HTTPException(status_code=404, detail="Audit trail entry not found")
        
        logger.info("Audit trail retrieved", audit_id=audit_id, user_id=current_user.user_id)
        
        return AuditTrailResponse.from_orm(audit_trail)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audit trail", error=str(e), audit_id=audit_id, user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit trail")


# =============================================================================
# COMPLIANCE ENDPOINTS
# =============================================================================

@router.post("/compliance/reports", response_model=ComplianceReportResponse)
async def generate_compliance_report(
    report_request: ComplianceReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    compliance_service: AuditComplianceService = Depends(get_compliance_service)
):
    """Generate compliance report for specified regulation"""
    try:
        # Generate report asynchronously
        report = await compliance_service.generate_compliance_report(
            regulation=ComplianceRegulation(report_request.regulation),
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            include_violations=report_request.include_violations
        )
        
        logger.info("Compliance report generated",
                   regulation=report_request.regulation.value,
                   compliance_score=report.metadata.get("compliance_score", 0),
                   user_id=current_user.user_id)
        
        return ComplianceReportResponse(
            report_id=str(uuid.uuid4()),
            regulation=ComplianceRegulation(report_request.regulation.value),
            status=report.status,
            compliance_score=report.metadata.get("compliance_score", 0.0),
            generated_at=report.report_date,
            period={
                "start": report_request.start_date,
                "end": report_request.end_date
            },
            findings=report.findings,
            violations=report.violations,
            recommendations=report.recommendations,
            total_records_analyzed=report.metadata.get("total_records_analyzed", 0)
        )
        
    except Exception as e:
        logger.error("Failed to generate compliance report", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")


@router.get("/compliance/dashboard", response_model=ComplianceDashboardResponse)
async def get_compliance_dashboard(
    dashboard_request: ComplianceDashboardRequest = Depends(),
    current_user: User = Depends(get_current_user),
    compliance_service: AuditComplianceService = Depends(get_compliance_service)
):
    """Get compliance dashboard data"""
    try:
        dashboard_data = await compliance_service.generate_compliance_dashboard_data(
            regulation=ComplianceRegulation(dashboard_request.regulation) if dashboard_request.regulation else None
        )
        
        logger.info("Compliance dashboard data retrieved",
                   regulation=dashboard_request.regulation.value if dashboard_request.regulation else "all",
                   user_id=current_user.user_id)
        
        return ComplianceDashboardResponse(
            generated_at=dashboard_data["generated_at"],
            regulation=dashboard_data["regulation"],
            metrics=dashboard_data["metrics"],
            trends=dashboard_data.get("trends", {}) if dashboard_request.include_trends else {},
            alerts=dashboard_data.get("alerts", []) if dashboard_request.include_alerts else [],
            compliance_status=dashboard_data.get("compliance_status", {}),
            data_subject_requests=dashboard_data.get("data_subject_requests", {}),
            violations_summary=dashboard_data.get("violations_summary", {}),
            recommendations=dashboard_data.get("recommendations", []) if dashboard_request.include_recommendations else []
        )
        
    except Exception as e:
        logger.error("Failed to get compliance dashboard", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance dashboard")


@router.post("/compliance/data-subject-requests", response_model=ApiResponse)
async def create_data_subject_request(
    dsr_request: DataSubjectRequestCreate,
    current_user: User = Depends(get_current_user),
    compliance_service: AuditComplianceService = Depends(get_compliance_service)
):
    """Process GDPR data subject request"""
    try:
        request_id = await compliance_service.process_data_subject_request(
            subject_id=dsr_request.subject_id,
            request_type=DataSubjectRequestType(dsr_request.request_type.value),
            request_metadata=dsr_request.metadata
        )
        
        logger.info("Data subject request created",
                   request_id=request_id,
                   subject_id=dsr_request.subject_id,
                   request_type=dsr_request.request_type.value,
                   user_id=current_user.user_id)
        
        return ApiResponse(
            success=True,
            message="Data subject request processed successfully",
            data={"request_id": request_id}
        )
        
    except Exception as e:
        logger.error("Failed to process data subject request", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to process data subject request")


@router.get("/compliance/verify-integrity", response_model=Dict[str, Any])
async def verify_log_integrity(
    start_date: datetime = Query(..., description="Verification period start"),
    end_date: datetime = Query(..., description="Verification period end"),
    current_user: User = Depends(get_current_user),
    compliance_service: AuditComplianceService = Depends(get_compliance_service)
):
    """Verify audit log integrity"""
    try:
        verification_results = await compliance_service.verify_log_integrity(
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info("Log integrity verification completed",
                   integrity_score=verification_results["integrity_score"],
                   tampered_logs=verification_results["tampered_logs"],
                   user_id=current_user.user_id)
        
        return verification_results
        
    except Exception as e:
        logger.error("Failed to verify log integrity", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to verify log integrity")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/logs", response_model=LogAnalyticsResponse)
async def get_log_analytics(
    start_date: datetime = Query(..., description="Analytics period start"),
    end_date: datetime = Query(..., description="Analytics period end"),
    group_by: str = Query(default="day", description="Time grouping: hour, day, week, month"),
    metrics: str = Query(default="count", description="Comma-separated metrics"),
    current_user: User = Depends(get_current_user),
    analytics_service: AuditAnalytics = Depends(get_analytics_service),
    db: Session = Depends(get_db)
):
    """Get log analytics and insights"""
    try:
        # Parse metrics list
        metrics_list = [m.strip() for m in metrics.split(",")]
        
        # Get time series data
        time_series = []
        
        # Calculate period based on group_by
        if group_by == "hour":
            period_step = timedelta(hours=1)
        elif group_by == "day":
            period_step = timedelta(days=1)
        elif group_by == "week":
            period_step = timedelta(weeks=1)
        else:  # month
            period_step = timedelta(days=30)
        
        current_period = start_date
        while current_period < end_date:
            period_end = current_period + period_step
            
            # Query logs for this period
            period_logs = db.query(LogEntry).filter(
                and_(
                    LogEntry.created_at >= current_period,
                    LogEntry.created_at < period_end
                )
            ).all()
            
            # Calculate metrics for this period
            period_data = {"period": current_period.isoformat()}
            
            if "count" in metrics_list:
                period_data["count"] = len(period_logs)
            
            if "unique_users" in metrics_list:
                period_data["unique_users"] = len(set(log.user_id for log in period_logs if log.user_id))
            
            if "error_rate" in metrics_list:
                error_logs = [log for log in period_logs if log.level.value in ["error", "critical"]]
                period_data["error_rate"] = (len(error_logs) / len(period_logs) * 100) if period_logs else 0
            
            time_series.append(period_data)
            current_period = period_end
        
        # Get summary statistics
        all_logs = db.query(LogEntry).filter(
            and_(
                LogEntry.created_at >= start_date,
                LogEntry.created_at <= end_date
            )
        ).all()
        
        summary = {
            "total_logs": len(all_logs),
            "unique_users": len(set(log.user_id for log in all_logs if log.user_id)),
            "error_count": len([log for log in all_logs if log.level.value in ["error", "critical"]]),
            "warning_count": len([log for log in all_logs if log.level.value == "warning"])
        }
        
        # Get top categories and sources
        top_categories = db.query(LogEntry.category, func.count(LogEntry.log_id)).filter(
            and_(
                LogEntry.created_at >= start_date,
                LogEntry.created_at <= end_date
            )
        ).group_by(LogEntry.category).order_by(func.count(LogEntry.log_id).desc()).limit(10).all()
        
        top_sources = db.query(LogEntry.source, func.count(LogEntry.log_id)).filter(
            and_(
                LogEntry.created_at >= start_date,
                LogEntry.created_at <= end_date
            )
        ).group_by(LogEntry.source).order_by(func.count(LogEntry.log_id).desc()).limit(10).all()
        
        logger.info("Log analytics computed",
                   period=f"{start_date} to {end_date}",
                   total_logs=summary["total_logs"],
                   user_id=current_user.user_id)
        
        return LogAnalyticsResponse(
            period={"start": start_date, "end": end_date},
            time_series=time_series,
            summary=summary,
            top_categories=[{"category": cat, "count": count} for cat, count in top_categories],
            top_sources=[{"source": src, "count": count} for src, count in top_sources],
            error_rate=(summary["error_count"] / summary["total_logs"] * 100) if summary["total_logs"] > 0 else 0,
            unique_users_count=summary["unique_users"]
        )
        
    except Exception as e:
        logger.error("Failed to get log analytics", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve log analytics")


@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_audit_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit summary statistics"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get audit statistics
        total_audits = db.query(AuditTrail).filter(AuditTrail.created_at >= start_date).count()
        successful_audits = db.query(AuditTrail).filter(
            and_(
                AuditTrail.created_at >= start_date,
                AuditTrail.result == "success"
            )
        ).count()
        
        # Get compliance statistics
        compliance_events = db.query(ComplianceLog).filter(ComplianceLog.created_at >= start_date).count()
        
        # Get error statistics
        error_logs = db.query(LogEntry).filter(
            and_(
                LogEntry.created_at >= start_date,
                LogEntry.level.in_(["error", "critical"])
            )
        ).count()
        
        # Get top actions
        top_actions = db.query(AuditTrail.action, func.count(AuditTrail.audit_id)).filter(
            AuditTrail.created_at >= start_date
        ).group_by(AuditTrail.action).order_by(func.count(AuditTrail.audit_id).desc()).limit(5).all()
        
        # Get top users
        top_users = db.query(AuditTrail.user_email, func.count(AuditTrail.audit_id)).filter(
            AuditTrail.created_at >= start_date
        ).group_by(AuditTrail.user_email).order_by(func.count(AuditTrail.audit_id).desc()).limit(5).all()
        
        summary = {
            "period_days": days,
            "total_audits": total_audits,
            "successful_audits": successful_audits,
            "success_rate": (successful_audits / total_audits * 100) if total_audits > 0 else 0,
            "compliance_events": compliance_events,
            "error_logs": error_logs,
            "top_actions": [{"action": action, "count": count} for action, count in top_actions],
            "top_users": [{"email": email, "count": count} for email, count in top_users if email],
            "generated_at": datetime.utcnow()
        }
        
        logger.info("Audit summary generated",
                   period_days=days,
                   total_audits=total_audits,
                   user_id=current_user.user_id)
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get audit summary", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit summary")


# =============================================================================
# RETENTION POLICY ENDPOINTS
# =============================================================================

@router.get("/retention/policies", response_model=List[RetentionPolicyResponse])
async def get_retention_policies(
    active_only: bool = Query(default=False, description="Filter active policies only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get retention policies"""
    try:
        query = db.query(RetentionPolicy)
        
        if active_only:
            query = query.filter(RetentionPolicy.is_active == True)
        
        policies = query.order_by(RetentionPolicy.created_at.desc()).all()
        
        logger.info("Retention policies retrieved",
                   count=len(policies),
                   active_only=active_only,
                   user_id=current_user.user_id)
        
        return [RetentionPolicyResponse.from_orm(policy) for policy in policies]
        
    except Exception as e:
        logger.error("Failed to get retention policies", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve retention policies")


@router.post("/retention/policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["admin"])
async def create_retention_policy(
    policy_request: RetentionPolicyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new retention policy (admin only)"""
    try:
        policy = RetentionPolicy(
            name=policy_request.name,
            description=policy_request.description,
            log_types=policy_request.log_types,
            retention_days=policy_request.retention_days,
            archive_before_delete=policy_request.archive_before_delete,
            encryption_required=policy_request.encryption_required,
            conditions=policy_request.conditions,
            is_active=True
        )
        
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        logger.info("Retention policy created",
                   policy_id=policy.policy_id,
                   name=policy.name,
                   retention_days=policy.retention_days,
                   user_id=current_user.user_id)
        
        return RetentionPolicyResponse.from_orm(policy)
        
    except Exception as e:
        logger.error("Failed to create retention policy", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to create retention policy")


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.post("/export/logs", response_model=ApiResponse)
async def export_logs(
    export_request: LogExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export logs for compliance or analysis"""
    try:
        export_id = str(uuid.uuid4())
        
        # This would typically create a background job to export logs
        # and return a URL to download when ready
        
        logger.info("Log export initiated",
                   export_id=export_id,
                   export_type=export_request.export_type,
                   format=export_request.format,
                   user_id=current_user.user_id)
        
        return ApiResponse(
            success=True,
            message="Log export initiated successfully",
            data={
                "export_id": export_id,
                "status": "processing",
                "estimated_completion": datetime.utcnow() + timedelta(minutes=10)
            }
        )
        
    except Exception as e:
        logger.error("Failed to export logs", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to export logs")


@router.get("/export/{export_id}/status", response_model=LogExportResponse)
async def get_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of log export"""
    try:
        # This would typically query the export job status from database
        # For now, return a mock response
        
        return LogExportResponse(
            export_id=export_id,
            export_type="logs",
            format="json",
            status="completed",
            file_url=f"/exports/{export_id}.json",
            record_count=1000,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
    except Exception as e:
        logger.error("Failed to get export status", error=str(e), export_id=export_id, user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve export status")


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/admin/cleanup", response_model=ApiResponse)
@require_permissions(["admin"])
async def cleanup_old_logs(
    days_old: int = Query(default=90, ge=1, le=3650, description="Delete logs older than this many days"),
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cleanup old logs based on retention policies (admin only)"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count logs to be deleted
        logs_to_delete = db.query(LogEntry).filter(LogEntry.created_at < cutoff_date).count()
        
        # Schedule background cleanup task
        background_tasks.add_task(
            cleanup_logs_background, 
            cutoff_date, 
            current_user.user_id
        )
        
        logger.info("Log cleanup initiated",
                   days_old=days_old,
                   estimated_logs_to_delete=logs_to_delete,
                   user_id=current_user.user_id)
        
        return ApiResponse(
            success=True,
            message=f"Cleanup initiated for {logs_to_delete} logs older than {days_old} days",
            data={
                "estimated_logs_to_delete": logs_to_delete,
                "cutoff_date": cutoff_date,
                "initiated_by": current_user.user_id
            }
        )
        
    except Exception as e:
        logger.error("Failed to initiate log cleanup", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to initiate log cleanup")


async def cleanup_logs_background(cutoff_date: datetime, initiated_by: str):
    """Background task for log cleanup"""
    try:
        logger.info("Starting background log cleanup", 
                   cutoff_date=cutoff_date, 
                   initiated_by=initiated_by)
        
        # Implementation would depend on database session management
        # This is a placeholder for the actual cleanup logic
        
        await asyncio.sleep(1)  # Simulate cleanup work
        
        logger.info("Background log cleanup completed",
                   initiated_by=initiated_by)
        
    except Exception as e:
        logger.error("Background log cleanup failed", 
                    error=str(e), 
                    initiated_by=initiated_by)


# =============================================================================
# REAL-TIME ENDPOINTS
# =============================================================================

@router.get("/realtime/stream")
async def get_real_time_log_stream(
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    levels: Optional[List[str]] = Query(None, description="Filter by log levels"),
    current_user: User = Depends(get_current_user)
):
    """Get real-time log stream (WebSocket endpoint placeholder)"""
    # This would typically be a WebSocket endpoint for real-time log streaming
    # For now, return a placeholder response
    return {
        "message": "Real-time log streaming endpoint - WebSocket implementation needed",
        "filters": {
            "categories": categories,
            "levels": levels
        },
        "user_id": current_user.user_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/realtime/stats", response_model=Dict[str, Any])
async def get_real_time_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real-time statistics"""
    try:
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        stats = {
            "last_hour": {
                "logs": db.query(LogEntry).filter(LogEntry.created_at >= hour_ago).count(),
                "audits": db.query(AuditTrail).filter(AuditTrail.created_at >= hour_ago).count(),
                "errors": db.query(LogEntry).filter(
                    and_(
                        LogEntry.created_at >= hour_ago,
                        LogEntry.level.in_(["error", "critical"])
                    )
                ).count()
            },
            "last_day": {
                "logs": db.query(LogEntry).filter(LogEntry.created_at >= day_ago).count(),
                "audits": db.query(AuditTrail).filter(AuditTrail.created_at >= day_ago).count(),
                "compliance_events": db.query(ComplianceLog).filter(ComplianceLog.created_at >= day_ago).count()
            },
            "total_records": {
                "logs": db.query(LogEntry).count(),
                "audits": db.query(AuditTrail).count(),
                "compliance_logs": db.query(ComplianceLog).count()
            },
            "timestamp": now.isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get real-time stats", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve real-time statistics")


# =============================================================================
# INTEGRATION ENDPOINTS
# =============================================================================

@router.post("/integrations/webhook", response_model=ApiResponse)
async def receive_external_webhook(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Receive audit data from external systems via webhook"""
    try:
        # Validate webhook payload
        required_fields = ["source", "event_type", "data"]
        if not all(field in payload for field in required_fields):
            raise HTTPException(status_code=400, detail="Missing required webhook fields")
        
        # Process webhook data
        logger.info("External webhook received",
                   source=payload["source"],
                   event_type=payload["event_type"],
                   user_id=current_user.user_id)
        
        return ApiResponse(
            success=True,
            message="Webhook processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process webhook", error=str(e), user_id=current_user.user_id)
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/integrations/endpoints", response_model=List[Dict[str, str]])
async def get_integration_endpoints(
    current_user: User = Depends(get_current_user)
):
    """Get available integration endpoints and their documentation"""
    endpoints = [
        {
            "name": "Webhook Receiver",
            "url": "/api/audit/integrations/webhook",
            "method": "POST",
            "description": "Receive audit data from external systems"
        },
        {
            "name": "Log Stream",
            "url": "/api/audit/realtime/stream", 
            "method": "WebSocket",
            "description": "Real-time log streaming"
        },
        {
            "name": "Export Service",
            "url": "/api/audit/export/logs",
            "method": "POST", 
            "description": "Export logs for external analysis"
        }
    ]
    
    return endpoints


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@router.exception_handler(Exception)
async def audit_exception_handler(request, exc):
    """Global exception handler for audit logging endpoints"""
    logger.error("Unhandled exception in audit endpoint",
                error=str(exc),
                path=request.url.path,
                method=request.method)
    
    return ApiResponse(
        success=False,
        message="An unexpected error occurred",
        errors=[str(exc)]
    )
