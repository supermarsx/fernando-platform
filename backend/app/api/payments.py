"""
Payment Processing API Endpoints

Comprehensive payment endpoints supporting:
- Multiple payment providers (Stripe, PayPal, Cryptocurrency)
- Payment method management
- Fraud detection integration
- Webhook handling for all providers
- Payment retry and dunning management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.billing import PaymentMethod as PaymentMethodEnum
from app.services.payment_gateway import UnifiedPaymentService, PaymentGatewayFactory, PaymentProvider
from app.services.fraud_detection_service import FraudDetectionService
from app.services.dunning_management_service import DunningManagementService
from app.services.stripe_service import handle_stripe_webhook
from app.services.paypal_service import PayPalService
from app.services.cryptocurrency_service import CryptocurrencyService

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PaymentRequest(BaseModel):
    """Request to create a payment"""
    invoice_id: int
    payment_method: str = Field(..., description="Payment method type")
    payment_method_id: Optional[str] = Field(None, description="Saved payment method ID")
    save_payment_method: bool = Field(False, description="Save for future use")
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None


class PaymentMethodCreateRequest(BaseModel):
    """Request to add a payment method"""
    type: str
    provider_token: str  # Token from Stripe.js, PayPal, etc.
    is_default: bool = False
    billing_address: Optional[Dict[str, Any]] = None


class FraudCheckRequest(BaseModel):
    """Request for fraud risk assessment"""
    amount: Decimal
    currency: str = "EUR"
    payment_method: str
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None


# ============================================================================
# PAYMENT PROCESSING ENDPOINTS
# ============================================================================

@router.post("/payments/process")
async def process_payment(
    payment_req: PaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a payment for an invoice using specified payment method
    
    Supports: Credit cards, PayPal, Cryptocurrency, Bank transfers
    """
    
    # Get invoice
    from app.services.billing_service import BillingService
    billing_service = BillingService(db)
    
    invoice = billing_service.get_invoice(payment_req.invoice_id, current_user.user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status == 'paid':
        raise HTTPException(status_code=400, detail="Invoice already paid")
    
    # Fraud check
    fraud_service = FraudDetectionService(db)
    fraud_assessment = fraud_service.assess_payment_risk(
        user_id=current_user.user_id,
        amount=Decimal(str(invoice.amount_due)),
        currency=invoice.currency,
        payment_method=payment_req.payment_method,
        ip_address=payment_req.ip_address,
        device_fingerprint=payment_req.device_fingerprint
    )
    
    if not fraud_assessment["approved"]:
        fraud_service.log_fraud_alert(
            user_id=current_user.user_id,
            payment_id=None,
            risk_assessment=fraud_assessment,
            action_taken="payment_blocked"
        )
        
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Payment blocked due to fraud risk",
                "risk_level": fraud_assessment["risk_level"],
                "risk_score": fraud_assessment["risk_score"],
                "requires_verification": fraud_assessment.get("requires_verification", False)
            }
        )
    
    # Process payment using unified service
    unified_service = UnifiedPaymentService(db)
    
    try:
        payment_method_enum = PaymentMethodEnum(payment_req.payment_method)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment method")
    
    payment_result = unified_service.process_payment(
        invoice_id=payment_req.invoice_id,
        user_id=current_user.user_id,
        payment_method=payment_method_enum,
        amount=Decimal(str(invoice.amount_due)),
        currency=invoice.currency,
        metadata={
            "fraud_check": fraud_assessment,
            "ip_address": payment_req.ip_address
        }
    )
    
    return {
        "status": "success",
        "payment": payment_result,
        "fraud_check": {
            "risk_level": fraud_assessment["risk_level"],
            "requires_verification": fraud_assessment.get("requires_verification", False)
        }
    }


@router.post("/payments/stripe-intent")
async def create_stripe_payment_intent(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe Payment Intent for invoice"""
    
    from app.services.stripe_service import StripeService
    from app.services.billing_service import BillingService
    
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id, current_user.user_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    stripe_service = StripeService(db)
    
    # Get or create Stripe customer
    customer = stripe_service.get_or_create_stripe_customer(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.full_name
    )
    
    # Create payment intent
    payment_intent = stripe_service.create_payment_intent(
        invoice_id=invoice_id,
        amount=invoice.amount_due,
        currency=invoice.currency,
        customer_id=customer.id
    )
    
    return {
        "client_secret": payment_intent.client_secret,
        "payment_intent_id": payment_intent.id,
        "amount": invoice.amount_due,
        "currency": invoice.currency
    }


@router.post("/payments/paypal-order")
async def create_paypal_order(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create PayPal order for invoice payment"""
    
    paypal_service = PayPalService(db)
    
    try:
        order = paypal_service.pay_invoice_with_paypal(
            invoice_id=invoice_id,
            user_id=current_user.user_id
        )
        
        return {
            "order_id": order["order_id"],
            "approval_url": order["approval_url"],
            "status": order["status"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PayPal order creation failed: {str(e)}")


@router.post("/payments/paypal-capture/{order_id}")
async def capture_paypal_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Capture (complete) PayPal order after customer approval"""
    
    paypal_service = PayPalService(db)
    
    try:
        capture = paypal_service.capture_order(order_id)
        return {
            "status": "success",
            "capture_id": capture["capture_id"],
            "amount": capture["amount"],
            "currency": capture["currency"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PayPal capture failed: {str(e)}")


@router.post("/payments/crypto-charge")
async def create_crypto_charge(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create cryptocurrency payment charge for invoice"""
    
    crypto_service = CryptocurrencyService(db)
    
    try:
        charge = crypto_service.pay_invoice_with_crypto(
            invoice_id=invoice_id,
            user_id=current_user.user_id
        )
        
        return {
            "charge_id": charge["charge_id"],
            "hosted_url": charge["hosted_url"],
            "addresses": charge["addresses"],
            "pricing": charge["pricing"],
            "expires_at": charge["expires_at"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crypto charge creation failed: {str(e)}")


@router.get("/payments/crypto-status/{charge_id}")
async def get_crypto_charge_status(
    charge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cryptocurrency charge status"""
    
    crypto_service = CryptocurrencyService(db)
    
    try:
        charge = crypto_service.get_charge(charge_id)
        return {
            "charge_id": charge["charge_id"],
            "status": charge["status"],
            "payments": charge["payments"],
            "timeline": charge["timeline"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PAYMENT METHODS MANAGEMENT
# ============================================================================

@router.get("/payment-methods")
async def list_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available payment methods for user"""
    
    unified_service = UnifiedPaymentService(db)
    methods = unified_service.get_available_payment_methods(current_user.user_id)
    
    # Also get user's saved payment methods
    from app.models.billing import PaymentMethodModel
    saved_methods = db.query(PaymentMethodModel).filter(
        PaymentMethodModel.user_id == current_user.user_id,
        PaymentMethodModel.is_active == True
    ).all()
    
    return {
        "available_methods": methods,
        "saved_methods": [
            {
                "id": pm.id,
                "type": pm.type.value,
                "provider": pm.provider,
                "card_last4": pm.card_last4,
                "card_brand": pm.card_brand,
                "is_default": pm.is_default
            }
            for pm in saved_methods
        ]
    }


# ============================================================================
# FRAUD DETECTION
# ============================================================================

@router.post("/payments/fraud-check")
async def check_fraud_risk(
    fraud_req: FraudCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pre-check fraud risk before payment processing
    
    Use this to show warnings or request additional verification
    """
    
    fraud_service = FraudDetectionService(db)
    
    assessment = fraud_service.assess_payment_risk(
        user_id=current_user.user_id,
        amount=fraud_req.amount,
        currency=fraud_req.currency,
        payment_method=fraud_req.payment_method,
        ip_address=fraud_req.ip_address,
        device_fingerprint=fraud_req.device_fingerprint,
        billing_address=fraud_req.billing_address
    )
    
    return assessment


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    
    from app.core.config import settings
    
    payload = await request.body()
    
    try:
        result = handle_stripe_webhook(
            payload=payload,
            sig_header=stripe_signature,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
            db=db
        )
        
        return {"status": "success", "event_type": result["event_type"]}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/paypal")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle PayPal webhook events"""
    
    from app.core.config import settings
    
    payload = await request.body()
    headers = dict(request.headers)
    
    paypal_service = PayPalService(db)
    
    try:
        # Verify webhook
        event = paypal_service.verify_webhook(
            payload=payload,
            headers=headers,
            webhook_id=settings.PAYPAL_WEBHOOK_ID
        )
        
        # Handle event
        result = paypal_service.handle_webhook_event(event)
        
        return {"status": "success", "result": result}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/coinbase")
async def coinbase_webhook(
    request: Request,
    x_cc_webhook_signature: str = Header(None, alias="X-CC-Webhook-Signature"),
    db: Session = Depends(get_db)
):
    """Handle Coinbase Commerce webhook events"""
    
    from app.core.config import settings
    
    payload = await request.body()
    
    crypto_service = CryptocurrencyService(db)
    
    try:
        # Verify webhook
        event = crypto_service.verify_webhook(
            payload=payload,
            signature=x_cc_webhook_signature,
            secret=settings.COINBASE_COMMERCE_WEBHOOK_SECRET
        )
        
        # Handle event
        result = crypto_service.handle_webhook_event(event)
        
        return {"status": "success", "result": result}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DUNNING MANAGEMENT (Admin)
# ============================================================================

@router.post("/admin/dunning/process-retries")
async def process_dunning_retries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process all scheduled payment retries (admin only)
    
    Should be called by cron job
    """
    
    # Check admin role
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    dunning_service = DunningManagementService(db)
    result = dunning_service.process_scheduled_retries()
    
    return result


@router.get("/admin/dunning/statistics")
async def get_dunning_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dunning statistics and recovery metrics (admin only)"""
    
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    dunning_service = DunningManagementService(db)
    stats = dunning_service.get_dunning_statistics(start, end)
    
    return stats


@router.post("/admin/dunning/check-grace-periods")
async def check_grace_periods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check and expire grace periods (admin only, called by cron)"""
    
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    dunning_service = DunningManagementService(db)
    result = dunning_service.check_grace_periods()
    
    return result
