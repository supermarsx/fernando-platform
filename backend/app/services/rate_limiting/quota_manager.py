"""
Quota Management Service

Provides comprehensive quota management for users and organizations including
daily/monthly limits, budget tracking, quota enforcement policies, and
real-time monitoring with automated notifications and throttling.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
import statistics

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, 
    Float, Text, JSON, Index, func, desc
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.models.proxy import APIKey
from app.core.database import get_database_url
from app.services.cache.redis_cache import RedisCache
from app.services.telemetry.event_tracker import EventTracker

logger = logging.getLogger(__name__)

Base = declarative_base()

class QuotaType(Enum):
    """Types of quotas"""
    REQUESTS_PER_DAY = "requests_per_day"
    REQUESTS_PER_MONTH = "requests_per_month"
    DATA_TRANSFER_GB = "data_transfer_gb"
    COMPUTE_TIME_HOURS = "compute_time_hours"
    BUDGET_USD = "budget_usd"
    ENDPOINT_CALLS = "endpoint_calls"
    BANDWIDTH_MBPS = "bandwidth_mbps"
    STORAGE_GB = "storage_gb"
    CONCURRENT_REQUESTS = "concurrent_requests"
    API_KEYS = "api_keys"
    USERS = "users"

class QuotaPeriod(Enum):
    """Quota period types"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ROLLING = "rolling"  # Rolling window

class QuotaStatus(Enum):
    """Quota status levels"""
    NORMAL = "normal"  # Under 70% usage
    WARNING = "warning"  # 70-90% usage
    CRITICAL = "critical"  # 90-100% usage
    EXCEEDED = "exceeded"  # Over limit
    SUSPENDED = "suspended"  # Quota suspended

class EnforcementAction(Enum):
    """Actions to take when quota is exceeded"""
    BLOCK = "block"
    THROTTLE = "throttle"
    NOTIFY = "notify"
    UPGRADE = "upgrade"
    GRACE_PERIOD = "grace_period"

@dataclass
class QuotaLimit:
    """Quota limit configuration"""
    id: str
    name: str
    quota_type: QuotaType
    period: QuotaPeriod
    limit_value: float
    scope_type: str  # 'user', 'organization', 'api_key'
    scope_id: str  # User ID, org ID, etc.
    enforcement_action: EnforcementAction = EnforcementAction.BLOCK
    warning_threshold: float = 0.7  # Warn at 70%
    critical_threshold: float = 0.9  # Critical at 90%
    grace_period_hours: int = 0  # Hours of grace period
    rollover_unused: bool = True  # Allow unused quota to rollover
    max_rollover_percentage: float = 0.2  # Max 20% rollover
    priority: int = 0  # Higher priority quotas applied first
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QuotaUsage:
    """Current quota usage tracking"""
    quota_id: str
    scope_type: str
    scope_id: str
    current_usage: float
    period_start: datetime
    period_end: datetime
    usage_breakdown: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class QuotaViolation:
    """Quota violation record"""
    quota_id: str
    scope_type: str
    scope_id: str
    quota_type: QuotaType
    limit_value: float
    current_usage: float
    violation_type: str  # 'threshold_exceeded', 'limit_exceeded', 'budget_exceeded'
    action_taken: EnforcementAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)

class QuotaManager:
    """
    Comprehensive Quota Management Service
    
    Features:
    - Multiple quota types and periods
    - Real-time usage tracking
    - Automated enforcement and throttling
    - Budget management and cost control
    - Rollover and grace period support
    - Hierarchical quota inheritance
    - Alert and notification system
    """
    
    def __init__(self):
        self.engine = create_engine(get_database_url())
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize integrations
        self.redis_cache = RedisCache()
        self.event_tracker = EventTracker()
        
        # Quota storage and tracking
        self._quota_limits: Dict[str, QuotaLimit] = {}
        self._quota_usage: Dict[str, QuotaUsage] = {}
        self._active_violations: Dict[str, QuotaViolation] = {}
        
        # Real-time statistics
        self._quota_stats = {
            'total_quotas': 0,
            'active_violations': 0,
            'enforcement_actions': defaultdict(int),
            'usage_updates': 0
        }
        
        # Configuration
        self.config = {
            'default_limits': {
                QuotaType.REQUESTS_PER_DAY: 10000,
                QuotaType.DATA_TRANSFER_GB: 10.0,
                QuotaType.BUDGET_USD: 100.0,
                QuotaType.CONCURRENT_REQUESTS: 100,
                QuotaType.API_KEYS: 5,
                QuotaType.USERS: 10
            },
            'warning_thresholds': {
                QuotaType.REQUESTS_PER_DAY: 0.7,
                QuotaType.DATA_TRANSFER_GB: 0.8,
                QuotaType.BUDGET_USD: 0.75,
                QuotaType.CONCURRENT_REQUESTS: 0.9,
                QuotaType.API_KEYS: 0.8,
                QuotaType.USERS: 0.9
            },
            'critical_thresholds': {
                QuotaType.REQUESTS_PER_DAY: 0.9,
                QuotaType.DATA_TRANSFER_GB: 0.95,
                QuotaType.BUDGET_USD: 0.9,
                QuotaType.CONCURRENT_REQUESTS: 0.95,
                QuotaType.API_KEYS: 0.9,
                QuotaType.USERS: 0.95
            },
            'cleanup_interval_hours': 24,
            'redis_namespace': 'quota',
            'max_violations_per_quota': 100,
            'notification_cooldown_minutes': 15
        }
        
        logger.info("QuotaManager initialized")
    
    async def create_quota_limit(self, quota_limit: QuotaLimit) -> bool:
        """Create a new quota limit"""
        try:
            # Validate quota configuration
            if not await self._validate_quota_config(quota_limit):
                logger.error(f"Invalid quota configuration for {quota_limit.id}")
                return False
            
            # Store in memory for fast access
            self._quota_limits[quota_limit.id] = quota_limit
            
            # Store in database for persistence
            session = self.SessionLocal()
            try:
                # This would create the database record
                # For now, we'll just log the creation
                pass
            finally:
                session.close()
            
            # Track quota creation
            await self.event_tracker.track_event(
                "quota_limit_created",
                {
                    "quota_id": quota_limit.id,
                    "quota_type": quota_limit.quota_type.value,
                    "scope_type": quota_limit.scope_type,
                    "limit_value": quota_limit.limit_value,
                    "period": quota_limit.period.value
                }
            )
            
            logger.info(f"Created quota limit: {quota_limit.id} for {quota_limit.scope_type} {quota_limit.scope_id}")
            self._quota_stats['total_quotas'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create quota limit: {e}")
            return False
    
    async def update_quota_limit(self, quota_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing quota limit"""
        try:
            if quota_id not in self._quota_limits:
                logger.error(f"Quota limit {quota_id} not found")
                return False
            
            quota_limit = self._quota_limits[quota_id]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(quota_limit, key):
                    setattr(quota_limit, key, value)
            
            # Validate updated configuration
            if not await self._validate_quota_config(quota_limit):
                logger.error(f"Invalid quota configuration update for {quota_id}")
                return False
            
            # Track quota update
            await self.event_tracker.track_event(
                "quota_limit_updated",
                {
                    "quota_id": quota_id,
                    "updated_fields": list(updates.keys())
                }
            )
            
            logger.info(f"Updated quota limit: {quota_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update quota limit: {e}")
            return False
    
    async def delete_quota_limit(self, quota_id: str) -> bool:
        """Delete quota limit"""
        try:
            if quota_id not in self._quota_limits:
                return False
            
            quota_limit = self._quota_limits[quota_id]
            del self._quota_limits[quota_id]
            
            # Remove from database
            session = self.SessionLocal()
            try:
                # This would delete the database record
                pass
            finally:
                session.close()
            
            # Track quota deletion
            await self.event_tracker.track_event(
                "quota_limit_deleted",
                {"quota_id": quota_id}
            )
            
            logger.info(f"Deleted quota limit: {quota_id}")
            self._quota_stats['total_quotas'] -= 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete quota limit: {e}")
            return False
    
    async def check_quota_usage(
        self,
        scope_type: str,
        scope_id: str,
        quota_type: QuotaType,
        usage_amount: float = 0.0
    ) -> Dict[str, Any]:
        """
        Check current quota usage and status
        
        Args:
            scope_type: Type of scope (user, organization, api_key)
            scope_id: Scope identifier
            quota_type: Type of quota to check
            usage_amount: Amount of usage to check against
            
        Returns:
            Comprehensive quota status information
        """
        try:
            # Find applicable quota limits
            applicable_quotas = await self._find_applicable_quotas(scope_type, scope_id, quota_type)
            
            if not applicable_quotas:
                return {
                    'scope_type': scope_type,
                    'scope_id': scope_id,
                    'quota_type': quota_type.value,
                    'status': 'no_quota',
                    'message': 'No quota limits defined'
                }
            
            # Check each applicable quota (most restrictive first)
            applicable_quotas.sort(key=lambda q: q.priority, reverse=True)
            
            for quota_limit in applicable_quotas:
                usage = await self._get_quota_usage(quota_limit.id)
                if not usage:
                    continue
                
                # Calculate usage percentage
                usage_percentage = usage.current_usage / quota_limit.limit_value
                
                # Determine status
                status = await self._determine_quota_status(quota_limit, usage_percentage)
                
                # Check if request would exceed quota
                would_exceed = (usage.current_usage + usage_amount) > quota_limit.limit_value
                
                # Get enforcement decision
                enforcement = await self._get_enforcement_decision(
                    quota_limit, status, would_exceed
                )
                
                result = {
                    'quota_id': quota_limit.id,
                    'scope_type': scope_type,
                    'scope_id': scope_id,
                    'quota_type': quota_type.value,
                    'limit_value': quota_limit.limit_value,
                    'current_usage': usage.current_usage,
                    'usage_percentage': round(usage_percentage * 100, 2),
                    'status': status.value,
                    'remaining_usage': max(0, quota_limit.limit_value - usage.current_usage),
                    'period': {
                        'start': usage.period_start.isoformat(),
                        'end': usage.period_end.isoformat()
                    },
                    'enforcement': {
                        'action': enforcement['action'],
                        'allowed': enforcement['allowed'],
                        'reason': enforcement['reason'],
                        'retry_after': enforcement.get('retry_after_seconds')
                    },
                    'thresholds': {
                        'warning': quota_limit.warning_threshold,
                        'critical': quota_limit.critical_threshold
                    }
                }
                
                # If this quota is violated, return immediately
                if not enforcement['allowed']:
                    return result
                
                # Continue checking more restrictive quotas
            
            # All quotas passed
            return {
                'scope_type': scope_type,
                'scope_id': scope_id,
                'quota_type': quota_type.value,
                'status': 'normal',
                'message': 'All quota checks passed'
            }
            
        except Exception as e:
            logger.error(f"Failed to check quota usage: {e}")
            return {
                'error': str(e),
                'scope_type': scope_type,
                'scope_id': scope_id,
                'quota_type': quota_type.value
            }
    
    async def update_usage(
        self,
        scope_type: str,
        scope_id: str,
        quota_type: QuotaType,
        usage_amount: float,
        usage_breakdown: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Update quota usage
        
        Args:
            scope_type: Type of scope
            scope_id: Scope identifier
            quota_type: Type of quota
            usage_amount: Amount to add to usage
            usage_breakdown: Detailed breakdown of usage
            
        Returns:
            True if update was successful
        """
        try:
            # Find applicable quotas
            applicable_quotas = await self._find_applicable_quotas(scope_type, scope_id, quota_type)
            
            update_success = True
            violations_detected = []
            
            for quota_limit in applicable_quotas:
                usage_key = f"{quota_limit.id}:{scope_type}:{scope_id}"
                
                # Get or create usage record
                usage = await self._get_or_create_usage(quota_limit, scope_type, scope_id)
                
                # Update usage
                old_usage = usage.current_usage
                usage.current_usage += usage_amount
                usage.last_updated = datetime.now(timezone.utc)
                
                # Update breakdown if provided
                if usage_breakdown:
                    for category, amount in usage_breakdown.items():
                        usage.usage_breakdown[category] = usage.usage_breakdown.get(category, 0) + amount
                
                # Store updated usage
                await self._store_usage(usage)
                
                # Check for violations
                if usage.current_usage > quota_limit.limit_value:
                    violation = await self._create_violation(
                        quota_limit, scope_type, scope_id, usage.current_usage, usage_amount
                    )
                    violations_detected.append(violation)
                    
                    # Trigger enforcement action
                    await self._trigger_enforcement(violation)
                    
                    update_success = False
                
                # Check for threshold breaches
                elif self._check_threshold_breach(quota_limit, usage.current_usage):
                    await self._handle_threshold_breach(quota_limit, scope_type, scope_id, usage.current_usage)
                
                self._quota_stats['usage_updates'] += 1
            
            # Track violations
            if violations_detected:
                await self._track_violations(violations_detected)
            
            return update_success
            
        except Exception as e:
            logger.error(f"Failed to update usage: {e}")
            return False
    
    async def get_quota_status(
        self,
        scope_type: str,
        scope_id: str,
        include_violations: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive quota status for scope"""
        try:
            # Find all quotas for scope
            scope_quotas = [
                quota for quota in self._quota_limits.values()
                if quota.scope_type == scope_type and quota.scope_id == scope_id and quota.enabled
            ]
            
            quota_statuses = []
            
            for quota_limit in scope_quotas:
                usage = await self._get_quota_usage(quota_limit.id)
                if not usage:
                    continue
                
                # Calculate status
                usage_percentage = usage.current_usage / quota_limit.limit_value
                status = await self._determine_quota_status(quota_limit, usage_percentage)
                
                quota_status = {
                    'quota_id': quota_limit.id,
                    'quota_name': quota_limit.name,
                    'quota_type': quota_limit.quota_type.value,
                    'period': quota_limit.period.value,
                    'limit_value': quota_limit.limit_value,
                    'current_usage': usage.current_usage,
                    'usage_percentage': round(usage_percentage * 100, 2),
                    'status': status.value,
                    'remaining_usage': max(0, quota_limit.limit_value - usage.current_usage),
                    'period_info': {
                        'start': usage.period_start.isoformat(),
                        'end': usage.period_end.isoformat(),
                        'time_remaining_hours': self._calculate_time_remaining(usage.period_end)
                    },
                    'breakdown': usage.usage_breakdown,
                    'thresholds': {
                        'warning': quota_limit.warning_threshold,
                        'critical': quota_limit.critical_threshold
                    }
                }
                
                quota_statuses.append(quota_status)
            
            # Get violations if requested
            violations = []
            if include_violations:
                violations = await self._get_active_violations(scope_type, scope_id)
            
            # Calculate overall status
            overall_status = self._calculate_overall_status(quota_statuses)
            
            return {
                'scope_type': scope_type,
                'scope_id': scope_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': overall_status['status'],
                'total_quotas': len(quota_statuses),
                'active_quotas': len([q for q in quota_statuses if q['status'] != QuotaStatus.EXCEEDED.value]),
                'quota_statuses': sorted(quota_statuses, key=lambda x: x['usage_percentage'], reverse=True),
                'active_violations': violations,
                'summary': overall_status['summary']
            }
            
        except Exception as e:
            logger.error(f"Failed to get quota status: {e}")
            return {'error': str(e)}
    
    async def reset_quota_period(self, scope_type: str, scope_id: str, quota_id: Optional[str] = None) -> int:
        """Reset quota period for scope (handles period rollover)"""
        try:
            reset_count = 0
            
            # Find quotas to reset
            if quota_id:
                quotas_to_reset = [q for q in self._quota_limits.values() if q.id == quota_id]
            else:
                quotas_to_reset = [
                    q for q in self._quota_limits.values()
                    if q.scope_type == scope_type and q.scope_id == scope_id
                ]
            
            current_time = datetime.now(timezone.utc)
            
            for quota_limit in quotas_to_reset:
                usage_key = f"{quota_limit.id}:{scope_type}:{scope_id}"
                
                # Check if period has ended
                usage = await self._get_quota_usage(quota_limit.id)
                if not usage or current_time >= usage.period_end:
                    # Calculate new period
                    new_period = await self._calculate_new_period(quota_limit.period, current_time)
                    
                    # Handle rollover if enabled
                    rollover_amount = 0
                    if usage and quota_limit.rollover_unused:
                        unused_amount = max(0, quota_limit.limit_value - usage.current_usage)
                        max_rollover = quota_limit.limit_value * quota_limit.max_rollover_percentage
                        rollover_amount = min(unused_amount, max_rollover)
                    
                    # Create new usage record
                    new_usage = QuotaUsage(
                        quota_id=quota_limit.id,
                        scope_type=scope_type,
                        scope_id=scope_id,
                        current_usage=rollover_amount,
                        period_start=new_period['start'],
                        period_end=new_period['end']
                    )
                    
                    # Store new usage record
                    await self._store_usage(new_usage)
                    
                    reset_count += 1
                    
                    # Track period reset
                    await self.event_tracker.track_event(
                        "quota_period_reset",
                        {
                            "quota_id": quota_limit.id,
                            "scope_type": scope_type,
                            "scope_id": scope_id,
                            "rollover_amount": rollover_amount,
                            "new_period_start": new_period['start'].isoformat()
                        }
                    )
            
            logger.info(f"Reset quota periods for {scope_type} {scope_id}: {reset_count} quotas")
            return reset_count
            
        except Exception as e:
            logger.error(f"Failed to reset quota periods: {e}")
            return 0
    
    async def get_quota_analytics(
        self,
        scope_type: str,
        scope_id: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get quota usage analytics and trends"""
        try:
            # Get quota status for current period
            current_status = await self.get_quota_status(scope_type, scope_id, include_violations=False)
            
            # Get historical usage data (simplified - would need historical storage)
            historical_data = await self._get_historical_usage(scope_type, scope_id, days_back)
            
            # Calculate trends and insights
            analytics = {
                'scope_type': scope_type,
                'scope_id': scope_id,
                'analysis_period_days': days_back,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_status': current_status,
                'historical_trends': self._analyze_usage_trends(historical_data),
                'usage_patterns': self._analyze_usage_patterns(historical_data),
                'recommendations': self._generate_quota_recommendations(current_status, historical_data)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get quota analytics: {e}")
            return {'error': str(e)}
    
    async def _validate_quota_config(self, quota_limit: QuotaLimit) -> bool:
        """Validate quota configuration"""
        # Check required fields
        if not quota_limit.id or not quota_limit.name:
            return False
        
        # Check limit value is positive
        if quota_limit.limit_value <= 0:
            return False
        
        # Check thresholds are reasonable
        if not (0 < quota_limit.warning_threshold < quota_limit.critical_threshold < 1):
            return False
        
        # Check scope
        if not quota_limit.scope_type or not quota_limit.scope_id:
            return False
        
        # Check rollover percentage
        if not (0 <= quota_limit.max_rollover_percentage <= 1):
            return False
        
        return True
    
    async def _find_applicable_quotas(
        self,
        scope_type: str,
        scope_id: str,
        quota_type: QuotaType
    ) -> List[QuotaLimit]:
        """Find quotas applicable to the scope and type"""
        applicable_quotas = []
        
        # Direct scope match
        for quota in self._quota_limits.values():
            if (quota.enabled and
                quota.quota_type == quota_type and
                quota.scope_type == scope_type and
                quota.scope_id == scope_id):
                applicable_quotas.append(quota)
        
        # Check for organization/user hierarchy if applicable
        if scope_type == "user":
            # Check for organization-level quotas
            # This would involve looking up the user's organization
            pass
        
        # Sort by priority (highest first)
        applicable_quotas.sort(key=lambda q: q.priority, reverse=True)
        
        return applicable_quotas
    
    async def _get_quota_usage(self, quota_id: str) -> Optional[QuotaUsage]:
        """Get current usage for quota"""
        # Check cache first
        cache_key = f"{self.config['redis_namespace']}:usage:{quota_id}"
        cached_usage = await self.redis_cache.get(cache_key)
        
        if cached_usage:
            try:
                usage_data = json.loads(cached_usage)
                return QuotaUsage(**usage_data)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Get from database (simplified)
        session = self.SessionLocal()
        try:
            # This would query the actual database
            # For now, return None to indicate no usage data
            pass
        finally:
            session.close()
        
        return None
    
    async def _get_or_create_usage(
        self,
        quota_limit: QuotaLimit,
        scope_type: str,
        scope_id: str
    ) -> QuotaUsage:
        """Get or create quota usage record"""
        usage = await self._get_quota_usage(quota_limit.id)
        
        if usage:
            return usage
        
        # Create new usage record
        period = await self._calculate_new_period(quota_limit.period)
        
        usage = QuotaUsage(
            quota_id=quota_limit.id,
            scope_type=scope_type,
            scope_id=scope_id,
            current_usage=0.0,
            period_start=period['start'],
            period_end=period['end']
        )
        
        await self._store_usage(usage)
        return usage
    
    async def _store_usage(self, usage: QuotaUsage) -> None:
        """Store quota usage"""
        # Store in memory cache
        usage_key = f"{usage.quota_id}:{usage.scope_type}:{usage.scope_id}"
        self._quota_usage[usage_key] = usage
        
        # Store in Redis cache
        cache_key = f"{self.config['redis_namespace']}:usage:{usage.quota_id}"
        usage_data = {
            'quota_id': usage.quota_id,
            'scope_type': usage.scope_type,
            'scope_id': usage.scope_id,
            'current_usage': usage.current_usage,
            'period_start': usage.period_start.isoformat(),
            'period_end': usage.period_end.isoformat(),
            'usage_breakdown': usage.usage_breakdown,
            'last_updated': usage.last_updated.isoformat()
        }
        
        await self.redis_cache.set(cache_key, json.dumps(usage_data), ttl=86400 * 7)  # 7 days
    
    async def _determine_quota_status(
        self,
        quota_limit: QuotaLimit,
        usage_percentage: float
    ) -> QuotaStatus:
        """Determine quota status based on usage percentage"""
        if usage_percentage >= 1.0:
            return QuotaStatus.EXCEEDED
        elif usage_percentage >= quota_limit.critical_threshold:
            return QuotaStatus.CRITICAL
        elif usage_percentage >= quota_limit.warning_threshold:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.NORMAL
    
    async def _get_enforcement_decision(
        self,
        quota_limit: QuotaLimit,
        status: QuotaStatus,
        would_exceed: bool
    ) -> Dict[str, Any]:
        """Get enforcement decision for quota"""
        if status == QuotaStatus.EXCEEDED or would_exceed:
            if quota_limit.enforcement_action == EnforcementAction.BLOCK:
                return {
                    'allowed': False,
                    'action': 'block',
                    'reason': 'Quota limit exceeded'
                }
            elif quota_limit.enforcement_action == EnforcementAction.THROTTLE:
                return {
                    'allowed': True,
                    'action': 'throttle',
                    'reason': 'Quota exceeded - throttling enabled'
                }
            elif quota_limit.enforcement_action == EnforcementAction.GRACE_PERIOD:
                # Check grace period
                if quota_limit.grace_period_hours > 0:
                    return {
                        'allowed': True,
                        'action': 'grace_period',
                        'reason': 'Within grace period',
                        'retry_after_seconds': quota_limit.grace_period_hours * 3600
                    }
                else:
                    return {
                        'allowed': False,
                        'action': 'block',
                        'reason': 'Quota exceeded and no grace period'
                    }
        
        return {
            'allowed': True,
            'action': 'none',
            'reason': 'Within quota limits'
        }
    
    def _check_threshold_breach(
        self,
        quota_limit: QuotaLimit,
        current_usage: float
    ) -> bool:
        """Check if threshold has been breached"""
        usage_percentage = current_usage / quota_limit.limit_value
        
        return (usage_percentage >= quota_limit.warning_threshold and
                usage_percentage < quota_limit.critical_threshold)
    
    async def _create_violation(
        self,
        quota_limit: QuotaLimit,
        scope_type: str,
        scope_id: str,
        current_usage: float,
        usage_amount: float
    ) -> QuotaViolation:
        """Create quota violation record"""
        violation_type = "limit_exceeded"
        if current_usage >= quota_limit.limit_value * quota_limit.critical_threshold:
            violation_type = "threshold_exceeded"
        
        violation = QuotaViolation(
            quota_id=quota_limit.id,
            scope_type=scope_type,
            scope_id=scope_id,
            quota_type=quota_limit.quota_type,
            limit_value=quota_limit.limit_value,
            current_usage=current_usage,
            violation_type=violation_type,
            action_taken=quota_limit.enforcement_action,
            details={'usage_amount': usage_amount}
        )
        
        return violation
    
    async def _trigger_enforcement(self, violation: QuotaViolation) -> None:
        """Trigger enforcement action for violation"""
        action = violation.action_taken
        
        self._quota_stats['enforcement_actions'][action.value] += 1
        
        if action == EnforcementAction.BLOCK:
            # Block the scope (would implement actual blocking logic)
            logger.warning(f"BLOCK quota enforcement: {violation.scope_type} {violation.scope_id}")
            
        elif action == EnforcementAction.THROTTLE:
            # Apply throttling (would implement throttling logic)
            logger.warning(f"THROTTLE quota enforcement: {violation.scope_type} {violation.scope_id}")
            
        elif action == EnforcementAction.NOTIFY:
            # Send notifications (would implement notification logic)
            logger.info(f"NOTIFY quota violation: {violation.scope_type} {violation.scope_id}")
        
        # Track enforcement in telemetry
        asyncio.create_task(self.event_tracker.track_event(
            "quota_enforcement_triggered",
            {
                "quota_id": violation.quota_id,
                "scope_type": violation.scope_type,
                "scope_id": violation.scope_id,
                "action": action.value,
                "violation_type": violation.violation_type
            }
        ))
    
    async def _track_violations(self, violations: List[QuotaViolation]) -> None:
        """Track quota violations"""
        for violation in violations:
            # Store in memory
            violation_key = f"{violation.quota_id}:{violation.scope_type}:{violation.scope_id}"
            self._active_violations[violation_key] = violation
            
            # Store in Redis
            cache_key = f"{self.config['redis_namespace']}:violations:{violation.quota_id}"
            violation_data = {
                'quota_id': violation.quota_id,
                'scope_type': violation.scope_type,
                'scope_id': violation.scope_id,
                'quota_type': violation.quota_type.value,
                'limit_value': violation.limit_value,
                'current_usage': violation.current_usage,
                'violation_type': violation.violation_type,
                'action_taken': violation.action_taken.value,
                'timestamp': violation.timestamp.isoformat(),
                'details': violation.details
            }
            
            await self.redis_cache.lpush(cache_key, json.dumps(violation_data))
            await self.redis_cache.ltrim(cache_key, 0, self.config['max_violations_per_quota'] - 1)
            await self.redis_cache.expire(cache_key, 86400 * 30)  # 30 days
        
        self._quota_stats['active_violations'] = len(self._active_violations)
    
    async def _handle_threshold_breach(
        self,
        quota_limit: QuotaLimit,
        scope_type: str,
        scope_id: str,
        current_usage: float
    ) -> None:
        """Handle quota threshold breach"""
        # Check notification cooldown
        cooldown_key = f"threshold_notified:{quota_limit.id}:{scope_type}:{scope_id}"
        last_notified = await self.redis_cache.get(cooldown_key)
        
        if last_notified:
            # Check if we're still within cooldown
            last_time = datetime.fromisoformat(last_notified)
            time_diff = datetime.now(timezone.utc) - last_time
            if time_diff.total_seconds() < self.config['notification_cooldown_minutes'] * 60:
                return
        
        # Send threshold notification
        usage_percentage = current_usage / quota_limit.limit_value
        
        notification_data = {
            'quota_id': quota_limit.id,
            'quota_name': quota_limit.name,
            'scope_type': scope_type,
            'scope_id': scope_id,
            'usage_percentage': round(usage_percentage * 100, 2),
            'current_usage': current_usage,
            'limit_value': quota_limit.limit_value,
            'threshold_type': 'warning' if usage_percentage < quota_limit.critical_threshold else 'critical'
        }
        
        # Store notification timestamp
        await self.redis_cache.set(cooldown_key, datetime.now(timezone.utc).isoformat(), 
                                 ttl=self.config['notification_cooldown_minutes'] * 60)
        
        # Track threshold breach
        await self.event_tracker.track_event(
            "quota_threshold_breached",
            notification_data
        )
        
        logger.info(f"Quota threshold breached: {quota_limit.id} for {scope_type} {scope_id} "
                   f"({usage_percentage*100:.1f}%)")
    
    async def _calculate_new_period(
        self,
        period: QuotaPeriod,
        reference_time: Optional[datetime] = None
    ) -> Dict[str, datetime]:
        """Calculate new quota period boundaries"""
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        
        if period == QuotaPeriod.HOURLY:
            start = reference_time.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
        elif period == QuotaPeriod.DAILY:
            start = reference_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == QuotaPeriod.WEEKLY:
            days_since_monday = reference_time.weekday()
            start = (reference_time - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=7)
        elif period == QuotaPeriod.MONTHLY:
            start = reference_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        elif period == QuotaPeriod.QUARTERLY:
            quarter = (reference_time.month - 1) // 3 + 1
            quarter_start_month = (quarter - 1) * 3 + 1
            start = reference_time.replace(
                month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=92)  # Approximate quarter
        elif period == QuotaPeriod.YEARLY:
            start = reference_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
        else:
            # Default to daily
            start = reference_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        
        return {'start': start, 'end': end}
    
    def _calculate_time_remaining(self, period_end: datetime) -> float:
        """Calculate time remaining in period (hours)"""
        now = datetime.now(timezone.utc)
        time_remaining = period_end - now
        return max(0, time_remaining.total_seconds() / 3600)
    
    async def _get_active_violations(
        self,
        scope_type: str,
        scope_id: str
    ) -> List[Dict[str, Any]]:
        """Get active violations for scope"""
        violations = []
        
        for violation_key, violation in self._active_violations.items():
            if (violation.scope_type == scope_type and 
                violation.scope_id == scope_id):
                
                violation_data = {
                    'quota_id': violation.quota_id,
                    'quota_type': violation.quota_type.value,
                    'violation_type': violation.violation_type,
                    'limit_value': violation.limit_value,
                    'current_usage': violation.current_usage,
                    'action_taken': violation.action_taken.value,
                    'timestamp': violation.timestamp.isoformat(),
                    'details': violation.details
                }
                
                violations.append(violation_data)
        
        return violations
    
    def _calculate_overall_status(self, quota_statuses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall quota status"""
        if not quota_statuses:
            return {'status': 'no_quotas', 'summary': 'No quotas defined'}
        
        # Count statuses
        status_counts = defaultdict(int)
        for status in quota_statuses:
            status_counts[status['status']] += 1
        
        # Determine overall status
        if status_counts[QuotaStatus.EXCEEDED.value] > 0:
            overall_status = 'exceeded'
        elif status_counts[QuotaStatus.CRITICAL.value] > 0:
            overall_status = 'critical'
        elif status_counts[QuotaStatus.WARNING.value] > 0:
            overall_status = 'warning'
        else:
            overall_status = 'normal'
        
        return {
            'status': overall_status,
            'summary': {
                'normal': status_counts[QuotaStatus.NORMAL.value],
                'warning': status_counts[QuotaStatus.WARNING.value],
                'critical': status_counts[QuotaStatus.CRITICAL.value],
                'exceeded': status_counts[QuotaStatus.EXCEEDED.value]
            }
        }
    
    async def _get_historical_usage(
        self,
        scope_type: str,
        scope_id: str,
        days_back: int
    ) -> Dict[str, Any]:
        """Get historical usage data (simplified implementation)"""
        # This would query historical usage from database
        # For now, return empty data
        return {}
    
    def _analyze_usage_trends(self, historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze usage trends from historical data"""
        # This would analyze trends in historical usage data
        return {
            'trend_direction': 'stable',
            'trend_strength': 0.0,
            'prediction': 'insufficient_data'
        }
    
    def _analyze_usage_patterns(self, historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze usage patterns from historical data"""
        # This would analyze patterns in usage data
        return {
            'peak_usage_day': None,
            'low_usage_day': None,
            'usage_variability': 0.0,
            'pattern_type': 'regular'
        }
    
    def _generate_quota_recommendations(
        self,
        current_status: Dict[str, Any],
        historical_data: Dict[str, Any]
    ) -> List[str]:
        """Generate quota optimization recommendations"""
        recommendations = []
        
        # Check for frequently exceeded quotas
        exceeded_count = len([
            q for q in current_status.get('quota_statuses', [])
            if q['status'] == QuotaStatus.EXCEEDED.value
        ])
        
        if exceeded_count > 0:
            recommendations.append(f"Consider increasing limits for {exceeded_count} frequently exceeded quotas")
        
        # Check for underutilized quotas
        warning_count = len([
            q for q in current_status.get('quota_statuses', [])
            if q['usage_percentage'] < 50
        ])
        
        if warning_count > 2:
            recommendations.append(f"Consider reducing limits for {warning_count} underutilized quotas to optimize costs")
        
        if not recommendations:
            recommendations.append("Quota allocation appears optimal for current usage patterns")
        
        return recommendations
    
    async def cleanup_expired_data(self) -> int:
        """Clean up expired quota data"""
        try:
            cleanup_count = 0
            current_time = datetime.now(timezone.utc)
            
            # Clean up expired usage records
            expired_usage_keys = []
            for usage_key, usage in self._quota_usage.items():
                if current_time > usage.period_end + timedelta(days=7):  # 7 days after period end
                    expired_usage_keys.append(usage_key)
            
            for key in expired_usage_keys:
                del self._quota_usage[key]
                cleanup_count += 1
            
            # Clean up old violations
            expired_violation_keys = []
            for violation_key, violation in self._active_violations.items():
                if current_time > violation.timestamp + timedelta(days=30):  # 30 days after violation
                    expired_violation_keys.append(violation_key)
            
            for key in expired_violation_keys:
                del self._active_violations[key]
                cleanup_count += 1
            
            # Clean up Redis violations
            # This would clean up old violation logs from Redis
            
            logger.info(f"Cleaned up {cleanup_count} expired quota entries")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def close(self):
        """Cleanup resources"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
        
        # Clear in-memory storage
        self._quota_limits.clear()
        self._quota_usage.clear()
        self._active_violations.clear()
        
        logger.info("QuotaManager closed")