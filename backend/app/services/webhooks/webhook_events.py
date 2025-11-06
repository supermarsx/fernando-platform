"""
Webhook Events Service
Handles event definitions, payload formatting, and event types
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EventCategory(Enum):
    """Event categories for organization"""
    DOCUMENT = "document"
    VERIFICATION = "verification"
    USER = "user"
    BILLING = "billing"
    SYSTEM = "system"
    SECURITY = "security"
    INTEGRATION = "integration"

class EventSeverity(Enum):
    """Event severity levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EventDefinition:
    """Definition of a webhook event"""
    name: str
    category: EventCategory
    description: str
    severity: EventSeverity
    schema: Dict[str, Any]
    example_payload: Dict[str, Any]
    rate_limit: int = 100  # Events per minute per endpoint
    requires_authentication: bool = False
    
class WebhookEventService:
    """Handles webhook event definitions and formatting"""
    
    def __init__(self, db):
        self.db = db
        self._event_registry: Dict[str, EventDefinition] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Register built-in events
        self._register_builtin_events()
    
    def _register_builtin_events(self):
        """Register built-in event definitions"""
        
        # Document Processing Events
        self.register_event(
            name="document.processing.started",
            category=EventCategory.DOCUMENT,
            description="Document processing has started",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["document_id", "document_type", "processing_type"],
                "properties": {
                    "document_id": {"type": "string", "description": "Unique document identifier"},
                    "document_type": {"type": "string", "enum": ["invoice", "receipt", "bank_statement", "contract", "other"]},
                    "processing_type": {"type": "string", "enum": ["ocr", "ai_extraction", "validation", "all"]},
                    "file_size": {"type": "integer", "description": "File size in bytes"},
                    "pages": {"type": "integer", "description": "Number of pages"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}
                }
            },
            example_payload={
                "document_id": "doc_123456",
                "document_type": "invoice",
                "processing_type": "ai_extraction",
                "file_size": 2048576,
                "pages": 3,
                "priority": "normal"
            }
        )
        
        self.register_event(
            name="document.processing.completed",
            category=EventCategory.DOCUMENT,
            description="Document processing has completed successfully",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["document_id", "processing_duration_ms", "extraction_success"],
                "properties": {
                    "document_id": {"type": "string"},
                    "processing_duration_ms": {"type": "integer"},
                    "extraction_success": {"type": "boolean"},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "extracted_fields": {"type": "object"},
                    "quality_score": {"type": "number", "minimum": 0, "maximum": 100},
                    "manual_review_required": {"type": "boolean"}
                }
            },
            example_payload={
                "document_id": "doc_123456",
                "processing_duration_ms": 3450,
                "extraction_success": True,
                "confidence_score": 0.94,
                "quality_score": 87,
                "manual_review_required": False
            }
        )
        
        self.register_event(
            name="document.processing.failed",
            category=EventCategory.DOCUMENT,
            description="Document processing has failed",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["document_id", "error_code", "error_message"],
                "properties": {
                    "document_id": {"type": "string"},
                    "error_code": {"type": "string"},
                    "error_message": {"type": "string"},
                    "failure_stage": {"type": "string"},
                    "retry_count": {"type": "integer"},
                    "last_retry_at": {"type": "string", "format": "date-time"}
                }
            },
            example_payload={
                "document_id": "doc_123456",
                "error_code": "OCR_PROCESSING_FAILED",
                "error_message": "Unable to extract text from document",
                "failure_stage": "ocr_extraction",
                "retry_count": 2
            }
        )
        
        # Verification Events
        self.register_event(
            name="verification.assigned",
            category=EventCategory.VERIFICATION,
            description="Document assigned to verification queue",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["document_id", "verification_id", "assigned_to", "priority"],
                "properties": {
                    "document_id": {"type": "string"},
                    "verification_id": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "priority": {"type": "string"},
                    "estimated_duration_minutes": {"type": "integer"},
                    "completion_deadline": {"type": "string", "format": "date-time"}
                }
            },
            example_payload={
                "document_id": "doc_123456",
                "verification_id": "verify_789",
                "assigned_to": "reviewer_123",
                "priority": "high",
                "estimated_duration_minutes": 15,
                "completion_deadline": "2024-01-15T16:00:00Z"
            }
        )
        
        self.register_event(
            name="verification.completed",
            category=EventCategory.VERIFICATION,
            description="Verification task completed",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["verification_id", "status", "reviewer_id", "completed_at"],
                "properties": {
                    "verification_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["approved", "rejected", "needs_corrections"]},
                    "reviewer_id": {"type": "string"},
                    "completed_at": {"type": "string", "format": "date-time"},
                    "processing_time_minutes": {"type": "number"},
                    "quality_score": {"type": "number", "minimum": 0, "maximum": 100},
                    "changes_made": {"type": "array", "items": {"type": "string"}}
                }
            },
            example_payload={
                "verification_id": "verify_789",
                "status": "approved",
                "reviewer_id": "reviewer_123",
                "processing_time_minutes": 12.5,
                "quality_score": 95
            }
        )
        
        # User Management Events
        self.register_event(
            name="user.created",
            category=EventCategory.USER,
            description="New user account created",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["user_id", "email", "created_at", "registration_method"],
                "properties": {
                    "user_id": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "registration_method": {"type": "string"},
                    "subscription_plan": {"type": "string"},
                    "referrer_id": {"type": "string"}
                }
            }
        )
        
        self.register_event(
            name="user.updated",
            category=EventCategory.USER,
            description="User profile updated",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["user_id", "updated_fields", "updated_at"],
                "properties": {
                    "user_id": {"type": "string"},
                    "updated_fields": {"type": "array", "items": {"type": "string"}},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "changes_summary": {"type": "object"}
                }
            }
        )
        
        self.register_event(
            name="user.deactivated",
            category=EventCategory.USER,
            description="User account deactivated",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["user_id", "deactivated_at", "deactivation_reason"],
                "properties": {
                    "user_id": {"type": "string"},
                    "deactivated_at": {"type": "string", "format": "date-time"},
                    "deactivation_reason": {"type": "string"},
                    "requested_by": {"type": "string"}
                }
            }
        )
        
        # Billing Events
        self.register_event(
            name="billing.payment_succeeded",
            category=EventCategory.BILLING,
            description="Payment successfully processed",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["payment_id", "amount", "currency", "payment_method", "timestamp"],
                "properties": {
                    "payment_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "payment_method": {"type": "string"},
                    "subscription_id": {"type": "string"},
                    "invoice_id": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"}
                }
            }
        )
        
        self.register_event(
            name="billing.payment_failed",
            category=EventCategory.BILLING,
            description="Payment processing failed",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["payment_id", "amount", "currency", "failure_reason", "timestamp"],
                "properties": {
                    "payment_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "failure_reason": {"type": "string"},
                    "retry_count": {"type": "integer"},
                    "next_retry_at": {"type": "string", "format": "date-time"},
                    "timestamp": {"type": "string", "format": "date-time"}
                }
            }
        )
        
        self.register_event(
            name="billing.subscription_updated",
            category=EventCategory.BILLING,
            description="Subscription plan changed or renewed",
            severity=EventSeverity.NORMAL,
            schema={
                "type": "object",
                "required": ["subscription_id", "action", "plan_name", "effective_date"],
                "properties": {
                    "subscription_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["created", "upgraded", "downgraded", "cancelled", "renewed"]},
                    "previous_plan": {"type": "string"},
                    "new_plan": {"type": "string"},
                    "effective_date": {"type": "string", "format": "date-time"},
                    "billing_cycle": {"type": "string"}
                }
            }
        )
        
        # Security Events
        self.register_event(
            name="security.login_failure",
            category=EventCategory.SECURITY,
            description="Failed login attempt",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["user_id", "ip_address", "timestamp", "failure_reason"],
                "properties": {
                    "user_id": {"type": "string"},
                    "ip_address": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "failure_reason": {"type": "string"},
                    "user_agent": {"type": "string"},
                    "geo_location": {"type": "object"},
                    "risk_score": {"type": "number", "minimum": 0, "maximum": 100}
                }
            }
        )
        
        self.register_event(
            name="security.suspicious_activity",
            category=EventCategory.SECURITY,
            description="Suspicious activity detected",
            severity=EventSeverity.CRITICAL,
            schema={
                "type": "object",
                "required": ["user_id", "activity_type", "timestamp", "risk_level"],
                "properties": {
                    "user_id": {"type": "string"},
                    "activity_type": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string"},
                    "evidence": {"type": "object"},
                    "action_taken": {"type": "string"}
                }
            }
        )
        
        # System Events
        self.register_event(
            name="system.status_changed",
            category=EventCategory.SYSTEM,
            description="System status changed",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["service", "status", "timestamp"],
                "properties": {
                    "service": {"type": "string"},
                    "status": {"type": "string", "enum": ["healthy", "degraded", "down", "maintenance"]},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "previous_status": {"type": "string"},
                    "affected_features": {"type": "array", "items": {"type": "string"}},
                    "estimated_recovery": {"type": "string"}
                }
            }
        )
        
        self.register_event(
            name="system.performance_alert",
            category=EventCategory.SYSTEM,
            description="Performance threshold exceeded",
            severity=EventSeverity.HIGH,
            schema={
                "type": "object",
                "required": ["metric", "current_value", "threshold", "timestamp"],
                "properties": {
                    "metric": {"type": "string"},
                    "current_value": {"type": "number"},
                    "threshold": {"type": "number"},
                    "threshold_type": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "affected_services": {"type": "array", "items": {"type": "string"}}
                }
            }
        )
    
    def register_event(
        self,
        name: str,
        category: EventCategory,
        description: str,
        severity: EventSeverity,
        schema: Dict[str, Any],
        example_payload: Dict[str, Any],
        rate_limit: int = 100,
        requires_authentication: bool = False
    ):
        """Register a new event definition"""
        
        event_def = EventDefinition(
            name=name,
            category=category,
            description=description,
            severity=severity,
            schema=schema,
            example_payload=example_payload,
            rate_limit=rate_limit,
            requires_authentication=requires_authentication
        )
        
        self._event_registry[name] = event_def
        
        logger.info(f"Registered event definition: {name}")
    
    def get_event_definition(self, event_name: str) -> Optional[EventDefinition]:
        """Get event definition by name"""
        return self._event_registry.get(event_name)
    
    def list_events(self, category: Optional[EventCategory] = None) -> List[EventDefinition]:
        """List all event definitions, optionally filtered by category"""
        
        events = list(self._event_registry.values())
        
        if category:
            events = [event for event in events if event.category == category]
        
        return sorted(events, key=lambda x: (x.category.value, x.name))
    
    def format_event_payload(
        self,
        event_name: str,
        data: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format event payload according to schema"""
        
        event_def = self.get_event_definition(event_name)
        if not event_def:
            raise ValueError(f"Unknown event: {event_name}")
        
        # Base payload structure
        payload = {
            "id": str(uuid.uuid4()),
            "event": event_name,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "category": event_def.category.value,
            "severity": event_def.severity.value
        }
        
        # Add additional context if provided
        if additional_context:
            payload["context"] = additional_context
        
        # Validate against schema (basic validation)
        if not self._validate_payload_against_schema(data, event_def.schema):
            raise ValueError(f"Data does not match event schema for {event_name}")
        
        return payload
    
    def validate_payload_against_schema(self, data: Dict[str, Any], event_name: str) -> bool:
        """Validate payload against event schema"""
        
        event_def = self.get_event_definition(event_name)
        if not event_def:
            return False
        
        return self._validate_payload_against_schema(data, event_def.schema)
    
    def _validate_payload_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Basic schema validation"""
        
        try:
            required_fields = schema.get("required", [])
            
            # Check required fields
            for field in required_fields:
                if field not in data:
                    return False
            
            # Basic type checking (simplified)
            properties = schema.get("properties", {})
            
            for field, value in data.items():
                if field in properties:
                    field_schema = properties[field]
                    
                    # Type validation
                    expected_type = field_schema.get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        return False
                    
                    # String format validation
                    if expected_type == "string" and "format" in field_schema:
                        if not self._validate_string_format(value, field_schema["format"]):
                            return False
                    
                    # Enum validation
                    if "enum" in field_schema:
                        if value not in field_schema["enum"]:
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        
        type_checks = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        return isinstance(value, type_checks.get(expected_type, object))
    
    def _validate_string_format(self, value: str, format_type: str) -> bool:
        """Validate string format"""
        
        if format_type == "email":
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, value))
        
        elif format_type == "date-time":
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        
        return True
    
    def get_events_by_category(self, category: EventCategory) -> List[str]:
        """Get all event names for a specific category"""
        
        events = self.list_events(category)
        return [event.name for event in events]
    
    def get_event_categories(self) -> List[EventCategory]:
        """Get list of all event categories"""
        
        categories = set()
        for event_def in self._event_registry.values():
            categories.add(event_def.category)
        
        return sorted(list(categories), key=lambda x: x.value)
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """Register an event handler function"""
        
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        
        self._event_handlers[event_name].append(handler)
        
        logger.info(f"Registered event handler for {event_name}")
    
    def create_test_payload(self, event_name: str) -> Dict[str, Any]:
        """Create a test payload for an event"""
        
        event_def = self.get_event_definition(event_name)
        if not event_def:
            raise ValueError(f"Unknown event: {event_name}")
        
        return self.format_event_payload(
            event_name,
            event_def.example_payload,
            {"source": "test", "generated_at": datetime.utcnow().isoformat()}
        )