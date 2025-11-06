"""
Payment Gateway Abstraction Layer

Provides a unified interface for multiple payment providers including:
- Stripe (credit cards, ACH, SEPA, wallets)
- PayPal (PayPal balance, credit cards)
- Cryptocurrency (Bitcoin, Ethereum, USDT)
- Buy Now Pay Later (Klarna, Afterpay)

This abstraction allows easy switching between providers and fallback logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.billing import PaymentMethod, PaymentStatus
from app.core.config import settings


class PaymentProvider(str, Enum):
    """Available payment providers"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    COINBASE = "coinbase"
    MANUAL = "manual"


class PaymentGatewayInterface(ABC):
    """Abstract base class for payment gateways"""
    
    @abstractmethod
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a payment"""
        pass
    
    @abstractmethod
    def confirm_payment(self, payment_id: str) -> Dict[str, Any]:
        """Confirm and process a payment"""
        pass
    
    @abstractmethod
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel a pending payment"""
        pass
    
    @abstractmethod
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refund a payment (full or partial)"""
        pass
    
    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """Get current payment status"""
        pass
    
    @abstractmethod
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a customer in the payment provider"""
        pass
    
    @abstractmethod
    def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Add a payment method to customer"""
        pass
    
    @abstractmethod
    def remove_payment_method(self, payment_method_id: str) -> bool:
        """Remove a payment method"""
        pass
    
    @abstractmethod
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> Dict[str, Any]:
        """Verify and parse webhook payload"""
        pass


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances"""
    
    @staticmethod
    def create_gateway(
        provider: PaymentProvider,
        db: Session
    ) -> PaymentGatewayInterface:
        """Create appropriate payment gateway based on provider"""
        
        if provider == PaymentProvider.STRIPE:
            from app.services.stripe_service import StripeService
            return StripePaymentGateway(db)
        
        elif provider == PaymentProvider.PAYPAL:
            from app.services.paypal_service import PayPalService
            return PayPalPaymentGateway(db)
        
        elif provider == PaymentProvider.COINBASE:
            from app.services.cryptocurrency_service import CryptocurrencyService
            return CryptocurrencyPaymentGateway(db)
        
        else:
            raise ValueError(f"Unsupported payment provider: {provider}")


class StripePaymentGateway(PaymentGatewayInterface):
    """Stripe payment gateway implementation"""
    
    def __init__(self, db: Session):
        from app.services.stripe_service import StripeService
        self.db = db
        self.stripe_service = StripeService(db)
    
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe payment intent"""
        import stripe
        
        amount_cents = int(amount * 100)
        
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            customer=customer_id,
            payment_method=payment_method_id,
            metadata=metadata or {},
            automatic_payment_methods={'enabled': True} if not payment_method_id else None
        )
        
        return {
            'payment_id': intent.id,
            'client_secret': intent.client_secret,
            'status': intent.status,
            'amount': float(intent.amount) / 100,
            'currency': intent.currency.upper()
        }
    
    def confirm_payment(self, payment_id: str) -> Dict[str, Any]:
        """Confirm Stripe payment intent"""
        import stripe
        intent = stripe.PaymentIntent.confirm(payment_id)
        return {
            'payment_id': intent.id,
            'status': intent.status,
            'amount': float(intent.amount) / 100
        }
    
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel Stripe payment intent"""
        import stripe
        intent = stripe.PaymentIntent.cancel(payment_id)
        return {'payment_id': intent.id, 'status': intent.status}
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refund Stripe payment"""
        return self.stripe_service.create_refund(payment_id, float(amount) if amount else None, reason)
    
    def get_payment_status(self, payment_id: str) -> str:
        """Get Stripe payment status"""
        intent = self.stripe_service.retrieve_payment_intent(payment_id)
        return intent.status
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe customer"""
        customer = self.stripe_service.create_stripe_customer(
            user_id=metadata.get('user_id', 0),
            email=email,
            name=name,
            metadata=metadata
        )
        return {'customer_id': customer.id, 'email': customer.email}
    
    def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Attach payment method to Stripe customer"""
        pm = self.stripe_service.attach_payment_method(payment_method_token, customer_id)
        return {'payment_method_id': pm.id, 'type': pm.type}
    
    def remove_payment_method(self, payment_method_id: str) -> bool:
        """Detach payment method from Stripe customer"""
        self.stripe_service.detach_payment_method(payment_method_id)
        return True
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> Dict[str, Any]:
        """Verify Stripe webhook"""
        import stripe
        event = stripe.Webhook.construct_event(payload, signature, secret)
        return {'event_type': event.type, 'data': event.data.object}


class PayPalPaymentGateway(PaymentGatewayInterface):
    """PayPal payment gateway implementation"""
    
    def __init__(self, db: Session):
        from app.services.paypal_service import PayPalService
        self.db = db
        self.paypal_service = PayPalService(db)
    
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create PayPal order"""
        return self.paypal_service.create_order(
            amount=float(amount),
            currency=currency,
            metadata=metadata
        )
    
    def confirm_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture PayPal order"""
        return self.paypal_service.capture_order(payment_id)
    
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel PayPal order"""
        # PayPal orders expire automatically if not captured
        return {'payment_id': payment_id, 'status': 'cancelled'}
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refund PayPal payment"""
        return self.paypal_service.refund_capture(
            capture_id=payment_id,
            amount=float(amount) if amount else None
        )
    
    def get_payment_status(self, payment_id: str) -> str:
        """Get PayPal order status"""
        order = self.paypal_service.get_order(payment_id)
        return order.get('status', 'UNKNOWN')
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """PayPal doesn't require customer creation"""
        return {'customer_id': email, 'email': email}
    
    def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Save PayPal payment method (billing agreement)"""
        return self.paypal_service.create_billing_agreement(payment_method_token)
    
    def remove_payment_method(self, payment_method_id: str) -> bool:
        """Cancel PayPal billing agreement"""
        return self.paypal_service.cancel_billing_agreement(payment_method_id)
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> Dict[str, Any]:
        """Verify PayPal webhook"""
        return self.paypal_service.verify_webhook(payload, signature, secret)


class CryptocurrencyPaymentGateway(PaymentGatewayInterface):
    """Cryptocurrency payment gateway implementation"""
    
    def __init__(self, db: Session):
        from app.services.cryptocurrency_service import CryptocurrencyService
        self.db = db
        self.crypto_service = CryptocurrencyService(db)
    
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create cryptocurrency charge"""
        return self.crypto_service.create_charge(
            amount=float(amount),
            currency=currency,
            metadata=metadata
        )
    
    def confirm_payment(self, payment_id: str) -> Dict[str, Any]:
        """Confirm cryptocurrency payment (automatic)"""
        return self.crypto_service.get_charge(payment_id)
    
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel cryptocurrency charge"""
        return self.crypto_service.cancel_charge(payment_id)
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cryptocurrency refunds not supported"""
        raise NotImplementedError("Cryptocurrency refunds require manual processing")
    
    def get_payment_status(self, payment_id: str) -> str:
        """Get cryptocurrency charge status"""
        charge = self.crypto_service.get_charge(payment_id)
        return charge.get('status', 'UNKNOWN')
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Cryptocurrency doesn't require customer creation"""
        return {'customer_id': email, 'email': email}
    
    def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Cryptocurrency doesn't use saved payment methods"""
        return {'payment_method_id': 'crypto', 'type': 'cryptocurrency'}
    
    def remove_payment_method(self, payment_method_id: str) -> bool:
        """Cryptocurrency doesn't use saved payment methods"""
        return True
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> Dict[str, Any]:
        """Verify cryptocurrency webhook"""
        return self.crypto_service.verify_webhook(payload, signature, secret)


class UnifiedPaymentService:
    """
    Unified payment service that provides a single interface for all payment operations
    with automatic provider selection and fallback logic
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_payment(
        self,
        invoice_id: int,
        user_id: int,
        payment_method: PaymentMethod,
        amount: Decimal,
        currency: str = "EUR",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process payment using appropriate gateway
        
        Returns payment details including status and transaction ID
        """
        
        # Determine provider based on payment method
        provider = self._get_provider_for_method(payment_method)
        
        # Create gateway
        gateway = PaymentGatewayFactory.create_gateway(provider, self.db)
        
        # Prepare metadata
        payment_metadata = metadata or {}
        payment_metadata.update({
            'invoice_id': invoice_id,
            'user_id': user_id,
            'payment_method': payment_method.value
        })
        
        # Create payment
        result = gateway.create_payment(
            amount=amount,
            currency=currency,
            customer_id=str(user_id),
            metadata=payment_metadata
        )
        
        return result
    
    def _get_provider_for_method(self, payment_method: PaymentMethod) -> PaymentProvider:
        """Determine payment provider based on payment method"""
        
        if payment_method in [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.STRIPE,
            PaymentMethod.SEPA_DEBIT,
            PaymentMethod.ACH_DEBIT,
            PaymentMethod.APPLE_PAY,
            PaymentMethod.GOOGLE_PAY
        ]:
            return PaymentProvider.STRIPE
        
        elif payment_method == PaymentMethod.PAYPAL:
            return PaymentProvider.PAYPAL
        
        elif payment_method in [
            PaymentMethod.CRYPTOCURRENCY,
            PaymentMethod.BITCOIN,
            PaymentMethod.ETHEREUM,
            PaymentMethod.USDT
        ]:
            return PaymentProvider.COINBASE
        
        else:
            return PaymentProvider.MANUAL
    
    def get_available_payment_methods(self, user_id: int) -> List[Dict[str, Any]]:
        """Get available payment methods for user"""
        
        methods = []
        
        # Stripe-based methods
        if settings.STRIPE_SECRET_KEY:
            methods.extend([
                {
                    'type': PaymentMethod.CREDIT_CARD.value,
                    'name': 'Credit/Debit Card',
                    'provider': 'stripe',
                    'enabled': True
                },
                {
                    'type': PaymentMethod.SEPA_DEBIT.value,
                    'name': 'SEPA Direct Debit',
                    'provider': 'stripe',
                    'enabled': settings.SEPA_ENABLED
                },
                {
                    'type': PaymentMethod.ACH_DEBIT.value,
                    'name': 'ACH Bank Transfer',
                    'provider': 'stripe',
                    'enabled': settings.ACH_ENABLED
                }
            ])
        
        # PayPal
        if settings.PAYPAL_CLIENT_ID:
            methods.append({
                'type': PaymentMethod.PAYPAL.value,
                'name': 'PayPal',
                'provider': 'paypal',
                'enabled': True
            })
        
        # Cryptocurrency
        if settings.CRYPTO_PAYMENT_ENABLED and settings.COINBASE_COMMERCE_API_KEY:
            methods.extend([
                {
                    'type': PaymentMethod.BITCOIN.value,
                    'name': 'Bitcoin',
                    'provider': 'coinbase',
                    'enabled': True
                },
                {
                    'type': PaymentMethod.ETHEREUM.value,
                    'name': 'Ethereum',
                    'provider': 'coinbase',
                    'enabled': True
                },
                {
                    'type': PaymentMethod.USDT.value,
                    'name': 'USDT (Tether)',
                    'provider': 'coinbase',
                    'enabled': True
                }
            ])
        
        return methods
