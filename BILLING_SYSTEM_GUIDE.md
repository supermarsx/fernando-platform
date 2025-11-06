# Billing and Subscription System Documentation

## Overview

The Fernando Platform includes a comprehensive billing and subscription management system that handles subscription plans, usage tracking, invoicing, payments, and analytics.

## Features

### 1. Subscription Management
- **Multiple billing cycles**: Monthly, quarterly, annually
- **Free trials**: Configurable trial periods
- **Automatic renewal**: Optional auto-renewal
- **Lifecycle management**: Create, pause, resume, cancel, upgrade
- **Proration**: Automatic proration when upgrading/downgrading plans

### 2. Usage-Based Billing
- **Resource tracking**: Documents processed, API calls, additional users
- **Overage charges**: Automatic calculation beyond plan limits
- **Real-time usage monitoring**: Track consumption throughout billing period
- **Granular metering**: Per-resource pricing

### 3. Invoice Management
- **Automatic generation**: Invoices created at billing cycle end
- **Line items**: Detailed breakdown of charges
- **Tax calculation**: Automatic VAT/sales tax based on jurisdiction
- **Multiple statuses**: Draft, pending, paid, void, overdue
- **PDF export**: Generate PDF invoices (extensible)

### 4. Payment Processing
- **Multiple payment methods**: Credit card, debit card, bank transfer, PayPal, Stripe
- **Payment tracking**: Full audit trail of all transactions
- **Refund support**: Partial and full refunds
- **Failed payment handling**: Retry logic and notifications

### 5. Analytics and Reporting
- **MRR/ARR tracking**: Monthly and annual recurring revenue
- **Churn analysis**: Subscription cancellation rates
- **Revenue forecasting**: Month-over-month trends
- **Usage analytics**: Resource consumption patterns
- **ARPU calculation**: Average revenue per user

## Subscription Plans

### Basic Plan
- **Price**: 29 EUR/month, 79 EUR/quarter, 299 EUR/year
- **Limits**: 100 documents/month, 3 users, 1,000 API calls/month
- **Overage**: 0.10 EUR/document, 5 EUR/user/month, 0.01 EUR/100 API calls
- **Features**: Email support, basic OCR, document extraction, JSON export
- **Trial**: 14 days

### Professional Plan
- **Price**: 99 EUR/month, 269 EUR/quarter, 999 EUR/year
- **Limits**: 1,000 documents/month, 10 users, 10,000 API calls/month
- **Overage**: 0.10 EUR/document, 5 EUR/user/month, 0.01 EUR/100 API calls
- **Features**: Priority support, advanced OCR, LLM extraction, batch processing, API access, custom workflows
- **Trial**: 14 days

### Enterprise Plan
- **Price**: 299 EUR/month, 799 EUR/quarter, 2,999 EUR/year
- **Limits**: Unlimited documents, unlimited users, unlimited API calls
- **Overage**: Not applicable
- **Features**: Dedicated support, unlimited processing, custom integrations, SLA guarantee, white-label options
- **Trial**: 30 days

## Database Schema

### Core Tables

#### subscription_plans
Defines available subscription tiers with pricing and limits.

```sql
- id: Primary key
- name: Plan name
- description: Plan description
- license_tier_id: Link to licensing system
- monthly_price, quarterly_price, annual_price: Pricing tiers
- max_documents_per_month, max_users, max_api_calls_per_month: Usage limits
- overage_*_price: Overage pricing
- features: JSON array of features
- trial_days: Trial period length
- is_active: Plan availability
```

#### subscriptions
Customer subscriptions with status and billing information.

```sql
- id: Primary key
- subscription_id: Public identifier (sub_xxx)
- user_id, plan_id, license_id: Foreign keys
- status: active, trialing, past_due, canceled, paused, expired
- billing_cycle: monthly, quarterly, annually
- start_date, end_date: Subscription lifetime
- current_period_start, current_period_end: Current billing period
- trial_start, trial_end: Trial period dates
- auto_renew: Automatic renewal flag
- documents_used_this_period: Usage counter
- api_calls_used_this_period: Usage counter
- additional_users_this_period: Usage counter
- base_amount: Subscription cost
- payment_method_id: Default payment method
```

#### invoices
Billing invoices with line items and payment status.

```sql
- id: Primary key
- invoice_number: Human-readable ID (INV-YYYYMM-XXXXX)
- subscription_id, user_id: Foreign keys
- status: draft, pending, paid, void, uncollectible, overdue
- subtotal, tax_amount, discount_amount: Amount breakdown
- total_amount, amount_paid, amount_due: Payment tracking
- line_items: JSON array of charges
- issue_date, due_date, paid_at: Date tracking
- period_start, period_end: Billing period
- tax_rate, tax_jurisdiction: Tax information
- pdf_url: Generated invoice PDF
```

#### payments
Payment transactions for invoices.

```sql
- id: Primary key
- payment_id: Public identifier (pay_xxx)
- invoice_id, user_id, payment_method_id: Foreign keys
- amount, currency: Payment amount
- status: pending, processing, succeeded, failed, refunded
- payment_method: Payment type
- transaction_id: External payment provider ID
- processed_at, failed_at: Status timestamps
- refunded_amount, refunded_at: Refund information
```

#### usage_records
Granular usage tracking for billing.

```sql
- id: Primary key
- subscription_id, user_id: Foreign keys
- resource_type: document, api_call, user, storage
- quantity: Number of units consumed
- unit_price: Price per unit
- timestamp: Usage timestamp
- billing_period_start, billing_period_end: Billing period
- billed: Whether included in invoice
- invoice_id: Associated invoice
```

#### payment_methods
Stored payment methods for customers.

```sql
- id: Primary key
- user_id: Foreign key
- type: credit_card, debit_card, bank_transfer, paypal, stripe, invoice
- is_default: Default payment method flag
- card_last4, card_brand, card_exp_month, card_exp_year: Card details (masked)
- bank_name, bank_account_last4: Bank details (masked)
- provider, provider_payment_method_id: External provider details
- is_active, verified: Status flags
```

#### billing_events
Audit trail for billing operations.

```sql
- id: Primary key
- subscription_id, invoice_id, payment_id, user_id: Foreign keys
- event_type: subscription_created, invoice_paid, payment_failed, etc.
- description: Human-readable description
- old_value, new_value: Change tracking (JSON)
- created_at: Event timestamp
```

#### tax_rates
Tax rates by jurisdiction.

```sql
- id: Primary key
- country, region: Jurisdiction
- tax_type: VAT, sales_tax, GST
- rate: Tax percentage
- applies_to_digital_services, applies_to_physical_goods: Applicability
- effective_from, effective_until: Validity period
- is_active: Active status
```

## API Endpoints

### Subscription Plans

```
GET    /api/v1/billing/plans                      # List all plans
GET    /api/v1/billing/plans/{plan_id}            # Get plan details
POST   /api/v1/billing/plans                      # Create plan (admin)
PUT    /api/v1/billing/plans/{plan_id}            # Update plan (admin)
```

### Subscriptions

```
POST   /api/v1/billing/subscriptions                        # Create subscription
GET    /api/v1/billing/subscriptions/my                     # Get user's subscriptions
GET    /api/v1/billing/subscriptions/{subscription_id}      # Get subscription details
POST   /api/v1/billing/subscriptions/{subscription_id}/cancel     # Cancel subscription
POST   /api/v1/billing/subscriptions/{subscription_id}/pause      # Pause subscription
POST   /api/v1/billing/subscriptions/{subscription_id}/resume     # Resume subscription
POST   /api/v1/billing/subscriptions/{subscription_id}/upgrade    # Upgrade/downgrade
GET    /api/v1/billing/subscriptions/{subscription_id}/usage      # Get usage summary
```

### Invoices

```
GET    /api/v1/billing/invoices/my                # Get user's invoices
GET    /api/v1/billing/invoices/{invoice_id}      # Get invoice details
POST   /api/v1/billing/invoices/{invoice_id}/pay  # Pay invoice
GET    /api/v1/billing/invoices/{invoice_id}/pdf  # Download PDF
```

### Payment Methods

```
POST   /api/v1/billing/payment-methods             # Add payment method
GET    /api/v1/billing/payment-methods             # List payment methods
DELETE /api/v1/billing/payment-methods/{method_id} # Delete payment method
```

### Usage Tracking

```
POST   /api/v1/billing/usage                       # Record usage
```

### Analytics (Admin Only)

```
GET    /api/v1/billing/analytics/billing          # Get billing analytics
GET    /api/v1/billing/analytics/dashboard        # Get dashboard data
GET    /api/v1/billing/admin/subscriptions        # List all subscriptions (admin)
GET    /api/v1/billing/admin/invoices             # List all invoices (admin)
```

## Usage Examples

### 1. Create a Subscription

```python
import requests

# Create subscription for current user
response = requests.post(
    "http://localhost:8000/api/v1/billing/subscriptions",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "plan_id": 1,  # Basic plan
        "billing_cycle": "monthly",
        "auto_renew": True,
        "trial_enabled": True
    }
)

subscription = response.json()
print(f"Subscription ID: {subscription['subscription_id']}")
print(f"Status: {subscription['status']}")
print(f"Trial ends: {subscription['trial_end']}")
```

### 2. Track Usage

```python
# Record document processing
requests.post(
    "http://localhost:8000/api/v1/billing/usage",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "subscription_id": subscription_id,
        "resource_type": "document",
        "quantity": 1,
        "description": "Invoice processing",
        "reference_id": "job_12345"
    }
)

# Check current usage
usage_response = requests.get(
    f"http://localhost:8000/api/v1/billing/subscriptions/{subscription_id}/usage",
    headers={"Authorization": f"Bearer {token}"}
)
usage = usage_response.json()
print(f"Documents used: {usage['documents']['used']}/{usage['documents']['included']}")
print(f"Overage charge: {usage['total_overage_charge']} EUR")
```

### 3. Upgrade Subscription

```python
# Upgrade to Professional plan
response = requests.post(
    f"http://localhost:8000/api/v1/billing/subscriptions/{subscription_id}/upgrade",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "new_plan_id": 2,  # Professional plan
        "prorate": True
    }
)

print(f"Upgraded to: {response.json()['plan_id']}")
```

### 4. Get Billing Analytics (Admin)

```python
response = requests.get(
    "http://localhost:8000/api/v1/billing/analytics/dashboard",
    headers={"Authorization": f"Bearer {admin_token}"}
)

analytics = response.json()
print(f"MRR: {analytics['billing_analytics']['monthly_recurring_revenue']} EUR")
print(f"Active subscriptions: {analytics['billing_analytics']['active_subscriptions']}")
print(f"Churn rate: {analytics['billing_analytics']['churn_rate']}%")
```

## Integration with Existing Systems

### Licensing System Integration
The billing system extends the existing licensing system:
- Each subscription plan is linked to a license tier
- Subscriptions can optionally create licenses
- Feature gating uses both licensing and subscription checks

### Usage Tracking Integration
Integrate usage tracking into your application:

```python
from app.services.billing_service import BillingService

# In your document processing code
def process_document(document_id, user_id, subscription_id, db):
    # Process document...
    result = process_invoice(document_id)
    
    # Record usage for billing
    billing_service = BillingService(db)
    billing_service.record_usage(
        subscription_id=subscription_id,
        user_id=user_id,
        resource_type="document",
        quantity=1,
        reference_id=f"doc_{document_id}"
    )
    
    return result
```

### Webhook Integration
For production deployment, integrate with payment providers:

```python
# Example Stripe webhook handler
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    event = stripe.Webhook.construct_event(
        payload, sig_header, webhook_secret
    )
    
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        # Update payment status in database
        # Mark invoice as paid
    
    return {"status": "success"}
```

## Tax Compliance

The system includes built-in tax calculation:
- **EU VAT**: Automatic VAT calculation for European customers
- **US Sales Tax**: State-specific sales tax rates
- **Tax reporting**: Audit trail for compliance

Default tax rates are included in the migration:
- Portugal: 23% VAT
- Spain: 21% VAT
- France: 20% VAT
- Germany: 19% VAT
- Italy: 22% VAT
- California: 7.25% Sales Tax
- New York: 4% Sales Tax

## Proration Logic

When users upgrade/downgrade plans, the system calculates proration:

```
Unused Amount = (Old Plan Price / Total Days) × Remaining Days
New Period Cost = (New Plan Price / Total Days) × Remaining Days
Proration Amount = max(0, New Period Cost - Unused Amount)
```

If proration is positive (upgrade), an immediate invoice is created.

## Billing Cycle Management

The system handles billing cycles automatically:
1. **End of trial**: Transition from trialing to active, create first invoice
2. **End of period**: Generate invoice with base amount + overage charges
3. **Auto-renewal**: Extend period and create new invoice
4. **Failed payment**: Mark subscription as past_due, send notifications
5. **Cancellation**: Either immediate or at period end based on user choice

## Best Practices

1. **Always use transactions**: Billing operations should be atomic
2. **Record everything**: Use billing_events for audit trails
3. **Handle failures gracefully**: Implement retry logic for payments
4. **Send notifications**: Email users about invoices, payments, failures
5. **Test thoroughly**: Use test subscriptions and mock payments
6. **Monitor metrics**: Track MRR, churn, ARPU regularly
7. **Review tax compliance**: Update tax rates when regulations change
8. **Secure payment data**: Never store full card numbers or CVV codes

## Migration

To apply the billing system to your database:

```bash
cd /workspace/fernando/backend
alembic upgrade head  # This will run migration 005_add_billing
```

This creates all 8 tables, indexes, and inserts default data:
- 3 subscription plans (Basic, Professional, Enterprise)
- 7 tax rates (EU countries + US states)

## Troubleshooting

### Common Issues

**Issue**: Subscription creation fails with "Plan not found"
**Solution**: Ensure subscription plans are created and active

**Issue**: Usage tracking not updating subscription counters
**Solution**: Verify subscription_id is correct and status is active

**Issue**: Invoice generation fails
**Solution**: Check that billing period dates are valid and plan has pricing

**Issue**: Payment processing stuck in pending
**Solution**: Implement actual payment gateway integration or mark as succeeded manually

## Future Enhancements

Potential improvements for production deployment:
1. **Dunning management**: Automated retry for failed payments
2. **Coupons and discounts**: Promotional codes and volume discounts
3. **Multi-currency support**: Dynamic currency conversion
4. **Revenue recognition**: GAAP-compliant revenue accounting
5. **Metered billing**: Real-time usage-based pricing
6. **Self-service portal**: Customer billing management interface
7. **Automated emails**: Invoice delivery, payment reminders
8. **Accounting integrations**: QuickBooks, Xero, Sage
9. **Payment gateways**: Full Stripe, PayPal, Braintree integration
10. **Subscription analytics**: Cohort analysis, LTV prediction

## Support

For technical support or questions about the billing system:
- Check API documentation: http://localhost:8000/docs
- Review audit logs in billing_events table
- Monitor system health: GET /api/v1/system/status
- Contact development team for customization requests
