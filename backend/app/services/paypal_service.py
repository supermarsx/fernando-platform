"""
PayPal Payment Service

Handles PayPal payment processing including:
- Order creation and capture
- Express Checkout integration
- Billing agreements for recurring payments
- Webhook handling
- Refund processing
"""

import requests
import base64
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json
import hashlib
import hmac

from app.core.config import settings
from app.models.billing import Payment, PaymentStatus, PaymentMethod as PaymentMethodEnum
from app.middleware.telemetry_decorators import (
    payment_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric
)
from app.services.proxy import get_proxy_client


class PayPalService:
    """Service for PayPal payment gateway integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.mode = settings.PAYPAL_MODE  # "sandbox" or "live"
        
        # Set API base URL based on mode
        if self.mode == "live":
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"
        
        # Initialize proxy client
        self.proxy_client = get_proxy_client()
        
        self._access_token = None
        self._token_expires_at = None
    
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    
    def get_access_token(self) -> str:
        """Get or refresh PayPal access token"""
        
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at:
                return self._access_token
        
        # Request new token
        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self._access_token = token_data["access_token"]
            # Token expires in seconds, cache for 95% of that time
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in * 0.95)
            return self._access_token
        else:
            raise Exception(f"Failed to get PayPal access token: {response.text}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_access_token()}"
        }
    
    # ============================================================================
    # ORDER MANAGEMENT
    # ============================================================================
    
    @payment_telemetry("create_order")
    def create_order(
        self,
        amount: float,
        currency: str = "EUR",
        description: Optional[str] = None,
        invoice_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a PayPal order for payment
        
        Returns order details including approval URL for customer
        """
        
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}"
                },
                "description": description or "Payment for invoice",
                "invoice_id": invoice_id,
                "custom_id": json.dumps(metadata) if metadata else None
            }],
            "application_context": {
                "return_url": f"{settings.APP_NAME}/payment/success",
                "cancel_url": f"{settings.APP_NAME}/payment/cancel",
                "brand_name": settings.APP_NAME,
                "user_action": "PAY_NOW"
            }
        }
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers=self._get_headers(),
            json=order_data
        )
        
        if response.status_code == 201:
            order = response.json()
            
            # Extract approval URL
            approval_url = next(
                (link["href"] for link in order.get("links", []) if link["rel"] == "approve"),
                None
            )
            
            return {
                "order_id": order["id"],
                "status": order["status"],
                "approval_url": approval_url,
                "amount": amount,
                "currency": currency
            }
        else:
            raise Exception(f"Failed to create PayPal order: {response.text}")
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get PayPal order details"""
        
        response = requests.get(
            f"{self.base_url}/v2/checkout/orders/{order_id}",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get PayPal order: {response.text}")
    
    @payment_telemetry("capture_order")
    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Capture (complete) a PayPal order after customer approval
        """
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers=self._get_headers()
        )
        
        if response.status_code == 201:
            capture_data = response.json()
            
            # Extract capture details
            purchase_unit = capture_data.get("purchase_units", [{}])[0]
            capture = purchase_unit.get("payments", {}).get("captures", [{}])[0]
            
            return {
                "capture_id": capture.get("id"),
                "status": capture.get("status"),
                "amount": float(capture.get("amount", {}).get("value", 0)),
                "currency": capture.get("amount", {}).get("currency_code"),
                "order_id": order_id
            }
        else:
            raise Exception(f"Failed to capture PayPal order: {response.text}")
    
    # ============================================================================
    # REFUND MANAGEMENT
    # ============================================================================
    
    @payment_telemetry("refund_capture")
    def refund_capture(
        self,
        capture_id: str,
        amount: Optional[float] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund a captured payment
        
        If amount is None, full refund is processed
        """
        
        refund_data = {}
        
        if amount:
            # Get original capture to determine currency
            capture = self.get_capture(capture_id)
            currency = capture.get("amount", {}).get("currency_code", "EUR")
            
            refund_data["amount"] = {
                "value": f"{amount:.2f}",
                "currency_code": currency
            }
        
        if note:
            refund_data["note_to_payer"] = note
        
        response = requests.post(
            f"{self.base_url}/v2/payments/captures/{capture_id}/refund",
            headers=self._get_headers(),
            json=refund_data if refund_data else None
        )
        
        if response.status_code == 201:
            refund = response.json()
            return {
                "refund_id": refund.get("id"),
                "status": refund.get("status"),
                "amount": float(refund.get("amount", {}).get("value", 0)),
                "currency": refund.get("amount", {}).get("currency_code")
            }
        else:
            raise Exception(f"Failed to refund PayPal capture: {response.text}")
    
    def get_capture(self, capture_id: str) -> Dict[str, Any]:
        """Get capture details"""
        
        response = requests.get(
            f"{self.base_url}/v2/payments/captures/{capture_id}",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get PayPal capture: {response.text}")
    
    # ============================================================================
    # BILLING AGREEMENTS (Recurring Payments)
    # ============================================================================
    
    def create_billing_agreement(
        self,
        billing_token: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a billing agreement for recurring payments
        """
        
        agreement_data = {
            "token_id": billing_token,
            "description": description or "Subscription billing agreement"
        }
        
        response = requests.post(
            f"{self.base_url}/v1/billing-agreements/agreement-tokens",
            headers=self._get_headers(),
            json=agreement_data
        )
        
        if response.status_code == 201:
            agreement = response.json()
            return {
                "agreement_id": agreement.get("id"),
                "status": agreement.get("state"),
                "approval_url": next(
                    (link["href"] for link in agreement.get("links", []) if link["rel"] == "approval_url"),
                    None
                )
            }
        else:
            raise Exception(f"Failed to create billing agreement: {response.text}")
    
    def cancel_billing_agreement(self, agreement_id: str) -> bool:
        """Cancel a billing agreement"""
        
        response = requests.post(
            f"{self.base_url}/v1/billing-agreements/agreements/{agreement_id}/cancel",
            headers=self._get_headers(),
            json={"note": "Customer requested cancellation"}
        )
        
        return response.status_code == 204
    
    # ============================================================================
    # WEBHOOK HANDLING
    # ============================================================================
    
    def verify_webhook(
        self,
        payload: bytes,
        headers: Dict[str, str],
        webhook_id: str
    ) -> Dict[str, Any]:
        """
        Verify PayPal webhook signature
        
        PayPal uses webhook verification API endpoint
        """
        
        # Extract required headers
        transmission_id = headers.get("PAYPAL-TRANSMISSION-ID")
        transmission_time = headers.get("PAYPAL-TRANSMISSION-TIME")
        cert_url = headers.get("PAYPAL-CERT-URL")
        transmission_sig = headers.get("PAYPAL-TRANSMISSION-SIG")
        auth_algo = headers.get("PAYPAL-AUTH-ALGO")
        
        # Verify webhook using PayPal API
        verify_data = {
            "transmission_id": transmission_id,
            "transmission_time": transmission_time,
            "cert_url": cert_url,
            "auth_algo": auth_algo,
            "transmission_sig": transmission_sig,
            "webhook_id": webhook_id,
            "webhook_event": json.loads(payload.decode())
        }
        
        response = requests.post(
            f"{self.base_url}/v1/notifications/verify-webhook-signature",
            headers=self._get_headers(),
            json=verify_data
        )
        
        if response.status_code == 200:
            verification = response.json()
            if verification.get("verification_status") == "SUCCESS":
                return json.loads(payload.decode())
            else:
                raise ValueError("Webhook verification failed")
        else:
            raise Exception(f"Failed to verify webhook: {response.text}")
    
    def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle PayPal webhook events
        
        Common event types:
        - PAYMENT.CAPTURE.COMPLETED
        - PAYMENT.CAPTURE.DENIED
        - PAYMENT.CAPTURE.REFUNDED
        - BILLING.SUBSCRIPTION.CREATED
        - BILLING.SUBSCRIPTION.CANCELLED
        """
        
        event_type = event.get("event_type")
        resource = event.get("resource", {})
        
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            # Handle successful payment
            return self._handle_payment_completed(resource)
        
        elif event_type == "PAYMENT.CAPTURE.DENIED":
            # Handle failed payment
            return self._handle_payment_failed(resource)
        
        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            # Handle refund
            return self._handle_payment_refunded(resource)
        
        elif event_type in ["BILLING.SUBSCRIPTION.CREATED", "BILLING.SUBSCRIPTION.ACTIVATED"]:
            # Handle subscription activation
            return self._handle_subscription_activated(resource)
        
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            # Handle subscription cancellation
            return self._handle_subscription_cancelled(resource)
        
        return {"status": "unhandled", "event_type": event_type}
    
    def _handle_payment_completed(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed payment webhook"""
        
        capture_id = resource.get("id")
        amount = float(resource.get("amount", {}).get("value", 0))
        currency = resource.get("amount", {}).get("currency_code", "EUR")
        custom_data = resource.get("custom_id")
        
        # Extract metadata
        metadata = json.loads(custom_data) if custom_data else {}
        invoice_id = metadata.get("invoice_id")
        user_id = metadata.get("user_id")
        
        if invoice_id and user_id:
            from app.models.billing import Invoice
            
            # Create payment record
            payment = Payment(
                payment_id=f"paypal_{capture_id}",
                invoice_id=int(invoice_id),
                user_id=int(user_id),
                amount=amount,
                currency=currency,
                status=PaymentStatus.SUCCEEDED,
                payment_method=PaymentMethodEnum.PAYPAL,
                transaction_id=capture_id,
                processed_at=datetime.utcnow()
            )
            
            self.db.add(payment)
            
            # Update invoice
            invoice = self.db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
            if invoice:
                invoice.amount_paid = amount
                invoice.amount_due = 0
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
            
            self.db.commit()
        
        return {"status": "processed", "capture_id": capture_id}
    
    def _handle_payment_failed(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment webhook"""
        return {"status": "processed", "event": "payment_failed"}
    
    def _handle_payment_refunded(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refund webhook"""
        return {"status": "processed", "event": "payment_refunded"}
    
    def _handle_subscription_activated(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription activation webhook"""
        return {"status": "processed", "event": "subscription_activated"}
    
    def _handle_subscription_cancelled(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription cancellation webhook"""
        return {"status": "processed", "event": "subscription_cancelled"}
    
    # ============================================================================
    # INTEGRATED INVOICE PAYMENT
    # ============================================================================
    
    def pay_invoice_with_paypal(
        self,
        invoice_id: int,
        user_id: int,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create PayPal order for invoice payment
        
        Returns order details with approval URL for customer redirect
        """
        
        from app.services.billing_service import BillingService
        billing_service = BillingService(self.db)
        
        invoice = billing_service.get_invoice(invoice_id, user_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status == 'paid':
            raise ValueError("Invoice already paid")
        
        # Create PayPal order
        order = self.create_order(
            amount=invoice.amount_due,
            currency=invoice.currency,
            description=f"Payment for invoice {invoice.invoice_number}",
            invoice_id=invoice.invoice_number,
            metadata={
                "invoice_id": str(invoice_id),
                "user_id": str(user_id)
            }
        )
        
        return order
    
    async def _process_via_proxy(
        self,
        operation: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process PayPal operations via proxy client"""
        try:
            request_data = data or {}
            request_data["operation"] = operation
            
            response = await self.proxy_client.request(
                service="paypal",
                endpoint=f"paypal/{operation}",
                method="POST",
                data=request_data
            )
            
            if response.get("success"):
                return response["data"]
            
            return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            print(f"PayPal proxy operation error: {e}")
            return {"success": False, "error": str(e)}
