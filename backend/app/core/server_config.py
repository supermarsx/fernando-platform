"""
Server Configuration Management

This module provides comprehensive configuration management for the dual-server architecture,
including environment-specific settings, feature flags, and performance tuning.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import os
import json
import yaml
from pathlib import Path
import logging

from .server_architecture import ServerType, ServerConfiguration, FeatureAvailability


class EnvironmentType(str, Enum):
    """Environment type enumeration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class FeatureToggle(str, Enum):
    """Feature toggle enumeration"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    BETA = "beta"
    ROLLOUT = "rollout"  # Gradual rollout


class ConfigSource(str, Enum):
    """Configuration source enumeration"""
    ENVIRONMENT = "environment"
    FILE = "file"
    DATABASE = "database"
    REMOTE = "remote"  # Remote config service


@dataclass
class ServerEnvironment:
    """Server environment configuration"""
    environment_type: EnvironmentType
    debug_mode: bool = False
    log_level: str = "INFO"
    monitoring_enabled: bool = True
    metrics_collection: bool = True
    security_level: str = "standard"  # basic, standard, high
    backup_enabled: bool = True
    auto_scaling: bool = False
    performance_mode: str = "balanced"  # performance, balanced, efficiency


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    description: str
    toggle: FeatureToggle
    server_types: List[ServerType]
    environments: List[EnvironmentType]
    rollout_percentage: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""
    max_connections: int = 100
    connection_pool_size: int = 20
    request_timeout: int = 30
    response_cache_ttl: int = 300
    compression_enabled: bool = True
    gzip_enabled: bool = True
    rate_limiting: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60
    memory_limit_mb: int = 512
    cpu_limit_percent: int = 80
    disk_usage_warning: float = 80.0
    auto_restart: bool = False
    health_check_interval: int = 30


@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_enabled: bool = True
    ssl_required: bool = False
    certificate_path: Optional[str] = None
    jwt_secret_key: str = "default-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    api_key_required: bool = True
    rate_limiting: bool = True
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    helmet_enabled: bool = True
    request_validation: bool = True
    audit_logging: bool = True
    intrusion_detection: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    ip_blacklist: List[str] = field(default_factory=list)


class ConfigurationManager:
    """
    Central configuration management system
    """
    
    def __init__(self, config_dir: str = "config"):
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._server_config: Optional[ServerConfiguration] = None
        self._environment: Optional[ServerEnvironment] = None
        
        # Load initial configuration
        self._load_configuration()
        
    def _load_configuration(self):
        """Load configuration from all sources"""
        try:
            # Load environment configuration
            self._load_environment_config()
            
            # Load feature flags
            self._load_feature_flags()
            
            # Load server configuration
            self._load_server_config()
            
            # Load performance configuration
            self._load_performance_config()
            
            # Load security configuration
            self._load_security_config()
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def _load_environment_config(self):
        """Load environment-specific configuration"""
        env_type = EnvironmentType(os.getenv("ENVIRONMENT_TYPE", "development"))
        
        # Load from environment file
        env_config_file = self.config_dir / f"{env_type.value}.yaml"
        if env_config_file.exists():
            with open(env_config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                self._environment = ServerEnvironment(
                    environment_type=env_type,
                    **config_data
                )
        else:
            # Default configuration
            self._environment = ServerEnvironment(environment_type=env_type)
            
        # Override with environment variables
        self._override_from_environment()
        
    def _override_from_environment(self):
        """Override configuration with environment variables"""
        if not self._environment:
            return
            
        # Debug mode
        if os.getenv("DEBUG"):
            self._environment.debug_mode = os.getenv("DEBUG").lower() == "true"
            
        # Log level
        if os.getenv("LOG_LEVEL"):
            self._environment.log_level = os.getenv("LOG_LEVEL")
            
        # Monitoring
        if os.getenv("MONITORING_ENABLED"):
            self._environment.monitoring_enabled = os.getenv("MONITORING_ENABLED").lower() == "true"
            
        # Performance mode
        if os.getenv("PERFORMANCE_MODE"):
            self._environment.performance_mode = os.getenv("PERFORMANCE_MODE")
    
    def _load_feature_flags(self):
        """Load feature flags configuration"""
        feature_flags_file = self.config_dir / "feature_flags.yaml"
        
        if feature_flags_file.exists():
            with open(feature_flags_file, 'r') as f:
                flags_data = yaml.safe_load(f)
                
                for flag_name, flag_config in flags_data.get("flags", {}).items():
                    flag = FeatureFlag(
                        name=flag_name,
                        description=flag_config.get("description", ""),
                        toggle=FeatureToggle(flag_config.get("toggle", "disabled")),
                        server_types=[ServerType(t) for t in flag_config.get("server_types", [])],
                        environments=[EnvironmentType(e) for e in flag_config.get("environments", [])],
                        rollout_percentage=flag_config.get("rollout_percentage", 0.0),
                        dependencies=flag_config.get("dependencies", []),
                        config=flag_config.get("config", {})
                    )
                    self._feature_flags[flag_name] = flag
        
        # Create default feature flags if file doesn't exist
        self._create_default_feature_flags()
    
    def _create_default_feature_flags(self):
        """Create default feature flags"""
        default_flags = [
            FeatureFlag(
                name="document_processing",
                description="Document upload and processing capabilities",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.CLIENT],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="customer_management",
                description="Customer onboarding and management",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.CLIENT],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="billing_integration",
                description="Billing and payment processing",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.CLIENT],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="licensing",
                description="License management for client servers",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.SUPPLIER],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="revenue_sharing",
                description="Revenue sharing and commission tracking",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.SUPPLIER],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="inter_server_communication",
                description="Communication between client and supplier servers",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="multi_tenant_support",
                description="Multi-tenant data isolation and management",
                toggle=FeatureToggle.BETA,
                server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING]
            ),
            FeatureFlag(
                name="analytics_dashboard",
                description="Advanced analytics and reporting dashboard",
                toggle=FeatureToggle.ENABLED,
                server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
                environments=[EnvironmentType.DEVELOPMENT, EnvironmentType.PRODUCTION]
            ),
            FeatureFlag(
                name="compliance_tools",
                description="Compliance and audit tools",
                toggle=FeatureToggle.ROLLOUT,
                server_types=[ServerType.CLIENT, ServerType.SUPPLIER],
                environments=[EnvironmentType.PRODUCTION],
                rollout_percentage=10.0
            )
        ]
        
        for flag in default_flags:
            self._feature_flags[flag.name] = flag
    
    def _load_server_config(self):
        """Load server configuration"""
        server_config_file = self.config_dir / "server_config.yaml"
        
        if server_config_file.exists():
            with open(server_config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                self._server_config = ServerConfiguration(**config_data)
        else:
            # Default server configuration
            self._server_config = ServerConfiguration(
                server_id=os.getenv("SERVER_ID", "default-server"),
                server_type=ServerType.CLIENT,  # Default to client
                name=os.getenv("SERVER_NAME", "Default Server"),
                description=os.getenv("SERVER_DESCRIPTION", "Default server instance")
            )
    
    def _load_performance_config(self):
        """Load performance configuration"""
        perf_config_file = self.config_dir / "performance.yaml"
        
        if perf_config_file.exists():
            with open(perf_config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                
                # Update server config with performance settings
                if self._server_config:
                    for key, value in config_data.items():
                        if hasattr(self._server_config, key):
                            setattr(self._server_config, key, value)
        
        # Environment-specific performance tuning
        if self._environment:
            self._apply_environment_performance_tuning()
    
    def _apply_environment_performance_tuning(self):
        """Apply environment-specific performance settings"""
        if not self._environment or not self._server_config:
            return
            
        if self._environment.environment_type == EnvironmentType.PRODUCTION:
            # Production optimizations
            self._server_config.max_concurrent_connections = 500
            self._server_config.max_requests_per_minute = 5000
            self._server_config.max_data_storage_gb = 100
        elif self._environment.environment_type == EnvironmentType.DEVELOPMENT:
            # Development optimizations
            self._server_config.max_concurrent_connections = 50
            self._server_config.max_requests_per_minute = 500
            self._server_config.max_data_storage_gb = 5
        elif self._environment.environment_type == EnvironmentType.TESTING:
            # Testing optimizations
            self._server_config.max_concurrent_connections = 10
            self._server_config.max_requests_per_minute = 100
            self._server_config.max_data_storage_gb = 1
    
    def _load_security_config(self):
        """Load security configuration"""
        security_config_file = self.config_dir / "security.yaml"
        
        if security_config_file.exists():
            with open(security_config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                
                # Apply security settings to server config
                if self._server_config:
                    if config_data.get("encryption_enabled") is not None:
                        self._server_config.encryption_enabled = config_data["encryption_enabled"]
                    if config_data.get("authentication_required") is not None:
                        self._server_config.authentication_required = config_data["authentication_required"]
                    if config_data.get("allowed_origins"):
                        self._server_config.allowed_origins = config_data["allowed_origins"]
        
        # Override with environment variables
        if os.getenv("SECRET_KEY"):
            if self._server_config:
                self._server_config.api_key = os.getenv("SECRET_KEY")
    
    def get_environment(self) -> ServerEnvironment:
        """Get current environment configuration"""
        if not self._environment:
            self._load_environment_config()
        return self._environment
    
    def get_server_config(self) -> ServerConfiguration:
        """Get current server configuration"""
        if not self._server_config:
            self._load_server_config()
        return self._server_config
    
    def is_feature_enabled(self, feature_name: str, server_type: ServerType, 
                          environment: EnvironmentType) -> bool:
        """Check if a feature is enabled"""
        flag = self._feature_flags.get(feature_name)
        if not flag:
            return False
            
        # Check toggle status
        if flag.toggle == FeatureToggle.DISABLED:
            return False
        if flag.toggle == FeatureToggle.ENABLED:
            # Check if feature is available for this server type and environment
            return (server_type in flag.server_types and 
                   environment in flag.environments)
        
        if flag.toggle == FeatureToggle.BETA:
            # Beta features are enabled for development/staging only
            return (server_type in flag.server_types and 
                   environment in [EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING])
        
        if flag.toggle == FeatureToggle.ROLLOUT:
            # Rollout features depend on percentage
            import random
            return (server_type in flag.server_types and 
                   environment in flag.environments and
                   random.random() * 100 < flag.rollout_percentage)
        
        return False
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        """Get feature configuration"""
        flag = self._feature_flags.get(feature_name)
        return flag.config if flag else {}
    
    def enable_feature(self, feature_name: str, server_types: List[ServerType] = None,
                      environments: List[EnvironmentType] = None):
        """Enable a feature"""
        flag = self._feature_flags.get(feature_name)
        if flag:
            flag.toggle = FeatureToggle.ENABLED
            if server_types:
                flag.server_types = server_types
            if environments:
                flag.environments = environments
            flag.updated_at = datetime.utcnow()
    
    def disable_feature(self, feature_name: str):
        """Disable a feature"""
        flag = self._feature_flags.get(feature_name)
        if flag:
            flag.toggle = FeatureToggle.DISABLED
            flag.updated_at = datetime.utcnow()
    
    def set_feature_rollout(self, feature_name: str, percentage: float):
        """Set feature rollout percentage"""
        flag = self._feature_flags.get(feature_name)
        if flag:
            flag.toggle = FeatureToggle.ROLLOUT
            flag.rollout_percentage = percentage
            flag.updated_at = datetime.utcnow()
    
    def get_available_features(self, server_type: ServerType, 
                             environment: EnvironmentType) -> List[str]:
        """Get list of available features for server type and environment"""
        available = []
        for flag_name, flag in self._feature_flags.items():
            if self.is_feature_enabled(flag_name, server_type, environment):
                available.append(flag_name)
        return available
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        # Create default performance config
        config = PerformanceConfig()
        
        # Apply environment-specific settings
        if self._environment:
            if self._environment.environment_type == EnvironmentType.PRODUCTION:
                config.max_connections = 1000
                config.connection_pool_size = 50
                config.request_timeout = 60
                config.memory_limit_mb = 2048
            elif self._environment.environment_type == EnvironmentType.DEVELOPMENT:
                config.max_connections = 50
                config.connection_pool_size = 10
                config.request_timeout = 15
                config.memory_limit_mb = 256
        
        # Override with server config if available
        if self._server_config:
            if self._server_config.max_concurrent_connections:
                config.max_connections = self._server_config.max_concurrent_connections
            if self._server_config.max_requests_per_minute:
                config.rate_limit_requests = self._server_config.max_requests_per_minute
        
        return config
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        config = SecurityConfig()
        
        # Apply server config settings
        if self._server_config:
            config.encryption_enabled = self._server_config.encryption_enabled
            config.api_key_required = self._server_config.authentication_required
            config.cors_origins = self._server_config.allowed_origins
        
        return config
    
    def update_config(self, config_type: str, config_data: Dict[str, Any]):
        """Update configuration"""
        try:
            if config_type == "environment":
                self._update_environment_config(config_data)
            elif config_type == "performance":
                self._update_performance_config(config_data)
            elif config_type == "security":
                self._update_security_config(config_data)
            elif config_type == "feature_flags":
                self._update_feature_flags(config_data)
            else:
                raise ValueError(f"Unknown config type: {config_type}")
            
            self.logger.info(f"Updated {config_type} configuration")
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {str(e)}")
            raise
    
    def _update_environment_config(self, config_data: Dict[str, Any]):
        """Update environment configuration"""
        if self._environment:
            for key, value in config_data.items():
                if hasattr(self._environment, key):
                    setattr(self._environment, key, value)
    
    def _update_performance_config(self, config_data: Dict[str, Any]):
        """Update performance configuration"""
        # Save to file
        perf_config_file = self.config_dir / "performance.yaml"
        with open(perf_config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
    
    def _update_security_config(self, config_data: Dict[str, Any]):
        """Update security configuration"""
        # Save to file
        security_config_file = self.config_dir / "security.yaml"
        with open(security_config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
    
    def _update_feature_flags(self, config_data: Dict[str, Any]):
        """Update feature flags configuration"""
        # Save to file
        flags_data = {"flags": config_data}
        feature_flags_file = self.config_dir / "feature_flags.yaml"
        with open(feature_flags_file, 'w') as f:
            yaml.dump(flags_data, f, default_flow_style=False)
        
        # Reload configuration
        self._load_feature_flags()
    
    def export_config(self, config_types: List[str] = None) -> Dict[str, Any]:
        """Export configuration"""
        export_data = {}
        
        if config_types is None:
            config_types = ["environment", "server", "performance", "security", "feature_flags"]
        
        if "environment" in config_types and self._environment:
            export_data["environment"] = self._environment.__dict__
        
        if "server" in config_types and self._server_config:
            export_data["server"] = self._server_config.__dict__
        
        if "performance" in config_types:
            export_data["performance"] = self.get_performance_config().__dict__
        
        if "security" in config_types:
            export_data["security"] = self.get_security_config().__dict__
        
        if "feature_flags" in config_types:
            export_data["feature_flags"] = {
                flag.name: {
                    "description": flag.description,
                    "toggle": flag.toggle.value,
                    "server_types": [t.value for t in flag.server_types],
                    "environments": [e.value for e in flag.environments],
                    "rollout_percentage": flag.rollout_percentage,
                    "dependencies": flag.dependencies,
                    "config": flag.config
                }
                for flag in self._feature_flags.values()
            }
        
        return export_data
    
    def validate_config(self) -> List[str]:
        """Validate current configuration"""
        errors = []
        
        # Validate environment
        if not self._environment:
            errors.append("Environment configuration not loaded")
        else:
            if self._environment.environment_type not in list(EnvironmentType):
                errors.append(f"Invalid environment type: {self._environment.environment_type}")
        
        # Validate server config
        if not self._server_config:
            errors.append("Server configuration not loaded")
        else:
            if not self._server_config.server_id:
                errors.append("Server ID is required")
            if not self._server_config.name:
                errors.append("Server name is required")
            if self._server_config.server_type not in list(ServerType):
                errors.append(f"Invalid server type: {self._server_config.server_type}")
        
        # Validate feature flags
        for flag_name, flag in self._feature_flags.items():
            if not flag.server_types:
                errors.append(f"Feature flag '{flag_name}' has no server types defined")
            if not flag.environments:
                errors.append(f"Feature flag '{flag_name}' has no environments defined")
            if flag.rollout_percentage < 0 or flag.rollout_percentage > 100:
                errors.append(f"Feature flag '{flag_name}' has invalid rollout percentage")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "environment": {
                "type": self._environment.environment_type.value if self._environment else None,
                "debug_mode": self._environment.debug_mode if self._environment else False,
                "log_level": self._environment.log_level if self._environment else None,
                "performance_mode": self._environment.performance_mode if self._environment else None
            },
            "server": {
                "server_id": self._server_config.server_id if self._server_config else None,
                "server_type": self._server_config.server_type.value if self._server_config else None,
                "name": self._server_config.name if self._server_config else None,
                "status": self._server_config.status if self._server_config else None
            },
            "features": {
                "total_flags": len(self._feature_flags),
                "enabled_flags": len([f for f in self._feature_flags.values() if f.toggle == FeatureToggle.ENABLED]),
                "beta_flags": len([f for f in self._feature_flags.values() if f.toggle == FeatureToggle.BETA]),
                "rollout_flags": len([f for f in self._feature_flags.values() if f.toggle == FeatureToggle.ROLLOUT])
            },
            "validation": {
                "is_valid": len(self.validate_config()) == 0,
                "errors": self.validate_config()
            },
            "last_updated": datetime.utcnow().isoformat()
        }


# Global configuration manager instance
config_manager = ConfigurationManager()


# Convenience functions
def get_current_environment() -> ServerEnvironment:
    """Get current environment configuration"""
    return config_manager.get_environment()


def get_current_server_config() -> ServerConfiguration:
    """Get current server configuration"""
    return config_manager.get_server_config()


def is_feature_enabled(feature_name: str, server_type: ServerType, 
                      environment: EnvironmentType = None) -> bool:
    """Check if feature is enabled"""
    if environment is None:
        environment = config_manager.get_environment().environment_type
    return config_manager.is_feature_enabled(feature_name, server_type, environment)


def get_available_features(server_type: ServerType, environment: EnvironmentType = None) -> List[str]:
    """Get available features for server type and environment"""
    if environment is None:
        environment = config_manager.get_environment().environment_type
    return config_manager.get_available_features(server_type, environment)


def get_performance_config() -> PerformanceConfig:
    """Get performance configuration"""
    return config_manager.get_performance_config()


def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return config_manager.get_security_config()


def update_configuration(config_type: str, config_data: Dict[str, Any]):
    """Update configuration"""
    config_manager.update_config(config_type, config_data)


def export_configuration(config_types: List[str] = None) -> Dict[str, Any]:
    """Export configuration"""
    return config_manager.export_config(config_types)


def validate_configuration() -> List[str]:
    """Validate current configuration"""
    return config_manager.validate_config()


def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary"""
    return config_manager.get_config_summary()