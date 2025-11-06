"""
Event Filters
Event filtering and transformation service
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import logging

from app.services.hooks.event_system import Event

logger = logging.getLogger(__name__)

class EventFilterService:
    """Service for filtering and transforming events"""
    
    def __init__(self):
        self.filter_cache = {}
        self.transformation_cache = {}
    
    def matches_conditions(
        self,
        event: Event,
        conditions: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if event matches filter conditions"""
        
        if not conditions:
            return True
        
        try:
            # Check each condition
            for field, condition in conditions.items():
                if not self._check_condition(event, field, condition):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking event conditions: {e}")
            return False
    
    def _check_condition(self, event: Event, field: str, condition: Any) -> bool:
        """Check a single condition against an event"""
        
        # Get event field value
        event_value = self._get_event_field(event, field)
        
        # Handle different condition types
        if isinstance(condition, dict):
            return self._check_complex_condition(event_value, condition)
        elif isinstance(condition, list):
            return event_value in condition
        else:
            return event_value == condition
    
    def _get_event_field(self, event: Event, field: str) -> Any:
        """Get a field value from an event"""
        
        # Direct attributes
        if hasattr(event, field):
            return getattr(event, field)
        
        # Nested fields in data
        if field in event.data:
            return event.data[field]
        
        # Nested data access (e.g., "data.user.email")
        if field.startswith("data."):
            path = field[5:].split(".")
            current = event.data
            for part in path:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        
        # Metadata
        if field.startswith("metadata.") and event.metadata:
            path = field[9:].split(".")
            current = event.metadata
            for part in path:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        
        return None
    
    def _check_complex_condition(self, event_value: Any, condition: Dict[str, Any]) -> bool:
        """Check complex condition with operators"""
        
        # Handle different operators
        if "eq" in condition:
            return event_value == condition["eq"]
        elif "ne" in condition:
            return event_value != condition["ne"]
        elif "gt" in condition:
            return event_value > condition["gt"]
        elif "gte" in condition:
            return event_value >= condition["gte"]
        elif "lt" in condition:
            return event_value < condition["lt"]
        elif "lte" in condition:
            return event_value <= condition["lte"]
        elif "in" in condition:
            return event_value in condition["in"]
        elif "not_in" in condition:
            return event_value not in condition["not_in"]
        elif "contains" in condition:
            if isinstance(event_value, str):
                return condition["contains"] in event_value.lower()
            elif isinstance(event_value, list):
                return condition["contains"] in event_value
            elif isinstance(event_value, dict):
                return condition["contains"] in event_value
            return False
        elif "starts_with" in condition:
            if isinstance(event_value, str):
                return event_value.startswith(condition["starts_with"])
            return False
        elif "ends_with" in condition:
            if isinstance(event_value, str):
                return event_value.endswith(condition["ends_with"])
            return False
        elif "regex" in condition:
            if isinstance(event_value, str):
                try:
                    pattern = re.compile(condition["regex"])
                    return pattern.search(event_value) is not None
                except re.error:
                    return False
            return False
        elif "between" in condition:
            if isinstance(event_value, (int, float)):
                min_val, max_val = condition["between"]
                return min_val <= event_value <= max_val
            return False
        elif "datetime_after" in condition:
            if isinstance(event_value, str):
                try:
                    event_dt = datetime.fromisoformat(event_value.replace('Z', '+00:00'))
                    filter_dt = datetime.fromisoformat(condition["datetime_after"].replace('Z', '+00:00'))
                    return event_dt > filter_dt
                except (ValueError, TypeError):
                    return False
            return False
        elif "datetime_before" in condition:
            if isinstance(event_value, str):
                try:
                    event_dt = datetime.fromisoformat(event_value.replace('Z', '+00:00'))
                    filter_dt = datetime.fromisoformat(condition["datetime_before"].replace('Z', '+00:00'))
                    return event_dt < filter_dt
                except (ValueError, TypeError):
                    return False
            return False
        
        return False
    
    def filter_events(
        self,
        events: List[Event],
        filter_rules: List[Dict[str, Any]]
    ) -> List[Event]:
        """Filter events based on multiple rules"""
        
        filtered_events = []
        
        for event in events:
            if self.matches_filter_rules(event, filter_rules):
                filtered_events.append(event)
        
        return filtered_events
    
    def matches_filter_rules(
        self,
        event: Event,
        filter_rules: List[Dict[str, Any]]
    ) -> bool:
        """Check if event matches any of the filter rules"""
        
        for rule in filter_rules:
            # Handle rule with logical operators
            rule_result = self._evaluate_rule(event, rule)
            
            # If rule uses 'any' operator, return True on first match
            if rule.get("any", False) and rule_result:
                return True
            
            # If rule uses 'all' operator, all conditions must match
            if not rule.get("any", False) and not rule_result:
                return False
        
        # If we get here, all 'all' rules matched
        return True
    
    def _evaluate_rule(self, event: Event, rule: Dict[str, Any]) -> bool:
        """Evaluate a single filter rule"""
        
        conditions = rule.get("conditions", {})
        if not conditions:
            return True
        
        # Handle rule with logical operators
        if "and" in conditions:
            and_conditions = conditions["and"]
            return all(
                self.matches_conditions(event, {"and": [cond]}) 
                for cond in and_conditions
            )
        
        if "or" in conditions:
            or_conditions = conditions["or"]
            return any(
                self.matches_conditions(event, {"or": [cond]}) 
                for cond in or_conditions
            )
        
        if "not" in conditions:
            not_condition = conditions["not"]
            return not self.matches_conditions(event, not_condition)
        
        # Simple condition
        return self.matches_conditions(event, conditions)
    
    def transform_event(
        self,
        event: Event,
        transformation_rules: Dict[str, Any]
    ) -> Event:
        """Transform an event according to transformation rules"""
        
        try:
            # Create a copy of the event
            transformed_event = Event(
                id=event.id,
                name=event.name,
                category=event.category,
                data=event.data.copy(),
                source=event.source,
                timestamp=event.timestamp,
                priority=event.priority,
                correlation_id=event.correlation_id,
                user_id=event.user_id,
                tenant_id=event.tenant_id,
                metadata=event.metadata.copy() if event.metadata else {},
                retry_count=event.retry_count,
                max_retries=event.max_retries
            )
            
            # Apply transformations
            for field, transformation in transformation_rules.items():
                self._apply_transformation(transformed_event, field, transformation)
            
            return transformed_event
            
        except Exception as e:
            logger.error(f"Error transforming event: {e}")
            return event
    
    def _apply_transformation(self, event: Event, field: str, transformation: Any):
        """Apply a single transformation to an event field"""
        
        if isinstance(transformation, str):
            # Simple string transformation
            if field.startswith("data."):
                data_path = field[5:].split(".")
                self._set_nested_value(event.data, data_path, transformation)
            elif field == "name":
                event.name = transformation
            elif field == "category":
                event.category = transformation
            elif field.startswith("metadata."):
                metadata_path = field[9:].split(".")
                self._set_nested_value(event.metadata, metadata_path, transformation)
        
        elif isinstance(transformation, dict):
            # Complex transformation
            if "map" in transformation:
                source_field = transformation["map"]
                mapped_value = self._get_event_field(event, source_field)
                if field.startswith("data."):
                    data_path = field[5:].split(".")
                    self._set_nested_value(event.data, data_path, mapped_value)
                elif field == "name":
                    event.name = mapped_value
                elif field == "category":
                    event.category = mapped_value
            elif "calculate" in transformation:
                # Mathematical calculation
                expression = transformation["calculate"]
                result = self._evaluate_expression(event, expression)
                if field.startswith("data."):
                    data_path = field[5:].split(".")
                    self._set_nested_value(event.data, data_path, result)
        
        elif callable(transformation):
            # Function transformation
            if field.startswith("data."):
                data_path = field[5:].split(".")
                original_value = self._get_nested_value(event.data, data_path[:-1]) or {}
                new_value = transformation(original_value)
                self._set_nested_value(event.data, data_path, new_value)
            elif field == "name":
                event.name = transformation(event.name)
            elif field == "category":
                event.category = transformation(event.category)
    
    def _set_nested_value(self, obj: Dict, path: List[str], value: Any):
        """Set a value in a nested dictionary using a path"""
        
        current = obj
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[path[-1]] = value
    
    def _get_nested_value(self, obj: Dict, path: List[str]) -> Any:
        """Get a value from a nested dictionary using a path"""
        
        current = obj
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _evaluate_expression(self, event: Event, expression: str) -> Any:
        """Evaluate a mathematical expression using event data"""
        
        try:
            # Simple expression evaluation (limited for security)
            # In production, use a proper expression parser
            
            # Replace variables with actual values
            def replace_var(match):
                var_name = match.group(1)
                value = self._get_event_field(event, var_name)
                return str(value) if value is not None else "0"
            
            # Replace variables like ${data.amount} with actual values
            processed_expression = re.sub(r'\$\{([^}]+)\}', replace_var, expression)
            
            # Only allow safe operations
            if re.search(r'[a-zA-Z_]', processed_expression):
                return 0  # Reject expressions with variables that aren't substitutions
            
            # Evaluate the expression
            result = eval(processed_expression)
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return 0
    
    def create_aggregation(
        self,
        events: List[Event],
        aggregation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate multiple events into a summary"""
        
        try:
            aggregation_result = {}
            
            for field, rule in aggregation_rules.items():
                aggregation_result[field] = self._aggregate_field(events, rule)
            
            return aggregation_result
            
        except Exception as e:
            logger.error(f"Error creating aggregation: {e}")
            return {}
    
    def _aggregate_field(self, events: List[Event], rule: Dict[str, Any]) -> Any:
        """Aggregate a field across multiple events"""
        
        aggregation_type = rule.get("type", "count")
        
        if aggregation_type == "count":
            return len(events)
        
        elif aggregation_type == "count_unique":
            field = rule.get("field")
            if not field:
                return 0
            
            values = set()
            for event in events:
                value = self._get_event_field(event, field)
                if value is not None:
                    values.add(value)
            
            return len(values)
        
        elif aggregation_type == "sum":
            field = rule.get("field")
            if not field:
                return 0
            
            total = 0
            for event in events:
                value = self._get_event_field(event, field)
                if isinstance(value, (int, float)):
                    total += value
            
            return total
        
        elif aggregation_type == "avg":
            field = rule.get("field")
            if not field:
                return 0
            
            total = 0
            count = 0
            for event in events:
                value = self._get_event_field(event, field)
                if isinstance(value, (int, float)):
                    total += value
                    count += 1
            
            return total / count if count > 0 else 0
        
        elif aggregation_type == "min":
            field = rule.get("field")
            if not field:
                return None
            
            values = []
            for event in events:
                value = self._get_event_field(event, field)
                if value is not None:
                    values.append(value)
            
            return min(values) if values else None
        
        elif aggregation_type == "max":
            field = rule.get("field")
            if not field:
                return None
            
            values = []
            for event in events:
                value = self._get_event_field(event, field)
                if value is not None:
                    values.append(value)
            
            return max(values) if values else None
        
        elif aggregation_type == "first":
            field = rule.get("field")
            if not field:
                return None
            
            for event in events:
                value = self._get_event_field(event, field)
                if value is not None:
                    return value
            
            return None
        
        elif aggregation_type == "last":
            field = rule.get("field")
            if not field:
                return None
            
            for event in reversed(events):
                value = self._get_event_field(event, field)
                if value is not None:
                    return value
            
            return None
        
        return None
    
    def enrich_event(
        self,
        event: Event,
        enrichment_rules: Dict[str, Any]
    ) -> Event:
        """Enrich an event with additional data"""
        
        try:
            # Create a copy of the event
            enriched_event = Event(
                id=event.id,
                name=event.name,
                category=event.category,
                data=event.data.copy(),
                source=event.source,
                timestamp=event.timestamp,
                priority=event.priority,
                correlation_id=event.correlation_id,
                user_id=event.user_id,
                tenant_id=event.tenant_id,
                metadata=(event.metadata or {}).copy(),
                retry_count=event.retry_count,
                max_retries=event.max_retries
            )
            
            # Apply enrichment rules
            for field, enrichment in enrichment_rules.items():
                self._apply_enrichment(enriched_event, field, enrichment)
            
            return enriched_event
            
        except Exception as e:
            logger.error(f"Error enriching event: {e}")
            return event
    
    def _apply_enrichment(self, event: Event, field: str, enrichment: Any):
        """Apply enrichment to an event"""
        
        if isinstance(enrichment, dict):
            if "static" in enrichment:
                # Static value enrichment
                value = enrichment["static"]
                self._set_event_field(event, field, value)
            elif "from_lookup" in enrichment:
                # Lookup from external source (simplified)
                lookup_key = enrichment["from_lookup"]
                lookup_value = self._perform_lookup(event, lookup_key)
                self._set_event_field(event, field, lookup_value)
        
        elif isinstance(enrichment, list):
            # Apply multiple enrichments
            for item in enrichment:
                self._apply_enrichment(event, field, item)
    
    def _set_event_field(self, event: Event, field: str, value: Any):
        """Set a field value on an event"""
        
        if field.startswith("data."):
            data_path = field[5:].split(".")
            self._set_nested_value(event.data, data_path, value)
        elif field == "name":
            event.name = value
        elif field == "category":
            event.category = value
        elif field.startswith("metadata."):
            metadata_path = field[9:].split(".")
            if not event.metadata:
                event.metadata = {}
            self._set_nested_value(event.metadata, metadata_path, value)
        elif hasattr(event, field):
            setattr(event, field, value)
    
    def _perform_lookup(self, event: Event, lookup_key: str) -> Any:
        """Perform a lookup for enrichment data"""
        
        # This is a simplified lookup implementation
        # In production, this would integrate with external data sources
        
        if lookup_key == "user_profile":
            # Simulate user profile lookup
            return {
                "user_name": event.user_id or "Unknown User",
                "user_type": "standard",
                "account_status": "active"
            }
        elif lookup_key == "ip_geo":
            # Simulate IP geolocation lookup
            return {
                "country": "US",
                "city": "San Francisco",
                "timezone": "America/Los_Angeles"
            }
        elif lookup_key == "device_info":
            # Simulate device information lookup
            return {
                "device_type": "desktop",
                "browser": "Chrome",
                "os": "Windows"
            }
        
        return None
    
    def batch_filter_and_transform(
        self,
        events: List[Event],
        rules: Dict[str, Any]
    ) -> Tuple[List[Event], List[Event]]:
        """Batch filter and transform events"""
        
        filtered_events = []
        transformed_events = []
        
        for event in events:
            # Apply filters
            if self.matches_filter_rules(event, rules.get("filters", [])):
                filtered_events.append(event)
                
                # Apply transformations
                if "transformations" in rules:
                    transformed_event = self.transform_event(event, rules["transformations"])
                    transformed_events.append(transformed_event)
                else:
                    transformed_events.append(event)
        
        return filtered_events, transformed_events
    
    def create_composite_filter(
        self,
        base_filters: List[Dict[str, Any]],
        operator: str = "and"
    ) -> Dict[str, Any]:
        """Create a composite filter from multiple base filters"""
        
        if operator == "and":
            return {
                "and": base_filters
            }
        elif operator == "or":
            return {
                "or": base_filters
            }
        elif operator == "not":
            return {
                "not": base_filters[0] if base_filters else {}
            }
        
        return {}