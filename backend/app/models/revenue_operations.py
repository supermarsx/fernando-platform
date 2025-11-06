"""
Revenue Operations Models

Database models for revenue analytics, predictive modeling, financial compliance,
and revenue recognition (ASC 606).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Numeric, Date, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.session import Base


class RevenueMetricType(str, enum.Enum):
    """Types of revenue metrics"""
    MRR = "mrr"  # Monthly Recurring Revenue
    ARR = "arr"  # Annual Recurring Revenue
    EXPANSION_REVENUE = "expansion_revenue"
    CONTRACTION_REVENUE = "contraction_revenue"
    CHURN_REVENUE = "churn_revenue"
    NEW_REVENUE = "new_revenue"


class ChurnRiskLevel(str, enum.Enum):
    """Customer churn risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RevenueRecognitionMethod(str, enum.Enum):
    """ASC 606 revenue recognition methods"""
    POINT_IN_TIME = "point_in_time"
    OVER_TIME = "over_time"
    PERCENTAGE_COMPLETION = "percentage_completion"


class TaxJurisdiction(str, enum.Enum):
    """Tax jurisdictions"""
    US_FEDERAL = "us_federal"
    US_STATE = "us_state"
    EU_VAT = "eu_vat"
    UK_VAT = "uk_vat"
    CANADA_GST = "canada_gst"


class RevenueMetric(Base):
    """
    Revenue metrics tracking (MRR, ARR, expansion, contraction)
    """
    __tablename__ = "revenue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Metric details
    metric_type = Column(String(50), nullable=False, index=True)
    value = Column(Numeric(15, 2), nullable=False)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)
    
    # Breakdown
    new_business = Column(Numeric(15, 2), default=0)
    expansion = Column(Numeric(15, 2), default=0)
    contraction = Column(Numeric(15, 2), default=0)
    churn = Column(Numeric(15, 2), default=0)
    
    # Calculated metrics
    growth_rate = Column(Float)
    month_over_month_change = Column(Float)
    year_over_year_change = Column(Float)
    
    # Metadata
    calculation_meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CustomerLifetimeValue(Base):
    """
    Customer lifetime value calculations and predictions
    """
    __tablename__ = "customer_lifetime_values"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, index=True)
    
    # LTV calculations
    historical_ltv = Column(Numeric(15, 2))  # Actual revenue to date
    predicted_ltv = Column(Numeric(15, 2))  # ML-predicted future value
    ltv_confidence_score = Column(Float)  # Model confidence (0-1)
    
    # Customer metrics
    customer_acquisition_cost = Column(Numeric(15, 2))
    ltv_cac_ratio = Column(Float)
    payback_period_months = Column(Float)
    
    # Behavioral features
    total_spend = Column(Numeric(15, 2))
    average_order_value = Column(Numeric(15, 2))
    purchase_frequency = Column(Float)
    customer_age_days = Column(Integer)
    last_purchase_days_ago = Column(Integer)
    
    # Engagement metrics
    feature_adoption_score = Column(Float)
    support_ticket_count = Column(Integer)
    nps_score = Column(Integer)
    
    # Model details
    model_version = Column(String(50))
    prediction_date = Column(DateTime, default=datetime.utcnow, index=True)
    features_used = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChurnPrediction(Base):
    """
    Churn prediction with early warning system
    """
    __tablename__ = "churn_predictions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, index=True)
    
    # Prediction
    churn_probability = Column(Float, nullable=False)  # 0-1
    risk_level = Column(String(20), nullable=False, index=True)
    predicted_churn_date = Column(Date)
    
    # Risk factors
    risk_factors = Column(JSON)  # List of contributing factors
    risk_score_breakdown = Column(JSON)  # Feature importance
    
    # Behavioral signals
    usage_decline_rate = Column(Float)
    payment_issues_count = Column(Integer)
    support_escalations = Column(Integer)
    feature_engagement_score = Column(Float)
    login_frequency_decline = Column(Float)
    
    # Recommended actions
    recommended_interventions = Column(JSON)
    intervention_priority = Column(Integer)
    estimated_save_probability = Column(Float)
    
    # Model details
    model_version = Column(String(50))
    model_accuracy = Column(Float)
    prediction_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Action tracking
    intervention_taken = Column(Boolean, default=False)
    intervention_date = Column(DateTime)
    intervention_outcome = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RevenueForecast(Base):
    """
    Revenue forecasting with machine learning
    """
    __tablename__ = "revenue_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Forecast details
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_type = Column(String(50), nullable=False)  # mrr, arr, total_revenue
    
    # Predictions
    predicted_value = Column(Numeric(15, 2), nullable=False)
    lower_bound = Column(Numeric(15, 2))  # 95% confidence interval
    upper_bound = Column(Numeric(15, 2))
    confidence_interval = Column(Float)
    
    # Actual vs predicted (filled after period ends)
    actual_value = Column(Numeric(15, 2))
    prediction_error = Column(Float)
    accuracy_percentage = Column(Float)
    
    # Model details
    model_type = Column(String(50))  # lstm, arima, prophet, ensemble
    model_version = Column(String(50))
    training_data_points = Column(Integer)
    features_used = Column(JSON)
    
    # Contributing factors
    trend_component = Column(Numeric(15, 2))
    seasonal_component = Column(Numeric(15, 2))
    residual_component = Column(Numeric(15, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class RevenueRecognition(Base):
    """
    ASC 606 Revenue Recognition tracking
    """
    __tablename__ = "revenue_recognition"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Contract references
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    contract_id = Column(Integer, ForeignKey('billing_contracts.id'))
    
    # Recognition details
    recognition_method = Column(String(50), nullable=False)
    total_contract_value = Column(Numeric(15, 2), nullable=False)
    recognized_revenue = Column(Numeric(15, 2), default=0)
    deferred_revenue = Column(Numeric(15, 2))
    
    # Performance obligations
    performance_obligations = Column(JSON)  # List of obligations
    completion_percentage = Column(Float, default=0)
    
    # Period tracking
    contract_start_date = Column(Date, nullable=False)
    contract_end_date = Column(Date, nullable=False)
    recognition_start_date = Column(Date)
    last_recognition_date = Column(Date)
    
    # Recognition schedule
    recognition_schedule = Column(JSON)  # Monthly recognition amounts
    next_recognition_date = Column(Date)
    next_recognition_amount = Column(Numeric(15, 2))
    
    # Status
    is_complete = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    
    # Audit trail
    recognition_history = Column(JSON)  # Immutable history
    last_recognized_by = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaxCompliance(Base):
    """
    Tax compliance and reporting (VAT, sales tax, GAAP)
    """
    __tablename__ = "tax_compliance"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Tax details
    jurisdiction = Column(String(50), nullable=False, index=True)
    tax_type = Column(String(50), nullable=False)  # vat, sales_tax, gst
    tax_period_start = Column(Date, nullable=False, index=True)
    tax_period_end = Column(Date, nullable=False)
    
    # Calculations
    taxable_revenue = Column(Numeric(15, 2), nullable=False)
    tax_rate = Column(Float, nullable=False)
    tax_amount = Column(Numeric(15, 2), nullable=False)
    
    # Breakdown by category
    product_revenue = Column(Numeric(15, 2))
    service_revenue = Column(Numeric(15, 2))
    exempt_revenue = Column(Numeric(15, 2))
    
    # Filing status
    filing_status = Column(String(50), default="pending")  # pending, filed, paid
    filing_date = Column(DateTime)
    payment_date = Column(DateTime)
    confirmation_number = Column(String(100))
    
    # Supporting documentation
    transaction_ids = Column(JSON)  # List of transaction IDs
    supporting_documents = Column(JSON)
    
    # Compliance checks
    compliance_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime)
    verified_by = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccountsReceivable(Base):
    """
    Accounts Receivable tracking and reconciliation
    """
    __tablename__ = "accounts_receivable"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Invoice details
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False, index=True)
    customer_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    
    # Amounts
    invoice_amount = Column(Numeric(15, 2), nullable=False)
    amount_paid = Column(Numeric(15, 2), default=0)
    amount_outstanding = Column(Numeric(15, 2), nullable=False)
    
    # Aging
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    days_outstanding = Column(Integer, index=True)
    aging_bucket = Column(String(50))  # current, 30, 60, 90, 120+
    
    # Status
    status = Column(String(50), nullable=False)  # outstanding, partial, paid, written_off
    payment_status = Column(String(50))
    
    # Collections
    collection_attempts = Column(Integer, default=0)
    last_collection_date = Column(DateTime)
    next_collection_date = Column(DateTime)
    collection_notes = Column(Text)
    
    # Reconciliation
    is_reconciled = Column(Boolean, default=False)
    reconciliation_date = Column(DateTime)
    reconciliation_meta_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccountsPayable(Base):
    """
    Accounts Payable tracking and reconciliation
    """
    __tablename__ = "accounts_payable"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Vendor details
    vendor_name = Column(String(255), nullable=False)
    vendor_id = Column(String(100))
    
    # Invoice details
    invoice_number = Column(String(100), nullable=False)
    invoice_amount = Column(Numeric(15, 2), nullable=False)
    amount_paid = Column(Numeric(15, 2), default=0)
    amount_outstanding = Column(Numeric(15, 2), nullable=False)
    
    # Dates
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    payment_date = Column(DateTime)
    
    # Status
    status = Column(String(50), nullable=False)  # pending, scheduled, paid, disputed
    payment_method = Column(String(50))
    
    # Approvals
    requires_approval = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    approved_by = Column(Integer)
    approved_date = Column(DateTime)
    
    # Reconciliation
    is_reconciled = Column(Boolean, default=False)
    reconciliation_date = Column(DateTime)
    bank_transaction_id = Column(String(100))
    
    # Metadata
    category = Column(String(100))
    gl_account = Column(String(50))
    notes = Column(Text)
    attachments = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinancialAuditLog(Base):
    """
    Tamper-proof financial audit trail
    """
    __tablename__ = "financial_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False)  # revenue, tax, ar, ap, reconciliation
    
    # References
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=False)
    
    # Change tracking
    previous_state = Column(JSON)
    new_state = Column(JSON)
    changes = Column(JSON)  # Detailed field-level changes
    
    # User context
    user_id = Column(String, ForeignKey('users.user_id'))
    user_email = Column(String(255))
    ip_address = Column(String(50))
    
    # Tamper protection
    record_hash = Column(String(256), nullable=False)  # SHA-256 hash
    previous_record_hash = Column(String(256))  # Chain of hashes
    
    # Compliance
    is_compliant = Column(Boolean, default=True)
    compliance_notes = Column(Text)
    retention_until = Column(DateTime)  # Legal retention period
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta_data = Column(JSON)


class CohortAnalysis(Base):
    """
    Customer cohort analysis for revenue patterns
    """
    __tablename__ = "cohort_analysis"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    
    # Cohort definition
    cohort_month = Column(Date, nullable=False, index=True)
    cohort_size = Column(Integer, nullable=False)
    
    # Revenue metrics by month
    month_offset = Column(Integer, nullable=False)  # Months since cohort start
    revenue_month = Column(Date, nullable=False)
    
    # Metrics
    active_customers = Column(Integer)
    retention_rate = Column(Float)
    revenue = Column(Numeric(15, 2))
    cumulative_revenue = Column(Numeric(15, 2))
    average_revenue_per_user = Column(Numeric(15, 2))
    
    # Customer behavior
    expansion_customers = Column(Integer)
    contraction_customers = Column(Integer)
    churned_customers = Column(Integer)
    
    # Calculated at cohort level
    ltv_estimate = Column(Numeric(15, 2))
    payback_achieved = Column(Boolean)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Indexes for performance
Index('idx_revenue_metrics_tenant_period', RevenueMetric.tenant_id, RevenueMetric.period_start)
Index('idx_churn_predictions_risk', ChurnPrediction.tenant_id, ChurnPrediction.risk_level, ChurnPrediction.churn_probability)
Index('idx_ar_aging', AccountsReceivable.tenant_id, AccountsReceivable.days_outstanding, AccountsReceivable.status)
Index('idx_audit_log_entity', FinancialAuditLog.tenant_id, FinancialAuditLog.entity_type, FinancialAuditLog.entity_id)
