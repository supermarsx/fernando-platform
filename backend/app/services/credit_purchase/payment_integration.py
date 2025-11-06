"""
Payment Integration Service

Integration with existing payment systems for credit purchases.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.billing import PaymentMethodModel, PaymentStatus, PaymentMethod
from app.models.credits import CreditPurchaseTransaction, CreditPackage
from app.db.session import get_db

logger = logging.getLogger(__name__)


class PaymentIntegrationService:
    """
    Service for integrating with payment systems
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_payment(self, purchase_id: str, payment_method_id: int,
                      amount: float, currency: str = "USD") -> Dict[str, Any]:
        """
        Process payment using configured payment method
        """
        try:
            # Get payment method
            payment_method = self.db.query(PaymentMethodModel).filter(
                PaymentMethodModel.id == payment_method_id
            ).first()
            
            if not payment_method:
                return {"success": False, "error": "Payment method not found"}
            
            if not payment_method.is_active:
                return {"success": False, "error": "Payment method is inactive"}
            
            # Get purchase transaction
            purchase = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.purchase_id == purchase_id
            ).first()
            
            if not purchase:
                return {"success": False, "error": "Purchase not found"}
            
            # Create payment record (would integrate with actual payment processor)
            payment_result = self._process_with_payment_provider(
                payment_method, amount, currency, purchase_id
            )
            
            # Update purchase with payment result
            if payment_result["success"]:
                purchase.payment_status = "succeeded"
                purchase.payment_transaction_id = payment_result["transaction_id"]
            else:
                purchase.payment_status = "failed"
            
            purchase.meta_data = purchase.meta_data or {}
            purchase.meta_data["payment_result"] = payment_result
            
            self.db.commit()
            
            return payment_result
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _process_with_payment_provider(self, payment_method: PaymentMethodModel,
                                     amount: float, currency: str, 
                                     purchase_id: str) -> Dict[str, Any]:
        """
        Process payment with actual payment provider
        """
        # This is a mock implementation
        # In a real implementation, this would integrate with Stripe, PayPal, etc.
        
        provider = payment_method.provider.lower()
        
        try:
            if provider == "stripe":
                return self._process_stripe_payment(payment_method, amount, currency, purchase_id)
            elif provider == "paypal":
                return self._process_paypal_payment(payment_method, amount, currency, purchase_id)
            else:
                return self._process_generic_payment(payment_method, amount, currency, purchase_id)
                
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return {
                "success": False,
                "error": "Payment processing failed",
                "details": str(e),
                "transaction_id": None
            }
    
    def _process_stripe_payment(self, payment_method: PaymentMethodModel,
                              amount: float, currency: str, purchase_id: str) -> Dict[str, Any]:
        """
        Mock Stripe payment processing
        """
        # Simulate Stripe API call
        transaction_id = f"stripe_{uuid.uuid4().hex}"
        
        # Simulate success/failure (90% success rate)
        import random
        success = random.random() > 0.1
        
        if success:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "provider": "stripe",
                "amount": amount,
                "currency": currency,
                "status": "succeeded",
                "processed_at": datetime.utcnow().isoformat(),
                "receipt_url": f"https://dashboard.stripe.com/receipts/{transaction_id}"
            }
        else:
            return {
                "success": False,
                "transaction_id": transaction_id,
                "provider": "stripe",
                "error": "Payment was declined",
                "error_code": "card_declined",
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _process_paypal_payment(self, payment_method: PaymentMethodModel,
                              amount: float, currency: str, purchase_id: str) -> Dict[str, Any]:
        """
        Mock PayPal payment processing
        """
        # Simulate PayPal API call
        transaction_id = f"paypal_{uuid.uuid4().hex}"
        
        # Simulate success/failure (85% success rate)
        import random
        success = random.random() > 0.15
        
        if success:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "provider": "paypal",
                "amount": amount,
                "currency": currency,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "transaction_id": transaction_id,
                "provider": "paypal",
                "error": "Payment declined by PayPal",
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _process_generic_payment(self, payment_method: PaymentMethodModel,
                               amount: float, currency: str, purchase_id: str) -> Dict[str, Any]:
        """
        Generic payment processing for other providers
        """
        transaction_id = f"generic_{uuid.uuid4().hex}"
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "provider": payment_method.provider,
            "amount": amount,
            "currency": currency,
            "status": "processed",
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def refund_payment(self, purchase_id: str, reason: str = "Customer request") -> Dict[str, Any]:
        """
        Process refund through payment provider
        """
        try:
            # Get purchase
            purchase = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.purchase_id == purchase_id
            ).first()
            
            if not purchase:
                return {"success": False, "error": "Purchase not found"}
            
            if not purchase.payment_transaction_id:
                return {"success": False, "error": "No payment transaction found"}
            
            # Process refund through provider
            refund_result = self._process_refund_with_provider(
                purchase.payment_transaction_id,
                purchase.total_amount,
                purchase.currency,
                reason
            )
            
            # Update purchase record
            if refund_result["success"]:
                purchase.meta_data = purchase.meta_data or {}
                purchase.meta_data["refund_result"] = refund_result
            
            self.db.commit()
            
            return refund_result
            
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _process_refund_with_provider(self, transaction_id: str, amount: float,
                                    currency: str, reason: str) -> Dict[str, Any]:
        """
        Process refund with payment provider
        """
        # Mock refund processing
        refund_id = f"refund_{uuid.uuid4().hex}"
        
        return {
            "success": True,
            "refund_id": refund_id,
            "original_transaction_id": transaction_id,
            "amount": amount,
            "currency": currency,
            "reason": reason,
            "processed_at": datetime.utcnow().isoformat(),
            "status": "succeeded"
        }
    
    def validate_payment_method(self, payment_method_id: int) -> Dict[str, Any]:
        """
        Validate a payment method
        """
        try:
            payment_method = self.db.query(PaymentMethodModel).filter(
                PaymentMethodModel.id == payment_method_id
            ).first()
            
            if not payment_method:
                return {"valid": False, "error": "Payment method not found"}
            
            if not payment_method.is_active:
                return {"valid": False, "error": "Payment method is inactive"}
            
            if not payment_method.verified:
                return {"valid": False, "error": "Payment method not verified"}
            
            # Additional validation based on provider
            validation_result = self._validate_with_provider(payment_method)
            
            return {
                "valid": True,
                "payment_method": {
                    "id": payment_method.id,
                    "type": payment_method.type,
                    "provider": payment_method.provider,
                    "is_default": payment_method.is_default,
                    "verified": payment_method.verified,
                    "card_last4": payment_method.card_last4,
                    "card_brand": payment_method.card_brand
                },
                "provider_validation": validation_result
            }
            
        except Exception as e:
            logger.error(f"Error validating payment method: {e}")
            return {"valid": False, "error": str(e)}
    
    def _validate_with_provider(self, payment_method: PaymentMethodModel) -> Dict[str, Any]:
        """
        Validate payment method with provider
        """
        provider = payment_method.provider.lower()
        
        if provider == "stripe":
            return self._validate_stripe_payment_method(payment_method)
        elif provider == "paypal":
            return self._validate_paypal_payment_method(payment_method)
        else:
            return {"status": "validated", "provider": provider}
    
    def _validate_stripe_payment_method(self, payment_method: PaymentMethodModel) -> Dict[str, Any]:
        """
        Mock Stripe payment method validation
        """
        return {
            "status": "valid",
            "provider": "stripe",
            "brand": payment_method.card_brand,
            "last4": payment_method.card_last4,
            "exp_month": payment_method.card_exp_month,
            "exp_year": payment_method.card_exp_year,
            "validated_at": datetime.utcnow().isoformat()
        }
    
    def _validate_paypal_payment_method(self, payment_method: PaymentMethodModel) -> Dict[str, Any]:
        """
        Mock PayPal payment method validation
        """
        return {
            "status": "valid",
            "provider": "paypal",
            "email": f"user{payment_method.user_id}@paypal.com",
            "verified": True,
            "validated_at": datetime.utcnow().isoformat()
        }
    
    def get_payment_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get payment analytics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get payment data from purchases
        purchases = self.db.query(CreditPurchaseTransaction).filter(
            CreditPurchaseTransaction.created_at >= start_date,
            CreditPurchaseTransaction.created_at <= end_date
        ).all()
        
        if not purchases:
            return {
                "period_days": days,
                "total_payments": 0,
                "successful_payments": 0,
                "failed_payments": 0,
                "total_revenue": 0,
                "provider_breakdown": {}
            }
        
        total_payments = len(purchases)
        successful_payments = len([p for p in purchases if p.payment_status == "succeeded"])
        failed_payments = len([p for p in purchases if p.payment_status == "failed"])
        total_revenue = sum(p.total_amount for p in purchases if p.payment_status == "succeeded")
        
        # Provider breakdown
        provider_breakdown = {}
        for purchase in purchases:
            # Get payment method provider (would need to join with payment_methods table)
            provider = "unknown"  # Placeholder
            
            if provider not in provider_breakdown:
                provider_breakdown[provider] = {
                    "total_payments": 0,
                    "successful_payments": 0,
                    "total_revenue": 0
                }
            
            provider_breakdown[provider]["total_payments"] += 1
            if purchase.payment_status == "succeeded":
                provider_breakdown[provider]["successful_payments"] += 1
                provider_breakdown[provider]["total_revenue"] += purchase.total_amount
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "success_rate": (successful_payments / total_payments * 100) if total_payments > 0 else 0,
            "total_revenue": total_revenue,
            "average_payment_value": total_revenue / successful_payments if successful_payments > 0 else 0,
            "provider_breakdown": provider_breakdown
        }


# Utility functions
def get_payment_integration_service(db: Session = None) -> PaymentIntegrationService:
    """
    Get PaymentIntegrationService instance
    """
    if db is None:
        db = next(get_db())
    return PaymentIntegrationService(db)


def process_credit_payment(purchase_id: str, payment_method_id: int, amount: float, 
                         db: Session = None) -> Dict[str, Any]:
    """
    Quick function to process credit purchase payment
    """
    service = get_payment_integration_service(db)
    return service.process_payment(purchase_id, payment_method_id, amount)