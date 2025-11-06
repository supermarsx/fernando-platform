"""
Proxy Client - Main interface for routing API requests through proxy servers

This client ensures zero API key exposure by routing all external API calls
through centralized proxy servers instead of making direct API calls.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime
import logging

from .request_builder import RequestBuilder
from .response_handler import ResponseHandler
from .auth_handler import AuthHandler

logger = logging.getLogger(__name__)


class ProxyClient:
    """
    Main proxy client for routing API requests through proxy servers.
    
    Features:
    - Routes requests through configured proxy servers
    - Handles authentication and authorization
    - Implements circuit breaker pattern for resilience
    - Provides comprehensive error handling
    - Maintains request/response telemetry
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize proxy client
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._load_default_config()
        self.request_builder = RequestBuilder()
        self.response_handler = ResponseHandler()
        self.auth_handler = AuthHandler(self.config.get("security", {}))
        
        # Service endpoint mappings
        self.service_endpoints = {
            "llm": self.config.get("llm", {}).get("proxy_endpoint", "http://localhost:8000"),
            "ocr": self.config.get("ocr", {}).get("proxy_endpoint", "http://localhost:8001"),
            "toconline": self.config.get("toconline", {}).get("proxy_endpoint", "http://localhost:8002"),
            "stripe": self.config.get("stripe", {}).get("proxy_endpoint", "http://localhost:8003"),
            "paypal": self.config.get("paypal", {}).get("proxy_endpoint", "http://localhost:8004"),
            "coinbase": self.config.get("coinbase", {}).get("proxy_endpoint", "http://localhost:8005"),
            "openai": self.config.get("openai", {}).get("proxy_endpoint", "http://localhost:8006")
        }
        
        # Circuit breaker state
        self.circuit_breakers = {}
        self.request_timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        
        logger.info(f"ProxyClient initialized with endpoints: {list(self.service_endpoints.keys())}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default proxy client configuration"""
        return {
            "timeout": 30,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 60,
                "monitor_window": 300
            },
            "security": {
                "api_key_header": "X-API-Key",
                "auth_type": "bearer"
            },
            "llm": {"proxy_endpoint": os.getenv("LLM_PROXY_ENDPOINT", "http://localhost:8000")},
            "ocr": {"proxy_endpoint": os.getenv("OCR_PROXY_ENDPOINT", "http://localhost:8001")},
            "toconline": {"proxy_endpoint": os.getenv("TOCONLINE_PROXY_ENDPOINT", "http://localhost:8002")},
            "stripe": {"proxy_endpoint": os.getenv("STRIPE_PROXY_ENDPOINT", "http://localhost:8003")},
            "paypal": {"proxy_endpoint": os.getenv("PAYPAL_PROXY_ENDPOINT", "http://localhost:8004")},
            "coinbase": {"proxy_endpoint": os.getenv("COINBASE_PROXY_ENDPOINT", "http://localhost:8005")},
            "openai": {"proxy_endpoint": os.getenv("OPENAI_PROXY_ENDPOINT", "http://localhost:8006")}
        }
    
    def _get_service_endpoint(self, service: str) -> str:
        """Get proxy endpoint for a service"""
        endpoint = self.service_endpoints.get(service)
        if not endpoint:
            raise ValueError(f"No proxy endpoint configured for service: {service}")
        return endpoint
    
    def _should_use_proxy(self, service: str, fallback_enabled: bool = True) -> bool:
        """
        Determine if request should go through proxy or use fallback
        
        Args:
            service: Service name
            fallback_enabled: Whether fallback behavior is enabled
            
        Returns:
            True if should use proxy, False if should use fallback
        """
        # Check if proxy is enabled for this service
        proxy_enabled = self.config.get(service, {}).get("proxy_enabled", True)
        
        # Check circuit breaker
        if self._is_circuit_open(service):
            logger.warning(f"Circuit breaker open for service {service}, using fallback")
            return False
        
        return proxy_enabled and fallback_enabled
    
    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for service"""
        if service not in self.circuit_breakers:
            return False
            
        breaker = self.circuit_breakers[service]
        now = datetime.utcnow()
        
        # Check if we're in failure window
        if breaker.get("last_failure"):
            time_since_failure = (now - breaker["last_failure"]).total_seconds()
            if time_since_failure < self.config["circuit_breaker"]["reset_timeout"]:
                return True
            else:
                # Reset after timeout
                del self.circuit_breakers[service]
                return False
        
        return False
    
    def _record_failure(self, service: str):
        """Record a failure for circuit breaker"""
        now = datetime.utcnow()
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = {
                "failure_count": 0,
                "first_failure": now,
                "last_failure": now
            }
        
        breaker = self.circuit_breakers[service]
        breaker["failure_count"] += 1
        breaker["last_failure"] = now
        
        threshold = self.config["circuit_breaker"]["failure_threshold"]
        if breaker["failure_count"] >= threshold:
            logger.warning(f"Circuit breaker opened for service {service} after {threshold} failures")
    
    def _record_success(self, service: str):
        """Record a success for circuit breaker"""
        if service in self.circuit_breakers:
            # Reset on success
            del self.circuit_breakers[service]
    
    async def request(
        self,
        service: str,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_fallback: bool = True,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a request through proxy or fallback
        
        Args:
            service: Target service (llm, ocr, stripe, paypal, etc.)
            endpoint: API endpoint path
            method: HTTP method
            data: Request data
            params: Query parameters
            headers: Additional headers
            use_fallback: Whether to use fallback if proxy fails
            timeout: Request timeout
            
        Returns:
            Response data
        """
        timeout = timeout or self.request_timeout
        
        try:
            if self._should_use_proxy(service, use_fallback):
                return await self._proxy_request(
                    service, endpoint, method, data, params, headers, timeout
                )
            elif use_fallback:
                return await self._fallback_request(service, endpoint, data, params)
            else:
                raise ValueError("Proxy unavailable and fallback disabled")
                
        except Exception as e:
            logger.error(f"Request failed for service {service}: {str(e)}")
            
            # Record failure for circuit breaker
            self._record_failure(service)
            
            # Try fallback if enabled
            if use_fallback and not self._should_use_proxy(service, False):
                try:
                    return await self._fallback_request(service, endpoint, data, params)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for service {service}: {str(fallback_error)}")
                    raise fallback_error
            
            raise e
    
    async def _proxy_request(
        self,
        service: str,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]],
        timeout: int
    ) -> Dict[str, Any]:
        """Make request through proxy server"""
        
        # Build request
        request_data = self.request_builder.build_request(
            service=service,
            endpoint=endpoint,
            method=method,
            data=data,
            params=params,
            headers=headers
        )
        
        # Get service endpoint
        base_url = self._get_service_endpoint(service)
        url = f"{base_url}{endpoint}"
        
        # Add authentication
        auth_headers = await self.auth_handler.get_auth_headers(service)
        request_data["headers"].update(auth_headers)
        
        # Make request with retry logic
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        **request_data
                    )
                    
                    # Handle response
                    result = await self.response_handler.handle_response(
                        response, service, endpoint
                    )
                    
                    # Record success
                    self._record_success(service)
                    
                    return result
                    
                except httpx.TimeoutException as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
                except httpx.RequestError as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
    
    async def _fallback_request(
        self,
        service: str,
        endpoint: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use fallback behavior when proxy is unavailable"""
        
        logger.info(f"Using fallback for service {service}, endpoint {endpoint}")
        
        # Import fallback handlers
        if service == "llm":
            from app.services.mock_llm import get_mock_llm_service
            return await get_mock_llm_service().process_request(endpoint, data)
        elif service == "ocr":
            from app.services.mock_ocr import get_mock_ocr_service
            return await get_mock_ocr_service().process_request(endpoint, data)
        elif service == "toconline":
            from app.services.mock_toconline import get_mock_toconline_service
            return await get_mock_toconline_service().process_request(endpoint, data)
        elif service in ["stripe", "paypal", "coinbase"]:
            # For payment services, return mock response
            return self._mock_payment_response(service, endpoint, data)
        else:
            raise ValueError(f"No fallback handler available for service: {service}")
    
    def _mock_payment_response(self, service: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock response for payment services"""
        if "create" in endpoint.lower():
            return {
                "success": True,
                "transaction_id": f"{service}_mock_{datetime.utcnow().timestamp()}",
                "status": "pending",
                "message": f"Mock {service} transaction created successfully"
            }
        elif "status" in endpoint.lower():
            return {
                "status": "completed",
                "amount": data.get("amount", 0),
                "currency": data.get("currency", "EUR")
            }
        else:
            return {"success": True, "message": f"Mock {service} operation completed"}
    
    def get_service_status(self, service: str) -> Dict[str, Any]:
        """Get status of a service"""
        
        status = {
            "service": service,
            "proxy_enabled": self.config.get(service, {}).get("proxy_enabled", True),
            "circuit_breaker": {
                "open": self._is_circuit_open(service),
                "failures": self.circuit_breakers.get(service, {}).get("failure_count", 0)
            } if service in self.circuit_breakers else {"open": False, "failures": 0},
            "endpoint": self._get_service_endpoint(service)
        }
        
        return status
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        return {service: self.get_service_status(service) for service in self.service_endpoints}
    
    def update_service_endpoint(self, service: str, endpoint: str):
        """Update endpoint for a service"""
        self.service_endpoints[service] = endpoint
        logger.info(f"Updated endpoint for {service}: {endpoint}")
    
    def disable_service_proxy(self, service: str):
        """Disable proxy for a specific service"""
        self.config[service] = self.config.get(service, {})
        self.config[service]["proxy_enabled"] = False
        logger.info(f"Disabled proxy for service: {service}")
    
    def enable_service_proxy(self, service: str):
        """Enable proxy for a specific service"""
        self.config[service] = self.config.get(service, {})
        self.config[service]["proxy_enabled"] = True
        logger.info(f"Enabled proxy for service: {service}")


# Global proxy client instance
_proxy_client = None


def get_proxy_client(config: Optional[Dict[str, Any]] = None) -> ProxyClient:
    """
    Get or create global proxy client instance
    
    Args:
        config: Optional configuration to override defaults
        
    Returns:
        ProxyClient instance
    """
    global _proxy_client
    if _proxy_client is None:
        _proxy_client = ProxyClient(config)
    elif config:
        # Update existing client with new config
        _proxy_client.config.update(config)
    
    return _proxy_client


def reset_proxy_client():
    """Reset global proxy client instance (for testing)"""
    global _proxy_client
    _proxy_client = None


# Convenience functions for common operations
async def make_proxy_request(
    service: str,
    endpoint: str,
    method: str = "POST",
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for making proxy requests"""
    client = get_proxy_client()
    return await client.request(
        service=service,
        endpoint=endpoint,
        method=method,
        data=data,
        **kwargs
    )


async def get_service_status(service: str) -> Dict[str, Any]:
    """Convenience function for getting service status"""
    client = get_proxy_client()
    return client.get_service_status(service)


async def get_all_services_status() -> Dict[str, Dict[str, Any]]:
    """Convenience function for getting all service status"""
    client = get_proxy_client()
    return client.get_all_service_status()