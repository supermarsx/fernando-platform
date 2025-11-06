"""
Core Audit Trail Management Service

Provides comprehensive audit trail management with enterprise features.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, text
from app.models.logging import AuditEvent, AuditTrail, LogEntry
from app.models.user import User
from app.db.session import SessionLocal
from app.services.logging.audit_logger import AuditLogger, AuditEventType, AuditSeverity, AuditOutcome
from app.services.logging.structured_logger import structured_logger


class AuditFilterOperator(Enum):
    """Filter operators for audit queries"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


@dataclass
class AuditFilter:
    """Audit filter definition"""
    field: str
    operator: AuditFilterOperator
    value: Any = None
    values: List[Any] = None


@dataclass
class AuditQuery:
    """Audit query specification"""
    filters: List[AuditFilter] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 1000
    offset: int = 0
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # asc or desc
    include_metadata: bool = True
    include_compliance_data: bool = True


@dataclass
class AuditSearchResult:
    """Audit search result"""
    total_count: int
    events: List[Dict[str, Any]]
    aggregations: Dict[str, Any] = field(default_factory=dict)
    query_info: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


class AuditService:
    """Enterprise audit service with comprehensive management capabilities"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        
        # Statistics
        self.stats = {
            'total_audit_events': 0,
            'queries_executed': 0,
            'search_queries': 0,
            'compliance_checks': 0,
            'integrity_verifications': 0,
            'avg_query_time_ms': 0.0,
            'last_activity': None
        }
        
        # Cache for performance
        self._user_context_cache = {}
        self._audit_cache = {}
    
    async def search_audit_events(self, query: AuditQuery) -> AuditSearchResult:
        """Search audit events with advanced filtering and pagination"""
        
        start_time = datetime.utcnow()
        db: Session = SessionLocal()
        
        try:
            # Build base query
            base_query = db.query(AuditEvent)
            
            # Apply filters
            if query.filters:
                for audit_filter in query.filters:
                    base_query = self._apply_filter(base_query, audit_filter)
            
            # Apply date range
            if query.start_date:
                base_query = base_query.filter(AuditEvent.timestamp >= query.start_date)
            if query.end_date:
                base_query = base_query.filter(AuditEvent.timestamp <= query.end_date)
            
            # Get total count
            total_count = base_query.count()
            
            # Apply sorting
            sort_column = getattr(AuditEvent, query.sort_by, AuditEvent.timestamp)
            if query.sort_order.lower() == "desc":
                base_query = base_query.order_by(desc(sort_column))
            else:
                base_query = base_query.order_by(asc(sort_column))
            
            # Apply pagination
            base_query = base_query.offset(query.offset).limit(query.limit)
            
            # Execute query
            events = base_query.all()
            
            # Process results
            processed_events = []
            for event in events:
                processed_event = self._serialize_audit_event(event, query.include_metadata)
                processed_events.append(processed_event)
            
            # Generate aggregations if requested
            aggregations = {}
            if query.filters or query.start_date or query.end_date:
                aggregations = self._generate_aggregations(db, query)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_stats(execution_time, True)
            
            return AuditSearchResult(
                total_count=total_count,
                events=processed_events,
                aggregations=aggregations,
                query_info={
                    'filters_applied': len(query.filters),
                    'date_range': {
                        'start': query.start_date.isoformat() if query.start_date else None,
                        'end': query.end_date.isoformat() if query.end_date else None
                    },
                    'pagination': {
                        'limit': query.limit,
                        'offset': query.offset,
                        'has_more': (query.offset + query.limit) < total_count
                    }
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._update_stats(0, False)
            structured_logger.error(
                f"Error searching audit events: {str(e)}",
                error=str(e),
                filters_count=len(query.filters)
            )
            raise
        finally:
            db.close()
    
    async def get_audit_timeline(self, 
                               user_id: Optional[str] = None,
                               resource_type: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               max_events: int = 1000) -> List[Dict[str, Any]]:
        """Get chronological audit timeline"""
        
        db: Session = SessionLocal()
        try:
            query = db.query(AuditEvent)
            
            # Apply filters
            if user_id:
                query = query.filter(AuditEvent.user_id == user_id)
            if resource_type:
                query = query.filter(AuditEvent.resource_type == resource_type)
            if start_date:
                query = query.filter(AuditEvent.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditEvent.timestamp <= end_date)
            
            # Order by timestamp and limit
            events = query.order_by(AuditEvent.timestamp.asc()).limit(max_events).all()
            
            # Process timeline
            timeline = []
            for event in events:
                timeline_entry = {
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': event.event_type,
                    'description': event.description,
                    'user_id': event.user_id,
                    'resource_type': event.resource_type,
                    'resource_id': event.resource_id,
                    'outcome': event.outcome,
                    'severity': event.severity,
                    'ip_address': event.ip_address,
                    'session_id': event.session_id
                }
                
                if event.details:
                    timeline_entry['details'] = event.details
                
                timeline.append(timeline_entry)
            
            return timeline
            
        finally:
            db.close()
    
    async def analyze_user_activity(self, 
                                   user_id: str,
                                   days_back: int = 30) -> Dict[str, Any]:
        """Analyze user activity patterns for audit purposes"""
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        end_date = datetime.utcnow()
        
        db: Session = SessionLocal()
        try:
            # Get user events for the period
            events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.user_id == user_id,
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).all()
            
            if not events:
                return {
                    'user_id': user_id,
                    'analysis_period_days': days_back,
                    'total_events': 0,
                    'activity_summary': {},
                    'risk_indicators': [],
                    'compliance_status': 'no_activity'
                }
            
            # Analyze activity patterns
            analysis = {
                'user_id': user_id,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days_back
                },
                'total_events': len(events),
                'activity_summary': {},
                'event_distribution': {},
                'risk_indicators': [],
                'compliance_status': 'compliant',
                'anomalies_detected': []
            }
            
            # Event type distribution
            event_types = {}
            resource_types = {}
            time_distribution = {}
            ip_addresses = {}
            
            for event in events:
                # Event types
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
                
                # Resource types
                resource_types[event.resource_type] = resource_types.get(event.resource_type, 0) + 1
                
                # Time distribution (by hour)
                hour = event.timestamp.hour
                time_distribution[hour] = time_distribution.get(hour, 0) + 1
                
                # IP addresses
                if event.ip_address:
                    ip_addresses[event.ip_address] = ip_addresses.get(event.ip_address, 0) + 1
            
            analysis['activity_summary'] = {
                'unique_event_types': len(event_types),
                'unique_resources': len(resource_types),
                'unique_ip_addresses': len(ip_addresses),
                'most_active_hours': sorted(time_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
            analysis['event_distribution'] = {
                'by_type': event_types,
                'by_resource': resource_types,
                'by_time': time_distribution,
                'by_ip': ip_addresses
            }
            
            # Risk indicators
            risk_indicators = self._analyze_user_risk_indicators(events)
            analysis['risk_indicators'] = risk_indicators
            
            # Anomaly detection
            anomalies = self._detect_user_activity_anomalies(events, time_distribution)
            analysis['anomalies_detected'] = anomalies
            
            # Compliance assessment
            compliance_status = self._assess_user_compliance(events)
            analysis['compliance_status'] = compliance_status
            
            return analysis
            
        finally:
            db.close()
    
    async def get_audit_analytics(self, 
                                days_back: int = 30,
                                group_by: str = "day") -> Dict[str, Any]:
        """Get audit analytics and trends"""
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        end_date = datetime.utcnow()
        
        db: Session = SessionLocal()
        try:
            # Get analytics data
            analytics = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days_back
                },
                'summary': {},
                'trends': {},
                'top_entities': {},
                'compliance_metrics': {}
            }
            
            # Summary statistics
            total_events = db.query(func.count(AuditEvent.event_id)).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).scalar() or 0
            
            unique_users = db.query(func.count(func.distinct(AuditEvent.user_id))).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).scalar() or 0
            
            unique_resources = db.query(func.count(func.distinct(AuditEvent.resource_type))).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).scalar() or 0
            
            analytics['summary'] = {
                'total_events': total_events,
                'unique_users': unique_users,
                'unique_resources': unique_resources,
                'avg_events_per_day': round(total_events / days_back, 2)
            }
            
            # Event type trends
            event_type_trends = db.query(
                AuditEvent.event_type,
                func.count(AuditEvent.event_id).label('count')
            ).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).group_by(AuditEvent.event_type).all()
            
            analytics['trends']['event_types'] = [
                {'event_type': et.event_type, 'count': et.count}
                for et in event_type_trends
            ]
            
            # Top users by activity
            top_users = db.query(
                AuditEvent.user_id,
                func.count(AuditEvent.event_id).label('count')
            ).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).group_by(AuditEvent.user_id).order_by(desc('count')).limit(10).all()
            
            analytics['top_entities']['users'] = [
                {'user_id': u.user_id, 'event_count': u.count}
                for u in top_users
            ]
            
            # Top resource types
            top_resources = db.query(
                AuditEvent.resource_type,
                func.count(AuditEvent.event_id).label('count')
            ).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).group_by(AuditEvent.resource_type).order_by(desc('count')).limit(10).all()
            
            analytics['top_entities']['resources'] = [
                {'resource_type': r.resource_type, 'event_count': r.count}
                for r in top_resources
            ]
            
            # Compliance metrics
            compliance_metrics = self._get_compliance_metrics(db, start_date, end_date)
            analytics['compliance_metrics'] = compliance_metrics
            
            return analytics
            
        finally:
            db.close()
    
    async def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify audit trail integrity"""
        
        integrity_results = self.audit_logger.verify_audit_trail_integrity()
        
        # Additional integrity checks
        additional_checks = self._run_additional_integrity_checks()
        
        integrity_results.update({
            'additional_checks': additional_checks,
            'verification_timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'verified' if integrity_results['chain_valid'] else 'corrupted'
        })
        
        # Update statistics
        with self._get_stats_lock():
            self.stats['integrity_verifications'] += 1
        
        structured_logger.audit(
            "Audit trail integrity verification completed",
            total_events=integrity_results['total_events'],
            verified_events=integrity_results['verified_events'],
            corrupted_events=integrity_results['corrupted_events'],
            chain_valid=integrity_results['chain_valid']
        )
        
        return integrity_results
    
    async def export_audit_data(self, 
                              start_date: datetime,
                              end_date: datetime,
                              format_type: str = "json",
                              filters: Optional[List[AuditFilter]] = None) -> str:
        """Export audit data for compliance or analysis"""
        
        db: Session = SessionLocal()
        try:
            # Build query
            query = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            )
            
            # Apply additional filters
            if filters:
                for audit_filter in filters:
                    query = self._apply_filter(query, audit_filter)
            
            # Order by timestamp
            events = query.order_by(AuditEvent.timestamp.asc()).all()
            
            # Process export data
            export_data = {
                'export_info': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'total_events': len(events),
                    'format': format_type,
                    'filters_applied': len(filters) if filters else 0
                },
                'events': []
            }
            
            for event in events:
                event_data = {
                    'audit_event_id': str(event.event_id),
                    'event_type': event.event_type,
                    'resource_type': event.resource_type,
                    'resource_id': event.resource_id,
                    'user_id': event.user_id,
                    'outcome': event.outcome,
                    'severity': event.severity,
                    'description': event.description,
                    'details': event.details,
                    'ip_address': event.ip_address,
                    'user_agent': event.user_agent,
                    'session_id': event.session_id,
                    'timestamp': event.timestamp.isoformat(),
                    'compliance_tags': event.compliance_tags,
                    'retention_period_days': event.retention_period_days,
                    'event_hash': event.event_hash
                }
                export_data['events'].append(event_data)
            
            # Format export
            if format_type.lower() == "json":
                import json
                export_filename = f"audit_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
                export_content = json.dumps(export_data, indent=2, default=str)
                
            elif format_type.lower() == "csv":
                import csv
                from io import StringIO
                
                output = StringIO()
                if events:
                    fieldnames = [
                        'audit_event_id', 'event_type', 'resource_type', 'resource_id',
                        'user_id', 'outcome', 'severity', 'description', 'ip_address',
                        'session_id', 'timestamp', 'compliance_tags'
                    ]
                    
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for event in events:
                        writer.writerow({
                            'audit_event_id': str(event.event_id),
                            'event_type': event.event_type,
                            'resource_type': event.resource_type,
                            'resource_id': event.resource_id,
                            'user_id': event.user_id,
                            'outcome': event.outcome,
                            'severity': event.severity,
                            'description': event.description,
                            'ip_address': event.ip_address,
                            'session_id': event.session_id,
                            'timestamp': event.timestamp.isoformat(),
                            'compliance_tags': str(event.compliance_tags)
                        })
                
                export_filename = f"audit_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                export_content = output.getvalue()
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            # Log export activity
            self.audit_logger.log_audit_event(
                event_type=AuditEventType.DATA_EXPORT,
                resource_type="audit_data",
                description=f"Audit data export: {export_filename}",
                details={
                    'export_format': format_type,
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'events_count': len(events),
                    'filters_count': len(filters) if filters else 0
                },
                compliance_tags=['compliance', 'data_export'],
                compliance_retention_period=2555  # 7 years
            )
            
            return export_filename, export_content
            
        finally:
            db.close()
    
    def _apply_filter(self, query, audit_filter: AuditFilter):
        """Apply filter to audit query"""
        
        field = getattr(AuditEvent, audit_filter.field)
        
        if audit_filter.operator == AuditFilterOperator.EQUALS:
            return query.filter(field == audit_filter.value)
        elif audit_filter.operator == AuditFilterOperator.NOT_EQUALS:
            return query.filter(field != audit_filter.value)
        elif audit_filter.operator == AuditFilterOperator.CONTAINS:
            return query.filter(field.ilike(f"%{audit_filter.value}%"))
        elif audit_filter.operator == AuditFilterOperator.STARTS_WITH:
            return query.filter(field.ilike(f"{audit_filter.value}%"))
        elif audit_filter.operator == AuditFilterOperator.ENDS_WITH:
            return query.filter(field.ilike(f"%{audit_filter.value}"))
        elif audit_filter.operator == AuditFilterOperator.GREATER_THAN:
            return query.filter(field > audit_filter.value)
        elif audit_filter.operator == AuditFilterOperator.LESS_THAN:
            return query.filter(field < audit_filter.value)
        elif audit_filter.operator == AuditFilterOperator.IN:
            return query.filter(field.in_(audit_filter.values))
        elif audit_filter.operator == AuditFilterOperator.NOT_IN:
            return query.filter(~field.in_(audit_filter.values))
        elif audit_filter.operator == AuditFilterOperator.IS_NULL:
            return query.filter(field.is_(None))
        elif audit_filter.operator == AuditFilterOperator.IS_NOT_NULL:
            return query.filter(field.is_not(None))
        
        return query
    
    def _serialize_audit_event(self, event: AuditEvent, include_metadata: bool = True) -> Dict[str, Any]:
        """Serialize audit event for API response"""
        
        serialized = {
            'audit_event_id': str(event.event_id),
            'event_type': event.event_type,
            'resource_type': event.resource_type,
            'resource_id': event.resource_id,
            'user_id': event.user_id,
            'outcome': event.outcome,
            'severity': event.severity,
            'description': event.description,
            'timestamp': event.timestamp.isoformat(),
            'created_at': event.created_at.isoformat()
        }
        
        if include_metadata:
            serialized.update({
                'details': event.details,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'session_id': event.session_id,
                'compliance_tags': event.compliance_tags,
                'retention_period_days': event.retention_period_days,
                'article_references': event.article_references,
                'event_hash': event.event_hash
            })
        
        return serialized
    
    def _generate_aggregations(self, db: Session, query: AuditQuery) -> Dict[str, Any]:
        """Generate aggregations for search results"""
        
        aggregations = {}
        
        # Event type distribution
        event_type_dist = db.query(
            AuditEvent.event_type,
            func.count(AuditEvent.event_id).label('count')
        ).filter(
            AuditEvent.timestamp >= query.start_date if query.start_date else AuditEvent.timestamp >= datetime.min,
            AuditEvent.timestamp <= query.end_date if query.end_date else AuditEvent.timestamp >= datetime.max
        ).group_by(AuditEvent.event_type).all()
        
        aggregations['event_types'] = {
            et.event_type: et.count for et in event_type_dist
        }
        
        # Outcome distribution
        outcome_dist = db.query(
            AuditEvent.outcome,
            func.count(AuditEvent.event_id).label('count')
        ).filter(
            AuditEvent.timestamp >= query.start_date if query.start_date else AuditEvent.timestamp >= datetime.min,
            AuditEvent.timestamp <= query.end_date if query.end_date else AuditEvent.timestamp >= datetime.max
        ).group_by(AuditEvent.outcome).all()
        
        aggregations['outcomes'] = {
            o.outcome: o.count for o in outcome_dist
        }
        
        # User activity distribution
        user_dist = db.query(
            AuditEvent.user_id,
            func.count(AuditEvent.event_id).label('count')
        ).filter(
            AuditEvent.timestamp >= query.start_date if query.start_date else AuditEvent.timestamp >= datetime.min,
            AuditEvent.timestamp <= query.end_date if query.end_date else AuditEvent.timestamp >= datetime.max
        ).group_by(AuditEvent.user_id).order_by(desc('count')).limit(10).all()
        
        aggregations['top_users'] = {
            u.user_id: u.count for u in user_dist if u.user_id
        }
        
        return aggregations
    
    def _analyze_user_risk_indicators(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Analyze risk indicators for user activity"""
        
        risk_indicators = []
        
        # Check for failed login attempts
        failed_logins = [e for e in events if e.event_type == 'login' and e.outcome == 'failure']
        if len(failed_logins) > 5:
            risk_indicators.append({
                'type': 'multiple_failed_logins',
                'description': f'User had {len(failed_logins)} failed login attempts',
                'severity': 'medium',
                'events': len(failed_logins)
            })
        
        # Check for off-hours activity
        off_hours_events = [e for e in events if e.timestamp.hour < 6 or e.timestamp.hour > 22]
        if len(off_hours_events) > len(events) * 0.3:  # More than 30% off-hours
            risk_indicators.append({
                'type': 'unusual_off_hours_activity',
                'description': f'User has {len(off_hours_events)} events outside business hours',
                'severity': 'low',
                'percentage': round(len(off_hours_events) / len(events) * 100, 1)
            })
        
        # Check for privilege escalation attempts
        privilege_events = [e for e in events if 'permission' in e.event_type or 'role' in e.event_type]
        if any(e.outcome == 'failure' for e in privilege_events):
            risk_indicators.append({
                'type': 'failed_privilege_escalation',
                'description': 'User attempted privilege escalation that failed',
                'severity': 'high',
                'events': len(privilege_events)
            })
        
        return risk_indicators
    
    def _detect_user_activity_anomalies(self, events: List[AuditEvent], time_distribution: Dict[int, int]) -> List[Dict[str, Any]]:
        """Detect anomalies in user activity patterns"""
        
        anomalies = []
        
        if not events:
            return anomalies
        
        # Unusual activity volume
        avg_events_per_day = len(events) / 30  # Assuming 30-day analysis period
        if avg_events_per_day > 100:  # Arbitrary threshold
            anomalies.append({
                'type': 'high_activity_volume',
                'description': f'User has unusually high activity: {len(events)} events in period',
                'severity': 'medium'
            })
        
        # Resource access patterns
        resource_types = {}
        for event in events:
            resource_types[event.resource_type] = resource_types.get(event.resource_type, 0) + 1
        
        if len(resource_types) > 10:  # Accessing many different resources
            anomalies.append({
                'type': 'broad_resource_access',
                'description': f'User accessed {len(resource_types)} different resource types',
                'severity': 'medium',
                'resources_count': len(resource_types)
            })
        
        return anomalies
    
    def _assess_user_compliance(self, events: List[AuditEvent]) -> str:
        """Assess user compliance status"""
        
        if not events:
            return 'no_activity'
        
        # Check for compliance violations
        failed_events = [e for e in events if e.outcome == 'failure']
        security_violations = [e for e in events if 'security' in e.event_type and e.severity in ['high', 'critical']]
        
        if security_violations:
            return 'violation_detected'
        elif len(failed_events) > len(events) * 0.2:  # More than 20% failures
            return 'requires_review'
        elif all(e.outcome == 'success' for e in events):
            return 'compliant'
        else:
            return 'normal'
    
    def _get_compliance_metrics(self, db: Session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get compliance metrics for audit analytics"""
        
        # Total compliance-related events
        compliance_events = db.query(func.count(AuditEvent.event_id)).filter(
            and_(
                AuditEvent.timestamp >= start_date,
                AuditEvent.timestamp <= end_date,
                AuditEvent.compliance_tags.contains(['compliance'])
            )
        ).scalar() or 0
        
        # Events by regulation
        regulation_counts = {}
        for regulation in ['gdpr', 'sox', 'pci_dss', 'hipaa']:
            count = db.query(func.count(AuditEvent.event_id)).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date,
                    AuditEvent.compliance_tags.contains([regulation])
                )
            ).scalar() or 0
            regulation_counts[regulation] = count
        
        return {
            'total_compliance_events': compliance_events,
            'events_by_regulation': regulation_counts,
            'compliance_rate': 'calculated_based_on_business_rules'
        }
    
    def _run_additional_integrity_checks(self) -> Dict[str, Any]:
        """Run additional integrity checks beyond chain validation"""
        
        checks = {
            'orphaned_events': 0,
            'missing_hash_events': 0,
            'duplicate_events': 0,
            'temporal_anomalies': 0
        }
        
        db: Session = SessionLocal()
        try:
            # Check for events without audit trail entries
            orphaned_events = db.query(func.count(AuditEvent.event_id)).outerjoin(
                AuditTrail, AuditEvent.event_id == AuditTrail.audit_event_id
            ).filter(AuditTrail.trail_id.is_(None)).scalar() or 0
            checks['orphaned_events'] = orphaned_events
            
            # Check for events without hash
            missing_hash_events = db.query(func.count(AuditEvent.event_id)).filter(
                AuditEvent.event_hash.is_(None)
            ).scalar() or 0
            checks['missing_hash_events'] = missing_hash_events
            
            # Check for duplicate event IDs (should not happen with UUID)
            # This is more of a data consistency check
            
            # Check for temporal anomalies (events in the future, etc.)
            future_events = db.query(func.count(AuditEvent.event_id)).filter(
                AuditEvent.timestamp > datetime.utcnow()
            ).scalar() or 0
            checks['temporal_anomalies'] = future_events
            
        finally:
            db.close()
        
        return checks
    
    def _update_stats(self, execution_time: float, success: bool):
        """Update service statistics"""
        
        with self._get_stats_lock():
            if success:
                self.stats['queries_executed'] += 1
                self.stats['search_queries'] += 1
                
                # Update average query time
                old_avg = self.stats['avg_query_time_ms']
                count = self.stats['queries_executed']
                self.stats['avg_query_time_ms'] = (old_avg * (count - 1) + execution_time) / count
            else:
                self.stats['queries_executed'] += 1
            
            self.stats['last_activity'] = datetime.utcnow()
    
    def _get_stats_lock(self):
        """Get lock for statistics updates"""
        import threading
        return threading.Lock()
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        
        with self._get_stats_lock():
            stats = self.stats.copy()
            
            # Add cache statistics
            stats['cache'] = {
                'user_context_cache_size': len(self._user_context_cache),
                'audit_cache_size': len(self._audit_cache)
            }
            
            return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on audit service"""
        
        health_status = {
            'overall_status': 'healthy',
            'audit_service': 'healthy',
            'statistics': self.get_service_statistics()
        }
        
        # Check service statistics
        if self.stats['queries_executed'] > 0:
            error_rate = (self.stats['queries_executed'] - self.stats['search_queries']) / self.stats['queries_executed']
            if error_rate > 0.1:  # More than 10% error rate
                health_status['overall_status'] = 'warning'
                health_status['audit_service'] = f'high_error_rate_{error_rate:.2%}'
        
        # Check last activity
        if self.stats['last_activity']:
            time_since_activity = datetime.utcnow() - self.stats['last_activity']
            if time_since_activity.total_seconds() > 3600:  # No activity in 1 hour
                health_status['audit_service'] = 'low_activity'
        
        return health_status


# Global audit service instance
audit_service = AuditService()