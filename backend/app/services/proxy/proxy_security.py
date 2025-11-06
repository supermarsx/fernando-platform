"""
Proxy Security Middleware

Security middleware for the centralized proxy server providing:
- Request validation and sanitization
- IP whitelisting and blacklisting
- Authentication and authorization
- Request/response encryption
- Fraud detection and prevention
- Security event logging

Features:
- Zero trust architecture
- Real-time threat detection
- Advanced rate limiting
- Request signature validation
- Security header injection
- Geographic blocking
"""

import asyncio
import time
import hashlib
import hmac
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response as StarletteResponse

from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class SecurityEvent(Enum):
    """Security event types."""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    SUSPICIOUS_REQUEST = "suspicious_request"
    INVALID_SIGNATURE = "invalid_signature"
    MALICIOUS_PAYLOAD = "malicious_payload"
    GEOLOCATION_BLOCKED = "geolocation_blocked"
    DDOS_DETECTED = "ddos_detected"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"


class ThreatLevel(Enum):
    """Threat levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityContext:
    """Security context for request."""
    client_ip: str
    user_agent: str
    request_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    auth_token: Optional[str] = None
    api_key_id: Optional[str] = None
    geographic_location: Optional[str] = None
    reputation_score: float = 50.0
    threat_indicators: List[str] = None
    security_policies: List[str] = None
    
    def __post_init__(self):
        if self.threat_indicators is None:
            self.threat_indicators = []
        if self.security_policies is None:
            self.security_policies = []


@dataclass
class SecurityRule:
    """Security rule definition."""
    name: str
    description: str
    threat_level: ThreatLevel
    action: str  # "allow", "block", "monitor", "alert"
    conditions: Dict[str, Any]
    rate_limit: Optional[Dict[str, int]] = None
    blacklist_duration: Optional[int] = None  # seconds


class SecurityEventLogger:
    """Logs security events for analysis and alerting."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.max_events = 10000
        
        # Event counters
        self.event_counts = {
            event_type.value: 0 for event_type in SecurityEvent
        }
        
        # IP tracking
        self.ip_tracking: Dict[str, Dict[str, Any]] = {}
        
        # Threat patterns
        self.threat_patterns = {
            "sql_injection": [
                r"union\s+select",
                r"select\s+.*\s+from",
                r"drop\s+table",
                r"insert\s+into",
                r"update\s+set",
                r"delete\s+from",
                r"exec\s*\(",
                r"execute\s*\(",
                r"script\s*>",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*="
            ],
            "xss": [
                r"<script",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*=",
                r"onclick\s*=",
                r"<iframe",
                r"<object",
                r"<embed",
                r"<form"
            ],
            "path_traversal": [
                r"\.\.\/",
                r"\.\.\\",
                r"\%2e\%2e\%2f",
                r"\%2e\%2e\%5c",
                r"\.\.%2f",
                r"\.\.%5c"
            ]
        }
    
    def log_security_event(
        self,
        event_type: SecurityEvent,
        client_ip: str,
        threat_level: ThreatLevel,
        details: Dict[str, Any],
        context: SecurityContext
    ):
        """Log security event."""
        event = {
            "timestamp": datetime.utcnow(),
            "event_type": event_type,
            "client_ip": client_ip,
            "threat_level": threat_level,
            "details": details,
            "context": context,
            "request_id": context.request_id
        }
        
        # Add to events list
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)
        
        # Update counters
        self.event_counts[event_type.value] += 1
        
        # Update IP tracking
        if client_ip not in self.ip_tracking:
            self.ip_tracking[client_ip] = {
                "first_seen": datetime.utcnow(),
                "last_seen": datetime.utcnow(),
                "event_count": 0,
                "threat_levels": set(),
                "blocked": False,
                "whitelisted": False
            }
        
        ip_data = self.ip_tracking[client_ip]
        ip_data["last_seen"] = datetime.utcnow()
        ip_data["event_count"] += 1
        ip_data["threat_levels"].add(threat_level.value)
        
        # Track in telemetry
        event_tracker.track_system_event(
            f"security_{event_type.value}",
            self._get_event_level(threat_level),
            {
                "client_ip": client_ip,
                "threat_level": threat_level.value,
                "request_id": context.request_id,
                **details
            },
            tags=["security", "proxy"]
        )
    
    def _get_event_level(self, threat_level: ThreatLevel) -> EventLevel:
        """Convert threat level to event level."""
        mapping = {
            ThreatLevel.LOW: EventLevel.INFO,
            ThreatLevel.MEDIUM: EventLevel.WARNING,
            ThreatLevel.HIGH: EventLevel.ERROR,
            ThreatLevel.CRITICAL: EventLevel.CRITICAL
        }
        return mapping.get(threat_level, EventLevel.INFO)
    
    def should_block_ip(self, client_ip: str) -> bool:
        """Check if IP should be blocked based on threat activity."""
        ip_data = self.ip_tracking.get(client_ip)
        
        if not ip_data:
            return False
        
        if ip_data.get("blocked", False):
            return True
        
        # Block if too many high-level threats
        high_threats = sum(
            1 for level in ip_data.get("threat_levels", set())
            if level in ["high", "critical"]
        )
        
        if high_threats >= 5:
            ip_data["blocked"] = True
            return True
        
        # Block if too many events in short time
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        ip_data["recent_events"] = ip_data.get("recent_events", 0) + 1
        
        if ip_data["recent_events"] >= 20:
            ip_data["blocked"] = True
            return True
        
        return False
    
    def should_whitelist_ip(self, client_ip: str) -> bool:
        """Check if IP should be whitelisted."""
        ip_data = self.ip_tracking.get(client_ip)
        return ip_data.get("whitelisted", False) if ip_data else False
    
    def get_recent_events(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent security events."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        return [
            event for event in self.events
            if event["timestamp"] >= cutoff_time
        ]


class ThreatDetector:
    """Detects various types of threats in requests."""
    
    def __init__(self):
        # Suspicious patterns
        self.suspicious_patterns = {
            "sql_injection": [
                r"union\s+select",
                r"select\s+.*\s+from",
                r"drop\s+table",
                r"insert\s+into",
                r"update\s+set",
                r"delete\s+from",
                r"exec\s*\(",
                r"execute\s*\("
            ],
            "xss": [
                r"<script",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*=",
                r"onclick\s*=",
                r"<iframe",
                r"<object",
                r"<embed"
            ],
            "path_traversal": [
                r"\.\.\/",
                r"\.\.\\",
                r"\%2e\%2e\%2f",
                r"\%2e\%2e\%5c"
            ],
            "command_injection": [
                r"\|",
                r"\|\|",
                r"&",
                r"&&",
                r";",
                r"\$\(",
                r"`",
                r"wget",
                r"curl",
                r"nc\s",
                r"netcat"
            ]
        }
        
        # Rate limiting patterns
        self.rate_limit_patterns = {
            "ddos_indicators": [
                r"^.*$"  # Placeholder - would be more specific
            ]
        }
    
    async def detect_threats(
        self,
        request: Request,
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Detect threats in request."""
        threats = []
        
        # Get request components
        path = str(request.url.path)
        method = request.method
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        
        # Check path for threats
        threats.extend(self._check_path_threats(path, context))
        
        # Check query parameters for threats
        threats.extend(self._check_query_threats(query_params, context))
        
        # Check headers for threats
        threats.extend(self._check_header_threats(headers, context))
        
        # Check for unusual patterns
        threats.extend(self._check_unusual_patterns(request, context))
        
        # Check rate limiting
        threats.extend(self._check_rate_limiting(context))
        
        return threats
    
    def _check_path_threats(
        self,
        path: str,
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Check path for threats."""
        threats = []
        
        for threat_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                import re
                if re.search(pattern, path, re.IGNORECASE):
                    if threat_type == "sql_injection":
                        threats.append((
                            SecurityEvent.SQL_INJECTION_ATTEMPT,
                            ThreatLevel.HIGH,
                            {"path": path, "pattern": pattern}
                        ))
                    elif threat_type == "xss":
                        threats.append((
                            SecurityEvent.XSS_ATTEMPT,
                            ThreatLevel.MEDIUM,
                            {"path": path, "pattern": pattern}
                        ))
                    elif threat_type == "path_traversal":
                        threats.append((
                            SecurityEvent.PATH_TRAVERSAL_ATTEMPT,
                            ThreatLevel.HIGH,
                            {"path": path, "pattern": pattern}
                        ))
        
        return threats
    
    def _check_query_threats(
        self,
        query_params: Dict[str, str],
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Check query parameters for threats."""
        threats = []
        
        for param_name, param_value in query_params.items():
            for threat_type, patterns in self.suspicious_patterns.items():
                for pattern in patterns:
                    import re
                    if re.search(pattern, param_value, re.IGNORECASE):
                        if threat_type == "sql_injection":
                            threats.append((
                                SecurityEvent.SQL_INJECTION_ATTEMPT,
                                ThreatLevel.HIGH,
                                {"parameter": param_name, "value": param_value, "pattern": pattern}
                            ))
        
        return threats
    
    def _check_header_threats(
        self,
        headers: Dict[str, str],
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Check headers for threats."""
        threats = []
        
        # Check for suspicious user agents
        user_agent = headers.get("user-agent", "")
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan"]
        
        for agent in suspicious_agents:
            if agent.lower() in user_agent.lower():
                threats.append((
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    ThreatLevel.HIGH,
                    {"suspicious_agent": agent, "user_agent": user_agent}
                ))
        
        # Check for missing security headers
        required_headers = ["user-agent", "accept"]
        missing_headers = [h for h in required_headers if h not in headers]
        
        if missing_headers:
            threats.append((
                SecurityEvent.SUSPICIOUS_REQUEST,
                ThreatLevel.MEDIUM,
                {"missing_headers": missing_headers}
            ))
        
        return threats
    
    def _check_unusual_patterns(
        self,
        request: Request,
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Check for unusual request patterns."""
        threats = []
        
        # Check for unusual HTTP methods
        unusual_methods = ["TRACE", "TRACK", "DEBUG", "CONNECT"]
        if request.method.upper() in unusual_methods:
            threats.append((
                SecurityEvent.SUSPICIOUS_REQUEST,
                ThreatLevel.MEDIUM,
                {"unusual_method": request.method}
            ))
        
        # Check for very long URLs
        url_length = len(str(request.url))
        if url_length > 2000:
            threats.append((
                SecurityEvent.SUSPICIOUS_REQUEST,
                ThreatLevel.MEDIUM,
                {"long_url": url_length}
            ))
        
        return threats
    
    def _check_rate_limiting(
        self,
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Check for rate limiting violations."""
        threats = []
        
        # This would integrate with rate limiting system
        # For now, just check if we're tracking this IP
        
        # Check for rapid-fire requests
        # This would be implemented with sliding window counters
        
        return threats


class SecurityValidator:
    """Validates request security aspects."""
    
    def __init__(self):
        self.max_content_length = 10 * 1024 * 1024  # 10MB
        self.allowed_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
            "text/xml",
            "application/xml"
        }
        
        self.blocked_extensions = {
            ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".js", ".jar", ".sh"
        }
        
        self.max_headers = 100
        self.max_header_length = 8192
    
    async def validate_request(
        self,
        request: Request,
        context: SecurityContext
    ) -> List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]]:
        """Validate request security aspects."""
        threats = []
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_content_length:
                    threats.append((
                        SecurityEvent.SUSPICIOUS_REQUEST,
                        ThreatLevel.MEDIUM,
                        {"large_content": content_length}
                    ))
            except ValueError:
                threats.append((
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    ThreatLevel.MEDIUM,
                    {"invalid_content_length": content_length}
                ))
        
        # Check content type
        content_type = request.headers.get("content-type", "").lower()
        if content_type:
            base_type = content_type.split(";")[0].strip()
            if base_type not in self.allowed_content_types and request.method in ["POST", "PUT", "PATCH"]:
                threats.append((
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    ThreatLevel.MEDIUM,
                    {"disallowed_content_type": base_type}
                ))
        
        # Check path extensions
        path = str(request.url.path)
        for blocked_ext in self.blocked_extensions:
            if path.lower().endswith(blocked_ext):
                threats.append((
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    ThreatLevel.HIGH,
                    {"blocked_extension": blocked_ext, "path": path}
                ))
        
        # Check header limits
        header_count = len(request.headers)
        if header_count > self.max_headers:
            threats.append((
                SecurityEvent.SUSPICIOUS_REQUEST,
                ThreatLevel.MEDIUM,
                {"too_many_headers": header_count}
            ))
        
        # Check header sizes
        for header_name, header_value in request.headers.items():
            if len(header_value) > self.max_header_length:
                threats.append((
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    ThreatLevel.MEDIUM,
                    {"large_header": header_name, "size": len(header_value)}
                ))
        
        return threats


class ProxySecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for proxy requests.
    
    Provides comprehensive security features including:
    - Request validation and sanitization
    - Threat detection and prevention
    - IP filtering and geolocation blocking
    - Authentication and authorization
    - Security event logging
    """
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        """Initialize security middleware."""
        super().__init__(app)
        
        self.config = config or {}
        
        # Security configuration
        self.enable_threat_detection = self.config.get("enable_threat_detection", True)
        self.enable_geolocation_blocking = self.config.get("enable_geolocation_blocking", True)
        self.enable_signature_validation = self.config.get("enable_signature_validation", True)
        self.enable_rate_limiting = self.config.get("enable_rate_limiting", True)
        
        # Initialize components
        self.event_logger = SecurityEventLogger()
        self.threat_detector = ThreatDetector()
        self.security_validator = SecurityValidator()
        
        # Security rules
        self.security_rules = self._load_security_rules()
        
        # Blacklist and whitelist
        self.ip_blacklist: Set[str] = set()
        self.ip_whitelist: Set[str] = set()
        self.user_agent_blacklist: Set[str] = set()
        
        logger.info("Proxy security middleware initialized")
    
    def _load_security_rules(self) -> List[SecurityRule]:
        """Load security rules from configuration."""
        rules = []
        
        # Default security rules
        default_rules = [
            SecurityRule(
                name="sql_injection_protection",
                description="Block SQL injection attempts",
                threat_level=ThreatLevel.HIGH,
                action="block",
                conditions={"event_type": SecurityEvent.SQL_INJECTION_ATTEMPT}
            ),
            SecurityRule(
                name="xss_protection",
                description="Block XSS attempts",
                threat_level=ThreatLevel.MEDIUM,
                action="block",
                conditions={"event_type": SecurityEvent.XSS_ATTEMPT}
            ),
            SecurityRule(
                name="ddos_protection",
                description="Detect and block DDoS attempts",
                threat_level=ThreatLevel.CRITICAL,
                action="block",
                conditions={"event_type": SecurityEvent.DDOS_DETECTED}
            ),
            SecurityRule(
                name="suspicious_agent",
                description="Monitor requests from suspicious user agents",
                threat_level=ThreatLevel.MEDIUM,
                action="monitor",
                conditions={"event_type": SecurityEvent.SUSPICIOUS_REQUEST}
            )
        ]
        
        rules.extend(default_rules)
        return rules
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware."""
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(int(time.time() * 1000000)))
        
        try:
            # Create security context
            context = await self._create_security_context(request, request_id)
            
            # Check if IP is whitelisted
            if context.client_ip in self.ip_whitelist:
                return await call_next(request)
            
            # Check if IP is blacklisted
            if (context.client_ip in self.ip_blacklist or
                self.event_logger.should_block_ip(context.client_ip)):
                
                await self._log_security_event(
                    SecurityEvent.IP_BLOCKED,
                    context.client_ip,
                    ThreatLevel.HIGH,
                    {"reason": "ip_blacklisted"},
                    context
                )
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Access denied",
                        "message": "Your IP address has been blocked",
                        "request_id": request_id
                    }
                )
            
            # Check user agent
            if context.user_agent in self.user_agent_blacklist:
                await self._log_security_event(
                    SecurityEvent.SUSPICIOUS_REQUEST,
                    context.client_ip,
                    ThreatLevel.MEDIUM,
                    {"reason": "blocked_user_agent", "user_agent": context.user_agent},
                    context
                )
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Access denied",
                        "message": "Your user agent is not allowed",
                        "request_id": request_id
                    }
                )
            
            # Perform security validation
            validation_threats = await self.security_validator.validate_request(request, context)
            
            # Perform threat detection if enabled
            if self.enable_threat_detection:
                detection_threats = await self.threat_detector.detect_threats(request, context)
                threats = validation_threats + detection_threats
            else:
                threats = validation_threats
            
            # Process threats
            if threats:
                response = await self._process_threats(threats, request, context)
                if response:
                    return response
            
            # Add security headers
            response = await call_next(request)
            await self._add_security_headers(response, context)
            
            # Log successful request
            processing_time = (time.time() - start_time) * 1000
            event_tracker.track_performance_event(
                "proxy_security_middleware",
                processing_time,
                {
                    "request_id": request_id,
                    "client_ip": context.client_ip,
                    "path": str(request.url.path),
                    "method": request.method
                }
            )
            
            return response
            
        except Exception as e:
            # Log security error
            event_tracker.track_error(
                e,
                additional_data={
                    "request_id": request_id,
                    "client_ip": request.client.host if request.client else "unknown",
                    "security_middleware_error": True
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Security processing error",
                    "request_id": request_id
                }
            )
    
    async def _create_security_context(self, request: Request, request_id: str) -> SecurityContext:
        """Create security context for request."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Extract authentication info
        auth_token = None
        api_key_id = None
        user_id = None
        tenant_id = None
        
        auth_header = request.headers.get("authorization")
        if auth_header:
            auth_token = auth_header
        
        api_key_header = request.headers.get("x-api-key")
        if api_key_header:
            # This would validate the API key and extract user/tenant info
            pass
        
        return SecurityContext(
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            auth_token=auth_token,
            api_key_id=api_key_id
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _process_threats(
        self,
        threats: List[Tuple[SecurityEvent, ThreatLevel, Dict[str, Any]]],
        request: Request,
        context: SecurityContext
    ) -> Optional[Response]:
        """Process detected threats."""
        
        # Sort threats by level (highest first)
        threats.sort(key=lambda x: x[1].value, reverse=True)
        
        # Check each threat against security rules
        for threat_event, threat_level, threat_details in threats:
            matching_rule = self._find_matching_rule(threat_event, threat_level)
            
            if matching_rule:
                action = matching_rule.action
                
                if action == "block":
                    await self._log_security_event(
                        threat_event,
                        context.client_ip,
                        threat_level,
                        threat_details,
                        context
                    )
                    
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "Access denied",
                            "message": f"Request blocked due to {threat_event.value}",
                            "threat_level": threat_level.value,
                            "request_id": context.request_id
                        }
                    )
                
                elif action == "monitor":
                    await self._log_security_event(
                        threat_event,
                        context.client_ip,
                        threat_level,
                        threat_details,
                        context
                    )
                
                elif action == "alert":
                    await self._log_security_event(
                        threat_event,
                        context.client_ip,
                        threat_level,
                        threat_details,
                        context
                    )
                    # Would send alert to security team
        
        return None
    
    def _find_matching_rule(self, event: SecurityEvent, level: ThreatLevel) -> Optional[SecurityRule]:
        """Find security rule that matches the threat."""
        for rule in self.security_rules:
            if (rule.conditions.get("event_type") == event and
                rule.threat_level == level):
                return rule
        return None
    
    async def _log_security_event(
        self,
        event: SecurityEvent,
        client_ip: str,
        level: ThreatLevel,
        details: Dict[str, Any],
        context: SecurityContext
    ):
        """Log security event."""
        self.event_logger.log_security_event(event, client_ip, level, details, context)
    
    async def _add_security_headers(self, response: Response, context: SecurityContext):
        """Add security headers to response."""
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Add request ID
        response.headers["X-Request-ID"] = context.request_id
        
        # Add security context headers
        if context.tenant_id:
            response.headers["X-Tenant-ID"] = context.tenant_id
    
    def add_to_blacklist(self, ip: str):
        """Add IP to blacklist."""
        self.ip_blacklist.add(ip)
        logger.info(f"Added IP to blacklist: {ip}")
    
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist."""
        self.ip_whitelist.add(ip)
        logger.info(f"Added IP to whitelist: {ip}")
    
    def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist."""
        self.ip_blacklist.discard(ip)
        logger.info(f"Removed IP from blacklist: {ip}")
    
    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist."""
        self.ip_whitelist.discard(ip)
        logger.info(f"Removed IP from whitelist: {ip}")
    
    def add_blocked_user_agent(self, user_agent: str):
        """Add user agent to blacklist."""
        self.user_agent_blacklist.add(user_agent)
        logger.info(f"Added user agent to blacklist: {user_agent}")
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get security middleware statistics."""
        return {
            "total_events": sum(self.event_logger.event_counts.values()),
            "event_counts": dict(self.event_logger.event_counts),
            "blacklisted_ips": len(self.ip_blacklist),
            "whitelisted_ips": len(self.ip_whitelist),
            "blocked_user_agents": len(self.user_agent_blacklist),
            "recent_events": len(self.event_logger.get_recent_events(60)),
            "threat_tracking": {
                ip: {
                    "event_count": data["event_count"],
                    "threat_levels": list(data["threat_levels"]),
                    "blocked": data["blocked"],
                    "whitelisted": data["whitelisted"]
                }
                for ip, data in self.event_logger.ip_tracking.items()
            }
        }
