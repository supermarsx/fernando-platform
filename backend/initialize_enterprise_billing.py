"""
Initialize Enterprise Billing System

This script sets up:
- Sample billing entities for testing
- Default departments and cost centers
- Sample budgets
- Default approval rules
- Sample contracts
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.services.enterprise_billing_service import EnterpriseBillingService
from app.models.enterprise_billing import EntityType, CostCenterType, ContractType, BudgetPeriod
from app.models.billing import Subscription
from app.models.user import User


def initialize_enterprise_billing():
    """Initialize enterprise billing with sample data"""
    db = SessionLocal()
    service = EnterpriseBillingService(db)
    
    print("=" * 80)
    print("ENTERPRISE BILLING INITIALIZATION")
    print("=" * 80)
    
    try:
        # Get first user for testing
        user = db.query(User).first()
        if not user:
            print("⚠️  No users found. Please create a user first.")
            return
        
        tenant_id = user.tenant_id if hasattr(user, 'tenant_id') else "default"
        
        # 1. Create Root Entity
        print("\n1. Creating billing entities...")
        root_entity = service.create_billing_entity(
            name="Acme Corporation",
            legal_name="Acme Corporation Ltd.",
            tenant_id=tenant_id,
            entity_type=EntityType.ROOT,
            tax_id="US123456789",
            billing_address={
                "street": "123 Business Ave",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001"
            },
            consolidated_billing=True,
            currency="USD",
            payment_terms_days=30
        )
        print(f"   ✓ Created root entity: {root_entity.name} ({root_entity.entity_id})")
        
        # Create subsidiaries
        us_entity = service.create_billing_entity(
            name="Acme USA",
            legal_name="Acme Corporation USA Inc.",
            tenant_id=tenant_id,
            entity_type=EntityType.SUBSIDIARY,
            parent_entity_id=root_entity.id,
            tax_id="US987654321",
            consolidated_billing=False,
            currency="USD"
        )
        print(f"   ✓ Created subsidiary: {us_entity.name} ({us_entity.entity_id})")
        
        eu_entity = service.create_billing_entity(
            name="Acme Europe",
            legal_name="Acme Corporation Europe GmbH",
            tenant_id=tenant_id,
            entity_type=EntityType.SUBSIDIARY,
            parent_entity_id=root_entity.id,
            tax_id="EU123456789",
            consolidated_billing=False,
            currency="EUR"
        )
        print(f"   ✓ Created subsidiary: {eu_entity.name} ({eu_entity.entity_id})")
        
        # 2. Create Departments
        print("\n2. Creating departments...")
        
        # Engineering department
        engineering = service.create_department(
            name="Engineering",
            entity_id=us_entity.id,
            department_code="ENG-001",
            cost_center_code="CC-ENG-001",
            cost_center_type=CostCenterType.OPERATIONAL,
            description="Software Engineering Department",
            default_gl_code="6000-100"
        )
        print(f"   ✓ Created department: {engineering.name} ({engineering.cost_center_code})")
        
        # Sales department
        sales = service.create_department(
            name="Sales",
            entity_id=us_entity.id,
            department_code="SAL-001",
            cost_center_code="CC-SAL-001",
            cost_center_type=CostCenterType.REVENUE,
            description="Sales Department",
            default_gl_code="4000-100"
        )
        print(f"   ✓ Created department: {sales.name} ({sales.cost_center_code})")
        
        # Finance department
        finance = service.create_department(
            name="Finance",
            entity_id=us_entity.id,
            department_code="FIN-001",
            cost_center_code="CC-FIN-001",
            cost_center_type=CostCenterType.OPERATIONAL,
            description="Finance & Accounting Department",
            default_gl_code="6100-100"
        )
        print(f"   ✓ Created department: {finance.name} ({finance.cost_center_code})")
        
        # 3. Create Budgets
        print("\n3. Creating budgets...")
        
        # Q1 Budget for Engineering
        q1_start = datetime(datetime.now().year, 1, 1)
        q1_end = datetime(datetime.now().year, 3, 31)
        
        eng_budget = service.create_budget(
            name="Engineering Q1 2025 Budget",
            description="Quarterly budget for Engineering department",
            allocated_amount=50000.0,
            period_start=q1_start,
            period_end=q1_end,
            department_id=engineering.id,
            entity_id=us_entity.id,
            period_type=BudgetPeriod.QUARTERLY,
            allow_overspend=True,
            overspend_limit_percent=10,
            alert_threshold_percent=75,
            warning_threshold_percent=90,
            currency="USD"
        )
        print(f"   ✓ Created budget: {eng_budget.name} (${eng_budget.allocated_amount:,.2f})")
        
        # Annual Budget for Sales
        annual_start = datetime(datetime.now().year, 1, 1)
        annual_end = datetime(datetime.now().year, 12, 31)
        
        sales_budget = service.create_budget(
            name="Sales Annual 2025 Budget",
            description="Annual budget for Sales department",
            allocated_amount=150000.0,
            period_start=annual_start,
            period_end=annual_end,
            department_id=sales.id,
            entity_id=us_entity.id,
            period_type=BudgetPeriod.ANNUAL,
            allow_overspend=False,
            alert_threshold_percent=80,
            warning_threshold_percent=95,
            require_approval_above=10000.0,
            currency="USD"
        )
        print(f"   ✓ Created budget: {sales_budget.name} (${sales_budget.allocated_amount:,.2f})")
        
        # 4. Create Contracts
        print("\n4. Creating billing contracts...")
        
        contract_start = datetime.now()
        
        enterprise_contract = service.create_contract(
            name="Acme Enterprise Agreement",
            entity_id=root_entity.id,
            contract_type=ContractType.ENTERPRISE,
            start_date=contract_start,
            term_length_months=12,
            contract_value=120000.0,
            created_by_user_id=user.user_id,
            discount_percent=15,
            auto_renew=True,
            payment_terms_days=30,
            sla_terms={
                "uptime_guarantee": 99.9,
                "support_response_time": "4 hours",
                "dedicated_account_manager": True
            },
            minimum_commitment=100000.0,
            support_level="enterprise"
        )
        print(f"   ✓ Created contract: {enterprise_contract.name} (${enterprise_contract.contract_value:,.2f})")
        print(f"      Contract ID: {enterprise_contract.contract_number}")
        print(f"      Term: {enterprise_contract.term_length_months} months")
        print(f"      Discount: {enterprise_contract.discount_percent}%")
        
        # 5. Create Approval Rules
        print("\n5. Creating approval rules...")
        
        from app.models.enterprise_billing import ApprovalRule
        
        # Rule 1: Purchases over $5,000 require approval
        rule1 = ApprovalRule(
            rule_name="Purchase Approval - Tier 1",
            description="All purchases over $5,000 require manager approval",
            entity_id=us_entity.id,
            request_type="purchase",
            min_amount=5000,
            max_amount=25000,
            required_approval_count=1,
            approval_sequence=False,
            escalation_hours=24,
            is_active=True,
            priority=1
        )
        db.add(rule1)
        print(f"   ✓ Created rule: {rule1.rule_name}")
        print(f"      Amount range: ${rule1.min_amount:,.2f} - ${rule1.max_amount:,.2f}")
        
        # Rule 2: Purchases over $25,000 require senior approval
        rule2 = ApprovalRule(
            rule_name="Purchase Approval - Tier 2",
            description="Purchases over $25,000 require senior management approval",
            entity_id=us_entity.id,
            request_type="purchase",
            min_amount=25000,
            required_approval_count=2,
            approval_sequence=True,
            escalation_hours=12,
            is_active=True,
            priority=2
        )
        db.add(rule2)
        print(f"   ✓ Created rule: {rule2.rule_name}")
        print(f"      Amount range: ${rule2.min_amount:,.2f}+")
        print(f"      Sequential approvals: {rule2.required_approval_count}")
        
        # Rule 3: Budget increase requests
        rule3 = ApprovalRule(
            rule_name="Budget Increase Approval",
            description="All budget increase requests require CFO approval",
            request_type="budget_increase",
            min_amount=0,
            required_approval_count=1,
            approval_sequence=False,
            escalation_hours=48,
            is_active=True,
            priority=1
        )
        db.add(rule3)
        print(f"   ✓ Created rule: {rule3.rule_name}")
        
        # 6. Create GL Code Mappings
        print("\n6. Creating GL code mappings...")
        
        from app.models.enterprise_billing import GLCodeMapping
        
        gl_mappings = [
            {
                "internal_gl_code": "4000-100",
                "external_gl_code": "4000",
                "account_name": "Software License Revenue",
                "account_type": "revenue",
                "category": "subscription_revenue"
            },
            {
                "internal_gl_code": "6000-100",
                "external_gl_code": "6000",
                "account_name": "Software Expenses",
                "account_type": "expense",
                "category": "subscription_expense"
            },
            {
                "internal_gl_code": "6100-100",
                "external_gl_code": "6100",
                "account_name": "Administrative Expenses",
                "account_type": "expense",
                "category": "operational_expense"
            }
        ]
        
        for mapping_data in gl_mappings:
            gl_mapping = GLCodeMapping(
                entity_id=us_entity.id,
                **mapping_data,
                is_active=True
            )
            db.add(gl_mapping)
            print(f"   ✓ Created GL mapping: {mapping_data['internal_gl_code']} → {mapping_data['external_gl_code']}")
        
        db.commit()
        
        print("\n" + "=" * 80)
        print("INITIALIZATION COMPLETE")
        print("=" * 80)
        print("\n✅ Enterprise billing system initialized successfully!")
        print("\nCreated resources:")
        print(f"  • Billing Entities: 3 (1 root, 2 subsidiaries)")
        print(f"  • Departments: 3 (Engineering, Sales, Finance)")
        print(f"  • Budgets: 2 (Q1 Engineering, Annual Sales)")
        print(f"  • Contracts: 1 (Enterprise Agreement)")
        print(f"  • Approval Rules: 3")
        print(f"  • GL Code Mappings: 3")
        
        print("\nNext steps:")
        print("  1. Review the created entities and departments")
        print("  2. Allocate costs to departments using the cost allocation API")
        print("  3. Create approval requests for testing workflows")
        print("  4. Set up financial integrations for QuickBooks/Xero/SAP")
        print("  5. Generate enterprise reports for CFO dashboard")
        
        print("\nAPI Endpoints:")
        print("  • GET /api/enterprise-billing/entities - List all entities")
        print("  • GET /api/enterprise-billing/departments - List all departments")
        print("  • GET /api/enterprise-billing/budgets - List all budgets")
        print("  • GET /api/enterprise-billing/contracts - List all contracts")
        print("  • GET /api/enterprise-billing/dashboard/summary - Dashboard summary")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    initialize_enterprise_billing()
