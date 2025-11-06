from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import stripe
import requests
import json

app = FastAPI(title="Stripe Payment Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe with server-side API key
stripe.api_key = "sk_test_mock_key"  # In production, this would be set from environment

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "eur"
    description: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class CustomerRequest(BaseModel):
    email: str
    name: str
    metadata: Optional[Dict[str, str]] = None

class RefundRequest(BaseModel):
    payment_intent_id: str
    amount: Optional[float] = None
    reason: Optional[str] = None

@app.post("/stripe/payment-intents")
async def create_payment_intent(request: PaymentIntentRequest):
    """Create Stripe payment intent through proxy"""
    try:
        # In production, this would call the real Stripe API
        payment_intent = {
            "id": "pi_mock_123456789",
            "object": "payment_intent",
            "amount": int(request.amount * 100),  # Convert to cents
            "currency": request.currency,
            "status": "requires_payment_method",
            "description": request.description or "Invoice payment",
            "metadata": request.metadata or {}
        }
        
        return {
            "success": True,
            "data": payment_intent
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stripe/customers")
async def create_customer(request: CustomerRequest):
    """Create Stripe customer through proxy"""
    try:
        customer = {
            "id": "cus_mock_123456789",
            "object": "customer",
            "email": request.email,
            "name": request.name,
            "metadata": request.metadata or {}
        }
        
        return {
            "success": True,
            "data": customer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stripe/refunds")
async def create_refund(request: RefundRequest):
    """Create Stripe refund through proxy"""
    try:
        refund = {
            "id": "re_mock_123456789",
            "object": "refund",
            "payment_intent": request.payment_intent_id,
            "amount": int((request.amount or 1000) * 100),  # Convert to cents
            "reason": request.reason or "requested_by_customer",
            "status": "succeeded"
        }
        
        return {
            "success": True,
            "data": refund
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stripe/{payment_intent_id}")
async def get_payment_intent(payment_intent_id: str):
    """Get Stripe payment intent"""
    try:
        payment_intent = {
            "id": payment_intent_id,
            "object": "payment_intent",
            "amount": 100000,  # 1000.00 in cents
            "currency": "eur",
            "status": "succeeded"
        }
        
        return {
            "success": True,
            "data": payment_intent
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stripe/webhook")
async def stripe_webhook(payload: Dict[str, Any]):
    """Handle Stripe webhooks through proxy"""
    try:
        # In production, verify webhook signature and handle events
        event_type = payload.get("type", "unknown")
        
        return {
            "success": True,
            "data": {
                "event_id": "evt_mock_123456789",
                "type": event_type,
                "processed": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "stripe-proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stripe_proxy:app", host="0.0.0.0", port=8003, reload=True)