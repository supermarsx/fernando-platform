"""
Billing and Subscription Models

This module defines the database models for the billing and subscription system,
including subscriptions, invoices, payments, usage tracking, and tax management.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.session import Base


class BillingCycle(str, enum.Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status options"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"
    EXPIRED = "expired"


class InvoiceStatus(str, enum.Enum):
    """Invoice status options"""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    OVERDUE = "overdue"


class PaymentStatus(str, enum.Enum):
    """Payment status options"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, enum.Enum):
    """Payment method types"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    INVOICE = "invoice"
    SEPA_DEBIT = "sepa_debit"
    ACH_DEBIT = "ach_debit"
    WIRE_TRANSFER = "wire_transfer"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    CRYPTOCURRENCY = "cryptocurrency"
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    USDT = "usdt"
    KLARNA = "klarna"
    AFTERPAY = "afterpay"


class SubscriptionPlan(Base):
    """
    Subscription plans that extend license tiers with billing information
    """
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    license_tier_id = Column(Integer, ForeignKey('license_tiers.tier_id'), nullable=False)
    
    # Pricing
    monthly_price = Column(Float, nullable=False)
    quarterly_price = Column(Float)  # Optional discount for quarterly
    annual_price = Column(Float)  # Optional discount for annual
    currency = Column(String(3), default="EUR")
    
    # Usage limits (inherited from license tier but can be overridden)
    max_documents_per_month = Column(Integer)
    max_users = Column(Integer)
    max_api_calls_per_month = Column(Integer)
    
    # Overage pricing
    overage_document_price = Column(Float, default=0.10)  # Per document
    overage_user_price = Column(Float, default=5.00)  # Per user per month
    overage_api_call_price = Column(Float, default=0.01)  # Per 100 calls
    
    # Features
    features = Column(JSON)  # JSON array of feature flags
    is_active = Column(Boolean, default=True)
    trial_days = Column(Integer, default=14)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    license_tier = relationship("LicenseTierModel", backref="subscription_plans")
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    """
    Customer subscriptions with billing cycle and status tracking
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(String(64), unique=True, index=True)  # Public ID
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    license_id = Column(Integer, ForeignKey('licenses.license_id'), nullable=True)
    
    # Status and lifecycle
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    billing_cycle = Column(Enum(BillingCycle), default=BillingCycle.MONTHLY)
    
    # Dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)
    
    # Billing
    auto_renew = Column(Boolean, default=True)
    next_billing_date = Column(DateTime)
    last_billing_date = Column(DateTime)
    
    # Usage tracking
    documents_used_this_period = Column(Integer, default=0)
    api_calls_used_this_period = Column(Integer, default=0)
    additional_users_this_period = Column(Integer, default=0)
    
    # Pricing (snapshot at subscription time)
    base_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    
    # Payment
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id'))
    
    # Metadata
    meta_data = Column(JSON)  # Additional custom data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    usage_records = relationship("UsageRecord", back_populates="subscription")
    payment_method = relationship("PaymentMethodModel", back_populates="subscriptions")


class Invoice(Base):
    """
    Invoices for subscriptions and one-time charges
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(64), unique=True, index=True)
    
    # References
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    # Status
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    
    # Amounts
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0)
    amount_due = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    
    # Line items
    line_items = Column(JSON)  # Array of {description, quantity, unit_price, amount}
    
    # Dates
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime)
    voided_at = Column(DateTime)
    
    # Billing period
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Tax information
    tax_rate = Column(Float, default=0)
    tax_jurisdiction = Column(String(100))
    tax_id_number = Column(String(50))  # Customer tax ID
    
    # PDF
    pdf_url = Column(String(500))
    
    # Metadata
    notes = Column(Text)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")


class Payment(Base):
    """
    Payment records for invoices
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(64), unique=True, index=True)
    
    # References
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id'))
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    
    # Status
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Payment details
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    transaction_id = Column(String(200))  # External payment provider ID
    
    # Processing
    processed_at = Column(DateTime)
    failed_at = Column(DateTime)
    failure_reason = Column(Text)
    
    # Refund information
    refunded_amount = Column(Float, default=0)
    refunded_at = Column(DateTime)
    refund_reason = Column(Text)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")


class PaymentMethodModel(Base):
    """
    Stored payment methods for customers
    """
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    # Payment method details
    type = Column(Enum(PaymentMethod), nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Card details (masked)
    card_last4 = Column(String(4))
    card_brand = Column(String(50))
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)
    
    # Bank details (masked)
    bank_name = Column(String(100))
    bank_account_last4 = Column(String(4))
    
    # External provider
    provider = Column(String(50))  # stripe, paypal, etc.
    provider_payment_method_id = Column(String(200))
    
    # Status
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="payment_method")


class UsageRecord(Base):
    """
    Track resource usage for billing purposes
    """
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    # Usage details
    resource_type = Column(String(50), nullable=False)  # document, api_call, user, storage
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float)
    
    # Context
    description = Column(Text)
    reference_id = Column(String(100))  # Reference to document, job, etc.
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    
    # Billing
    billed = Column(Boolean, default=False)
    invoice_id = Column(Integer, ForeignKey('invoices.id'))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")


class BillingEvent(Base):
    """
    Audit trail for billing events
    """
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    invoice_id = Column(Integer, ForeignKey('invoices.id'))
    payment_id = Column(Integer, ForeignKey('payments.id'))
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # subscription_created, invoice_paid, etc.
    description = Column(Text)
    
    # Changes
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class TaxRate(Base):
    """
    Tax rates by jurisdiction for compliance
    """
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    
    # Jurisdiction
    country = Column(String(2), nullable=False)  # ISO country code
    region = Column(String(100))  # State, province, etc.
    jurisdiction_name = Column(String(200))
    
    # Tax details
    tax_type = Column(String(50), nullable=False)  # VAT, sales_tax, GST, etc.
    rate = Column(Float, nullable=False)  # Percentage
    
    # Applicability
    applies_to_digital_services = Column(Boolean, default=True)
    applies_to_physical_goods = Column(Boolean, default=True)
    
    # Validity
    effective_from = Column(DateTime, nullable=False)
    effective_until = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
