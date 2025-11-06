"""
Enterprise Billing API Endpoints

REST API for enterprise billing operations including:
- Multi-entity billing management
- Department and cost allocation
- Contract management
- Budget tracking and controls
- Approval workflows
- Dispute management
- Financial integration
- Enterprise reporting
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.enterprise_billing_service import EnterpriseBillingService
from app.models.enterprise_billing import (
    EntityType, CostCenterType, ContractType, ContractStatus,
    BudgetPeriod, ApprovalStatus, DisputeStatus, DisputeCategory,
    IntegrationProvider
)
from app.api.deps import get_current_user, require_admin
from app.models.user import User


router = APIRouter(prefix="/api/enterprise-billing", tags=["enterprise-billing"])


# ============================
# Request/Response Schemas
# ============================

class BillingEntityCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    entity_type: EntityType
    parent_entity_id: Optional[int] = None
    tax_id: Optional[str] = None
    billing_address: Optional[dict] = None
    consolidated_billing: bool = False
    currency: str = "EUR"
    payment_terms_days: int = 30


class BillingEntityResponse(BaseModel):
    id: int
    entity_id: str
    name: str
    entity_type: EntityType
    parent_entity_id: Optional[int]
    consolidated_billing: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    department_code: str
    cost_center_code: str
    entity_id: int
    manager_user_id: Optional[int] = None
    cost_center_type: CostCenterType = CostCenterType.OPERATIONAL
    default_gl_code: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: int
    department_id: str
    name: str
    department_code: str
    cost_center_code: str
    entity_id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class CostAllocationCreate(BaseModel):
    department_id: int
    allocation_type: str
    amount: float
    period_start: datetime
    period_end: datetime
    description: Optional[str] = None
    gl_code: Optional[str] = None
    subscription_id: Optional[int] = None
    invoice_id: Optional[int] = None


class ContractCreate(BaseModel):
    name: str
    entity_id: int
    contract_type: ContractType
    start_date: datetime
    term_length_months: int
    contract_value: float
    discount_percent: float = 0
    auto_renew: bool = True
    payment_terms_days: int = 30
    sla_terms: Optional[dict] = None


class ContractResponse(BaseModel):
    id: int
    contract_id: str
    contract_number: str
    name: str
    contract_type: ContractType
    status: ContractStatus
    contract_value: float
    start_date: datetime
    end_date: datetime
    
    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    allocated_amount: float
    period_start: datetime
    period_end: datetime
    entity_id: Optional[int] = None
    department_id: Optional[int] = None
    period_type: BudgetPeriod = BudgetPeriod.MONTHLY
    allow_overspend: bool = False
    alert_threshold_percent: float = 80
    warning_threshold_percent: float = 90


class BudgetResponse(BaseModel):
    id: int
    budget_id: str
    name: str
    allocated_amount: float
    spent_amount: float
    remaining_amount: float
    is_active: bool
    is_frozen: bool
    
    class Config:
        from_attributes = True


class ApprovalRequestCreate(BaseModel):
    request_type: str
    title: str
    description: Optional[str] = None
    amount: float
    contract_id: Optional[int] = None
    budget_id: Optional[int] = None
    department_id: Optional[int] = None
    metadata: Optional[dict] = None


class ApprovalRequestResponse(BaseModel):
    id: int
    request_id: str
    request_type: str
    title: str
    amount: float
    status: ApprovalStatus
    required_approvals: int
    approvals_received: int
    submitted_at: datetime
    
    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    action: str  # approved, rejected
    comments: Optional[str] = None
    rejection_reason: Optional[str] = None


class DisputeCreate(BaseModel):
    title: str
    description: str
    category: DisputeCategory
    disputed_amount: float
    invoice_id: Optional[int] = None
    payment_id: Optional[int] = None
    subscription_id: Optional[int] = None


class DisputeResponse(BaseModel):
    id: int
    dispute_id: str
    title: str
    category: DisputeCategory
    status: DisputeStatus
    disputed_amount: float
    opened_at: datetime
    
    class Config:
        from_attributes = True


# ============================
# Entity Management Endpoints
# ============================

@router.post("/entities", response_model=BillingEntityResponse)
def create_billing_entity(
    entity_data: BillingEntityCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new billing entity"""
    service = EnterpriseBillingService(db)
    try:
        entity = service.create_billing_entity(
            name=entity_data.name,
            tenant_id=current_user.tenant_id if hasattr(current_user, 'tenant_id') else "default",
            entity_type=entity_data.entity_type,
            parent_entity_id=entity_data.parent_entity_id,
            legal_name=entity_data.legal_name,
            tax_id=entity_data.tax_id,
            billing_address=entity_data.billing_address,
            consolidated_billing=entity_data.consolidated_billing,
            currency=entity_data.currency,
            payment_terms_days=entity_data.payment_terms_days
        )
        return entity
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entities", response_model=List[BillingEntityResponse])
def list_billing_entities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all billing entities"""
    from app.models.enterprise_billing import BillingEntity
    entities = db.query(BillingEntity).filter(
        BillingEntity.is_active == True
    ).offset(skip).limit(limit).all()
    return entities


@router.get("/entities/{entity_id}")
def get_billing_entity(
    entity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing entity with hierarchy"""
    service = EnterpriseBillingService(db)
    hierarchy = service.get_entity_hierarchy(entity_id)
    if not hierarchy:
        raise HTTPException(status_code=404, detail="Entity not found")
    return hierarchy


@router.post("/entities/{entity_id}/consolidated-invoice")
def generate_consolidated_invoice(
    entity_id: int,
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Generate consolidated invoice for entity and children"""
    service = EnterpriseBillingService(db)
    try:
        invoice = service.generate_consolidated_invoice(
            parent_entity_id=entity_id,
            period_start=period_start,
            period_end=period_end,
            user_id=current_user.user_id
        )
        return {"invoice_id": invoice.id, "invoice_number": invoice.invoice_number, "total_amount": invoice.total_amount}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================
# Department Management Endpoints
# ============================

@router.post("/departments", response_model=DepartmentResponse)
def create_department(
    dept_data: DepartmentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new department"""
    service = EnterpriseBillingService(db)
    try:
        department = service.create_department(
            name=dept_data.name,
            entity_id=dept_data.entity_id,
            department_code=dept_data.department_code,
            cost_center_code=dept_data.cost_center_code,
            manager_user_id=dept_data.manager_user_id,
            description=dept_data.description,
            cost_center_type=dept_data.cost_center_type,
            default_gl_code=dept_data.default_gl_code
        )
        return department
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    entity_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all departments"""
    from app.models.enterprise_billing import Department
    query = db.query(Department).filter(Department.is_active == True)
    if entity_id:
        query = query.filter(Department.entity_id == entity_id)
    departments = query.offset(skip).limit(limit).all()
    return departments


@router.post("/departments/{department_id}/allocations")
def create_cost_allocation(
    department_id: int,
    allocation_data: CostAllocationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Allocate cost to a department"""
    service = EnterpriseBillingService(db)
    try:
        allocation = service.allocate_cost(
            department_id=allocation_data.department_id,
            allocation_type=allocation_data.allocation_type,
            amount=allocation_data.amount,
            period_start=allocation_data.period_start,
            period_end=allocation_data.period_end,
            subscription_id=allocation_data.subscription_id,
            invoice_id=allocation_data.invoice_id,
            description=allocation_data.description,
            gl_code=allocation_data.gl_code
        )
        return {"allocation_id": allocation.id, "amount": allocation.amount}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/departments/{department_id}/costs")
def get_department_costs(
    department_id: int,
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get department cost summary"""
    service = EnterpriseBillingService(db)
    costs = service.get_department_costs(department_id, period_start, period_end)
    return costs


# ============================
# Contract Management Endpoints
# ============================

@router.post("/contracts", response_model=ContractResponse)
def create_contract(
    contract_data: ContractCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new billing contract"""
    service = EnterpriseBillingService(db)
    try:
        contract = service.create_contract(
            name=contract_data.name,
            entity_id=contract_data.entity_id,
            contract_type=contract_data.contract_type,
            start_date=contract_data.start_date,
            term_length_months=contract_data.term_length_months,
            contract_value=contract_data.contract_value,
            created_by_user_id=current_user.user_id,
            discount_percent=contract_data.discount_percent,
            auto_renew=contract_data.auto_renew,
            payment_terms_days=contract_data.payment_terms_days,
            sla_terms=contract_data.sla_terms
        )
        return contract
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contracts", response_model=List[ContractResponse])
def list_contracts(
    entity_id: Optional[int] = None,
    status: Optional[ContractStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all contracts"""
    from app.models.enterprise_billing import BillingContract
    query = db.query(BillingContract)
    if entity_id:
        query = query.filter(BillingContract.entity_id == entity_id)
    if status:
        query = query.filter(BillingContract.status == status)
    contracts = query.offset(skip).limit(limit).all()
    return contracts


@router.put("/contracts/{contract_id}/activate")
def activate_contract(
    contract_id: int,
    signed_by_customer: str,
    signed_by_vendor: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate a contract"""
    service = EnterpriseBillingService(db)
    try:
        contract = service.activate_contract(contract_id, signed_by_customer, signed_by_vendor)
        return {"contract_id": contract.id, "status": contract.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contracts/{contract_id}/renewal-check")
def check_contract_renewal(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if contract needs renewal"""
    service = EnterpriseBillingService(db)
    renewal_info = service.check_contract_renewal(contract_id)
    if not renewal_info:
        raise HTTPException(status_code=404, detail="Contract not found")
    return renewal_info


# ============================
# Budget Management Endpoints
# ============================

@router.post("/budgets", response_model=BudgetResponse)
def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new budget"""
    service = EnterpriseBillingService(db)
    try:
        budget = service.create_budget(
            name=budget_data.name,
            allocated_amount=budget_data.allocated_amount,
            period_start=budget_data.period_start,
            period_end=budget_data.period_end,
            entity_id=budget_data.entity_id,
            department_id=budget_data.department_id,
            owner_user_id=current_user.user_id,
            description=budget_data.description,
            period_type=budget_data.period_type,
            allow_overspend=budget_data.allow_overspend,
            alert_threshold_percent=budget_data.alert_threshold_percent,
            warning_threshold_percent=budget_data.warning_threshold_percent
        )
        return budget
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budgets", response_model=List[BudgetResponse])
def list_budgets(
    entity_id: Optional[int] = None,
    department_id: Optional[int] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all budgets"""
    from app.models.enterprise_billing import Budget
    query = db.query(Budget).filter(Budget.is_active == is_active)
    if entity_id:
        query = query.filter(Budget.entity_id == entity_id)
    if department_id:
        query = query.filter(Budget.department_id == department_id)
    budgets = query.offset(skip).limit(limit).all()
    return budgets


@router.post("/budgets/{budget_id}/check-availability")
def check_budget_availability(
    budget_id: int,
    amount: float = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if budget has sufficient funds"""
    service = EnterpriseBillingService(db)
    availability = service.check_budget_availability(budget_id, amount)
    return availability


@router.post("/budgets/{budget_id}/charge")
def charge_budget(
    budget_id: int,
    amount: float = Query(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Charge an amount to the budget"""
    service = EnterpriseBillingService(db)
    try:
        budget = service.charge_budget(budget_id, amount)
        return {
            "budget_id": budget.id,
            "spent_amount": budget.spent_amount,
            "remaining_amount": budget.remaining_amount
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budgets/{budget_id}/alerts")
def get_budget_alerts(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get alerts for a budget"""
    from app.models.enterprise_billing import BudgetAlert
    alerts = db.query(BudgetAlert).filter(
        BudgetAlert.budget_id == budget_id,
        BudgetAlert.is_resolved == False
    ).all()
    return alerts


# ============================
# Approval Workflow Endpoints
# ============================

@router.post("/approvals", response_model=ApprovalRequestResponse)
def create_approval_request(
    request_data: ApprovalRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an approval request"""
    service = EnterpriseBillingService(db)
    try:
        request = service.create_approval_request(
            request_type=request_data.request_type,
            title=request_data.title,
            amount=request_data.amount,
            requested_by_user_id=current_user.user_id,
            description=request_data.description,
            contract_id=request_data.contract_id,
            budget_id=request_data.budget_id,
            department_id=request_data.department_id,
            metadata=request_data.metadata
        )
        return request
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approvals", response_model=List[ApprovalRequestResponse])
def list_approval_requests(
    status: Optional[ApprovalStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List approval requests"""
    from app.models.enterprise_billing import ApprovalRequest
    query = db.query(ApprovalRequest)
    if status:
        query = query.filter(ApprovalRequest.status == status)
    # Filter by user's department or if user is approver
    requests = query.offset(skip).limit(limit).all()
    return requests


@router.post("/approvals/{request_id}/action")
def process_approval_action(
    request_id: int,
    action_data: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject an approval request"""
    service = EnterpriseBillingService(db)
    try:
        if action_data.action == "approved":
            request = service.approve_request(
                request_id=request_id,
                approver_user_id=current_user.user_id,
                comments=action_data.comments
            )
        elif action_data.action == "rejected":
            request = service.reject_request(
                request_id=request_id,
                approver_user_id=current_user.user_id,
                reason=action_data.rejection_reason or "Rejected by approver",
                comments=action_data.comments
            )
        else:
            raise ValueError("Invalid action")
        
        return {"request_id": request.id, "status": request.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approvals/{request_id}/history")
def get_approval_history(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get approval action history"""
    from app.models.enterprise_billing import ApprovalAction
    actions = db.query(ApprovalAction).filter(
        ApprovalAction.request_id == request_id
    ).all()
    return actions


# ============================
# Dispute Management Endpoints
# ============================

@router.post("/disputes", response_model=DisputeResponse)
def create_dispute(
    dispute_data: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a billing dispute"""
    service = EnterpriseBillingService(db)
    try:
        dispute = service.create_dispute(
            title=dispute_data.title,
            description=dispute_data.description,
            category=dispute_data.category,
            disputed_amount=dispute_data.disputed_amount,
            raised_by_user_id=current_user.user_id,
            invoice_id=dispute_data.invoice_id,
            payment_id=dispute_data.payment_id,
            subscription_id=dispute_data.subscription_id
        )
        return dispute
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/disputes", response_model=List[DisputeResponse])
def list_disputes(
    status: Optional[DisputeStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all disputes"""
    from app.models.enterprise_billing import BillingDispute
    query = db.query(BillingDispute)
    if status:
        query = query.filter(BillingDispute.status == status)
    disputes = query.offset(skip).limit(limit).all()
    return disputes


@router.post("/disputes/{dispute_id}/comments")
def add_dispute_comment(
    dispute_id: int,
    comment: str,
    is_internal: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a dispute"""
    service = EnterpriseBillingService(db)
    try:
        comment_obj = service.add_dispute_comment(
            dispute_id=dispute_id,
            author_user_id=current_user.user_id,
            comment=comment,
            is_internal=is_internal
        )
        return {"comment_id": comment_obj.id, "created_at": comment_obj.created_at}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/disputes/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: int,
    resolution: str,
    resolution_type: str,
    credit_amount: float = 0,
    refund_amount: float = 0,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Resolve a billing dispute"""
    service = EnterpriseBillingService(db)
    try:
        dispute = service.resolve_dispute(
            dispute_id=dispute_id,
            resolution=resolution,
            resolution_type=resolution_type,
            credit_amount=credit_amount,
            refund_amount=refund_amount
        )
        return {"dispute_id": dispute.id, "status": dispute.status, "resolved_at": dispute.resolved_at}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================
# Financial Integration Endpoints
# ============================

@router.post("/integrations")
def create_financial_integration(
    name: str,
    provider: IntegrationProvider,
    entity_id: int,
    api_endpoint: str,
    credentials: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a financial system integration"""
    service = EnterpriseBillingService(db)
    try:
        integration = service.create_financial_integration(
            name=name,
            provider=provider,
            entity_id=entity_id,
            api_endpoint=api_endpoint,
            credentials=credentials  # Should be encrypted
        )
        return {"integration_id": integration.id, "integration_id_string": integration.integration_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/integrations")
def list_financial_integrations(
    entity_id: Optional[int] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all financial integrations"""
    from app.models.enterprise_billing import FinancialIntegration
    query = db.query(FinancialIntegration).filter(FinancialIntegration.is_active == True)
    if entity_id:
        query = query.filter(FinancialIntegration.entity_id == entity_id)
    integrations = query.all()
    return integrations


@router.post("/integrations/{integration_id}/sync")
def sync_to_financial_system(
    integration_id: int,
    sync_type: str = "invoice",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Trigger sync to financial system"""
    service = EnterpriseBillingService(db)
    try:
        sync_log = service.sync_to_financial_system(integration_id, sync_type)
        return {
            "sync_log_id": sync_log.id,
            "status": sync_log.status,
            "records_processed": sync_log.records_processed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/integrations/{integration_id}/logs")
def get_integration_sync_logs(
    integration_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get sync logs for an integration"""
    from app.models.enterprise_billing import IntegrationSyncLog
    logs = db.query(IntegrationSyncLog).filter(
        IntegrationSyncLog.integration_id == integration_id
    ).order_by(IntegrationSyncLog.started_at.desc()).limit(limit).all()
    return logs


# ============================
# Enterprise Reporting Endpoints
# ============================

@router.post("/reports")
def generate_enterprise_report(
    report_name: str,
    report_type: str,
    period_start: datetime,
    period_end: datetime,
    entity_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an enterprise report"""
    service = EnterpriseBillingService(db)
    try:
        report = service.generate_enterprise_report(
            report_name=report_name,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            generated_by_user_id=current_user.user_id,
            entity_id=entity_id
        )
        return {
            "report_id": report.id,
            "report_id_string": report.report_id,
            "status": report.status,
            "report_data": report.report_data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports")
def list_enterprise_reports(
    report_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all enterprise reports"""
    from app.models.enterprise_billing import EnterpriseReport
    query = db.query(EnterpriseReport)
    if report_type:
        query = query.filter(EnterpriseReport.report_type == report_type)
    if entity_id:
        query = query.filter(EnterpriseReport.entity_id == entity_id)
    reports = query.order_by(EnterpriseReport.created_at.desc()).offset(skip).limit(limit).all()
    return reports


@router.get("/reports/{report_id}")
def get_enterprise_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific enterprise report"""
    from app.models.enterprise_billing import EnterpriseReport
    report = db.query(EnterpriseReport).filter(EnterpriseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ============================
# Dashboard & Analytics
# ============================

@router.get("/dashboard/summary")
def get_enterprise_dashboard_summary(
    entity_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enterprise billing dashboard summary"""
    from app.models.enterprise_billing import Budget, BillingContract, ApprovalRequest
    from sqlalchemy import func
    
    # Budget summary
    budget_query = db.query(
        func.count(Budget.id).label("total_budgets"),
        func.sum(Budget.allocated_amount).label("total_allocated"),
        func.sum(Budget.spent_amount).label("total_spent")
    ).filter(Budget.is_active == True)
    
    if entity_id:
        budget_query = budget_query.filter(Budget.entity_id == entity_id)
    
    budget_summary = budget_query.first()
    
    # Contract summary
    contract_query = db.query(
        func.count(BillingContract.id).label("total_contracts"),
        func.sum(BillingContract.contract_value).label("total_value")
    ).filter(BillingContract.status == ContractStatus.ACTIVE)
    
    if entity_id:
        contract_query = contract_query.filter(BillingContract.entity_id == entity_id)
    
    contract_summary = contract_query.first()
    
    # Pending approvals
    pending_approvals = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == ApprovalStatus.PENDING
    ).scalar()
    
    return {
        "budgets": {
            "total_count": budget_summary.total_budgets or 0,
            "total_allocated": budget_summary.total_allocated or 0,
            "total_spent": budget_summary.total_spent or 0,
            "utilization_percent": (budget_summary.total_spent / budget_summary.total_allocated * 100) if budget_summary.total_allocated else 0
        },
        "contracts": {
            "total_count": contract_summary.total_contracts or 0,
            "total_value": contract_summary.total_value or 0
        },
        "approvals": {
            "pending_count": pending_approvals or 0
        }
    }
