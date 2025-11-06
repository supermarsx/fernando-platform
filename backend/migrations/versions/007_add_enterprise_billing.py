"""
Database Migration: Add Enterprise Billing Tables

This migration creates all tables required for enterprise billing features including:
- Multi-entity billing structures
- Department and cost center management
- Billing contracts and amendments
- Budget tracking and alerts
- Approval workflows
- Dispute management
- Financial integrations
- Enterprise reporting
"""

from sqlalchemy import create_engine, MetaData
from app.db.session import engine, Base
# Import all models to ensure they're registered with Base
from app.models import user, job, document, extraction, audit, billing, license, enterprise, usage
from app.models.enterprise_billing import (
    BillingEntity, Department, CostAllocation,
    BillingContract, ContractAmendment,
    Budget, BudgetAlert,
    ApprovalRequest, ApprovalAction, ApprovalRule,
    BillingDispute, DisputeComment,
    FinancialIntegration, IntegrationSyncLog, GLCodeMapping,
    EnterpriseReport
)


def upgrade():
    """Create all enterprise billing tables"""
    print("Creating enterprise billing tables...")
    
    # Create all tables defined in enterprise_billing models
    Base.metadata.create_all(bind=engine, tables=[
        BillingEntity.__table__,
        Department.__table__,
        CostAllocation.__table__,
        BillingContract.__table__,
        ContractAmendment.__table__,
        Budget.__table__,
        BudgetAlert.__table__,
        ApprovalRequest.__table__,
        ApprovalAction.__table__,
        ApprovalRule.__table__,
        BillingDispute.__table__,
        DisputeComment.__table__,
        FinancialIntegration.__table__,
        IntegrationSyncLog.__table__,
        GLCodeMapping.__table__,
        EnterpriseReport.__table__
    ])
    
    print("Enterprise billing tables created successfully!")
    print("\nCreated tables:")
    print("  - billing_entities (Multi-entity billing)")
    print("  - departments (Department management)")
    print("  - cost_allocations (Cost center allocations)")
    print("  - billing_contracts (Contract management)")
    print("  - contract_amendments (Contract amendments)")
    print("  - budgets (Budget tracking)")
    print("  - budget_alerts (Budget alerts)")
    print("  - approval_requests (Approval workflows)")
    print("  - approval_actions (Approval actions)")
    print("  - approval_rules (Approval rules)")
    print("  - billing_disputes (Dispute management)")
    print("  - dispute_comments (Dispute comments)")
    print("  - financial_integrations (Financial system integrations)")
    print("  - integration_sync_logs (Integration sync logs)")
    print("  - gl_code_mappings (GL code mappings)")
    print("  - enterprise_reports (Enterprise reports)")


def downgrade():
    """Drop all enterprise billing tables"""
    print("Dropping enterprise billing tables...")
    
    Base.metadata.drop_all(bind=engine, tables=[
        EnterpriseReport.__table__,
        GLCodeMapping.__table__,
        IntegrationSyncLog.__table__,
        FinancialIntegration.__table__,
        DisputeComment.__table__,
        BillingDispute.__table__,
        ApprovalRule.__table__,
        ApprovalAction.__table__,
        ApprovalRequest.__table__,
        BudgetAlert.__table__,
        Budget.__table__,
        ContractAmendment.__table__,
        BillingContract.__table__,
        CostAllocation.__table__,
        Department.__table__,
        BillingEntity.__table__
    ])
    
    print("Enterprise billing tables dropped successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
