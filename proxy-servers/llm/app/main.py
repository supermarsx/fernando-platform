from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import os
import json

app = FastAPI(title="LLM Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractionRequest(BaseModel):
    text: str
    document_type: str = "invoice"
    language: str = "portuguese"
    model: str = "gpt-4"  # gpt-4, gpt-3.5-turbo, phi-4, local

class ExtractionResponse(BaseModel):
    fields: Dict[str, Dict[str, any]]
    confidence_avg: float
    model_used: str


@app.post("/llm/extract", response_model=ExtractionResponse)
async def extract_fields(request: ExtractionRequest):
    """Extract structured fields from text using LLM"""
    
    # Mock extraction (in production, call OpenAI or local LLM)
    extracted_fields = {
        "supplier_name": {
            "value": "TECNOLOGIA AVANCADA LDA",
            "confidence": 0.95
        },
        "supplier_nif": {
            "value": "123456789",
            "confidence": 0.98
        },
        "invoice_date": {
            "value": "15/10/2025",
            "confidence": 0.92
        },
        "invoice_number": {
            "value": "2025/1234",
            "confidence": 0.90
        },
        "subtotal": {
            "value": "875.00",
            "confidence": 0.94
        },
        "vat_amount": {
            "value": "201.25",
            "confidence": 0.93
        },
        "total_amount": {
            "value": "1076.25",
            "confidence": 0.96
        },
        "vat_rate": {
            "value": "23",
            "confidence": 0.91
        },
        "currency": {
            "value": "EUR",
            "confidence": 0.99
        }
    }
    
    # Calculate average confidence
    confidences = [field["confidence"] for field in extracted_fields.values()]
    avg_confidence = sum(confidences) / len(confidences)
    
    return ExtractionResponse(
        fields=extracted_fields,
        confidence_avg=avg_confidence,
        model_used=request.model
    )


@app.post("/llm/validate")
async def validate_fields(fields: Dict[str, any]):
    """Validate extracted fields"""
    validations = {}
    
    for field_name, field_data in fields.items():
        # Simple validation rules
        if field_name == "supplier_nif":
            value = str(field_data.get("value", ""))
            validations[field_name] = len(value) == 9 and value.isdigit()
        elif field_name in ["subtotal", "vat_amount", "total_amount"]:
            try:
                float(field_data.get("value", "0"))
                validations[field_name] = True
            except:
                validations[field_name] = False
        else:
            validations[field_name] = field_data.get("confidence", 0) > 0.7
    
    return {"validations": validations}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "llm-proxy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
