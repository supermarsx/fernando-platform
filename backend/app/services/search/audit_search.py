"""
Audit Search Service for Compliance and Security
Provides specialized searching across audit trail logs with compliance features
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..elk import ElasticsearchClient

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILURE = "login_failure"
    ACCESS_GRANT = "access_grant"
    ACCESS_DENY = "access_deny"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_STARTUP = "system_startup"
    BACKUP = "backup"
    RESTORE = "restore"
    EXPORT = "export"
    IMPORT = "import"


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditSearchCriteria:
    """Advanced audit search criteria"""
    event_types: List[AuditEventType] = None
    user_ids: List[str] = None
    resource_types: List[str] = None
    risk_levels: List[RiskLevel] = None
    success_only: bool = None
    date_range: Tuple[datetime, datetime] = None
    ip_addresses: List[str] = None
    compliance_relevant: bool = None
    geo_locations: List[str] = None
    search_pattern: str = None
    result_limit: int = 1000


@dataclass
class AuditTimeline:
    """Audit event timeline entry"""
    timestamp: datetime
    event_type: str
    user_id: str
    resource: str
    success: bool
    details: Dict[str, Any]
    risk_score: float
    compliance_flag: bool


class AuditSearchService:
    """Specialized service for audit log searching and analysis"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Initialize audit search service
        
        Args:
            es_client: Elasticsearch client
        """
        self.es_client = es_client
        
        # Audit-specific search patterns
        self.audit_patterns = {
            'suspicious_login_pattern': {
                'description': 'Detect suspicious login patterns',
                'conditions': {
                    'event_types': [AuditEventType.LOGIN_FAILURE],
                    'time_window': timedelta(hours=1),
                    'threshold': 5
                },
                'analysis': 'high_risk_login_attempts'
            },
            'privilege_escalation': {
                'description': 'Detect privilege escalation attempts',
                'conditions': {
                    'event_types': [AuditEventType.PRIVILEGE_ESCALATION, AuditEventType.ACCESS_GRANT],
                    'success_only': False
                },
                'analysis': 'unauthorized_privilege_changes'
            },
            'data_exfiltration': {
                'description': 'Detect potential data exfiltration',
                'conditions': {
                    'event_types': [AuditEventType.DATA_ACCESS, AuditEventType.EXPORT],
                    'volume_threshold': True
                },
                'analysis': 'unusual_data_access_patterns'
            },
            'configuration_drift': {
                'description': 'Detect configuration changes',
                'conditions': {
                    'event_types': [AuditEventType.CONFIGURATION_CHANGE],
                    'risk_levels': [RiskLevel.HIGH, RiskLevel.CRITICAL]
                },
                'analysis': 'critical_config_changes'
            }
        }
        
        # Compliance mappings
        self.compliance_mappings = {
            'GDPR': {
                'data_access_events': [AuditEventType.DATA_ACCESS, AuditEventType.EXPORT],
                'consent_events': [AuditEventType.ACCESS_GRANT],
                'retention_events': [AuditEventType.DATA_DELETION],
                'required_fields': ['user_id', 'ip_address', 'timestamp', 'resource']
            },
            'SOX': {
                'financial_events': [AuditEventType.DATA_MODIFICATION, AuditEventType.CONFIGURATION_CHANGE],
                'approval_events': [AuditEventType.ACCESS_GRANT],
                'access_events': [AuditEventType.DATA_ACCESS],
                'required_fields': ['user_id', 'timestamp', 'resource', 'success']
            },
            'PCI_DSS': {
                'cardholder_events': [AuditEventType.DATA_ACCESS, AuditEventType.DATA_MODIFICATION],
                'system_events': [AuditEventType.SYSTEM_STARTUP, AuditEventType.SYSTEM_SHUTDOWN],
                'access_events': [AuditEventType.LOGIN, AuditEventType.LOGIN_FAILURE],
                'required_fields': ['user_id', 'ip_address', 'timestamp', 'event_type', 'success']
            }
        }
    
    def search_audit_logs(self, criteria: AuditSearchCriteria) -> Dict[str, Any]:
        """
        Search audit logs with advanced filtering
        
        Args:
            criteria: Search criteria
            
        Returns:
            Search results with audit analysis
        """
        try:
            # Build Elasticsearch query
            query = self._build_audit_query(criteria)
            
            # Add audit-specific aggregations
            aggregations = {
                'event_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1h',
                        'min_doc_count': 0
                    }
                },
                'user_activity': {
                    'terms': {
                        'field': 'user_id',
                        'size': 50
                    }
                },
                'resource_access': {
                    'terms': {
                        'field': 'resource',
                        'size': 50
                    }
                },
                'success_rate': {
                    'avg': {
                        'script': {
                            'source': 'doc[\"success\"].value ? 1 : 0'
                        }
                    }
                },
                'risk_analysis': {
                    'terms': {
                        'field': 'risk_level',
                        'size': 10
                    }
                }
            }
            
            # Execute search
            response = self.es_client.advanced_search(
                index_types=['audit_logs'],
                query=query,
                aggregations=aggregations,
                size=criteria.result_limit
            )
            
            # Process results
            results = self._process_audit_results(response, criteria)
            
            logger.info(f"Audit search completed: {len(results['events'])} events found")
            return results
            
        except Exception as e:
            logger.error(f"Audit search failed: {e}")
            raise
    
    def _build_audit_query(self, criteria: AuditSearchCriteria) -> Dict:
        """Build Elasticsearch query from audit search criteria"""
        must_conditions = []
        filter_conditions = []
        
        # Event types filter
        if criteria.event_types:
            event_type_values = [event.value for event in criteria.event_types]
            must_conditions.append({
                'terms': {'event_type': event_type_values}
            })
        
        # User filter
        if criteria.user_ids:
            must_conditions.append({
                'terms': {'user_id': criteria.user_ids}
            })
        
        # Resource filter
        if criteria.resource_types:
            must_conditions.append({
                'terms': {'resource': criteria.resource_types}
            })
        
        # Risk level filter
        if criteria.risk_levels:
            risk_values = [level.value for level in criteria.risk_levels]
            must_conditions.append({
                'terms': {'risk_level': risk_values}
            })
        
        # Success filter
        if criteria.success_only is not None:
            must_conditions.append({
                'term': {'success': criteria.success_only}
            })
        
        # Date range filter
        if criteria.date_range:
            start_time, end_time = criteria.date_range
            filter_conditions.append({
                'range': {
                    'timestamp': {
                        'gte': start_time,
                        'lte': end_time
                    }
                }
            })
        
        # IP address filter
        if criteria.ip_addresses:
            must_conditions.append({
                'terms': {'ip_address': criteria.ip_addresses}
            })
        
        # Compliance relevant filter
        if criteria.compliance_relevant is not None:
            must_conditions.append({
                'term': {'compliance_flag': criteria.compliance_relevant}
            })
        
        # Search pattern filter
        if criteria.search_pattern:
            must_conditions.append({
                'multi_match': {
                    'query': criteria.search_pattern,
                    'fields': ['details.*', 'message', 'user_agent'],
                    'fuzziness': 'AUTO'
                }
            })
        
        # Build final query
        query = {'bool': {'must': must_conditions, 'filter': filter_conditions}}
        
        # Default to match_all if no conditions
        if not must_conditions and not filter_conditions:
            query = {'match_all': {}}
        
        return query
    
    def _process_audit_results(self, response: Dict, criteria: AuditSearchCriteria) -> Dict:
        """Process audit search results with additional analysis"""
        events = []
        for hit in response['hits']['hits']:
            event = hit['_source']
            events.append({
                'timestamp': event.get('timestamp'),
                'event_type': event.get('event_type'),
                'user_id': event.get('user_id'),
                'user_email': event.get('user_email'),
                'resource': event.get('resource'),
                'success': event.get('success'),
                'risk_level': event.get('risk_level'),
                'ip_address': event.get('ip_address'),
                'details': event.get('details', {}),
                'compliance_flag': event.get('compliance_flag', False),
                'changes': event.get('changes', {})
            })
        
        # Calculate additional metrics
        aggregations = response.get('aggregations', {})
        
        analysis = {
            'total_events': len(events),
            'success_rate': aggregations.get('success_rate', {}).get('value', 0) * 100,
            'unique_users': len(aggregations.get('user_activity', {}).get('buckets', [])),
            'unique_resources': len(aggregations.get('resource_access', {}).get('buckets', [])),
            'risk_distribution': self._analyze_risk_distribution(aggregations),
            'timeline_data': self._extract_timeline_data(aggregations),
            'compliance_score': self._calculate_compliance_score(events),
            'anomalies': self._detect_audit_anomalies(events)
        }
        
        return {
            'events': events,
            'analysis': analysis,
            'aggregations': aggregations,
            'total': response['hits']['total']['value']
        }
    
    def _analyze_risk_distribution(self, aggregations: Dict) -> Dict:
        """Analyze risk level distribution"""
        risk_buckets = aggregations.get('risk_analysis', {}).get('buckets', [])
        
        distribution = {}
        for bucket in risk_buckets:
            level = bucket['key']
            count = bucket['doc_count']
            distribution[level] = {
                'count': count,
                'percentage': 0  # Will be calculated
            }
        
        total = sum(item['count'] for item in distribution.values())
        if total > 0:
            for level in distribution:
                distribution[level]['percentage'] = (distribution[level]['count'] / total) * 100
        
        return distribution
    
    def _extract_timeline_data(self, aggregations: Dict) -> List[Dict]:
        """Extract timeline data for visualization"""
        timeline_buckets = aggregations.get('event_timeline', {}).get('buckets', [])
        
        timeline = []
        for bucket in timeline_buckets:
            timeline.append({
                'timestamp': bucket['key'],
                'event_count': bucket['doc_count'],
                'key_as_string': bucket.get('key_as_string', '')
            })
        
        return timeline
    
    def _calculate_compliance_score(self, events: List[Dict]) -> float:
        """Calculate compliance score based on audit events"""
        if not events:
            return 0.0
        
        # Count compliance-relevant events
        compliance_events = [e for e in events if e.get('compliance_flag', False)]
        total_events = len(events)
        compliance_events_count = len(compliance_events)
        
        # Score based on completeness of audit trail
        if total_events == 0:
            return 0.0
        
        # Base score from compliance relevance
        compliance_rate = compliance_events_count / total_events
        
        # Bonus for successful events
        successful_events = [e for e in events if e.get('success', False)]
        success_rate = len(successful_events) / total_events if total_events > 0 else 0
        
        # Final score (0-100)
        score = (compliance_rate * 0.6 + success_rate * 0.4) * 100
        
        return round(score, 2)
    
    def _detect_audit_anomalies(self, events: List[Dict]) -> List[Dict]:
        """Detect anomalies in audit events"""
        anomalies = []
        
        # Detect rapid consecutive failures
        failure_patterns = self._detect_failure_patterns(events)
        anomalies.extend(failure_patterns)
        
        # Detect unusual time patterns
        time_anomalies = self._detect_time_anomalies(events)
        anomalies.extend(time_anomalies)
        
        # Detect privilege escalation attempts
        privilege_anomalies = self._detect_privilege_anomalies(events)
        anomalies.extend(privilege_anomalies)
        
        return anomalies
    
    def _detect_failure_patterns(self, events: List[Dict]) -> List[Dict]:
        """Detect patterns of repeated failures"""
        anomalies = []
        
        # Group events by user and short time windows
        user_failures = {}
        for event in events:
            if not event.get('success', True):  # Failed event
                user_id = event.get('user_id', 'unknown')
                timestamp = event.get('timestamp')
                
                if user_id not in user_failures:
                    user_failures[user_id] = []
                user_failures[user_id].append(event)
        
        # Check for failure patterns
        for user_id, user_events in user_failures.items():
            if len(user_events) >= 5:  # 5+ failures
                # Check if failures are within a short time window
                timestamps = [datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) if isinstance(e['timestamp'], str) else e['timestamp'] for e in user_events]
                timestamps.sort()
                
                time_span = timestamps[-1] - timestamps[0]
                if time_span.total_seconds() < 3600:  # Within 1 hour
                    anomalies.append({
                        'type': 'repeated_failures',
                        'user_id': user_id,
                        'count': len(user_events),
                        'time_span': str(time_span),
                        'severity': 'high',
                        'description': f"User {user_id} had {len(user_events)} failures within {time_span}"
                    })
        
        return anomalies
    
    def _detect_time_anomalies(self, events: List[Dict]) -> List[Dict]:
        """Detect events at unusual times"""
        anomalies = []
        
        for event in events:
            timestamp = event.get('timestamp')
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if isinstance(timestamp, str) else timestamp
                hour = dt.hour
                
                # Flag events outside business hours (9 AM - 6 PM)
                if hour < 9 or hour > 18:
                    if event.get('event_type') in ['privilege_escalation', 'configuration_change']:
                        anomalies.append({
                            'type': 'off_hours_critical',
                            'event_type': event.get('event_type'),
                            'user_id': event.get('user_id'),
                            'timestamp': timestamp,
                            'hour': hour,
                            'severity': 'medium',
                            'description': f"Critical event occurred at {hour}:00 (outside business hours)"
                        })
        
        return anomalies
    
    def _detect_privilege_anomalies(self, events: List[Dict]) -> List[Dict]:
        """Detect suspicious privilege escalation patterns"""
        anomalies = []
        
        privilege_events = [e for e in events if e.get('event_type') == 'privilege_escalation']
        
        for event in privilege_events:
            if not event.get('success', True):  # Failed privilege escalation
                anomalies.append({
                    'type': 'failed_privilege_escalation',
                    'user_id': event.get('user_id'),
                    'resource': event.get('resource'),
                    'timestamp': event.get('timestamp'),
                    'severity': 'high',
                    'description': "Failed privilege escalation attempt detected"
                })
        
        return anomalies
    
    def search_by_pattern(self, pattern_name: str, time_window: timedelta = None) -> Dict[str, Any]:
        """
        Search using predefined audit patterns
        
        Args:
            pattern_name: Name of audit pattern to search
            time_window: Time window to analyze
            
        Returns:
            Pattern analysis results
        """
        pattern = self.audit_patterns.get(pattern_name)
        if not pattern:
            raise ValueError(f"Audit pattern not found: {pattern_name}")
        
        # Get end time (now) and start time
        end_time = datetime.utcnow()
        start_time = end_time - (time_window or timedelta(days=1))
        
        # Build search criteria based on pattern
        criteria = AuditSearchCriteria(
            event_types=pattern['conditions'].get('event_types', []),
            success_only=pattern['conditions'].get('success_only'),
            date_range=(start_time, end_time),
            search_pattern=pattern['conditions'].get('search_pattern'),
            result_limit=1000
        )
        
        # Execute search
        results = self.search_audit_logs(criteria)
        
        # Apply pattern-specific analysis
        analysis = self._apply_pattern_analysis(pattern, results['events'])
        
        results['pattern_analysis'] = analysis
        
        return results
    
    def _apply_pattern_analysis(self, pattern: Dict, events: List[Dict]) -> Dict:
        """Apply pattern-specific analysis to results"""
        analysis = {
            'pattern_name': pattern['description'],
            'matches_found': len(events),
            'risk_assessment': 'low',
            'recommendations': []
        }
        
        # Apply different analysis based on pattern
        if pattern['analysis'] == 'high_risk_login_attempts':
            analysis.update(self._analyze_login_failures(events))
        elif pattern['analysis'] == 'unauthorized_privilege_changes':
            analysis.update(self._analyze_privilege_changes(events))
        elif pattern['analysis'] == 'unusual_data_access_patterns':
            analysis.update(self._analyze_data_access_patterns(events))
        elif pattern['analysis'] == 'critical_config_changes':
            analysis.update(self._analyze_config_changes(events))
        
        return analysis
    
    def _analyze_login_failures(self, events: List[Dict]) -> Dict:
        """Analyze login failure patterns"""
        failed_logins = [e for e in events if not e.get('success', True)]
        
        user_failure_counts = {}
        for event in failed_logins:
            user_id = event.get('user_id', 'unknown')
            user_failure_counts[user_id] = user_failure_counts.get(user_id, 0) + 1
        
        high_risk_users = [user for user, count in user_failure_counts.items() if count >= 5]
        
        return {
            'failed_attempts': len(failed_logins),
            'unique_users': len(user_failure_counts),
            'high_risk_users': high_risk_users,
            'recommendation': 'Review high-risk users and consider account lockout policies' if high_risk_users else 'No immediate concerns detected'
        }
    
    def _analyze_privilege_changes(self, events: List[Dict]) -> Dict:
        """Analyze privilege escalation patterns"""
        failed_escalations = [e for e in events if not e.get('success', True)]
        
        return {
            'failed_escalations': len(failed_escalations),
            'severity': 'high' if failed_escalations else 'low',
            'recommendation': 'Investigate failed privilege escalations immediately' if failed_escalations else 'No failed privilege escalations detected'
        }
    
    def _analyze_data_access_patterns(self, events: List[Dict]) -> Dict:
        """Analyze data access patterns"""
        data_access_events = [e for e in events if e.get('event_type') in ['data_access', 'export']]
        
        user_data_volume = {}
        for event in data_access_events:
            user_id = event.get('user_id', 'unknown')
            details = event.get('details', {})
            volume = details.get('data_volume', 0)
            user_data_volume[user_id] = user_data_volume.get(user_id, 0) + volume
        
        high_volume_users = [user for user, volume in user_data_volume.items() if volume > 1000000]
        
        return {
            'data_access_events': len(data_access_events),
            'high_volume_users': high_volume_users,
            'recommendation': 'Review data access patterns for high-volume users' if high_volume_users else 'Normal data access patterns detected'
        }
    
    def _analyze_config_changes(self, events: List[Dict]) -> Dict:
        """Analyze configuration change patterns"""
        config_changes = events
        
        return {
            'config_changes': len(config_changes),
            'severity': 'high' if config_changes else 'low',
            'recommendation': 'Review all configuration changes for security impact' if config_changes else 'No recent configuration changes detected'
        }
    
    def compliance_audit_search(self, regulation: str, time_period: str) -> Dict[str, Any]:
        """
        Search audit logs for compliance-specific events
        
        Args:
            regulation: Compliance regulation (GDPR, SOX, PCI_DSS)
            time_period: Time period to analyze (e.g., '7d', '30d', '90d')
            
        Returns:
            Compliance audit results
        """
        compliance_mapping = self.compliance_mappings.get(regulation)
        if not compliance_mapping:
            raise ValueError(f"Compliance regulation not supported: {regulation}")
        
        # Parse time period
        time_value = int(time_period[:-1])
        time_unit = time_period[-1]
        
        if time_unit == 'd':
            time_delta = timedelta(days=time_value)
        elif time_unit == 'h':
            time_delta = timedelta(hours=time_value)
        elif time_unit == 'w':
            time_delta = timedelta(weeks=time_value)
        else:
            raise ValueError(f"Invalid time period format: {time_period}")
        
        # Get event types for regulation
        relevant_event_types = []
        for event_category, event_types in compliance_mapping.items():
            if event_category.endswith('_events'):
                relevant_event_types.extend(event_types)
        
        # Build search criteria
        criteria = AuditSearchCriteria(
            event_types=relevant_event_types,
            date_range=(datetime.utcnow() - time_delta, datetime.utcnow()),
            compliance_relevant=True,
            result_limit=5000
        )
        
        # Execute search
        results = self.search_audit_logs(criteria)
        
        # Compliance-specific analysis
        compliance_analysis = {
            'regulation': regulation,
            'time_period': time_period,
            'required_fields': compliance_mapping['required_fields'],
            'field_completeness': self._assess_field_completeness(results['events'], compliance_mapping['required_fields']),
            'compliance_score': self._calculate_compliance_score(results['events']),
            'gaps': self._identify_compliance_gaps(results['events'], compliance_mapping),
            'recommendations': self._generate_compliance_recommendations(regulation, results['events'])
        }
        
        results['compliance_analysis'] = compliance_analysis
        
        return results
    
    def _assess_field_completeness(self, events: List[Dict], required_fields: List[str]) -> Dict:
        """Assess completeness of required fields"""
        completeness = {}
        
        for field in required_fields:
            complete_count = 0
            for event in events:
                if event.get(field) is not None:
                    complete_count += 1
            
            completeness[field] = {
                'complete': complete_count,
                'total': len(events),
                'percentage': (complete_count / len(events)) * 100 if events else 0
            }
        
        return completeness
    
    def _identify_compliance_gaps(self, events: List[Dict], compliance_mapping: Dict) -> List[Dict]:
        """Identify compliance gaps in audit trail"""
        gaps = []
        
        # Check for missing event types
        required_event_types = []
        for event_category, event_types in compliance_mapping.items():
            if event_category.endswith('_events'):
                required_event_types.extend(event_types)
        
        found_events = set(event.get('event_type') for event in events)
        missing_events = set(required_event_types) - found_events
        
        if missing_events:
            gaps.append({
                'type': 'missing_events',
                'missing_event_types': list(missing_events),
                'severity': 'medium',
                'description': f"Missing required event types: {', '.join(missing_events)}"
            })
        
        # Check for incomplete fields
        required_fields = compliance_mapping['required_fields']
        for field in required_fields:
            incomplete_events = [e for e in events if not e.get(field)]
            if incomplete_events:
                gaps.append({
                    'type': 'incomplete_fields',
                    'field': field,
                    'incomplete_count': len(incomplete_events),
                    'severity': 'high' if field in ['user_id', 'timestamp'] else 'medium',
                    'description': f"Field '{field}' is incomplete in {len(incomplete_events)} events"
                })
        
        return gaps
    
    def _generate_compliance_recommendations(self, regulation: str, events: List[Dict]) -> List[str]:
        """Generate compliance recommendations based on analysis"""
        recommendations = []
        
        if regulation == 'GDPR':
            recommendations.extend([
                "Ensure all data access events have proper consent records",
                "Implement automated data deletion for expired retention periods",
                "Add detailed purpose tracking for data processing activities"
            ])
        elif regulation == 'SOX':
            recommendations.extend([
                "Implement approval workflows for financial system changes",
                "Ensure all access events have proper authorization records",
                "Add change management tracking for system configurations"
            ])
        elif regulation == 'PCI_DSS':
            recommendations.extend([
                "Implement strong authentication for all cardholder data access",
                "Add network monitoring for cardholder data environment",
                "Ensure proper logging of all security-relevant events"
            ])
        
        # Add general recommendations based on gaps
        compliance_score = self._calculate_compliance_score(events)
        if compliance_score < 80:
            recommendations.append("Improve audit trail completeness and accuracy")
        
        return recommendations
    
    def get_audit_timeline(self, 
                         user_id: str = None,
                         resource: str = None,
                         time_range: timedelta = None) -> List[AuditTimeline]:
        """
        Generate audit timeline for analysis
        
        Args:
            user_id: Specific user to track
            resource: Specific resource to track
            time_range: Time range for timeline
            
        Returns:
            Chronological audit timeline
        """
        end_time = datetime.utcnow()
        start_time = end_time - (time_range or timedelta(days=7))
        
        criteria = AuditSearchCriteria(
            date_range=(start_time, end_time),
            result_limit=10000
        )
        
        if user_id:
            criteria.user_ids = [user_id]
        
        if resource:
            criteria.resource_types = [resource]
        
        # Search audit logs
        results = self.search_audit_logs(criteria)
        
        # Build timeline
        timeline = []
        for event in results['events']:
            timeline_entry = AuditTimeline(
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) if isinstance(event['timestamp'], str) else event['timestamp'],
                event_type=event['event_type'],
                user_id=event['user_id'],
                resource=event['resource'],
                success=event['success'],
                details=event['details'],
                risk_score=self._calculate_risk_score(event),
                compliance_flag=event['compliance_flag']
            )
            timeline.append(timeline_entry)
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.timestamp)
        
        return timeline
    
    def _calculate_risk_score(self, event: Dict) -> float:
        """Calculate risk score for an audit event"""
        base_score = 0.0
        
        # Base score by event type
        event_scores = {
            'login_failure': 0.3,
            'privilege_escalation': 0.8,
            'data_deletion': 0.7,
            'configuration_change': 0.6,
            'system_shutdown': 0.4
        }
        
        event_type = event.get('event_type', '')
        base_score = event_scores.get(event_type, 0.1)
        
        # Adjust for success/failure
        if not event.get('success', True):
            base_score *= 1.5
        
        # Adjust for risk level
        risk_level = event.get('risk_level', 'low')
        risk_multipliers = {
            'low': 1.0,
            'medium': 1.3,
            'high': 1.6,
            'critical': 2.0
        }
        base_score *= risk_multipliers.get(risk_level, 1.0)
        
        # Cap at 1.0
        return min(base_score, 1.0)
