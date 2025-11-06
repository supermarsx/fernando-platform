# Payment System Frontend Integration - Setup Guide

## Overview

The frontend payment UI has been implemented with support for:
- Stripe card payments with Stripe Elements
- PayPal payments with PayPal SDK
- Cryptocurrency payments (Bitcoin, Ethereum, USDT)

## Files Created/Modified

### Created:
1. `src/components/PaymentModal.tsx` (408 lines)
   - Stripe card payment component
   - PayPal payment component
   - Cryptocurrency payment component
   - Tabbed interface for payment method selection

### Modified:
1. `src/pages/BillingPage.tsx`
   - Added payment modal integration
   - Updated invoice "Pay Now" buttons
   - Added payment success handler

2. `src/lib/api.ts`
   - Added payment API methods (billingAPI.createStripePaymentIntent, etc.)
   - Added paymentAPI object with fraud check and payment methods

3. `.env.template` - Created environment variable template

---

## Setup Instructions

### Step 1: Install Required Dependencies

```bash
cd /workspace/fernando/frontend/accounting-frontend

# Install Stripe libraries
npm install @stripe/stripe-js @stripe/react-stripe-js

# Install PayPal SDK
npm install @paypal/react-paypal-js

# Install if missing
npm install lucide-react
```

### Step 2: Configure Environment Variables

Create `.env` file from template:

```bash
cp .env.template .env
```

Edit `.env` and add your API keys:

```env
# Stripe Publishable Key (starts with pk_test_ for testing)
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE

# PayPal Client ID (from PayPal Developer Dashboard)
REACT_APP_PAYPAL_CLIENT_ID=YOUR_CLIENT_ID_HERE

# API Base URL
REACT_APP_API_BASE_URL=http://localhost:8000
```

### Step 3: Get API Keys

#### Stripe (Free Test Account)
1. Go to https://dashboard.stripe.com/register
2. Create account (no credit card required for testing)
3. Navigate to Developers → API keys
4. Copy "Publishable key" (starts with `pk_test_`)
5. Copy "Secret key" (starts with `sk_test_`) - for backend .env

#### PayPal (Sandbox Account)
1. Go to https://developer.paypal.com
2. Sign in with PayPal account (or create one)
3. Go to "My Apps & Credentials"
4. Under "REST API apps", click "Create App"
5. Copy "Client ID" for Sandbox environment
6. Copy "Secret" for backend .env

#### Coinbase Commerce (Optional for Crypto)
1. Go to https://commerce.coinbase.com
2. Create account
3. Go to Settings → API keys
4. Generate API key
5. Copy API key and Webhook secret for backend .env

---

## Component Usage

### PaymentModal Component

The `PaymentModal` component provides a complete payment interface with tabs for different payment methods.

**Props:**
```typescript
interface PaymentModalProps {
  invoice: Invoice;        // Invoice object with id, amount, currency
  onClose: () => void;     // Called when modal is closed
  onSuccess: () => void;   // Called when payment succeeds
}
```

**Features:**
- **Card Tab**: Stripe Elements for secure card entry
- **PayPal Tab**: PayPal buttons for PayPal/credit card payment
- **Crypto Tab**: Coinbase Commerce hosted payment page

**Example:**
```tsx
{showPaymentModal && selectedInvoice && (
  <PaymentModal
    invoice={selectedInvoice}
    onClose={() => setShowPaymentModal(false)}
    onSuccess={() => {
      fetchData();  // Refresh invoices
      setShowPaymentModal(false);
    }}
  />
)}
```

---

## Payment Flow

### Stripe Card Payment

1. User clicks "Pay Now" on invoice
2. PaymentModal opens with Card tab selected
3. Component calls backend `/api/v1/payments/stripe-intent?invoice_id=X`
4. Backend creates Stripe PaymentIntent and returns client_secret
5. User enters card details in Stripe Elements
6. User clicks "Pay" button
7. Stripe.js confirms payment with client_secret
8. On success, Stripe webhook notifies backend
9. Backend updates invoice status to "paid"
10. Frontend refreshes data and shows success

### PayPal Payment

1. User clicks "Pay Now" on invoice
2. PaymentModal opens with PayPal tab
3. Component calls backend `/api/v1/payments/paypal-order?invoice_id=X`
4. Backend creates PayPal order and returns order_id + approval_url
5. User clicks PayPal button
6. PayPal popup opens for authentication
7. User approves payment in PayPal
8. Component calls backend `/api/v1/payments/paypal-capture/{order_id}`
9. Backend captures payment and updates invoice
10. Frontend refreshes data and shows success

### Cryptocurrency Payment

1. User clicks "Pay Now" on invoice
2. PaymentModal opens with Crypto tab
3. User clicks "Pay with Crypto" button
4. Component calls backend `/api/v1/payments/crypto-charge?invoice_id=X`
5. Backend creates Coinbase charge and returns hosted_url
6. New window opens with Coinbase payment page
7. User sends crypto to provided address
8. Component polls backend `/api/v1/payments/crypto-status/{charge_id}` every 5 seconds
9. When payment detected on blockchain, Coinbase webhook notifies backend
10. Backend updates invoice status
11. Frontend polling detects status change and shows success

---

## Testing

### Test Credit Cards (Stripe)

```
Success:          4242 4242 4242 4242
Decline:          4000 0000 0000 0002
3D Secure:        4000 0025 0000 3155
Insufficient:     4000 0000 0000 9995

CVC: Any 3 digits
Expiry: Any future date
ZIP: Any 5 digits
```

### PayPal Sandbox

1. Create sandbox buyer account in PayPal Developer Dashboard
2. Use sandbox credentials to test
3. Payments don't use real money

### Cryptocurrency

Use Coinbase Commerce test mode - charges don't require real crypto.

---

## API Methods

### billingAPI (extended)

```typescript
// Stripe
billingAPI.createStripePaymentIntent(invoiceId: number)
  // Returns: { client_secret, payment_intent_id, amount, currency }

// PayPal
billingAPI.createPayPalOrder(invoiceId: number)
  // Returns: { order_id, approval_url, status }

billingAPI.capturePayPalOrder(orderId: string)
  // Returns: { capture_id, status, amount }

// Cryptocurrency
billingAPI.createCryptoCharge(invoiceId: number)
  // Returns: { charge_id, hosted_url, addresses, pricing }

billingAPI.getCryptoChargeStatus(chargeId: string)
  // Returns: { charge_id, status, payments, timeline }
```

---

## Security Considerations

### PCI Compliance

- **No card data storage**: All card data handled by Stripe Elements
- **Tokenization**: Stripe creates payment method tokens
- **TLS required**: All API calls over HTTPS in production
- **CSP headers**: Configure Content Security Policy for Stripe domains

### Environment Variables

- **Never commit .env**: Add to .gitignore
- **Use different keys**: Separate test and production keys
- **Rotate regularly**: Change API keys periodically

### Webhook Security

- **Verify signatures**: Backend validates all webhook signatures
- **Use webhook secrets**: Each provider has separate webhook secret
- **Idempotency**: Handle duplicate webhook deliveries

---

## Troubleshooting

### "Stripe not loaded" Error

**Cause**: Stripe publishable key not configured or invalid

**Solution**: 
```bash
# Check .env file has correct key
cat frontend/accounting-frontend/.env | grep STRIPE

# Ensure key starts with pk_test_ or pk_live_
```

### PayPal Button Not Showing

**Cause**: PayPal client ID not configured

**Solution**:
```bash
# Check .env file
cat frontend/accounting-frontend/.env | grep PAYPAL

# Ensure client ID is correct (no spaces)
```

### Crypto Payment Window Won't Open

**Cause**: Pop-up blocker preventing window

**Solution**:
- Allow pop-ups for your domain
- User must click button directly (not from setTimeout)

### Payment Intent Creation Fails

**Cause**: Backend doesn't have Stripe secret key

**Solution**:
```bash
# Check backend .env
cat backend/.env | grep STRIPE_SECRET_KEY

# Should start with sk_test_ or sk_live_
```

---

## Production Checklist

### Frontend
- [ ] Change to production Stripe publishable key (pk_live_...)
- [ ] Change to production PayPal client ID
- [ ] Update API_BASE_URL to production API
- [ ] Enable CSP headers for payment domains
- [ ] Test all payment methods end-to-end
- [ ] Configure error tracking (Sentry, etc.)

### Backend  
- [ ] Change to production Stripe secret key (sk_live_...)
- [ ] Change to production PayPal credentials
- [ ] Configure Coinbase Commerce production mode
- [ ] Set up webhook endpoints with TLS
- [ ] Register webhook URLs with providers
- [ ] Test webhook signature validation
- [ ] Enable fraud detection rules
- [ ] Configure email notifications

---

## Support

### Stripe Documentation
- https://stripe.com/docs/payments/payment-intents
- https://stripe.com/docs/stripe-js

### PayPal Documentation
- https://developer.paypal.com/docs/checkout/
- https://developer.paypal.com/sdk/js/

### Coinbase Commerce Documentation
- https://commerce.coinbase.com/docs/

---

## Next Steps

1. Install npm dependencies
2. Get Stripe and PayPal test API keys
3. Configure .env files (frontend and backend)
4. Start backend server
5. Start frontend development server
6. Test payment flow with test cards
7. Monitor backend logs for webhook events
8. Verify invoice status updates in database

---

**Status**: Frontend Implementation Complete
**Ready For**: API Key Configuration & Testing
