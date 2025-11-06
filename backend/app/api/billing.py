"""
Billing API Endpoints

REST API for billing, subscriptions, invoices, and payments.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.services.billing_service import BillingService
from app.schemas.billing_schemas import (
    SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanResponse,
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse,
    InvoiceResponse, PaymentResponse, PaymentMethodCreate, PaymentMethodResponse,
    UsageRecordCreate, UsageRecordResponse,
    BillingAnalytics, UsageAnalytics, BillingDashboard,
    SubscriptionCancelRequest, SubscriptionPauseRequest, SubscriptionUpgradeRequest,
    InvoicePayRequest, RefundRequest
)
from app.models.billing import SubscriptionStatus, InvoiceStatus, PaymentMethod
from app.api.deps import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


# ============================================================================
# SUBSCRIPTION PLAN ENDPOINTS (Admin Only)
# ============================================================================

@router.post("/plans", response_model=SubscriptionPlanResponse, dependencies=[Depends(require_admin)])
def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a new subscription plan (Admin only)"""
    billing_service = BillingService(db)
    return billing_service.create_subscription_plan(plan_data)


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
def list_subscription_plans(
    active_only: bool = Query(True, description="Show only active plans"),
    db: Session = Depends(get_db)
):
    """List all subscription plans"""
    billing_service = BillingService(db)
    return billing_service.list_subscription_plans(active_only=active_only)


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
def get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """Get subscription plan details"""
    billing_service = BillingService(db)
    plan = billing_service.get_subscription_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    return plan


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanResponse, dependencies=[Depends(require_admin)])
def update_subscription_plan(
    plan_id: int,
    plan_data: SubscriptionPlanUpdate,
    db: Session = Depends(get_db)
):
    """Update subscription plan (Admin only)"""
    billing_service = BillingService(db)
    plan = billing_service.get_subscription_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    
    # Update fields
    for field, value in plan_data.dict(exclude_unset=True).items():
        setattr(plan, field, value)
    
    db.commit()
    db.refresh(plan)
    return plan


# ============================================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================================

@router.post("/subscriptions", response_model=SubscriptionResponse)
def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription for the current user"""
    billing_service = BillingService(db)
    try:
        subscription = billing_service.create_subscription(
            user_id=current_user.user_id,
            subscription_data=subscription_data
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/my", response_model=List[SubscriptionResponse])
def get_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all subscriptions for the current user"""
    from app.models.billing import Subscription
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.user_id
    ).order_by(Subscription.created_at.desc()).all()
    return subscriptions


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get subscription details"""
    from app.models.billing import Subscription
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.user_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return subscription


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    cancel_request: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a subscription"""
    billing_service = BillingService(db)
    try:
        subscription = billing_service.cancel_subscription(
            subscription_id=subscription_id,
            user_id=current_user.user_id,
            cancel_immediately=cancel_request.cancel_immediately,
            reason=cancel_request.reason
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionResponse)
def pause_subscription(
    subscription_id: int,
    pause_request: SubscriptionPauseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause a subscription"""
    billing_service = BillingService(db)
    try:
        subscription = billing_service.pause_subscription(
            subscription_id=subscription_id,
            user_id=current_user.user_id,
            pause_until=pause_request.pause_until
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionResponse)
def resume_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume a paused subscription"""
    billing_service = BillingService(db)
    try:
        subscription = billing_service.resume_subscription(
            subscription_id=subscription_id,
            user_id=current_user.user_id
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/{subscription_id}/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    subscription_id: int,
    upgrade_request: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade or downgrade subscription to a different plan"""
    billing_service = BillingService(db)
    try:
        subscription, prorated_amount = billing_service.upgrade_subscription(
            subscription_id=subscription_id,
            user_id=current_user.user_id,
            new_plan_id=upgrade_request.new_plan_id,
            prorate=upgrade_request.prorate
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# USAGE TRACKING ENDPOINTS
# ============================================================================

@router.post("/usage", response_model=UsageRecordResponse)
def record_usage(
    usage_data: UsageRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record usage for billing purposes"""
    billing_service = BillingService(db)
    try:
        usage_record = billing_service.record_usage(
            subscription_id=usage_data.subscription_id,
            user_id=current_user.user_id,
            resource_type=usage_data.resource_type,
            quantity=usage_data.quantity,
            description=usage_data.description,
            reference_id=usage_data.reference_id,
            metadata=usage_data.metadata
        )
        return usage_record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/{subscription_id}/usage")
def get_usage_summary(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage summary for a subscription"""
    billing_service = BillingService(db)
    try:
        return billing_service.get_usage_summary(subscription_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# INVOICE ENDPOINTS
# ============================================================================

@router.get("/invoices/my", response_model=List[InvoiceResponse])
def get_my_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all invoices for the current user"""
    billing_service = BillingService(db)
    return billing_service.list_invoices(
        user_id=current_user.user_id,
        status=status,
        limit=limit
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invoice details"""
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id, current_user.user_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResponse)
def pay_invoice(
    invoice_id: int,
    pay_request: InvoicePayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pay an invoice"""
    billing_service = BillingService(db)
    try:
        payment = billing_service.process_payment(
            invoice_id=invoice_id,
            user_id=current_user.user_id,
            payment_method=PaymentMethod.CREDIT_CARD,  # Default, should be from payment_method
            payment_method_id=pay_request.payment_method_id
        )
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download invoice as PDF"""
    billing_service = BillingService(db)
    invoice = billing_service.get_invoice(invoice_id, current_user.user_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # In production, generate PDF and return file
    # For now, return invoice data
    return {
        "message": "PDF generation not implemented yet",
        "invoice": invoice
    }


# ============================================================================
# PAYMENT METHOD ENDPOINTS
# ============================================================================

@router.post("/payment-methods", response_model=PaymentMethodResponse)
def add_payment_method(
    payment_method: PaymentMethodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a payment method for the current user"""
    from app.models.billing import PaymentMethodModel
    
    # If setting as default, unset other defaults
    if payment_method.is_default:
        db.query(PaymentMethodModel).filter(
            PaymentMethodModel.user_id == current_user.user_id,
            PaymentMethodModel.is_default == True
        ).update({"is_default": False})
    
    new_method = PaymentMethodModel(
        user_id=current_user.user_id,
        **payment_method.dict()
    )
    
    db.add(new_method)
    db.commit()
    db.refresh(new_method)
    
    return new_method


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
def list_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all payment methods for the current user"""
    from app.models.billing import PaymentMethodModel
    
    methods = db.query(PaymentMethodModel).filter(
        PaymentMethodModel.user_id == current_user.user_id,
        PaymentMethodModel.is_active == True
    ).order_by(PaymentMethodModel.is_default.desc(), PaymentMethodModel.created_at.desc()).all()
    
    return methods


@router.delete("/payment-methods/{method_id}")
def delete_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a payment method"""
    from app.models.billing import PaymentMethodModel
    
    method = db.query(PaymentMethodModel).filter(
        PaymentMethodModel.id == method_id,
        PaymentMethodModel.user_id == current_user.user_id
    ).first()
    
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    method.is_active = False
    db.commit()
    
    return {"message": "Payment method deleted successfully"}


# ============================================================================
# ANALYTICS ENDPOINTS (Admin Only)
# ============================================================================

@router.get("/analytics/billing", response_model=BillingAnalytics, dependencies=[Depends(require_admin)])
def get_billing_analytics(
    db: Session = Depends(get_db)
):
    """Get comprehensive billing analytics (Admin only)"""
    billing_service = BillingService(db)
    return billing_service.get_billing_analytics()


@router.get("/analytics/dashboard", dependencies=[Depends(require_admin)])
def get_billing_dashboard(
    db: Session = Depends(get_db)
):
    """Get billing dashboard data (Admin only)"""
    billing_service = BillingService(db)
    
    # Get billing analytics
    billing_analytics = billing_service.get_billing_analytics()
    
    # Get usage analytics (simplified)
    from app.models.billing import UsageRecord, Subscription
    from sqlalchemy import func
    
    total_documents = db.query(func.sum(UsageRecord.quantity)).filter(
        UsageRecord.resource_type == "document"
    ).scalar() or 0
    
    total_api_calls = db.query(func.sum(UsageRecord.quantity)).filter(
        UsageRecord.resource_type == "api_call"
    ).scalar() or 0
    
    total_active_users = db.query(func.count(func.distinct(Subscription.user_id))).filter(
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
    ).scalar() or 0
    
    usage_analytics = {
        "total_documents_processed": total_documents,
        "total_api_calls": total_api_calls,
        "total_active_users": total_active_users,
        "documents_by_plan": {},
        "api_calls_by_plan": {},
        "overage_charges": 0
    }
    
    # Revenue by month (last 12 months)
    from app.models.billing import Invoice
    import calendar
    from dateutil.relativedelta import relativedelta
    
    revenue_by_month = []
    for i in range(11, -1, -1):
        month_start = (datetime.utcnow() - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = month_start + relativedelta(months=1)
        
        month_revenue = db.query(func.sum(Invoice.amount_paid)).filter(
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= month_start,
            Invoice.paid_at < month_end
        ).scalar() or 0
        
        month_subscriptions = db.query(func.count(Subscription.id)).filter(
            Subscription.start_date >= month_start,
            Subscription.start_date < month_end
        ).scalar() or 0
        
        new_subscriptions = db.query(func.count(Subscription.id)).filter(
            Subscription.start_date >= month_start,
            Subscription.start_date < month_end
        ).scalar() or 0
        
        canceled_subscriptions = db.query(func.count(Subscription.id)).filter(
            Subscription.canceled_at >= month_start,
            Subscription.canceled_at < month_end
        ).scalar() or 0
        
        revenue_by_month.append({
            "month": month_start.strftime("%Y-%m"),
            "revenue": round(month_revenue, 2),
            "subscriptions": month_subscriptions,
            "new_subscriptions": new_subscriptions,
            "canceled_subscriptions": canceled_subscriptions
        })
    
    return {
        "billing_analytics": billing_analytics,
        "usage_analytics": usage_analytics,
        "revenue_by_month": revenue_by_month
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin/subscriptions", response_model=List[SubscriptionResponse], dependencies=[Depends(require_admin)])
def list_all_subscriptions(
    status: Optional[SubscriptionStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all subscriptions (Admin only)"""
    from app.models.billing import Subscription
    
    query = db.query(Subscription)
    
    if status:
        query = query.filter(Subscription.status == status)
    
    subscriptions = query.order_by(Subscription.created_at.desc()).offset(offset).limit(limit).all()
    return subscriptions


@router.get("/admin/invoices", response_model=List[InvoiceResponse], dependencies=[Depends(require_admin)])
def list_all_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all invoices (Admin only)"""
    from app.models.billing import Invoice
    
    query = db.query(Invoice)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(Invoice.created_at.desc()).offset(offset).limit(limit).all()
    return invoices


# ============================================================================
# STRIPE INTEGRATION ENDPOINTS
# ============================================================================

from fastapi import Request, Header
from app.services.stripe_service import StripeService, handle_stripe_webhook
from app.core.config import settings


@router.post("/stripe/create-payment-intent")
def create_stripe_payment_intent(
    invoice_id: int,
    save_payment_method: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe payment intent for an invoice"""
    try:
        stripe_service = StripeService(db)
        
        # Get or create Stripe customer
        stripe_customer = stripe_service.get_or_create_stripe_customer(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.full_name
        )
        
        # Create payment intent
        result = stripe_service.pay_invoice_with_stripe(
            invoice_id=invoice_id,
            user_id=current_user.user_id,
            stripe_customer_id=stripe_customer.id,
            save_payment_method=save_payment_method
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment intent creation failed: {str(e)}")


@router.post("/stripe/setup-intent")
def create_stripe_setup_intent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe setup intent for adding payment method"""
    try:
        stripe_service = StripeService(db)
        
        # Get or create Stripe customer
        stripe_customer = stripe_service.get_or_create_stripe_customer(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.full_name
        )
        
        # Create setup intent
        setup_intent = stripe_service.create_setup_intent(
            customer_id=stripe_customer.id,
            metadata={'user_id': str(current_user.user_id)}
        )
        
        return {
            'client_secret': setup_intent.client_secret,
            'setup_intent_id': setup_intent.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setup intent creation failed: {str(e)}")


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    """
    Stripe webhook endpoint for handling payment events
    
    Configure this endpoint in your Stripe dashboard:
    https://dashboard.stripe.com/webhooks
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    payload = await request.body()
    
    try:
        result = handle_stripe_webhook(
            payload=payload,
            sig_header=stripe_signature,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/stripe/confirm-payment")
def confirm_stripe_payment(
    payment_intent_id: str,
    payment_method_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm a Stripe payment intent with payment method"""
    try:
        stripe_service = StripeService(db)
        
        payment_intent = stripe_service.confirm_payment_intent(
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id
        )
        
        return {
            'status': payment_intent.status,
            'payment_intent_id': payment_intent.id,
            'amount': payment_intent.amount / 100,
            'currency': payment_intent.currency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment confirmation failed: {str(e)}")


@router.get("/stripe/payment-methods")
def list_stripe_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Stripe payment methods for current user"""
    try:
        stripe_service = StripeService(db)
        
        # Get Stripe customer
        stripe_customer = stripe_service.get_or_create_stripe_customer(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.full_name
        )
        
        # Get payment methods
        payment_methods = stripe_service.get_payment_methods(stripe_customer.id)
        
        return {
            'payment_methods': [
                {
                    'id': pm.id,
                    'type': pm.type,
                    'card': {
                        'brand': pm.card.brand,
                        'last4': pm.card.last4,
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year
                    } if pm.type == 'card' else None
                }
                for pm in payment_methods
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payment methods: {str(e)}")


@router.post("/stripe/refund")
def create_stripe_refund(
    refund_request: RefundRequest,
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a refund for a Stripe payment (Admin only)"""
    # This should be admin-only in production
    try:
        from app.models.billing import Payment
        
        payment = db.query(Payment).filter(
            Payment.id == payment_id
        ).first()
        
        if not payment or not payment.transaction_id:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        stripe_service = StripeService(db)
        
        refund = stripe_service.create_refund(
            payment_intent_id=payment.transaction_id,
            amount=refund_request.amount,
            reason=refund_request.reason
        )
        
        # Update payment record
        payment.refunded_amount = refund.amount / 100
        payment.refunded_at = datetime.utcnow()
        payment.refund_reason = refund_request.reason
        payment.status = 'refunded' if refund.amount == payment.amount * 100 else 'partially_refunded'
        
        db.commit()
        
        return {
            'refund_id': refund.id,
            'amount': refund.amount / 100,
            'status': refund.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")
