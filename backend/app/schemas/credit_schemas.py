"""
Credit System Schemas

API schemas for credit system operations including:
- Credit account management
- Transaction handling
- Usage tracking
- Analytics and forecasting
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# Enums for validation
class CreditTransactionType(str, Enum):
    PURCHASE = "purchase"
    USAGE_DEDUCTION = "usage_deduction"
    REFUND = "refund"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ALLOCATION = "allocation"
    ADJUSTMENT = "adjustment"
    EXPIRY = "expiry"


class CreditStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    FROZEN = "frozen"
    PENDING = "pending"


class CreditPolicyType(str, Enum):
    LLM_TOKENS = "llm_tokens"
    API_CALLS = "api_calls"
    DOCUMENT_PROCESSING = "document_processing"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    CUSTOM = "custom"


class LLMModelType(str, Enum):
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    LOCAL_MODEL = "local_model"


# Base schemas
class CreditBase(BaseModel):
    """Base credit schema"""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Credit Account schemas
class CreditAccountCreate(CreditBase):
    """Schema for creating credit account"""
    user_id: int
    organization_id: Optional[int] = None
    auto_renew: bool = True
    expiration_policy: Optional[str] = None


class CreditAccountUpdate(CreditBase):
    """Schema for updating credit account"""
    status: Optional[CreditStatus] = None
    auto_renew: Optional[bool] = None
    expiration_policy: Optional[str] = None


class CreditAccount(CreditBase):
    """Credit account response schema"""
    id: int
    user_id: int
    organization_id: Optional[int]
    current_balance: float
    reserved_balance: float
    total_earned: float
    total_spent: float
    status: CreditStatus
    auto_renew: bool
    expiration_policy: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True


class CreditAccountWithDetails(CreditAccount):
    """Credit account with additional details"""
    policies: List["CreditPolicy"] = Field(default_factory=list)
    recent_transactions: List["CreditTransaction"] = Field(default_factory=list)
    forecast: Optional["CreditForecast"] = None


# Credit Transaction schemas
class CreditTransactionCreate(CreditBase):
    """Schema for creating credit transaction"""
    account_id: int
    transaction_type: CreditTransactionType
    amount: float
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    description: Optional[str] = None
    llm_model: Optional[LLMModelType] = None
    tokens_used: Optional[int] = None
    cost_per_token: Optional[float] = None


class CreditTransaction(CreditBase):
    """Credit transaction response schema"""
    id: int
    account_id: int
    transaction_type: CreditTransactionType
    amount: float
    balance_before: float
    balance_after: float
    reference_id: Optional[str]
    reference_type: Optional[str]
    description: Optional[str]
    llm_model: Optional[LLMModelType]
    tokens_used: Optional[int]
    cost_per_token: Optional[float]
    created_at: datetime
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Credit Policy schemas
class CreditPolicyCreate(CreditBase):
    """Schema for creating credit policy"""
    account_id: int
    policy_type: CreditPolicyType
    name: str
    description: Optional[str] = None
    monthly_allocation: Optional[float] = None
    auto_replenish: bool = False
    minimum_balance: float = 0.0
    maximum_allocation: Optional[float] = None
    daily_limit: Optional[float] = None
    hourly_limit: Optional[float] = None
    rate_limit: Optional[float] = None
    cost_per_unit: Optional[float] = None
    bulk_discount_rate: float = 0.0
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None


class CreditPolicyUpdate(CreditBase):
    """Schema for updating credit policy"""
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_allocation: Optional[float] = None
    auto_replenish: Optional[bool] = None
    minimum_balance: Optional[float] = None
    maximum_allocation: Optional[float] = None
    daily_limit: Optional[float] = None
    hourly_limit: Optional[float] = None
    rate_limit: Optional[float] = None
    cost_per_unit: Optional[float] = None
    bulk_discount_rate: Optional[float] = None
    is_active: Optional[bool] = None
    valid_to: Optional[datetime] = None


class CreditPolicy(CreditBase):
    """Credit policy response schema"""
    id: int
    account_id: int
    policy_type: CreditPolicyType
    name: str
    description: Optional[str]
    monthly_allocation: Optional[float]
    auto_replenish: bool
    minimum_balance: float
    maximum_allocation: Optional[float]
    daily_limit: Optional[float]
    hourly_limit: Optional[float]
    rate_limit: Optional[float]
    cost_per_unit: Optional[float]
    bulk_discount_rate: float
    is_active: bool
    valid_from: datetime
    valid_to: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Credit Usage Record schemas
class CreditUsageRecordCreate(CreditBase):
    """Schema for creating credit usage record"""
    account_id: int
    service_type: str
    operation_type: str
    resource_id: Optional[str] = None
    quantity_used: float
    unit_type: str
    cost_per_unit: float
    total_cost: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model_used: Optional[str] = None
    response_time_ms: Optional[int] = None
    success: bool = True
    endpoint: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class CreditUsageRecord(CreditBase):
    """Credit usage record response schema"""
    id: int
    account_id: int
    transaction_id: Optional[int]
    service_type: str
    operation_type: str
    resource_id: Optional[str]
    quantity_used: float
    unit_type: str
    cost_per_unit: float
    total_cost: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    model_used: Optional[str]
    response_time_ms: Optional[int]
    success: bool
    endpoint: Optional[str]
    user_agent: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Credit Alert schemas
class CreditAlertCreate(CreditBase):
    """Schema for creating credit alert"""
    account_id: int
    alert_type: str
    severity: str = "info"
    threshold_value: float
    current_value: float


class CreditAlertUpdate(CreditBase):
    """Schema for updating credit alert"""
    is_resolved: bool = False
    resolution_notes: Optional[str] = None


class CreditAlert(CreditBase):
    """Credit alert response schema"""
    id: int
    account_id: int
    alert_type: str
    severity: str
    threshold_value: float
    current_value: float
    is_active: bool
    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    resolution_notes: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Credit Forecast schemas
class CreditForecastCreate(CreditBase):
    """Schema for creating credit forecast"""
    account_id: int
    forecast_type: str
    time_period: str
    predicted_usage: float
    predicted_cost: float
    confidence_level: float = 0.8
    based_on_days: int = 30


class CreditForecast(CreditBase):
    """Credit forecast response schema"""
    id: int
    account_id: int
    forecast_type: str
    time_period: str
    predicted_usage: float
    predicted_cost: float
    confidence_level: float
    based_on_days: int
    last_calculated: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# LLM Usage Metrics schemas
class LLMUsageMetricsCreate(CreditBase):
    """Schema for creating LLM usage metrics"""
    aggregation_period: str
    period_start: datetime
    period_end: datetime
    model_type: LLMModelType
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    unique_users: int = 0


class LLMUsageMetrics(CreditBase):
    """LLM usage metrics response schema"""
    id: int
    aggregation_period: str
    period_start: datetime
    period_end: datetime
    model_type: LLMModelType
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    avg_response_time_ms: Optional[float]
    success_rate: Optional[float]
    unique_users: int
    created_at: datetime
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Bulk Operations schemas
class BulkCreditOperation(BaseModel):
    """Schema for bulk credit operations"""
    account_ids: List[int]
    operation_type: str
    amount: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CreditTransferRequest(BaseModel):
    """Schema for credit transfers"""
    from_account_id: int
    to_account_id: int
    amount: float
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Analytics schemas
class CreditAnalyticsRequest(BaseModel):
    """Schema for credit analytics requests"""
    account_id: Optional[int] = None
    organization_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    aggregation_level: str = "daily"  # hourly, daily, weekly, monthly


class CreditUsageSummary(BaseModel):
    """Summary of credit usage"""
    total_cost: float
    total_usage: float
    total_transactions: int
    avg_cost_per_transaction: float
    most_used_service: Optional[str]
    cost_by_service: Dict[str, float]
    usage_trend: List[Dict[str, Any]]
    top_models: List[Dict[str, Any]]


class CreditBalanceProjection(BaseModel):
    """Credit balance projection"""
    projected_balance: float
    projected_runout_date: Optional[datetime]
    recommended_purchase_amount: float
    confidence_level: float
    based_on_days: int
    projection_factors: Dict[str, Any]


# Validation schemas
class CreditValidationRequest(BaseModel):
    """Schema for credit validation requests"""
    account_id: int
    estimated_cost: float
    operation_type: str
    service_type: str = "llm"
    model_type: Optional[str] = None
    estimated_tokens: Optional[int] = None


class CreditValidationResponse(BaseModel):
    """Schema for credit validation response"""
    sufficient_credits: bool
    available_balance: float
    reserved_balance: float
    estimated_cost: float
    balance_after_operation: float
    requires_approval: bool
    approval_required_amount: Optional[float] = None
    alternative_options: Optional[List[str]] = None


# Add forward references
CreditAccountWithDetails.model_rebuild()
CreditAccountWithDetails.update_forward_refs()