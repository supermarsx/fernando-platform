# Proxy Integration Guide

## Overview

The Fernando platform implements a comprehensive proxy infrastructure to route all external API calls through centralized proxy servers, ensuring **zero API key exposure** to clients while maintaining full functionality and improving security.

## Architecture

### Core Components

1. **ProxyClient** - Main interface for proxy operations
2. **RequestBuilder** - Standardizes request construction
3. **ResponseHandler** - Processes and validates responses
4. **AuthHandler** - Manages authentication and authorization

### Proxy Servers

- **LLM Proxy** (`http://localhost:8000`) - OpenAI, Anthropic, Local models
- **OCR Proxy** (`http://localhost:8001`) - PaddleOCR, Google Vision, Azure, AWS
- **ToConline Proxy** (`http://localhost:8002`) - Document extraction APIs
- **Stripe Proxy** (`http://localhost:8003`) - Payment processing
- **PayPal Proxy** (`http://localhost:8004`) - PayPal payment APIs
- **Coinbase Proxy** (`http://localhost:8005`) - Cryptocurrency payments
- **OpenAI Proxy** (`http://localhost:8006`) - Direct OpenAI API calls

## Configuration

### Environment Variables

```bash
# Proxy Configuration
PROXY_ENABLED=true
PROXY_FALLBACK_ENABLED=true
PROXY_TIMEOUT=30
PROXY_MAX_RETRIES=3

# LLM Proxy
LLM_PROXY_ENDPOINT=http://localhost:8000
LLM_PROXY_ENABLED=true

# OCR Proxy  
OCR_PROXY_ENDPOINT=http://localhost:8001
OCR_PROXY_ENABLED=true

# Payment Proxy Services
STRIPE_PROXY_ENDPOINT=http://localhost:8003
STRIPE_PROXY_ENABLED=true

PAYPAL_PROXY_ENDPOINT=http://localhost:8004
PAYPAL_PROXY_ENABLED=true

COINBASE_PROXY_ENDPOINT=http://localhost:8005
COINBASE_PROXY_ENABLED=true

# Security Configuration
PROXY_API_KEY_HEADER=X-API-Key
PROXY_AUTH_TYPE=bearer
PROXY_ENCRYPTION_ENABLED=true

# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RESET_TIMEOUT=60
```

### Service Configuration

```python
# Example: Custom proxy configuration
from app.services.proxy import get_proxy_client

config = {
    "timeout": 60,
    "max_retries": 5,
    "circuit_breaker": {
        "failure_threshold": 10,
        "reset_timeout": 120
    },
    "security": {
        "api_key_header": "X-Custom-API-Key"
    }
}

proxy_client = get_proxy_client(config)
```

## Usage Patterns

### Basic Proxy Requests

```python
from app.services.proxy import get_proxy_client

# Initialize proxy client
proxy_client = get_proxy_client()

# Make a request
response = await proxy_client.request(
    service="llm",
    endpoint="extract_fields", 
    method="POST",
    data={
        "text": "Invoice text content",
        "document_type": "invoice",
        "model": "gpt-4"
    }
)

if response["success"]:
    result = response["data"]
    fields = result["fields"]
    confidence = result["confidence_avg"]
else:
    error = response["error"]
    print(f"Request failed: {error['message']}")
```

### Service-Specific Patterns

#### LLM Service Integration

```python
from app.services.llm_service import get_llm_service

llm_service = get_llm_service()

# Extraction automatically uses proxy with fallback
result = await llm_service.extract_fields(
    text="Invoice content...",
    document_type="invoice"
)

# Result structure:
# {
#     "supplier_name": "Company Name",
#     "supplier_nif": "123456789", 
#     "invoice_date": "15/10/2025",
#     "total_amount": "1000.00",
#     "backend": "proxy",  # or "openai", "anthropic", etc.
#     "confidence": 0.95
# }
```

#### OCR Service Integration

```python
from app.services.ocr_service import get_ocr_service

ocr_service = get_ocr_service()

# Text extraction automatically uses proxy with fallback
result = await ocr_service.extract_text(
    image_path="/path/to/invoice.jpg"
)

# Result structure:
# {
#     "text": "Extracted invoice text...",
#     "confidence": 0.95,
#     "language": "pt", 
#     "backend": "proxy",  # or "paddleocr", "google", etc.
#     "blocks": [{"text": "...", "confidence": 0.95, "bbox": [...]}]
# }
```

#### Stripe Service Integration

```python
from app.services.stripe_service import StripeService

stripe_service = StripeService(db)

# Payment intent creation
payment_intent = await stripe_service._process_via_proxy(
    operation="create_payment_intent",
    data={
        "amount": 100.00,
        "currency": "eur",
        "invoice_id": 12345,
        "metadata": {"description": "Invoice payment"}
    }
)
```

### Direct Proxy Usage

```python
from app.services.proxy import get_proxy_client, make_proxy_request

# Simple requests using convenience function
response = await make_proxy_request(
    service="llm",
    endpoint="extract_fields",
    method="POST", 
    data={"text": "Sample text"}
)

# Or get client for more control
client = get_proxy_client()
status = await client.get_service_status("llm")
```

## Security Features

### API Key Protection

- **No direct API keys** in client code
- **Server-side authentication** through proxy servers
- **Encrypted communication** between services and proxies
- **Request signing** for sensitive operations

### Circuit Breaker Pattern

```python
# Automatic failure detection and circuit breaking
client = get_proxy_client()

# After 5 failures, circuit opens automatically
# All subsequent requests fail fast for 60 seconds
# Automatically retries after reset timeout
```

### Authentication Handling

```python
from app.services.proxy import get_auth_handler

auth_handler = get_auth_handler()

# Get authentication headers for a service
headers = await auth_handler.get_auth_headers("stripe")

# Validate credentials
is_valid = await auth_handler.validate_credentials("stripe")

# Get credential status for all services
status = await auth_handler.get_all_service_credentials_status()
```

## Error Handling

### Response Structure

```python
# Success Response
{
    "success": True,
    "data": {...},           # Service-specific data
    "metadata": {
        "status_code": 200,
        "service": "llm",
        "endpoint": "/extract",
        "timestamp": "2025-11-06T07:54:26Z",
        "response_time_ms": 1250.5
    }
}

# Error Response
{
    "success": False,
    "error": {
        "type": "validation_error",     # authentication_error, server_error, etc.
        "message": "Invalid input data",
        "code": 422,
        "details": {...},               # Service-specific error details
        "retryable": false              # For 429, 502, 503, 504
    },
    "metadata": {
        "status_code": 422,
        "service": "llm", 
        "endpoint": "/extract",
        "timestamp": "2025-11-06T07:54:26Z"
    }
}
```

### Error Types

| Error Type | HTTP Code | Retryable | Description |
|------------|-----------|-----------|-------------|
| `authentication_error` | 401 | No | Invalid API key or token |
| `authorization_error` | 403 | No | Insufficient permissions |
| `not_found_error` | 404 | No | Resource not found |
| `validation_error` | 422 | No | Invalid request data |
| `rate_limit_error` | 429 | Yes | Too many requests |
| `server_error` | 5xx | Yes | Server temporary error |
| `parsing_error` | 0 | No | Response parsing failed |

### Retry Logic

```python
# Automatic retry with exponential backoff
client = get_proxy_client()

# Configure retry behavior
client.max_retries = 3
client.request_timeout = 30

# Retry happens automatically for:
# - Network timeouts
# - 502, 503, 504 errors (server temporarily unavailable)
# - Rate limit errors (with exponential backoff)
```

## Monitoring and Observability

### Service Status

```python
from app.services.proxy import get_all_services_status

# Get status of all services
all_status = await get_all_services_status()

# Individual service status
llm_status = await get_service_status("llm")

# Example response:
{
    "llm": {
        "service": "llm",
        "proxy_enabled": True,
        "circuit_breaker": {
            "open": False,
            "failures": 0
        },
        "endpoint": "http://localhost:8000"
    }
}
```

### Telemetry

Each proxy request includes comprehensive telemetry:

```python
# Request metadata includes:
{
    "request_id": "uuid-here",
    "service": "llm",
    "timestamp": "2025-11-06T07:54:26Z",
    "response_time_ms": 1250.5,
    "success": True
}
```

### Health Checks

```python
# Check proxy server health
import httpx

async def check_proxy_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        return response.json()

# Health endpoint returns:
{
    "status": "healthy",
    "service": "llm-proxy",
    "timestamp": "2025-11-06T07:54:26Z",
    "version": "1.0.0"
}
```

## Migration Guide

### From Direct API Calls

**Before (Direct API):**

```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Extract invoice fields..."}],
    api_key="sk-..."  # API key exposed!
)
```

**After (Proxy):**

```python
from app.services.llm_service import get_llm_service

llm_service = get_llm_service()
result = await llm_service.extract_fields(
    text="Invoice content...",
    document_type="invoice"
)
# No API keys exposed!
```

### Configuration Migration

**Step 1: Update Environment Variables**

```bash
# Remove client-side API keys from .env files
# OLD: OPENAI_API_KEY=sk-...
# OLD: STRIPE_SECRET_KEY=sk_...

# Add proxy server configuration
LLM_PROXY_ENDPOINT=http://localhost:8000
LLM_PROXY_ENABLED=true
STRIPE_PROXY_ENDPOINT=http://localhost:8003
STRIPE_PROXY_ENABLED=true
```

**Step 2: Update Service Imports**

```python
# OLD: from app.services.llm_service import LLMService
# NEW: Use proxy-enabled service (same import)

from app.services.llm_service import get_llm_service
```

**Step 3: Remove Direct API Calls**

Replace direct API calls with proxy methods:

```python
# OLD: Direct Stripe call
import stripe
stripe.api_key = "sk_..."
payment_intent = stripe.PaymentIntent.create(...)

# NEW: Use proxy service
from app.services.stripe_service import StripeService
stripe_service = StripeService(db)
payment_intent = await stripe_service._process_via_proxy(
    operation="create_payment_intent",
    data={...}
)
```

## Testing

### Unit Tests

```bash
# Run proxy integration tests
cd /workspace/fernando/backend
python -m pytest tests/test_proxy_integration.py -v
```

### Integration Testing

```python
from app.services.proxy import get_proxy_client

async def test_proxy_integration():
    client = get_proxy_client()
    
    # Test LLM extraction
    response = await client.request(
        service="llm",
        endpoint="extract_fields",
        data={
            "text": "Sample invoice text",
            "document_type": "invoice"
        }
    )
    
    assert response["success"] is True
    assert "fields" in response["data"]

# Run with pytest
pytest -k test_proxy_integration -v
```

### Mock Testing

```python
from unittest.mock import Mock, patch
import pytest

@pytest.mark.asyncio
async def test_with_mock_proxy():
    with patch('app.services.proxy.proxy_client.httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"test": "value"}}
        
        mock_instance = Mock()
        mock_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await make_proxy_request("llm", "/test")
        assert result["success"] is True
```

## Troubleshooting

### Common Issues

#### 1. Proxy Server Unavailable

**Symptom:**
```
Error: Connection refused to proxy server
```

**Solution:**
```bash
# Check proxy server status
curl http://localhost:8000/health

# Start proxy server if not running
docker-compose up -d llm-proxy
```

#### 2. Authentication Errors

**Symptom:**
```
Error: authentication_error - Invalid API key
```

**Solution:**
```python
from app.services.proxy import get_auth_handler

# Check credential status
auth_handler = get_auth_handler()
status = await auth_handler.get_all_service_credentials_status()

# Verify API keys are set on server side
print(f"Stripe configured: {status['stripe']['configured']}")
```

#### 3. Circuit Breaker Open

**Symptom:**
```
Error: Circuit breaker open for service llm
```

**Solution:**
```python
from app.services.proxy import get_proxy_client

client = get_proxy_client()

# Check circuit breaker status
status = client.get_service_status("llm")
print(f"Circuit breaker open: {status['circuit_breaker']['open']}")

# Wait for automatic reset or restart service
```

#### 4. Timeout Issues

**Symptom:**
```
Error: Request timeout after 30 seconds
```

**Solution:**
```python
from app.services.proxy import get_proxy_client

client = get_proxy_client()
client.request_timeout = 60  # Increase timeout

# Or with individual request
response = await client.request(
    service="llm",
    endpoint="/extract",
    timeout=60
)
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable proxy-specific logging
logger = logging.getLogger("app.services.proxy")
logger.setLevel(logging.DEBUG)
```

### Health Monitoring

```python
# Create health check endpoint
@app.get("/api/v1/proxy/health")
async def proxy_health():
    from app.services.proxy import get_all_services_status
    
    status = await get_all_services_status()
    return {
        "overall_status": "healthy" if all(
            s["proxy_enabled"] for s in status.values()
        ) else "degraded",
        "services": status,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Performance Optimization

### Connection Pooling

```python
# Proxy client automatically manages connection pooling
client = get_proxy_client()

# For high-throughput scenarios, configure connection limits
client.config["connection_pool_size"] = 10
client.config["connection_pool_maxsize"] = 20
```

### Response Caching

```python
# Enable response caching for idempotent requests
client = get_proxy_client()
client.config["cache_responses"] = True
client.config["cache_ttl"] = 3600  # 1 hour

# For LLM extraction, cache results
response = await client.request(
    service="llm",
    endpoint="extract_fields",
    data={
        "text": "Common invoice format...",
        "cache_key": "invoice_v1"
    }
)
```

### Batch Operations

```python
# Process multiple requests in parallel
async def batch_extract(texts):
    tasks = []
    for text in texts:
        task = make_proxy_request(
            "llm", 
            "extract_fields", 
            data={"text": text}
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

## Security Best Practices

### 1. Environment Isolation

```bash
# Development
PROXY_ENABLED=true
PROXY_FALLBACK_ENABLED=true

# Production  
PROXY_ENABLED=true
PROXY_FALLBACK_ENABLED=false
```

### 2. API Key Management

```python
# Store API keys only on proxy servers
# Never expose to client code
API_KEYS = {
    "stripe": "sk_live_...",
    "openai": "sk-...",
    # etc.
}
```

### 3. Request Validation

```python
# Validate requests before proxy
from pydantic import BaseModel, ValidationError

class InvoiceRequest(BaseModel):
    text: str
    document_type: str = "invoice"
    model: str = "gpt-4"

async def safe_extract_fields(data: dict):
    try:
        request = InvoiceRequest(**data)
        return await make_proxy_request("llm", "extract_fields", data=request.dict())
    except ValidationError as e:
        return {"success": False, "error": "Invalid request data"}
```

### 4. Rate Limiting

```python
# Implement client-side rate limiting
import asyncio
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    async def acquire(self, service: str):
        now = time.time()
        # Clean old requests
        self.requests[service] = [
            req_time for req_time in self.requests[service]
            if now - req_time < self.time_window
        ]
        
        if len(self.requests[service]) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[service][0])
            await asyncio.sleep(sleep_time)
        
        self.requests[service].append(now)

# Usage
rate_limiter = RateLimiter()
await rate_limiter.acquire("llm")
response = await make_proxy_request("llm", "/extract")
```

## Conclusion

The proxy infrastructure provides a secure, scalable, and maintainable way to handle all external API integrations in the Fernando platform. Key benefits:

✅ **Zero API key exposure** - All authentication handled server-side  
✅ **Unified error handling** - Consistent response format across services  
✅ **Circuit breaker resilience** - Automatic failure detection and recovery  
✅ **Comprehensive monitoring** - Full telemetry and health checks  
✅ **Easy migration** - Drop-in replacement for existing API calls  
✅ **Security-first design** - Encrypted communication and request validation  

The system is production-ready and provides enterprise-grade reliability while maintaining the existing functionality of all Fernando platform services.