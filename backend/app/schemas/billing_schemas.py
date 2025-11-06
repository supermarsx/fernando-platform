"""
Pydantic Schemas for Billing and Subscription System

Validation and serialization schemas for billing API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class BillingCycleEnum(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"
    EXPIRED = "expired"


class InvoiceStatusEnum(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    OVERDUE = "overdue"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethodEnum(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    INVOICE = "invoice"


# Subscription Plan Schemas
class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    license_tier_id: int
    monthly_price: float = Field(..., gt=0)
    quarterly_price: Optional[float] = Field(None, gt=0)
    annual_price: Optional[float] = Field(None, gt=0)
    currency: str = Field(default="EUR", max_length=3)
    max_documents_per_month: Optional[int] = None
    max_users: Optional[int] = None
    max_api_calls_per_month: Optional[int] = None
    overage_document_price: float = Field(default=0.10, ge=0)
    overage_user_price: float = Field(default=5.00, ge=0)
    overage_api_call_price: float = Field(default=0.01, ge=0)
    features: Optional[Dict[str, Any]] = None
    trial_days: int = Field(default=14, ge=0)
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    monthly_price: Optional[float] = Field(None, gt=0)
    quarterly_price: Optional[float] = Field(None, gt=0)
    annual_price: Optional[float] = Field(None, gt=0)
    max_documents_per_month: Optional[int] = None
    max_users: Optional[int] = None
    max_api_calls_per_month: Optional[int] = None
    overage_document_price: Optional[float] = Field(None, ge=0)
    overage_user_price: Optional[float] = Field(None, ge=0)
    overage_api_call_price: Optional[float] = Field(None, ge=0)
    features: Optional[Dict[str, Any]] = None
    trial_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Subscription Schemas
class SubscriptionBase(BaseModel):
    plan_id: int
    billing_cycle: BillingCycleEnum = BillingCycleEnum.MONTHLY
    auto_renew: bool = True


class SubscriptionCreate(SubscriptionBase):
    payment_method_id: Optional[int] = None
    trial_enabled: bool = False


class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    billing_cycle: Optional[BillingCycleEnum] = None
    auto_renew: Optional[bool] = None
    payment_method_id: Optional[int] = None


class SubscriptionResponse(BaseModel):
    id: int
    subscription_id: str
    user_id: int
    plan_id: int
    status: SubscriptionStatusEnum
    billing_cycle: BillingCycleEnum
    start_date: datetime
    end_date: Optional[datetime]
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]
    auto_renew: bool
    next_billing_date: Optional[datetime]
    last_billing_date: Optional[datetime]
    documents_used_this_period: int
    api_calls_used_this_period: int
    additional_users_this_period: int
    base_amount: float
    currency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceLineItem(BaseModel):
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    amount: float = Field(..., ge=0)


class InvoiceCreate(BaseModel):
    subscription_id: Optional[int] = None
    line_items: List[InvoiceLineItem]
    due_date: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    tax_rate: float = Field(default=0, ge=0, le=1)
    tax_jurisdiction: Optional[str] = None
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    subscription_id: Optional[int]
    user_id: int
    status: InvoiceStatusEnum
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    amount_paid: float
    amount_due: float
    currency: str
    line_items: List[Dict[str, Any]]
    issue_date: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    tax_rate: float
    tax_jurisdiction: Optional[str]
    pdf_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethodEnum
    payment_method_id: Optional[int] = None
    transaction_id: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    payment_id: str
    invoice_id: int
    user_id: int
    amount: float
    currency: str
    status: PaymentStatusEnum
    payment_method: PaymentMethodEnum
    transaction_id: Optional[str]
    processed_at: Optional[datetime]
    failed_at: Optional[datetime]
    failure_reason: Optional[str]
    refunded_amount: float
    refunded_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Payment Method Schemas
class PaymentMethodCreate(BaseModel):
    type: PaymentMethodEnum
    is_default: bool = False
    card_last4: Optional[str] = Field(None, max_length=4)
    card_brand: Optional[str] = Field(None, max_length=50)
    card_exp_month: Optional[int] = Field(None, ge=1, le=12)
    card_exp_year: Optional[int] = Field(None, ge=2025)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_last4: Optional[str] = Field(None, max_length=4)
    provider: Optional[str] = Field(None, max_length=50)
    provider_payment_method_id: Optional[str] = Field(None, max_length=200)


class PaymentMethodResponse(BaseModel):
    id: int
    user_id: int
    type: PaymentMethodEnum
    is_default: bool
    card_last4: Optional[str]
    card_brand: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    bank_name: Optional[str]
    bank_account_last4: Optional[str]
    provider: Optional[str]
    is_active: bool
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Usage Record Schemas
class UsageRecordCreate(BaseModel):
    subscription_id: int
    resource_type: str = Field(..., max_length=50)
    quantity: int = Field(default=1, gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = None


class UsageRecordResponse(BaseModel):
    id: int
    subscription_id: int
    user_id: int
    resource_type: str
    quantity: int
    unit_price: Optional[float]
    description: Optional[str]
    reference_id: Optional[str]
    timestamp: datetime
    billing_period_start: datetime
    billing_period_end: datetime
    billed: bool
    invoice_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics Schemas
class BillingAnalytics(BaseModel):
    total_revenue: float
    monthly_recurring_revenue: float
    annual_recurring_revenue: float
    active_subscriptions: int
    trialing_subscriptions: int
    canceled_subscriptions: int
    churn_rate: float
    average_revenue_per_user: float
    total_invoices: int
    paid_invoices: int
    outstanding_amount: float
    overdue_invoices: int


class UsageAnalytics(BaseModel):
    total_documents_processed: int
    total_api_calls: int
    total_active_users: int
    documents_by_plan: Dict[str, int]
    api_calls_by_plan: Dict[str, int]
    overage_charges: float


class RevenueByMonth(BaseModel):
    month: str
    revenue: float
    subscriptions: int
    new_subscriptions: int
    canceled_subscriptions: int


class BillingDashboard(BaseModel):
    billing_analytics: BillingAnalytics
    usage_analytics: UsageAnalytics
    revenue_by_month: List[RevenueByMonth]


# Action Schemas
class SubscriptionCancelRequest(BaseModel):
    reason: Optional[str] = None
    cancel_immediately: bool = False


class SubscriptionPauseRequest(BaseModel):
    reason: Optional[str] = None
    pause_until: Optional[datetime] = None


class SubscriptionUpgradeRequest(BaseModel):
    new_plan_id: int
    prorate: bool = True


class InvoicePayRequest(BaseModel):
    payment_method_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)


class RefundRequest(BaseModel):
    amount: float = Field(..., gt=0)
    reason: str
