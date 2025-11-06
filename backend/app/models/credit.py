"""
Credit System Models

Comprehensive credit management for the Fernando platform including:
- Credit balances and transactions
- Credit policies and allocation
- Usage tracking and cost calculation
- Credit forecasting and analytics
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import json

Base = declarative_base()


class CreditTransactionType(PyEnum):
    """Types of credit transactions"""
    PURCHASE = "purchase"
    USAGE_DEDUCTION = "usage_deduction"
    REFUND = "refund"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ALLOCATION = "allocation"
    ADJUSTMENT = "adjustment"
    EXPIRY = "expiry"


class CreditStatus(PyEnum):
    """Credit status types"""
    ACTIVE = "active"
    EXPIRED = "expired"
    FROZEN = "frozen"
    PENDING = "pending"


class CreditPolicyType(PyEnum):
    """Types of credit policies"""
    LLM_TOKENS = "llm_tokens"
    API_CALLS = "api_calls"
    DOCUMENT_PROCESSING = "document_processing"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    CUSTOM = "custom"


class LLMModelType(PyEnum):
    """LLM model types for cost calculation"""
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    LOCAL_MODEL = "local_model"


class CreditAccount(Base):
    """Credit account for users and organizations"""
    __tablename__ = "credit_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    # Balance information
    current_balance = Column(Float, default=0.0, nullable=False)
    reserved_balance = Column(Float, default=0.0, nullable=False)
    total_earned = Column(Float, default=0.0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    
    # Credit status
    status = Column(Enum(CreditStatus), default=CreditStatus.ACTIVE, nullable=False)
    
    # Expiration settings
    auto_renew = Column(Boolean, default=True, nullable=False)
    expiration_policy = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    transactions = relationship("CreditTransaction", back_populates="account")
    policies = relationship("CreditPolicy", back_populates="account")
    usage_records = relationship("CreditUsageRecord", back_populates="account")
    forecasts = relationship("CreditForecast", back_populates="account")


class CreditTransaction(Base):
    """Individual credit transactions"""
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(Enum(CreditTransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Context information
    reference_id = Column(String, nullable=True)  # ID of related record (subscription, etc.)
    reference_type = Column(String, nullable=True)  # Type of reference
    description = Column(Text, nullable=True)
    
    # LLM-specific information
    llm_model = Column(Enum(LLMModelType), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost_per_token = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    account = relationship("CreditAccount", back_populates="transactions")
    usage_records = relationship("CreditUsageRecord", back_populates="transaction")


class CreditPolicy(Base):
    """Credit allocation and usage policies"""
    __tablename__ = "credit_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    
    # Policy details
    policy_type = Column(Enum(CreditPolicyType), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Allocation settings
    monthly_allocation = Column(Float, nullable=True)
    auto_replenish = Column(Boolean, default=False, nullable=False)
    minimum_balance = Column(Float, default=0.0, nullable=False)
    maximum_allocation = Column(Float, nullable=True)
    
    # Usage limits
    daily_limit = Column(Float, nullable=True)
    hourly_limit = Column(Float, nullable=True)
    rate_limit = Column(Float, nullable=True)  # requests per second
    
    # Cost settings
    cost_per_unit = Column(Float, nullable=True)
    bulk_discount_rate = Column(Float, default=0.0, nullable=False)
    
    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    account = relationship("CreditAccount", back_populates="policies")


class CreditUsageRecord(Base):
    """Detailed credit usage records"""
    __tablename__ = "credit_usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("credit_transactions.id"), nullable=True)
    
    # Usage details
    service_type = Column(String, nullable=False)  # llm, api, document_processing, etc.
    operation_type = Column(String, nullable=False)  # extract_fields, generate_text, etc.
    
    # Resource usage
    resource_id = Column(String, nullable=True)  # document ID, session ID, etc.
    quantity_used = Column(Float, nullable=False)
    unit_type = Column(String, nullable=False)  # tokens, api_calls, documents, etc.
    
    # Cost calculation
    cost_per_unit = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # LLM-specific metrics
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    
    # Context
    endpoint = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    account = relationship("CreditAccount", back_populates="usage_records")
    transaction = relationship("CreditTransaction", back_populates="usage_records")


class CreditAlert(Base):
    """Credit balance and usage alerts"""
    __tablename__ = "credit_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String, nullable=False)  # low_balance, high_usage, forecast_exceeded
    severity = Column(String, nullable=False, default="info")  # info, warning, critical
    
    # Alert conditions
    threshold_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    
    # Alert state
    is_active = Column(Boolean, default=True, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    account = relationship("CreditAccount")


class CreditForecast(Base):
    """Credit usage forecasts and predictions"""
    __tablename__ = "credit_forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("credit_accounts.id"), nullable=False)
    
    # Forecast details
    forecast_type = Column(String, nullable=False)  # daily, weekly, monthly
    time_period = Column(String, nullable=False)  # next_24h, next_week, next_month
    
    # Predicted usage
    predicted_usage = Column(Float, nullable=False)
    predicted_cost = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False, default=0.8)
    
    # Context
    based_on_days = Column(Integer, nullable=False, default=30)
    last_calculated = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    account = relationship("CreditAccount", back_populates="forecasts")


class LLMUsageMetrics(Base):
    """Aggregated LLM usage metrics for analytics"""
    __tablename__ = "llm_usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time aggregation
    aggregation_period = Column(String, nullable=False)  # hourly, daily, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Model metrics
    model_type = Column(Enum(LLMModelType), nullable=False)
    
    # Usage statistics
    total_requests = Column(Integer, default=0, nullable=False)
    total_prompt_tokens = Column(Integer, default=0, nullable=False)
    total_completion_tokens = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    
    # Performance metrics
    avg_response_time_ms = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    
    # User distribution
    unique_users = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)