"""
Cryptocurrency Payment Service

Handles cryptocurrency payments using Coinbase Commerce including:
- Bitcoin (BTC)
- Ethereum (ETH)
- USDT (Tether)
- Other supported cryptocurrencies

Features:
- Payment charge creation
- Real-time payment status tracking
- Webhook handling for payment events
- Automatic currency conversion
"""

import requests
import hmac
import hashlib
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.core.config import settings
from app.models.billing import Payment, PaymentStatus, PaymentMethod as PaymentMethodEnum
from app.middleware.telemetry_decorators import (
    payment_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric
)
from app.services.proxy import get_proxy_client


class CryptocurrencyService:
    """Service for cryptocurrency payment processing via Coinbase Commerce"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.COINBASE_COMMERCE_API_KEY
        self.webhook_secret = settings.COINBASE_COMMERCE_WEBHOOK_SECRET
        self.base_url = "https://api.commerce.coinbase.com"
        
        # Initialize proxy client
        self.proxy_client = get_proxy_client()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        return {
            "Content-Type": "application/json",
            "X-CC-Api-Key": self.api_key,
            "X-CC-Version": "2018-03-22"
        }
    
    # ============================================================================
    # CHARGE MANAGEMENT
    # ============================================================================
    
    @payment_telemetry("create_charge")
    def create_charge(
        self,
        amount: float,
        currency: str = "EUR",
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a cryptocurrency payment charge
        
        Returns charge details including payment addresses for each cryptocurrency
        """
        
        charge_data = {
            "name": name or "Invoice Payment",
            "description": description or "Payment for Fernando service",
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": f"{amount:.2f}",
                "currency": currency
            },
            "metadata": metadata or {},
            "redirect_url": redirect_url,
            "cancel_url": cancel_url
        }
        
        response = requests.post(
            f"{self.base_url}/charges",
            headers=self._get_headers(),
            json=charge_data
        )
        
        if response.status_code == 201:
            charge = response.json().get("data", {})
            
            return {
                "charge_id": charge.get("id"),
                "code": charge.get("code"),
                "hosted_url": charge.get("hosted_url"),
                "status": charge.get("timeline", [{}])[-1].get("status", "NEW"),
                "pricing": charge.get("pricing"),
                "payments": charge.get("payments", []),
                "expires_at": charge.get("expires_at"),
                "created_at": charge.get("created_at"),
                "addresses": charge.get("addresses", {})
            }
        else:
            raise Exception(f"Failed to create Coinbase charge: {response.text}")
    
    def get_charge(self, charge_id: str) -> Dict[str, Any]:
        """Get charge details and current status"""
        
        response = requests.get(
            f"{self.base_url}/charges/{charge_id}",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            charge = response.json().get("data", {})
            
            # Get latest status from timeline
            timeline = charge.get("timeline", [])
            latest_status = timeline[-1].get("status") if timeline else "UNKNOWN"
            
            return {
                "charge_id": charge.get("id"),
                "code": charge.get("code"),
                "status": latest_status,
                "pricing": charge.get("pricing"),
                "payments": charge.get("payments", []),
                "timeline": timeline,
                "metadata": charge.get("metadata", {})
            }
        else:
            raise Exception(f"Failed to get Coinbase charge: {response.text}")
    
    def cancel_charge(self, charge_id: str) -> Dict[str, Any]:
        """
        Cancel a pending charge
        
        Note: Can only cancel charges that haven't been paid
        """
        
        response = requests.post(
            f"{self.base_url}/charges/{charge_id}/cancel",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            charge = response.json().get("data", {})
            return {
                "charge_id": charge.get("id"),
                "status": "CANCELLED"
            }
        else:
            raise Exception(f"Failed to cancel Coinbase charge: {response.text}")
    
    def list_charges(
        self,
        limit: int = 25,
        starting_after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all charges with pagination"""
        
        params = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after
        
        response = requests.get(
            f"{self.base_url}/charges",
            headers=self._get_headers(),
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            raise Exception(f"Failed to list Coinbase charges: {response.text}")
    
    # ============================================================================
    # WEBHOOK HANDLING
    # ============================================================================
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify Coinbase Commerce webhook signature
        
        Coinbase uses HMAC SHA256 for webhook verification
        """
        
        webhook_secret = secret or self.webhook_secret
        
        if not webhook_secret:
            raise ValueError("Webhook secret not configured")
        
        # Compute expected signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid webhook signature")
        
        # Parse and return event
        event = json.loads(payload.decode())
        return event
    
    def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Coinbase Commerce webhook events
        
        Event types:
        - charge:created - New charge created
        - charge:confirmed - Payment confirmed on blockchain
        - charge:failed - Payment failed or expired
        - charge:delayed - Payment detected but not confirmed
        - charge:pending - Payment detected on blockchain
        - charge:resolved - Previously pending charge resolved
        """
        
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        if event_type == "charge:confirmed":
            return self._handle_charge_confirmed(event_data)
        
        elif event_type == "charge:failed":
            return self._handle_charge_failed(event_data)
        
        elif event_type == "charge:pending":
            return self._handle_charge_pending(event_data)
        
        elif event_type == "charge:resolved":
            return self._handle_charge_resolved(event_data)
        
        return {"status": "unhandled", "event_type": event_type}
    
    def _handle_charge_confirmed(self, charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle confirmed cryptocurrency payment"""
        
        charge_id = charge_data.get("id")
        code = charge_data.get("code")
        metadata = charge_data.get("metadata", {})
        pricing = charge_data.get("pricing", {})
        payments = charge_data.get("payments", [])
        
        # Extract metadata
        invoice_id = metadata.get("invoice_id")
        user_id = metadata.get("user_id")
        
        if not invoice_id or not user_id:
            return {"status": "skipped", "reason": "missing metadata"}
        
        # Get payment amount in local currency
        local_amount = float(pricing.get("local", {}).get("amount", 0))
        currency = pricing.get("local", {}).get("currency", "EUR")
        
        # Determine cryptocurrency used
        crypto_currency = "UNKNOWN"
        if payments:
            first_payment = payments[0]
            crypto_currency = first_payment.get("value", {}).get("crypto", {}).get("currency", "UNKNOWN")
        
        # Map cryptocurrency to payment method enum
        payment_method_map = {
            "BTC": PaymentMethodEnum.BITCOIN,
            "ETH": PaymentMethodEnum.ETHEREUM,
            "USDT": PaymentMethodEnum.USDT
        }
        payment_method = payment_method_map.get(crypto_currency, PaymentMethodEnum.CRYPTOCURRENCY)
        
        from app.models.billing import Invoice
        
        # Create payment record
        payment = Payment(
            payment_id=f"crypto_{code}",
            invoice_id=int(invoice_id),
            user_id=int(user_id),
            amount=local_amount,
            currency=currency,
            status=PaymentStatus.SUCCEEDED,
            payment_method=payment_method,
            transaction_id=charge_id,
            processed_at=datetime.utcnow(),
            metadata={
                "cryptocurrency": crypto_currency,
                "charge_code": code,
                "payments": payments
            }
        )
        
        self.db.add(payment)
        
        # Update invoice
        invoice = self.db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
        if invoice:
            invoice.amount_paid = local_amount
            invoice.amount_due = 0
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "status": "processed",
            "charge_id": charge_id,
            "amount": local_amount,
            "cryptocurrency": crypto_currency
        }
    
    def _handle_charge_failed(self, charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed cryptocurrency payment"""
        
        charge_id = charge_data.get("id")
        code = charge_data.get("code")
        metadata = charge_data.get("metadata", {})
        
        # Extract metadata
        invoice_id = metadata.get("invoice_id")
        user_id = metadata.get("user_id")
        
        if invoice_id and user_id:
            # Create failed payment record
            payment = Payment(
                payment_id=f"crypto_{code}",
                invoice_id=int(invoice_id),
                user_id=int(user_id),
                amount=0,  # Amount not paid
                currency="EUR",
                status=PaymentStatus.FAILED,
                payment_method=PaymentMethodEnum.CRYPTOCURRENCY,
                transaction_id=charge_id,
                failed_at=datetime.utcnow(),
                failure_reason="Charge expired or payment failed"
            )
            
            self.db.add(payment)
            self.db.commit()
        
        return {"status": "processed", "charge_id": charge_id}
    
    def _handle_charge_pending(self, charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pending cryptocurrency payment (detected but not confirmed)"""
        
        charge_id = charge_data.get("id")
        code = charge_data.get("code")
        
        # Update payment status to processing if exists
        payment = self.db.query(Payment).filter(
            Payment.payment_id == f"crypto_{code}"
        ).first()
        
        if payment:
            payment.status = PaymentStatus.PROCESSING
            self.db.commit()
        
        return {"status": "processed", "charge_id": charge_id}
    
    def _handle_charge_resolved(self, charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resolved charge (pending charge that got confirmed or failed)"""
        
        # Check final status and route to appropriate handler
        timeline = charge_data.get("timeline", [])
        latest_status = timeline[-1].get("status") if timeline else "UNKNOWN"
        
        if latest_status == "COMPLETED":
            return self._handle_charge_confirmed(charge_data)
        elif latest_status in ["EXPIRED", "CANCELED"]:
            return self._handle_charge_failed(charge_data)
        
        return {"status": "unhandled", "final_status": latest_status}
    
    # ============================================================================
    # PRICING AND CONVERSION
    # ============================================================================
    
    def get_exchange_rates(self) -> Dict[str, Any]:
        """
        Get current cryptocurrency exchange rates
        
        Returns rates for major cryptocurrencies
        """
        
        response = requests.get(
            f"{self.base_url}/exchange-rates",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            return {
                "currency": data.get("currency"),
                "rates": data.get("rates", {})
            }
        else:
            raise Exception(f"Failed to get exchange rates: {response.text}")
    
    def convert_fiat_to_crypto(
        self,
        amount: float,
        from_currency: str = "EUR",
        to_cryptocurrency: str = "BTC"
    ) -> Dict[str, Any]:
        """
        Convert fiat currency amount to cryptocurrency amount
        
        Returns approximate cryptocurrency amount based on current rates
        """
        
        rates = self.get_exchange_rates()
        
        # Get rate for target cryptocurrency
        crypto_rate = rates.get("rates", {}).get(to_cryptocurrency)
        if not crypto_rate:
            raise ValueError(f"Exchange rate not available for {to_cryptocurrency}")
        
        # Convert
        crypto_amount = amount / float(crypto_rate)
        
        return {
            "fiat_amount": amount,
            "fiat_currency": from_currency,
            "crypto_amount": crypto_amount,
            "cryptocurrency": to_cryptocurrency,
            "exchange_rate": crypto_rate
        }
    
    # ============================================================================
    # INTEGRATED INVOICE PAYMENT
    # ============================================================================
    
    def pay_invoice_with_crypto(
        self,
        invoice_id: int,
        user_id: int,
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create cryptocurrency charge for invoice payment
        
        Returns charge details with hosted payment page URL
        """
        
        from app.services.billing_service import BillingService
        billing_service = BillingService(self.db)
        
        invoice = billing_service.get_invoice(invoice_id, user_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status == 'paid':
            raise ValueError("Invoice already paid")
        
        # Create cryptocurrency charge
        charge = self.create_charge(
            amount=invoice.amount_due,
            currency=invoice.currency,
            name=f"Invoice {invoice.invoice_number}",
            description=f"Payment for invoice {invoice.invoice_number}",
            metadata={
                "invoice_id": str(invoice_id),
                "user_id": str(user_id),
                "invoice_number": invoice.invoice_number
            },
            redirect_url=redirect_url,
            cancel_url=cancel_url
        )
        
        return charge
    
    async def _process_via_proxy(
        self,
        operation: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process cryptocurrency operations via proxy client"""
        try:
            request_data = data or {}
            request_data["operation"] = operation
            
            response = await self.proxy_client.request(
                service="coinbase",
                endpoint=f"coinbase/{operation}",
                method="POST",
                data=request_data
            )
            
            if response.get("success"):
                return response["data"]
            
            return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            print(f"Coinbase proxy operation error: {e}")
            return {"success": False, "error": str(e)}
