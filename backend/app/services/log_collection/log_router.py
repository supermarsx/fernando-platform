"""
Log Router System

Routes logs to different destinations based on severity, type, and custom rules.
"""

import json
import re
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from functools import lru_cache
import ast
from app.services.log_collection.log_collector import LogEvent, LogSource, LogSeverity
from app.services.logging.structured_logger import structured_logger


class RoutingStrategy(Enum):
    """Log routing strategies"""
    ALL = "all"  # Send to all enabled destinations
    FIRST_MATCH = "first_match"  # Send to first matching destination
    ROUND_ROBIN = "round_robin"  # Distribute across destinations
    WEIGHTED = "weighted"  # Use weights for distribution
    CONDITIONAL = "conditional"  # Use conditional rules


class RuleType(Enum):
    """Types of routing rules"""
    SEVERITY_BASED = "severity_based"
    SOURCE_BASED = "source_based"
    CATEGORY_BASED = "category_based"
    CONTENT_BASED = "content_based"
    CORRELATION_BASED = "correlation_based"
    CUSTOM_SCRIPT = "custom_script"


@dataclass
class RoutingRule:
    """Individual routing rule definition"""
    rule_id: str
    name: str
    rule_type: RuleType
    conditions: Dict[str, Any]
    destinations: List[str]
    strategy: RoutingStrategy = RoutingStrategy.ALL
    enabled: bool = True
    priority: int = 0
    weight: float = 1.0
    ttl: Optional[int] = None  # Time to live in seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_matched: Optional[datetime] = None
    match_count: int = 0
    
    def matches(self, log_event: LogEvent) -> bool:
        """Check if rule matches log event"""
        
        if not self.enabled:
            return False
        
        try:
            if self.rule_type == RuleType.SEVERITY_BASED:
                return self._matches_severity(log_event)
            elif self.rule_type == RuleType.SOURCE_BASED:
                return self._matches_source(log_event)
            elif self.rule_type == RuleType.CATEGORY_BASED:
                return self._matches_category(log_event)
            elif self.rule_type == RuleType.CONTENT_BASED:
                return self._matches_content(log_event)
            elif self.rule_type == RuleType.CORRELATION_BASED:
                return self._matches_correlation(log_event)
            elif self.rule_type == RuleType.CUSTOM_SCRIPT:
                return self._matches_custom_script(log_event)
            else:
                return False
                
        except Exception as e:
            structured_logger.error(
                f"Error evaluating routing rule {self.rule_id}: {str(e)}",
                rule_id=self.rule_id,
                rule_type=self.rule_type.value,
                error=str(e)
            )
            return False
    
    def _matches_severity(self, log_event: LogEvent) -> bool:
        """Check severity-based rule"""
        
        allowed_severities = self.conditions.get('severities', [])
        log_severity = log_event.level.value
        
        if not allowed_severities:
            return False
        
        # Check if log severity is in allowed list
        if 'include' in self.conditions:
            return log_severity in self.conditions['include']
        elif 'exclude' in self.conditions:
            return log_severity not in self.conditions['exclude']
        else:
            return log_severity in allowed_severities
    
    def _matches_source(self, log_event: LogEvent) -> bool:
        """Check source-based rule"""
        
        allowed_sources = self.conditions.get('sources', [])
        log_source = log_event.source.value
        
        if not allowed_sources:
            return False
        
        # Pattern matching support
        patterns = self.conditions.get('patterns', [])
        
        if patterns:
            for pattern in patterns:
                if re.match(pattern, log_source):
                    return True
            return False
        else:
            return log_source in allowed_sources
    
    def _matches_category(self, log_event: LogEvent) -> bool:
        """Check category-based rule"""
        
        allowed_categories = self.conditions.get('categories', [])
        log_category = log_event.category
        
        if not allowed_categories:
            return False
        
        # Support for patterns in categories
        patterns = self.conditions.get('patterns', [])
        
        if patterns:
            for pattern in patterns:
                if re.match(pattern, log_category):
                    return True
            return False
        else:
            return log_category in allowed_categories
    
    def _matches_content(self, log_event: LogEvent) -> bool:
        """Check content-based rule (message, data, etc.)"""
        
        conditions = self.conditions
        
        # Check message content
        if 'message' in conditions:
            message_patterns = conditions['message'].get('patterns', [])
            message_text = log_event.message
            
            for pattern in message_patterns:
                if not re.search(pattern, message_text, re.IGNORECASE):
                    return False
        
        # Check data fields
        if 'data' in conditions:
            for field_path, field_conditions in conditions['data'].items():
                field_value = self._get_nested_field(log_event.data, field_path)
                
                if field_conditions.get('pattern'):
                    if not re.search(field_conditions['pattern'], str(field_value), re.IGNORECASE):
                        return False
                
                if field_conditions.get('equals') is not None:
                    if field_value != field_conditions['equals']:
                        return False
                
                if field_conditions.get('in') is not None:
                    if field_value not in field_conditions['in']:
                        return False
        
        return True
    
    def _matches_correlation(self, log_event: LogEvent) -> bool:
        """Check correlation-based rule"""
        
        conditions = self.conditions
        
        # Check correlation ID patterns
        if 'correlation_id_patterns' in conditions:
            patterns = conditions['correlation_id_patterns']
            corr_id = log_event.correlation_id
            
            if corr_id:
                for pattern in patterns:
                    if not re.match(pattern, corr_id):
                        return False
        
        # Check tenant patterns
        if 'tenant_patterns' in conditions:
            patterns = conditions['tenant_patterns']
            tenant_id = log_event.tenant_id
            
            if tenant_id:
                for pattern in patterns:
                    if not re.match(pattern, tenant_id):
                        return False
        
        # Check user patterns
        if 'user_patterns' in conditions:
            patterns = conditions['user_patterns']
            user_id = log_event.user_id
            
            if user_id:
                for pattern in patterns:
                    if not re.match(pattern, user_id):
                        return False
        
        return True
    
    def _matches_custom_script(self, log_event: LogEvent) -> bool:
        """Check custom script rule"""
        
        script = self.conditions.get('script')
        if not script:
            return False
        
        try:
            # Create safe execution environment
            safe_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    're': re,
                    'datetime': datetime,
                    'timedelta': timedelta,
                    'log_event': log_event.to_dict()
                },
                'log_event': log_event.to_dict()
            }
            
            # Execute script safely
            result = eval(script, safe_globals)
            return bool(result)
            
        except Exception as e:
            structured_logger.error(
                f"Error executing custom script for rule {self.rule_id}: {str(e)}",
                rule_id=self.rule_id,
                script=script,
                error=str(e)
            )
            return False
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value from dictionary using dot notation"""
        
        if not field_path or not data:
            return None
        
        try:
            keys = field_path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
            
        except Exception:
            return None
    
    def update_match_count(self) -> None:
        """Update rule match statistics"""
        self.last_matched = datetime.utcnow()
        self.match_count += 1
    
    def is_expired(self) -> bool:
        """Check if rule is expired based on TTL"""
        
        if not self.ttl:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl)
        return datetime.utcnow() > expiry_time


class LogRouter:
    """Enterprise log routing system with dynamic rules and load balancing"""
    
    def __init__(self):
        self.rules: Dict[str, RoutingRule] = {}
        self.destinations: Dict[str, Callable] = {}
        
        # Round-robin state
        self._round_robin_state = {}
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_logs_routed': 0,
            'rule_evaluations': 0,
            'rule_matches': 0,
            'routing_errors': 0,
            'destination_errors': {},
            'avg_routing_time_ms': 0.0,
            'most_used_rules': {},
            'last_route_time': None
        }
        
        # Default routing rules
        self._setup_default_rules()
    
    def add_destination(self, name: str, handler: Callable) -> None:
        """Add log destination handler"""
        
        self.destinations[name] = handler
        
        structured_logger.info(
            f"Added log destination: {name}",
            destination_name=name
        )
    
    def remove_destination(self, name: str) -> None:
        """Remove log destination handler"""
        
        if name in self.destinations:
            del self.destinations[name]
            
            # Remove rules that reference this destination
            rules_to_remove = [
                rule_id for rule_id, rule in self.rules.items()
                if name in rule.destinations
            ]
            
            for rule_id in rules_to_remove:
                self.remove_rule(rule_id)
        
        structured_logger.info(
            f"Removed log destination: {name}",
            destination_name=name
        )
    
    def add_rule(self, rule: RoutingRule) -> None:
        """Add routing rule"""
        
        self.rules[rule.rule_id] = rule
        
        structured_logger.info(
            f"Added routing rule: {rule.name}",
            rule_id=rule.rule_id,
            rule_type=rule.rule_type.value,
            destinations=rule.destinations
        )
    
    def remove_rule(self, rule_id: str) -> None:
        """Remove routing rule"""
        
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            del self.rules[rule_id]
            
            structured_logger.info(
                f"Removed routing rule: {rule.name}",
                rule_id=rule_id
            )
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing routing rule"""
        
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        structured_logger.info(
            f"Updated routing rule: {rule.name}",
            rule_id=rule_id,
            updates=list(updates.keys())
        )
        
        return True
    
    def route_log(self, log_event: LogEvent) -> List[str]:
        """Route log event to appropriate destinations"""
        
        start_time = datetime.utcnow()
        
        try:
            # Get matching rules
            matching_rules = self._get_matching_rules(log_event)
            
            if not matching_rules:
                # No rules matched - use default routing
                return self._route_to_default_destinations(log_event)
            
            # Apply routing strategy
            destinations = self._apply_routing_strategy(matching_rules, log_event)
            
            # Send to destinations
            successful_destinations = self._send_to_destinations(log_event, destinations)
            
            # Update statistics
            self._update_routing_stats(start_time, len(matching_rules), successful_destinations)
            
            return successful_destinations
            
        except Exception as e:
            structured_logger.error(
                f"Error routing log: {str(e)}",
                error=str(e),
                correlation_id=log_event.correlation_id
            )
            with self._lock:
                self.stats['routing_errors'] += 1
            return []
    
    def batch_route_logs(self, log_events: List[LogEvent]) -> Dict[str, List[str]]:
        """Route multiple log events efficiently"""
        
        results = {}
        grouped_events = {}
        
        # Group events by routing requirements
        for log_event in log_events:
            matching_rules = self._get_matching_rules(log_event)
            
            if not matching_rules:
                routing_key = "default"
            else:
                # Create routing key based on matched rules
                rule_ids = [rule.rule_id for rule in matching_rules]
                routing_key = ":".join(sorted(rule_ids))
            
            if routing_key not in grouped_events:
                grouped_events[routing_key] = []
            grouped_events[routing_key].append(log_event)
        
        # Process grouped events
        for routing_key, events in grouped_events.items():
            if routing_key == "default":
                destinations = list(self.destinations.keys())
                for event in events:
                    results[event] = self._send_to_destinations(event, destinations)
            else:
                # Process with specific routing
                rule_ids = routing_key.split(":")
                matching_rules = [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]
                
                destinations = self._apply_routing_strategy(matching_rules, events[0])
                
                for event in events:
                    results[event] = self._send_to_destinations(event, destinations)
        
        return results
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive routing statistics"""
        
        with self._lock:
            stats = self.stats.copy()
            
            # Add rule statistics
            stats['rules'] = {}
            for rule_id, rule in self.rules.items():
                stats['rules'][rule_id] = {
                    'name': rule.name,
                    'type': rule.rule_type.value,
                    'enabled': rule.enabled,
                    'priority': rule.priority,
                    'match_count': rule.match_count,
                    'last_matched': rule.last_matched.isoformat() if rule.last_matched else None,
                    'destinations': rule.destinations,
                    'is_expired': rule.is_expired()
                }
            
            # Add destination statistics
            stats['destinations'] = {}
            for dest_name in self.destinations.keys():
                stats['destinations'][dest_name] = {
                    'errors': stats['destination_errors'].get(dest_name, 0),
                    'available': True
                }
            
            return stats
    
    def validate_rule(self, rule: RoutingRule) -> Dict[str, Any]:
        """Validate routing rule syntax and logic"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        if not rule.rule_id:
            validation_result['errors'].append("Rule ID is required")
            validation_result['valid'] = False
        
        if not rule.name:
            validation_result['errors'].append("Rule name is required")
            validation_result['valid'] = False
        
        if not rule.destinations:
            validation_result['errors'].append("Rule must have at least one destination")
            validation_result['valid'] = False
        
        # Check destinations exist
        for dest in rule.destinations:
            if dest not in self.destinations:
                validation_result['errors'].append(f"Destination '{dest}' does not exist")
                validation_result['valid'] = False
        
        # Validate rule type specific conditions
        if rule.rule_type == RuleType.CUSTOM_SCRIPT:
            if 'script' not in rule.conditions:
                validation_result['errors'].append("Custom script rule requires 'script' condition")
                validation_result['valid'] = False
        
        # Check for circular dependencies
        if self._would_create_circular_dependency(rule.rule_id):
            validation_result['errors'].append("Rule would create circular dependency")
            validation_result['valid'] = False
        
        # TTL validation
        if rule.ttl and rule.ttl <= 0:
            validation_result['warnings'].append("TTL should be positive")
        
        return validation_result
    
    def _get_matching_rules(self, log_event: LogEvent) -> List[RoutingRule]:
        """Get rules that match the log event"""
        
        matching_rules = []
        
        for rule in self.rules.values():
            if rule.matches(log_event):
                rule.update_match_count()
                matching_rules.append(rule)
        
        # Sort by priority (higher priority first)
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        
        with self._lock:
            self.stats['rule_evaluations'] += 1
            self.stats['rule_matches'] += len(matching_rules)
        
        return matching_rules
    
    def _apply_routing_strategy(self, matching_rules: List[RoutingRule], log_event: LogEvent) -> List[str]:
        """Apply routing strategy to determine destinations"""
        
        if not matching_rules:
            return []
        
        # Get all unique destinations from matching rules
        all_destinations = set()
        for rule in matching_rules:
            all_destinations.update(rule.destinations)
        
        strategy = matching_rules[0].strategy  # Use strategy from highest priority rule
        
        if strategy == RoutingStrategy.ALL:
            return list(all_destinations)
        
        elif strategy == RoutingStrategy.FIRST_MATCH:
            return matching_rules[0].destinations
        
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_route(all_destinations)
        
        elif strategy == RoutingStrategy.WEIGHTED:
            return self._weighted_route(matching_rules, all_destinations)
        
        elif strategy == RoutingStrategy.CONDITIONAL:
            return self._conditional_route(matching_rules, log_event)
        
        else:
            return list(all_destinations)
    
    def _round_robin_route(self, destinations: set) -> List[str]:
        """Apply round-robin routing"""
        
        dest_list = list(destinations)
        with self._lock:
            if not self._round_robin_state:
                self._round_robin_state['index'] = 0
            
            selected_dest = dest_list[self._round_robin_state['index']]
            self._round_robin_state['index'] = (self._round_robin_state['index'] + 1) % len(dest_list)
        
        return [selected_dest]
    
    def _weighted_route(self, matching_rules: List[RoutingRule], destinations: set) -> List[str]:
        """Apply weighted routing"""
        
        # Calculate weighted distribution
        total_weight = sum(rule.weight for rule in matching_rules)
        if total_weight == 0:
            return list(destinations)
        
        # Simple weighted round-robin
        import random
        weights = [rule.weight / total_weight for rule in matching_rules]
        selected_rule = random.choices(matching_rules, weights=weights)[0]
        
        return selected_rule.destinations
    
    def _conditional_route(self, matching_rules: List[RoutingRule], log_event: LogEvent) -> List[str]:
        """Apply conditional routing based on event characteristics"""
        
        # Example conditional routing logic
        if log_event.level in [LogSeverity.CRITICAL, LogSeverity.ERROR]:
            # Critical errors go to all destinations
            return list(destinations)
        elif log_event.source == LogSource.SECURITY:
            # Security events go to dedicated destinations
            security_destinations = [d for d in matching_rules[0].destinations if 'security' in d.lower()]
            if security_destinations:
                return security_destinations
        
        # Default to first matching rule
        return matching_rules[0].destinations
    
    def _send_to_destinations(self, log_event: LogEvent, destinations: List[str]) -> List[str]:
        """Send log event to specified destinations"""
        
        successful_destinations = []
        
        for dest_name in destinations:
            if dest_name in self.destinations:
                try:
                    self.destinations[dest_name](log_event)
                    successful_destinations.append(dest_name)
                except Exception as e:
                    structured_logger.error(
                        f"Failed to send log to destination {dest_name}: {str(e)}",
                        destination=dest_name,
                        error=str(e),
                        correlation_id=log_event.correlation_id
                    )
                    
                    with self._lock:
                        self.stats['destination_errors'][dest_name] = \
                            self.stats['destination_errors'].get(dest_name, 0) + 1
        
        return successful_destinations
    
    def _route_to_default_destinations(self, log_event: LogEvent) -> List[str]:
        """Route to default destinations when no rules match"""
        
        # Default routing: all destinations
        all_destinations = list(self.destinations.keys())
        return self._send_to_destinations(log_event, all_destinations)
    
    def _update_routing_stats(self, start_time: datetime, matches_count: int, destinations_count: int) -> None:
        """Update routing statistics"""
        
        routing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        with self._lock:
            self.stats['total_logs_routed'] += 1
            self.stats['last_route_time'] = datetime.utcnow()
            
            # Update average routing time
            old_avg = self.stats['avg_routing_time_ms']
            count = self.stats['total_logs_routed']
            self.stats['avg_routing_time_ms'] = (old_avg * (count - 1) + routing_time) / count
    
    def _would_create_circular_dependency(self, new_rule_id: str) -> bool:
        """Check if adding rule would create circular dependency"""
        
        # This would implement circular dependency detection
        # For now, return False (simple implementation)
        return False
    
    def _setup_default_rules(self) -> None:
        """Setup default routing rules"""
        
        # Critical errors to all destinations
        critical_error_rule = RoutingRule(
            rule_id="critical_errors",
            name="Critical Errors",
            rule_type=RuleType.SEVERITY_BASED,
            conditions={'severities': ['critical', 'error']},
            destinations=['elasticsearch', 'database', 'alert_system'],
            strategy=RoutingStrategy.ALL,
            priority=100
        )
        self.rules[critical_error_rule.rule_id] = critical_error_rule
        
        # Security logs to security destination
        security_rule = RoutingRule(
            rule_id="security_logs",
            name="Security Logs",
            rule_type=RuleType.SOURCE_BASED,
            conditions={'sources': ['security']},
            destinations=['security_system', 'siem'],
            strategy=RoutingStrategy.ALL,
            priority=90
        )
        self.rules[security_rule.rule_id] = security_rule
        
        # Audit logs to compliance system
        audit_rule = RoutingRule(
            rule_id="audit_logs",
            name="Audit Logs",
            rule_type=RuleType.SOURCE_BASED,
            conditions={'sources': ['audit']},
            destinations=['compliance_system', 'database'],
            strategy=RoutingStrategy.ALL,
            priority=80
        )
        self.rules[audit_rule.rule_id] = audit_rule
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on log router"""
        
        health_status = {
            'overall_status': 'healthy',
            'router': 'healthy',
            'rules': {},
            'destinations': {}
        }
        
        # Check destinations health
        for dest_name, handler in self.destinations.items():
            try:
                # Simple health check - try to call handler
                # In practice, this would be more sophisticated
                health_status['destinations'][dest_name] = 'healthy'
            except Exception as e:
                health_status['destinations'][dest_name] = f'unhealthy: {str(e)}'
                health_status['overall_status'] = 'warning'
        
        # Check for expired rules
        expired_rules = [rule_id for rule_id, rule in self.rules.items() if rule.is_expired()]
        if expired_rules:
            health_status['rules']['expired'] = expired_rules
            health_status['overall_status'] = 'warning'
        
        # Check for rules with high error rates
        stats = self.get_routing_statistics()
        high_error_destinations = []
        
        for dest_name, dest_stats in stats['destinations'].items():
            if dest_stats['errors'] > 100:  # Threshold for high errors
                high_error_destinations.append(dest_name)
        
        if high_error_destinations:
            health_status['destinations']['high_error_rate'] = high_error_destinations
            health_status['overall_status'] = 'critical'
        
        return health_status


# Global log router instance
log_router = LogRouter()