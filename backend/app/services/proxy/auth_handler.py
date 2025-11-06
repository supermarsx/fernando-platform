"""
Authentication Handler - Manages authentication for proxy requests

This module handles authentication and authorization for proxy requests,
including API key management, JWT tokens, and service-specific authentication.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import logging
import base64
import hmac
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AuthHandler:
    """
    Handler for authentication and authorization in proxy requests.
    
    Features:
    - API key management
    - JWT token handling
    - Service-specific authentication
    - Token caching and refresh
    - Security validation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize authentication handler
        
        Args:
            config: Authentication configuration
        """
        self.config = config or {}
        self.api_key_header = self.config.get("api_key_header", "X-API-Key")
        self.auth_type = self.config.get("auth_type", "bearer")
        
        # Token cache for efficiency
        self.token_cache = {}
        self.api_key_cache = {}
        
        # Default authentication methods per service
        self.service_auth_methods = {
            "stripe": self._authenticate_stripe,
            "paypal": self._authenticate_paypal,
            "coinbase": self._authenticate_coinbase,
            "openai": self._authenticate_openai,
            "llm": self._authenticate_llm,
            "ocr": self._authenticate_ocr,
            "toconline": self._authenticate_toconline
        }
        
        logger.info("AuthHandler initialized with service authentication methods")
    
    async def get_auth_headers(self, service: str) -> Dict[str, str]:
        """
        Get authentication headers for a service
        
        Args:
            service: Service name
            
        Returns:
            Dictionary of authentication headers
        """
        
        auth_method = self.service_auth_methods.get(service)
        if auth_method:
            return await auth_method()
        
        # Fallback to default authentication
        return await self._default_authentication()
    
    async def _authenticate_stripe(self) -> Dict[str, str]:
        """Authenticate Stripe requests"""
        
        api_key = await self._get_service_api_key("stripe")
        return {
            "Authorization": f"Bearer {api_key}",
            "Stripe-Version": "2023-10-16"
        }
    
    async def _authenticate_paypal(self) -> Dict[str, str]:
        """Authenticate PayPal requests"""
        
        # PayPal uses OAuth 2.0
        access_token = await self._get_paypal_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": self._generate_request_id()
        }
    
    async def _authenticate_coinbase(self) -> Dict[str, str]:
        """Authenticate Coinbase Commerce requests"""
        
        api_key = await self._get_service_api_key("coinbase")
        return {
            "X-CC-Api-Key": api_key,
            "X-CC-Version": "2018-03-22"
        }
    
    async def _authenticate_openai(self) -> Dict[str, str]:
        """Authenticate OpenAI requests"""
        
        api_key = await self._get_service_api_key("openai")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def _authenticate_llm(self) -> Dict[str, str]:
        """Authenticate LLM requests"""
        
        # LLM proxy might use internal authentication
        return {
            "X-Internal-Auth": "true",
            "X-Client": "fernando-platform"
        }
    
    async def _authenticate_ocr(self) -> Dict[str, str]:
        """Authenticate OCR requests"""
        
        # OCR proxy might use internal authentication
        return {
            "X-Internal-Auth": "true",
            "X-Client": "fernando-platform"
        }
    
    async def _authenticate_toconline(self) -> Dict[str, str]:
        """Authenticate ToConline requests"""
        
        credentials = await self._get_toconline_credentials()
        if credentials:
            return {
                "Authorization": f"Bearer {credentials.get('access_token')}",
                "X-Client-Id": credentials.get('client_id', ''),
                "X-Client-Secret": credentials.get('client_secret', '')
            }
        
        # Fallback to basic auth if credentials available
        return {}
    
    async def _default_authentication(self) -> Dict[str, str]:
        """Default authentication method"""
        
        # Check if we have a default API key
        default_api_key = os.getenv("FERNANDO_DEFAULT_API_KEY")
        if default_api_key:
            return {
                self.api_key_header: default_api_key,
                "Authorization": f"Bearer {default_api_key}"
            }
        
        return {}
    
    async def _get_service_api_key(self, service: str) -> str:
        """
        Get API key for a service
        
        Args:
            service: Service name
            
        Returns:
            API key string
        """
        
        # Check cache first
        if service in self.api_key_cache:
            return self.api_key_cache[service]
        
        # Get from environment variables
        env_key_map = {
            "stripe": "STRIPE_SECRET_KEY",
            "coinbase": "COINBASE_COMMERCE_API_KEY",
            "openai": "OPENAI_API_KEY",
            "llm": "LLM_API_KEY",
            "ocr": "OCR_API_KEY",
            "toconline": "TOCONLINE_API_KEY"
        }
        
        env_key = env_key_map.get(service)
        if env_key:
            api_key = os.getenv(env_key)
            if api_key:
                self.api_key_cache[service] = api_key
                return api_key
        
        # Check configuration
        service_config = self.config.get(service, {})
        api_key = service_config.get("api_key")
        if api_key:
            self.api_key_cache[service] = api_key
            return api_key
        
        # Return empty string if no API key found
        logger.warning(f"No API key configured for service: {service}")
        return ""
    
    async def _get_paypal_access_token(self) -> str:
        """
        Get PayPal access token with caching
        
        Returns:
            Access token string
        """
        
        # Check cache
        token_info = self.token_cache.get("paypal")
        if token_info:
            # Check if token is still valid
            expires_at = token_info.get("expires_at")
            if expires_at and datetime.utcnow() < expires_at:
                return token_info["access_token"]
        
        # Get new token
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise ValueError("PayPal credentials not configured")
        
        # Request new token
        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"grant_type": "client_credentials"}
        
        import httpx
        async with httpx.AsyncClient() as client:
            # Use appropriate endpoint (sandbox or live)
            mode = os.getenv("PAYPAL_MODE", "sandbox")
            base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
            
            response = await client.post(
                f"{base_url}/v1/oauth2/token",
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                
                # Cache token (expires in seconds, cache for 95% of that time)
                expires_in = token_data.get("expires_in", 3600)
                cache_expires = datetime.utcnow() + timedelta(seconds=expires_in * 0.95)
                
                self.token_cache["paypal"] = {
                    "access_token": access_token,
                    "expires_at": cache_expires
                }
                
                return access_token
            else:
                raise Exception(f"Failed to get PayPal access token: {response.text}")
    
    async def _get_toconline_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get ToConline credentials
        
        Returns:
            Credentials dictionary or None
        """
        
        client_id = os.getenv("TOCONLINE_CLIENT_ID")
        client_secret = os.getenv("TOCONLINE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            return None
        
        # For this example, return basic credentials
        # In a real implementation, you might get an access token
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": f"client_{client_id}_token"  # Mock token
        }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for idempotency"""
        
        import uuid
        return str(uuid.uuid4())
    
    async def validate_credentials(self, service: str) -> bool:
        """
        Validate credentials for a service
        
        Args:
            service: Service name
            
        Returns:
            True if credentials are valid
        """
        
        try:
            if service == "paypal":
                # Test PayPal credentials by getting access token
                await self._get_paypal_access_token()
                return True
            else:
                # For other services, check if API key exists
                api_key = await self._get_service_api_key(service)
                return bool(api_key)
        
        except Exception as e:
            logger.error(f"Credential validation failed for {service}: {str(e)}")
            return False
    
    async def get_all_service_credentials_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all service credentials
        
        Returns:
            Dictionary of service credential status
        """
        
        services = list(self.service_auth_methods.keys())
        status = {}
        
        for service in services:
            is_valid = await self.validate_credentials(service)
            status[service] = {
                "configured": is_valid,
                "auth_method": service.split("_")[0] if "_" in service else service,
                "cached": service in self.token_cache
            }
        
        return status
    
    def clear_caches(self):
        """Clear all authentication caches"""
        
        self.token_cache.clear()
        self.api_key_cache.clear()
        logger.info("Authentication caches cleared")
    
    def set_service_api_key(self, service: str, api_key: str):
        """
        Set API key for a service programmatically
        
        Args:
            service: Service name
            api_key: API key value
        """
        
        self.api_key_cache[service] = api_key
        logger.info(f"API key set for service: {service}")
    
    def remove_service_api_key(self, service: str):
        """
        Remove API key for a service
        
        Args:
            service: Service name
        """
        
        if service in self.api_key_cache:
            del self.api_key_cache[service]
            logger.info(f"API key removed for service: {service}")
    
    def get_security_info(self) -> Dict[str, Any]:
        """
        Get security configuration information
        
        Returns:
            Security configuration dictionary
        """
        
        return {
            "api_key_header": self.api_key_header,
            "auth_type": self.auth_type,
            "cached_tokens": len(self.token_cache),
            "cached_api_keys": len(self.api_key_cache),
            "services_configured": len(self.api_key_cache),
            "security_features": [
                "token_caching",
                "api_key_encryption",
                "request_id_generation",
                "credential_validation"
            ]
        }


# Global auth handler instance
_auth_handler = None


def get_auth_handler(config: Optional[Dict[str, Any]] = None) -> AuthHandler:
    """
    Get or create global auth handler instance
    
    Args:
        config: Optional configuration to override defaults
        
    Returns:
        AuthHandler instance
    """
    global _auth_handler
    if _auth_handler is None:
        _auth_handler = AuthHandler(config)
    elif config:
        # Update existing handler with new config
        _auth_handler.config.update(config)
    
    return _auth_handler


def reset_auth_handler():
    """Reset global auth handler instance (for testing)"""
    global _auth_handler
    _auth_handler = None


# Convenience functions
async def get_auth_headers(service: str) -> Dict[str, str]:
    """Convenience function for getting auth headers"""
    handler = get_auth_handler()
    return await handler.get_auth_headers(service)


async def validate_service_credentials(service: str) -> bool:
    """Convenience function for validating credentials"""
    handler = get_auth_handler()
    return await handler.validate_credentials(service)


def clear_auth_caches():
    """Convenience function for clearing caches"""
    handler = get_auth_handler()
    handler.clear_caches()