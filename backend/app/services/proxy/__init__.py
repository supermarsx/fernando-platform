"""
Proxy Client Infrastructure for Fernando Platform Services

This module provides standardized proxy client functionality to route all
API calls through centralized proxy servers, ensuring zero API key exposure.
"""

from .proxy_client import ProxyClient, get_proxy_client
from .request_builder import RequestBuilder
from .response_handler import ResponseHandler
from .auth_handler import AuthHandler

__all__ = [
    "ProxyClient",
    "get_proxy_client",
    "RequestBuilder", 
    "ResponseHandler",
    "AuthHandler"
]