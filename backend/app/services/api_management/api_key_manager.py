"""
API Key Management System

Centralized API key storage, rotation, and security:
- Encrypted key storage
- Automated rotation with minimal downtime
- Usage analytics and cost tracking
- Health monitoring and failover
- Provider-specific key management

Features:
- AES encryption for key storage
- Minimal downtime key rotation
- Provider-specific authentication
- Usage analytics and cost tracking
- Key health monitoring
- Automatic failover to healthy keys
"""

import asyncio
import time
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.models.proxy import ApiKey, ApiKeyUsage, ApiKeyRotation
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    """API key status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class KeyType(Enum):
    """API key types."""
    LLM = "llm"
    OCR = "ocr"
    TOCONLINE = "toconline"
    STRIPE = "stripe"
    GENERIC = "generic"


class RotationStrategy(Enum):
    """Key rotation strategies."""
    IMMEDIATE = "immediate"  # Replace immediately
    OVERLAPPING = "overlapping"  # Both keys active during transition
    GRADUAL = "gradual"  # Gradually shift traffic
    SCHEDULED = "scheduled"  # Rotate at specific time


@dataclass
class KeyValidationResult:
    """Result of API key validation."""
    is_valid: bool
    key_status: KeyStatus
    provider_response: Dict[str, Any]
    response_time_ms: float
    error_message: Optional[str] = None
    health_score: float = 0.0


@dataclass
class UsageAnalytics:
    """API key usage analytics."""
    key_id: str
    period_start: datetime
    period_end: datetime
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    
    # Cost metrics
    total_cost: float = 0.0
    cost_per_request: float = 0.0
    
    # Health metrics
    success_rate: float = 100.0
    error_rate: float = 0.0
    health_score: float = 100.0


class KeyEncryption:
    """Handles API key encryption and decryption."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        """Initialize key encryption."""
        if master_key is None:
            master_key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(master_key)
        
        # For password-based key derivation (for additional security)
        self.salt = b'stable_salt_for_key_derivation'  # In production, use random salt
    
    def encrypt_key(self, api_key: str) -> str:
        """Encrypt API key."""
        try:
            encrypted_bytes = self.cipher_suite.encrypt(api_key.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise
    
    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt API key."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_key.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password."""
        if salt is None:
            salt = self.salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key


class KeyHealthMonitor:
    """Monitors API key health and performance."""
    
    def __init__(self, http_client=None):
        self.http_client = http_client
        self.health_cache: Dict[str, Dict[str, Any]] = {}
        self.health_cache_ttl = 300  # 5 minutes
        self.validation_history: Dict[str, List[KeyValidationResult]] = {}
    
    async def validate_api_key(
        self,
        api_key: ApiKey,
        test_endpoint: Optional[str] = None
    ) -> KeyValidationResult:
        """Validate API key by making test request."""
        start_time = time.time()
        
        try:
            decrypted_key = await self._decrypt_api_key(api_key)
            
            # Build validation request based on provider
            validation_request = await self._build_validation_request(
                api_key.provider, decrypted_key, test_endpoint
            )
            
            # Execute validation request
            if self.http_client:
                response = await self.http_client.request(**validation_request)
                response_time = (time.time() - start_time) * 1000
                
                # Parse response
                validation_result = await self._parse_validation_response(
                    api_key.provider, response
                )
            else:
                # Mock validation for testing
                response_time = (time.time() - start_time) * 1000
                validation_result = KeyValidationResult(
                    is_valid=True,
                    key_status=KeyStatus.HEALTHY,
                    provider_response={"status": "ok"},
                    response_time_ms=response_time
                )
            
            # Update health cache
            self.health_cache[api_key.id] = {
                "last_check": datetime.utcnow(),
                "result": validation_result,
                "response_time": response_time
            }
            
            # Store validation history
            if api_key.id not in self.validation_history:
                self.validation_history[api_key.id] = []
            
            self.validation_history[api_key.id].append(validation_result)
            
            # Keep only last 100 validations
            if len(self.validation_history[api_key.id]) > 100:
                self.validation_history[api_key.id] = self.validation_history[api_key.id][-100:]
            
            return validation_result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            validation_result = KeyValidationResult(
                is_valid=False,
                key_status=KeyStatus.UNHEALTHY,
                provider_response={},
                response_time_ms=response_time,
                error_message=str(e),
                health_score=0.0
            )
            
            # Update health cache
            self.health_cache[api_key.id] = {
                "last_check": datetime.utcnow(),
                "result": validation_result,
                "response_time": response_time
            }
            
            return validation_result
    
    async def _decrypt_api_key(self, api_key: ApiKey) -> str:
        """Decrypt API key (placeholder for actual implementation)."""
        # This would use the KeyEncryption class
        return "mock_decrypted_key"
    
    async def _build_validation_request(
        self,
        provider: str,
        decrypted_key: str,
        test_endpoint: Optional[str]
    ) -> Dict[str, Any]:
        """Build validation request for specific provider."""
        if provider == "openai":
            return {
                "method": "GET",
                "url": "https://api.openai.com/v1/models",
                "headers": {"Authorization": f"Bearer {decrypted_key}"}
            }
        elif provider == "azure":
            return {
                "method": "GET",
                "url": f"{test_endpoint}/openai/deployments",
                "headers": {"api-key": decrypted_key}
            }
        elif provider == "stripe":
            return {
                "method": "GET",
                "url": "https://api.stripe.com/v1/account",
                "headers": {"Authorization": f"Bearer {decrypted_key}"}
            }
        else:
            # Generic validation
            return {
                "method": "GET",
                "url": test_endpoint or "https://httpbin.org/get",
                "headers": {"X-API-Key": decrypted_key}
            }
    
    async def _parse_validation_response(
        self,
        provider: str,
        response
    ) -> KeyValidationResult:
        """Parse validation response from provider."""
        response_time_ms = 0  # This would be calculated from response
        
        try:
            if response.status_code == 200:
                # Determine health score based on provider response
                health_score = 100.0
                
                # Provider-specific health checks
                if provider == "openai":
                    # Check response for specific health indicators
                    try:
                        data = response.json()
                        if "data" in data and len(data["data"]) > 0:
                            health_score = 100.0
                        else:
                            health_score = 50.0
                    except:
                        health_score = 75.0
                
                return KeyValidationResult(
                    is_valid=True,
                    key_status=KeyStatus.HEALTHY,
                    provider_response={"status_code": response.status_code},
                    response_time_ms=response_time_ms,
                    health_score=health_score
                )
            else:
                return KeyValidationResult(
                    is_valid=False,
                    key_status=KeyStatus.DEGRADED,
                    provider_response={"status_code": response.status_code},
                    response_time_ms=response_time_ms,
                    error_message=f"HTTP {response.status_code}",
                    health_score=0.0
                )
        except Exception as e:
            return KeyValidationResult(
                is_valid=False,
                key_status=KeyStatus.UNHEALTHY,
                provider_response={},
                response_time_ms=response_time_ms,
                error_message=str(e),
                health_score=0.0
            )
    
    def get_health_status(self, api_key_id: str) -> Optional[KeyStatus]:
        """Get current health status of API key."""
        cached_data = self.health_cache.get(api_key_id)
        
        if not cached_data:
            return None
        
        last_check = cached_data["last_check"]
        
        # Check if cache is still valid
        if (datetime.utcnow() - last_check).total_seconds() > self.health_cache_ttl:
            return None
        
        return cached_data["result"].key_status
    
    def get_validation_history(self, api_key_id: str, limit: int = 10) -> List[KeyValidationResult]:
        """Get recent validation history for API key."""
        history = self.validation_history.get(api_key_id, [])
        return history[-limit:] if history else []


class UsageAnalyzer:
    """Analyzes API key usage patterns and costs."""
    
    def __init__(self):
        self.usage_cache: Dict[str, UsageAnalytics] = {}
    
    async def analyze_usage(
        self,
        api_key_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> UsageAnalytics:
        """Analyze usage for API key over time period."""
        
        # Get usage data from database
        # This would query the ApiKeyUsage model
        usage_data = await self._get_usage_data_from_db(api_key_id, period_start, period_end)
        
        # Calculate analytics
        analytics = UsageAnalytics(
            key_id=api_key_id,
            period_start=period_start,
            period_end=period_end
        )
        
        # Process usage data
        total_requests = len(usage_data)
        successful_requests = sum(1 for usage in usage_data if usage.get("is_successful", True))
        failed_requests = total_requests - successful_requests
        
        analytics.total_requests = total_requests
        analytics.successful_requests = successful_requests
        analytics.failed_requests = failed_requests
        
        # Calculate response times
        response_times = [usage.get("response_time_ms", 0) for usage in usage_data]
        if response_times:
            analytics.avg_response_time_ms = sum(response_times) / len(response_times)
            analytics.p95_response_time_ms = self._calculate_percentile(response_times, 95)
            analytics.p99_response_time_ms = self._calculate_percentile(response_times, 99)
        
        # Calculate costs
        total_cost = sum(usage.get("cost_amount", 0) for usage in usage_data)
        analytics.total_cost = total_cost
        analytics.cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        
        # Calculate rates
        analytics.success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        analytics.error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate health score
        analytics.health_score = self._calculate_health_score(analytics)
        
        # Cache analytics
        self.usage_cache[api_key_id] = analytics
        
        return analytics
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _calculate_health_score(self, analytics: UsageAnalytics) -> float:
        """Calculate health score based on analytics."""
        score = 100.0
        
        # Deduct for high error rate
        if analytics.error_rate > 5.0:
            score -= 30
        elif analytics.error_rate > 2.0:
            score -= 15
        
        # Deduct for slow response times
        if analytics.avg_response_time_ms > 5000:  # 5 seconds
            score -= 25
        elif analytics.avg_response_time_ms > 2000:  # 2 seconds
            score -= 10
        
        # Deduct for low success rate
        if analytics.success_rate < 95.0:
            score -= 20
        elif analytics.success_rate < 98.0:
            score -= 10
        
        return max(0.0, score)
    
    async def _get_usage_data_from_db(
        self,
        api_key_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> List[Dict[str, Any]]:
        """Get usage data from database."""
        # This would query the ApiKeyUsage model
        # For now, return mock data
        return []


class ApiKeyManager:
    """
    Centralized API key management system.
    
    Features:
    - Encrypted key storage
    - Automated rotation with minimal downtime
    - Health monitoring and failover
    - Usage analytics and cost tracking
    - Provider-specific key management
    """
    
    def __init__(self):
        """Initialize API key manager."""
        self.key_encryption = KeyEncryption()
        self.health_monitor = KeyHealthMonitor()
        self.usage_analyzer = UsageAnalyzer()
        
        # Key storage
        self.keys_cache: Dict[str, ApiKey] = {}
        self.key_by_provider: Dict[str, List[str]] = {}  # provider -> [key_ids]
        self.rotation_schedules: Dict[str, Dict[str, Any]] = {}
        
        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.rotation_check_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.statistics = {
            "total_keys": 0,
            "healthy_keys": 0,
            "unhealthy_keys": 0,
            "rotating_keys": 0,
            "total_requests": 0,
            "total_cost": 0.0
        }
        
        logger.info("API key manager initialized")
    
    async def initialize(self):
        """Initialize API key manager."""
        try:
            # Load keys from database
            await self._load_keys_from_db()
            
            # Start background tasks
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.rotation_check_task = asyncio.create_task(self._rotation_check_loop())
            
            logger.info("API key manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize API key manager: {e}")
            raise
    
    async def _load_keys_from_db(self):
        """Load API keys from database."""
        # This would load keys from database
        # For now, create placeholder
        
        self.statistics["total_keys"] = len(self.keys_cache)
        logger.info(f"Loaded {self.statistics['total_keys']} API keys")
    
    async def _health_check_loop(self):
        """Background loop for health checks."""
        try:
            while True:
                await self._perform_health_checks()
                await asyncio.sleep(300)  # Every 5 minutes
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
    
    async def _rotation_check_loop(self):
        """Background loop for rotation checks."""
        try:
            while True:
                await self._check_rotation_schedules()
                await asyncio.sleep(3600)  # Every hour
        except asyncio.CancelledError:
            logger.info("Rotation check loop cancelled")
        except Exception as e:
            logger.error(f"Error in rotation check loop: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all active keys."""
        for api_key in self.keys_cache.values():
            if api_key.is_active:
                try:
                    await self.health_monitor.validate_api_key(api_key)
                except Exception as e:
                    logger.error(f"Health check failed for key {api_key.id}: {e}")
    
    async def _check_rotation_schedules(self):
        """Check for keys that need rotation."""
        now = datetime.utcnow()
        
        for key_id, schedule in self.rotation_schedules.items():
            next_rotation = schedule.get("next_rotation")
            if next_rotation and now >= next_rotation:
                # Trigger rotation
                api_key = self.keys_cache.get(key_id)
                if api_key and api_key.is_active:
                    await self.rotate_api_key(key_id, reason="scheduled")
    
    async def get_healthy_api_key(
        self,
        endpoint_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[ApiKey]:
        """Get healthy API key for endpoint."""
        
        # Get API keys for endpoint
        # This would query keys based on endpoint association
        eligible_keys = [
            key for key in self.keys_cache.values()
            if key.is_active and key.is_healthy
        ]
        
        if not eligible_keys:
            logger.warning(f"No healthy API keys available for endpoint {endpoint_id}")
            return None
        
        # Sort by health score and recent usage
        eligible_keys.sort(
            key=lambda k: (k.health_score, -k.total_requests),
            reverse=True
        )
        
        # Return most healthy key
        selected_key = eligible_keys[0]
        
        # Track key selection
        event_tracker.track_system_event(
            "api_key_selected",
            EventLevel.DEBUG,
            {
                "key_id": selected_key.id,
                "endpoint_id": endpoint_id,
                "health_score": selected_key.health_score
            }
        )
        
        return selected_key
    
    async def rotate_api_key(
        self,
        key_id: str,
        reason: str = "manual",
        strategy: RotationStrategy = RotationStrategy.OVERLAPPING
    ) -> bool:
        """Rotate API key with minimal downtime."""
        
        api_key = self.keys_cache.get(key_id)
        if not api_key:
            logger.error(f"API key {key_id} not found")
            return False
        
        if api_key.rotation_in_progress:
            logger.warning(f"API key {key_id} is already being rotated")
            return False
        
        try:
            # Mark as rotating
            api_key.rotation_in_progress = True
            
            # Create rotation record
            rotation_record = ApiKeyRotation(
                api_key_id=key_id,
                rotation_type=reason,
                status="in_progress"
            )
            
            logger.info(f"Starting rotation for API key {key_id}, strategy: {strategy.value}")
            
            # Track rotation event
            event_tracker.track_system_event(
                "api_key_rotation_started",
                EventLevel.INFO,
                {
                    "key_id": key_id,
                    "strategy": strategy.value,
                    "reason": reason
                }
            )
            
            if strategy == RotationStrategy.IMMEDIATE:
                return await self._immediate_rotation(api_key, rotation_record)
            elif strategy == RotationStrategy.OVERLAPPING:
                return await self._overlapping_rotation(api_key, rotation_record)
            elif strategy == RotationStrategy.GRADUAL:
                return await self._gradual_rotation(api_key, rotation_record)
            else:
                logger.error(f"Unknown rotation strategy: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"API key rotation failed for {key_id}: {e}")
            
            # Mark rotation as failed
            if api_key.rotation_in_progress:
                api_key.rotation_in_progress = False
            
            event_tracker.track_error(
                e,
                additional_data={
                    "key_id": key_id,
                    "rotation_reason": reason
                }
            )
            
            return False
    
    async def _immediate_rotation(
        self,
        api_key: ApiKey,
        rotation_record: ApiKeyRotation
    ) -> bool:
        """Perform immediate rotation (no overlap)."""
        
        try:
            # Generate new key
            new_key = await self._generate_new_key(api_key.provider)
            
            # Encrypt new key
            encrypted_new_key = self.key_encryption.encrypt_key(new_key)
            
            # Update key
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            api_key.rotation_in_progress = False
            
            # Update rotation record
            rotation_record.status = "completed"
            rotation_record.new_key_version = api_key.key_version
            
            logger.info(f"Immediate rotation completed for API key {api_key.id}")
            
            return True
            
        except Exception as e:
            rotation_record.status = "failed"
            rotation_record.error_message = str(e)
            api_key.rotation_in_progress = False
            raise
    
    async def _overlapping_rotation(
        self,
        api_key: ApiKey,
        rotation_record: ApiKeyRotation
    ) -> bool:
        """Perform overlapping rotation (both keys active)."""
        
        try:
            # Generate new key
            new_key = await self._generate_new_key(api_key.provider)
            
            # Encrypt new key
            encrypted_new_key = self.key_encryption.encrypt_key(new_key)
            
            # Create new ApiKey record for overlapping period
            new_api_key = ApiKey(
                name=f"{api_key.name}_rotated",
                key_type=api_key.key_type,
                provider=api_key.provider,
                encrypted_key=encrypted_new_key,
                key_version=api_key.key_version + 1
            )
            
            # Store new key temporarily
            # This would be persisted to database
            temp_key_id = f"{api_key.id}_rotated"
            self.keys_cache[temp_key_id] = new_api_key
            
            # Wait for health check on new key
            validation_result = await self.health_monitor.validate_api_key(new_api_key)
            
            if not validation_result.is_valid:
                raise Exception(f"New key validation failed: {validation_result.error_message}")
            
            # Update original key
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            api_key.rotation_in_progress = False
            
            # Remove temporary key
            self.keys_cache.pop(temp_key_id, None)
            
            # Update rotation record
            rotation_record.status = "completed"
            rotation_record.new_key_version = api_key.key_version
            
            logger.info(f"Overlapping rotation completed for API key {api_key.id}")
            
            return True
            
        except Exception as e:
            rotation_record.status = "failed"
            rotation_record.error_message = str(e)
            api_key.rotation_in_progress = False
            
            # Clean up temporary key
            temp_key_id = f"{api_key.id}_rotated"
            self.keys_cache.pop(temp_key_id, None)
            
            raise
    
    async def _gradual_rotation(
        self,
        api_key: ApiKey,
        rotation_record: ApiKeyRotation
    ) -> bool:
        """Perform gradual rotation (shift traffic over time)."""
        
        try:
            # Generate new key
            new_key = await self._generate_new_key(api_key.provider)
            
            # Encrypt new key
            encrypted_new_key = self.key_encryption.encrypt_key(new_key)
            
            # Create new ApiKey record
            new_api_key = ApiKey(
                name=f"{api_key.name}_gradual",
                key_type=api_key.key_type,
                provider=api_key.provider,
                encrypted_key=encrypted_new_key,
                key_version=api_key.key_version + 1
            )
            
            # Store new key
            new_key_id = f"{api_key.id}_gradual"
            self.keys_cache[new_key_id] = new_api_key
            
            # Phase 1: Start with low traffic (10%)
            # Phase 2: Increase to 50%
            # Phase 3: Switch to 100% new key
            # This would be implemented with load balancing logic
            
            await asyncio.sleep(60)  # Simulate gradual transition
            
            # Update original key
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            api_key.rotation_in_progress = False
            
            # Remove new key record
            self.keys_cache.pop(new_key_id, None)
            
            # Update rotation record
            rotation_record.status = "completed"
            rotation_record.new_key_version = api_key.key_version
            
            logger.info(f"Gradual rotation completed for API key {api_key.id}")
            
            return True
            
        except Exception as e:
            rotation_record.status = "failed"
            rotation_record.error_message = str(e)
            api_key.rotation_in_progress = False
            
            # Clean up
            new_key_id = f"{api_key.id}_gradual"
            self.keys_cache.pop(new_key_id, None)
            
            raise
    
    async def _generate_new_key(self, provider: str) -> str:
        """Generate new API key for provider."""
        
        if provider == "openai":
            # Generate OpenAI-style key
            return f"sk-{self._generate_random_string(51)}"
        elif provider == "azure":
            # Generate Azure-style key
            return self._generate_random_string(32)
        elif provider == "stripe":
            # Generate Stripe-style key
            return f"sk_test_{self._generate_random_string(47)}"
        else:
            # Generate generic key
            return self._generate_random_string(32)
    
    def _generate_random_string(self, length: int) -> str:
        """Generate random string for API key."""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key."""
        return self.key_encryption.decrypt_key(encrypted_key)
    
    async def get_usage_analytics(
        self,
        key_id: str,
        hours: int = 24
    ) -> UsageAnalytics:
        """Get usage analytics for API key."""
        
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(hours=hours)
        
        return await self.usage_analyzer.analyze_usage(key_id, period_start, period_end)
    
    async def add_api_key(
        self,
        name: str,
        key_type: KeyType,
        provider: str,
        api_key_value: str,
        **kwargs
    ) -> ApiKey:
        """Add new API key."""
        
        # Encrypt the API key
        encrypted_key = self.key_encryption.encrypt_key(api_key_value)
        
        # Create ApiKey record
        api_key = ApiKey(
            name=name,
            key_type=key_type.value,
            provider=provider,
            encrypted_key=encrypted_key,
            internal_key_id=self._generate_internal_key_id(),
            **kwargs
        )
        
        # Store in cache
        self.keys_cache[api_key.id] = api_key
        
        # Update statistics
        self.statistics["total_keys"] += 1
        
        # Initial health check
        try:
            validation_result = await self.health_monitor.validate_api_key(api_key)
            api_key.is_healthy = validation_result.is_valid
            api_key.health_check_status = validation_result.key_status.value
        except Exception as e:
            logger.error(f"Initial health check failed for key {api_key.id}: {e}")
        
        logger.info(f"Added API key: {name} ({provider})")
        
        # Track key addition
        event_tracker.track_system_event(
            "api_key_added",
            EventLevel.INFO,
            {
                "key_id": api_key.id,
                "name": name,
                "provider": provider,
                "key_type": key_type.value
            }
        )
        
        return api_key
    
    def _generate_internal_key_id(self) -> str:
        """Generate unique internal key ID."""
        import uuid
        return f"key_{uuid.uuid4().hex[:16]}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API key manager statistics."""
        
        return {
            "total_keys": self.statistics["total_keys"],
            "healthy_keys": sum(1 for key in self.keys_cache.values() if key.is_healthy),
            "unhealthy_keys": sum(1 for key in self.keys_cache.values() if not key.is_healthy),
            "rotating_keys": sum(1 for key in self.keys_cache.values() if key.rotation_in_progress),
            "keys_by_provider": {
                provider: len(keys) for provider, keys in self.key_by_provider.items()
            },
            "total_requests": self.statistics["total_requests"],
            "total_cost": self.statistics["total_cost"],
            "key_health_summary": {
                key_id: {
                    "status": "healthy" if key.is_healthy else "unhealthy",
                    "last_health_check": key.last_health_check.isoformat() if key.last_health_check else None,
                    "health_score": getattr(key, 'health_score', 0.0),
                    "rotation_in_progress": key.rotation_in_progress
                }
                for key_id, key in self.keys_cache.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown API key manager."""
        logger.info("Shutting down API key manager...")
        
        try:
            # Cancel background tasks
            tasks = [self.health_check_task, self.rotation_check_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[task for task in tasks if task], return_exceptions=True)
            
            logger.info("API key manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during API key manager shutdown: {e}")
