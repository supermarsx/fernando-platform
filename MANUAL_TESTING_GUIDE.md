# Payment Integration Testing - Manual Setup Guide

## Current Situation

The automated setup has encountered environment configuration issues. This guide provides manual steps to complete the setup and testing.

## Issue Summary

1. **Bash Session**: Stuck in interactive mode, commands not executing properly
2. **Python Environment**: `/app/.venv/bin/python3` exists but missing pip module
3. **Missing Package**: sqlalchemy is not installed, blocking backend startup
4. **Status**: Configuration files created successfully, package installation incomplete

## ✓ What's Already Done

### Backend Configuration
- ✅ `.env` file created at `/workspace/fernando/backend/.env`
- ✅ All payment provider credentials configured (Stripe, PayPal, Coinbase)
- ✅ Fraud detection and dunning management settings configured
- ✅ Test mode enabled for all providers

### Frontend Configuration
- ✅ `.env.local` file created at `/workspace/fernando/frontend/accounting-frontend/.env.local`
- ✅ Stripe publishable key configured
- ✅ PayPal client ID configured
- ✅ Feature flags enabled

### Payment System Code
- ✅ Backend services implemented (payment_gateway.py, stripe_service.py, paypal_service.py, etc.)
- ✅ Frontend PaymentModal component created
- ✅ API endpoints registered
- ✅ Database models defined

## 🔧 Manual Setup Steps

### Option 1: Using System Python (Recommended)

```bash
# Open a fresh terminal session

# 1. Install packages with system Python
cd /workspace/fernando/backend
python3 -m pip install --user sqlalchemy==2.0.23 alembic==1.12.1 \\
  pydantic==2.5.0 pydantic-settings==2.1.0 \\
  python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 \\
  python-multipart==0.0.6 python-dotenv==1.0.0 \\
  fastapi==0.104.1 uvicorn[standard]==0.24.0 \\
  stripe requests

# 2. Verify installation
python3 -c "import sqlalchemy, fastapi, stripe; print('✓ All packages installed')"

# 3. Initialize database
python3 -c "from app.db.session import init_db; init_db(); print('✓ Database initialized')"

# 4. Seed subscription plans
python3 seed_subscription_plans.py

# 5. Start backend server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In a new terminal:
# 6. Install frontend dependencies
cd /workspace/fernando/frontend/accounting-frontend
npm install

# 7. Start frontend server
npm run dev
```

### Option 2: Using uv Package Manager

```bash
# Open a fresh terminal session

cd /workspace/fernando/backend

# 1. Install packages with uv
uv pip install -r requirements.txt
uv pip install stripe requests

# 2. Continue with steps 2-7 from Option 1
```

### Option 3: Recreate Virtual Environment

```bash
# Open a fresh terminal session

cd /workspace/fernando/backend

# 1. Remove problematic venv
rm -rf venv

# 2. Create new venv
python3 -m venv venv

# 3. Activate venv
source venv/bin/activate

# 4. Install pip
python -m ensurepip --upgrade

# 5. Install all dependencies
pip install -r requirements.txt
pip install stripe requests

# 6. Continue with steps 2-7 from Option 1
```

## 🧪 Testing Steps

Once both servers are running:

### 1. Create Test User Account
```
1. Open http://localhost:3000
2. Click "Register"
3. Fill in test user details:
   - Email: test@example.com
   - Password: Test123!
   - Full Name: Test User
4. Click "Register"
```

### 2. Navigate to Billing
```
1. After login, click "Billing" button in dashboard
2. You should see 3 subscription plans:
   - Basic: €29/month
   - Professional: €99/month
   - Enterprise: €299/month
```

### 3. Test Payment Flow
```
1. Click "Subscribe" on Basic plan
2. Payment modal should open
3. Select "Stripe" as payment provider
4. Enter test card details:
   - Card Number: 4242 4242 4242 4242
   - Expiry: 12/34 (any future date)
   - CVC: 123 (any 3 digits)
   - ZIP: 12345 (any 5 digits)
5. Click "Pay €29.00"
6. Wait for payment processing
7. Expected result: "Payment successful" message
8. Subscription should activate immediately
9. Invoice should be generated
```

### 4. Test Different Payment Providers
```
Repeat payment flow with each provider:

✓ Stripe (Credit Card)
  - Use test card: 4242 4242 4242 4242

✓ PayPal
  - Click PayPal button
  - Use PayPal sandbox test account

✓ SEPA Direct Debit
  - Enter test IBAN: DE89370400440532013000
  - Account holder: Test User

✓ Cryptocurrency (if enabled)
  - Select crypto option
  - Test address and QR code display
```

### 5. Test Fraud Detection
```
1. Attempt to make 6 payments in quick succession
2. Expected: 6th attempt should be blocked
3. Error message: "Too many payment attempts. Please try again later."
4. Check API response for risk score
```

### 6. Test Failed Payments
```
1. Use decline test card: 4000 0000 0000 0002
2. Expected: Payment fails with error message
3. Check database for dunning schedule creation
4. Retry should be scheduled for days 3, 7, and 14
```

### 7. Verify Invoice Generation
```
1. Navigate to Invoices section in billing page
2. Check invoice details:
   - Invoice number
   - Amount (€29.00)
   - Payment method
   - Status (Paid)
   - PDF download link
```

### 8. Test Admin Analytics
```
1. Login as admin user
2. Navigate to /admin/billing-analytics
3. Verify data displays:
   - Revenue charts
   - Subscription distribution
   - Payment success rate
   - Churn rate
```

## 🐛 Troubleshooting

### Backend won't start
**Error**: `ModuleNotFoundError: No module named 'sqlalchemy'`
**Solution**: Reinstall packages with one of the methods above

### Frontend build fails
**Error**: `Cannot find module 'react'`
**Solution**: Run `npm install` in frontend directory

### Payment modal doesn't open
**Solution**: Check browser console for errors, verify API is running

### Stripe test card declined
**Solution**: Use different test card from list below

### PayPal button not showing
**Solution**: Verify VITE_PAYPAL_CLIENT_ID in .env.local

## 🔑 Additional Test Cards

### Success Scenarios
- **Generic success**: 4242 4242 4242 4242
- **Visa**: 4012 8888 8888 1881
- **Mastercard**: 5555 5555 5555 4444
- **American Express**: 3782 822463 10005

### Failure Scenarios
- **Card declined**: 4000 0000 0000 0002
- **Insufficient funds**: 4000 0000 0000 9995
- **Lost card**: 4000 0000 0000 9987
- **Stolen card**: 4000 0000 0000 9979

### Special Cases
- **3D Secure required**: 4000 0027 6000 3184
- **Expires immediately**: 4000 0000 0000 0069
- **Processing error**: 4000 0000 0000 0119

## 📊 Expected Test Results

### Successful Payment
```json
{
  "status": "success",
  "payment_id": "pay_xxx",
  "amount": 29.00,
  "currency": "EUR",
  "subscription_id": "sub_xxx",
  "invoice_id": "inv_xxx"
}
```

### Failed Payment
```json
{
  "status": "failed",
  "error": "Card declined",
  "code": "card_declined",
  "decline_code": "generic_decline"
}
```

### Fraud Detection Triggered
```json
{
  "status": "blocked",
  "error": "Too many payment attempts",
  "code": "velocity_limit_exceeded",
  "retry_after": 86400
}
```

## 📝 Testing Checklist

- [ ] Backend server running on port 8000
- [ ] Frontend server running on port 3000
- [ ] User can register new account
- [ ] User can login successfully
- [ ] Billing page displays 3 subscription plans
- [ ] "Subscribe" button opens payment modal
- [ ] Payment modal shows all 4 provider options
- [ ] Stripe payment completes successfully
- [ ] Subscription activates after payment
- [ ] Invoice is generated correctly
- [ ] Invoice PDF can be downloaded
- [ ] PayPal integration works (sandbox)
- [ ] SEPA form accepts test IBAN
- [ ] Cryptocurrency option displays address/QR
- [ ] Fraud detection blocks excessive attempts
- [ ] Failed payment creates dunning schedule
- [ ] Admin analytics page displays data
- [ ] All API endpoints respond correctly

## 🎯 Success Criteria

**The payment integration testing is considered successful when:**

1. ✅ User can complete full payment flow from start to finish
2. ✅ All payment providers are accessible and functional
3. ✅ Subscription activates immediately after payment
4. ✅ Invoice is generated with correct details
5. ✅ Fraud detection triggers appropriately
6. ✅ Failed payments are handled gracefully
7. ✅ Admin analytics display payment data correctly

## 📞 Support Resources

### Configuration Files
- Backend config: `/workspace/fernando/backend/.env`
- Frontend config: `/workspace/fernando/frontend/accounting-frontend/.env.local`
- Database: `/workspace/fernando/backend/accounting_automation.db`

### Documentation
- Payment Implementation: `PAYMENT_INTEGRATION_COMPLETE.md`
- Quick Start Guide: `PAYMENT_QUICK_START.md`
- Frontend Setup: `PAYMENT_FRONTEND_SETUP.md`
- Testing Progress: `PAYMENT_TESTING_PROGRESS.md`

### API Endpoints
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/auth/test
- Subscription Plans: http://localhost:8000/api/v1/billing/subscription-plans

## 🔍 Next Steps After Testing

1. **Document Test Results**: Note any issues or unexpected behavior
2. **Review Logs**: Check both backend and frontend logs for errors
3. **Verify Database**: Confirm all records created correctly
4. **Performance Testing**: Test with multiple concurrent users
5. **Security Review**: Verify PCI compliance measures
6. **Production Preparation**: Update credentials for live environment

---

**Created**: 2025-11-06 03:04:32
**Status**: Manual setup required due to environment issues
**Priority**: High - Payment system ready for testing once environment configured
