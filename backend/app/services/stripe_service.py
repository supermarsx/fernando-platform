"""
Stripe Payment Gateway Integration Service

Handles all Stripe-related operations including:
- Customer creation and management
- Payment intent creation
- Subscription management via Stripe
- Webhook handling
- Payment method management
"""

import stripe
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from app.models.billing import (
    Payment, PaymentMethodModel, Invoice, Subscription,
    PaymentStatus, PaymentMethod as PaymentMethodEnum
)
from app.services.billing_service import BillingService
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel, TelemetryMixin
from app.middleware.telemetry_decorators import (
    payment_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric
)
from app.services.proxy import get_proxy_client


class StripeService(TelemetryMixin):
    """Service for Stripe payment gateway integration"""
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        self.db = db
        stripe.api_key = api_key or settings.STRIPE_SECRET_KEY
        self.billing_service = BillingService(db)
        
        # Initialize proxy client
        self.proxy_client = get_proxy_client()
        
        self.log_telemetry_event(
            "stripe.service_initialized", 
            TelemetryEvent.PAYMENT_INTENT_CREATED,
            level=TelemetryLevel.INFO
        )
    
    # ============================================================================
    # CUSTOMER MANAGEMENT
    # ============================================================================
    
    @payment_telemetry("create_stripe_customer")
    def create_stripe_customer(
        self,
        user_id: int,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> stripe.Customer:
        """Create a customer in Stripe"""
        customer_metadata = metadata or {}
        customer_metadata['user_id'] = str(user_id)
        
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=customer_metadata
        )
        
        # Record customer creation metrics
        self.record_business_kpi(
            "payment.customers.created.count", 
            1.0,
            {"user_id": str(user_id), "email_domain": email.split('@')[1] if '@' in email else "unknown"}
        )
        
        return {
            "customer": customer,
            "business_metric": "payment.customers.created.count",
            "metric_value": 1.0
        }
    
    def get_or_create_stripe_customer(
        self,
        user_id: int,
        email: str,
        name: str
    ) -> stripe.Customer:
        """Get existing Stripe customer or create new one"""
        # Search for existing customer
        customers = stripe.Customer.list(
            email=email,
            limit=1
        )
        
        if customers.data:
            return customers.data[0]
        
        return self.create_stripe_customer(user_id, email, name)
    
    # ============================================================================
    # PAYMENT INTENT MANAGEMENT
    # ============================================================================
    
    @payment_telemetry("create_payment_intent")
    def create_payment_intent(
        self,
        invoice_id: int,
        amount: float,
        currency: str = "eur",
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> stripe.PaymentIntent:
        """Create a Stripe payment intent for an invoice"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Convert amount to cents (Stripe uses smallest currency unit)
        amount_cents = int(amount * 100)
        
        intent_metadata = metadata or {}
        intent_metadata.update({
            'invoice_id': str(invoice_id),
            'invoice_number': invoice.invoice_number,
            'user_id': str(invoice.user_id)
        })
        
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            customer=customer_id,
            payment_method=payment_method_id,
            metadata=intent_metadata,
            description=f"Payment for invoice {invoice.invoice_number}",
            automatic_payment_methods={'enabled': True} if not payment_method_id else None
        )
        
        return payment_intent
    
    @payment_telemetry("confirm_payment_intent")
    def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> stripe.PaymentIntent:
        """Confirm a payment intent"""
        params = {}
        if payment_method_id:
            params['payment_method'] = payment_method_id
        
        return stripe.PaymentIntent.confirm(payment_intent_id, **params)
    
    # ============================================================================
    # PAYMENT METHOD MANAGEMENT
    # ============================================================================
    
    def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str
    ) -> stripe.PaymentMethod:
        """Attach a payment method to a customer"""
        return stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id
        )
    
    def detach_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """Detach a payment method from a customer"""
        return stripe.PaymentMethod.detach(payment_method_id)
    
    def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> stripe.Customer:
        """Set default payment method for a customer"""
        return stripe.Customer.modify(
            customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id
            }
        )
    
    def create_setup_intent(
        self,
        customer_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> stripe.SetupIntent:
        """Create a setup intent for collecting payment method"""
        return stripe.SetupIntent.create(
            customer=customer_id,
            metadata=metadata or {},
            automatic_payment_methods={'enabled': True}
        )
    
    # ============================================================================
    # REFUND MANAGEMENT
    # ============================================================================
    
    def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> stripe.Refund:
        """Create a refund for a payment"""
        refund_params = {'payment_intent': payment_intent_id}
        
        if amount:
            refund_params['amount'] = int(amount * 100)
        
        if reason:
            refund_params['reason'] = reason
        
        return stripe.Refund.create(**refund_params)
    
    # ============================================================================
    # WEBHOOK HANDLING
    # ============================================================================
    
    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
        webhook_secret: str
    ) -> stripe.Event:
        """Verify and construct webhook event from Stripe"""
        return stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    
    def handle_payment_intent_succeeded(self, payment_intent: stripe.PaymentIntent):
        """Handle successful payment intent"""
        invoice_id = int(payment_intent.metadata.get('invoice_id'))
        user_id = int(payment_intent.metadata.get('user_id'))
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return
        
        # Create payment record
        payment = Payment(
            payment_id=f"pay_{payment_intent.id}",
            invoice_id=invoice_id,
            user_id=user_id,
            amount=payment_intent.amount / 100,  # Convert from cents
            currency=payment_intent.currency.upper(),
            status=PaymentStatus.SUCCEEDED,
            payment_method=PaymentMethodEnum.STRIPE,
            transaction_id=payment_intent.id,
            processed_at=datetime.utcnow()
        )
        
        self.db.add(payment)
        
        # Update invoice
        invoice.amount_paid = payment.amount
        invoice.amount_due = 0
        invoice.status = 'paid'
        invoice.paid_at = datetime.utcnow()
        
        self.db.commit()
        
        # Log event
        self.billing_service._log_billing_event(
            user_id=user_id,
            invoice_id=invoice_id,
            payment_id=payment.id,
            event_type="payment_succeeded",
            description=f"Stripe payment {payment_intent.id} succeeded",
            new_value={"amount": payment.amount, "transaction_id": payment_intent.id}
        )
    
    def handle_payment_intent_failed(self, payment_intent: stripe.PaymentIntent):
        """Handle failed payment intent"""
        invoice_id = int(payment_intent.metadata.get('invoice_id'))
        user_id = int(payment_intent.metadata.get('user_id'))
        
        # Create failed payment record
        payment = Payment(
            payment_id=f"pay_{payment_intent.id}",
            invoice_id=invoice_id,
            user_id=user_id,
            amount=payment_intent.amount / 100,
            currency=payment_intent.currency.upper(),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethodEnum.STRIPE,
            transaction_id=payment_intent.id,
            failed_at=datetime.utcnow(),
            failure_reason=payment_intent.last_payment_error.message if payment_intent.last_payment_error else "Unknown error"
        )
        
        self.db.add(payment)
        self.db.commit()
        
        # Log event
        self.billing_service._log_billing_event(
            user_id=user_id,
            invoice_id=invoice_id,
            payment_id=payment.id,
            event_type="payment_failed",
            description=f"Stripe payment {payment_intent.id} failed",
            new_value={
                "transaction_id": payment_intent.id,
                "failure_reason": payment.failure_reason
            }
        )
    
    def handle_payment_method_attached(self, payment_method: stripe.PaymentMethod):
        """Handle payment method attached to customer"""
        customer_id = payment_method.customer
        
        # Find user by Stripe customer ID (would need to store this mapping)
        # For now, extract from metadata if available
        customer = stripe.Customer.retrieve(customer_id)
        user_id = int(customer.metadata.get('user_id', 0))
        
        if not user_id:
            return
        
        # Create payment method record
        pm_data = {
            'user_id': user_id,
            'type': PaymentMethodEnum.CREDIT_CARD if payment_method.type == 'card' else PaymentMethodEnum.STRIPE,
            'provider': 'stripe',
            'provider_payment_method_id': payment_method.id,
            'is_active': True,
            'verified': True
        }
        
        if payment_method.type == 'card':
            pm_data.update({
                'card_last4': payment_method.card.last4,
                'card_brand': payment_method.card.brand,
                'card_exp_month': payment_method.card.exp_month,
                'card_exp_year': payment_method.card.exp_year
            })
        
        db_payment_method = PaymentMethodModel(**pm_data)
        self.db.add(db_payment_method)
        self.db.commit()
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_payment_methods(self, customer_id: str) -> List[stripe.PaymentMethod]:
        """List payment methods for a customer"""
        return stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        ).data
    
    def retrieve_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """Retrieve a payment intent"""
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    
    def retrieve_customer(self, customer_id: str) -> stripe.Customer:
        """Retrieve a customer"""
        return stripe.Customer.retrieve(customer_id)
    
    # ============================================================================
    # INTEGRATED INVOICE PAYMENT
    # ============================================================================
    
    def pay_invoice_with_stripe(
        self,
        invoice_id: int,
        user_id: int,
        stripe_customer_id: str,
        payment_method_id: Optional[str] = None,
        save_payment_method: bool = False
    ) -> Dict[str, Any]:
        """
        Complete flow to pay an invoice using Stripe
        
        Returns dict with payment_intent and status
        """
        invoice = self.billing_service.get_invoice(invoice_id, user_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status == 'paid':
            raise ValueError("Invoice already paid")
        
        # Create payment intent
        payment_intent = self.create_payment_intent(
            invoice_id=invoice_id,
            amount=invoice.amount_due,
            currency=invoice.currency,
            customer_id=stripe_customer_id,
            payment_method_id=payment_method_id
        )
        
        # If payment method provided, attach and confirm
        if payment_method_id:
            if save_payment_method:
                self.attach_payment_method(payment_method_id, stripe_customer_id)
            
            # Confirm payment immediately
            payment_intent = self.confirm_payment_intent(
                payment_intent.id,
                payment_method_id
            )
        
        return {
            'payment_intent_id': payment_intent.id,
            'client_secret': payment_intent.client_secret,
            'status': payment_intent.status,
            'amount': payment_intent.amount / 100,
            'currency': payment_intent.currency
        }
    
    async def _process_via_proxy(
        self,
        operation: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process Stripe operations via proxy client"""
        try:
            request_data = data or {}
            request_data["operation"] = operation
            
            response = await self.proxy_client.request(
                service="stripe",
                endpoint=f"stripe/{operation}",
                method="POST",
                data=request_data
            )
            
            if response.get("success"):
                return response["data"]
            
            return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            print(f"Stripe proxy operation error: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# WEBHOOK ENDPOINT HANDLER
# ============================================================================

def handle_stripe_webhook(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
    db: Session
) -> Dict[str, Any]:
    """
    Main webhook handler for Stripe events
    
    Usage in FastAPI endpoint:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        result = handle_stripe_webhook(payload, sig_header, webhook_secret, db)
    """
    stripe_service = StripeService(db)
    
    try:
        event = stripe_service.construct_webhook_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        raise ValueError(f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}")
    
    # Handle event based on type
    event_type = event.type
    
    if event_type == 'payment_intent.succeeded':
        stripe_service.handle_payment_intent_succeeded(event.data.object)
    
    elif event_type == 'payment_intent.payment_failed':
        stripe_service.handle_payment_intent_failed(event.data.object)
    
    elif event_type == 'payment_method.attached':
        stripe_service.handle_payment_method_attached(event.data.object)
    
    elif event_type == 'customer.subscription.created':
        # Handle subscription created if using Stripe subscriptions
        pass
    
    elif event_type == 'customer.subscription.updated':
        # Handle subscription updated
        pass
    
    elif event_type == 'customer.subscription.deleted':
        # Handle subscription canceled
        pass
    
    elif event_type == 'invoice.payment_succeeded':
        # Handle Stripe-managed invoice paid
        pass
    
    elif event_type == 'invoice.payment_failed':
        # Handle Stripe-managed invoice payment failed
        pass
    
    return {
        'status': 'success',
        'event_type': event_type,
        'event_id': event.id
    }
