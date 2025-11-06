"""
Enterprise Billing Models

This module defines advanced enterprise billing features including:
- Multi-entity billing with parent/child organization hierarchies
- Department allocation and cost center mapping
- Custom billing agreements and contract management
- Budget tracking and spending controls
- Approval workflows for purchases and license changes
- Billing dispute management and resolution
- Financial integration connectors (QuickBooks, Xero, SAP)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON, Numeric, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.session import Base


class EntityType(str, enum.Enum):
    """Organization entity types"""
    ROOT = "root"  # Root parent organization
    SUBSIDIARY = "subsidiary"  # Subsidiary or child company
    DIVISION = "division"  # Business division
    DEPARTMENT = "department"  # Department unit
    BRANCH = "branch"  # Geographic branch


class CostCenterType(str, enum.Enum):
    """Cost center types"""
    OPERATIONAL = "operational"  # Operational department
    REVENUE = "revenue"  # Revenue-generating unit
    PROFIT = "profit"  # Profit center
    INVESTMENT = "investment"  # Investment center


class ContractStatus(str, enum.Enum):
    """Contract status options"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"


class ContractType(str, enum.Enum):
    """Contract types"""
    STANDARD = "standard"  # Standard subscription agreement
    CUSTOM = "custom"  # Custom negotiated contract
    ENTERPRISE = "enterprise"  # Enterprise volume contract
    MSA = "msa"  # Master service agreement
    PILOT = "pilot"  # Pilot program contract


class ApprovalStatus(str, enum.Enum):
    """Approval workflow status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"
    EXPIRED = "expired"


class DisputeStatus(str, enum.Enum):
    """Dispute status options"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class DisputeCategory(str, enum.Enum):
    """Dispute categories"""
    BILLING_ERROR = "billing_error"
    SERVICE_ISSUE = "service_issue"
    USAGE_DISPUTE = "usage_dispute"
    CONTRACT_VIOLATION = "contract_violation"
    PRICING_DISCREPANCY = "pricing_discrepancy"
    REFUND_REQUEST = "refund_request"


class BudgetPeriod(str, enum.Enum):
    """Budget period types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class IntegrationProvider(str, enum.Enum):
    """Financial integration providers"""
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAP = "sap"
    NETSUITE = "netsuite"
    SAGE = "sage"
    DYNAMICS = "dynamics"
    CUSTOM = "custom"


# ============================
# Multi-Entity Billing Models
# ============================

class BillingEntity(Base):
    """
    Organization entities for multi-entity billing
    Supports parent/child hierarchies for consolidated invoicing
    """
    __tablename__ = "billing_entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String(64), unique=True, index=True)
    
    # Entity details
    name = Column(String(200), nullable=False)
    legal_name = Column(String(200))
    entity_type = Column(Enum(EntityType), default=EntityType.SUBSIDIARY)
    
    # Hierarchy
    parent_entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=True)
    
    # References
    tenant_id = Column(String, ForeignKey('tenants.tenant_id'), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    
    # Tax and legal information
    tax_id = Column(String(100))
    registration_number = Column(String(100))
    billing_address = Column(JSON)  # Street, city, state, country, postal_code
    
    # Billing settings
    consolidated_billing = Column(Boolean, default=False)  # Bill through parent
    billing_contact_name = Column(String(200))
    billing_contact_email = Column(String(200))
    billing_contact_phone = Column(String(50))
    
    # Financial settings
    currency = Column(String(3), default="EUR")
    payment_terms_days = Column(Integer, default=30)
    credit_limit = Column(Float, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # GL code mapping for accounting integration
    default_gl_code = Column(String(50))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_entity = relationship("BillingEntity", remote_side=[id], backref="child_entities")
    departments = relationship("Department", back_populates="entity")
    contracts = relationship("BillingContract", back_populates="entity")
    budgets = relationship("Budget", back_populates="entity")


# ============================
# Department & Cost Center Models
# ============================

class Department(Base):
    """
    Departments for cost allocation and budget tracking
    """
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(String(64), unique=True, index=True)
    
    # Department details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    department_code = Column(String(50), unique=True, index=True)
    
    # References
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=False)
    parent_department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    
    # Cost center information
    cost_center_code = Column(String(50), unique=True, index=True)
    cost_center_type = Column(Enum(CostCenterType), default=CostCenterType.OPERATIONAL)
    
    # Manager
    manager_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # GL code mapping
    default_gl_code = Column(String(50))
    expense_gl_code = Column(String(50))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity = relationship("BillingEntity", back_populates="departments")
    parent_department = relationship("Department", remote_side=[id], backref="child_departments")
    cost_allocations = relationship("CostAllocation", back_populates="department")
    budgets = relationship("Budget", back_populates="department")

    # Indexes
    __table_args__ = (
        Index('idx_department_entity', 'entity_id'),
        Index('idx_department_cost_center', 'cost_center_code'),
    )


class CostAllocation(Base):
    """
    Usage and cost allocation to departments/cost centers
    """
    __tablename__ = "cost_allocations"

    id = Column(Integer, primary_key=True, index=True)
    
    # References
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    
    # Allocation details
    allocation_type = Column(String(50), nullable=False)  # subscription, usage, overage, license
    description = Column(Text)
    
    # Amounts
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    
    # Allocation period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # GL codes
    gl_code = Column(String(50))
    expense_category = Column(String(100))
    
    # Usage details
    quantity = Column(Float)  # Number of units (users, documents, etc.)
    unit_type = Column(String(50))  # users, documents, api_calls, storage_gb
    unit_price = Column(Float)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    department = relationship("Department", back_populates="cost_allocations")

    # Indexes
    __table_args__ = (
        Index('idx_allocation_department_period', 'department_id', 'period_start', 'period_end'),
        Index('idx_allocation_gl_code', 'gl_code'),
    )


# ============================
# Contract Management Models
# ============================

class BillingContract(Base):
    """
    Custom billing agreements and contracts for enterprise customers
    """
    __tablename__ = "billing_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String(64), unique=True, index=True)
    
    # Contract details
    contract_number = Column(String(100), unique=True, index=True)
    name = Column(String(200), nullable=False)
    contract_type = Column(Enum(ContractType), default=ContractType.STANDARD)
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT)
    
    # References
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    
    # Terms
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    term_length_months = Column(Integer, nullable=False)
    auto_renew = Column(Boolean, default=True)
    renewal_notice_days = Column(Integer, default=30)
    
    # Pricing
    contract_value = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    billing_frequency = Column(String(50), default="monthly")  # monthly, quarterly, annually, upfront
    
    # Discount and pricing
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    custom_pricing = Column(JSON)  # Custom pricing for specific services/tiers
    
    # Commitment
    minimum_commitment = Column(Float)  # Minimum spend commitment
    usage_commitment = Column(JSON)  # Committed usage volumes
    
    # Payment terms
    payment_terms_days = Column(Integer, default=30)
    payment_method = Column(String(50))
    credit_limit = Column(Float)
    
    # SLA terms
    sla_terms = Column(JSON)  # Service level agreement details
    uptime_guarantee = Column(Float)  # Percentage
    support_level = Column(String(50))  # standard, priority, enterprise
    
    # Compliance and legal
    compliance_requirements = Column(JSON)  # GDPR, SOX, HIPAA, etc.
    data_residency = Column(String(100))  # Geographic data storage requirements
    
    # Contract documents
    pdf_url = Column(String(500))
    signed_pdf_url = Column(String(500))
    
    # Parties
    signed_by_customer = Column(String(200))
    signed_by_customer_date = Column(DateTime)
    signed_by_vendor = Column(String(200))
    signed_by_vendor_date = Column(DateTime)
    
    # Renewal tracking
    renewal_count = Column(Integer, default=0)
    previous_contract_id = Column(Integer, ForeignKey('billing_contracts.id'))
    
    # Termination
    termination_date = Column(DateTime)
    termination_reason = Column(Text)
    early_termination_fee = Column(Float)
    
    # Metadata
    notes = Column(Text)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey('users.user_id'))
    
    # Relationships
    entity = relationship("BillingEntity", back_populates="contracts")
    contract_amendments = relationship("ContractAmendment", back_populates="contract")
    approval_requests = relationship("ApprovalRequest", back_populates="contract")

    # Indexes
    __table_args__ = (
        Index('idx_contract_status', 'status'),
        Index('idx_contract_dates', 'start_date', 'end_date'),
    )


class ContractAmendment(Base):
    """
    Track amendments to billing contracts
    """
    __tablename__ = "contract_amendments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey('billing_contracts.id'), nullable=False)
    
    # Amendment details
    amendment_number = Column(String(50))
    description = Column(Text, nullable=False)
    amendment_type = Column(String(50))  # pricing, term, scope, sla, etc.
    
    # Changes
    old_values = Column(JSON)
    new_values = Column(JSON)
    
    # Effective dates
    effective_date = Column(DateTime, nullable=False)
    
    # Approval
    approved_by_user_id = Column(Integer, ForeignKey('users.user_id'))
    approved_at = Column(DateTime)
    
    # Document
    pdf_url = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey('users.user_id'))
    
    # Relationships
    contract = relationship("BillingContract", back_populates="contract_amendments")


# ============================
# Budget Management Models
# ============================

class Budget(Base):
    """
    Budget allocation and tracking for departments/entities
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(String(64), unique=True, index=True)
    
    # Budget details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # References
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    
    # Budget period
    period_type = Column(Enum(BudgetPeriod), default=BudgetPeriod.MONTHLY)
    fiscal_year = Column(Integer)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Budget amounts
    allocated_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0)
    committed_amount = Column(Float, default=0)  # Pending approvals
    remaining_amount = Column(Float)
    currency = Column(String(3), default="EUR")
    
    # Controls
    allow_overspend = Column(Boolean, default=False)
    overspend_limit_percent = Column(Float)  # Maximum overspend percentage
    require_approval_above = Column(Float)  # Require approval for charges above this amount
    
    # Alerts
    alert_threshold_percent = Column(Float, default=80)  # Alert at 80% spent
    warning_threshold_percent = Column(Float, default=90)  # Warning at 90% spent
    
    # Rollover settings
    allow_rollover = Column(Boolean, default=False)
    rollover_percent = Column(Float, default=100)  # Percentage of unused budget to roll over
    
    # Status
    is_active = Column(Boolean, default=True)
    is_frozen = Column(Boolean, default=False)  # Temporarily freeze spending
    
    # Owner
    owner_user_id = Column(Integer, ForeignKey('users.user_id'))
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity = relationship("BillingEntity", back_populates="budgets")
    department = relationship("Department", back_populates="budgets")
    alerts = relationship("BudgetAlert", back_populates="budget")

    # Indexes
    __table_args__ = (
        Index('idx_budget_period', 'period_start', 'period_end'),
        Index('idx_budget_entity_dept', 'entity_id', 'department_id'),
    )


class BudgetAlert(Base):
    """
    Alerts generated when budget thresholds are exceeded
    """
    __tablename__ = "budget_alerts"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # threshold, overspend, freeze
    severity = Column(String(50), default="warning")  # info, warning, critical
    message = Column(Text, nullable=False)
    
    # Threshold information
    threshold_percent = Column(Float)
    spent_amount = Column(Float)
    allocated_amount = Column(Float)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    
    # Notifications
    notified_users = Column(JSON)  # List of user IDs who were notified
    notification_sent_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    budget = relationship("Budget", back_populates="alerts")

    # Indexes
    __table_args__ = (
        Index('idx_alert_budget_resolved', 'budget_id', 'is_resolved'),
    )


# ============================
# Approval Workflow Models
# ============================

class ApprovalRequest(Base):
    """
    Approval requests for purchases, license changes, and contract modifications
    """
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), unique=True, index=True)
    
    # Request details
    request_type = Column(String(50), nullable=False)  # purchase, license_change, contract_amendment, budget_increase
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # References
    contract_id = Column(Integer, ForeignKey('billing_contracts.id'), nullable=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)
    
    # Financial details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    
    # Requestor
    requested_by_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    
    # Status
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    
    # Approval workflow
    approval_level = Column(Integer, default=1)  # Current approval level
    required_approvals = Column(Integer, default=1)  # Total approvals needed
    approvals_received = Column(Integer, default=0)
    
    # Dates
    submitted_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    expires_at = Column(DateTime)  # Auto-reject if not approved by this date
    
    # Rejection details
    rejection_reason = Column(Text)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("BillingContract", back_populates="approval_requests")
    approvals = relationship("ApprovalAction", back_populates="request")

    # Indexes
    __table_args__ = (
        Index('idx_approval_status', 'status'),
        Index('idx_approval_requester', 'requested_by_user_id'),
    )


class ApprovalAction(Base):
    """
    Individual approval actions within the workflow
    """
    __tablename__ = "approval_actions"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey('approval_requests.id'), nullable=False)
    
    # Approver
    approver_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    approval_level = Column(Integer, nullable=False)  # Level in workflow
    
    # Action
    action = Column(String(50), nullable=False)  # approved, rejected, delegated
    comments = Column(Text)
    
    # Delegation
    delegated_to_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Metadata
    acted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    request = relationship("ApprovalRequest", back_populates="approvals")


class ApprovalRule(Base):
    """
    Configurable approval rules based on amount, type, department
    """
    __tablename__ = "approval_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Rule details
    rule_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Applicability
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    request_type = Column(String(50))  # Blank for all types
    
    # Conditions
    min_amount = Column(Float)  # Rule applies if amount >= min_amount
    max_amount = Column(Float)  # Rule applies if amount <= max_amount
    
    # Approval requirements
    required_approvers = Column(JSON)  # List of user_ids or role names
    required_approval_count = Column(Integer, default=1)
    approval_sequence = Column(Boolean, default=False)  # Sequential vs parallel
    
    # Escalation
    escalation_hours = Column(Integer, default=24)  # Escalate if not approved within hours
    escalate_to_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority rules evaluated first
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================
# Dispute Management Models
# ============================

class BillingDispute(Base):
    """
    Billing disputes and resolution tracking
    """
    __tablename__ = "billing_disputes"

    id = Column(Integer, primary_key=True, index=True)
    dispute_id = Column(String(64), unique=True, index=True)
    
    # Dispute details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(DisputeCategory), default=DisputeCategory.BILLING_ERROR)
    status = Column(Enum(DisputeStatus), default=DisputeStatus.OPEN)
    
    # References
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    
    # Financial details
    disputed_amount = Column(Float, nullable=False)
    resolved_amount = Column(Float)  # Final amount after resolution
    currency = Column(String(3), default="EUR")
    
    # Parties
    raised_by_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Timeline
    opened_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    closed_at = Column(DateTime)
    sla_response_deadline = Column(DateTime)  # SLA for first response
    sla_resolution_deadline = Column(DateTime)  # SLA for resolution
    
    # Resolution
    resolution = Column(Text)
    resolution_type = Column(String(50))  # credit, refund, adjustment, no_action
    credit_amount = Column(Float, default=0)
    refund_amount = Column(Float, default=0)
    
    # Escalation
    escalation_level = Column(Integer, default=0)
    escalated_to_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    escalated_at = Column(DateTime)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = relationship("DisputeComment", back_populates="dispute")

    # Indexes
    __table_args__ = (
        Index('idx_dispute_status', 'status'),
        Index('idx_dispute_invoice', 'invoice_id'),
    )


class DisputeComment(Base):
    """
    Comments and communication thread for disputes
    """
    __tablename__ = "dispute_comments"

    id = Column(Integer, primary_key=True, index=True)
    dispute_id = Column(Integer, ForeignKey('billing_disputes.id'), nullable=False)
    
    # Comment details
    comment = Column(Text, nullable=False)
    comment_type = Column(String(50), default="comment")  # comment, status_change, resolution
    
    # Author
    author_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    is_internal = Column(Boolean, default=False)  # Internal notes not visible to customer
    
    # Attachments
    attachments = Column(JSON)  # List of file URLs
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dispute = relationship("BillingDispute", back_populates="comments")


# ============================
# Financial Integration Models
# ============================

class FinancialIntegration(Base):
    """
    Financial system integrations (QuickBooks, Xero, SAP, etc.)
    """
    __tablename__ = "financial_integrations"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(String(64), unique=True, index=True)
    
    # Integration details
    name = Column(String(200), nullable=False)
    provider = Column(Enum(IntegrationProvider), nullable=False)
    
    # References
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=False)
    
    # Configuration
    api_endpoint = Column(String(500))
    auth_type = Column(String(50))  # oauth, api_key, basic
    credentials = Column(Text)  # Encrypted credentials
    
    # Sync settings
    sync_frequency = Column(String(50), default="daily")  # realtime, hourly, daily, manual
    auto_sync_enabled = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    next_sync_at = Column(DateTime)
    
    # Mapping configuration
    chart_of_accounts_mapping = Column(JSON)  # Map local GL codes to external system
    customer_mapping = Column(JSON)  # Map entities to external customer IDs
    product_mapping = Column(JSON)  # Map subscription plans to external products
    
    # Sync scope
    sync_invoices = Column(Boolean, default=True)
    sync_payments = Column(Boolean, default=True)
    sync_credits = Column(Boolean, default=True)
    sync_customers = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Metadata
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sync_logs = relationship("IntegrationSyncLog", back_populates="integration")


class IntegrationSyncLog(Base):
    """
    Log of financial system sync operations
    """
    __tablename__ = "integration_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey('financial_integrations.id'), nullable=False)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # invoice, payment, customer, full
    sync_direction = Column(String(50), default="export")  # export, import, bidirectional
    
    # Status
    status = Column(String(50), nullable=False)  # started, completed, failed, partial
    
    # Results
    records_processed = Column(Integer, default=0)
    records_succeeded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Error details
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Metadata
    meta_data = Column(JSON)
    
    # Relationships
    integration = relationship("FinancialIntegration", back_populates="sync_logs")

    # Indexes
    __table_args__ = (
        Index('idx_sync_integration_time', 'integration_id', 'started_at'),
    )


class GLCodeMapping(Base):
    """
    General Ledger code mapping for accounting integration
    """
    __tablename__ = "gl_code_mappings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Entity reference
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=True)
    
    # GL code details
    internal_gl_code = Column(String(50), nullable=False, index=True)
    external_gl_code = Column(String(50))  # GL code in external system
    account_name = Column(String(200))
    account_type = Column(String(50))  # asset, liability, revenue, expense
    
    # Categorization
    category = Column(String(100))  # subscription_revenue, usage_revenue, etc.
    subcategory = Column(String(100))
    
    # Integration
    integration_id = Column(Integer, ForeignKey('financial_integrations.id'), nullable=True)
    external_account_id = Column(String(100))  # Account ID in external system
    
    # Tax handling
    tax_treatment = Column(String(50))  # taxable, exempt, zero_rated
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    description = Column(Text)
    meta_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_gl_mapping_codes', 'internal_gl_code', 'external_gl_code'),
    )


# ============================
# Enterprise Reporting Models
# ============================

class EnterpriseReport(Base):
    """
    Enterprise financial reports and dashboards
    """
    __tablename__ = "enterprise_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True)
    
    # Report details
    report_name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)  # financial, usage, budget, forecast
    description = Column(Text)
    
    # References
    entity_id = Column(Integer, ForeignKey('billing_entities.id'), nullable=True)
    
    # Report period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Generated data
    report_data = Column(JSON)  # Actual report data
    summary_metrics = Column(JSON)  # Key metrics summary
    
    # Files
    pdf_url = Column(String(500))
    excel_url = Column(String(500))
    
    # Status
    status = Column(String(50), default="generating")  # generating, completed, failed
    
    # Scheduling
    is_scheduled = Column(Boolean, default=False)
    schedule_frequency = Column(String(50))  # daily, weekly, monthly, quarterly
    last_generated_at = Column(DateTime)
    next_generation_at = Column(DateTime)
    
    # Recipients
    recipients = Column(JSON)  # List of user_ids or email addresses
    
    # Metadata
    generated_by_user_id = Column(Integer, ForeignKey('users.user_id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_report_entity_period', 'entity_id', 'period_start', 'period_end'),
    )
