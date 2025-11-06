"""
Credit System API Endpoints

Comprehensive credit management endpoints including:
- Credit balance and transaction endpoints
- LLM usage tracking endpoints  
- Credit purchase and allocation endpoints
- Credit transfer and policy endpoints
- Credit analytics and reporting endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.user import User
from app.models.credit import (
    CreditAccount, CreditTransaction, CreditPolicy, CreditUsageRecord,
    CreditAlert, LLMUsageMetrics
)
from app.schemas.credit_schemas import (
    CreditAccount as CreditAccountSchema,
    CreditAccountCreate, CreditAccountUpdate,
    CreditTransaction as CreditTransactionSchema,
    CreditTransactionCreate,
    CreditPolicy as CreditPolicySchema,
    CreditPolicyCreate, CreditPolicyUpdate,
    CreditUsageRecord as CreditUsageRecordSchema,
    CreditUsageRecordCreate,
    CreditAlert as CreditAlertSchema,
    CreditAlertCreate, CreditAlertUpdate,
    CreditForecast as CreditForecastSchema,
    CreditForecastCreate,
    LLMUsageMetrics as LLMUsageMetricsSchema,
    LLMUsageMetricsCreate,
    BulkCreditOperation, CreditTransferRequest,
    CreditAnalyticsRequest, CreditUsageSummary,
    CreditBalanceProjection, CreditValidationRequest,
    CreditValidationResponse,
    CreditTransactionType, CreditPolicyType
)
from app.services.credit_service import CreditService
from app.services.usage_tracking.llm_usage_tracker import LLMUsageTracker
from app.services.usage_tracking.cost_calculator import CostCalculator
from app.services.usage_tracking.usage_analytics import UsageAnalytics
from app.services.usage_tracking.forecasting_engine import ForecastingEngine
from app.middleware.credit_validation import CreditValidator
from app.core.auth import get_current_user, get_current_admin_user
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel

router = APIRouter(prefix="/api/credits", tags=["credits"])


# Dependency to get services
def get_credit_services(db: Session = Depends(get_db)):
    """Get all credit-related services"""
    credit_service = CreditService(db)
    usage_tracker = LLMUsageTracker(db, credit_service)
    cost_calculator = CostCalculator()
    usage_analytics = UsageAnalytics(db)
    forecasting_engine = ForecastingEngine(db)
    credit_validator = CreditValidator(db)
    
    return {
        "credit_service": credit_service,
        "usage_tracker": usage_tracker,
        "cost_calculator": cost_calculator,
        "usage_analytics": usage_analytics,
        "forecasting_engine": forecasting_engine,
        "credit_validator": credit_validator
    }


# =============================================================================
# CREDIT ACCOUNT ENDPOINTS
# =============================================================================

@router.post("/accounts", response_model=CreditAccountSchema)
async def create_credit_account(
    account_data: CreditAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new credit account"""
    if account_data.user_id != current_user.id:
        # Only allow users to create accounts for themselves unless admin
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create account for another user"
            )
    
    try:
        services = get_credit_services(db)
        credit_account = services["credit_service"].create_credit_account(account_data)
        
        telemetry_event(
            "credit.account_created",
            TelemetryEvent.SYSTEM_EVENT,
            level=TelemetryLevel.INFO,
            user_id=current_user.id,
            metadata={
                "account_id": credit_account.id,
                "user_id": account_data.user_id
            }
        )
        
        return CreditAccountSchema.from_orm(credit_account)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/accounts/{user_id}", response_model=CreditAccountSchema)
async def get_credit_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get credit account for user"""
    # Users can only access their own account unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's credit account"
            )
    
    services = get_credit_services(db)
    credit_account = services["credit_service"].get_credit_account(user_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    return CreditAccountSchema.from_orm(credit_account)


@router.patch("/accounts/{user_id}", response_model=CreditAccountSchema)
async def update_credit_account(
    user_id: int,
    update_data: CreditAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update credit account settings"""
    # Users can only update their own account unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update another user's credit account"
            )
    
    services = get_credit_services(db)
    updated_account = services["credit_service"].update_credit_account(user_id, update_data)
    
    if not updated_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    return CreditAccountSchema.from_orm(updated_account)


# =============================================================================
# TRANSACTION ENDPOINTS
# =============================================================================

@router.post("/transactions", response_model=CreditTransactionSchema)
async def create_transaction(
    transaction_data: CreditTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new credit transaction"""
    # Get credit account to verify user access
    services = get_credit_services(db)
    credit_account = services["credit_service"].get_credit_account(transaction_data.account_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    # Verify user has access to this account
    if credit_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create transactions for another user's account"
            )
    
    try:
        # Create transaction based on type
        if transaction_data.transaction_type == CreditTransactionType.PURCHASE:
            result_account = services["credit_service"].add_credits(
                user_id=credit_account.user_id,
                amount=transaction_data.amount,
                transaction_type=transaction_data.transaction_type,
                description=transaction_data.description,
                reference_id=transaction_data.reference_id,
                reference_type=transaction_data.reference_type,
                llm_model=transaction_data.llm_model,
                tokens_used=transaction_data.tokens_used,
                cost_per_token=transaction_data.cost_per_token,
                metadata=transaction_data.metadata
            )
        elif transaction_data.transaction_type == CreditTransactionType.USAGE_DEDUCTION:
            result_account = services["credit_service"].deduct_credits(
                user_id=credit_account.user_id,
                amount=transaction_data.amount,
                transaction_type=transaction_data.transaction_type,
                description=transaction_data.description,
                reference_id=transaction_data.reference_id,
                reference_type=transaction_data.reference_type,
                llm_model=transaction_data.llm_model,
                tokens_used=transaction_data.tokens_used,
                cost_per_token=transaction_data.cost_per_token,
                metadata=transaction_data.metadata
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction type not supported via API"
            )
        
        # Get the created transaction
        transactions, _ = services["credit_service"].get_transaction_history(
            user_id=credit_account.user_id, limit=1
        )
        
        if transactions:
            return CreditTransactionSchema.from_orm(transactions[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transaction created but not found"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/transactions/{user_id}", response_model=List[CreditTransactionSchema])
async def get_transaction_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    transaction_type: Optional[CreditTransactionType] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transaction history for user"""
    # Users can only access their own transactions unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's transactions"
            )
    
    services = get_credit_services(db)
    transactions, total = services["credit_service"].get_transaction_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type
    )
    
    return [CreditTransactionSchema.from_orm(t) for t in transactions]


# =============================================================================
# USAGE TRACKING ENDPOINTS
# =============================================================================

@router.post("/usage", response_model=CreditUsageRecordSchema)
async def record_usage(
    usage_data: CreditUsageRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record usage and deduct credits"""
    # Get credit account to verify user access
    services = get_credit_services(db)
    credit_account = services["credit_service"].get_credit_account(usage_data.account_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    # Verify user has access to this account
    if credit_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot record usage for another user's account"
            )
    
    try:
        usage_record = services["credit_service"].record_usage(
            user_id=credit_account.user_id,
            usage_data=usage_data
        )
        
        return CreditUsageRecordSchema.from_orm(usage_record)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/usage/{user_id}/summary")
async def get_usage_summary(
    user_id: int,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage summary for user"""
    # Users can only access their own summary unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's usage summary"
            )
    
    services = get_credit_services(db)
    usage_summary = services["credit_service"].get_usage_summary(user_id, start_date, end_date)
    
    return usage_summary.dict()


@router.get("/usage/{user_id}/real-time")
async def get_real_time_usage(
    user_id: int,
    time_window_minutes: int = Query(60, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time usage statistics"""
    # Users can only access their own usage unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's real-time usage"
            )
    
    services = get_credit_services(db)
    real_time_usage = services["usage_tracker"].get_real_time_usage(user_id, time_window_minutes)
    
    return real_time_usage


@router.post("/usage/analytics")
async def get_usage_analytics(
    request: CreditAnalyticsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive usage analytics"""
    # Verify user access
    if request.account_id:
        # Check if user has access to this account
        services = get_credit_services(db)
        credit_account = services["credit_service"].get_credit_account_by_id(request.account_id)
        
        if not credit_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit account not found"
            )
        
        if credit_account.user_id != current_user.id:
            current_admin = get_current_admin_user(current_user)
            if not current_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access another user's analytics"
                )
        
        user_id = credit_account.user_id
    elif request.organization_id:
        # Check organization access
        # This would require organization membership verification
        user_id = None
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify account_id or organization_id"
        )
    
    services = get_credit_services(db)
    analytics = services["usage_analytics"].generate_comprehensive_report(
        user_id=user_id,
        organization_id=request.organization_id,
        days_back=30
    )
    
    return analytics


# =============================================================================
# CREDIT FORECASTING ENDPOINTS
# =============================================================================

@router.get("/forecast/{user_id}")
async def forecast_usage(
    user_id: int,
    period: str = Query("next_month", regex="^(next_day|next_week|next_month|next_quarter)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate usage forecast"""
    # Users can only access their own forecast unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's forecast"
            )
    
    services = get_credit_services(db)
    
    # Convert period string to enum
    from app.services.usage_tracking.forecasting_engine import ForecastPeriod
    period_map = {
        "next_day": ForecastPeriod.NEXT_DAY,
        "next_week": ForecastPeriod.NEXT_WEEK,
        "next_month": ForecastPeriod.NEXT_MONTH,
        "next_quarter": ForecastPeriod.NEXT_QUARTER
    }
    
    forecast = services["forecasting_engine"].forecast_usage(
        user_id=user_id,
        forecast_period=period_map[period]
    )
    
    return forecast


@router.get("/forecast/{user_id}/balance")
async def forecast_credit_balance(
    user_id: int,
    forecast_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Forecast credit balance"""
    # Users can only access their own balance unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's balance forecast"
            )
    
    services = get_credit_services(db)
    credit_account = services["credit_service"].get_credit_account(user_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    balance_forecast = services["forecasting_engine"].forecast_credit_balance(
        user_id=user_id,
        current_balance=credit_account.current_balance,
        forecast_days=forecast_days
    )
    
    return balance_forecast


@router.post("/forecast/optimization")
async def forecast_cost_optimization(
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    optimization_scenarios: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Forecast cost optimization scenarios"""
    # Verify access
    if user_id and user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's optimization forecast"
            )
    
    services = get_credit_services(db)
    optimization_forecast = services["forecasting_engine"].forecast_cost_optimization(
        user_id=user_id,
        organization_id=organization_id,
        optimization_scenarios=optimization_scenarios
    )
    
    return optimization_forecast


# =============================================================================
# CREDIT VALIDATION ENDPOINTS
# =============================================================================

@router.post("/validate", response_model=CreditValidationResponse)
async def validate_credits(
    validation_request: CreditValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate credits before operation"""
    # Users can only validate their own credits unless admin
    credit_account = None
    services = get_credit_services(db)
    
    if validation_request.account_id:
        credit_account = services["credit_service"].get_credit_account_by_id(validation_request.account_id)
    else:
        credit_account = services["credit_service"].get_credit_account(validation_request.account_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    if credit_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot validate another user's credits"
            )
    
    try:
        validation_result = services["credit_validator"].validate_credit_balance(
            user_id=credit_account.user_id,
            estimated_cost=validation_request.estimated_cost,
            operation_type=validation_request.operation_type,
            service_type=validation_request.service_type,
            model_type=validation_request.model_type,
            estimated_tokens=validation_request.estimated_tokens
        )
        
        return CreditValidationResponse(**validation_result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =============================================================================
# CREDIT POLICIES ENDPOINTS
# =============================================================================

@router.post("/policies", response_model=CreditPolicySchema)
async def create_credit_policy(
    policy_data: CreditPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create credit policy"""
    # Get credit account to verify access
    services = get_credit_services(db)
    credit_account = services["credit_service"].get_credit_account(policy_data.account_id)
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit account not found"
        )
    
    # Verify user has access
    if credit_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create policies for another user's account"
            )
    
    try:
        policy = services["credit_service"].create_credit_policy(policy_data)
        return CreditPolicySchema.from_orm(policy)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/policies/{user_id}", response_model=List[CreditPolicySchema])
async def get_credit_policies(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get credit policies for user"""
    # Users can only access their own policies unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's credit policies"
            )
    
    services = get_credit_services(db)
    policies = services["credit_service"].get_user_policies(user_id)
    
    return [CreditPolicySchema.from_orm(p) for p in policies]


# =============================================================================
# CREDIT TRANSFERS ENDPOINTS
# =============================================================================

@router.post("/transfer")
async def transfer_credits(
    transfer_request: CreditTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfer credits between users"""
    # Verify user owns the source account
    services = get_credit_services(db)
    from_account = services["credit_service"].get_credit_account(transfer_request.from_account_id)
    to_account = services["credit_service"].get_credit_account(transfer_request.to_account_id)
    
    if not from_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source credit account not found"
        )
    
    if not to_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination credit account not found"
        )
    
    # Verify user has access to source account
    if from_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot transfer from another user's account"
            )
    
    try:
        from_account, to_account = services["credit_service"].transfer_credits(
            from_user_id=from_account.user_id,
            to_user_id=to_account.user_id,
            amount=transfer_request.amount,
            reason=transfer_request.reason
        )
        
        return {
            "success": True,
            "from_account_balance": from_account.current_balance,
            "to_account_balance": to_account.current_balance,
            "transferred_amount": transfer_request.amount
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =============================================================================
# CREDIT ALERTS ENDPOINTS
# =============================================================================

@router.get("/alerts/{user_id}", response_model=List[CreditAlertSchema])
async def get_credit_alerts(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active credit alerts for user"""
    # Users can only access their own alerts unless admin
    if user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's alerts"
            )
    
    services = get_credit_services(db)
    alerts = services["credit_service"].get_active_alerts(user_id)
    
    return [CreditAlertSchema.from_orm(a) for a in alerts]


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_credit_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve a credit alert"""
    services = get_credit_services(db)
    
    # Verify user owns the alert
    alert = db.query(CreditAlert).filter(CreditAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    credit_account = services["credit_service"].get_credit_account_by_id(alert.account_id)
    if credit_account.user_id != current_user.id:
        current_admin = get_current_admin_user(current_user)
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot resolve another user's alerts"
            )
    
    success = services["credit_service"].resolve_alert(alert_id, current_user.id, resolution_notes)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resolve alert"
        )
    
    return {"success": True, "message": "Alert resolved successfully"}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/admin/bulk-operation")
async def bulk_credit_operation(
    operation: BulkCreditOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Perform bulk credit operations (admin only)"""
    services = get_credit_services(db)
    
    results = []
    for account_id in operation.account_ids:
        try:
            if operation.operation_type == "add":
                services["credit_service"].add_credits(
                    user_id=services["credit_service"].get_credit_account_by_id(account_id).user_id,
                    amount=operation.amount,
                    transaction_type=CreditTransactionType.ADJUSTMENT,
                    description=operation.reason,
                    metadata=operation.metadata
                )
            elif operation.operation_type == "deduct":
                services["credit_service"].deduct_credits(
                    user_id=services["credit_service"].get_credit_account_by_id(account_id).user_id,
                    amount=operation.amount,
                    transaction_type=CreditTransactionType.ADJUSTMENT,
                    description=operation.reason,
                    metadata=operation.metadata
                )
            
            results.append({"account_id": account_id, "status": "success"})
        
        except Exception as e:
            results.append({"account_id": account_id, "status": "error", "error": str(e)})
    
    return {"results": results}


@router.get("/admin/usage-metrics")
async def get_admin_usage_metrics(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    aggregation_period: str = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get aggregated usage metrics (admin only)"""
    services = get_credit_services(db)
    
    # Convert period string to enum
    from app.services.usage_tracking.usage_analytics import AnalyticsPeriod
    period_map = {
        "hourly": AnalyticsPeriod.HOURLY,
        "daily": AnalyticsPeriod.DAILY,
        "weekly": AnalyticsPeriod.WEEKLY,
        "monthly": AnalyticsPeriod.MONTHLY
    }
    
    metrics = services["usage_tracker"].aggregate_usage_metrics(
        aggregation_period=period_map[aggregation_period],
        start_time=start_date,
        end_time=end_date
    )
    
    return {"metrics": [m.__dict__ for m in metrics]}


@router.post("/admin/forecasts/alerts")
async def generate_forecast_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate forecast-based alerts for all users (admin only)"""
    services = get_credit_services(db)
    
    # Get all active credit accounts
    credit_accounts = db.query(CreditAccount).filter(
        CreditAccount.status == "active"
    ).all()
    
    alerts_created = []
    
    for account in credit_accounts:
        try:
            alerts = services["forecasting_engine"].generate_alert_forecasts(
                user_id=account.user_id,
                alert_thresholds={
                    "low_balance": 100.0,
                    "high_daily_cost": 50.0,
                    "unusual_usage_spike": 200.0,
                    "budget_exhaustion": 0.0
                }
            )
            
            for alert in alerts:
                # Check if similar alert already exists
                existing_alert = db.query(CreditAlert).filter(
                    and_(
                        CreditAlert.account_id == account.id,
                        CreditAlert.alert_type == alert["alert_type"],
                        CreditAlert.is_active == True,
                        CreditAlert.is_resolved == False
                    )
                ).first()
                
                if not existing_alert:
                    alert_data = CreditAlertCreate(
                        account_id=account.id,
                        alert_type=alert["alert_type"],
                        severity=alert.get("severity", "info"),
                        threshold_value=alert.get("threshold", 0),
                        current_value=alert.get("predicted_cost", 0)
                    )
                    
                    created_alert = services["credit_service"].create_alert(alert_data)
                    alerts_created.append(created_alert.__dict__)
        
        except Exception as e:
            # Log error but continue with other accounts
            continue
    
    return {"alerts_created": len(alerts_created), "alerts": alerts_created}