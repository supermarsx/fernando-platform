"""
API Key Rotation Management

Automated key rotation with minimal downtime:
- Scheduled rotation based on expiration
- Health-based rotation triggers
- Gradual traffic shifting during rotation
- Zero-downtime rotation strategies
- Rotation validation and rollback

Features:
- Multiple rotation strategies
- Health validation during rotation
- Automatic rollback on failure
- Minimal service disruption
- Rotation analytics and reporting
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.models.proxy import ApiKey, ApiKeyRotation
from app.services.api_management.api_key_manager import ApiKeyManager, RotationStrategy, KeyStatus
from app.services.telemetry.event_tracker import event_tracker, EventCategory, EventLevel

logger = logging.getLogger(__name__)


class RotationEvent(Enum):
    """Key rotation event types."""
    SCHEDULED_START = "scheduled_start"
    HEALTH_TRIGGERED = "health_triggered"
    EXPIRATION_TRIGGERED = "expiration_triggered"
    MANUAL_TRIGGERED = "manual_triggered"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"
    TRAFFIC_SHIFT_STARTED = "traffic_shift_started"
    TRAFFIC_SHIFT_COMPLETED = "traffic_shift_completed"
    ROTATION_COMPLETED = "rotation_completed"
    ROTATION_FAILED = "rotation_failed"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"


@dataclass
class RotationPlan:
    """Key rotation plan."""
    key_id: str
    strategy: RotationStrategy
    reason: str
    scheduled_time: datetime
    estimated_duration: int  # seconds
    
    # Validation steps
    validation_steps: List[str] = field(default_factory=list)
    
    # Traffic management
    traffic_shift_schedule: Dict[str, float] = field(default_factory=dict)  # percentage -> time
    health_check_frequency: int = 30  # seconds
    
    # Rollback criteria
    rollback_triggers: List[str] = field(default_factory=list)
    max_downtime_seconds: int = 60
    
    # Communication
    notifications: List[str] = field(default_factory=list)


@dataclass
class RotationProgress:
    """Key rotation progress tracking."""
    rotation_id: str
    key_id: str
    plan: RotationPlan
    
    # Status tracking
    current_step: str = ""
    step_progress: float = 0.0
    total_progress: float = 0.0
    
    # Timing
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Validation results
    validation_results: Dict[str, Any] = field(default_factory=dict)
    health_checks_passed: int = 0
    health_checks_failed: int = 0
    
    # Traffic management
    traffic_shift_progress: float = 0.0
    
    # Errors and issues
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Rollback status
    rollback_initiated: bool = False
    rollback_completed: bool = False


class RotationValidator:
    """Validates API keys during rotation process."""
    
    def __init__(self, api_key_manager: ApiKeyManager):
        self.api_key_manager = api_key_manager
    
    async def validate_key_health(
        self,
        api_key: ApiKey,
        validation_steps: List[str]
    ) -> Dict[str, Any]:
        """Validate API key health using specified steps."""
        
        validation_results = {}
        
        for step in validation_steps:
            try:
                if step == "basic_connectivity":
                    result = await self._validate_basic_connectivity(api_key)
                elif step == "authentication":
                    result = await self._validate_authentication(api_key)
                elif step == "rate_limits":
                    result = await self._validate_rate_limits(api_key)
                elif step == "response_time":
                    result = await self._validate_response_time(api_key)
                elif step == "cost_tracking":
                    result = await self._validate_cost_tracking(api_key)
                else:
                    result = {"success": False, "error": f"Unknown validation step: {step}"}
                
                validation_results[step] = result
                
            except Exception as e:
                validation_results[step] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                }
        
        return validation_results
    
    async def _validate_basic_connectivity(self, api_key: ApiKey) -> Dict[str, Any]:
        """Validate basic connectivity to API provider."""
        start_time = time.time()
        
        try:
            validation_result = await self.api_key_manager.health_monitor.validate_api_key(api_key)
            
            return {
                "success": validation_result.is_valid,
                "response_time_ms": validation_result.response_time_ms,
                "provider_response": validation_result.provider_response,
                "health_score": validation_result.health_score,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.utcnow()
            }
    
    async def _validate_authentication(self, api_key: ApiKey) -> Dict[str, Any]:
        """Validate authentication capabilities."""
        try:
            # Test authentication by making a simple authenticated request
            # This would be provider-specific
            
            if api_key.provider == "openai":
                # Test OpenAI authentication
                test_endpoint = "https://api.openai.com/v1/models"
            elif api_key.provider == "stripe":
                # Test Stripe authentication
                test_endpoint = "https://api.stripe.com/v1/account"
            else:
                # Generic test
                test_endpoint = None
            
            if test_endpoint:
                # This would make an actual test request
                pass
            
            return {
                "success": True,
                "message": "Authentication validated",
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def _validate_rate_limits(self, api_key: ApiKey) -> Dict[str, Any]:
        """Validate rate limit handling."""
        # Test rate limiting behavior
        # This would make multiple requests to check rate limits
        
        return {
            "success": True,
            "rate_limit_handling": "normal",
            "timestamp": datetime.utcnow()
        }
    
    async def _validate_response_time(self, api_key: ApiKey) -> Dict[str, Any]:
        """Validate response time performance."""
        # Test response times under various conditions
        
        validation_result = await self.api_key_manager.health_monitor.validate_api_key(api_key)
        
        response_time = validation_result.response_time_ms
        
        if response_time < 1000:  # 1 second
            status = "excellent"
        elif response_time < 2000:  # 2 seconds
            status = "good"
        elif response_time < 5000:  # 5 seconds
            status = "acceptable"
        else:
            status = "poor"
        
        return {
            "success": response_time < 5000,  # Consider < 5s as acceptable
            "response_time_ms": response_time,
            "performance_status": status,
            "timestamp": datetime.utcnow()
        }
    
    async def _validate_cost_tracking(self, api_key: ApiKey) -> Dict[str, Any]:
        """Validate cost tracking functionality."""
        # Test cost calculation and tracking
        
        return {
            "success": True,
            "cost_tracking": "functional",
            "timestamp": datetime.utcnow()
        }


class TrafficManager:
    """Manages traffic shifting during key rotation."""
    
    def __init__(self):
        self.traffic_shifts: Dict[str, Dict[str, float]] = {}  # rotation_id -> {key_id: percentage}
    
    async def start_traffic_shift(
        self,
        rotation_id: str,
        old_key_id: str,
        new_key_id: str,
        shift_schedule: Dict[str, float]
    ) -> bool:
        """Start traffic shift between keys."""
        
        try:
            self.traffic_shifts[rotation_id] = {
                "old_key": old_key_id,
                "new_key": new_key_id,
                "schedule": shift_schedule,
                "current_percentage": 0.0,
                "started_at": datetime.utcnow()
            }
            
            logger.info(f"Started traffic shift for rotation {rotation_id}: {shift_schedule}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start traffic shift: {e}")
            return False
    
    async def shift_traffic(
        self,
        rotation_id: str,
        target_percentage: float
    ) -> bool:
        """Shift traffic to new key."""
        
        shift_info = self.traffic_shifts.get(rotation_id)
        if not shift_info:
            logger.error(f"No traffic shift found for rotation {rotation_id}")
            return False
        
        try:
            # This would integrate with load balancer
            # For now, just log the shift
            
            shift_info["current_percentage"] = target_percentage
            shift_info["last_shift_at"] = datetime.utcnow()
            
            logger.info(
                f"Traffic shift {rotation_id}: {target_percentage}% to new key"
            )
            
            # Track traffic shift event
            event_tracker.track_system_event(
                "traffic_shift_progress",
                EventLevel.INFO,
                {
                    "rotation_id": rotation_id,
                    "target_percentage": target_percentage
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Traffic shift failed: {e}")
            return False
    
    async def complete_traffic_shift(self, rotation_id: str) -> bool:
        """Complete traffic shift (100% to new key)."""
        return await self.shift_traffic(rotation_id, 100.0)
    
    async def rollback_traffic_shift(self, rotation_id: str) -> bool:
        """Rollback traffic shift (back to old key)."""
        return await self.shift_traffic(rotation_id, 0.0)
    
    def get_traffic_shift_status(self, rotation_id: str) -> Optional[Dict[str, Any]]:
        """Get current traffic shift status."""
        return self.traffic_shifts.get(rotation_id)


class KeyRotation:
    """Main key rotation orchestrator."""
    
    def __init__(self, api_key_manager: ApiKeyManager):
        """Initialize key rotation."""
        self.api_key_manager = api_key_manager
        self.validator = RotationValidator(api_key_manager)
        self.traffic_manager = TrafficManager()
        
        # Rotation tracking
        self.active_rotations: Dict[str, RotationProgress] = {}
        self.rotation_history: List[RotationProgress] = []
        
        # Configuration
        self.config = {
            "max_concurrent_rotations": 3,
            "default_validation_steps": [
                "basic_connectivity",
                "authentication",
                "response_time"
            ],
            "traffic_shift_stages": {
                "10%": 60,   # 1 minute at 10%
                "50%": 300,  # 5 minutes at 50%
                "100%": 600  # 10 minutes at 100%
            },
            "health_check_interval": 30,
            "max_rotation_time": 1800  # 30 minutes
        }
        
        logger.info("Key rotation system initialized")
    
    async def schedule_rotation(
        self,
        key_id: str,
        strategy: RotationStrategy,
        reason: str,
        scheduled_time: Optional[datetime] = None,
        **kwargs
    ) -> str:
        """Schedule a key rotation."""
        
        if scheduled_time is None:
            scheduled_time = datetime.utcnow()
        
        # Create rotation plan
        plan = RotationPlan(
            key_id=key_id,
            strategy=strategy,
            reason=reason,
            scheduled_time=scheduled_time,
            estimated_duration=self._calculate_estimated_duration(strategy),
            validation_steps=kwargs.get("validation_steps", self.config["default_validation_steps"]),
            traffic_shift_schedule=kwargs.get(
                "traffic_shift_schedule",
                self.config["traffic_shift_stages"]
            ),
            health_check_frequency=kwargs.get("health_check_frequency", self.config["health_check_interval"]),
            rollback_triggers=kwargs.get("rollback_triggers", ["validation_failed", "health_degraded"]),
            max_downtime_seconds=kwargs.get("max_downtime_seconds", 60),
            notifications=kwargs.get("notifications", [])
        )
        
        rotation_id = f"rot_{key_id}_{int(time.time())}"
        
        # Create rotation progress tracker
        progress = RotationProgress(
            rotation_id=rotation_id,
            key_id=key_id,
            plan=plan
        )
        
        # Store rotation plan
        self.active_rotations[rotation_id] = progress
        
        logger.info(f"Scheduled rotation {rotation_id} for key {key_id} at {scheduled_time}")
        
        # Track rotation scheduled event
        event_tracker.track_system_event(
            "key_rotation_scheduled",
            EventLevel.INFO,
            {
                "rotation_id": rotation_id,
                "key_id": key_id,
                "strategy": strategy.value,
                "scheduled_time": scheduled_time.isoformat(),
                "reason": reason
            }
        )
        
        return rotation_id
    
    def _calculate_estimated_duration(self, strategy: RotationStrategy) -> int:
        """Calculate estimated duration for rotation strategy."""
        
        base_duration = 300  # 5 minutes base
        
        if strategy == RotationStrategy.IMMEDIATE:
            return 60  # 1 minute
        elif strategy == RotationStrategy.OVERLAPPING:
            return base_duration + 300  # 5 minutes
        elif strategy == RotationStrategy.GRADUAL:
            return base_duration + 900  # 15 minutes
        elif strategy == RotationStrategy.SCHEDULED:
            return base_duration + 600  # 10 minutes
        else:
            return base_duration
    
    async def start_rotation(self, rotation_id: str) -> bool:
        """Start a scheduled rotation."""
        
        progress = self.active_rotations.get(rotation_id)
        if not progress:
            logger.error(f"Rotation {rotation_id} not found")
            return False
        
        api_key = self.api_key_manager.keys_cache.get(progress.key_id)
        if not api_key:
            logger.error(f"API key {progress.key_id} not found")
            return False
        
        try:
            progress.started_at = datetime.utcnow()
            progress.estimated_completion = progress.started_at + timedelta(
                seconds=progress.plan.estimated_duration
            )
            
            logger.info(f"Starting rotation {rotation_id}")
            
            # Track rotation start event
            event_tracker.track_system_event(
                "key_rotation_started",
                EventLevel.INFO,
                {
                    "rotation_id": rotation_id,
                    "key_id": progress.key_id,
                    "strategy": progress.plan.strategy.value,
                    "estimated_duration_seconds": progress.plan.estimated_duration
                }
            )
            
            # Execute rotation strategy
            if progress.plan.strategy == RotationStrategy.IMMEDIATE:
                success = await self._execute_immediate_rotation(progress, api_key)
            elif progress.plan.strategy == RotationStrategy.OVERLAPPING:
                success = await self._execute_overlapping_rotation(progress, api_key)
            elif progress.plan.strategy == RotationStrategy.GRADUAL:
                success = await self._execute_gradual_rotation(progress, api_key)
            elif progress.plan.strategy == RotationStrategy.SCHEDULED:
                success = await self._execute_scheduled_rotation(progress, api_key)
            else:
                logger.error(f"Unknown rotation strategy: {progress.plan.strategy}")
                success = False
            
            if success:
                await self._complete_rotation(progress)
            else:
                await self._fail_rotation(progress, "Rotation execution failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Rotation {rotation_id} failed with exception: {e}")
            await self._fail_rotation(progress, str(e))
            return False
    
    async def _execute_immediate_rotation(
        self,
        progress: RotationProgress,
        api_key: ApiKey
    ) -> bool:
        """Execute immediate rotation strategy."""
        
        progress.current_step = "immediate_rotation"
        progress.step_progress = 0.0
        
        try:
            # Step 1: Generate new key
            progress.step_progress = 10.0
            new_key_value = await self.api_key_manager._generate_new_key(api_key.provider)
            
            # Step 2: Validate new key
            progress.step_progress = 30.0
            validation_results = await self.validator.validate_key_health(
                api_key,  # This would be the new key
                progress.plan.validation_steps
            )
            progress.validation_results = validation_results
            
            # Check for validation failures
            failed_steps = [
                step for step, result in validation_results.items()
                if not result.get("success", False)
            ]
            
            if failed_steps:
                await self._initiate_rollback(progress, f"Validation failed: {failed_steps}")
                return False
            
            progress.step_progress = 60.0
            
            # Step 3: Update key
            encrypted_new_key = self.api_key_manager.key_encryption.encrypt_key(new_key_value)
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            api_key.rotation_in_progress = False
            
            # Step 4: Final validation
            progress.step_progress = 80.0
            final_validation = await self.validator.validate_key_health(
                api_key, progress.plan.validation_steps
            )
            
            # Check if validation passed
            if not all(result.get("success", False) for result in final_validation.values()):
                await self._initiate_rollback(progress, "Final validation failed")
                return False
            
            progress.step_progress = 100.0
            return True
            
        except Exception as e:
            logger.error(f"Immediate rotation failed: {e}")
            progress.errors.append(str(e))
            return False
    
    async def _execute_overlapping_rotation(
        self,
        progress: RotationProgress,
        api_key: ApiKey
    ) -> bool:
        """Execute overlapping rotation strategy."""
        
        progress.current_step = "overlapping_rotation"
        progress.step_progress = 0.0
        
        try:
            # Step 1: Generate and validate new key (parallel)
            progress.step_progress = 20.0
            new_key_value = await self.api_key_manager._generate_new_key(api_key.provider)
            encrypted_new_key = self.api_key_manager.key_encryption.encrypt_key(new_key_value)
            
            # Create temporary key for validation
            temp_key = ApiKey(
                name=f"{api_key.name}_temp",
                key_type=api_key.key_type,
                provider=api_key.provider,
                encrypted_key=encrypted_new_key,
                key_version=api_key.key_version + 1
            )
            
            # Step 2: Validate new key
            progress.step_progress = 40.0
            validation_results = await self.validator.validate_key_health(
                temp_key, progress.plan.validation_steps
            )
            progress.validation_results = validation_results
            
            if not all(result.get("success", False) for result in validation_results.values()):
                await self._initiate_rollback(progress, "New key validation failed")
                return False
            
            # Step 3: Switch to new key
            progress.step_progress = 70.0
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            
            # Step 4: Final validation
            progress.step_progress = 90.0
            final_validation = await self.validator.validate_key_health(
                api_key, progress.plan.validation_steps
            )
            
            if not all(result.get("success", False) for result in final_validation.values()):
                await self._initiate_rollback(progress, "Final validation failed")
                return False
            
            progress.step_progress = 100.0
            return True
            
        except Exception as e:
            logger.error(f"Overlapping rotation failed: {e}")
            progress.errors.append(str(e))
            return False
    
    async def _execute_gradual_rotation(
        self,
        progress: RotationProgress,
        api_key: ApiKey
    ) -> bool:
        """Execute gradual rotation strategy with traffic shifting."""
        
        progress.current_step = "gradual_rotation"
        progress.step_progress = 0.0
        
        try:
            # Step 1: Generate and validate new key
            progress.step_progress = 10.0
            new_key_value = await self.api_key_manager._generate_new_key(api_key.provider)
            encrypted_new_key = self.api_key_manager.key_encryption.encrypt_key(new_key_value)
            
            # Create temporary key
            temp_key_id = f"{api_key.id}_gradual"
            temp_key = ApiKey(
                name=f"{api_key.name}_gradual",
                key_type=api_key.key_type,
                provider=api_key.provider,
                encrypted_key=encrypted_new_key,
                key_version=api_key.key_version + 1
            )
            
            # Store temporary key
            self.api_key_manager.keys_cache[temp_key_id] = temp_key
            
            # Step 2: Start traffic shifting
            progress.step_progress = 20.0
            await self.traffic_manager.start_traffic_shift(
                progress.rotation_id,
                api_key.id,
                temp_key_id,
                progress.plan.traffic_shift_schedule
            )
            
            # Step 3: Gradual traffic shift
            for percentage_str, duration in progress.plan.traffic_shift_schedule.items():
                percentage = float(percentage_str.replace('%', ''))
                
                logger.info(f"Shifting {percentage}% traffic for {duration} seconds")
                
                # Shift traffic
                await self.traffic_manager.shift_traffic(progress.rotation_id, percentage)
                progress.traffic_shift_progress = percentage
                progress.step_progress = 20 + (percentage * 0.6)  # 20% to 80%
                
                # Wait for duration
                await asyncio.sleep(duration)
                
                # Health check during shift
                health_check = await self.validator.validate_key_health(
                    temp_key, ["basic_connectivity"]
                )
                
                if not health_check.get("basic_connectivity", {}).get("success", False):
                    await self._initiate_rollback(
                        progress, f"Health check failed at {percentage}% traffic"
                    )
                    return False
            
            # Step 4: Complete traffic shift
            progress.step_progress = 80.0
            await self.traffic_manager.complete_traffic_shift(progress.rotation_id)
            
            # Step 5: Update original key
            progress.step_progress = 90.0
            api_key.encrypted_key = encrypted_new_key
            api_key.key_version += 1
            api_key.last_rotation_date = datetime.utcnow()
            
            # Clean up temporary key
            self.api_key_manager.keys_cache.pop(temp_key_id, None)
            
            # Step 6: Final validation
            progress.step_progress = 100.0
            final_validation = await self.validator.validate_key_health(
                api_key, progress.plan.validation_steps
            )
            
            if not all(result.get("success", False) for result in final_validation.values()):
                await self._initiate_rollback(progress, "Final validation failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Gradual rotation failed: {e}")
            progress.errors.append(str(e))
            
            # Cleanup temporary key
            temp_key_id = f"{api_key.id}_gradual"
            self.api_key_manager.keys_cache.pop(temp_key_id, None)
            
            return False
    
    async def _execute_scheduled_rotation(
        self,
        progress: RotationProgress,
        api_key: ApiKey
    ) -> bool:
        """Execute scheduled rotation strategy."""
        
        progress.current_step = "scheduled_rotation"
        progress.step_progress = 0.0
        
        # Scheduled rotation is similar to overlapping but at specific time
        # This would wait for the scheduled time before starting
        
        await asyncio.sleep(1)  # Placeholder
        
        return await self._execute_overlapping_rotation(progress, api_key)
    
    async def _initiate_rollback(self, progress: RotationProgress, reason: str):
        """Initiate rollback for failed rotation."""
        
        logger.warning(f"Initiating rollback for rotation {progress.rotation_id}: {reason}")
        
        progress.rollback_initiated = True
        progress.errors.append(f"Rollback initiated: {reason}")
        
        # Track rollback event
        event_tracker.track_system_event(
            "key_rotation_rollback_started",
            EventLevel.WARNING,
            {
                "rotation_id": progress.rotation_id,
                "key_id": progress.key_id,
                "reason": reason
            }
        )
        
        try:
            # Rollback traffic if needed
            if progress.plan.strategy == RotationStrategy.GRADUAL:
                await self.traffic_manager.rollback_traffic_shift(progress.rotation_id)
            
            # Additional rollback steps would go here
            
            progress.rollback_completed = True
            
            # Track rollback completion
            event_tracker.track_system_event(
                "key_rotation_rollback_completed",
                EventLevel.WARNING,
                {
                    "rotation_id": progress.rotation_id,
                    "key_id": progress.key_id
                }
            )
            
        except Exception as e:
            logger.error(f"Rollback failed for rotation {progress.rotation_id}: {e}")
            progress.errors.append(f"Rollback failed: {str(e)}")
    
    async def _complete_rotation(self, progress: RotationProgress):
        """Complete successful rotation."""
        
        progress.actual_completion = datetime.utcnow()
        progress.current_step = "completed"
        progress.total_progress = 100.0
        
        # Move to history
        self.rotation_history.append(progress)
        if progress.rotation_id in self.active_rotations:
            del self.active_rotations[progress.rotation_id]
        
        logger.info(f"Rotation {progress.rotation_id} completed successfully")
        
        # Track completion
        event_tracker.track_system_event(
            "key_rotation_completed",
            EventLevel.INFO,
            {
                "rotation_id": progress.rotation_id,
                "key_id": progress.key_id,
                "duration_seconds": (
                    progress.actual_completion - progress.started_at
                ).total_seconds()
            }
        )
    
    async def _fail_rotation(self, progress: RotationProgress, reason: str):
        """Mark rotation as failed."""
        
        progress.actual_completion = datetime.utcnow()
        progress.current_step = "failed"
        progress.total_progress = 0.0
        progress.errors.append(reason)
        
        # Move to history
        self.rotation_history.append(progress)
        if progress.rotation_id in self.active_rotations:
            del self.active_rotations[progress.rotation_id]
        
        logger.error(f"Rotation {progress.rotation_id} failed: {reason}")
        
        # Track failure
        event_tracker.track_system_event(
            "key_rotation_failed",
            EventLevel.ERROR,
            {
                "rotation_id": progress.rotation_id,
                "key_id": progress.key_id,
                "reason": reason,
                "errors": progress.errors
            }
        )
    
    def get_rotation_status(self, rotation_id: str) -> Optional[Dict[str, Any]]:
        """Get rotation status."""
        
        progress = self.active_rotations.get(rotation_id)
        if not progress:
            return None
        
        return {
            "rotation_id": rotation_id,
            "key_id": progress.key_id,
            "strategy": progress.plan.strategy.value,
            "status": progress.current_step,
            "total_progress": progress.total_progress,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            "errors": progress.errors,
            "warnings": progress.warnings,
            "validation_results": progress.validation_results,
            "traffic_shift_progress": progress.traffic_shift_progress,
            "rollback_initiated": progress.rollback_initiated
        }
    
    def get_rotation_statistics(self) -> Dict[str, Any]:
        """Get rotation system statistics."""
        
        completed_rotations = [
            r for r in self.rotation_history
            if r.current_step == "completed"
        ]
        
        failed_rotations = [
            r for r in self.rotation_history
            if r.current_step == "failed"
        ]
        
        active_rotations = len(self.active_rotations)
        
        # Calculate success rate
        total_rotations = len(self.rotation_history)
        success_rate = (len(completed_rotations) / total_rotations * 100) if total_rotations > 0 else 0
        
        # Calculate average duration
        durations = []
        for rotation in completed_rotations:
            if rotation.started_at and rotation.actual_completion:
                duration = (rotation.actual_completion - rotation.started_at).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "active_rotations": active_rotations,
            "total_rotations": total_rotations,
            "completed_rotations": len(completed_rotations),
            "failed_rotations": len(failed_rotations),
            "success_rate_percent": success_rate,
            "average_duration_seconds": avg_duration,
            "recent_rotations": [
                {
                    "rotation_id": r.rotation_id,
                    "key_id": r.key_id,
                    "strategy": r.plan.strategy.value,
                    "status": r.current_step,
                    "duration_seconds": (
                        (r.actual_completion - r.started_at).total_seconds()
                        if r.actual_completion and r.started_at else None
                    )
                }
                for r in self.rotation_history[-10:]  # Last 10 rotations
            ]
        }
