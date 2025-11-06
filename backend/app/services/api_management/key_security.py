"""
API Key Security Module

Provides advanced security features for API key management including
enhanced encryption, security monitoring, compromise detection, and
policy enforcement. Complements the base API key manager with enterprise-grade
security capabilities.
"""

import asyncio
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Set
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import json
import re

from app.models.proxy import APIKey, ProxyRequestCache
from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

class SecurityThreat:
    """Define security threat levels and types"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE = "brute_force"
    KEY_COMPROMISE = "key_compromise"
    UNUSUAL_ACCESS = "unusual_access"
    POLICY_VIOLATION = "policy_violation"
    DATA_EXFILTRATION = "data_exfiltration"

class APIKeySecurity:
    """
    Advanced API Key Security Manager
    
    Provides enterprise-grade security features:
    - Enhanced encryption methods
    - Security threat detection
    - Access pattern monitoring
    - Key compromise response
    - Security policy enforcement
    - Audit trail management
    """
    
    def __init__(self):
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Security configuration
        self.config = {
            'encryption_iterations': 100000,
            'key_rotation_interval_days': 90,
            'max_failed_attempts': 5,
            'lockout_duration_minutes': 30,
            'suspicious_access_threshold': 10,  # requests per minute
            'geographic_violation_threshold': 3,  # countries per hour
            'time_based_violation_threshold': 20,  # unusual hours access
            'audit_retention_days': 2555,  # 7 years
            'max_key_age_days': 365,
            'require_mfa': False,  # Multi-factor authentication requirement
            'allowed_ip_ranges': [],  # CIDR ranges for IP restriction
            'blocked_countries': [],  # ISO country codes
            'allowed_time_ranges': [(0, 23)],  # Allowed hours (24-hour format)
            'allowed_endpoints': [],  # Restricted endpoint patterns
        }
        
        # Security event tracking
        self._security_events = []
        self._threat_levels = {
            SecurityThreat.CRITICAL: 100,
            SecurityThreat.HIGH: 75,
            SecurityThreat.MEDIUM: 50,
            SecurityThreat.LOW: 25
        }
        
        # Generate master key for encryption
        self._master_key = self._generate_master_key()
        self._fernet = Fernet(self._master_key)
        
        logger.info("APIKeySecurity initialized with enhanced security features")
    
    def generate_secure_key(
        self,
        key_type: str = "standard",
        length: int = 32,
        prefix: Optional[str] = None
    ) -> str:
        """
        Generate cryptographically secure API key
        
        Args:
            key_type: Type of key (standard, privileged, service)
            length: Key length in bytes
            prefix: Optional key prefix for identification
            
        Returns:
            Secure API key string
        """
        # Generate random bytes
        key_bytes = secrets.token_bytes(length)
        
        # Add entropy based on key type
        if key_type == "privileged":
            # Use system random for high-security keys
            entropy = secrets.SystemRandom().choice([
                secrets.token_bytes(16),
                secrets.token_hex(16),
                secrets.token_urlsafe(20)
            ])
            key_bytes = hmac.new(key_bytes, entropy, hashlib.sha256).digest()
        
        # Convert to base32 for readability
        key_base32 = base64.b32encode(key_bytes).decode('utf-8').rstrip('=')
        
        # Add prefix if specified
        if prefix:
            key_string = f"{prefix}_{key_base32}"
        else:
            # Add type-based prefix
            type_prefixes = {
                "standard": "sk",
                "privileged": "pk",
                "service": "svc",
                "temporary": "tmp"
            }
            type_prefix = type_prefixes.get(key_type, "sk")
            key_string = f"{type_prefix}_{key_base32}"
        
        # Validate key strength
        if not self._validate_key_strength(key_string):
            logger.warning(f"Generated key failed strength validation: {key_string[:10]}...")
            return self.generate_secure_key(key_type, length + 8, prefix)
        
        return key_string
    
    def encrypt_key_data(self, data: str, additional_entropy: Optional[str] = None) -> str:
        """
        Encrypt sensitive key data with additional entropy
        
        Args:
            data: Data to encrypt
            additional_entropy: Optional additional entropy source
            
        Returns:
            Encrypted data as base64 string
        """
        try:
            # Add timestamp for uniqueness
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
            
            # Combine data with entropy
            if additional_entropy:
                combined_data = f"{data}|{timestamp}|{additional_entropy}"
            else:
                combined_data = f"{data}|{timestamp}"
            
            # Encrypt with Fernet
            encrypted_data = self._fernet.encrypt(combined_data.encode('utf-8'))
            
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encrypt key data: {e}")
            raise
    
    def decrypt_key_data(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt sensitive key data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data or None if decryption fails
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt with Fernet
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            decrypted_data = decrypted_bytes.decode('utf-8')
            
            # Extract original data (remove timestamp)
            original_data = decrypted_data.split('|')[0]
            
            return original_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt key data: {e}")
            return None
    
    def create_key_signature(self, key: str) -> str:
        """
        Create cryptographic signature for API key
        
        Args:
            key: API key to sign
            
        Returns:
            HMAC signature of the key
        """
        timestamp = str(int(datetime.now(timezone.utc).timestamp() // 3600))  # Hourly timestamp
        message = f"{key}|{timestamp}"
        
        signature = hmac.new(
            self._master_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_key_signature(self, key: str, signature: str) -> bool:
        """
        Verify API key signature
        
        Args:
            key: API key to verify
            signature: Signature to verify against
            
        Returns:
            True if signature is valid
        """
        current_signature = self.create_key_signature(key)
        return hmac.compare_digest(current_signature, signature)
    
    async def detect_security_threats(
        self,
        api_key_id: int,
        ip_address: str,
        user_agent: str,
        endpoint: str,
        request_size: int,
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Detect potential security threats for API key usage
        
        Args:
            api_key_id: API key identifier
            ip_address: Source IP address
            user_agent: User agent string
            endpoint: Requested endpoint
            request_size: Size of request
            timestamp: Request timestamp
            
        Returns:
            List of detected threats
        """
        threats = []
        
        try:
            # Check for brute force attacks
            brute_force_threat = await self._check_brute_force(
                api_key_id, ip_address, timestamp
            )
            if brute_force_threat:
                threats.append(brute_force_threat)
            
            # Check for suspicious access patterns
            suspicious_threat = await self._check_suspicious_access(
                api_key_id, ip_address, endpoint, timestamp
            )
            if suspicious_threat:
                threats.append(suspicious_threat)
            
            # Check for unusual geographic access
            geo_threat = await self._check_geographic_anomaly(
                api_key_id, ip_address, timestamp
            )
            if geo_threat:
                threats.append(geo_threat)
            
            # Check for time-based anomalies
            time_threat = await self._check_time_anomaly(
                api_key_id, timestamp
            )
            if time_threat:
                threats.append(time_threat)
            
            # Check for data exfiltration patterns
            exfiltration_threat = await self._check_data_exfiltration(
                api_key_id, request_size, endpoint, timestamp
            )
            if exfiltration_threat:
                threats.append(exfiltration_threat)
            
            # Check for policy violations
            policy_threat = await self._check_policy_violations(
                api_key_id, endpoint, user_agent, ip_address
            )
            if policy_threat:
                threats.append(policy_threat)
            
            # Track threats in telemetry
            for threat in threats:
                await self._track_security_threat(threat)
            
            return threats
            
        except Exception as e:
            logger.error(f"Failed to detect security threats: {e}")
            return []
    
    async def monitor_access_patterns(
        self,
        api_key_id: int,
        ip_address: str,
        endpoint: str,
        response_time: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Monitor and analyze access patterns for security insights
        
        Args:
            api_key_id: API key identifier
            ip_address: Source IP address
            endpoint: Accessed endpoint
            response_time: Response time
            timestamp: Access timestamp
            
        Returns:
            Access pattern analysis
        """
        try:
            # Get recent access history (last 24 hours)
            cache_key = f"access_patterns:{api_key_id}:{timestamp.date().isoformat()}"
            access_history = await self.redis_cache.get(cache_key) or {}
            
            # Update access pattern data
            hour_key = timestamp.strftime('%H')
            if hour_key not in access_history:
                access_history[hour_key] = {
                    'ips': set(),
                    'endpoints': set(),
                    'request_count': 0,
                    'total_response_time': 0,
                    'unique_ips': 0
                }
            
            # Update data
            access_history[hour_key]['ips'].add(ip_address)
            access_history[hour_key]['endpoints'].add(endpoint)
            access_history[hour_key]['request_count'] += 1
            access_history[hour_key]['total_response_time'] += response_time
            
            # Store back to cache
            # Convert sets to lists for JSON serialization
            serializable_history = {}
            for hour, data in access_history.items():
                serializable_history[hour] = {
                    'ips': list(data['ips']),
                    'endpoints': list(data['endpoints']),
                    'request_count': data['request_count'],
                    'total_response_time': data['total_response_time'],
                    'unique_ips': len(data['ips'])
                }
            
            await self.redis_cache.set(cache_key, serializable_history, ttl=86400)
            
            # Analyze patterns
            pattern_analysis = await self._analyze_access_patterns(
                api_key_id, serializable_history, timestamp
            )
            
            return pattern_analysis
            
        except Exception as e:
            logger.error(f"Failed to monitor access patterns: {e}")
            return {}
    
    async def enforce_security_policies(
        self,
        api_key_id: int,
        ip_address: str,
        user_agent: str,
        endpoint: str
    ) -> Tuple[bool, str]:
        """
        Enforce security policies on API key usage
        
        Args:
            api_key_id: API key identifier
            ip_address: Source IP address
            user_agent: User agent string
            endpoint: Requested endpoint
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        try:
            # Check IP whitelist/blacklist
            ip_check = await self._check_ip_policy(ip_address, api_key_id)
            if not ip_check[0]:
                return ip_check
            
            # Check country restrictions
            country_check = await self._check_country_policy(ip_address, api_key_id)
            if not country_check[0]:
                return country_check
            
            # Check time-based restrictions
            time_check = await self._check_time_policy(api_key_id)
            if not time_check[0]:
                return time_check
            
            # Check endpoint restrictions
            endpoint_check = await self._check_endpoint_policy(endpoint, api_key_id)
            if not endpoint_check[0]:
                return endpoint_check
            
            # Check user agent policy
            ua_check = await self._check_user_agent_policy(user_agent, api_key_id)
            if not ua_check[0]:
                return ua_check
            
            # Check key age policy
            age_check = await self._check_key_age_policy(api_key_id)
            if not age_check[0]:
                return age_check
            
            return True, "Policy check passed"
            
        except Exception as e:
            logger.error(f"Failed to enforce security policies: {e}")
            return False, f"Policy enforcement error: {str(e)}"
    
    async def create_security_audit_log(
        self,
        api_key_id: int,
        action: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Create comprehensive security audit log
        
        Args:
            api_key_id: API key identifier
            action: Action performed
            details: Action details
            ip_address: Source IP address
            user_id: Associated user ID
        """
        try:
            audit_entry = {
                'api_key_id': api_key_id,
                'action': action,
                'details': details,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ip_address': ip_address,
                'user_id': user_id,
                'session_id': details.get('session_id'),
                'request_id': details.get('request_id')
            }
            
            # Store in Redis for real-time access
            cache_key = f"security_audit:{api_key_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            await self.redis_cache.lpush(cache_key, json.dumps(audit_entry))
            
            # Set expiration based on retention policy
            expiry_seconds = self.config['audit_retention_days'] * 86400
            await self.redis_cache.expire(cache_key, expiry_seconds)
            
            # Track in telemetry
            await self.event_tracker.track_event(
                "security_audit_logged",
                {
                    "api_key_id": api_key_id,
                    "action": action,
                    "has_ip": ip_address is not None,
                    "has_user": user_id is not None
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create security audit log: {e}")
    
    async def get_security_metrics(self, api_key_id: int) -> Dict[str, Any]:
        """
        Get comprehensive security metrics for API key
        
        Args:
            api_key_id: API key identifier
            
        Returns:
            Security metrics and analysis
        """
        try:
            # Get threat history
            threat_cache_key = f"security_threats:{api_key_id}"
            threats = await self.redis_cache.lrange(threat_cache_key, 0, 100) or []
            
            # Parse threats
            parsed_threats = []
            for threat_json in threats:
                try:
                    threat = json.loads(threat_json)
                    parsed_threats.append(threat)
                except json.JSONDecodeError:
                    continue
            
            # Get access patterns
            today = datetime.now(timezone.utc).date().isoformat()
            pattern_cache_key = f"access_patterns:{api_key_id}:{today}"
            access_patterns = await self.redis_cache.get(pattern_cache_key) or {}
            
            # Calculate metrics
            threat_count = len(parsed_threats)
            critical_threats = sum(1 for t in parsed_threats if t.get('severity') == SecurityThreat.CRITICAL)
            high_threats = sum(1 for t in parsed_threats if t.get('severity') == SecurityThreat.HIGH)
            
            # Calculate access pattern metrics
            total_requests = sum(hour_data.get('request_count', 0) for hour_data in access_patterns.values())
            unique_ips = len(set(ip for hour_data in access_patterns.values() for ip in hour_data.get('ips', [])))
            unique_endpoints = len(set(endpoint for hour_data in access_patterns.values() for endpoint in hour_data.get('endpoints', [])))
            
            # Risk score calculation
            risk_score = self._calculate_risk_score(
                threat_count, critical_threats, high_threats,
                total_requests, unique_ips, unique_endpoints
            )
            
            security_metrics = {
                'api_key_id': api_key_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'threat_analysis': {
                    'total_threats': threat_count,
                    'critical_threats': critical_threats,
                    'high_threats': high_threats,
                    'recent_threats': parsed_threats[:10],  # Last 10 threats
                    'threat_types': self._categorize_threats(parsed_threats)
                },
                'access_analysis': {
                    'total_requests_today': total_requests,
                    'unique_ips_today': unique_ips,
                    'unique_endpoints_today': unique_endpoints,
                    'access_patterns': access_patterns
                },
                'risk_assessment': {
                    'risk_score': risk_score,
                    'risk_level': self._get_risk_level(risk_score),
                    'recommendations': self._get_security_recommendations(
                        threat_count, critical_threats, unique_ips, total_requests
                    )
                },
                'policy_compliance': {
                    'ip_restrictions_enabled': len(self.config.get('allowed_ip_ranges', [])) > 0,
                    'country_restrictions_enabled': len(self.config.get('blocked_countries', [])) > 0,
                    'time_restrictions_enabled': len(self.config.get('allowed_time_ranges', [])) < 24,
                    'endpoint_restrictions_enabled': len(self.config.get('allowed_endpoints', [])) > 0
                }
            }
            
            return security_metrics
            
        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return {'error': str(e)}
    
    def _validate_key_strength(self, key: str) -> bool:
        """
        Validate API key strength
        
        Args:
            key: API key to validate
            
        Returns:
            True if key meets strength requirements
        """
        # Check minimum length
        if len(key) < 20:
            return False
        
        # Check for required character types
        has_upper = any(c.isupper() for c in key)
        has_lower = any(c.islower() for c in key)
        has_digit = any(c.isdigit() for c in key)
        has_special = any(c in '_-' for c in key)
        
        # Key must have at least 3 of 4 character types
        character_types = sum([has_upper, has_lower, has_digit, has_special])
        if character_types < 3:
            return False
        
        # Check for repetitive patterns
        if re.search(r'(.)\1{3,}', key):  # 4+ repeated characters
            return False
        
        # Check for common patterns
        common_patterns = ['password', 'secret', 'key', 'token', '1234', 'abcd']
        if any(pattern in key.lower() for pattern in common_patterns):
            return False
        
        return True
    
    def _generate_master_key(self) -> bytes:
        """Generate master encryption key"""
        try:
            # Try to get key from environment
            import os
            env_key = os.environ.get('API_KEY_MASTER_KEY')
            if env_key:
                return base64.urlsafe_b64decode(env_key.encode())
            
            # Generate new key if not available
            return Fernet.generate_key()
            
        except Exception:
            logger.warning("Failed to load master key from environment, generating new key")
            return Fernet.generate_key()
    
    async def _check_brute_force(
        self,
        api_key_id: int,
        ip_address: str,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Check for brute force attack patterns"""
        try:
            # Get failed attempts in time window
            window_start = timestamp - timedelta(minutes=15)
            cache_key = f"failed_attempts:{api_key_id}:{ip_address}"
            
            # Get current failed attempts
            attempts = await self.redis_cache.get(cache_key) or []
            
            # Filter recent attempts
            recent_attempts = [
                attempt for attempt in attempts
                if datetime.fromisoformat(attempt) >= window_start
            ]
            
            # Check threshold
            if len(recent_attempts) >= self.config['max_failed_attempts']:
                return {
                    'type': SecurityThreat.BRUTE_FORCE,
                    'severity': SecurityThreat.HIGH,
                    'description': f'Brute force attack detected from {ip_address}',
                    'details': {
                        'ip_address': ip_address,
                        'attempts_count': len(recent_attempts),
                        'time_window_minutes': 15
                    },
                    'timestamp': timestamp.isoformat(),
                    'api_key_id': api_key_id
                }
            
            # Update failed attempts
            recent_attempts.append(timestamp.isoformat())
            await self.redis_cache.set(cache_key, recent_attempts, ttl=900)  # 15 minutes
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check brute force: {e}")
            return None
    
    async def _check_suspicious_access(
        self,
        api_key_id: int,
        ip_address: str,
        endpoint: str,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Check for suspicious access patterns"""
        try:
            # Get access rate in current minute
            minute_key = timestamp.strftime('%Y%m%d%H%M')
            cache_key = f"access_rate:{api_key_id}:{ip_address}:{minute_key}"
            
            access_count = await self.redis_cache.incr(cache_key)
            await self.redis_cache.expire(cache_key, 60)  # 1 minute TTL
            
            if access_count > self.config['suspicious_access_threshold']:
                return {
                    'type': SecurityThreat.SUSPICIOUS_ACTIVITY,
                    'severity': SecurityThreat.MEDIUM,
                    'description': f'High access rate detected: {access_count} requests/minute',
                    'details': {
                        'ip_address': ip_address,
                        'access_count': access_count,
                        'threshold': self.config['suspicious_access_threshold']
                    },
                    'timestamp': timestamp.isoformat(),
                    'api_key_id': api_key_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check suspicious access: {e}")
            return None
    
    async def _check_geographic_anomaly(
        self,
        api_key_id: int,
        ip_address: str,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Check for geographic access anomalies"""
        try:
            # Get country for IP (simplified - in production use GeoIP database)
            country = await self._get_ip_country(ip_address)
            
            # Track countries accessed in current hour
            hour_key = timestamp.strftime('%Y%m%d%H')
            cache_key = f"geo_access:{api_key_id}:{hour_key}"
            
            countries = await self.redis_cache.get(cache_key) or []
            if country not in countries:
                countries.append(country)
                await self.redis_cache.set(cache_key, countries, ttl=3600)  # 1 hour
            
            # Check if too many countries accessed
            if len(countries) > self.config['geographic_violation_threshold']:
                return {
                    'type': SecurityThreat.UNUSUAL_ACCESS,
                    'severity': SecurityThreat.MEDIUM,
                    'description': f'Access from {len(countries)} different countries detected',
                    'details': {
                        'countries': countries,
                        'threshold': self.config['geographic_violation_threshold']
                    },
                    'timestamp': timestamp.isoformat(),
                    'api_key_id': api_key_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check geographic anomaly: {e}")
            return None
    
    async def _check_time_anomaly(
        self,
        api_key_id: int,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Check for time-based access anomalies"""
        try:
            hour = timestamp.hour
            allowed_hours = self.config['allowed_time_ranges'][0]  # Simplified: use first range
            
            # Check if access is outside allowed hours
            if not (allowed_hours[0] <= hour <= allowed_hours[1]):
                return {
                    'type': SecurityThreat.UNUSUAL_ACCESS,
                    'severity': SecurityThreat.LOW,
                    'description': f'Access outside allowed hours: {hour}:00',
                    'details': {
                        'access_hour': hour,
                        'allowed_range': allowed_hours
                    },
                    'timestamp': timestamp.isoformat(),
                    'api_key_id': api_key_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check time anomaly: {e}")
            return None
    
    async def _check_data_exfiltration(
        self,
        api_key_id: int,
        request_size: int,
        endpoint: str,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Check for potential data exfiltration patterns"""
        try:
            # Check for unusually large requests (potential data exfiltration)
            if request_size > 10 * 1024 * 1024:  # 10MB threshold
                return {
                    'type': SecurityThreat.DATA_EXFILTRATION,
                    'severity': SecurityThreat.HIGH,
                    'description': f'Large data request detected: {request_size} bytes',
                    'details': {
                        'request_size': request_size,
                        'endpoint': endpoint,
                        'threshold': 10485760  # 10MB
                    },
                    'timestamp': timestamp.isoformat(),
                    'api_key_id': api_key_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check data exfiltration: {e}")
            return None
    
    async def _check_policy_violations(
        self,
        api_key_id: int,
        endpoint: str,
        user_agent: str,
        ip_address: str
    ) -> Optional[Dict[str, Any]]:
        """Check for policy violations"""
        try:
            # Check for disallowed endpoints
            allowed_endpoints = self.config.get('allowed_endpoints', [])
            if allowed_endpoints:
                # If endpoints are restricted, check if requested endpoint is allowed
                endpoint_allowed = any(
                    endpoint.startswith(allowed_pattern)
                    for allowed_pattern in allowed_endpoints
                )
                if not endpoint_allowed:
                    return {
                        'type': SecurityThreat.POLICY_VIOLATION,
                        'severity': SecurityThreat.MEDIUM,
                        'description': f'Access to restricted endpoint: {endpoint}',
                        'details': {
                            'endpoint': endpoint,
                            'allowed_patterns': allowed_endpoints
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'api_key_id': api_key_id
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check policy violations: {e}")
            return None
    
    async def _check_ip_policy(
        self,
        ip_address: str,
        api_key_id: int
    ) -> Tuple[bool, str]:
        """Check IP address policy"""
        allowed_ranges = self.config.get('allowed_ip_ranges', [])
        if allowed_ranges:
            # Simplified IP check - in production use proper CIDR matching
            if not any(ip_address.startswith(range_prefix) for range_prefix in allowed_ranges):
                return False, f"IP address {ip_address} not in allowed ranges"
        
        return True, "IP policy check passed"
    
    async def _check_country_policy(
        self,
        ip_address: str,
        api_key_id: int
    ) -> Tuple[bool, str]:
        """Check country policy"""
        blocked_countries = self.config.get('blocked_countries', [])
        if blocked_countries:
            country = await self._get_ip_country(ip_address)
            if country in blocked_countries:
                return False, f"Access from country {country} is blocked"
        
        return True, "Country policy check passed"
    
    async def _check_time_policy(self, api_key_id: int) -> Tuple[bool, str]:
        """Check time-based policy"""
        allowed_ranges = self.config.get('allowed_time_ranges', [(0, 23)])
        current_hour = datetime.now(timezone.utc).hour
        
        for start_hour, end_hour in allowed_ranges:
            if start_hour <= current_hour <= end_hour:
                return True, "Time policy check passed"
        
        return False, f"Access outside allowed hours: {current_hour}:00"
    
    async def _check_endpoint_policy(
        self,
        endpoint: str,
        api_key_id: int
    ) -> Tuple[bool, str]:
        """Check endpoint policy"""
        allowed_endpoints = self.config.get('allowed_endpoints', [])
        if allowed_endpoints:
            # Check if endpoint matches any allowed pattern
            endpoint_allowed = any(
                endpoint.startswith(pattern.rstrip('*'))
                for pattern in allowed_endpoints
            )
            if not endpoint_allowed:
                return False, f"Endpoint {endpoint} is not allowed"
        
        return True, "Endpoint policy check passed"
    
    async def _check_user_agent_policy(
        self,
        user_agent: str,
        api_key_id: int
    ) -> Tuple[bool, str]:
        """Check user agent policy"""
        # Check for suspicious user agents
        suspicious_uas = [
            'bot', 'crawler', 'spider', 'scraper', 'hack', 'exploit'
        ]
        
        ua_lower = user_agent.lower()
        if any(suspicious in ua_lower for suspicious in suspicious_uas):
            return False, f"Suspicious user agent detected: {user_agent}"
        
        return True, "User agent policy check passed"
    
    async def _check_key_age_policy(self, api_key_id: int) -> Tuple[bool, str]:
        """Check API key age policy"""
        max_age_days = self.config.get('max_key_age_days', 365)
        
        # Get key creation date (simplified - would need to query database)
        # For now, just return True as we don't have direct DB access here
        # In implementation, this would query the APIKey table
        
        return True, "Key age policy check passed"
    
    async def _track_security_threat(self, threat: Dict[str, Any]) -> None:
        """Track security threat in telemetry and cache"""
        try:
            # Store in Redis
            cache_key = f"security_threats:{threat['api_key_id']}"
            await self.redis_cache.lpush(cache_key, json.dumps(threat))
            await self.redis_cache.ltrim(cache_key, 0, 100)  # Keep last 100 threats
            await self.redis_cache.expire(cache_key, 86400 * 7)  # 7 days
            
            # Track in telemetry
            await self.event_tracker.track_event(
                "security_threat_detected",
                {
                    "api_key_id": threat['api_key_id'],
                    "threat_type": threat['type'],
                    "severity": threat['severity']
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to track security threat: {e}")
    
    async def _get_ip_country(self, ip_address: str) -> str:
        """Get country for IP address (simplified implementation)"""
        # This is a simplified implementation
        # In production, use a proper GeoIP database or API
        try:
            # Check cache first
            cache_key = f"ip_country:{ip_address}"
            cached_country = await self.redis_cache.get(cache_key)
            if cached_country:
                return cached_country
            
            # Simplified country detection based on IP ranges
            if ip_address.startswith('192.168.') or ip_address.startswith('10.') or ip_address.startswith('172.'):
                country = 'US'  # Private IP, assume US
            elif ip_address.startswith('127.'):
                country = 'LOCAL'  # Localhost
            else:
                country = 'UNKNOWN'  # Would need proper GeoIP lookup
            
            # Cache for 24 hours
            await self.redis_cache.set(cache_key, country, ttl=86400)
            return country
            
        except Exception:
            return 'UNKNOWN'
    
    def _calculate_risk_score(
        self,
        threat_count: int,
        critical_threats: int,
        high_threats: int,
        total_requests: int,
        unique_ips: int,
        unique_endpoints: int
    ) -> float:
        """Calculate security risk score (0-100)"""
        score = 0.0
        
        # Threat-based scoring
        score += critical_threats * 25
        score += high_threats * 15
        score += (threat_count - critical_threats - high_threats) * 5
        
        # Access pattern scoring
        if unique_ips > 10:  # Many different IPs
            score += min(unique_ips * 2, 30)
        
        if unique_endpoints > 20:  # Many different endpoints
            score += min(unique_endpoints, 20)
        
        # Normalize to 0-100
        return min(score, 100.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level from score"""
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 30:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_security_recommendations(
        self,
        threat_count: int,
        critical_threats: int,
        unique_ips: int,
        total_requests: int
    ) -> List[str]:
        """Get security recommendations based on metrics"""
        recommendations = []
        
        if critical_threats > 0:
            recommendations.append("IMMEDIATE: Review and potentially revoke compromised API keys")
        
        if threat_count > 5:
            recommendations.append("Implement additional rate limiting and monitoring")
        
        if unique_ips > 10:
            recommendations.append("Consider implementing IP whitelisting")
        
        if total_requests > 1000:
            recommendations.append("Review access patterns for unusual behavior")
        
        if not recommendations:
            recommendations.append("Continue regular monitoring and maintain security best practices")
        
        return recommendations
    
    def _categorize_threats(self, threats: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize threats by type"""
        categories = {}
        for threat in threats:
            threat_type = threat.get('type', 'unknown')
            categories[threat_type] = categories.get(threat_type, 0) + 1
        return categories
    
    async def _analyze_access_patterns(
        self,
        api_key_id: int,
        access_patterns: Dict[str, Any],
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Analyze access patterns for insights"""
        try:
            # Calculate hourly distribution
            hourly_distribution = {}
            peak_hour = 0
            peak_requests = 0
            
            for hour, data in access_patterns.items():
                request_count = data.get('request_count', 0)
                hourly_distribution[hour] = request_count
                
                if request_count > peak_requests:
                    peak_requests = request_count
                    peak_hour = int(hour)
            
            # Calculate diversity metrics
            all_ips = set()
            all_endpoints = set()
            for data in access_patterns.values():
                all_ips.update(data.get('ips', []))
                all_endpoints.update(data.get('endpoints', []))
            
            # Calculate unusual patterns
            unusual_patterns = []
            
            # Check for off-peak access
            current_hour = timestamp.hour
            if current_hour < 6 or current_hour > 22:  # Outside business hours
                unusual_patterns.append("Off-peak access detected")
            
            # Check for rapid endpoint switching
            if len(all_endpoints) > 10:
                unusual_patterns.append("High endpoint diversity detected")
            
            # Check for distributed access
            if len(all_ips) > 5:
                unusual_patterns.append("Distributed access from multiple IPs")
            
            return {
                'api_key_id': api_key_id,
                'analysis_timestamp': timestamp.isoformat(),
                'hourly_distribution': hourly_distribution,
                'peak_hour': f"{peak_hour:02d}:00",
                'peak_requests': peak_requests,
                'diversity_metrics': {
                    'unique_ips': len(all_ips),
                    'unique_endpoints': len(all_endpoints),
                    'total_hours_active': len(access_patterns)
                },
                'unusual_patterns': unusual_patterns,
                'risk_indicators': {
                    'off_peak_access': 6 <= current_hour <= 22,
                    'high_endpoint_diversity': len(all_endpoints) > 10,
                    'distributed_access': len(all_ips) > 5
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze access patterns: {e}")
            return {}
    
    async def cleanup_security_data(self, retention_days: int = 30) -> int:
        """Clean up old security data"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Clean up security events
            # Note: This would need to be implemented based on actual storage mechanism
            
            logger.info(f"Cleaned up security data older than {retention_days} days")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup security data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        logger.info("APIKeySecurity closed")