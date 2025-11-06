"""
Server Architecture Foundation for Fernando Platform

This module provides the foundation for dual-server architecture supporting
both Client Server and Supplier Server deployment models.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime
import logging
from dataclasses import dataclass


class ServerType(str, Enum):
    """Server type enumeration"""
    CLIENT = "client"
    SUPPLIER = "supplier"


class ServerStatus(str, Enum):
    """Server status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class FeatureAvailability(BaseModel):
    """Feature availability configuration"""
    feature_name: str
    available: bool
    level: Optional[str] = None
    restrictions: Dict[str, Any] = {}


class ServerConfiguration(BaseModel):
    """Server configuration model"""
    server_id: str
    server_type: ServerType
    name: str
    description: str
    status: ServerStatus
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Network Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    ssl_enabled: bool = False
    api_base_url: Optional[str] = None
    
    # Feature Configuration
    enabled_features: List[str] = []
    disabled_features: List[str] = []
    feature_restrictions: Dict[str, FeatureAvailability] = {}
    
    # Security Configuration
    api_key: Optional[str] = None
    authentication_required: bool = True
    encryption_enabled: bool = True
    allowed_origins: List[str] = ["*"]
    
    # Resource Limits
    max_concurrent_connections: int = 100
    max_requests_per_minute: int = 1000
    max_data_storage_gb: int = 10
    
    # Monitoring
    health_check_url: str = "/health"
    metrics_enabled: bool = True
    logging_level: str = "INFO"


@dataclass
class ServerCapability:
    """Represents a server capability"""
    name: str
    description: str
    server_types: List[ServerType]
    required: bool = False
    version: str = "1.0.0"


class ServerArchitecture:
    """
    Main server architecture manager
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config: Optional[ServerConfiguration] = None
        self._capabilities: Dict[str, ServerCapability] = {}
        self._feature_registry: Dict[str, FeatureAvailability] = {}
        self._server_registry: Dict[str, ServerConfiguration] = {}
        
        # Initialize default capabilities
        self._initialize_capabilities()
        
    def _initialize_capabilities(self):
        """Initialize default server capabilities"""
        
        # Client Server Capabilities
        self.register_capability(ServerCapability(
            name="document_processing",
            description="Document upload and processing",
            server_types=[ServerType.CLIENT],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="customer_management",
            description="Customer onboarding and management",
            server_types=[ServerType.CLIENT],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="billing_integration",
            description="Billing and payment processing",
            server_types=[ServerType.CLIENT],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="usage_tracking",
            description="Track customer usage and metrics",
            server_types=[ServerType.CLIENT],
            required=True
        ))
        
        # Supplier Server Capabilities
        self.register_capability(ServerCapability(
            name="licensing",
            description="Manage licenses for clients and client servers",
            server_types=[ServerType.SUPPLIER],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="client_server_management",
            description="Register and manage client servers",
            server_types=[ServerType.SUPPLIER],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="revenue_sharing",
            description="Calculate and track revenue sharing",
            server_types=[ServerType.SUPPLIER],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="multi_tenant_support",
            description="Support multiple tenants with data isolation",
            server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
            required=False
        ))
        
        # Shared Capabilities
        self.register_capability(ServerCapability(
            name="inter_server_communication",
            description="Communication between client and supplier servers",
            server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
            required=True
        ))
        
        self.register_capability(ServerCapability(
            name="analytics_dashboard",
            description="Provide analytics and reporting",
            server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
            required=False
        ))
        
        self.register_capability(ServerCapability(
            name="security_monitoring",
            description="Security monitoring and compliance",
            server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
            required=True
        ))

    def register_capability(self, capability: ServerCapability):
        """Register a server capability"""
        self._capabilities[capability.name] = capability
        self.logger.info(f"Registered capability: {capability.name}")

    def get_capability(self, name: str) -> Optional[ServerCapability]:
        """Get a server capability by name"""
        return self._capabilities.get(name)

    def get_capabilities_for_server_type(self, server_type: ServerType) -> List[ServerCapability]:
        """Get all capabilities available for a server type"""
        return [cap for cap in self._capabilities.values() 
                if server_type in cap.server_types]

    def configure_server(self, config: ServerConfiguration):
        """Configure the current server"""
        self._config = config
        self._validate_configuration()
        self.logger.info(f"Configured {config.server_type} server: {config.server_id}")

    def _validate_configuration(self):
        """Validate server configuration"""
        if not self._config:
            raise ValueError("Server configuration is not set")
            
        # Validate capabilities based on server type
        available_capabilities = self.get_capabilities_for_server_type(self._config.server_type)
        capability_names = {cap.name for cap in available_capabilities}
        
        for feature in self._config.enabled_features:
            if feature not in capability_names:
                self.logger.warning(f"Feature '{feature}' not supported by {self._config.server_type} server")
                
        self.logger.info(f"Server configuration validated for {self._config.server_id}")

    def get_current_server_type(self) -> Optional[ServerType]:
        """Get the current server type"""
        return self._config.server_type if self._config else None

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled for the current server"""
        if not self._config:
            return False
            
        if feature_name in self._config.disabled_features:
            return False
            
        if feature_name in self._config.enabled_features:
            return True
            
        # Check feature restrictions
        if feature_name in self._config.feature_restrictions:
            return self._config.feature_restrictions[feature_name].available
            
        # Check capabilities
        capability = self.get_capability(feature_name)
        if capability and self._config.server_type in capability.server_types:
            return True
            
        return False

    def get_available_features(self) -> List[str]:
        """Get list of available features for current server"""
        if not self._config:
            return []
            
        available_features = set(self._config.enabled_features)
        
        # Add capabilities for this server type
        for capability in self.get_capabilities_for_server_type(self._config.server_type):
            if capability.required or capability.name in available_features:
                available_features.add(capability.name)
                
        return list(available_features)

    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get current server information"""
        if not self._config:
            return None
            
        return {
            "server_id": self._config.server_id,
            "server_type": self._config.server_type,
            "name": self._config.name,
            "version": self._config.version,
            "status": self._config.status,
            "host": self._config.host,
            "port": self._config.port,
            "available_features": self.get_available_features(),
            "capabilities": [cap.name for cap in self.get_capabilities_for_server_type(self._config.server_type)],
            "created_at": self._config.created_at.isoformat(),
            "updated_at": self._config.updated_at.isoformat()
        }

    def update_server_status(self, status: ServerStatus):
        """Update server status"""
        if self._config:
            self._config.status = status
            self._config.updated_at = datetime.utcnow()
            self.logger.info(f"Server {self._config.server_id} status updated to {status}")

    def add_feature_restriction(self, feature_name: str, restriction: FeatureAvailability):
        """Add feature restriction for current server"""
        if self._config:
            self._config.feature_restrictions[feature_name] = restriction
            self.logger.info(f"Added restriction for feature: {feature_name}")

    def get_resource_limits(self) -> Dict[str, Any]:
        """Get resource limits for current server"""
        if not self._config:
            return {}
            
        return {
            "max_concurrent_connections": self._config.max_concurrent_connections,
            "max_requests_per_minute": self._config.max_requests_per_minute,
            "max_data_storage_gb": self._config.max_data_storage_gb
        }

    def can_handle_request(self, resource_type: str, current_load: int = 0) -> bool:
        """Check if server can handle additional request"""
        if not self._config or self._config.status != ServerStatus.ACTIVE:
            return False
            
        limits = self.get_resource_limits()
        
        if current_load >= limits.get("max_concurrent_connections", 100):
            return False
            
        return True

    def get_monitoring_info(self) -> Dict[str, Any]:
        """Get monitoring information for current server"""
        if not self._config:
            return {}
            
        return {
            "health_check_url": self._config.health_check_url,
            "metrics_enabled": self._config.metrics_enabled,
            "logging_level": self._config.logging_level,
            "status": self._config.status,
            "uptime": (datetime.utcnow() - self._config.created_at).total_seconds()
        }


# Global server architecture instance
server_architecture = ServerArchitecture()


def get_server_type() -> Optional[ServerType]:
    """Get current server type"""
    return server_architecture.get_current_server_type()


def is_client_server() -> bool:
    """Check if current server is a client server"""
    return get_server_type() == ServerType.CLIENT


def is_supplier_server() -> bool:
    """Check if current server is a supplier server"""
    return get_server_type() == ServerType.SUPPLIER


def is_feature_enabled(feature_name: str) -> bool:
    """Check if feature is enabled"""
    return server_architecture.is_feature_enabled(feature_name)


def get_available_features() -> List[str]:
    """Get available features for current server"""
    return server_architecture.get_available_features()


def configure_server(config: ServerConfiguration):
    """Configure the server"""
    server_architecture.configure_server(config)


def get_server_info() -> Optional[Dict[str, Any]]:
    """Get server information"""
    return server_architecture.get_server_info()


# Convenience decorators for feature-based routing
def require_feature(feature_name: str):
    """Decorator to require a feature for endpoint access"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_feature_enabled(feature_name):
                raise ValueError(f"Feature '{feature_name}' is not available on this server")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_server_type(server_type: ServerType):
    """Decorator to require specific server type"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if get_server_type() != server_type:
                raise ValueError(f"This endpoint requires a {server_type} server")
            return func(*args, **kwargs)
        return wrapper
    return decorator