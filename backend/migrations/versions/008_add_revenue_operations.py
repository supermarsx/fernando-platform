"""
Database Migration: Add Revenue Operations Tables

Creates all tables for revenue analytics, predictive modeling, financial compliance,
and audit trails.
"""

from sqlalchemy import create_engine, MetaData
from app.db.session import engine, Base
# Import all models to ensure they're registered
from app.models import user, job, document, extraction, audit, billing, license, enterprise, usage, enterprise_billing
from app.models.revenue_operations import (
    RevenueMetric, CustomerLifetimeValue, ChurnPrediction, RevenueForecast,
    RevenueRecognition, TaxCompliance, AccountsReceivable, AccountsPayable,
    FinancialAuditLog, CohortAnalysis
)


def upgrade():
    """Create all revenue operations tables"""
    print("Creating revenue operations tables...")
    
    # Create all tables defined in revenue_operations models
    Base.metadata.create_all(bind=engine, tables=[
        RevenueMetric.__table__,
        CustomerLifetimeValue.__table__,
        ChurnPrediction.__table__,
        RevenueForecast.__table__,
        RevenueRecognition.__table__,
        TaxCompliance.__table__,
        AccountsReceivable.__table__,
        AccountsPayable.__table__,
        FinancialAuditLog.__table__,
        CohortAnalysis.__table__
    ])
    
    print("Revenue operations tables created successfully!")
    print("\nCreated tables:")
    print("  - revenue_metrics (MRR, ARR, expansion, contraction)")
    print("  - customer_lifetime_values (LTV predictions)")
    print("  - churn_predictions (ML-based churn risk)")
    print("  - revenue_forecasts (Time series forecasting)")
    print("  - revenue_recognition (ASC 606 compliance)")
    print("  - tax_compliance (VAT, sales tax reporting)")
    print("  - accounts_receivable (AR automation)")
    print("  - accounts_payable (AP automation)")
    print("  - financial_audit_logs (Tamper-proof audit trail)")
    print("  - cohort_analysis (Customer cohort tracking)")


def downgrade():
    """Drop all revenue operations tables"""
    print("Dropping revenue operations tables...")
    
    Base.metadata.drop_all(bind=engine, tables=[
        CohortAnalysis.__table__,
        FinancialAuditLog.__table__,
        AccountsPayable.__table__,
        AccountsReceivable.__table__,
        TaxCompliance.__table__,
        RevenueRecognition.__table__,
        RevenueForecast.__table__,
        ChurnPrediction.__table__,
        CustomerLifetimeValue.__table__,
        RevenueMetric.__table__
    ])
    
    print("Revenue operations tables dropped successfully!")


if __name__ == "__main__":
    try:
        upgrade()
        print("\nMigration completed successfully!")
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise
