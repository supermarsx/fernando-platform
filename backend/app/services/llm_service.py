"""
Real LLM Service with OpenAI and Alternatives

This service provides production-ready LLM functionality for Portuguese document
field extraction using OpenAI API, Azure OpenAI, or local models.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
import requests
import time
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel, TelemetryMixin
from app.middleware.telemetry_decorators import (
    llm_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric, timer_metric
)
from app.services.proxy import get_proxy_client, ProxyClient
from app.services.credit_service import CreditService
from app.services.usage_tracking.llm_usage_tracker import LLMUsageTracker
from app.middleware.credit_validation import validate_credits, CreditValidationError
from app.models.credit import LLMModelType


class LLMService(TelemetryMixin):
    """
    Production LLM service supporting multiple backends:
    - OpenAI GPT-4/GPT-3.5
    - Azure OpenAI
    - Anthropic Claude
    - Local models (Ollama, llama.cpp)
    """
    
    def __init__(self, backend: str = "openai", db: Optional[Any] = None):
        self.backend = backend
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.api_endpoint = os.getenv("LLM_API_ENDPOINT")
        self.model = os.getenv("LLM_MODEL", "gpt-4")
        
        # Initialize proxy client
        self.proxy_client = get_proxy_client()
        
        # Initialize credit and usage tracking services
        self.db = db
        if db:
            self.credit_service = CreditService(db)
            self.usage_tracker = LLMUsageTracker(db, self.credit_service)
        else:
            self.credit_service = None
            self.usage_tracker = None
        
        self.log_telemetry_event(
            "llm.service_initialized", 
            TelemetryEvent.SYSTEM_STARTED,
            level=TelemetryLevel.INFO,
            metadata={"backend": backend, "model": self.model}
        )
        
        if backend == "openai":
            self._init_openai()
        elif backend == "azure":
            self._init_azure_openai()
        elif backend == "anthropic":
            self._init_anthropic()
        elif backend == "ollama":
            self._init_ollama()
    
    def _init_openai(self):
        """Initialize OpenAI"""
        if not self.api_key:
            print("OpenAI API key not configured. Using fallback mode.")
            self.available = False
            return
        
        try:
            import openai
            openai.api_key = self.api_key
            self.client = openai
            self.available = True
        except ImportError:
            print("OpenAI package not installed.")
            self.available = False
    
    def _init_azure_openai(self):
        """Initialize Azure OpenAI"""
        if not self.api_key or not self.api_endpoint:
            print("Azure OpenAI credentials not configured.")
            self.available = False
            return
        
        try:
            import openai
            openai.api_type = "azure"
            openai.api_key = self.api_key
            openai.api_base = self.api_endpoint
            openai.api_version = "2023-05-15"
            self.client = openai
            self.available = True
        except ImportError:
            print("OpenAI package not installed.")
            self.available = False
    
    def _init_anthropic(self):
        """Initialize Anthropic Claude"""
        if not self.api_key:
            print("Anthropic API key not configured.")
            self.available = False
            return
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = "claude-3-sonnet-20240229"
            self.available = True
        except ImportError:
            print("Anthropic package not installed.")
            self.available = False
    
    def _init_ollama(self):
        """Initialize Ollama (local)"""
        self.api_endpoint = self.api_endpoint or "http://localhost:11434"
        self.model = self.model or "llama2"
        self.available = True
    
    @llm_telemetry("extract_fields")
    def extract_fields(
        self, 
        text: str, 
        document_type: str = "invoice",
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured fields from text using LLM.
        
        Args:
            text: OCR-extracted text
            document_type: Type of document (invoice, receipt, etc.)
            user_id: User ID for credit tracking (optional)
            session_id: Session ID for usage tracking (optional)
            
        Returns:
            Dict containing extracted fields
        """
        start_time = time.time()
        
        # Validate credits before proceeding
        if self.credit_service and user_id:
            try:
                # Estimate tokens and cost for validation
                model_type = self._get_llm_model_type()
                prompt = self._get_extraction_prompt(text, document_type)
                estimated_prompt_tokens = self.usage_tracker.estimate_tokens(prompt, model_type)
                estimated_completion_tokens = self.usage_tracker.estimate_tokens("{}", model_type)
                
                estimated_cost, _ = self.credit_service.calculate_llm_cost(
                    model_type=model_type,
                    prompt_tokens=estimated_prompt_tokens,
                    completion_tokens=estimated_completion_tokens
                )
                
                # Validate credits
                validation_result = self.credit_service.validate_credit_balance(
                    user_id=user_id,
                    estimated_cost=estimated_cost,
                    operation_type="extract_fields",
                    service_type="llm",
                    model_type=model_type.value,
                    estimated_tokens=estimated_prompt_tokens + estimated_completion_tokens
                )
                
                if not validation_result.get("sufficient_credits", False):
                    raise CreditValidationError(
                        "Insufficient credits for LLM extraction",
                        validation_result.get("available_balance", 0),
                        estimated_cost
                    )
                
            except Exception as e:
                if isinstance(e, CreditValidationError):
                    raise
                else:
                    # Log credit validation error but continue
                    self.log_telemetry_event(
                        "llm.credit_validation_error",
                        TelemetryEvent.SYSTEM_EVENT,
                        level=TelemetryLevel.ERROR,
                        metadata={"error": str(e), "user_id": user_id}
                    )
        
        # Initialize usage tracking session
        if self.usage_tracker and session_id and user_id:
            self.usage_tracker.start_usage_session(
                session_id=session_id,
                user_id=user_id,
                model_type=self._get_llm_model_type().value,
                operation_type="extract_fields",
                context={"document_type": document_type, "text_length": len(text)}
            )
        
        if not hasattr(self, 'available') or not self.available:
            self.log_telemetry_event(
                "llm.extraction_failed", 
                TelemetryEvent.EXTRACTION_FAILED,
                level=TelemetryLevel.WARNING,
                metadata={"reason": "service_unavailable", "backend": self.backend}
            )
            return self._fallback_extraction(text, document_type)
        
        try:
            # Try using proxy client first
            result = asyncio.run(self._extract_via_proxy(text, document_type))
            
            # Fallback to direct API calls if proxy fails
            if not result.get("success", False):
                if self.backend == "openai" or self.backend == "azure":
                    result = self._extract_openai(text, document_type, user_id, session_id)
                elif self.backend == "anthropic":
                    result = self._extract_anthropic(text, document_type, user_id, session_id)
                elif self.backend == "ollama":
                    result = self._extract_ollama(text, document_type, user_id, session_id)
                else:
                    result = self._fallback_extraction(text, document_type)
            
            # Record success metrics
            processing_time = time.time() - start_time
            
            self.record_business_kpi(
                "llm.extraction.success.count", 
                1.0,
                {
                    "backend": self.backend,
                    "model": self.model,
                    "document_type": document_type,
                    "processing_time": processing_time
                }
            )
            
            self.log_telemetry_event(
                "llm.extraction_completed", 
                TelemetryEvent.EXTRACTION_COMPLETED,
                level=TelemetryLevel.INFO,
                metadata={
                    "backend": self.backend,
                    "model": self.model,
                    "document_type": document_type,
                    "processing_time": processing_time,
                    "confidence": result.get("confidence", 0.0),
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
            
            # Track usage and deduct credits
            if self.usage_tracker and session_id and user_id:
                self._track_extraction_usage(
                    session_id, user_id, processing_time, 
                    result.get("total_tokens", 0), result.get("total_cost", 0)
                )
            
            return result
            
        except Exception as e:
            # Record error metrics
            processing_time = time.time() - start_time
            
            self.record_business_kpi(
                "llm.extraction.error.count", 
                1.0,
                {
                    "backend": self.backend,
                    "model": self.model,
                    "document_type": document_type,
                    "error_type": type(e).__name__
                }
            )
            
            self.log_telemetry_event(
                "llm.extraction_error", 
                TelemetryEvent.EXTRACTION_FAILED,
                level=TelemetryLevel.ERROR,
                metadata={
                    "backend": self.backend,
                    "model": self.model,
                    "document_type": document_type,
                    "processing_time": processing_time,
                    "error_message": str(e),
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
            
            # Track failed usage (partial credit for attempt)
            if self.usage_tracker and session_id and user_id:
                self._track_extraction_usage(
                    session_id, user_id, processing_time, 
                    0, 0, success=False, error_message=str(e)
                )
            
            return self._fallback_extraction(text, document_type)
    
    def _get_llm_model_type(self) -> LLMModelType:
        """Convert backend/model string to LLMModelType enum"""
        model_mapping = {
            "gpt-4": LLMModelType.GPT4,
            "gpt-3.5-turbo": LLMModelType.GPT35_TURBO,
            "claude-3-sonnet": LLMModelType.CLAUDE_3_SONNET,
            "claude-3-haiku": LLMModelType.CLAUDE_3_HAIKU,
        }
        return model_mapping.get(self.model, LLMModelType.LOCAL_MODEL)
    
    def _track_extraction_usage(
        self,
        session_id: str,
        user_id: int,
        processing_time: float,
        total_tokens: int,
        total_cost: float,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Track LLM extraction usage and deduct credits"""
        try:
            if not self.usage_tracker or not self.credit_service:
                return
            
            # Start request tracking
            request_info = self.usage_tracker.track_request_start(
                session_id=session_id,
                prompt="Extraction prompt",
                request_params={"model": self.model, "backend": self.backend}
            )
            
            # Track completion
            completion_info = self.usage_tracker.track_request_complete(
                session_id=session_id,
                request_id=request_info["request_id"],
                response="Extraction response",
                completion_tokens=total_tokens,
                total_tokens=total_tokens,
                success=success,
                error_message=error_message,
                response_time_ms=int(processing_time * 1000)
            )
            
            # Finalize usage session
            self.usage_tracker.finalize_usage_session(
                session_id=session_id,
                user_id=user_id,
                resource_id=f"extraction_{session_id}",
                endpoint="extract_fields"
            )
            
        except Exception as e:
            self.log_telemetry_event(
                "llm.usage_tracking_error",
                TelemetryEvent.SYSTEM_EVENT,
                level=TelemetryLevel.ERROR,
                metadata={"error": str(e), "session_id": session_id, "user_id": user_id}
            )
    
    def _extract_openai(self, text: str, document_type: str, user_id: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract fields using OpenAI"""
        try:
            prompt = self._get_extraction_prompt(text, document_type)
            
            response = self.client.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from Portuguese invoices and financial documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                extracted_data = json.loads(result_text)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract from markdown code block
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0].strip()
                    extracted_data = json.loads(json_str)
                else:
                    raise
            
            extracted_data["backend"] = "openai"
            extracted_data["model"] = self.model
            extracted_data["confidence"] = 0.95
            
            return extracted_data
            
        except Exception as e:
            print(f"OpenAI extraction error: {e}")
            return self._fallback_extraction(text, document_type)
    
    def _extract_anthropic(self, text: str, document_type: str, user_id: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract fields using Anthropic Claude"""
        try:
            prompt = self._get_extraction_prompt(text, document_type)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                system="You are an expert at extracting structured data from Portuguese invoices and financial documents.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = message.content[0].text
            
            # Parse JSON response
            try:
                extracted_data = json.loads(result_text)
            except json.JSONDecodeError:
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0].strip()
                    extracted_data = json.loads(json_str)
                else:
                    raise
            
            extracted_data["backend"] = "anthropic"
            extracted_data["model"] = self.model
            extracted_data["confidence"] = 0.95
            
            return extracted_data
            
        except Exception as e:
            print(f"Anthropic extraction error: {e}")
            return self._fallback_extraction(text, document_type)
    
    def _extract_ollama(self, text: str, document_type: str, user_id: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract fields using Ollama (local)"""
        try:
            prompt = self._get_extraction_prompt(text, document_type)
            
            response = requests.post(
                f"{self.api_endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            
            result_text = response.json()["response"]
            
            # Parse JSON response
            try:
                extracted_data = json.loads(result_text)
            except json.JSONDecodeError:
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0].strip()
                    extracted_data = json.loads(json_str)
                else:
                    raise
            
            extracted_data["backend"] = "ollama"
            extracted_data["model"] = self.model
            extracted_data["confidence"] = 0.85
            
            return extracted_data
            
        except Exception as e:
            print(f"Ollama extraction error: {e}")
            return self._fallback_extraction(text, document_type)
    
    async def _extract_via_proxy(self, text: str, document_type: str) -> Dict[str, Any]:
        """Extract fields using proxy client"""
        try:
            request_data = {
                "text": text,
                "document_type": document_type,
                "model": self.model,
                "language": "portuguese"
            }
            
            response = await self.proxy_client.request(
                service="llm",
                endpoint="extract_fields",
                method="POST",
                data=request_data
            )
            
            if response.get("success"):
                # Transform proxy response to expected format
                result = {
                    "backend": response["data"].get("backend", "proxy"),
                    "model": response["data"].get("model", self.model),
                    "confidence": response["data"].get("confidence_avg", 0.95),
                    "fields": response["data"].get("fields", {})
                }
                
                # Flatten fields for backward compatibility
                for field_name, field_data in result["fields"].items():
                    result[field_name] = field_data.get("value")
                
                return result
            
            return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            print(f"Proxy extraction error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_extraction_prompt(self, text: str, document_type: str) -> str:
        """Generate extraction prompt"""
        if document_type == "invoice":
            return f"""Extract the following fields from this Portuguese invoice text and return ONLY a JSON object:

Text:
{text}

Extract these fields:
- supplier_name: Company/person issuing the invoice
- supplier_nif: Portuguese tax ID (NIF) of supplier
- supplier_address: Full address of supplier
- customer_name: Customer name
- customer_nif: Customer NIF
- invoice_number: Invoice/document number
- invoice_date: Date in format DD/MM/YYYY
- due_date: Payment due date
- subtotal: Subtotal before tax (number)
- vat_rate: VAT/IVA rate percentage (number)
- vat_amount: VAT/IVA amount (number)
- total: Total amount with VAT (number)
- currency: Currency code (usually EUR)
- line_items: Array of items with description, quantity, unit_price, total

Return ONLY valid JSON, no explanations. For numbers, use Portuguese format (1.234,56)."""
        else:
            return f"""Extract all relevant structured information from this Portuguese document and return as JSON.

Text:
{text}

Return ONLY valid JSON with appropriate fields."""
    
    def _fallback_extraction(self, text: str, document_type: str) -> Dict[str, Any]:
        """Fallback extraction using regex and rules"""
        import re
        from datetime import datetime
        
        # Extract common patterns from Portuguese invoices
        result = {
            "supplier_name": None,
            "supplier_nif": None,
            "customer_name": None,
            "customer_nif": None,
            "invoice_number": None,
            "invoice_date": None,
            "total": None,
            "currency": "EUR",
            "line_items": [],
            "backend": "fallback",
            "confidence": 0.70,
            "note": "Using rule-based extraction. Configure LLM_API_KEY for better accuracy."
        }
        
        # Extract NIFs (9 digits)
        nifs = re.findall(r'NIF[:\s]*(\d{9})', text, re.IGNORECASE)
        if len(nifs) >= 1:
            result["supplier_nif"] = nifs[0]
        if len(nifs) >= 2:
            result["customer_nif"] = nifs[1]
        
        # Extract dates (DD/MM/YYYY)
        dates = re.findall(r'(\d{2}/\d{2}/\d{4})', text)
        if dates:
            result["invoice_date"] = dates[0]
        
        # Extract invoice number
        invoice_match = re.search(r'(?:FATURA|INVOICE|RECIBO|RECEIPT)[:\s#]*([A-Z0-9/-]+)', text, re.IGNORECASE)
        if invoice_match:
            result["invoice_number"] = invoice_match.group(1)
        
        # Extract total amount
        total_match = re.search(r'(?:TOTAL|TOTALE)[:\s]*([\d.,]+)€?', text, re.IGNORECASE)
        if total_match:
            amount_str = total_match.group(1).replace('.', '').replace(',', '.')
            try:
                result["total"] = float(amount_str)
            except:
                pass
        
        # Extract company name (usually in first few lines)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            result["supplier_name"] = lines[0]
        
        return result


# Singleton instance
_llm_service = None

def get_llm_service(backend: str = None, db: Optional[Any] = None) -> LLMService:
    """Get LLM service instance"""
    global _llm_service
    if _llm_service is None:
        backend = backend or os.getenv("LLM_BACKEND", "openai")
        _llm_service = LLMService(backend=backend, db=db)
    return _llm_service
