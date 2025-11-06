"""
Multi-Tenant Support System

This module provides multi-tenant capabilities including data isolation,
tenant configuration, resource allocation, and tenant-specific features.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import uuid
import json
from decimal import Decimal
import asyncio

from ..core.server_architecture import ServerType, server_architecture
from ..models.server_architecture import Tenant, TenantConfig, ResourceQuota, TenantFeature
from ..core.database import get_db
from ..core.config import settings
from ..core.telemetry import telemetry_tracker


class TenantStatus(str, Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"
    MAINTENANCE = "maintenance"


class ResourceType(str, Enum):
    """Resource type enumeration"""
    STORAGE = "storage"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DATABASE = "database"
    API_CALLS = "api_calls"
    USERS = "users"
    CUSTOMERS = "customers"


class IsolationLevel(str, Enum):
    """Data isolation level"""
    STRONG = "strong"    # Complete data separation
    MODERATE = "moderate"  # Shared schema with row-level security
    WEAK = "weak"        # Shared schema with basic separation


@dataclass
class ResourceAllocation:
    """Resource allocation configuration"""
    resource_type: ResourceType
    limit: float
    unit: str
    used: float = 0.0
    reserved: float = 0.0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def available(self) -> float:
        """Get available resource amount"""
        return max(0.0, self.limit - self.used - self.reserved)
    
    def utilization_percent(self) -> float:
        """Get resource utilization percentage"""
        if self.limit <= 0:
            return 0.0
        return ((self.used + self.reserved) / self.limit) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'resource_type': self.resource_type,
            'limit': self.limit,
            'unit': self.unit,
            'used': self.used,
            'reserved': self.reserved,
            'available': self.available(),
            'utilization_percent': self.utilization_percent(),
            'last_reset': self.last_reset.isoformat()
        }


@dataclass
class TenantMetrics:
    """Tenant usage metrics"""
    tenant_id: str
    api_calls_today: int = 0
    storage_used_gb: float = 0.0
    database_queries: int = 0
    active_users: int = 0
    documents_processed: int = 0
    revenue_generated: Decimal = Decimal('0.00')
    last_activity: Optional[datetime] = None
    creation_date: datetime = field(default_factory=datetime.utcnow)
    
    def reset_daily_counters(self):
        """Reset daily usage counters"""
        self.api_calls_today = 0
        self.database_queries = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'api_calls_today': self.api_calls_today,
            'storage_used_gb': self.storage_used_gb,
            'database_queries': self.database_queries,
            'active_users': self.active_users,
            'documents_processed': self.documents_processed,
            'revenue_generated': float(self.revenue_generated),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'creation_date': self.creation_date.isoformat(),
            'days_active': (datetime.utcnow() - self.creation_date).days
        }


class TenantSecurity:
    """
    Tenant security and data isolation management
    """
    
    def __init__(self, isolation_level: IsolationLevel = IsolationLevel.STRONG):
        self.isolation_level = isolation_level
        self.logger = logging.getLogger(__name__)
        self._tenant_keys: Dict[str, str] = {}  # tenant_id -> encryption_key
        self._access_tokens: Dict[str, Dict[str, Any]] = {}  # token -> access_info
    
    def generate_tenant_key(self, tenant_id: str) -> str:
        """Generate unique encryption key for tenant"""
        import secrets
        key = secrets.token_urlsafe(32)
        self._tenant_keys[tenant_id] = key
        return key
    
    def get_tenant_key(self, tenant_id: str) -> Optional[str]:
        """Get tenant encryption key"""
        return self._tenant_keys.get(tenant_id)
    
    def create_access_token(self, tenant_id: str, user_id: str, 
                          permissions: List[str], expires_in: int = 3600) -> str:
        """Create tenant access token"""
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        self._access_tokens[token] = {
            'tenant_id': tenant_id,
            'user_id': user_id,
            'permissions': permissions,
            'expires_at': expires_at,
            'created_at': datetime.utcnow()
        }
        
        return token
    
    def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate access token"""
        access_info = self._access_tokens.get(token)
        if not access_info:
            return None
        
        # Check expiration
        if access_info['expires_at'] < datetime.utcnow():
            del self._access_tokens[token]
            return None
        
        return access_info
    
    def get_data_filter(self, tenant_id: str) -> Dict[str, Any]:
        """Get database filter for tenant data isolation"""
        if self.isolation_level == IsolationLevel.STRONG:
            return {'tenant_id': tenant_id}
        elif self.isolation_level == IsolationLevel.MODERATE:
            return {'tenant_id': tenant_id}
        else:  # WEAK
            return {'tenant_id': tenant_id}  # Basic filtering
    
    def audit_data_access(self, tenant_id: str, operation: str, resource: str):
        """Log data access for audit purposes"""
        self.logger.info(f"Tenant data access: {tenant_id} - {operation} - {resource}")
        
        # Track telemetry
        telemetry_tracker.track_event('tenant_data_access', {
            'tenant_id': tenant_id,
            'operation': operation,
            'resource': resource,
            'isolation_level': self.isolation_level,
            'server_type': server_architecture.get_current_server_type()
        })


class ResourceManager:
    """
    Resource allocation and monitoring for tenants
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._resource_allocations: Dict[str, Dict[str, ResourceAllocation]] = {}
        self._usage_tracking: Dict[str, TenantMetrics] = {}
    
    def allocate_resources(self, tenant_id: str, resource_config: Dict[str, Any]):
        """Allocate resources to a tenant"""
        try:
            allocations = {}
            
            for resource_type_str, config in resource_config.items():
                resource_type = ResourceType(resource_type_str)
                
                allocation = ResourceAllocation(
                    resource_type=resource_type,
                    limit=config.get('limit', 0),
                    unit=config.get('unit', 'units')
                )
                
                allocations[resource_type_str] = allocation
            
            self._resource_allocations[tenant_id] = allocations
            
            # Initialize usage tracking
            if tenant_id not in self._usage_tracking:
                self._usage_tracking[tenant_id] = TenantMetrics(tenant_id=tenant_id)
            
            self.logger.info(f"Allocated resources to tenant {tenant_id}")
            
        except Exception as e:
            self.logger.error(f"Error allocating resources: {str(e)}")
            raise
    
    def get_resource_allocation(self, tenant_id: str, 
                              resource_type: Optional[ResourceType] = None) -> Dict[str, Any]:
        """Get resource allocation for tenant"""
        allocations = self._resource_allocations.get(tenant_id, {})
        
        if resource_type:
            allocation = allocations.get(resource_type.value)
            return allocation.to_dict() if allocation else {}
        
        return {k: v.to_dict() for k, v in allocations.items()}
    
    def check_resource_limit(self, tenant_id: str, resource_type: ResourceType, 
                           requested_amount: float) -> bool:
        """Check if resource request is within limits"""
        allocations = self._resource_allocations.get(tenant_id, {})
        allocation = allocations.get(resource_type.value)
        
        if not allocation:
            return False
        
        return allocation.available() >= requested_amount
    
    def consume_resource(self, tenant_id: str, resource_type: ResourceType, 
                        amount: float) -> bool:
        """Consume resource for tenant"""
        try:
            allocations = self._resource_allocations.get(tenant_id, {})
            allocation = allocations.get(resource_type.value)
            
            if not allocation:
                return False
            
            if allocation.available() < amount:
                return False
            
            allocation.used += amount
            
            # Update metrics
            metrics = self._usage_tracking.get(tenant_id)
            if metrics:
                if resource_type == ResourceType.STORAGE:
                    metrics.storage_used_gb += amount
                elif resource_type == ResourceType.API_CALLS:
                    metrics.api_calls_today += int(amount)
            
            # Track telemetry
            telemetry_tracker.track_event('resource_consumed', {
                'tenant_id': tenant_id,
                'resource_type': resource_type,
                'amount': amount,
                'remaining': allocation.available(),
                'server_type': server_architecture.get_current_server_type()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error consuming resource: {str(e)}")
            return False
    
    def reserve_resource(self, tenant_id: str, resource_type: ResourceType, 
                        amount: float) -> bool:
        """Reserve resource for tenant (temporary allocation)"""
        allocations = self._resource_allocations.get(tenant_id, {})
        allocation = allocations.get(resource_type.value)
        
        if not allocation or allocation.available() < amount:
            return False
        
        allocation.reserved += amount
        return True
    
    def release_reservation(self, tenant_id: str, resource_type: ResourceType, 
                          amount: float):
        """Release reserved resource"""
        allocations = self._resource_allocations.get(tenant_id, {})
        allocation = allocations.get(resource_type.value)
        
        if allocation:
            allocation.reserved = max(0, allocation.reserved - amount)
    
    def reset_resource_usage(self, tenant_id: str, resource_type: ResourceType):
        """Reset resource usage for tenant (daily/monthly reset)"""
        allocations = self._resource_allocations.get(tenant_id, {})
        allocation = allocations.get(resource_type.value)
        
        if allocation:
            allocation.used = 0
            allocation.reserved = 0
            allocation.last_reset = datetime.utcnow()
        
        # Reset usage metrics
        metrics = self._usage_tracking.get(tenant_id)
        if metrics:
            metrics.reset_daily_counters()
    
    def get_resource_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive resource summary for tenant"""
        allocations = self._resource_allocations.get(tenant_id, {})
        metrics = self._usage_tracking.get(tenant_id, TenantMetrics(tenant_id))
        
        summary = {
            'tenant_id': tenant_id,
            'total_allocations': len(allocations),
            'resource_summary': {},
            'metrics': metrics.to_dict(),
            'alert_level': 'normal',
            'recommendations': []
        }
        
        for resource_type_str, allocation in allocations.items():
            summary['resource_summary'][resource_type_str] = {
                'allocation': allocation.to_dict(),
                'health_status': 'healthy'
            }
            
            # Check for resource pressure
            if allocation.utilization_percent() > 80:
                summary['alert_level'] = 'warning'
                summary['resource_summary'][resource_type_str]['health_status'] = 'warning'
                summary['recommendations'].append(f"High utilization for {resource_type_str}")
            elif allocation.utilization_percent() > 95:
                summary['alert_level'] = 'critical'
                summary['resource_summary'][resource_type_str]['health_status'] = 'critical'
                summary['recommendations'].append(f"Critical utilization for {resource_type_str}")
        
        return summary


class TenantConfiguration:
    """
    Tenant configuration and feature management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._configurations: Dict[str, TenantConfig] = {}
        self._feature_flags: Dict[str, Dict[str, Any]] = {}
        
    def create_tenant(self, config_data: Dict[str, Any]) -> str:
        """Create a new tenant"""
        try:
            tenant_id = str(uuid.uuid4())
            
            # Create tenant configuration
            config = TenantConfig(
                tenant_id=tenant_id,
                name=config_data['name'],
                domain=config_data.get('domain'),
                settings=config_data.get('settings', {}),
                features_enabled=config_data.get('features_enabled', []),
                features_disabled=config_data.get('features_disabled', []),
                custom_branding=config_data.get('custom_branding', {}),
                integrations=config_data.get('integrations', {}),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db = next(get_db())
            db.add(config)
            db.commit()
            
            self._configurations[tenant_id] = config
            
            # Set default features
            self._initialize_default_features(tenant_id)
            
            # Track telemetry
            telemetry_tracker.track_event('tenant_created', {
                'tenant_id': tenant_id,
                'name': config_data['name'],
                'server_type': server_architecture.get_current_server_type()
            })
            
            self.logger.info(f"Created tenant: {tenant_id}")
            return tenant_id
            
        except Exception as e:
            self.logger.error(f"Error creating tenant: {str(e)}")
            raise
    
    def _initialize_default_features(self, tenant_id: str):
        """Initialize default features for tenant"""
        server_type = server_architecture.get_current_server_type()
        available_features = server_architecture.get_available_features()
        
        # Create tenant feature records
        for feature_name in available_features:
            feature = TenantFeature(
                tenant_id=tenant_id,
                feature_name=feature_name,
                enabled=True,
                configuration={},
                created_at=datetime.utcnow()
            )
            
            db = next(get_db())
            db.add(feature)
            db.commit()
    
    def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration"""
        config = self._configurations.get(tenant_id)
        
        if not config:
            # Try to load from database
            db = next(get_db())
            config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
            if config:
                self._configurations[tenant_id] = config
        
        if config:
            return {
                'tenant_id': config.tenant_id,
                'name': config.name,
                'domain': config.domain,
                'settings': config.settings,
                'features_enabled': config.features_enabled,
                'features_disabled': config.features_disabled,
                'custom_branding': config.custom_branding,
                'integrations': config.integrations,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat()
            }
        
        return None
    
    def update_tenant_config(self, tenant_id: str, updates: Dict[str, Any]) -> bool:
        """Update tenant configuration"""
        try:
            config = self._configurations.get(tenant_id)
            
            if not config:
                # Try to load from database
                db = next(get_db())
                config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
                if config:
                    self._configurations[tenant_id] = config
            
            if not config:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            # Update fields
            for field, value in updates.items():
                if hasattr(config, field):
                    setattr(config, field, value)
            
            config.updated_at = datetime.utcnow()
            
            # Save to database
            db = next(get_db())
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('tenant_config_updated', {
                'tenant_id': tenant_id,
                'updated_fields': list(updates.keys()),
                'server_type': server_architecture.get_current_server_type()
            })
            
            self.logger.info(f"Updated configuration for tenant {tenant_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating tenant config: {str(e)}")
            return False
    
    def toggle_feature(self, tenant_id: str, feature_name: str, enabled: bool) -> bool:
        """Toggle feature for tenant"""
        try:
            db = next(get_db())
            feature = db.query(TenantFeature).filter(
                TenantFeature.tenant_id == tenant_id,
                TenantFeature.feature_name == feature_name
            ).first()
            
            if feature:
                feature.enabled = enabled
                feature.updated_at = datetime.utcnow()
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('tenant_feature_toggled', {
                    'tenant_id': tenant_id,
                    'feature_name': feature_name,
                    'enabled': enabled,
                    'server_type': server_architecture.get_current_server_type()
                })
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error toggling feature: {str(e)}")
            return False
    
    def is_feature_enabled(self, tenant_id: str, feature_name: str) -> bool:
        """Check if feature is enabled for tenant"""
        try:
            db = next(get_db())
            feature = db.query(TenantFeature).filter(
                TenantFeature.tenant_id == tenant_id,
                TenantFeature.feature_name == feature_name
            ).first()
            
            return feature.enabled if feature else False
            
        except Exception as e:
            self.logger.error(f"Error checking feature: {str(e)}")
            return False
    
    def get_tenant_features(self, tenant_id: str) -> Dict[str, bool]:
        """Get all features for tenant"""
        try:
            db = next(get_db())
            features = db.query(TenantFeature).filter(
                TenantFeature.tenant_id == tenant_id
            ).all()
            
            return {feature.feature_name: feature.enabled for feature in features}
            
        except Exception as e:
            self.logger.error(f"Error getting tenant features: {str(e)}")
            return {}
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Dict[str, Any]]:
        """List all tenants"""
        try:
            db = next(get_db())
            query = db.query(TenantConfig)
            
            # Note: In a real implementation, we'd have a status field
            tenants = query.all()
            
            result = []
            for tenant in tenants:
                result.append({
                    'tenant_id': tenant.tenant_id,
                    'name': tenant.name,
                    'domain': tenant.domain,
                    'features_enabled': len(tenant.features_enabled),
                    'created_at': tenant.created_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing tenants: {str(e)}")
            return []


class TenantManager:
    """
    Main tenant management system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.security = TenantSecurity()
        self.resource_manager = ResourceManager()
        self.config_manager = TenantConfiguration()
        self._tenant_metrics: Dict[str, TenantMetrics] = {}
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tenant management tasks"""
        asyncio.create_task(self._resource_monitor_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def _resource_monitor_loop(self):
        """Monitor tenant resource usage"""
        while True:
            try:
                await self._check_resource_alerts()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in resource monitor: {str(e)}")
                await asyncio.sleep(300)
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while True:
            try:
                await self._cleanup_expired_data()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _check_resource_alerts(self):
        """Check for resource alerts and send notifications"""
        for tenant_id in self.resource_manager._resource_allocations.keys():
            summary = self.resource_manager.get_resource_summary(tenant_id)
            
            if summary['alert_level'] in ['warning', 'critical']:
                # In real implementation, send alerts to tenant admins
                self.logger.warning(f"Resource alert for tenant {tenant_id}: {summary['alert_level']}")
    
    async def _cleanup_expired_data(self):
        """Clean up expired tokens and temporary data"""
        # Clean up expired access tokens
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, info in self.security._access_tokens.items()
            if info['expires_at'] < current_time
        ]
        
        for token in expired_tokens:
            del self.security._access_tokens[token]
        
        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired access tokens")
    
    def create_tenant_with_resources(self, tenant_config: Dict[str, Any], 
                                   resource_config: Dict[str, Any]) -> str:
        """Create tenant with configuration and resources"""
        try:
            # Create tenant
            tenant_id = self.config_manager.create_tenant(tenant_config)
            
            # Allocate resources
            self.resource_manager.allocate_resources(tenant_id, resource_config)
            
            # Generate security key
            self.security.generate_tenant_key(tenant_id)
            
            # Track telemetry
            telemetry_tracker.track_event('tenant_provisioned', {
                'tenant_id': tenant_id,
                'server_type': server_architecture.get_current_server_type()
            })
            
            self.logger.info(f"Created tenant {tenant_id} with resources")
            return tenant_id
            
        except Exception as e:
            self.logger.error(f"Error creating tenant with resources: {str(e)}")
            raise
    
    def suspend_tenant(self, tenant_id: str, reason: str) -> bool:
        """Suspend tenant operations"""
        try:
            # Update configuration
            success = self.config_manager.update_tenant_config(
                tenant_id, 
                {'status': TenantStatus.SUSPENDED.value}
            )
            
            if success:
                # Track telemetry
                telemetry_tracker.track_event('tenant_suspended', {
                    'tenant_id': tenant_id,
                    'reason': reason,
                    'server_type': server_architecture.get_current_server_type()
                })
                
                self.logger.info(f"Suspended tenant {tenant_id}: {reason}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error suspending tenant: {str(e)}")
            return False
    
    def get_tenant_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive tenant dashboard data"""
        try:
            config = self.config_manager.get_tenant_config(tenant_id)
            resource_summary = self.resource_manager.get_resource_summary(tenant_id)
            features = self.config_manager.get_tenant_features(tenant_id)
            
            return {
                'tenant_id': tenant_id,
                'configuration': config,
                'resources': resource_summary,
                'features': features,
                'health_status': 'healthy',
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting tenant dashboard: {str(e)}")
            return {}
    
    def validate_tenant_access(self, tenant_id: str, token: str) -> bool:
        """Validate tenant access token"""
        access_info = self.security.validate_access_token(token)
        return access_info and access_info['tenant_id'] == tenant_id
    
    def get_tenant_isolation_filter(self, tenant_id: str) -> Dict[str, Any]:
        """Get database filter for tenant data isolation"""
        return self.security.get_data_filter(tenant_id)


# Global tenant manager instance
tenant_manager = TenantManager()


# Convenience functions
def create_tenant(tenant_config: Dict[str, Any], resource_config: Dict[str, Any]) -> str:
    """Create a new tenant"""
    return tenant_manager.create_tenant_with_resources(tenant_config, resource_config)


def get_tenant_info(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get tenant information"""
    return tenant_manager.config_manager.get_tenant_config(tenant_id)


def check_resource_limit(tenant_id: str, resource_type: ResourceType, amount: float) -> bool:
    """Check if resource request is within limits"""
    return tenant_manager.resource_manager.check_resource_limit(tenant_id, resource_type, amount)


def consume_resource(tenant_id: str, resource_type: ResourceType, amount: float) -> bool:
    """Consume resource for tenant"""
    return tenant_manager.resource_manager.consume_resource(tenant_id, resource_type, amount)


def is_tenant_feature_enabled(tenant_id: str, feature_name: str) -> bool:
    """Check if feature is enabled for tenant"""
    return tenant_manager.config_manager.is_feature_enabled(tenant_id, feature_name)


def validate_tenant_access(tenant_id: str, token: str) -> bool:
    """Validate tenant access"""
    return tenant_manager.validate_tenant_access(tenant_id, token)


def get_tenant_data_filter(tenant_id: str) -> Dict[str, Any]:
    """Get tenant data isolation filter"""
    return tenant_manager.get_tenant_isolation_filter(tenant_id)