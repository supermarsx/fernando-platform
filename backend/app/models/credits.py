"""
Credit Management System Models

This module defines comprehensive models for the credit system, including
credit balances, transactions, usage tracking, pricing, and policies.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

from app.db.session import Base


class CreditTransactionType(str, enum.Enum):
    """Types of credit transactions"""
    PURCHASE = "purchase"
    USAGE = "usage"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    EXPIRATION = "expiration"
    ROLLOVER = "rollover"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    BONUS = "bonus"
    REVERSAL = "reversal"


class CreditStatus(str, enum.Enum):
    """Status of credit transactions"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class CreditPackageStatus(str, enum.Enum):
    """Status of credit packages"""
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    ARCHIVED = "archived"
    SEASONAL = "seasonal"


class LLMProvider(str, enum.Enum):
    """LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"


class CreditBalance(Base):
    """
    Credit balance tracking per user/organization
    """
    __tablename__ = "credit_balances"
    __table_args__ = (
        Index('idx_credit_balances_user_org', 'user_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)  # For multi-tenant
    
    # Balance details
    total_credits = Column(Float, default=0, nullable=False)  # Total available credits
    available_credits = Column(Float, default=0, nullable=False)  # Credits available for use
    reserved_credits = Column(Float, default=0, nullable=False)  # Credits reserved for pending requests
    pending_credits = Column(Float, default=0, nullable=False)  # Credits being processed
    
    # Usage tracking
    credits_used_today = Column(Float, default=0, nullable=False)
    credits_used_this_month = Column(Float, default=0, nullable=False)
    credits_used_this_year = Column(Float, default=0, nullable=False)
    
    # Lifetime usage
    total_credits_earned = Column(Float, default=0, nullable=False)  # Lifetime credits earned
    total_credits_used = Column(Float, default=0, nullable=False)  # Lifetime credits used
    
    # Expiration tracking
    next_expiration_date = Column(DateTime)  # Date of earliest expiring credits
    expired_credits_this_month = Column(Float, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(Text)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("CreditTransaction", back_populates="balance", cascade="all, delete-orphan")
    usage_records = relationship("LLMUsageRecord", back_populates="balance")


class CreditTransaction(Base):
    """
    Individual credit transactions for audit trail
    """
    __tablename__ = "credit_transactions"
    __table_args__ = (
        Index('idx_credit_transactions_user_date', 'user_id', 'created_at'),
        Index('idx_credit_transactions_type_status', 'transaction_type', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    balance_id = Column(Integer, ForeignKey('credit_balances.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Transaction details
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    transaction_type = Column(Enum(CreditTransactionType), nullable=False)
    status = Column(Enum(CreditStatus), default=CreditStatus.PENDING)
    
    # Credit amounts
    credit_amount = Column(Float, nullable=False)  # Positive for credits gained, negative for usage
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Context and reference
    description = Column(Text, nullable=False)
    reference_type = Column(String(50))  # purchase, usage, transfer, etc.
    reference_id = Column(String(100))  # ID of related object (purchase_id, usage_record_id, etc.)
    
    # Source and destination
    source_user_id = Column(Integer, ForeignKey('users.user_id'))  # For transfers
    destination_user_id = Column(Integer, ForeignKey('users.user_id'))  # For transfers
    
    # Expiration (for purchased credits)
    expires_at = Column(DateTime)
    is_expired = Column(Boolean, default=False)
    expired_at = Column(DateTime)
    
    # Pricing (for purchases)
    amount_paid = Column(Float)  # Money paid for credits
    currency = Column(String(3), default="USD")
    unit_price = Column(Float)  # Price per credit
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    balance = relationship("CreditBalance", back_populates="transactions")


class LLMUsageRecord(Base):
    """
    LLM usage tracking for credit consumption
    """
    __tablename__ = "llm_usage_records"
    __table_args__ = (
        Index('idx_llm_usage_user_date', 'user_id', 'timestamp'),
        Index('idx_llm_usage_provider_model', 'provider', 'model_name'),
        Index('idx_llm_usage_cost', 'total_cost_credits', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    balance_id = Column(Integer, ForeignKey('credit_balances.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Usage details
    provider = Column(Enum(LLMProvider), nullable=False)
    model_name = Column(String(100), nullable=False)
    operation_type = Column(String(50))  # text_generation, chat, completion, etc.
    
    # Token usage
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    
    # Credit calculation
    cost_per_1k_prompt_tokens = Column(Float, nullable=False)
    cost_per_1k_completion_tokens = Column(Float, nullable=False)
    prompt_cost_credits = Column(Float, default=0, nullable=False)
    completion_cost_credits = Column(Float, default=0, nullable=False)
    total_cost_credits = Column(Float, nullable=False)
    
    # Usage context
    request_id = Column(String(100), index=True)  # Unique request identifier
    session_id = Column(String(100))  # Session for multi-turn conversations
    document_id = Column(String(100))  # Related document if applicable
    job_id = Column(String(100))  # Related processing job
    
    # Performance metrics
    response_time_ms = Column(Integer)
    tokens_per_second = Column(Float)
    
    # Error handling
    error_occurred = Column(Boolean, default=False)
    error_code = Column(String(50))
    error_message = Column(Text)
    partially_processed = Column(Boolean, default=False)
    
    # Credit deduction
    credits_deducted = Column(Float, default=0, nullable=False)
    transaction_id = Column(Integer, ForeignKey('credit_transactions.id'))
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    request_start_time = Column(DateTime, nullable=False)
    request_end_time = Column(DateTime)
    
    # Quality metrics (for feedback)
    user_rating = Column(Integer)  # 1-5 rating
    quality_score = Column(Float)  # AI-assessed quality
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    balance = relationship("CreditBalance", back_populates="usage_records")


class CreditPackage(Base):
    """
    Available credit packages for purchase
    """
    __tablename__ = "credit_packages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Package details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    credits_amount = Column(Float, nullable=False)
    
    # Pricing
    price_usd = Column(Float, nullable=False)
    price_eur = Column(Float)
    price_gbp = Column(Float)
    currency = Column(String(3), default="USD")
    
    # Discounts
    discount_percentage = Column(Float, default=0)  # Percentage discount
    is_bulk_discount = Column(Boolean, default=False)  # Whether this is a bulk discount package
    
    # Validity
    validity_days = Column(Integer, default=365)  # How long credits are valid
    auto_renew = Column(Boolean, default=False)  # Whether to auto-renew
    
    # Features
    includes_priority_support = Column(Boolean, default=False)
    includes_advanced_analytics = Column(Boolean, default=False)
    includes_api_access = Column(Boolean, default=True)
    
    # Targeting
    target_user_tier = Column(String(50))  # starter, professional, enterprise
    organization_only = Column(Boolean, default=False)  # Available only to organizations
    region_restrictions = Column(JSON)  # List of restricted regions
    
    # Status and availability
    status = Column(Enum(CreditPackageStatus), default=CreditPackageStatus.ACTIVE)
    is_featured = Column(Boolean, default=False)  # Show prominently
    is_limited_time = Column(Boolean, default=False)  # Limited time offer
    limited_time_end = Column(DateTime)
    
    # Usage limits
    max_daily_usage = Column(Float)  # Optional daily usage cap
    max_monthly_usage = Column(Float)  # Optional monthly usage cap
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_transactions = relationship("CreditPurchaseTransaction", back_populates="package")


class CreditPurchaseTransaction(Base):
    """
    Credit purchase transactions
    """
    __tablename__ = "credit_purchase_transactions"
    __table_args__ = (
        Index('idx_purchase_user_date', 'user_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    package_id = Column(Integer, ForeignKey('credit_packages.id'), nullable=False)
    balance_id = Column(Integer, ForeignKey('credit_balances.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Purchase details
    purchase_id = Column(String(100), unique=True, nullable=False, index=True)
    quantity = Column(Integer, default=1)  # Number of packages purchased
    
    # Credits
    total_credits = Column(Float, nullable=False)
    bonus_credits = Column(Float, default=0)  # Bonus credits included
    
    # Pricing
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Payment
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id'))
    payment_transaction_id = Column(String(200))  # External payment processor ID
    payment_status = Column(String(50), default="pending")
    
    # Status
    status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    
    # Timing
    expires_at = Column(DateTime)  # When the purchased credits expire
    activated_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    package = relationship("CreditPackage", back_populates="purchase_transactions")


class LLMModelPricing(Base):
    """
    Pricing configuration for different LLM models
    """
    __tablename__ = "llm_model_pricing"

    id = Column(Integer, primary_key=True, index=True)
    
    # Model details
    provider = Column(Enum(LLMProvider), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), default="latest")
    
    # Token pricing (credits per 1K tokens)
    prompt_price_credits = Column(Float, nullable=False)
    completion_price_credits = Column(Float, nullable=False)
    
    # Character pricing (alternative pricing model)
    character_price_credits = Column(Float)
    
    # Fixed cost per request
    request_cost_credits = Column(Float, default=0)
    
    # Minimum charges
    minimum_prompt_tokens = Column(Integer, default=1)
    minimum_completion_tokens = Column(Integer, default=1)
    
    # Maximum limits
    max_tokens_per_request = Column(Integer)
    max_requests_per_day = Column(Integer)
    max_requests_per_month = Column(Integer)
    
    # Quality tiers
    quality_tier = Column(String(50), default="standard")  # standard, premium, enterprise
    
    # Context window
    context_window_tokens = Column(Integer)
    
    # Availability
    is_active = Column(Boolean, default=True)
    is_deprecated = Column(Boolean, default=False)
    deprecation_date = Column(DateTime)
    
    # Regional pricing
    region = Column(String(50), default="global")  # Different regions may have different prices
    region_multiplier = Column(Float, default=1.0)
    
    # Discounts and promotions
    bulk_discount_threshold = Column(Integer)  # Apply discount after this many tokens
    bulk_discount_percentage = Column(Float, default=0)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CreditPolicy(Base):
    """
    Credit policies for expiration, rollover, and transfers
    """
    __tablename__ = "credit_policies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Policy details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    policy_type = Column(String(50), nullable=False)  # expiration, rollover, transfer, etc.
    
    # Policy configuration
    config = Column(JSON, nullable=False)  # Policy-specific configuration
    
    # Targeting
    applies_to_user_tier = Column(String(50))  # starter, professional, enterprise, all
    applies_to_organization_type = Column(String(50))  # individual, business, enterprise, all
    organization_only = Column(Boolean, default=False)
    
    # Validity
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_until = Column(DateTime)
    
    # Priority (lower number = higher priority)
    priority = Column(Integer, default=100)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CreditTransfer(Base):
    """
    Credit transfer records between users/organizations
    """
    __tablename__ = "credit_transfers"
    __table_args__ = (
        Index('idx_credit_transfers_users', 'from_user_id', 'to_user_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    from_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    from_organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    to_organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Transfer details
    transfer_id = Column(String(100), unique=True, nullable=False, index=True)
    credit_amount = Column(Float, nullable=False)
    
    # Context
    reason = Column(String(200))  # Reason for transfer
    reference_id = Column(String(100))  # Related reference (invoice, project, etc.)
    
    # Permissions and approvals
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey('users.user_id'))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    # Status
    status = Column(String(50), default="pending")  # pending, approved, rejected, completed, canceled
    
    # Transaction records
    from_transaction_id = Column(Integer, ForeignKey('credit_transactions.id'))
    to_transaction_id = Column(Integer, ForeignKey('credit_transactions.id'))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class CreditAlert(Base):
    """
    Credit balance alerts and notifications
    """
    __tablename__ = "credit_alerts"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    balance_id = Column(Integer, ForeignKey('credit_balances.id'), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # low_balance, critical_balance, expiration_warning
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Current state
    current_balance = Column(Float, nullable=False)
    threshold_balance = Column(Float, nullable=False)
    threshold_percentage = Column(Float)
    
    # Context
    message = Column(Text, nullable=False)
    suggested_action = Column(Text)
    
    # Status
    status = Column(String(20), default="active")  # active, acknowledged, resolved
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(Integer, ForeignKey('users.user_id'))
    resolved_at = Column(DateTime)
    
    # Notification tracking
    email_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)
    push_sent = Column(Boolean, default=False)
    webhook_sent = Column(Boolean, default=False)
    
    # Escalation
    escalation_level = Column(Integer, default=0)  # 0=initial, 1=escalated, etc.
    escalated_at = Column(DateTime)
    escalated_to = Column(Integer, ForeignKey('users.user_id'))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreditAnalytics(Base):
    """
    Credit usage analytics and forecasting
    """
    __tablename__ = "credit_analytics"
    __table_args__ = (
        Index('idx_credit_analytics_user_date', 'user_id', 'analysis_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Analysis details
    analysis_type = Column(String(50), nullable=False)  # daily, weekly, monthly, forecast
    analysis_date = Column(DateTime, nullable=False, index=True)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Usage metrics
    total_credits_used = Column(Float, default=0)
    total_credits_purchased = Column(Float, default=0)
    net_credit_flow = Column(Float, default=0)
    
    # Usage patterns
    avg_daily_usage = Column(Float, default=0)
    peak_daily_usage = Column(Float, default=0)
    usage_trend = Column(String(20))  # increasing, decreasing, stable
    
    # Model breakdown
    provider_usage = Column(JSON)  # {provider: {tokens: amount, credits: amount}}
    model_usage = Column(JSON)  # {model: {tokens: amount, credits: amount}}
    
    # Cost analysis
    total_cost_usd = Column(Float, default=0)
    cost_per_token = Column(Float, default=0)
    efficiency_score = Column(Float, default=0)  # Credits per dollar
    roi_score = Column(Float, default=0)  # Return on investment score
    
    # Forecasts (for future periods)
    predicted_usage = Column(Float)  # Predicted usage for next period
    predicted_cost = Column(Float)  # Predicted cost
    confidence_level = Column(Float)  # 0-1 confidence in prediction
    
    # Recommendations
    usage_optimization_suggestions = Column(JSON)  # Array of suggestions
    cost_optimization_suggestions = Column(JSON)  # Array of suggestions
    recommended_top_up = Column(Float)  # Recommended credit top-up amount
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CreditExpirationSchedule(Base):
    """
    Schedule for credit expirations to enable proactive notifications
    """
    __tablename__ = "credit_expiration_schedule"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    balance_id = Column(Integer, ForeignKey('credit_balances.id'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('credit_transactions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    
    # Expiration details
    credit_amount = Column(Float, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Notification tracking
    notification_7_days_sent = Column(Boolean, default=False)
    notification_3_days_sent = Column(Boolean, default=False)
    notification_1_day_sent = Column(Boolean, default=False)
    notification_expired_sent = Column(Boolean, default=False)
    
    # Status
    is_expired = Column(Boolean, default=False)
    expired_at = Column(DateTime)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)