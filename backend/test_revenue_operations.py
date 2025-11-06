"""
Comprehensive Test Suite for Revenue Operations

Tests all revenue analytics, predictive models, financial compliance,
and document processing features.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.db.session import Base
from app.services.revenue_analytics_service import RevenueAnalyticsService, PredictiveAnalyticsService
from app.services.financial_compliance_service import (
    RevenueRecognitionService, TaxComplianceService, ARAPService, FinancialAuditService
)
from app.models.revenue_operations import (
    RevenueMetric, CustomerLifetimeValue, ChurnPrediction, RevenueForecast,
    RevenueRecognition, TaxCompliance, AccountsReceivable, AccountsPayable,
    FinancialAuditLog, RevenueRecognitionMethod, TaxJurisdiction
)
from app.models.user import User
from app.models.billing import Subscription, Invoice, SubscriptionStatus, InvoiceStatus, SubscriptionPlan
from app.models.enterprise import Tenant
from app.models.license import LicenseTierModel, License
from app.models.job import Job  # Import Job model
from app.ml.revenue_ml_models import ltv_model, churn_model, train_models_with_historical_data

# Import all other models to ensure their tables are created
try:
    from app.models.enterprise_billing import *  # Import all enterprise billing models
except ImportError:
    pass

try:
    from app.models.usage import *  # Import usage models
except ImportError:
    pass


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_tenant(db_session):
    """Create a sample tenant"""
    tenant = Tenant(
        tenant_id="test-tenant",
        name="Fernando",
        slug="fernando"
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def sample_user(db_session, sample_tenant):
    """Create a sample user"""
    user = User(
        user_id="user-123",
        tenant_id=sample_tenant.tenant_id,
        email="customer@example.com",
        password_hash="hashed",
        full_name="Test Customer",
        created_at=datetime.utcnow() - timedelta(days=365)
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_subscription(db_session, sample_tenant, sample_user):
    """Create a sample subscription"""
    subscription = Subscription(
        tenant_id=sample_tenant.tenant_id,
        user_id=sample_user.user_id,
        subscription_id="sub-123",
        status=SubscriptionStatus.ACTIVE,
        amount=Decimal('99.00'),
        billing_cycle="monthly",
        current_period_start=date.today() - timedelta(days=15),
        current_period_end=date.today() + timedelta(days=15)
    )
    db_session.add(subscription)
    db_session.commit()
    return subscription


@pytest.fixture
def sample_invoice(db_session, sample_tenant, sample_user):
    """Create a sample paid invoice"""
    invoice = Invoice(
        tenant_id=sample_tenant.tenant_id,
        user_id=sample_user.user_id,
        invoice_number="INV-001",
        status=InvoiceStatus.PAID,
        subtotal=Decimal('99.00'),
        tax=Decimal('19.80'),
        total=Decimal('118.80'),
        paid=True,
        paid_date=datetime.utcnow() - timedelta(days=5),
        period_start=date.today() - timedelta(days=30),
        period_end=date.today()
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice


# ============================================================================
# REVENUE ANALYTICS TESTS
# ============================================================================

def test_calculate_mrr(db_session, sample_tenant, sample_subscription):
    """Test MRR calculation"""
    service = RevenueAnalyticsService(db_session)
    mrr = service.calculate_mrr(sample_tenant.tenant_id, date.today())
    
    assert mrr == Decimal('99.00')


def test_calculate_arr(db_session, sample_tenant, sample_subscription):
    """Test ARR calculation"""
    service = RevenueAnalyticsService(db_session)
    arr = service.calculate_arr(sample_tenant.tenant_id, date.today())
    
    assert arr == Decimal('1188.00')  # 99 * 12


def test_revenue_breakdown(db_session, sample_tenant):
    """Test revenue breakdown calculation"""
    service = RevenueAnalyticsService(db_session)
    
    # Create historical subscriptions to test breakdown
    user1 = User(
        user_id="user-1",
        tenant_id=sample_tenant.tenant_id,
        email="user1@example.com",
        password_hash="hashed",
        full_name="User One"
    )
    user2 = User(
        user_id="user-2",
        tenant_id=sample_tenant.tenant_id,
        email="user2@example.com",
        password_hash="hashed",
        full_name="User Two"
    )
    db_session.add_all([user1, user2])
    
    # New customer
    new_sub = Subscription(
        tenant_id=sample_tenant.tenant_id,
        user_id=user1.user_id,
        subscription_id="sub-new",
        status=SubscriptionStatus.ACTIVE,
        amount=Decimal('50.00'),
        billing_cycle="monthly",
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=30)
    )
    
    # Expansion customer (was $50, now $100)
    expansion_sub = Subscription(
        tenant_id=sample_tenant.tenant_id,
        user_id=user2.user_id,
        subscription_id="sub-expansion",
        status=SubscriptionStatus.ACTIVE,
        amount=Decimal('100.00'),
        billing_cycle="monthly",
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=30)
    )
    
    db_session.add_all([new_sub, expansion_sub])
    db_session.commit()
    
    # Test breakdown
    breakdown = service.calculate_revenue_breakdown(
        sample_tenant.tenant_id,
        date.today() - timedelta(days=30),
        date.today()
    )
    
    assert "new_revenue" in breakdown
    assert "expansion_revenue" in breakdown
    assert "contraction_revenue" in breakdown
    assert "churn_revenue" in breakdown


def test_save_revenue_metrics(db_session, sample_tenant, sample_subscription):
    """Test saving revenue metrics"""
    service = RevenueAnalyticsService(db_session)
    
    metric = service.save_revenue_metrics(
        sample_tenant.tenant_id,
        date.today() - timedelta(days=30),
        date.today()
    )
    
    assert metric.id is not None
    assert metric.value > 0
    assert metric.metric_type == "mrr"
    assert metric.growth_rate is not None


# ============================================================================
# PREDICTIVE ANALYTICS TESTS
# ============================================================================

def test_calculate_customer_ltv(db_session, sample_tenant, sample_user, sample_invoice):
    """Test customer LTV calculation"""
    service = PredictiveAnalyticsService(db_session)
    
    ltv = service.calculate_customer_ltv(sample_tenant.tenant_id, sample_user.user_id)
    
    assert ltv is not None
    assert ltv.historical_ltv > 0
    assert ltv.predicted_ltv > 0
    assert 0 <= ltv.ltv_confidence_score <= 1
    assert ltv.customer_age_days > 0


def test_predict_churn(db_session, sample_tenant, sample_user, sample_subscription):
    """Test churn prediction"""
    service = PredictiveAnalyticsService(db_session)
    
    prediction = service.predict_churn(sample_tenant.tenant_id, sample_user.user_id)
    
    assert prediction is not None
    assert 0 <= prediction.churn_probability <= 1
    assert prediction.risk_level in ["low", "medium", "high", "critical"]
    assert isinstance(prediction.risk_factors, list)
    assert isinstance(prediction.recommended_interventions, list)


def test_ml_model_training():
    """Test ML model training with sample data"""
    # Create sample training data
    training_data = []
    for i in range(100):
        training_data.append({
            'customer_features': {
                'historical_ltv': float(100 + i * 10),
                'avg_order_value': float(50 + i * 2),
                'purchase_frequency': 1.5 + (i % 10) * 0.1,
                'customer_age_days': 365 + i * 10,
                'last_purchase_days': i % 90,
                'feature_adoption_score': 0.5 + (i % 5) * 0.1,
                'support_ticket_count': i % 3,
                'payment_issues': i % 2
            },
            'actual_ltv': float(150 + i * 15),
            'churned': bool(i % 4 == 0)  # 25% churn rate
        })
    
    # Train models
    results = train_models_with_historical_data(training_data)
    
    assert results['ltv_score'] > 0
    assert results['churn_accuracy'] > 0.5
    assert ltv_model.is_trained
    assert churn_model.is_trained


# ============================================================================
# REVENUE RECOGNITION TESTS (ASC 606)
# ============================================================================

def test_create_recognition_schedule(db_session, sample_tenant, sample_invoice):
    """Test ASC 606 revenue recognition schedule creation"""
    service = RevenueRecognitionService(db_session)
    
    recognition = service.create_recognition_schedule(
        sample_tenant.tenant_id,
        sample_invoice.id,
        method=RevenueRecognitionMethod.OVER_TIME
    )
    
    assert recognition.id is not None
    assert recognition.total_contract_value == sample_invoice.total
    assert recognition.deferred_revenue == sample_invoice.total
    assert recognition.recognized_revenue == 0
    assert len(recognition.recognition_schedule) > 0


def test_recognize_revenue(db_session, sample_tenant, sample_invoice):
    """Test revenue recognition execution"""
    service = RevenueRecognitionService(db_session)
    
    # Create schedule
    recognition = service.create_recognition_schedule(
        sample_tenant.tenant_id,
        sample_invoice.id
    )
    
    # Recognize revenue for current period
    result = service.recognize_revenue(recognition.id, date.today())
    
    assert result['status'] == 'success'
    assert Decimal(result['amount_recognized']) > 0
    assert Decimal(result['total_recognized']) > 0


def test_point_in_time_recognition(db_session, sample_tenant, sample_invoice):
    """Test point-in-time revenue recognition"""
    service = RevenueRecognitionService(db_session)
    
    recognition = service.create_recognition_schedule(
        sample_tenant.tenant_id,
        sample_invoice.id,
        method=RevenueRecognitionMethod.POINT_IN_TIME
    )
    
    # Should have single recognition event
    assert len(recognition.recognition_schedule) == 1
    assert Decimal(recognition.recognition_schedule[0]['amount']) == sample_invoice.total


# ============================================================================
# TAX COMPLIANCE TESTS
# ============================================================================

def test_calculate_tax_liability(db_session, sample_tenant, sample_invoice):
    """Test tax liability calculation"""
    service = TaxComplianceService(db_session)
    
    tax_record = service.calculate_tax_liability(
        sample_tenant.tenant_id,
        TaxJurisdiction.EU_VAT,
        date.today() - timedelta(days=30),
        date.today()
    )
    
    assert tax_record.id is not None
    assert tax_record.taxable_revenue > 0
    assert tax_record.tax_amount > 0
    assert tax_record.tax_rate > 0
    assert tax_record.jurisdiction == "eu_vat"


def test_tax_rate_determination(db_session, sample_tenant):
    """Test tax rate determination for different jurisdictions"""
    service = TaxComplianceService(db_session)
    
    us_rate = service._get_tax_rate(TaxJurisdiction.US_STATE)
    eu_rate = service._get_tax_rate(TaxJurisdiction.EU_VAT)
    uk_rate = service._get_tax_rate(TaxJurisdiction.UK_VAT)
    
    assert us_rate == 0.07
    assert eu_rate == 0.20
    assert uk_rate == 0.20


# ============================================================================
# AR/AP TESTS
# ============================================================================

def test_create_ar_record(db_session, sample_tenant, sample_invoice):
    """Test AR record creation"""
    service = ARAPService(db_session)
    
    ar_record = service.create_ar_record(sample_tenant.tenant_id, sample_invoice.id)
    
    assert ar_record.id is not None
    assert ar_record.invoice_amount == sample_invoice.total
    assert ar_record.status == "paid"  # Invoice was paid
    assert ar_record.days_outstanding >= 0


def test_ar_aging_report(db_session, sample_tenant, sample_invoice):
    """Test AR aging report generation"""
    service = ARAPService(db_session)
    
    # Create AR record
    service.create_ar_record(sample_tenant.tenant_id, sample_invoice.id)
    
    # Generate report
    report = service.get_ar_aging_report(sample_tenant.tenant_id)
    
    assert "aging_summary" in report
    assert "total_outstanding" in report
    assert "record_count" in report
    assert report["record_count"] >= 0


def test_ar_aging_buckets(db_session, sample_tenant):
    """Test AR aging bucket classification"""
    # Create overdue invoice
    user = User(
        user_id="user-overdue",
        tenant_id=sample_tenant.tenant_id,
        email="overdue@example.com",
        password_hash="hashed",
        full_name="Overdue Customer",
        created_at=datetime.utcnow() - timedelta(days=100)
    )
    db_session.add(user)
    
    old_invoice = Invoice(
        tenant_id=sample_tenant.tenant_id,
        user_id=user.user_id,
        invoice_number="INV-OVERDUE",
        status=InvoiceStatus.PENDING,
        subtotal=Decimal('500.00'),
        tax=Decimal('0'),
        total=Decimal('500.00'),
        paid=False,
        created_at=datetime.utcnow() - timedelta(days=75)
    )
    db_session.add(old_invoice)
    db_session.commit()
    
    service = ARAPService(db_session)
    ar_record = service.create_ar_record(sample_tenant.tenant_id, old_invoice.id)
    
    # Should be in 60-day bucket
    assert ar_record.aging_bucket == "60"
    assert ar_record.days_outstanding >= 60


# ============================================================================
# FINANCIAL AUDIT TRAIL TESTS
# ============================================================================

def test_log_financial_event(db_session, sample_tenant, sample_user):
    """Test financial event logging"""
    service = FinancialAuditService(db_session)
    
    previous_state = {"amount": "100.00", "status": "pending"}
    new_state = {"amount": "100.00", "status": "paid"}
    
    audit_log = service.log_financial_event(
        tenant_id=sample_tenant.tenant_id,
        event_type="invoice_paid",
        event_category="revenue",
        entity_type="invoice",
        entity_id=1,
        user_id=sample_user.user_id,
        previous_state=previous_state,
        new_state=new_state,
        ip_address="127.0.0.1"
    )
    
    assert audit_log.id is not None
    assert audit_log.record_hash is not None
    assert len(audit_log.record_hash) == 64  # SHA-256
    assert len(audit_log.changes) > 0


def test_audit_chain_integrity(db_session, sample_tenant, sample_user):
    """Test audit chain integrity verification"""
    service = FinancialAuditService(db_session)
    
    # Create multiple audit entries
    for i in range(5):
        service.log_financial_event(
            tenant_id=sample_tenant.tenant_id,
            event_type=f"event_{i}",
            event_category="revenue",
            entity_type="test",
            entity_id=i,
            user_id=sample_user.user_id,
            previous_state={"value": i},
            new_state={"value": i + 1}
        )
    
    # Verify chain
    verification = service.verify_audit_chain(sample_tenant.tenant_id)
    
    assert verification["chain_intact"] is True
    assert verification["total_records"] == 5
    assert verification["verified_records"] == 5
    assert len(verification["broken_links"]) == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_end_to_end_revenue_flow(db_session, sample_tenant, sample_user, sample_invoice):
    """Test complete revenue operations flow"""
    # 1. Calculate revenue metrics
    analytics_service = RevenueAnalyticsService(db_session)
    metric = analytics_service.save_revenue_metrics(
        sample_tenant.tenant_id,
        date.today() - timedelta(days=30),
        date.today()
    )
    assert metric.value > 0
    
    # 2. Predict customer LTV
    predictive_service = PredictiveAnalyticsService(db_session)
    ltv = predictive_service.calculate_customer_ltv(
        sample_tenant.tenant_id,
        sample_user.user_id
    )
    assert ltv.predicted_ltv > 0
    
    # 3. Predict churn
    churn = predictive_service.predict_churn(
        sample_tenant.tenant_id,
        sample_user.user_id
    )
    assert churn.churn_probability >= 0
    
    # 4. Create revenue recognition
    recognition_service = RevenueRecognitionService(db_session)
    recognition = recognition_service.create_recognition_schedule(
        sample_tenant.tenant_id,
        sample_invoice.id
    )
    assert recognition.deferred_revenue > 0
    
    # 5. Calculate tax
    tax_service = TaxComplianceService(db_session)
    tax = tax_service.calculate_tax_liability(
        sample_tenant.tenant_id,
        TaxJurisdiction.US_STATE,
        date.today() - timedelta(days=30),
        date.today()
    )
    assert tax.tax_amount > 0
    
    # 6. Create AR record
    ar_service = ARAPService(db_session)
    ar = ar_service.create_ar_record(sample_tenant.tenant_id, sample_invoice.id)
    assert ar.invoice_amount > 0
    
    # 7. Log audit event
    audit_service = FinancialAuditService(db_session)
    audit = audit_service.log_financial_event(
        tenant_id=sample_tenant.tenant_id,
        event_type="revenue_recognized",
        event_category="revenue",
        entity_type="invoice",
        entity_id=sample_invoice.id,
        user_id=sample_user.user_id,
        previous_state={},
        new_state={"recognized": True}
    )
    assert audit.record_hash is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
