"""
Request Builder - Standardizes proxy request construction

This module handles the standardization of proxy requests, ensuring consistent
request formatting, endpoint mapping, and parameter handling across all services.
"""

import os
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class RequestBuilder:
    """
    Builder for standardized proxy requests.
    
    Features:
    - Standardizes request format across services
    - Handles endpoint mapping and transformation
    - Validates request parameters
    - Manages request metadata and tracing
    """
    
    def __init__(self):
        """Initialize request builder"""
        
        # Service endpoint mappings
        self.endpoint_mappings = {
            "llm": {
                "extract_fields": "/llm/extract",
                "validate_fields": "/llm/validate",
                "chat": "/llm/chat",
                "embeddings": "/llm/embeddings"
            },
            "ocr": {
                "extract_text": "/ocr/extract",
                "process": "/ocr/process",
                "status": "/ocr/status",
                "analyze": "/ocr/analyze"
            },
            "toconline": {
                "extract_documents": "/toconline/extract",
                "search": "/toconline/search",
                "authenticate": "/toconline/auth"
            },
            "stripe": {
                "create_customer": "/stripe/customers",
                "create_payment_intent": "/stripe/payment-intents",
                "confirm_payment": "/stripe/confirm-payment",
                "create_refund": "/stripe/refunds",
                "webhook": "/stripe/webhook"
            },
            "paypal": {
                "create_order": "/paypal/orders",
                "capture_order": "/paypal/orders/{id}/capture",
                "refund": "/paypal/refunds",
                "webhook": "/paypal/webhook"
            },
            "coinbase": {
                "create_charge": "/coinbase/charges",
                "get_charge": "/coinbase/charges/{id}",
                "cancel_charge": "/coinbase/charges/{id}/cancel",
                "webhook": "/coinbase/webhook"
            },
            "openai": {
                "chat_completions": "/openai/chat/completions",
                "embeddings": "/openai/embeddings",
                "images": "/openai/images"
            }
        }
    
    def build_request(
        self,
        service: str,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Build standardized request for proxy
        
        Args:
            service: Target service
            endpoint: API endpoint (can be mapped endpoint or raw path)
            method: HTTP method
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Standardized request dictionary
        """
        
        # Map endpoint if necessary
        mapped_endpoint = self._map_endpoint(service, endpoint)
        
        # Build base request
        request = {
            "method": method.upper(),
            "headers": self._build_headers(service, headers),
            "json": data if method.upper() in ["POST", "PUT", "PATCH"] else None,
            "params": self._clean_params(params) if params else None,
            "url": mapped_endpoint,
            "metadata": self._build_metadata(service, endpoint, method)
        }
        
        # Validate request
        self._validate_request(request, service, endpoint)
        
        logger.debug(f"Built request for {service}:{endpoint} -> {mapped_endpoint}")
        
        return request
    
    def _map_endpoint(self, service: str, endpoint: str) -> str:
        """Map endpoint to proxy endpoint"""
        
        # If endpoint starts with '/', it's already mapped
        if endpoint.startswith('/'):
            return endpoint
        
        # Try to find mapping
        service_mappings = self.endpoint_mappings.get(service, {})
        mapped = service_mappings.get(endpoint)
        
        if mapped:
            return mapped
        
        # If no mapping found, return the endpoint as-is
        # This allows for custom endpoints while maintaining backward compatibility
        return f"/{service}/{endpoint}" if not endpoint.startswith('/') else endpoint
    
    def _build_headers(self, service: str, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build standardized headers"""
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"Fernando-Proxy-Client/1.0",
            "X-Requested-With": "XMLHttpRequest",
            "X-Service": service
        }
        
        # Add service-specific headers
        service_headers = self._get_service_headers(service)
        headers.update(service_headers)
        
        # Add additional headers
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    def _get_service_headers(self, service: str) -> Dict[str, str]:
        """Get service-specific headers"""
        
        service_header_configs = {
            "stripe": {
                "X-Stripe-Version": "2023-10-16"
            },
            "paypal": {
                "X-PayPal-SDK": "fernando-platform",
                "Accept-Language": "pt-PT"
            },
            "coinbase": {
                "X-CC-Version": "2018-03-22"
            },
            "openai": {
                "X-OpenAI-Client": "fernando-platform"
            },
            "llm": {
                "Accept-Language": "pt-PT",
                "X-Document-Type": "invoice"
            },
            "ocr": {
                "X-Document-Type": "invoice",
                "X-OCR-Engine": "proxy-managed"
            },
            "toconline": {
                "X-Client": "fernando-platform",
                "Accept-Language": "pt-PT"
            }
        }
        
        return service_header_configs.get(service, {})
    
    def _build_metadata(self, service: str, endpoint: str, method: str) -> Dict[str, Any]:
        """Build request metadata for tracing and monitoring"""
        
        return {
            "service": service,
            "original_endpoint": endpoint,
            "method": method,
            "timestamp": self._get_timestamp(),
            "request_id": self._generate_request_id(),
            "client": "fernando-platform",
            "version": "1.0.0"
        }
    
    def _validate_request(self, request: Dict[str, Any], service: str, endpoint: str):
        """Validate request before sending"""
        
        # Validate method
        if request["method"] not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
            raise ValueError(f"Invalid HTTP method: {request['method']}")
        
        # Validate headers
        required_headers = ["Content-Type"]
        for header in required_headers:
            if header not in request["headers"]:
                raise ValueError(f"Missing required header: {header}")
        
        # Service-specific validations
        self._validate_service_request(service, request)
    
    def _validate_service_request(self, service: str, request: Dict[str, Any]):
        """Validate request for specific service"""
        
        validations = {
            "stripe": self._validate_stripe_request,
            "paypal": self._validate_paypal_request,
            "coinbase": self._validate_coinbase_request,
            "llm": self._validate_llm_request,
            "ocr": self._validate_ocr_request,
            "toconline": self._validate_toconline_request
        }
        
        validator = validations.get(service)
        if validator:
            validator(request)
    
    def _validate_stripe_request(self, request: Dict[str, Any]):
        """Validate Stripe-specific request"""
        
        if request["json"]:
            # Validate required fields for common endpoints
            if "amount" in str(request["json"]):
                if not isinstance(request["json"].get("amount"), (int, float)):
                    raise ValueError("Stripe amount must be a number")
            
            if "currency" in str(request["json"]):
                currency = request["json"].get("currency")
                if currency and not isinstance(currency, str):
                    raise ValueError("Stripe currency must be a string")
    
    def _validate_paypal_request(self, request: Dict[str, Any]):
        """Validate PayPal-specific request"""
        
        if request["json"]:
            # Validate required PayPal fields
            if "intent" in request["json"]:
                intent = request["json"]["intent"]
                if intent not in ["CAPTURE", "AUTHORIZE"]:
                    raise ValueError("PayPal intent must be CAPTURE or AUTHORIZE")
    
    def _validate_coinbase_request(self, request: Dict[str, Any]):
        """Validate Coinbase Commerce-specific request"""
        
        if request["json"]:
            # Validate Coinbase fields
            if "pricing_type" in request["json"]:
                pricing_type = request["json"]["pricing_type"]
                if pricing_type not in ["fixed_price", "no_price"]:
                    raise ValueError("Coinbase pricing_type must be fixed_price or no_price")
    
    def _validate_llm_request(self, request: Dict[str, Any]):
        """Validate LLM-specific request"""
        
        if request["json"]:
            # Validate LLM request
            if "text" not in request["json"]:
                raise ValueError("LLM request must include 'text' field")
            
            if "model" in request["json"]:
                model = request["json"]["model"]
                # Common model validation
                if model not in ["gpt-4", "gpt-3.5-turbo", "claude-3", "phi-4", "local"]:
                    logger.warning(f"Uncommon model: {model}")
    
    def _validate_ocr_request(self, request: Dict[str, Any]):
        """Validate OCR-specific request"""
        
        if request["json"]:
            # Validate OCR request
            required_fields = ["document_url", "image_path"]
            has_required = any(field in request["json"] for field in required_fields)
            
            if not has_required:
                raise ValueError(f"OCR request must include one of: {required_fields}")
            
            if "language" in request["json"]:
                language = request["json"]["language"]
                valid_languages = ["pt", "en", "es", "fr", "de"]
                if language not in valid_languages:
                    logger.warning(f"Uncommon language: {language}")
    
    def _validate_toconline_request(self, request: Dict[str, Any]):
        """Validate ToConline-specific request"""
        
        if request["json"]:
            # Validate ToConline request
            if "credentials" not in request["json"]:
                logger.warning("ToConline request should include credentials")
    
    def _clean_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate query parameters"""
        
        cleaned = {}
        for key, value in params.items():
            # Skip None values
            if value is None:
                continue
            
            # Convert complex objects to strings
            if isinstance(value, (dict, list)):
                cleaned[key] = json.dumps(value)
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())
    
    def add_endpoint_mapping(self, service: str, endpoint_name: str, endpoint_path: str):
        """Add custom endpoint mapping"""
        
        if service not in self.endpoint_mappings:
            self.endpoint_mappings[service] = {}
        
        self.endpoint_mappings[service][endpoint_name] = endpoint_path
        logger.info(f"Added endpoint mapping: {service}.{endpoint_name} -> {endpoint_path}")
    
    def remove_endpoint_mapping(self, service: str, endpoint_name: str):
        """Remove endpoint mapping"""
        
        if service in self.endpoint_mappings and endpoint_name in self.endpoint_mappings[service]:
            del self.endpoint_mappings[service][endpoint_name]
            logger.info(f"Removed endpoint mapping: {service}.{endpoint_name}")
    
    def get_endpoint_mapping(self, service: str, endpoint_name: str) -> Optional[str]:
        """Get endpoint mapping"""
        return self.endpoint_mappings.get(service, {}).get(endpoint_name)
    
    def list_endpoint_mappings(self, service: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """List all endpoint mappings"""
        
        if service:
            return {service: self.endpoint_mappings.get(service, {})}
        
        return self.endpoint_mappings


# Global request builder instance
_request_builder = None


def get_request_builder() -> RequestBuilder:
    """Get global request builder instance"""
    global _request_builder
    if _request_builder is None:
        _request_builder = RequestBuilder()
    return _request_builder


def reset_request_builder():
    """Reset global request builder (for testing)"""
    global _request_builder
    _request_builder = None