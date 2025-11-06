from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import json

app = FastAPI(title="PayPal Payment Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderRequest(BaseModel):
    amount: float
    currency: str = "EUR"
    description: Optional[str] = None
    invoice_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CaptureRequest(BaseModel):
    order_id: str

class RefundRequest(BaseModel):
    capture_id: str
    amount: Optional[float] = None
    note: Optional[str] = None

@app.post("/paypal/orders")
async def create_order(request: OrderRequest):
    """Create PayPal order through proxy"""
    try:
        order = {
            "id": "PAYPAL_ORDER_MOCK_123456789",
            "status": "CREATED",
            "purchase_units": [{
                "amount": {
                    "currency_code": request.currency,
                    "value": f"{request.amount:.2f}"
                },
                "description": request.description or "Invoice payment",
                "invoice_id": request.invoice_id
            }],
            "links": [{
                "href": "https://www.paypal.com/checkoutnow?token=mock_token",
                "rel": "approve"
            }]
        }
        
        return {
            "success": True,
            "data": order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paypal/orders/{order_id}/capture")
async def capture_order(order_id: str, request: CaptureRequest):
    """Capture PayPal order through proxy"""
    try:
        capture = {
            "id": "CAPTURE_MOCK_123456789",
            "status": "COMPLETED",
            "purchase_units": [{
                "payments": {
                    "captures": [{
                        "id": "CAPTURE_MOCK_123456789",
                        "status": "COMPLETED",
                        "amount": {
                            "value": "100.00",
                            "currency_code": "EUR"
                        }
                    }]
                }
            }]
        }
        
        return {
            "success": True,
            "data": capture
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paypal/refunds")
async def create_refund(request: RefundRequest):
    """Create PayPal refund through proxy"""
    try:
        refund = {
            "id": "REFUND_MOCK_123456789",
            "status": "COMPLETED",
            "amount": {
                "value": f"{request.amount or 100.00:.2f}",
                "currency_code": "EUR"
            },
            "note_to_payer": request.note or "Refund for invoice payment"
        }
        
        return {
            "success": True,
            "data": refund
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/paypal/orders/{order_id}")
async def get_order(order_id: str):
    """Get PayPal order details"""
    try:
        order = {
            "id": order_id,
            "status": "COMPLETED",
            "purchase_units": [{
                "amount": {
                    "currency_code": "EUR",
                    "value": "100.00"
                }
            }]
        }
        
        return {
            "success": True,
            "data": order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/paypal/captures/{capture_id}")
async def get_capture(capture_id: str):
    """Get PayPal capture details"""
    try:
        capture = {
            "id": capture_id,
            "status": "COMPLETED",
            "amount": {
                "value": "100.00",
                "currency_code": "EUR"
            }
        }
        
        return {
            "success": True,
            "data": capture
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paypal/webhook")
async def paypal_webhook(payload: Dict[str, Any]):
    """Handle PayPal webhooks through proxy"""
    try:
        event_type = payload.get("event_type", "unknown")
        
        return {
            "success": True,
            "data": {
                "event_id": "PAYPAL_EVENT_MOCK_123456789",
                "event_type": event_type,
                "processed": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "paypal-proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("paypal_proxy:app", host="0.0.0.0", port=8004, reload=True)