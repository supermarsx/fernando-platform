# Billing System - Testing and Verification Checklist

## Pre-Deployment Checklist

### Database Setup
- [ ] Run database migration: `alembic upgrade head`
- [ ] Verify all 8 tables created successfully
- [ ] Confirm 3 subscription plans inserted
- [ ] Confirm 7 tax rates inserted
- [ ] Check all indexes created
- [ ] Verify foreign key constraints

### API Registration
- [ ] Billing router registered in main.py
- [ ] API endpoints accessible at `/api/v1/billing/*`
- [ ] Swagger documentation updated at `/docs`
- [ ] Authentication middleware working
- [ ] Admin role checks functioning

### Configuration
- [ ] CORS settings allow frontend origin
- [ ] Rate limiting configured appropriately
- [ ] Database connection pool sized correctly
- [ ] Environment variables set (if any)

## Functional Testing

### Subscription Plan Management

#### Test 1: List Subscription Plans
```bash
curl http://localhost:8000/api/v1/billing/plans
```
**Expected**: JSON array with 3 plans (Basic, Professional, Enterprise)

**Verify**:
- [ ] All 3 plans returned
- [ ] Correct pricing (29, 99, 299 EUR)
- [ ] Correct limits displayed
- [ ] Features properly formatted

#### Test 2: Get Single Plan
```bash
curl http://localhost:8000/api/v1/billing/plans/1
```
**Expected**: Single plan details

**Verify**:
- [ ] Plan details complete
- [ ] Linked to license tier
- [ ] Features JSON properly formatted

#### Test 3: Create Plan (Admin Only)
```bash
curl -X POST http://localhost:8000/api/v1/billing/plans \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Plan",
    "license_tier_id": 1,
    "monthly_price": 49.99,
    "max_documents_per_month": 500
  }'
```
**Expected**: New plan created

**Verify**:
- [ ] Plan created successfully
- [ ] Default values applied
- [ ] Returns complete plan object

### Subscription Management

#### Test 4: Create Subscription
```bash
curl -X POST http://localhost:8000/api/v1/billing/subscriptions \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1,
    "billing_cycle": "monthly",
    "auto_renew": true,
    "trial_enabled": true
  }'
```
**Expected**: New subscription created with trial status

**Verify**:
- [ ] Subscription ID generated (sub_xxx format)
- [ ] Status is "trialing"
- [ ] Trial period set to 14 days
- [ ] Current period dates calculated
- [ ] Next billing date set correctly
- [ ] Base amount equals plan price

#### Test 5: Get User Subscriptions
```bash
curl http://localhost:8000/api/v1/billing/subscriptions/my \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Array of user's subscriptions

**Verify**:
- [ ] All user subscriptions returned
- [ ] Sorted by creation date
- [ ] Complete subscription data

#### Test 6: Cancel Subscription
```bash
curl -X POST http://localhost:8000/api/v1/billing/subscriptions/1/cancel \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cancel_immediately": false,
    "reason": "Testing cancellation"
  }'
```
**Expected**: Subscription canceled at period end

**Verify**:
- [ ] auto_renew set to false
- [ ] end_date set to current_period_end
- [ ] canceled_at timestamp set
- [ ] Billing event logged

#### Test 7: Upgrade Subscription
```bash
curl -X POST http://localhost:8000/api/v1/billing/subscriptions/1/upgrade \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_plan_id": 2,
    "prorate": true
  }'
```
**Expected**: Subscription upgraded with proration

**Verify**:
- [ ] Plan changed to Professional
- [ ] Proration amount calculated
- [ ] Proration invoice created (if amount > 0)
- [ ] Billing event logged
- [ ] Base amount updated

### Usage Tracking

#### Test 8: Record Usage
```bash
curl -X POST http://localhost:8000/api/v1/billing/usage \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1,
    "resource_type": "document",
    "quantity": 1,
    "description": "Invoice processing",
    "reference_id": "doc_12345"
  }'
```
**Expected**: Usage recorded

**Verify**:
- [ ] Usage record created
- [ ] Subscription counter incremented
- [ ] Unit price set from plan
- [ ] Billing period dates set correctly

#### Test 9: Get Usage Summary
```bash
curl http://localhost:8000/api/v1/billing/subscriptions/1/usage \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Usage summary with overage calculations

**Verify**:
- [ ] Current usage displayed
- [ ] Overage calculated correctly
- [ ] Overage charges computed
- [ ] Breakdown by resource type

#### Test 10: Record Multiple Usage Types
```bash
# Record document usage
curl -X POST http://localhost:8000/api/v1/billing/usage \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"subscription_id": 1, "resource_type": "document", "quantity": 150}'

# Record API calls
curl -X POST http://localhost:8000/api/v1/billing/usage \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"subscription_id": 1, "resource_type": "api_call", "quantity": 1200}'

# Check combined usage
curl http://localhost:8000/api/v1/billing/subscriptions/1/usage \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Combined usage with overages for both types

**Verify**:
- [ ] Document overage: 50 documents
- [ ] API call overage: 200 calls
- [ ] Total overage charge calculated correctly
- [ ] Documents: 50 × 0.10 = 5 EUR
- [ ] API calls: 200 × 0.01 = 2 EUR
- [ ] Total: 7 EUR overage

### Invoice Management

#### Test 11: List User Invoices
```bash
curl http://localhost:8000/api/v1/billing/invoices/my \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Array of user's invoices

**Verify**:
- [ ] All invoices returned
- [ ] Sorted by creation date
- [ ] Contains line items
- [ ] Tax calculated correctly

#### Test 12: Get Invoice Details
```bash
curl http://localhost:8000/api/v1/billing/invoices/1 \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Complete invoice details

**Verify**:
- [ ] Invoice number format correct (INV-YYYYMM-XXXXX)
- [ ] Line items detailed
- [ ] Subtotal, tax, total calculated correctly
- [ ] Tax rate 23% (Portugal)
- [ ] Due date set appropriately

#### Test 13: Pay Invoice
```bash
curl -X POST http://localhost:8000/api/v1/billing/invoices/1/pay \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_method_id": 1
  }'
```
**Expected**: Payment processed, invoice marked as paid

**Verify**:
- [ ] Payment record created
- [ ] Payment ID generated (pay_xxx format)
- [ ] Payment status "succeeded"
- [ ] Invoice status changed to "paid"
- [ ] amount_paid equals total_amount
- [ ] amount_due equals 0
- [ ] paid_at timestamp set
- [ ] Billing event logged

### Payment Methods

#### Test 14: Add Payment Method
```bash
curl -X POST http://localhost:8000/api/v1/billing/payment-methods \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "credit_card",
    "is_default": true,
    "card_last4": "4242",
    "card_brand": "Visa",
    "card_exp_month": 12,
    "card_exp_year": 2026,
    "provider": "stripe",
    "provider_payment_method_id": "pm_test_123"
  }'
```
**Expected**: Payment method added

**Verify**:
- [ ] Method created
- [ ] Set as default
- [ ] Only last 4 digits stored
- [ ] Verified flag set appropriately

#### Test 15: List Payment Methods
```bash
curl http://localhost:8000/api/v1/billing/payment-methods \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: Array of payment methods

**Verify**:
- [ ] All active methods returned
- [ ] Default method listed first
- [ ] Sensitive data masked

### Analytics (Admin Only)

#### Test 16: Get Billing Analytics
```bash
curl http://localhost:8000/api/v1/billing/analytics/billing \
  -H "Authorization: Bearer ADMIN_TOKEN"
```
**Expected**: Comprehensive billing metrics

**Verify**:
- [ ] MRR calculated correctly
- [ ] ARR equals MRR × 12
- [ ] Active subscription count accurate
- [ ] Churn rate calculated
- [ ] ARPU computed
- [ ] Outstanding amount summed

#### Test 17: Get Billing Dashboard
```bash
curl http://localhost:8000/api/v1/billing/analytics/dashboard \
  -H "Authorization: Bearer ADMIN_TOKEN"
```
**Expected**: Complete dashboard data

**Verify**:
- [ ] Billing analytics included
- [ ] Usage analytics included
- [ ] Revenue by month (12 months)
- [ ] Subscription trends
- [ ] All data formatted correctly

### Admin Operations

#### Test 18: List All Subscriptions (Admin)
```bash
curl "http://localhost:8000/api/v1/billing/admin/subscriptions?status=active&limit=50" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```
**Expected**: Paginated list of all subscriptions

**Verify**:
- [ ] Returns subscriptions across all users
- [ ] Filtering by status works
- [ ] Pagination parameters respected
- [ ] Requires admin authentication

#### Test 19: List All Invoices (Admin)
```bash
curl "http://localhost:8000/api/v1/billing/admin/invoices?status=pending&limit=50" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```
**Expected**: Paginated list of all invoices

**Verify**:
- [ ] Returns invoices across all users
- [ ] Filtering by status works
- [ ] Pagination parameters respected
- [ ] Requires admin authentication

## Edge Cases and Error Handling

### Test 20: Invalid Plan ID
```bash
curl -X POST http://localhost:8000/api/v1/billing/subscriptions \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"plan_id": 9999, "billing_cycle": "monthly"}'
```
**Expected**: 400 Bad Request with error message

### Test 21: Duplicate Subscription
```bash
# Create subscription
curl -X POST http://localhost:8000/api/v1/billing/subscriptions \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"plan_id": 1, "billing_cycle": "monthly"}'

# Try to create another active subscription (if business rule prevents it)
```
**Expected**: Handle according to business rules

### Test 22: Cancel Already Canceled
```bash
curl -X POST http://localhost:8000/api/v1/billing/subscriptions/1/cancel \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"cancel_immediately": true}'
```
**Expected**: 400 Bad Request - "Subscription already canceled"

### Test 23: Unauthorized Access
```bash
# User A tries to access User B's subscription
curl http://localhost:8000/api/v1/billing/subscriptions/2 \
  -H "Authorization: Bearer USER_A_TOKEN"
```
**Expected**: 404 Not Found (security through obscurity)

### Test 24: Pay Already Paid Invoice
```bash
curl -X POST http://localhost:8000/api/v1/billing/invoices/1/pay \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: 400 Bad Request - "Invoice already paid"

### Test 25: Record Usage for Invalid Subscription
```bash
curl -X POST http://localhost:8000/api/v1/billing/usage \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"subscription_id": 9999, "resource_type": "document", "quantity": 1}'
```
**Expected**: 400 Bad Request - "Subscription not found"

## Database Integrity Tests

### Test 26: Foreign Key Constraints
```sql
-- Try to create subscription with invalid plan_id
INSERT INTO subscriptions (subscription_id, user_id, plan_id, ...)
VALUES ('sub_test', 1, 9999, ...);
```
**Expected**: Foreign key constraint violation

### Test 27: Unique Constraints
```sql
-- Try to create duplicate subscription_id
INSERT INTO subscriptions (subscription_id, ...)
VALUES ('sub_existing', ...);
```
**Expected**: Unique constraint violation

### Test 28: Cascading Deletes
```sql
-- Delete user, verify subscriptions cascade properly
DELETE FROM users WHERE user_id = 1;
-- Check related records handled according to ON DELETE rules
```
**Expected**: Cascade or set null according to schema

## Performance Tests

### Test 29: List Plans Performance
```bash
# Time the request
time curl http://localhost:8000/api/v1/billing/plans
```
**Expected**: Response in < 100ms

### Test 30: Analytics Query Performance
```bash
# Time complex analytics query
time curl http://localhost:8000/api/v1/billing/analytics/dashboard \
  -H "Authorization: Bearer ADMIN_TOKEN"
```
**Expected**: Response in < 500ms (adjust based on data volume)

### Test 31: Bulk Usage Recording
```bash
# Record 100 usage events
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/billing/usage \
    -H "Authorization: Bearer USER_TOKEN" \
    -d '{"subscription_id": 1, "resource_type": "document", "quantity": 1}'
done
```
**Expected**: All requests complete successfully

## Integration Tests

### Test 32: End-to-End Subscription Flow
1. User creates subscription with trial
2. System records document processing usage
3. Trial period ends, subscription becomes active
4. System generates first invoice
5. User pays invoice
6. Billing period ends
7. System generates renewal invoice with overage charges
8. User upgrades to higher plan
9. System calculates proration and creates invoice
10. User cancels subscription at period end

**Verify**: All steps complete successfully with proper state transitions

### Test 33: Overage Billing Flow
1. User with Basic plan (100 documents) processes 150 documents
2. System tracks usage in real-time
3. Billing period ends
4. Invoice generated with:
   - Base amount: 29 EUR
   - Overage (50 docs × 0.10): 5 EUR
   - Tax (23%): 7.82 EUR
   - Total: 41.82 EUR

**Verify**: Invoice calculations correct

## Security Tests

### Test 34: Authentication Required
```bash
# Try to access without token
curl http://localhost:8000/api/v1/billing/subscriptions/my
```
**Expected**: 401 Unauthorized

### Test 35: Admin Authorization Required
```bash
# Regular user tries to access admin endpoint
curl http://localhost:8000/api/v1/billing/admin/subscriptions \
  -H "Authorization: Bearer USER_TOKEN"
```
**Expected**: 403 Forbidden

### Test 36: SQL Injection Prevention
```bash
# Try SQL injection in parameters
curl "http://localhost:8000/api/v1/billing/invoices/1; DROP TABLE invoices;"
```
**Expected**: Query parameterization prevents injection

## Audit Trail Tests

### Test 37: Billing Events Logged
```sql
-- Check billing_events table after operations
SELECT * FROM billing_events 
WHERE user_id = 1 
ORDER BY created_at DESC 
LIMIT 10;
```
**Expected**: All major operations logged

**Verify events for**:
- [ ] subscription_created
- [ ] subscription_upgraded
- [ ] subscription_canceled
- [ ] invoice_created
- [ ] payment_succeeded
- [ ] usage_recorded

### Test 38: Audit Data Completeness
```sql
SELECT event_type, old_value, new_value
FROM billing_events
WHERE subscription_id = 1 AND event_type = 'subscription_upgraded';
```
**Expected**: Complete change tracking with before/after values

## Post-Deployment Monitoring

### Metrics to Track
- [ ] MRR and ARR trends
- [ ] Active subscription count
- [ ] Churn rate
- [ ] Failed payment rate
- [ ] Average invoice amount
- [ ] Overage revenue percentage
- [ ] Trial to paid conversion rate
- [ ] API response times
- [ ] Database query performance

### Alerts to Configure
- [ ] Failed payment spike
- [ ] Sudden churn increase
- [ ] Overdue invoices exceeding threshold
- [ ] Database connection issues
- [ ] API error rate increase

## Final Verification

- [ ] All 38 tests passed
- [ ] Database migration successful
- [ ] API documentation complete
- [ ] Audit trail functioning
- [ ] Performance acceptable
- [ ] Security measures verified
- [ ] Error handling robust
- [ ] Integration with existing systems working

## Sign-Off

**Tested By**: ________________
**Date**: ________________
**Environment**: ________________
**Test Results**: Pass / Fail
**Notes**: ________________

---

## Quick Test Script

Save this as `test_billing.sh`:

```bash
#!/bin/bash
API_URL="http://localhost:8000/api/v1/billing"
ADMIN_TOKEN="your_admin_token"
USER_TOKEN="your_user_token"

echo "Testing Billing System..."

# Test 1: List plans
echo "1. Listing subscription plans..."
curl -s "$API_URL/plans" | jq

# Test 2: Create subscription
echo "2. Creating subscription..."
curl -s -X POST "$API_URL/subscriptions" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 1, "billing_cycle": "monthly", "trial_enabled": true}' | jq

# Test 3: Record usage
echo "3. Recording usage..."
curl -s -X POST "$API_URL/usage" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subscription_id": 1, "resource_type": "document", "quantity": 1}' | jq

# Test 4: Get analytics
echo "4. Getting billing analytics..."
curl -s "$API_URL/analytics/billing" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Tests complete!"
```

Run with: `bash test_billing.sh`
