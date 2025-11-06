"""
Comprehensive Test Suite for Enterprise Billing Features

Tests all major workflows including:
- Multi-entity billing and consolidated invoicing
- Department cost allocation
- Budget enforcement and alerts
- Approval workflows
- Contract management
- Dispute resolution
- Financial integration
- Enterprise reporting
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.services.enterprise_billing_service import EnterpriseBillingService
from app.models.enterprise_billing import (
    EntityType, CostCenterType, ContractType, BudgetPeriod,
    DisputeCategory, DisputeStatus, ApprovalStatus
)
from app.models.billing import Subscription, Invoice
from app.models.user import User
import requests
import json


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"   ✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"   ✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 80)
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print("=" * 80)


def test_enterprise_billing_service():
    """Test the service layer directly"""
    print("\n" + "=" * 80)
    print("ENTERPRISE BILLING SERVICE TESTS")
    print("=" * 80)
    
    db = SessionLocal()
    service = EnterpriseBillingService(db)
    results = TestResult()
    
    try:
        # Get or create test user
        user = db.query(User).first()
        if not user:
            print("⚠️  No users found. Skipping service tests.")
            return
        
        tenant_id = user.tenant_id if hasattr(user, 'tenant_id') else "default"
        
        # Test 1: Multi-Entity Management
        print("\n1. Multi-Entity Management Tests")
        try:
            # Create root entity
            root = service.create_billing_entity(
                name="Test Corp",
                tenant_id=tenant_id,
                entity_type=EntityType.ROOT,
                consolidated_billing=True
            )
            assert root.id is not None
            assert root.entity_type == EntityType.ROOT
            results.add_pass("Create root entity")
            
            # Create subsidiary
            subsidiary = service.create_billing_entity(
                name="Test Subsidiary",
                tenant_id=tenant_id,
                entity_type=EntityType.SUBSIDIARY,
                parent_entity_id=root.id
            )
            assert subsidiary.parent_entity_id == root.id
            results.add_pass("Create subsidiary entity")
            
            # Get hierarchy
            hierarchy = service.get_entity_hierarchy(root.id)
            assert hierarchy is not None
            assert len(hierarchy['children']) > 0
            results.add_pass("Get entity hierarchy")
            
        except Exception as e:
            results.add_fail("Multi-entity management", str(e))
        
        # Test 2: Department Management
        print("\n2. Department Management Tests")
        try:
            # Create department
            dept = service.create_department(
                name="Test Engineering",
                entity_id=root.id,
                department_code="TEST-ENG-001",
                cost_center_code="CC-TEST-001",
                cost_center_type=CostCenterType.OPERATIONAL
            )
            assert dept.id is not None
            assert dept.cost_center_code == "CC-TEST-001"
            results.add_pass("Create department")
            
            # Allocate cost
            allocation = service.allocate_cost(
                department_id=dept.id,
                allocation_type="subscription",
                amount=1000.0,
                period_start=datetime.now(),
                period_end=datetime.now() + timedelta(days=30),
                description="Test allocation"
            )
            assert allocation.amount == 1000.0
            results.add_pass("Allocate cost to department")
            
            # Get department costs
            costs = service.get_department_costs(
                dept.id,
                datetime.now() - timedelta(days=1),
                datetime.now() + timedelta(days=31)
            )
            assert costs['total_cost'] == 1000.0
            results.add_pass("Get department costs")
            
        except Exception as e:
            results.add_fail("Department management", str(e))
        
        # Test 3: Budget Management
        print("\n3. Budget Management Tests")
        try:
            # Create budget
            budget = service.create_budget(
                name="Test Budget",
                allocated_amount=10000.0,
                period_start=datetime.now(),
                period_end=datetime.now() + timedelta(days=90),
                department_id=dept.id,
                allow_overspend=True,
                overspend_limit_percent=10
            )
            assert budget.allocated_amount == 10000.0
            results.add_pass("Create budget")
            
            # Check availability
            availability = service.check_budget_availability(budget.id, 5000.0)
            assert availability['available'] == True
            results.add_pass("Check budget availability - sufficient funds")
            
            # Commit budget
            service.commit_budget_amount(budget.id, 5000.0)
            db.refresh(budget)
            assert budget.committed_amount == 5000.0
            results.add_pass("Commit budget amount")
            
            # Charge budget
            service.charge_budget(budget.id, 3000.0, release_commitment=True)
            db.refresh(budget)
            assert budget.spent_amount == 3000.0
            results.add_pass("Charge budget")
            
            # Check availability after spending
            availability = service.check_budget_availability(budget.id, 8000.0)
            assert availability['available'] == False
            results.add_pass("Check budget availability - insufficient funds")
            
            # Test overspend with allowance
            availability = service.check_budget_availability(budget.id, 7500.0)
            # Should allow with overspend since limit is 10%
            assert availability['available'] == True
            assert availability['overspend'] == True
            results.add_pass("Check budget with overspend allowance")
            
        except Exception as e:
            results.add_fail("Budget management", str(e))
        
        # Test 4: Contract Management
        print("\n4. Contract Management Tests")
        try:
            # Create contract
            contract = service.create_contract(
                name="Test Enterprise Contract",
                entity_id=root.id,
                contract_type=ContractType.ENTERPRISE,
                start_date=datetime.now(),
                term_length_months=12,
                contract_value=50000.0,
                created_by_user_id=user.user_id,
                auto_renew=True
            )
            assert contract.contract_value == 50000.0
            results.add_pass("Create contract")
            
            # Add amendment
            amendment = service.add_contract_amendment(
                contract_id=contract.id,
                description="Price adjustment",
                amendment_type="pricing",
                old_values={"contract_value": 50000.0},
                new_values={"contract_value": 55000.0},
                effective_date=datetime.now() + timedelta(days=30),
                created_by_user_id=user.user_id
            )
            assert amendment.amendment_type == "pricing"
            results.add_pass("Add contract amendment")
            
            # Check renewal
            renewal_info = service.check_contract_renewal(contract.id)
            assert renewal_info is not None
            assert 'needs_renewal' in renewal_info
            results.add_pass("Check contract renewal")
            
        except Exception as e:
            results.add_fail("Contract management", str(e))
        
        # Test 5: Approval Workflow
        print("\n5. Approval Workflow Tests")
        try:
            # Create approval request
            approval_request = service.create_approval_request(
                request_type="purchase",
                title="Test Purchase",
                amount=7500.0,
                requested_by_user_id=user.user_id,
                budget_id=budget.id,
                description="Test approval workflow"
            )
            assert approval_request.status == ApprovalStatus.PENDING
            results.add_pass("Create approval request")
            
            # Verify budget was committed
            db.refresh(budget)
            assert budget.committed_amount >= 7500.0
            results.add_pass("Budget committed during approval")
            
            # Approve request
            approved = service.approve_request(
                request_id=approval_request.id,
                approver_user_id=user.user_id,
                comments="Test approval"
            )
            assert approved.status == ApprovalStatus.APPROVED
            results.add_pass("Approve request")
            
            # Verify budget was charged
            db.refresh(budget)
            assert budget.spent_amount >= 7500.0
            results.add_pass("Budget charged after approval")
            
            # Test rejection
            approval_request2 = service.create_approval_request(
                request_type="purchase",
                title="Test Rejection",
                amount=1000.0,
                requested_by_user_id=user.user_id,
                budget_id=budget.id
            )
            rejected = service.reject_request(
                request_id=approval_request2.id,
                approver_user_id=user.user_id,
                reason="Test rejection",
                comments="Testing rejection workflow"
            )
            assert rejected.status == ApprovalStatus.REJECTED
            results.add_pass("Reject request")
            
        except Exception as e:
            results.add_fail("Approval workflow", str(e))
        
        # Test 6: Dispute Management
        print("\n6. Dispute Management Tests")
        try:
            # Create dispute
            dispute = service.create_dispute(
                title="Test Dispute",
                description="Testing dispute management",
                category=DisputeCategory.BILLING_ERROR,
                disputed_amount=500.0,
                raised_by_user_id=user.user_id
            )
            assert dispute.status == DisputeStatus.OPEN
            results.add_pass("Create dispute")
            
            # Add comment
            comment = service.add_dispute_comment(
                dispute_id=dispute.id,
                author_user_id=user.user_id,
                comment="Investigating the issue",
                is_internal=False
            )
            assert comment.comment == "Investigating the issue"
            results.add_pass("Add dispute comment")
            
            # Resolve dispute
            resolved = service.resolve_dispute(
                dispute_id=dispute.id,
                resolution="Verified error, issuing credit",
                resolution_type="credit",
                credit_amount=500.0
            )
            assert resolved.status == DisputeStatus.RESOLVED
            assert resolved.credit_amount == 500.0
            results.add_pass("Resolve dispute")
            
        except Exception as e:
            results.add_fail("Dispute management", str(e))
        
        # Test 7: Financial Integration
        print("\n7. Financial Integration Tests")
        try:
            # Create integration
            integration = service.create_financial_integration(
                name="Test QuickBooks Integration",
                provider="quickbooks",
                entity_id=root.id,
                api_endpoint="https://api.quickbooks.com",
                credentials="encrypted_test_credentials"
            )
            assert integration.provider == "quickbooks"
            results.add_pass("Create financial integration")
            
            # Sync to financial system
            sync_log = service.sync_to_financial_system(
                integration_id=integration.id,
                sync_type="invoice"
            )
            assert sync_log.status in ["completed", "started"]
            results.add_pass("Sync to financial system")
            
        except Exception as e:
            results.add_fail("Financial integration", str(e))
        
        # Test 8: Enterprise Reporting
        print("\n8. Enterprise Reporting Tests")
        try:
            # Generate financial report
            report = service.generate_enterprise_report(
                report_name="Test Financial Report",
                report_type="financial",
                period_start=datetime.now() - timedelta(days=30),
                period_end=datetime.now(),
                generated_by_user_id=user.user_id,
                entity_id=root.id
            )
            assert report.status == "completed"
            assert report.report_data is not None
            results.add_pass("Generate financial report")
            
            # Generate budget report
            budget_report = service.generate_enterprise_report(
                report_name="Test Budget Report",
                report_type="budget",
                period_start=datetime.now() - timedelta(days=30),
                period_end=datetime.now() + timedelta(days=60),
                generated_by_user_id=user.user_id,
                entity_id=root.id
            )
            assert budget_report.status == "completed"
            results.add_pass("Generate budget report")
            
        except Exception as e:
            results.add_fail("Enterprise reporting", str(e))
        
        db.commit()
        
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
    
    results.summary()
    return results


def test_api_endpoints():
    """Test API endpoints via HTTP"""
    print("\n" + "=" * 80)
    print("API ENDPOINT TESTS")
    print("=" * 80)
    
    BASE_URL = "http://localhost:8000"
    results = TestResult()
    
    # First, register a test user and get token
    print("\n0. Authentication Setup")
    try:
        register_data = {
            "email": f"test_enterprise_{int(datetime.now().timestamp())}@example.com",
            "password": "TestPassword123!",
            "full_name": "Enterprise Test User",
            "company_name": "Fernando"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)
        if response.status_code == 200:
            token = response.json().get('access_token')
            headers = {"Authorization": f"Bearer {token}"}
            results.add_pass("User registration and authentication")
        else:
            print(f"   ⚠️  Could not register user: {response.text}")
            print("   Skipping API tests - backend may not be running")
            return
    except Exception as e:
        print(f"   ⚠️  Could not connect to backend: {str(e)}")
        print("   Skipping API tests - backend may not be running")
        return
    
    # Test dashboard summary (doesn't require data)
    print("\n1. Dashboard & Analytics Tests")
    try:
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/dashboard/summary",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert 'budgets' in data
        assert 'contracts' in data
        assert 'approvals' in data
        results.add_pass("GET /dashboard/summary")
    except Exception as e:
        results.add_fail("Dashboard summary", str(e))
    
    # Test entity endpoints
    print("\n2. Entity Management API Tests")
    try:
        # Create entity
        entity_data = {
            "name": "API Test Corporation",
            "entity_type": "root",
            "consolidated_billing": True,
            "currency": "USD",
            "payment_terms_days": 30
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/entities",
            json=entity_data,
            headers=headers
        )
        assert response.status_code == 200
        entity_id = response.json()['id']
        results.add_pass("POST /entities (create)")
        
        # List entities
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/entities",
            headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        results.add_pass("GET /entities (list)")
        
        # Get entity hierarchy
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/entities/{entity_id}",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /entities/{id} (hierarchy)")
        
    except Exception as e:
        results.add_fail("Entity API", str(e))
    
    # Test department endpoints
    print("\n3. Department Management API Tests")
    try:
        # Create department
        dept_data = {
            "name": "API Test Engineering",
            "department_code": "API-ENG-001",
            "cost_center_code": "CC-API-001",
            "entity_id": entity_id,
            "cost_center_type": "operational"
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/departments",
            json=dept_data,
            headers=headers
        )
        assert response.status_code == 200
        dept_id = response.json()['id']
        results.add_pass("POST /departments (create)")
        
        # List departments
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/departments",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /departments (list)")
        
    except Exception as e:
        results.add_fail("Department API", str(e))
    
    # Test budget endpoints
    print("\n4. Budget Management API Tests")
    try:
        # Create budget
        budget_data = {
            "name": "API Test Budget",
            "allocated_amount": 50000.0,
            "period_start": datetime.now().isoformat(),
            "period_end": (datetime.now() + timedelta(days=90)).isoformat(),
            "department_id": dept_id,
            "allow_overspend": True,
            "alert_threshold_percent": 80
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/budgets",
            json=budget_data,
            headers=headers
        )
        assert response.status_code == 200
        budget_id = response.json()['id']
        results.add_pass("POST /budgets (create)")
        
        # List budgets
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/budgets",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /budgets (list)")
        
        # Check availability
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/budgets/{budget_id}/check-availability?amount=10000",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()['available'] == True
        results.add_pass("POST /budgets/{id}/check-availability")
        
    except Exception as e:
        results.add_fail("Budget API", str(e))
    
    # Test contract endpoints
    print("\n5. Contract Management API Tests")
    try:
        # Create contract
        contract_data = {
            "name": "API Test Contract",
            "entity_id": entity_id,
            "contract_type": "enterprise",
            "start_date": datetime.now().isoformat(),
            "term_length_months": 12,
            "contract_value": 120000.0,
            "auto_renew": True,
            "payment_terms_days": 30
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/contracts",
            json=contract_data,
            headers=headers
        )
        assert response.status_code == 200
        contract_id = response.json()['id']
        results.add_pass("POST /contracts (create)")
        
        # List contracts
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/contracts",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /contracts (list)")
        
        # Check renewal
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/contracts/{contract_id}/renewal-check",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /contracts/{id}/renewal-check")
        
    except Exception as e:
        results.add_fail("Contract API", str(e))
    
    # Test approval endpoints
    print("\n6. Approval Workflow API Tests")
    try:
        # Create approval request
        approval_data = {
            "request_type": "purchase",
            "title": "API Test Purchase",
            "description": "Testing approval workflow via API",
            "amount": 15000.0,
            "budget_id": budget_id
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/approvals",
            json=approval_data,
            headers=headers
        )
        assert response.status_code == 200
        approval_id = response.json()['id']
        results.add_pass("POST /approvals (create)")
        
        # List approvals
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/approvals",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /approvals (list)")
        
    except Exception as e:
        results.add_fail("Approval API", str(e))
    
    # Test dispute endpoints
    print("\n7. Dispute Management API Tests")
    try:
        # Create dispute
        dispute_data = {
            "title": "API Test Dispute",
            "description": "Testing dispute management via API",
            "category": "billing_error",
            "disputed_amount": 1000.0
        }
        response = requests.post(
            f"{BASE_URL}/api/enterprise-billing/disputes",
            json=dispute_data,
            headers=headers
        )
        assert response.status_code == 200
        dispute_id = response.json()['id']
        results.add_pass("POST /disputes (create)")
        
        # List disputes
        response = requests.get(
            f"{BASE_URL}/api/enterprise-billing/disputes",
            headers=headers
        )
        assert response.status_code == 200
        results.add_pass("GET /disputes (list)")
        
    except Exception as e:
        results.add_fail("Dispute API", str(e))
    
    results.summary()
    return results


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ENTERPRISE BILLING COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run service tests
    service_results = test_enterprise_billing_service()
    
    # Run API tests
    api_results = test_api_endpoints()
    
    # Overall summary
    total_passed = service_results.passed + api_results.passed
    total_failed = service_results.failed + api_results.failed
    total_tests = total_passed + total_failed
    
    print("\n" + "=" * 80)
    print("OVERALL TEST RESULTS")
    print("=" * 80)
    print(f"Service Tests: {service_results.passed}/{service_results.passed + service_results.failed} passed")
    print(f"API Tests: {api_results.passed}/{api_results.passed + api_results.failed} passed")
    print(f"\nTotal: {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
    
    if total_failed == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")
    
    print("=" * 80)
