"""
Custom Integrations
Custom integration framework for extending the platform
"""

import json
import asyncio
import importlib
import inspect
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from app.models.notifications import CustomIntegration
from app.services.hooks.hook_registries import HookRegistry
from app.services.hooks.event_system import Event, EventSystem
from app.services.hooks.event_filters import EventFilterService

logger = logging.getLogger(__name__)

class IntegrationType(Enum):
    """Types of custom integrations"""
    WEBHOOK = "webhook"
    FUNCTION = "function"
    PLUGIN = "plugin"
    API = "api"
    TASK = "task"
    TRANSFORMER = "transformer"

class IntegrationStatus(Enum):
    """Integration status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class IntegrationConfig:
    """Integration configuration"""
    id: str
    name: str
    description: str
    integration_type: IntegrationType
    config_data: Dict[str, Any]
    environment_variables: Dict[str, str]
    secrets: Dict[str, str]
    timeout_seconds: int = 300
    retry_count: int = 3
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None

class CustomIntegrationManager:
    """Manages custom integrations"""
    
    def __init__(self, db):
        self.db = db
        self.integrations: Dict[str, CustomIntegration] = {}
        self.hooks = {}
        self.functions = {}
        self.plugins = {}
        self.api_endpoints = {}
        self.task_queues = {}
        
        # Core services
        self.hook_registry = HookRegistry()
        self.event_system = EventSystem(db)
        self.filter_service = EventFilterService()
        
        # Register built-in integrations
        self._register_builtin_integrations()
    
    def _register_builtin_integrations(self):
        """Register built-in custom integrations"""
        
        # Sample webhook integration
        async def sample_webhook_integration(event: Event, config: Dict[str, Any]):
            """Sample webhook integration"""
            
            import httpx
            
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                return {"success": False, "error": "Webhook URL not configured"}
            
            payload = {
                "event": event.name,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers=config.get("headers", {})
                    )
                    
                    return {
                        "success": response.status_code < 400,
                        "status_code": response.status_code,
                        "response": response.text[:500]
                    }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Sample function integration
        async def sample_function_integration(input_data: Dict[str, Any]) -> Dict[str, Any]:
            """Sample function integration"""
            
            operation = input_data.get("operation", "echo")
            
            if operation == "echo":
                return {
                    "result": "echo",
                    "data": input_data.get("data", {})
                }
            elif operation == "transform":
                # Simple data transformation
                data = input_data.get("data", {})
                transformed = {}
                
                # Uppercase all string values
                for key, value in data.items():
                    if isinstance(value, str):
                        transformed[key] = value.upper()
                    else:
                        transformed[key] = value
                
                return {"result": transformed}
            
            elif operation == "calculate":
                # Simple calculation
                expression = input_data.get("expression", "0")
                try:
                    # WARNING: In production, use a safe expression evaluator
                    result = eval(expression)
                    return {"result": result}
                except:
                    return {"result": "Error in calculation"}
            
            return {"result": "Unknown operation"}
        
        # Register built-in integrations
        self.register_custom_function("webhook_forwarder", sample_webhook_integration)
        self.register_custom_function("data_transformer", sample_function_integration)
    
    def register_custom_function(
        self,
        name: str,
        function: Callable,
        config_schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a custom function integration"""
        
        try:
            # Validate function signature
            sig = inspect.signature(function)
            parameters = list(sig.parameters.keys())
            
            # Check if function expects event parameter
            expects_event = 'event' in parameters
            
            # Register the function
            self.functions[name] = {
                "function": function,
                "expects_event": expects_event,
                "config_schema": config_schema or {},
                "description": getattr(function, '__doc__', ''),
                "parameters": parameters
            }
            
            logger.info(f"Registered custom function: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering custom function {name}: {e}")
            return False
    
    def register_custom_plugin(
        self,
        name: str,
        plugin: Any,
        config_schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a custom plugin integration"""
        
        try:
            # Validate plugin interface
            if not hasattr(plugin, 'process'):
                raise ValueError("Plugin must have a 'process' method")
            
            # Register the plugin
            self.plugins[name] = {
                "plugin": plugin,
                "config_schema": config_schema or {},
                "description": getattr(plugin, '__doc__', ''),
                "methods": [method for method in dir(plugin) if not method.startswith('_')]
            }
            
            logger.info(f"Registered custom plugin: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering custom plugin {name}: {e}")
            return False
    
    def register_custom_api(
        self,
        name: str,
        api_config: Dict[str, Any]
    ) -> bool:
        """Register a custom API integration"""
        
        try:
            required_fields = ["base_url", "methods", "authentication"]
            for field in required_fields:
                if field not in api_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Register the API
            self.api_endpoints[name] = {
                "config": api_config,
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"Registered custom API: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering custom API {name}: {e}")
            return False
    
    async def create_integration(
        self,
        name: str,
        description: str,
        integration_type: IntegrationType,
        config_data: Dict[str, Any],
        environment_variables: Optional[Dict[str, str]] = None,
        secrets: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 300,
        retry_count: int = 3
    ) -> Optional[str]:
        """Create a new custom integration"""
        
        try:
            import uuid
            
            integration_id = str(uuid.uuid4())
            
            # Create database record
            integration = CustomIntegration(
                id=integration_id,
                name=name,
                description=description,
                integration_type=integration_type.value,
                config_data=json.dumps(config_data),
                environment_variables=json.dumps(environment_variables or {}),
                secrets=json.dumps(secrets or {}),
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                status=IntegrationStatus.ACTIVE.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(integration)
            self.db.commit()
            
            # Validate and configure the integration
            success = await self._validate_integration_config(
                integration_type, config_data
            )
            
            if not success:
                integration.status = IntegrationStatus.ERROR.value
                self.db.commit()
                return None
            
            # Load integration based on type
            if integration_type == IntegrationType.FUNCTION:
                await self._load_function_integration(integration_id, config_data)
            elif integration_type == IntegrationType.PLUGIN:
                await self._load_plugin_integration(integration_id, config_data)
            elif integration_type == IntegrationType.WEBHOOK:
                await self._load_webhook_integration(integration_id, config_data)
            
            self.integrations[integration_id] = integration
            
            logger.info(f"Created custom integration: {name} ({integration_id})")
            return integration_id
            
        except Exception as e:
            logger.error(f"Error creating integration {name}: {e}")
            self.db.rollback()
            return None
    
    async def execute_integration(
        self,
        integration_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        event: Optional[Event] = None
    ) -> Dict[str, Any]:
        """Execute a custom integration"""
        
        if integration_id not in self.integrations:
            return {"success": False, "error": "Integration not found"}
        
        integration = self.integrations[integration_id]
        integration_type = IntegrationType(integration.integration_type)
        config_data = json.loads(integration.config_data)
        
        try:
            if integration_type == IntegrationType.FUNCTION:
                return await self._execute_function_integration(
                    integration_id, config_data, input_data, event
                )
            elif integration_type == IntegrationType.PLUGIN:
                return await self._execute_plugin_integration(
                    integration_id, config_data, input_data, event
                )
            elif integration_type == IntegrationType.WEBHOOK:
                return await self._execute_webhook_integration(
                    integration_id, config_data, event
                )
            elif integration_type == IntegrationType.API:
                return await self._execute_api_integration(
                    integration_id, config_data, input_data
                )
            elif integration_type == IntegrationType.TASK:
                return await self._execute_task_integration(
                    integration_id, config_data, input_data
                )
            else:
                return {"success": False, "error": f"Unknown integration type: {integration_type}"}
                
        except Exception as e:
            logger.error(f"Error executing integration {integration_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_function_integration(
        self,
        integration_id: str,
        config: Dict[str, Any],
        input_data: Optional[Dict[str, Any]],
        event: Optional[Event]
    ) -> Dict[str, Any]:
        """Execute a function integration"""
        
        function_name = config.get("function_name")
        if function_name not in self.functions:
            return {"success": False, "error": f"Function {function_name} not found"}
        
        function_info = self.functions[function_name]
        function = function_info["function"]
        
        # Prepare function arguments
        if function_info["expects_event"]:
            # Function expects an event
            if not event:
                return {"success": False, "error": "Event required for this function"}
            result = await function(event, config)
        else:
            # Function expects input data
            result = await function(input_data or {}, config)
        
        return {"success": True, "result": result}
    
    async def _execute_plugin_integration(
        self,
        integration_id: str,
        config: Dict[str, Any],
        input_data: Optional[Dict[str, Any]],
        event: Optional[Event]
    ) -> Dict[str, Any]:
        """Execute a plugin integration"""
        
        plugin_name = config.get("plugin_name")
        if plugin_name not in self.plugins:
            return {"success": False, "error": f"Plugin {plugin_name} not found"}
        
        plugin_info = self.plugins[plugin_name]
        plugin = plugin_info["plugin"]
        
        # Execute plugin
        result = await plugin.process(input_data or {}, config, event)
        
        return {"success": True, "result": result}
    
    async def _execute_webhook_integration(
        self,
        integration_id: str,
        config: Dict[str, Any],
        event: Optional[Event]
    ) -> Dict[str, Any]:
        """Execute a webhook integration"""
        
        if not event:
            return {"success": False, "error": "Event required for webhook integration"}
        
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        # Prepare webhook payload
        payload = {
            "event": event.name,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "integration_id": integration_id
        }
        
        # Add custom fields from config
        for field, value in config.get("additional_fields", {}).items():
            payload[field] = value
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = config.get("headers", {})
                headers.update(config.get("auth_headers", {}))
                
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers
                )
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response": response.text[:500]
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_api_integration(
        self,
        integration_id: str,
        config: Dict[str, Any],
        input_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute an API integration"""
        
        base_url = config.get("base_url")
        if not base_url:
            return {"success": False, "error": "Base URL not configured"}
        
        # This is a simplified API integration
        # In production, you'd implement full API client functionality
        
        return {"success": True, "result": "API integration executed"}
    
    async def _execute_task_integration(
        self,
        integration_id: str,
        config: Dict[str, Any],
        input_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a task integration"""
        
        # This would integrate with a task queue like Celery
        # For now, just return a simple result
        
        return {"success": True, "result": "Task integration executed"}
    
    async def _validate_integration_config(
        self,
        integration_type: IntegrationType,
        config: Dict[str, Any]
    ) -> bool:
        """Validate integration configuration"""
        
        if integration_type == IntegrationType.FUNCTION:
            function_name = config.get("function_name")
            if function_name not in self.functions:
                logger.error(f"Function {function_name} not found")
                return False
            
            # Validate configuration schema
            function_info = self.functions[function_name]
            schema = function_info.get("config_schema", {})
            
            # Basic validation (in production, use proper schema validation)
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in config:
                    logger.error(f"Required field {field} not provided")
                    return False
        
        elif integration_type == IntegrationType.PLUGIN:
            plugin_name = config.get("plugin_name")
            if plugin_name not in self.plugins:
                logger.error(f"Plugin {plugin_name} not found")
                return False
        
        elif integration_type == IntegrationType.WEBHOOK:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                logger.error("Webhook URL not provided")
                return False
            
            # Basic URL validation
            if not webhook_url.startswith(("http://", "https://")):
                logger.error("Webhook URL must start with http:// or https://")
                return False
        
        return True
    
    async def _load_function_integration(
        self,
        integration_id: str,
        config: Dict[str, Any]
    ):
        """Load a function integration"""
        
        # Function integrations are automatically available when registered
        pass
    
    async def _load_plugin_integration(
        self,
        integration_id: str,
        config: Dict[str, Any]
    ):
        """Load a plugin integration"""
        
        # Plugin integrations are automatically available when registered
        pass
    
    async def _load_webhook_integration(
        self,
        integration_id: str,
        config: Dict[str, Any]
    ):
        """Load a webhook integration"""
        
        # Create event subscription for webhook
        webhook_url = config.get("webhook_url")
        events_to_forward = config.get("events_to_forward", ["*"])
        
        for event_pattern in events_to_forward:
            self.event_system.subscribe(
                event_pattern,
                lambda event: self.execute_integration(integration_id, event_data={"event": event}),
                priority=EventPriority.NORMAL
            )
    
    def get_integration(self, integration_id: str) -> Optional[CustomIntegration]:
        """Get integration by ID"""
        return self.integrations.get(integration_id)
    
    def list_integrations(self, integration_type: Optional[IntegrationType] = None) -> List[CustomIntegration]:
        """List all integrations"""
        
        integrations = list(self.integrations.values())
        
        if integration_type:
            integrations = [
                integration 
                for integration in integrations 
                if IntegrationType(integration.integration_type) == integration_type
            ]
        
        return sorted(integrations, key=lambda x: x.created_at, reverse=True)
    
    async def update_integration(
        self,
        integration_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing integration"""
        
        if integration_id not in self.integrations:
            return False
        
        integration = self.integrations[integration_id]
        
        try:
            # Update basic fields
            for field in ["name", "description", "timeout_seconds", "retry_count", "enabled"]:
                if field in updates:
                    setattr(integration, field, updates[field])
            
            # Update configuration
            if "config_data" in updates:
                integration.config_data = json.dumps(updates["config_data"])
            
            # Update status
            if "status" in updates:
                integration.status = updates["status"]
            
            integration.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated integration {integration_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating integration {integration_id}: {e}")
            self.db.rollback()
            return False
    
    async def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration"""
        
        if integration_id not in self.integrations:
            return False
        
        try:
            # Remove from memory
            del self.integrations[integration_id]
            
            # Remove from database
            integration = self.db.query(CustomIntegration).filter(
                CustomIntegration.id == integration_id
            ).first()
            
            if integration:
                self.db.delete(integration)
                self.db.commit()
            
            logger.info(f"Deleted integration {integration_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting integration {integration_id}: {e}")
            self.db.rollback()
            return False
    
    async def test_integration(
        self,
        integration_id: str,
        test_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test an integration with sample data"""
        
        integration = self.get_integration(integration_id)
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Create test event
        test_event = Event(
            id=f"test_{integration_id}",
            name="integration.test",
            category="test",
            data=test_data or {"test": True},
            source="integration_test",
            timestamp=datetime.utcnow()
        )
        
        # Execute integration
        result = await self.execute_integration(
            integration_id,
            input_data=test_data,
            event=test_event
        )
        
        return result
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        
        total_integrations = len(self.integrations)
        active_integrations = sum(
            1 for integration in self.integrations.values()
            if IntegrationStatus(integration.status) == IntegrationStatus.ACTIVE
        )
        
        # Count by type
        integrations_by_type = {}
        for integration_type in IntegrationType:
            integrations_by_type[integration_type.value] = sum(
                1 for integration in self.integrations.values()
                if IntegrationType(integration.integration_type) == integration_type
            )
        
        return {
            "total_integrations": total_integrations,
            "active_integrations": active_integrations,
            "integrations_by_type": integrations_by_type,
            "registered_functions": len(self.functions),
            "registered_plugins": len(self.plugins),
            "registered_apis": len(self.api_endpoints)
        }
    
    async def load_from_database(self):
        """Load integrations from database"""
        
        try:
            db_integrations = self.db.query(CustomIntegration).all()
            
            for db_integration in db_integrations:
                self.integrations[db_integration.id] = db_integration
            
            logger.info(f"Loaded {len(self.integrations)} integrations from database")
            
        except Exception as e:
            logger.error(f"Error loading integrations from database: {e}")