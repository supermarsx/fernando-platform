# Enterprise Billing - Quick Start Guide

Get started with Enterprise Billing features in 10 minutes.

---

## Prerequisites

- Backend server running
- Database configured
- Admin user account
- API access token

---

## Step 1: Run Database Migration (2 minutes)

Create all enterprise billing tables:

```bash
cd /workspace/fernando/backend
python migrations/versions/007_add_enterprise_billing.py
```

**Expected Output:**
```
Creating enterprise billing tables...
Enterprise billing tables created successfully!

Created tables:
  - billing_entities (Multi-entity billing)
  - departments (Department management)
  - cost_allocations (Cost center allocations)
  ...
```

---

## Step 2: Initialize Sample Data (2 minutes)

Set up sample entities, departments, budgets, and contracts:

```bash
python initialize_enterprise_billing.py
```

**Expected Output:**
```
ENTERPRISE BILLING INITIALIZATION
================================================================================

1. Creating billing entities...
   ✓ Created root entity: Acme Corporation (ENT-XXXX)
   ✓ Created subsidiary: Acme USA (ENT-YYYY)
   ✓ Created subsidiary: Acme Europe (ENT-ZZZZ)

2. Creating departments...
   ✓ Created department: Engineering (CC-ENG-001)
   ✓ Created department: Sales (CC-SAL-001)
   ✓ Created department: Finance (CC-FIN-001)

3. Creating budgets...
   ✓ Created budget: Engineering Q1 2025 Budget ($50,000.00)
   ✓ Created budget: Sales Annual 2025 Budget ($150,000.00)

4. Creating billing contracts...
   ✓ Created contract: Acme Enterprise Agreement ($120,000.00)

5. Creating approval rules...
   ✓ Created rule: Purchase Approval - Tier 1
   ✓ Created rule: Purchase Approval - Tier 2
   ✓ Created rule: Budget Increase Approval

✅ Enterprise billing system initialized successfully!
```

---

## Step 3: Verify Installation (1 minute)

Check the dashboard summary:

```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/dashboard/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "budgets": {
    "total_count": 2,
    "total_allocated": 200000,
    "total_spent": 0,
    "utilization_percent": 0
  },
  "contracts": {
    "total_count": 1,
    "total_value": 120000
  },
  "approvals": {
    "pending_count": 0
  }
}
```

---

## Step 4: Try Key Features (5 minutes)

### A. Multi-Entity Billing

**List all entities:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/entities" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Get entity hierarchy:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/entities/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Generate consolidated invoice:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/entities/1/consolidated-invoice?period_start=2025-01-01T00:00:00&period_end=2025-01-31T23:59:59" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### B. Department Cost Allocation

**List departments:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/departments" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Allocate cost to department:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/departments/1/allocations" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "department_id": 1,
    "allocation_type": "subscription",
    "amount": 5000,
    "period_start": "2025-01-01T00:00:00",
    "period_end": "2025-01-31T23:59:59",
    "description": "Monthly subscription allocation",
    "gl_code": "6000-100"
  }'
```

**Get department costs:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/departments/1/costs?period_start=2025-01-01T00:00:00&period_end=2025-01-31T23:59:59" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### C. Budget Management

**List budgets:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/budgets" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Check budget availability:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/budgets/1/check-availability?amount=10000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "available": true,
  "overspend": false,
  "available_amount": 50000,
  "requires_approval": false
}
```

**Charge budget:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/budgets/1/charge?amount=10000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### D. Approval Workflow

**Create approval request:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/approvals" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_type": "purchase",
    "title": "New Software Licenses",
    "description": "Purchase 50 enterprise licenses",
    "amount": 15000,
    "budget_id": 1
  }'
```

**List pending approvals:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/approvals?status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Approve request:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/approvals/1/action" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approved",
    "comments": "Approved based on budget availability"
  }'
```

### E. Contract Management

**List contracts:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/contracts" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Check contract renewal:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/contracts/1/renewal-check" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### F. Dispute Management

**Create dispute:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/disputes" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Incorrect Invoice Amount",
    "description": "Invoice #12345 shows incorrect usage charges",
    "category": "billing_error",
    "disputed_amount": 500,
    "invoice_id": 1
  }'
```

**Add comment to dispute:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/disputes/1/comments" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Investigating the usage data for this period",
    "is_internal": false
  }'
```

**Resolve dispute:**
```bash
curl -X PUT "http://localhost:8000/api/enterprise-billing/disputes/1/resolve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resolution": "Verified usage data error. Issuing credit.",
    "resolution_type": "credit",
    "credit_amount": 500
  }'
```

### G. Enterprise Reporting

**Generate financial report:**
```bash
curl -X POST "http://localhost:8000/api/enterprise-billing/reports" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_name": "Q1 2025 Financial Report",
    "report_type": "financial",
    "period_start": "2025-01-01T00:00:00",
    "period_end": "2025-03-31T23:59:59",
    "entity_id": 1
  }'
```

**List reports:**
```bash
curl -X GET "http://localhost:8000/api/enterprise-billing/reports" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Common Workflows

### Workflow 1: Department Budget Tracking

1. Create department budget
2. Check budget availability before spending
3. Charge budget after purchase
4. Monitor budget alerts
5. Generate budget variance report

### Workflow 2: Multi-Entity Consolidated Billing

1. Create parent entity
2. Create child entities
3. Link subscriptions to entities
4. Allocate costs to departments
5. Generate consolidated invoice
6. Export to accounting system

### Workflow 3: Purchase Approval Flow

1. Check budget availability
2. Create approval request
3. Budget amount committed
4. Approvers notified
5. Approval action taken
6. Budget charged or released

### Workflow 4: Contract Lifecycle

1. Create contract in draft status
2. Add contract terms and SLA
3. Get signatures and activate
4. Monitor for renewal
5. Create amendment if needed
6. Renew or terminate

### Workflow 5: Dispute Resolution

1. Customer creates dispute
2. Support adds investigation comments
3. Internal notes for tracking
4. Determine resolution type
5. Apply credit or refund
6. Close dispute with resolution

---

## Configuration Options

### Budget Settings

```python
# Allow overspend with limit
budget = {
    "allow_overspend": True,
    "overspend_limit_percent": 10,  # Max 10% over
    "require_approval_above": 10000  # Approve if charge > $10k
}

# Alert thresholds
alerts = {
    "alert_threshold_percent": 75,    # Alert at 75%
    "warning_threshold_percent": 90   # Warning at 90%
}
```

### Approval Rules

```python
# Tiered approval based on amount
rule = {
    "min_amount": 5000,
    "max_amount": 25000,
    "required_approval_count": 1,
    "approval_sequence": False,  # Parallel
    "escalation_hours": 24
}
```

### Contract Terms

```python
contract = {
    "term_length_months": 12,
    "auto_renew": True,
    "renewal_notice_days": 30,
    "payment_terms_days": 30,
    "discount_percent": 15
}
```

---

## Troubleshooting

### Issue: Tables not created

**Solution:**
```bash
# Check database connection
python -c "from app.db.session import engine; print(engine.url)"

# Run migration again
python migrations/versions/007_add_enterprise_billing.py
```

### Issue: Authorization errors

**Solution:**
```bash
# Verify token is valid
# Use admin token for admin endpoints
# Check user permissions
```

### Issue: Budget calculations incorrect

**Solution:**
```bash
# Check budget period dates
# Verify spent_amount and committed_amount
# Review cost allocations for period
```

### Issue: Approval rules not matching

**Solution:**
```bash
# Check rule priority order
# Verify amount ranges
# Check request_type filter
# Ensure rules are active
```

---

## Best Practices

### 1. Entity Structure

- Create clear hierarchy (Root → Subsidiary → Division → Department)
- Use consolidated billing for parent entities
- Set currency per entity
- Configure payment terms per entity

### 2. Budget Management

- Create budgets before spending
- Set realistic alert thresholds
- Use budget rollover for unused amounts
- Review budget alerts regularly

### 3. Approval Workflows

- Define clear approval rules by amount
- Use sequential approvals for high-value items
- Set appropriate escalation timeframes
- Document approval rationale in comments

### 4. Cost Allocation

- Allocate costs as they occur
- Use consistent GL code structure
- Map to external accounting system
- Generate allocation reports monthly

### 5. Contract Management

- Review contracts before expiration
- Document amendments properly
- Track SLA compliance
- Automate renewal reminders

---

## Next Steps

1. **Customize Configuration:**
   - Adjust budget thresholds
   - Configure approval rules
   - Set up GL code mappings

2. **Integrate Systems:**
   - Connect QuickBooks/Xero
   - Set up sync schedules
   - Test data mappings

3. **Train Users:**
   - Department managers on budgets
   - Approvers on workflow
   - Finance team on reporting

4. **Monitor Performance:**
   - Track budget utilization
   - Monitor approval SLAs
   - Review dispute metrics
   - Generate regular reports

---

## API Reference

Full API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **Tag:** `enterprise-billing`
- **Base Path:** `/api/enterprise-billing`

---

## Support

For additional help:
- Review implementation docs: `ENTERPRISE_BILLING_IMPLEMENTATION.md`
- Check API docs: `/docs`
- Review sample code: `initialize_enterprise_billing.py`

---

**Quick Start Version:** 1.0.0  
**Last Updated:** 2025-11-06  
**Time to Complete:** 10 minutes
