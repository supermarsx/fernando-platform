"""
Proxy Integration Tests

Comprehensive tests for proxy infrastructure integration with all services.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from app.services.proxy import (
    ProxyClient, RequestBuilder, ResponseHandler, AuthHandler,
    get_proxy_client, reset_proxy_client
)
from app.services.proxy.proxy_client import get_proxy_client as get_client


class TestProxyClient:
    """Test ProxyClient functionality"""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "timeout": 30,
            "max_retries": 3,
            "llm": {"proxy_endpoint": "http://test-llm:8000"},
            "ocr": {"proxy_endpoint": "http://test-ocr:8001"},
            "stripe": {"proxy_endpoint": "http://test-stripe:8003"}
        }
    
    def test_proxy_client_initialization(self, mock_config):
        """Test proxy client initialization"""
        client = ProxyClient(mock_config)
        
        assert client.request_timeout == 30
        assert client.max_retries == 3
        assert "llm" in client.service_endpoints
        assert "ocr" in client.service_endpoints
        assert "stripe" in client.service_endpoints
    
    def test_service_endpoint_configuration(self, mock_config):
        """Test service endpoint configuration"""
        client = ProxyClient(mock_config)
        
        assert client.service_endpoints["llm"] == "http://test-llm:8000"
        assert client.service_endpoints["ocr"] == "http://test-ocr:8001"
        assert client.service_endpoints["stripe"] == "http://test-stripe:8003"
    
    @pytest.mark.asyncio
    async def test_proxy_request_success(self):
        """Test successful proxy request"""
        client = ProxyClient()
        
        with patch('app.services.proxy.proxy_client.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True, "data": {"test": "value"}}
            mock_response.elapsed = Mock()
            mock_response.elapsed.total_seconds.return_value = 0.5
            
            mock_instance = Mock()
            mock_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await client.request(
                service="llm",
                endpoint="/test",
                method="POST",
                data={"test": "data"}
            )
            
            assert result["success"] is True
            assert result["data"]["test"] == "value"
    
    @pytest.mark.asyncio
    async def test_proxy_request_with_circuit_breaker(self):
        """Test circuit breaker functionality"""
        client = ProxyClient()
        
        # Simulate circuit breaker state
        client.circuit_breakers["test_service"] = {
            "failure_count": 10,
            "first_failure": None,
            "last_failure": None
        }
        
        # Should return False for should_use_proxy when circuit is open
        assert not client._should_use_proxy("test_service")
        
        # Should work normally when circuit is closed
        assert client._should_use_proxy("llm")
    
    @pytest.mark.asyncio
    async def test_fallback_request(self):
        """Test fallback request when proxy is disabled"""
        client = ProxyClient()
        client.config["llm"]["proxy_enabled"] = False
        
        result = await client._fallback_request(
            service="llm",
            endpoint="/extract",
            data={"text": "test text"},
            params=None
        )
        
        # Should return mock data for fallback
        assert "extracted_text" in result
        assert "confidence" in result
        assert "backend" in result
    
    def test_get_service_status(self):
        """Test service status retrieval"""
        client = ProxyClient()
        
        status = client.get_service_status("llm")
        
        assert status["service"] == "llm"
        assert "proxy_enabled" in status
        assert "circuit_breaker" in status
        assert "endpoint" in status
    
    def test_update_service_endpoint(self):
        """Test updating service endpoint"""
        client = ProxyClient()
        
        client.update_service_endpoint("llm", "http://new-llm:9000")
        
        assert client.service_endpoints["llm"] == "http://new-llm:9000"
    
    def test_disable_enable_service_proxy(self):
        """Test disabling and enabling service proxy"""
        client = ProxyClient()
        
        # Disable proxy
        client.disable_service_proxy("llm")
        assert client.config["llm"]["proxy_enabled"] is False
        
        # Enable proxy
        client.enable_service_proxy("llm")
        assert client.config["llm"]["proxy_enabled"] is True


class TestRequestBuilder:
    """Test RequestBuilder functionality"""
    
    @pytest.fixture
    def request_builder(self):
        return RequestBuilder()
    
    def test_initialization(self):
        """Test request builder initialization"""
        builder = RequestBuilder()
        
        assert "llm" in builder.endpoint_mappings
        assert "ocr" in builder.endpoint_mappings
        assert "stripe" in builder.endpoint_mappings
        assert "extract_fields" in builder.endpoint_mappings["llm"]
    
    def test_endpoint_mapping(self):
        """Test endpoint mapping"""
        builder = RequestBuilder()
        
        # Test known mapping
        mapped = builder._map_endpoint("llm", "extract_fields")
        assert mapped == "/llm/extract"
        
        # Test unknown mapping (should return as-is)
        mapped = builder._map_endpoint("llm", "unknown_endpoint")
        assert mapped == "/llm/unknown_endpoint"
        
        # Test direct path
        mapped = builder._map_endpoint("llm", "/direct/path")
        assert mapped == "/direct/path"
    
    def test_build_headers(self):
        """Test header building"""
        builder = RequestBuilder()
        
        headers = builder._build_headers("stripe")
        
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "X-Stripe-Version" in headers
    
    def test_build_headers_with_additional(self):
        """Test header building with additional headers"""
        builder = RequestBuilder()
        
        additional = {"Custom-Header": "value"}
        headers = builder._build_headers("llm", additional)
        
        assert headers["Custom-Header"] == "value"
        assert headers["X-Service"] == "llm"
    
    def test_build_metadata(self):
        """Test metadata building"""
        builder = RequestBuilder()
        
        metadata = builder._build_metadata("llm", "/extract", "POST")
        
        assert metadata["service"] == "llm"
        assert metadata["original_endpoint"] == "/extract"
        assert metadata["method"] == "POST"
        assert "timestamp" in metadata
        assert "request_id" in metadata
    
    def test_service_request_validation(self):
        """Test service-specific request validation"""
        builder = RequestBuilder()
        
        # Valid Stripe request
        stripe_request = {
            "json": {"amount": 100, "currency": "EUR"},
            "method": "POST"
        }
        builder._validate_service_request("stripe", stripe_request)  # Should not raise
        
        # Invalid Stripe request
        invalid_stripe_request = {
            "json": {"amount": "invalid", "currency": "EUR"},
            "method": "POST"
        }
        with pytest.raises(ValueError):
            builder._validate_service_request("stripe", invalid_stripe_request)
    
    def test_add_remove_endpoint_mapping(self):
        """Test adding and removing endpoint mappings"""
        builder = RequestBuilder()
        
        builder.add_endpoint_mapping("test_service", "custom_endpoint", "/custom/path")
        assert builder.get_endpoint_mapping("test_service", "custom_endpoint") == "/custom/path"
        
        builder.remove_endpoint_mapping("test_service", "custom_endpoint")
        assert builder.get_endpoint_mapping("test_service", "custom_endpoint") is None


class TestResponseHandler:
    """Test ResponseHandler functionality"""
    
    @pytest.fixture
    def response_handler(self):
        return ResponseHandler()
    
    @pytest.mark.asyncio
    async def test_success_response_handling(self, response_handler):
        """Test handling of successful responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"data": "test_value"}
        mock_response.elapsed = Mock()
        mock_response.elapsed.total_seconds.return_value = 1.0
        
        result = await response_handler.handle_response(mock_response, "llm", "/test")
        
        assert result["success"] is True
        assert result["data"]["data"] == "test_value"
        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_error_response_handling(self, response_handler):
        """Test handling of error responses"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error": "Unauthorized"}
        
        result = await response_handler.handle_response(mock_response, "llm", "/test")
        
        assert result["success"] is False
        assert result["error"]["type"] == "authentication_error"
        assert result["error"]["code"] == 401
    
    @pytest.mark.asyncio
    async def test_parsing_error_handling(self, response_handler):
        """Test handling of response parsing errors"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = json.JSONDecodeError("Test error", "", 0)
        
        result = await response_handler.handle_response(mock_response, "llm", "/test")
        
        assert result["success"] is False
        assert result["error"]["type"] == "parsing_error"
    
    def test_error_classification(self, response_handler):
        """Test error type classification"""
        response_info = {"status_code": 401}
        content = {"error": "unauthorized"}
        
        error_type = response_handler._classify_error(response_info, content)
        assert error_type == "authentication_error"
        
        response_info = {"status_code": 404}
        content = {"error": "not found"}
        
        error_type = response_handler._classify_error(response_info, content)
        assert error_type == "not_found_error"
    
    def test_extract_error_message(self, response_handler):
        """Test error message extraction"""
        content = {"message": "Test error message"}
        message = response_handler._extract_error_message(content)
        assert message == "Test error message"
        
        content = {"errors": ["error1", "error2"]}
        message = response_handler._extract_error_message(content)
        assert "error1" in message and "error2" in message
    
    def test_service_response_processing(self, response_handler):
        """Test service-specific response processing"""
        # Test Stripe response processing
        content = {"id": "test_id", "object": "test_object"}
        result = {"data": {}, "metadata": {}}
        processed = response_handler._process_stripe_response(result, content)
        
        assert processed["metadata"]["stripe_id"] == "test_id"
        assert processed["metadata"]["stripe_object"] == "test_object"
        
        # Test LLM response processing
        content = {"text": "extracted text", "confidence": 0.95}
        result = {"data": {}, "metadata": {}}
        processed = response_handler._process_llm_response(result, content)
        
        assert "extracted_text" in processed["data"]
        assert processed["data"]["confidence"] == 0.95


class TestAuthHandler:
    """Test AuthHandler functionality"""
    
    @pytest.fixture
    def auth_handler(self):
        return AuthHandler()
    
    @pytest.mark.asyncio
    async def test_get_auth_headers_stripe(self, auth_handler):
        """Test Stripe authentication headers"""
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'test_key'}):
            headers = await auth_handler.get_auth_headers("stripe")
            
            assert "Authorization" in headers
            assert "Bearer" in headers["Authorization"]
            assert "X-Stripe-Version" in headers
    
    @pytest.mark.asyncio
    async def test_get_auth_headers_coinbase(self, auth_handler):
        """Test Coinbase Commerce authentication headers"""
        with patch.dict('os.environ', {'COINBASE_COMMERCE_API_KEY': 'test_key'}):
            headers = await auth_handler.get_auth_headers("coinbase")
            
            assert "X-CC-Api-Key" in headers
            assert "X-CC-Version" in headers
    
    @pytest.mark.asyncio
    async def test_validate_credentials(self, auth_handler):
        """Test credential validation"""
        with patch.dict('os.environ', {'STRIPE_SECRET_KEY': 'test_key'}):
            is_valid = await auth_handler.validate_credentials("stripe")
            assert is_valid is True
        
        # Test invalid service
        is_valid = await auth_handler.validate_credentials("nonexistent")
        assert is_valid is False
    
    def test_api_key_cache_management(self, auth_handler):
        """Test API key caching"""
        auth_handler.set_service_api_key("test_service", "test_key")
        
        assert auth_handler.api_key_cache["test_service"] == "test_key"
        
        # Test retrieval from cache
        with patch.dict('os.environ', {}, clear=False):
            # Don't clear environment, but should use cache
            key = asyncio.run(auth_handler._get_service_api_key("test_service"))
            assert key == "test_key"
        
        auth_handler.remove_service_api_key("test_service")
        assert "test_service" not in auth_handler.api_key_cache
    
    def test_security_info(self, auth_handler):
        """Test security information retrieval"""
        info = auth_handler.get_security_info()
        
        assert "api_key_header" in info
        assert "auth_type" in info
        assert "cached_tokens" in info
        assert "security_features" in info


class TestGlobalProxyClient:
    """Test global proxy client functions"""
    
    def setup_method(self):
        """Reset global state before each test"""
        reset_proxy_client()
    
    def test_get_proxy_client_creates_singleton(self):
        """Test that get_proxy_client creates a singleton instance"""
        client1 = get_proxy_client()
        client2 = get_proxy_client()
        
        assert client1 is client2
        assert isinstance(client1, ProxyClient)
    
    def test_get_proxy_client_with_config(self):
        """Test get_proxy_client with custom config"""
        config = {"timeout": 60}
        client1 = get_proxy_client()
        
        assert client1.request_timeout == 30  # default
        
        client2 = get_proxy_client(config)
        assert client2.config["timeout"] == 60
        assert client1 is client2  # same instance, config updated
    
    def test_reset_proxy_client(self):
        """Test resetting global proxy client"""
        client1 = get_proxy_client()
        reset_proxy_client()
        client2 = get_proxy_client()
        
        assert client1 is not client2
    
    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """Test convenience functions"""
        client = get_proxy_client()
        
        # Mock the client methods
        client.get_all_service_status = Mock(return_value={"llm": {"status": "active"}})
        
        # Test convenience function
        status = await asyncio.create_task(get_all_services_status())
        assert "llm" in status
        
        service_status = await asyncio.create_task(get_service_status("llm"))
        assert "status" in service_status


class TestProxyIntegration:
    """Integration tests for proxy with existing services"""
    
    @pytest.mark.asyncio
    async def test_service_health_check(self):
        """Test service health check through proxy"""
        client = ProxyClient()
        
        # Mock successful health check
        with patch('app.services.proxy.proxy_client.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy", "service": "llm-proxy"}
            
            mock_instance = Mock()
            mock_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await client.request(
                service="llm",
                endpoint="/health",
                method="GET"
            )
            
            assert result["success"] is True
            assert result["data"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_llm_extraction_via_proxy(self):
        """Test LLM field extraction through proxy"""
        client = ProxyClient()
        
        # Mock successful extraction
        with patch('app.services.proxy.proxy_client.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "fields": {
                        "supplier_name": {"value": "Fernando", "confidence": 0.95},
                        "total_amount": {"value": "100.00", "confidence": 0.98}
                    },
                    "confidence_avg": 0.965,
                    "backend": "proxy",
                    "model": "gpt-4"
                }
            }
            
            mock_instance = Mock()
            mock_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await client.request(
                service="llm",
                endpoint="extract_fields",
                method="POST",
                data={
                    "text": "Sample invoice text",
                    "document_type": "invoice",
                    "model": "gpt-4"
                }
            )
            
            assert result["success"] is True
            assert "fields" in result["data"]
            assert result["data"]["confidence_avg"] == 0.965
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration across multiple failures"""
        client = ProxyClient()
        
        # Simulate failures for a service
        for _ in range(5):
            client._record_failure("test_service")
        
        # Circuit should be open
        assert client._is_circuit_open("test_service")
        
        # Should not use proxy when circuit is open
        assert not client._should_use_proxy("test_service")
        
        # Record success should reset circuit breaker
        client._record_success("test_service")
        assert not client._is_circuit_open("test_service")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])