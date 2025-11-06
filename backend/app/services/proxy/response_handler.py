"""
Response Handler - Standardizes proxy response processing

This module handles the processing of responses from proxy servers,
including error handling, response validation, and data transformation.
"""

import json
from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class ResponseHandler:
    """
    Handler for processing proxy responses.
    
    Features:
    - Standardizes response format across services
    - Handles errors and exceptions
    - Validates response data
    - Extracts metadata and telemetry
    """
    
    def __init__(self):
        """Initialize response handler"""
        
        # Success response status codes
        self.success_status_codes = {200, 201, 202, 203, 204}
        
        # Error response patterns
        self.error_patterns = {
            "validation_error": ["validation", "invalid", "required"],
            "authentication_error": ["unauthorized", "auth", "token"],
            "authorization_error": ["forbidden", "permission"],
            "not_found_error": ["not found", "404", "missing"],
            "rate_limit_error": ["rate limit", "too many", "429"],
            "server_error": ["internal error", "500", "502", "503", "server error"]
        }
    
    async def handle_response(
        self,
        response: httpx.Response,
        service: str,
        endpoint: str
    ) -> Dict[str, Any]:
        """
        Handle HTTP response from proxy server
        
        Args:
            response: HTTP response object
            service: Service name
            endpoint: API endpoint
            
        Returns:
            Processed response data
        """
        
        # Basic response info
        response_info = {
            "status_code": response.status_code,
            "success": response.status_code in self.success_status_codes,
            "service": service,
            "endpoint": endpoint,
            "timestamp": self._get_timestamp(),
            "response_time": getattr(response, "elapsed", None)
        }
        
        # Add headers to response info
        response_info["headers"] = dict(response.headers)
        
        try:
            # Parse response content
            content = await self._parse_response_content(response)
            response_info["content"] = content
            
            # Handle success response
            if response.status_code in self.success_status_codes:
                return self._handle_success_response(response_info, content)
            
            # Handle error response
            return self._handle_error_response(response_info, content)
        
        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            return self._handle_parsing_error(response_info, str(e))
    
    async def _parse_response_content(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse response content based on content type"""
        
        content_type = response.headers.get("content-type", "")
        
        try:
            if "application/json" in content_type:
                return response.json()
            elif "text/" in content_type:
                return {"text": response.text}
            else:
                # For binary content, return basic info
                return {
                    "binary_content": True,
                    "content_type": content_type,
                    "content_length": len(response.content)
                }
        
        except json.JSONDecodeError:
            # Fallback to text if JSON parsing fails
            try:
                return {"text": response.text}
            except:
                return {"raw_content": response.content.hex()}
    
    def _handle_success_response(self, response_info: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful response"""
        
        # Standardize success response
        result = {
            "success": True,
            "data": self._standardize_response_data(content),
            "metadata": {
                "status_code": response_info["status_code"],
                "service": response_info["service"],
                "endpoint": response_info["endpoint"],
                "timestamp": response_info["timestamp"],
                "response_time_ms": self._get_response_time_ms(response_info["response_time"])
            }
        }
        
        # Add specific service data
        service_processor = self._get_service_processor(response_info["service"])
        if service_processor:
            result = service_processor(result, content)
        
        return result
    
    def _handle_error_response(self, response_info: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error response"""
        
        # Determine error type
        error_type = self._classify_error(response_info, content)
        
        # Create error response
        error_response = {
            "success": False,
            "error": {
                "type": error_type,
                "message": self._extract_error_message(content),
                "code": response_info["status_code"],
                "details": content
            },
            "metadata": {
                "status_code": response_info["status_code"],
                "service": response_info["service"],
                "endpoint": response_info["endpoint"],
                "timestamp": response_info["timestamp"]
            }
        }
        
        # Add retry information if applicable
        if response_info["status_code"] in [429, 502, 503, 504]:
            error_response["error"]["retryable"] = True
            error_response["error"]["retry_after"] = self._extract_retry_after(response_info["headers"])
        
        return error_response
    
    def _handle_parsing_error(self, response_info: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Handle response parsing errors"""
        
        return {
            "success": False,
            "error": {
                "type": "parsing_error",
                "message": f"Failed to parse response: {error_message}",
                "code": 0
            },
            "metadata": {
                "status_code": response_info.get("status_code", 0),
                "service": response_info.get("service", "unknown"),
                "endpoint": response_info.get("endpoint", "unknown"),
                "timestamp": response_info.get("timestamp", self._get_timestamp())
            }
        }
    
    def _classify_error(self, response_info: Dict[str, Any], content: Dict[str, Any]) -> str:
        """Classify error type based on status code and content"""
        
        status_code = response_info["status_code"]
        message_text = self._extract_error_message(content).lower()
        
        # Status code based classification
        if status_code == 401:
            return "authentication_error"
        elif status_code == 403:
            return "authorization_error"
        elif status_code == 404:
            return "not_found_error"
        elif status_code == 422:
            return "validation_error"
        elif status_code == 429:
            return "rate_limit_error"
        elif status_code >= 500:
            return "server_error"
        
        # Message based classification for 4xx errors
        for error_type, patterns in self.error_patterns.items():
            if any(pattern in message_text for pattern in patterns):
                return error_type
        
        return "unknown_error"
    
    def _extract_error_message(self, content: Dict[str, Any]) -> str:
        """Extract error message from response content"""
        
        # Common error message fields
        message_fields = ["message", "error", "error_message", "detail", "errors"]
        
        for field in message_fields:
            if field in content:
                message = content[field]
                if isinstance(message, str):
                    return message
                elif isinstance(message, dict):
                    # Handle nested error objects
                    return str(message)
                elif isinstance(message, list):
                    return "; ".join(str(item) for item in message)
        
        # Fallback to content as string
        return str(content)
    
    def _extract_retry_after(self, headers: Dict[str, str]) -> Optional[int]:
        """Extract retry-after header value"""
        
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        
        return None
    
    def _standardize_response_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize response data format"""
        
        if not isinstance(content, dict):
            return {"data": content}
        
        # Remove common metadata fields
        standardized = {}
        
        for key, value in content.items():
            # Skip metadata fields
            if key in ["timestamp", "created_at", "updated_at", "id"]:
                continue
            
            standardized[key] = value
        
        return standardized
    
    def _get_response_time_ms(self, response_time) -> Optional[float]:
        """Get response time in milliseconds"""
        
        if not response_time:
            return None
        
        try:
            return response_time.total_seconds() * 1000
        except:
            return None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    def _get_service_processor(self, service: str):
        """Get service-specific response processor"""
        
        processors = {
            "stripe": self._process_stripe_response,
            "paypal": self._process_paypal_response,
            "coinbase": self._process_coinbase_response,
            "llm": self._process_llm_response,
            "ocr": self._process_ocr_response,
            "toconline": self._process_toconline_response
        }
        
        return processors.get(service)
    
    def _process_stripe_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process Stripe-specific response"""
        
        # Add Stripe-specific metadata
        if "id" in content:
            result["metadata"]["stripe_id"] = content["id"]
        
        if "object" in content:
            result["metadata"]["stripe_object"] = content["object"]
        
        return result
    
    def _process_paypal_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process PayPal-specific response"""
        
        # Add PayPal-specific metadata
        if "id" in content:
            result["metadata"]["paypal_id"] = content["id"]
        
        if "status" in content:
            result["metadata"]["paypal_status"] = content["status"]
        
        return result
    
    def _process_coinbase_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process Coinbase Commerce-specific response"""
        
        # Add Coinbase-specific metadata
        if "data" in content:
            data = content["data"]
            if "id" in data:
                result["metadata"]["coinbase_id"] = data["id"]
            
            if "code" in data:
                result["metadata"]["coinbase_code"] = data["code"]
        
        return result
    
    def _process_llm_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process LLM-specific response"""
        
        # Ensure consistent field structure
        if "fields" not in content and "text" in content:
            # Convert simple text response to fields format
            result["data"] = {
                "extracted_text": content["text"],
                "confidence": content.get("confidence", 0.95),
                "backend": content.get("backend", "proxy")
            }
        
        return result
    
    def _process_ocr_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process OCR-specific response"""
        
        # Ensure consistent OCR response format
        if "text" not in content and "result" in content:
            content.update(content.pop("result"))
        
        return result
    
    def _process_toconline_response(self, result: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """Process ToConline-specific response"""
        
        # Add ToConline-specific metadata
        if "documents" in content:
            result["metadata"]["document_count"] = len(content["documents"])
        
        return result
    
    def validate_response_schema(self, content: Dict[str, Any], service: str) -> bool:
        """Validate response schema for a service"""
        
        # This is a placeholder for response schema validation
        # In a production system, you might use JSON Schema or similar
        
        required_fields = {
            "stripe": ["id", "object"],
            "paypal": ["id", "status"],
            "coinbase": ["data", "timeline"],
            "llm": ["fields", "confidence_avg"],
            "ocr": ["text", "confidence"],
            "toconline": ["documents", "success"]
        }
        
        service_required = required_fields.get(service, [])
        if not service_required:
            return True
        
        return all(field in content for field in service_required)
    
    def extract_telemetry(self, response_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract telemetry data from response"""
        
        return {
            "service": response_info.get("service"),
            "endpoint": response_info.get("endpoint"),
            "status_code": response_info.get("status_code"),
            "success": response_info.get("success"),
            "response_time_ms": self._get_response_time_ms(response_info.get("response_time")),
            "timestamp": response_info.get("timestamp"),
            "content_length": len(str(response_info.get("content", "")))
        }


# Global response handler instance
_response_handler = None


def get_response_handler() -> ResponseHandler:
    """Get global response handler instance"""
    global _response_handler
    if _response_handler is None:
        _response_handler = ResponseHandler()
    return _response_handler


def reset_response_handler():
    """Reset global response handler (for testing)"""
    global _response_handler
    _response_handler = None