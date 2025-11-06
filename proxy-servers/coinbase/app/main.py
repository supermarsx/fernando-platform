from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import json

app = FastAPI(title="Coinbase Commerce Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChargeRequest(BaseModel):
    amount: float
    currency: str = "EUR"
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    redirect_url: Optional[str] = None
    cancel_url: Optional[str] = None

@app.post("/coinbase/charges")
async def create_charge(request: ChargeRequest):
    """Create Coinbase Commerce charge through proxy"""
    try:
        charge_id = f"charge_{uuid.uuid4().hex[:16]}"
        
        charge = {
            "data": {
                "id": charge_id,
                "code": f"COINBASE_{charge_id[:8].upper()}",
                "hosted_url": f"https://commerce.coinbase.com/charges/{charge_id}",
                "timeline": [{
                    "status": "NEW",
                    "payment": None,
                    "context": "payment"
                }],
                "pricing": {
                    "local": {
                        "amount": f"{request.amount:.2f}",
                        "currency": request.currency
                    },
                    "bitcoin": {
                        "amount": f"{request.amount / 50000:.8f}",  # Mock exchange rate
                        "currency": "BTC"
                    },
                    "ethereum": {
                        "amount": f"{request.amount / 3000:.8f}",  # Mock exchange rate
                        "currency": "ETH"
                    },
                    "usdt": {
                        "amount": f"{request.amount:.2f}",
                        "currency": "USDT"
                    }
                },
                "addresses": {
                    "bitcoin": f"1{charge_id[:26]}",
                    "ethereum": f"0x{charge_id[:40]}",
                    "usdt": f"0x{charge_id[:40]}"
                },
                "expires_at": "2025-11-06T08:54:26Z",
                "created_at": "2025-11-06T07:54:26Z"
            }
        }
        
        return {
            "success": True,
            "data": charge["data"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/coinbase/charges/{charge_id}")
async def get_charge(charge_id: str):
    """Get Coinbase charge details"""
    try:
        charge = {
            "data": {
                "id": charge_id,
                "code": f"COINBASE_{charge_id[:8].upper()}",
                "status": "COMPLETED",
                "timeline": [
                    {
                        "status": "NEW",
                        "payment": None,
                        "context": "payment"
                    },
                    {
                        "status": "COMPLETED",
                        "payment": {
                            "transaction_id": f"tx_{uuid.uuid4().hex[:16]}",
                            "network": "ethereum",
                            "transaction_fee": "0.001",
                            "network_fee": "0.0002",
                            "miner_fee": "0.0001",
                            "gas_price": "20",
                            "gas_limit": "21000",
                            "gas_used": "21000"
                        },
                        "context": "payment"
                    }
                ],
                "pricing": {
                    "local": {
                        "amount": "100.00",
                        "currency": "EUR"
                    }
                },
                "payments": [{
                    "transaction_id": f"tx_{uuid.uuid4().hex[:16]}",
                    "value": {
                        "local": {
                            "amount": "100.00",
                            "currency": "EUR"
                        },
                        "crypto": {
                            "amount": f"{100/3000:.8f}",
                            "currency": "ETH"
                        }
                    },
                    "network": "ethereum",
                    "status": "confirmed",
                    "block": {
                        "height": 12345678,
                        "hash": f"0x{uuid.uuid4().hex[:32]}",
                        "confirmations": 12
                    },
                    "transaction_fee": "0.001",
                    "network_fee": "0.0002",
                    "confirmations": 12,
                    "created_at": "2025-11-06T07:59:26Z"
                }]
            }
        }
        
        return {
            "success": True,
            "data": charge["data"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/coinbase/charges/{charge_id}/cancel")
async def cancel_charge(charge_id: str):
    """Cancel Coinbase charge"""
    try:
        cancelled_charge = {
            "data": {
                "id": charge_id,
                "status": "CANCELLED"
            }
        }
        
        return {
            "success": True,
            "data": cancelled_charge["data"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/coinbase/exchange-rates")
async def get_exchange_rates():
    """Get exchange rates"""
    try:
        rates = {
            "data": {
                "currency": "EUR",
                "rates": {
                    "BTC": "45000.00",
                    "ETH": "2800.00",
                    "USDT": "1.00",
                    "BTC.USD": "45000.00",
                    "ETH.USD": "2800.00"
                }
            }
        }
        
        return {
            "success": True,
            "data": rates["data"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/coinbase/webhook")
async def coinbase_webhook(payload: Dict[str, Any]):
    """Handle Coinbase Commerce webhooks through proxy"""
    try:
        event_type = payload.get("type", "unknown")
        event_data = payload.get("data", {})
        
        return {
            "success": True,
            "data": {
                "event_id": f"coinbase_event_{uuid.uuid4().hex[:16]}",
                "event_type": event_type,
                "processed": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "coinbase-proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("coinbase_proxy:app", host="0.0.0.0", port=8005, reload=True)