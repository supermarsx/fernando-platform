"""
Revenue Operations API Endpoints

Comprehensive REST API for revenue analytics, predictive models, financial compliance,
and automated accounting integration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.services.revenue_analytics_service import RevenueAnalyticsService, PredictiveAnalyticsService
from app.services.financial_compliance_service import (
    RevenueRecognitionService, TaxComplianceService, ARAPService, FinancialAuditService
)
from app.models.revenue_operations import (
    RevenueMetricType, ChurnRiskLevel, RevenueRecognitionMethod, TaxJurisdiction
)

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class RevenueMetricsResponse(BaseModel):
    mrr: str
    arr: str
    new_revenue: str
    expansion_revenue: str
    contraction_revenue: str
    churn_revenue: str
    growth_rate: float
    nrr: float

class LTVResponse(BaseModel):
    user_id: int
    historical_ltv: str
    predicted_ltv: str
    ltv_cac_ratio: float
    payback_period_months: float
    confidence_score: float

class ChurnPredictionResponse(BaseModel):
    user_id: int
    churn_probability: float
    risk_level: str
    predicted_churn_date: Optional[date]
    risk_factors: List[dict]
    recommended_interventions: List[dict]

class RevenueRecognitionResponse(BaseModel):
    id: int
    invoice_id: int
    total_contract_value: str
    recognized_revenue: str
    deferred_revenue: str
    completion_percentage: float
    is_complete: bool

class TaxComplianceResponse(BaseModel):
    id: int
    jurisdiction: str
    tax_period_start: date
    tax_period_end: date
    taxable_revenue: str
    tax_amount: str
    filing_status: str

class ARAgingResponse(BaseModel):
    aging_summary: dict
    total_outstanding: str
    record_count: int


# ============================================================================
# REVENUE ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/metrics", response_model=RevenueMetricsResponse)
def get_revenue_metrics(
    tenant_id: str = Query(...),
    period_start: date = Query(None),
    period_end: date = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive revenue metrics (MRR, ARR, expansion, contraction)
    """
    if not period_end:
        period_end = date.today()
    if not period_start:
        period_start = period_end - timedelta(days=30)
    
    service = RevenueAnalyticsService(db)
    
    mrr = service.calculate_mrr(tenant_id, period_end)
    arr = service.calculate_arr(tenant_id, period_end)
    breakdown = service.calculate_revenue_breakdown(tenant_id, period_start, period_end)
    nrr = service.calculate_nrr(tenant_id)
    
    prev_mrr = service.calculate_mrr(tenant_id, period_start - timedelta(days=1))
    growth_rate = float((mrr - prev_mrr) / prev_mrr) if prev_mrr > 0 else 0.0
    
    return RevenueMetricsResponse(
        mrr=str(mrr),
        arr=str(arr),
        new_revenue=str(breakdown["new_revenue"]),
        expansion_revenue=str(breakdown["expansion_revenue"]),
        contraction_revenue=str(breakdown["contraction_revenue"]),
        churn_revenue=str(breakdown["churn_revenue"]),
        growth_rate=growth_rate,
        nrr=nrr
    )


@router.post("/analytics/metrics/calculate")
def calculate_and_save_metrics(
    tenant_id: str,
    period_start: date,
    period_end: date,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Calculate and persist revenue metrics
    """
    service = RevenueAnalyticsService(db)
    metric = service.save_revenue_metrics(tenant_id, period_start, period_end)
    
    return {
        "id": metric.id,
        "metric_type": metric.metric_type,
        "value": str(metric.value),
        "growth_rate": metric.growth_rate,
        "period_start": metric.period_start.isoformat(),
        "period_end": metric.period_end.isoformat()
    }


# ============================================================================
# PREDICTIVE ANALYTICS ENDPOINTS  
# ============================================================================

@router.get("/predictive/ltv/{user_id}", response_model=LTVResponse)
def get_customer_ltv(
    user_id: int,
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get customer lifetime value prediction
    """
    service = PredictiveAnalyticsService(db)
    ltv = service.calculate_customer_ltv(tenant_id, user_id)
    
    if not ltv:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return LTVResponse(
        user_id=ltv.user_id,
        historical_ltv=str(ltv.historical_ltv),
        predicted_ltv=str(ltv.predicted_ltv),
        ltv_cac_ratio=ltv.ltv_cac_ratio,
        payback_period_months=ltv.payback_period_months,
        confidence_score=ltv.ltv_confidence_score
    )


@router.get("/predictive/churn/{user_id}", response_model=ChurnPredictionResponse)
def get_churn_prediction(
    user_id: int,
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get customer churn prediction with risk factors
    """
    service = PredictiveAnalyticsService(db)
    prediction = service.predict_churn(tenant_id, user_id)
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return ChurnPredictionResponse(
        user_id=prediction.user_id,
        churn_probability=prediction.churn_probability,
        risk_level=prediction.risk_level,
        predicted_churn_date=prediction.predicted_churn_date,
        risk_factors=prediction.risk_factors,
        recommended_interventions=prediction.recommended_interventions
    )


@router.get("/predictive/churn/at-risk")
def get_at_risk_customers(
    tenant_id: str = Query(...),
    risk_level: Optional[str] = Query(None),
    min_probability: float = Query(0.5),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of at-risk customers
    """
    from app.models.revenue_operations import ChurnPrediction
    
    query = db.query(ChurnPrediction).filter(
        ChurnPrediction.tenant_id == tenant_id,
        ChurnPrediction.churn_probability >= min_probability
    )
    
    if risk_level:
        query = query.filter(ChurnPrediction.risk_level == risk_level)
    
    predictions = query.order_by(ChurnPrediction.churn_probability.desc()).all()
    
    return {
        "at_risk_count": len(predictions),
        "customers": [
            {
                "user_id": p.user_id,
                "churn_probability": p.churn_probability,
                "risk_level": p.risk_level,
                "risk_factors": p.risk_factors[:3]  # Top 3 factors
            }
            for p in predictions
        ]
    }


# ============================================================================
# REVENUE RECOGNITION ENDPOINTS (ASC 606)
# ============================================================================

@router.post("/revenue-recognition/create", response_model=RevenueRecognitionResponse)
def create_recognition_schedule(
    invoice_id: int,
    tenant_id: str,
    contract_id: Optional[int] = None,
    method: RevenueRecognitionMethod = RevenueRecognitionMethod.OVER_TIME,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create ASC 606 revenue recognition schedule
    """
    service = RevenueRecognitionService(db)
    recognition = service.create_recognition_schedule(
        tenant_id, invoice_id, contract_id, method
    )
    
    return RevenueRecognitionResponse(
        id=recognition.id,
        invoice_id=recognition.invoice_id,
        total_contract_value=str(recognition.total_contract_value),
        recognized_revenue=str(recognition.recognized_revenue),
        deferred_revenue=str(recognition.deferred_revenue),
        completion_percentage=recognition.completion_percentage,
        is_complete=recognition.is_complete
    )


@router.post("/revenue-recognition/{recognition_id}/recognize")
def recognize_revenue(
    recognition_id: int,
    period_date: Optional[date] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Recognize revenue for a period
    """
    service = RevenueRecognitionService(db)
    result = service.recognize_revenue(recognition_id, period_date)
    
    return result


@router.get("/revenue-recognition/deferred-revenue")
def get_deferred_revenue(
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get total deferred revenue
    """
    from app.models.revenue_operations import RevenueRecognition
    
    recognitions = db.query(RevenueRecognition).filter(
        RevenueRecognition.tenant_id == tenant_id,
        RevenueRecognition.is_complete == False
    ).all()
    
    total_deferred = sum([r.deferred_revenue for r in recognitions])
    
    return {
        "total_deferred_revenue": str(total_deferred),
        "contract_count": len(recognitions),
        "contracts": [
            {
                "id": r.id,
                "invoice_id": r.invoice_id,
                "deferred_revenue": str(r.deferred_revenue),
                "completion_percentage": r.completion_percentage
            }
            for r in recognitions
        ]
    }


# ============================================================================
# TAX COMPLIANCE ENDPOINTS
# ============================================================================

@router.post("/tax/calculate", response_model=TaxComplianceResponse)
def calculate_tax_liability(
    tenant_id: str,
    jurisdiction: TaxJurisdiction,
    period_start: date,
    period_end: date,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Calculate tax liability for jurisdiction and period
    """
    service = TaxComplianceService(db)
    tax_record = service.calculate_tax_liability(
        tenant_id, jurisdiction, period_start, period_end
    )
    
    return TaxComplianceResponse(
        id=tax_record.id,
        jurisdiction=tax_record.jurisdiction,
        tax_period_start=tax_record.tax_period_start,
        tax_period_end=tax_record.tax_period_end,
        taxable_revenue=str(tax_record.taxable_revenue),
        tax_amount=str(tax_record.tax_amount),
        filing_status=tax_record.filing_status
    )


@router.get("/tax/summary")
def get_tax_summary(
    tenant_id: str = Query(...),
    year: int = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get annual tax summary
    """
    from app.models.revenue_operations import TaxCompliance
    
    tax_records = db.query(TaxCompliance).filter(
        TaxCompliance.tenant_id == tenant_id,
        TaxCompliance.tax_period_start >= date(year, 1, 1),
        TaxCompliance.tax_period_end <= date(year, 12, 31)
    ).all()
    
    summary_by_jurisdiction = {}
    for record in tax_records:
        jurisdiction = record.jurisdiction
        if jurisdiction not in summary_by_jurisdiction:
            summary_by_jurisdiction[jurisdiction] = {
                "taxable_revenue": 0,
                "tax_amount": 0,
                "periods": 0
            }
        
        summary_by_jurisdiction[jurisdiction]["taxable_revenue"] += float(record.taxable_revenue)
        summary_by_jurisdiction[jurisdiction]["tax_amount"] += float(record.tax_amount)
        summary_by_jurisdiction[jurisdiction]["periods"] += 1
    
    return {
        "year": year,
        "summary_by_jurisdiction": summary_by_jurisdiction,
        "total_tax": sum([v["tax_amount"] for v in summary_by_jurisdiction.values()])
    }


# ============================================================================
# AR/AP ENDPOINTS
# ============================================================================

@router.post("/ar/create")
def create_ar_record(
    tenant_id: str,
    invoice_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create Accounts Receivable record
    """
    service = ARAPService(db)
    ar_record = service.create_ar_record(tenant_id, invoice_id)
    
    return {
        "id": ar_record.id,
        "invoice_id": ar_record.invoice_id,
        "amount_outstanding": str(ar_record.amount_outstanding),
        "days_outstanding": ar_record.days_outstanding,
        "aging_bucket": ar_record.aging_bucket
    }


@router.get("/ar/aging-report", response_model=ARAgingResponse)
def get_ar_aging_report(
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get AR aging report
    """
    service = ARAPService(db)
    report = service.get_ar_aging_report(tenant_id)
    
    return ARAgingResponse(**report)


@router.get("/ar/overdue")
def get_overdue_invoices(
    tenant_id: str = Query(...),
    days_overdue: int = Query(30),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get overdue invoices
    """
    from app.models.revenue_operations import AccountsReceivable
    
    overdue = db.query(AccountsReceivable).filter(
        AccountsReceivable.tenant_id == tenant_id,
        AccountsReceivable.status == "outstanding",
        AccountsReceivable.days_outstanding >= days_overdue
    ).order_by(AccountsReceivable.days_outstanding.desc()).all()
    
    return {
        "overdue_count": len(overdue),
        "total_amount": str(sum([r.amount_outstanding for r in overdue])),
        "invoices": [
            {
                "invoice_id": r.invoice_id,
                "customer_id": r.customer_id,
                "amount": str(r.amount_outstanding),
                "days_overdue": r.days_outstanding,
                "aging_bucket": r.aging_bucket
            }
            for r in overdue
        ]
    }


# ============================================================================
# AUDIT TRAIL ENDPOINTS
# ============================================================================

@router.get("/audit/verify-chain")
def verify_audit_chain(
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Verify integrity of financial audit chain
    """
    service = FinancialAuditService(db)
    verification = service.verify_audit_chain(tenant_id)
    
    return verification


@router.get("/audit/logs")
def get_audit_logs(
    tenant_id: str = Query(...),
    event_category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get financial audit logs
    """
    from app.models.revenue_operations import FinancialAuditLog
    
    query = db.query(FinancialAuditLog).filter(
        FinancialAuditLog.tenant_id == tenant_id
    )
    
    if event_category:
        query = query.filter(FinancialAuditLog.event_category == event_category)
    
    if start_date:
        query = query.filter(FinancialAuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(FinancialAuditLog.timestamp <= datetime.combine(end_date, datetime.max.time()))
    
    logs = query.order_by(FinancialAuditLog.timestamp.desc()).limit(limit).all()
    
    return {
        "log_count": len(logs),
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "user_email": log.user_email,
                "timestamp": log.timestamp.isoformat(),
                "record_hash": log.record_hash[:16] + "..."
            }
            for log in logs
        ]
    }


# ============================================================================
# CFO DASHBOARD ENDPOINT
# ============================================================================

@router.get("/dashboard/cfo")
def get_cfo_dashboard(
    tenant_id: str = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive CFO dashboard with all key metrics
    """
    analytics_service = RevenueAnalyticsService(db)
    ar_service = ARAPService(db)
    
    # Revenue metrics
    today = date.today()
    period_start = today - timedelta(days=30)
    
    mrr = analytics_service.calculate_mrr(tenant_id, today)
    arr = analytics_service.calculate_arr(tenant_id, today)
    nrr = analytics_service.calculate_nrr(tenant_id)
    breakdown = analytics_service.calculate_revenue_breakdown(tenant_id, period_start, today)
    
    # AR metrics
    ar_report = ar_service.get_ar_aging_report(tenant_id)
    
    # Churn metrics
    from app.models.revenue_operations import ChurnPrediction
    at_risk = db.query(ChurnPrediction).filter(
        ChurnPrediction.tenant_id == tenant_id,
        ChurnPrediction.risk_level.in_(["high", "critical"])
    ).count()
    
    # Deferred revenue
    from app.models.revenue_operations import RevenueRecognition
    deferred_contracts = db.query(RevenueRecognition).filter(
        RevenueRecognition.tenant_id == tenant_id,
        RevenueRecognition.is_complete == False
    ).all()
    total_deferred = sum([r.deferred_revenue for r in deferred_contracts])
    
    return {
        "period": {
            "start": period_start.isoformat(),
            "end": today.isoformat()
        },
        "revenue_metrics": {
            "mrr": str(mrr),
            "arr": str(arr),
            "nrr": nrr,
            "new_business": str(breakdown["new_revenue"]),
            "expansion": str(breakdown["expansion_revenue"]),
            "contraction": str(breakdown["contraction_revenue"]),
            "churn": str(breakdown["churn_revenue"])
        },
        "ar_metrics": {
            "total_outstanding": ar_report["total_outstanding"],
            "aging_summary": ar_report["aging_summary"]
        },
        "customer_health": {
            "at_risk_customers": at_risk
        },
        "deferred_revenue": {
            "total": str(total_deferred),
            "contract_count": len(deferred_contracts)
        }
    }
