"""
Webhook Security Service
Handles webhook signature verification, security, and authentication
"""

import hmac
import hashlib
import base64
import secrets
import time
from typing import Dict, Any, Optional, Tuple
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebhookSecurityService:
    """Handles webhook security, signatures, and validation"""
    
    def __init__(self):
        self.algorithm = 'sha256'
        self.signature_header = 'X-Webhook-Signature'
        self.timestamp_header = 'X-Webhook-Timestamp'
        
        # Security configuration
        self.max_payload_size = 1024 * 1024  # 1MB
        self.max_timestamp_skew = 300  # 5 minutes
        self.allowed_content_types = ['application/json', 'text/json']
        
    def generate_secret(self, length: int = 32) -> str:
        """Generate a secure webhook secret"""
        return secrets.token_urlsafe(length)
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"v1={signature}"
    
    def sign_payload(self, payload: Dict[str, Any], secret: str) -> Dict[str, Any]:
        """Create signed payload with signature"""
        # Create the payload with metadata
        signed_payload = {
            "event": payload.get("event"),
            "data": payload.get("data", {}),
            "timestamp": int(time.time()),
            "id": payload.get("id", secrets.token_hex(16))
        }
        
        # Add signature to payload
        json_payload = self._json_dumps_for_signature(signed_payload)
        signature = self.generate_signature(json_payload, secret)
        
        signed_payload["signature"] = signature
        
        return signed_payload
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str,
        timestamp: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify webhook signature and timestamp"""
        
        try:
            # Verify timestamp if provided
            if timestamp:
                if not self._verify_timestamp(timestamp):
                    return False, "Timestamp too old or invalid"
            
            # Verify signature format
            if not signature.startswith("v1="):
                return False, "Invalid signature format"
            
            # Extract signature value
            expected_signature = signature[3:]
            
            # Calculate expected signature
            calculated_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(calculated_signature, expected_signature):
                return False, "Signature mismatch"
            
            return True, "Signature verified"
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False, f"Verification error: {str(e)}"
    
    def verify_incoming_webhook(
        self,
        headers: Dict[str, str],
        raw_payload: str,
        secret: str,
        timestamp_skew_check: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Verify incoming webhook request"""
        
        try:
            # Extract signature and timestamp
            signature = headers.get(self.signature_header)
            timestamp = headers.get(self.timestamp_header)
            
            if not signature:
                return False, "Missing signature header", {}
            
            # Check payload size
            if len(raw_payload.encode('utf-8')) > self.max_payload_size:
                return False, "Payload too large", {}
            
            # Verify signature
            valid, message = self.verify_signature(
                raw_payload,
                signature,
                secret,
                timestamp
            )
            
            if not valid:
                return False, message, {}
            
            # Parse payload
            try:
                payload = self._safe_json_loads(raw_payload)
            except Exception as e:
                return False, f"Invalid JSON payload: {str(e)}", {}
            
            return True, "Verified", payload
            
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return False, f"Verification failed: {str(e)}", {}
    
    def _verify_timestamp(self, timestamp: str) -> bool:
        """Verify timestamp is within acceptable range"""
        try:
            timestamp_int = int(timestamp)
            current_time = int(time.time())
            time_diff = abs(current_time - timestamp_int)
            
            return time_diff <= self.max_timestamp_skew
            
        except (ValueError, TypeError):
            return False
    
    def _safe_json_loads(self, json_str: str) -> Dict[str, Any]:
        """Safely parse JSON with validation"""
        import json
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
    
    def _json_dumps_for_signature(self, data: Dict[str, Any]) -> str:
        """Create deterministic JSON for signature"""
        import json
        
        # Sort keys for deterministic output
        def sort_keys(obj):
            if isinstance(obj, dict):
                return {k: sort_keys(obj[k]) for k in sorted(obj.keys())}
            elif isinstance(obj, list):
                return [sort_keys(item) for item in obj]
            else:
                return obj
        
        sorted_data = sort_keys(data)
        return json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)
    
    def validate_webhook_url(self, url: str) -> Tuple[bool, str]:
        """Validate webhook URL for security"""
        
        try:
            parsed = urlparse(url)
            
            # Basic URL structure
            if not all([parsed.scheme, parsed.netloc]):
                return False, "Invalid URL structure"
            
            # Security: Allow only HTTPS for production
            if parsed.scheme not in ['https', 'http']:
                return False, "Only HTTP/HTTPS protocols allowed"
            
            # Port restrictions
            if parsed.port:
                # Block common non-standard ports
                dangerous_ports = [22, 23, 25, 53, 135, 139, 445, 1433, 3389]
                if parsed.port in dangerous_ports:
                    return False, f"Port {parsed.port} not allowed"
            
            # Domain validation
            if not self._validate_domain(parsed.netloc):
                return False, "Invalid domain or IP"
            
            # Path validation
            if parsed.path and not self._validate_path(parsed.path):
                return False, "Invalid path"
            
            return True, "URL validation passed"
            
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    def _validate_domain(self, netloc: str) -> bool:
        """Validate domain or IP address"""
        
        # Check for valid hostname/IP pattern
        import re
        
        # IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, netloc):
            # Validate each octet is in range 0-255
            octets = netloc.split('.')
            return all(0 <= int(octet) <= 255 for octet in octets)
        
        # Hostname pattern (simplified)
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(hostname_pattern, netloc))
    
    def _validate_path(self, path: str) -> bool:
        """Validate URL path for security"""
        
        # Path should not contain dangerous patterns
        dangerous_patterns = [
            r'\.\./',  # Directory traversal
            r'[\x00-\x1f]',  # Control characters
            r'[<>:"|?*]',  # Forbidden characters in URLs
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, path):
                return False
        
        # Path should be reasonably short
        if len(path) > 200:
            return False
        
        return True
    
    def validate_payload_structure(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate webhook payload structure"""
        
        required_fields = ['event', 'data']
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Validate event name
        if not isinstance(payload['event'], str) or not payload['event']:
            return False, "Event must be a non-empty string"
        
        # Validate data field
        if not isinstance(payload['data'], dict):
            return False, "Data must be an object"
        
        # Optional: Validate event name format
        event_pattern = r'^[a-z0-9_.-]+$'
        if not re.match(event_pattern, payload['event']):
            return False, "Event name contains invalid characters"
        
        return True, "Payload structure valid"
    
    def create_security_headers(self, endpoint_url: str, secret: str) -> Dict[str, str]:
        """Create security headers for webhook registration"""
        
        import secrets
        
        return {
            'X-Webhook-Registration': 'Fernando-Platform',
            'X-Webhook-Version': '1.0',
            'X-Webhook-Algorithm': self.algorithm,
            'X-Webhook-Format': 'json',
            'X-Webhook-Idempotency': 'supported'
        }
    
    def rate_limit_key(self, endpoint_id: str, endpoint_url: str) -> str:
        """Generate rate limiting key for endpoint"""
        import hashlib
        
        key_data = f"{endpoint_id}:{endpoint_url}".encode('utf-8')
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def validate_event_name(self, event_name: str) -> Tuple[bool, str]:
        """Validate event name format and allowed characters"""
        
        # Event name pattern: lowercase letters, numbers, dots, hyphens, underscores
        pattern = r'^[a-z0-9_.-]+$'
        
        if not re.match(pattern, event_name):
            return False, "Event name can only contain lowercase letters, numbers, dots, hyphens, and underscores"
        
        if len(event_name) > 100:
            return False, "Event name too long (max 100 characters)"
        
        if event_name.startswith('.') or event_name.startswith('-'):
            return False, "Event name cannot start with dots or hyphens"
        
        return True, "Event name valid"
    
    def sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize webhook payload to remove potential security risks"""
        
        # Recursively sanitize the payload
        def sanitize_item(item):
            if isinstance(item, dict):
                return {key: sanitize_item(value) for key, value in item.items()}
            elif isinstance(item, list):
                return [sanitize_item(value) for value in item]
            elif isinstance(item, str):
                # Remove potentially dangerous content
                dangerous_patterns = [
                    r'<script[^>]*>.*?</script>',  # Script tags
                    r'javascript:',  # JavaScript URLs
                    r'data:text/html',  # Data URIs with HTML
                ]
                
                import re
                sanitized = item
                for pattern in dangerous_patterns:
                    sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
                
                return sanitized
            else:
                return item
        
        return sanitize_item(payload)
    
    def create_idempotency_key(self, endpoint_id: str, event_name: str, data_hash: str) -> str:
        """Create idempotency key for webhook delivery"""
        import hashlib
        
        key_data = f"{endpoint_id}:{event_name}:{data_hash}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:32]
    
    def hash_data_for_comparison(self, data: Dict[str, Any]) -> str:
        """Create hash for data comparison (idempotency checks)"""
        import json
        
        # Create deterministic JSON representation
        json_str = self._json_dumps_for_signature(data)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()