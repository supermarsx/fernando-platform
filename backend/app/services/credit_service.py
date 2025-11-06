"""
Credit Service

Core credit management service providing:
- Credit balance management
- Transaction processing
- Usage tracking and cost calculation
- Credit policies and allocation
- Analytics and forecasting
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm.attributes import flag_modified

from app.models.credit import (
    CreditAccount, CreditTransaction, CreditPolicy, CreditUsageRecord,
    CreditAlert, CreditForecast, LLMUsageMetrics,
    CreditTransactionType, CreditStatus, CreditPolicyType, LLMModelType
)
from app.models.user import User
from app.models.organization import Organization
from app.schemas.credit_schemas import (
    CreditAccountCreate, CreditAccountUpdate,
    CreditTransactionCreate,
    CreditPolicyCreate, CreditPolicyUpdate,
    CreditUsageRecordCreate,
    CreditAlertCreate, CreditAlertUpdate,
    CreditForecastCreate,
    LLMUsageMetricsCreate,
    CreditAnalyticsRequest, CreditUsageSummary,
    CreditBalanceProjection, CreditValidationResponse,
    LLMModelType as SchemaLLMModelType
)
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel


class CreditService:
    """
    Core service for credit management and operations
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================================================
    # CREDIT ACCOUNT MANAGEMENT
    # ============================================================================
    
    def create_credit_account(self, account_data: CreditAccountCreate) -> CreditAccount:
        """Create a new credit account"""
        # Check if account already exists
        existing = self.db.query(CreditAccount).filter(
            CreditAccount.user_id == account_data.user_id
        ).first()
        
        if existing:
            raise ValueError("Credit account already exists for this user")
        
        # Create new account
        credit_account = CreditAccount(**account_data.dict())
        self.db.add(credit_account)
        self.db.commit()
        self.db.refresh(credit_account)
        
        # Create initial transaction for allocation
        initial_allocation = 1000.0  # Default allocation
        self.add_credits(
            user_id=account_data.user_id,
            amount=initial_allocation,
            transaction_type=CreditTransactionType.ALLOCATION,
            description="Initial credit allocation",
            metadata={"source": "system_setup"}
        )
        
        return credit_account
    
    def get_credit_account(self, user_id: int) -> Optional[CreditAccount]:
        """Get credit account for user"""
        return self.db.query(CreditAccount).filter(
            and_(
                CreditAccount.user_id == user_id,
                CreditAccount.status == CreditStatus.ACTIVE
            )
        ).first()
    
    def get_organization_credit_account(self, organization_id: int) -> Optional[CreditAccount]:
        """Get credit account for organization"""
        return self.db.query(CreditAccount).filter(
            and_(
                CreditAccount.organization_id == organization_id,
                CreditAccount.status == CreditStatus.ACTIVE
            )
        ).first()
    
    def update_credit_account(self, user_id: int, update_data: CreditAccountUpdate) -> Optional[CreditAccount]:
        """Update credit account settings"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return None
        
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(credit_account, field, value)
        
        self.db.commit()
        self.db.refresh(credit_account)
        return credit_account
    
    # ============================================================================
    # CREDIT TRANSACTIONS
    # ============================================================================
    
    def add_credits(
        self,
        user_id: int,
        amount: float,
        transaction_type: CreditTransactionType,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        llm_model: Optional[LLMModelType] = None,
        tokens_used: Optional[int] = None,
        cost_per_token: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditAccount:
        """Add credits to user's account"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            raise ValueError("Credit account not found")
        
        # Create transaction
        transaction = CreditTransaction(
            account_id=credit_account.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=credit_account.current_balance,
            balance_after=credit_account.current_balance + amount,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description,
            llm_model=llm_model,
            tokens_used=tokens_used,
            cost_per_token=cost_per_token,
            metadata=metadata or {}
        )
        
        # Update account
        credit_account.current_balance += amount
        credit_account.total_earned += amount
        credit_account.last_activity = datetime.utcnow()
        
        # Add to database
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Check for alerts
        self._check_balance_alerts(credit_account)
        
        # Log telemetry
        self._log_transaction_telemetry(credit_account, transaction)
        
        return credit_account
    
    def deduct_credits(
        self,
        user_id: int,
        amount: float,
        transaction_type: CreditTransactionType,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        llm_model: Optional[LLMModelType] = None,
        tokens_used: Optional[int] = None,
        cost_per_token: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditAccount:
        """Deduct credits from user's account"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            raise ValueError("Credit account not found")
        
        if credit_account.current_balance < amount:
            raise ValueError(f"Insufficient credits. Current: {credit_account.current_balance}, Required: {amount}")
        
        # Create transaction
        transaction = CreditTransaction(
            account_id=credit_account.id,
            transaction_type=transaction_type,
            amount=-amount,  # Negative for deduction
            balance_before=credit_account.current_balance,
            balance_after=credit_account.current_balance - amount,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description,
            llm_model=llm_model,
            tokens_used=tokens_used,
            cost_per_token=cost_per_token,
            metadata=metadata or {}
        )
        
        # Update account
        credit_account.current_balance -= amount
        credit_account.total_spent += amount
        credit_account.last_activity = datetime.utcnow()
        
        # Add to database
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Check for alerts
        self._check_balance_alerts(credit_account)
        
        # Log telemetry
        self._log_transaction_telemetry(credit_account, transaction)
        
        return credit_account
    
    def transfer_credits(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: float,
        reason: Optional[str] = None
    ) -> Tuple[CreditAccount, CreditAccount]:
        """Transfer credits between users"""
        from_account = self.get_credit_account(from_user_id)
        to_account = self.get_credit_account(to_user_id)
        
        if not from_account:
            raise ValueError("Source credit account not found")
        if not to_account:
            raise ValueError("Destination credit account not found")
        
        # Deduct from source
        source_transaction = CreditTransaction(
            account_id=from_account.id,
            transaction_type=CreditTransactionType.TRANSFER_OUT,
            amount=-amount,
            balance_before=from_account.current_balance,
            balance_after=from_account.current_balance - amount,
            description=f"Transfer to user {to_user_id}" + (f": {reason}" if reason else ""),
            reference_id=str(to_user_id),
            reference_type="user_transfer",
            metadata={"transfer_reason": reason}
        )
        
        # Add to destination
        dest_transaction = CreditTransaction(
            account_id=to_account.id,
            transaction_type=CreditTransactionType.TRANSFER_IN,
            amount=amount,
            balance_before=to_account.current_balance,
            balance_after=to_account.current_balance + amount,
            description=f"Transfer from user {from_user_id}" + (f": {reason}" if reason else ""),
            reference_id=str(from_user_id),
            reference_type="user_transfer",
            metadata={"transfer_reason": reason}
        )
        
        # Update accounts
        from_account.current_balance -= amount
        from_account.total_spent += amount
        from_account.last_activity = datetime.utcnow()
        
        to_account.current_balance += amount
        to_account.total_earned += amount
        to_account.last_activity = datetime.utcnow()
        
        # Add transactions
        self.db.add(source_transaction)
        self.db.add(dest_transaction)
        self.db.commit()
        
        return from_account, to_account
    
    def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[CreditTransactionType] = None
    ) -> Tuple[List[CreditTransaction], int]:
        """Get transaction history for user"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return [], 0
        
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.account_id == credit_account.id
        )
        
        if transaction_type:
            query = query.filter(CreditTransaction.transaction_type == transaction_type)
        
        total = query.count()
        transactions = query.order_by(desc(CreditTransaction.created_at)).offset(offset).limit(limit).all()
        
        return transactions, total
    
    # ============================================================================
    # CREDIT POLICIES
    # ============================================================================
    
    def create_credit_policy(self, policy_data: CreditPolicyCreate) -> CreditPolicy:
        """Create credit policy"""
        # Verify account exists
        credit_account = self.db.query(CreditAccount).filter(
            CreditAccount.id == policy_data.account_id
        ).first()
        
        if not credit_account:
            raise ValueError("Credit account not found")
        
        policy = CreditPolicy(**policy_data.dict())
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        
        return policy
    
    def get_user_policies(self, user_id: int) -> List[CreditPolicy]:
        """Get all policies for user"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return []
        
        return self.db.query(CreditPolicy).filter(
            and_(
                CreditPolicy.account_id == credit_account.id,
                CreditPolicy.is_active == True
            )
        ).order_by(CreditPolicy.created_at.desc()).all()
    
    # ============================================================================
    # USAGE TRACKING
    # ============================================================================
    
    def record_usage(
        self,
        user_id: int,
        usage_data: CreditUsageRecordCreate
    ) -> CreditUsageRecord:
        """Record usage and deduct credits"""
        # Validate usage
        if usage_data.total_cost <= 0:
            raise ValueError("Usage cost must be positive")
        
        # Create usage record
        usage_record = CreditUsageRecord(**usage_data.dict())
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        # Deduct credits
        try:
            self.deduct_credits(
                user_id=user_id,
                amount=usage_data.total_cost,
                transaction_type=CreditTransactionType.USAGE_DEDUCTION,
                description=f"{usage_data.service_type}: {usage_data.operation_type}",
                reference_id=usage_data.resource_id,
                reference_type="usage_record",
                llm_model=SchemaLLMModelType(usage_data.model_used) if usage_data.model_used else None,
                tokens_used=usage_data.completion_tokens or usage_data.prompt_tokens,
                metadata={
                    "usage_record_id": usage_record.id,
                    "service_type": usage_data.service_type,
                    "operation_type": usage_data.operation_type
                }
            )
        except Exception as e:
            # Rollback usage record if credit deduction fails
            self.db.delete(usage_record)
            self.db.commit()
            raise e
        
        return usage_record
    
    # ============================================================================
    # LLM COST CALCULATION
    # ============================================================================
    
    def calculate_llm_cost(
        self,
        model_type: LLMModelType,
        prompt_tokens: int,
        completion_tokens: int,
        **kwargs
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate cost for LLM usage
        
        Args:
            model_type: LLM model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            **kwargs: Additional cost factors
        
        Returns:
            Tuple of (total_cost, cost_breakdown)
        """
        # LLM pricing per 1K tokens (USD)
        pricing = {
            LLMModelType.GPT4: {
                "prompt_cost_per_1k": 0.03,
                "completion_cost_per_1k": 0.06,
                "currency": "USD"
            },
            LLMModelType.GPT35_TURBO: {
                "prompt_cost_per_1k": 0.002,
                "completion_cost_per_1k": 0.006,
                "currency": "USD"
            },
            LLMModelType.CLAUDE_3_SONNET: {
                "prompt_cost_per_1k": 0.015,
                "completion_cost_per_1k": 0.075,
                "currency": "USD"
            },
            LLMModelType.CLAUDE_3_HAIKU: {
                "prompt_cost_per_1k": 0.00025,
                "completion_cost_per_1k": 0.00125,
                "currency": "USD"
            },
            LLMModelType.LOCAL_MODEL: {
                "prompt_cost_per_1k": 0.001,
                "completion_cost_per_1k": 0.001,
                "currency": "USD"
            }
        }
        
        if model_type not in pricing:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        model_pricing = pricing[model_type]
        
        # Calculate costs
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt_cost_per_1k"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion_cost_per_1k"]
        total_cost = prompt_cost + completion_cost
        
        cost_breakdown = {
            "model_type": model_type.value,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
            "currency": model_pricing["currency"],
            "cost_per_1k_prompt": model_pricing["prompt_cost_per_1k"],
            "cost_per_1k_completion": model_pricing["completion_cost_per_1k"]
        }
        
        return total_cost, cost_breakdown
    
    # ============================================================================
    # ANALYTICS AND FORECASTING
    # ============================================================================
    
    def get_usage_summary(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> CreditUsageSummary:
        """Get usage summary for user"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return CreditUsageSummary(
                total_cost=0, total_usage=0, total_transactions=0,
                avg_cost_per_transaction=0, cost_by_service={}, usage_trend=[]
            )
        
        # Get usage records
        usage_records = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.account_id == credit_account.id,
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date
            )
        ).all()
        
        # Calculate summary
        total_cost = sum(record.total_cost for record in usage_records)
        total_usage = sum(record.quantity_used for record in usage_records)
        total_transactions = len(usage_records)
        avg_cost_per_transaction = total_cost / total_transactions if total_transactions > 0 else 0
        
        # Cost by service
        cost_by_service = {}
        for record in usage_records:
            service = record.service_type
            cost_by_service[service] = cost_by_service.get(service, 0) + record.total_cost
        
        most_used_service = max(cost_by_service, key=cost_by_service.get) if cost_by_service else None
        
        # Usage trend (daily aggregation)
        daily_usage = {}
        for record in usage_records:
            day = record.created_at.date().isoformat()
            if day not in daily_usage:
                daily_usage[day] = {"cost": 0, "count": 0}
            daily_usage[day]["cost"] += record.total_cost
            daily_usage[day]["count"] += 1
        
        usage_trend = [
            {"date": date, "cost": data["cost"], "count": data["count"]}
            for date, data in sorted(daily_usage.items())
        ]
        
        # Top models
        model_usage = {}
        for record in usage_records:
            if record.model_used:
                model = record.model_used
                if model not in model_usage:
                    model_usage[model] = {"cost": 0, "tokens": 0, "requests": 0}
                model_usage[model]["cost"] += record.total_cost
                model_usage[model]["tokens"] += (record.prompt_tokens or 0) + (record.completion_tokens or 0)
                model_usage[model]["requests"] += 1
        
        top_models = [
            {"model": model, **data}
            for model, data in sorted(
                model_usage.items(),
                key=lambda x: x[1]["cost"],
                reverse=True
            )
        ][:5]
        
        return CreditUsageSummary(
            total_cost=total_cost,
            total_usage=total_usage,
            total_transactions=total_transactions,
            avg_cost_per_transaction=avg_cost_per_transaction,
            most_used_service=most_used_service,
            cost_by_service=cost_by_service,
            usage_trend=usage_trend,
            top_models=top_models
        )
    
    def get_balance_projection(
        self,
        user_id: int,
        days_ahead: int = 30
    ) -> CreditBalanceProjection:
        """Get credit balance projection"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return CreditBalanceProjection(
                projected_balance=0, confidence_level=0, based_on_days=0, projection_factors={}
            )
        
        # Analyze historical usage
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        usage_records = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.account_id == credit_account.id,
                CreditUsageRecord.created_at >= start_date,
                CreditUsageRecord.created_at <= end_date,
                CreditUsageRecord.service_type == "llm"
            )
        ).all()
        
        if not usage_records:
            return CreditBalanceProjection(
                projected_balance=credit_account.current_balance,
                confidence_level=0.5,
                based_on_days=0,
                projection_factors={"reason": "No historical data"}
            )
        
        # Calculate daily usage pattern
        daily_usage = {}
        for record in usage_records:
            day = record.created_at.date().isoformat()
            daily_usage[day] = daily_usage.get(day, 0) + record.total_cost
        
        # Calculate average daily usage
        avg_daily_usage = sum(daily_usage.values()) / len(daily_usage)
        
        # Project future balance
        projected_daily_usage = avg_daily_usage * (1 + 0.1)  # 10% buffer for growth
        projected_total_usage = projected_daily_usage * days_ahead
        projected_balance = credit_account.current_balance - projected_total_usage
        
        # Calculate confidence based on data quality
        confidence_level = min(0.9, len(daily_usage) / 30)  # Higher confidence with more data
        
        # Determine runout date
        runout_date = None
        if projected_balance <= 0:
            days_to_runout = credit_account.current_balance / projected_daily_usage
            runout_date = datetime.utcnow() + timedelta(days=days_to_runout)
        
        # Recommended purchase amount
        recommended_purchase = projected_total_usage * 1.2  # 20% buffer
        
        return CreditBalanceProjection(
            projected_balance=projected_balance,
            projected_runout_date=runout_date,
            recommended_purchase_amount=recommended_purchase,
            confidence_level=confidence_level,
            based_on_days=30,
            projection_factors={
                "historical_days": len(daily_usage),
                "avg_daily_usage": avg_daily_usage,
                "projected_daily_usage": projected_daily_usage,
                "growth_buffer": 0.1
            }
        )
    
    # ============================================================================
    # ALERTS AND NOTIFICATIONS
    # ============================================================================
    
    def create_alert(self, alert_data: CreditAlertCreate) -> CreditAlert:
        """Create credit alert"""
        alert = CreditAlert(**alert_data.dict())
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        return alert
    
    def get_active_alerts(self, user_id: int) -> List[CreditAlert]:
        """Get active alerts for user"""
        credit_account = self.get_credit_account(user_id)
        if not credit_account:
            return []
        
        return self.db.query(CreditAlert).filter(
            and_(
                CreditAlert.account_id == credit_account.id,
                CreditAlert.is_active == True,
                CreditAlert.is_resolved == False
            )
        ).order_by(desc(CreditAlert.created_at)).all()
    
    def resolve_alert(self, alert_id: int, user_id: int, resolution_notes: Optional[str] = None) -> bool:
        """Resolve credit alert"""
        alert = self.db.query(CreditAlert).filter(
            and_(
                CreditAlert.id == alert_id,
                CreditAlert.is_active == True
            )
        ).first()
        
        if not alert:
            return False
        
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user_id
        alert.resolution_notes = resolution_notes
        
        self.db.commit()
        return True
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _check_balance_alerts(self, credit_account: CreditAccount):
        """Check and create balance alerts"""
        # Low balance alert (when below 20% of typical usage)
        low_balance_threshold = 20.0
        
        if credit_account.current_balance <= low_balance_threshold:
            # Check if alert already exists
            existing_alert = self.db.query(CreditAlert).filter(
                and_(
                    CreditAlert.account_id == credit_account.id,
                    CreditAlert.alert_type == "low_balance",
                    CreditAlert.is_active == True,
                    CreditAlert.is_resolved == False
                )
            ).first()
            
            if not existing_alert:
                self.create_alert(CreditAlertCreate(
                    account_id=credit_account.id,
                    alert_type="low_balance",
                    severity="warning",
                    threshold_value=low_balance_threshold,
                    current_value=credit_account.current_balance
                ))
    
    def _log_transaction_telemetry(self, account: CreditTransaction, transaction: CreditTransaction):
        """Log transaction for telemetry"""
        try:
            telemetry_event(
                event_name="credit.transaction",
                event_type=TelemetryEvent.SYSTEM_EVENT,
                level=TelemetryLevel.INFO,
                user_id=account.user_id,
                metadata={
                    "transaction_id": transaction.id,
                    "transaction_type": transaction.transaction_type.value,
                    "amount": transaction.amount,
                    "balance_after": transaction.balance_after,
                    "description": transaction.description
                }
            )
        except Exception as e:
            # Silently handle telemetry errors
            pass