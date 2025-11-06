"""
Audit Trail Analysis and Reporting

Provides comprehensive analytics for audit trails with insights and trend analysis.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from app.models.logging import AuditEvent
from app.services.audit.audit_events import AuditEventTypes, EventSeverity, EventCategory, EventDefinition
from app.services.logging.structured_logger import structured_logger


class AnalysisPeriod(Enum):
    """Analysis periods for audit analytics"""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class InsightType(Enum):
    """Types of audit insights"""
    SECURITY_TREND = "security_trend"
    USER_BEHAVIOR = "user_behavior"
    COMPLIANCE_STATUS = "compliance_status"
    RISK_ANOMALY = "risk_anomaly"
    PERFORMANCE_ISSUE = "performance_issue"
    SYSTEM_CHANGE = "system_change"
    DATA_ACCESS_PATTERN = "data_access_pattern"
    THREAT_INDICATOR = "threat_indicator"


@dataclass
class TimeSeriesPoint:
    """Time series data point"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = None


@dataclass
class Insight:
    """Audit insight with recommendations"""
    insight_id: str
    type: InsightType
    title: str
    description: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    affected_entities: List[str]
    recommendations: List[str]
    evidence: Dict[str, Any]
    detected_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'insight_id': self.insight_id,
            'type': self.type.value,
            'title': self.title,
            'description': self.description,
            'severity': self.severity,
            'confidence': self.confidence,
            'affected_entities': self.affected_entities,
            'recommendations': self.recommendations,
            'evidence': self.evidence,
            'detected_at': self.detected_at.isoformat()
        }


class AuditAnalytics:
    """Advanced audit analytics and reporting service"""
    
    def __init__(self):
        self.insights_cache = {}
        self.analytics_cache = {}
        self.trend_cache = {}
        
        # Analysis thresholds
        self.thresholds = {
            'security_event_spike': 0.8,  # 80% increase from baseline
            'failed_login_threshold': 5,   # 5 failed logins in period
            'unusual_access_hours': [22, 23, 0, 1, 2, 3, 4, 5],  # Night hours
            'bulk_operation_threshold': 100,  # 100+ operations
            'high_risk_score': 80,          # Risk score >= 80
            'privilege_escalation_attempts': 3,  # 3 attempts
        }
    
    def analyze_security_trends(self,
                              start_date: datetime,
                              end_date: datetime,
                              period: AnalysisPeriod = AnalysisPeriod.LAST_MONTH) -> Dict[str, Any]:
        """Analyze security trends and patterns"""
        
        # Get security-related events
        security_events = self._get_security_events(start_date, end_date)
        
        if not security_events:
            return {
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'security_score': 0,
                'trends': {},
                'anomalies': [],
                'insights': []
            }
        
        # Calculate security metrics
        security_metrics = self._calculate_security_metrics(security_events)
        
        # Detect anomalies
        anomalies = self._detect_security_anomalies(security_events, start_date, end_date)
        
        # Generate insights
        insights = self._generate_security_insights(security_events, anomalies)
        
        # Calculate overall security score
        security_score = self._calculate_security_score(security_metrics, anomalies)
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'analysis_period': period.value
            },
            'security_score': security_score,
            'metrics': security_metrics,
            'trends': self._analyze_security_trends(security_events),
            'anomalies': [anomaly.to_dict() for anomaly in anomalies],
            'insights': [insight.to_dict() for insight in insights],
            'event_distribution': self._analyze_event_distribution(security_events),
            'geographic_analysis': self._analyze_geographic_patterns(security_events),
            'temporal_analysis': self._analyze_temporal_patterns(security_events)
        }
    
    def analyze_user_behavior(self,
                            user_id: str,
                            start_date: datetime,
                            end_date: datetime) -> Dict[str, Any]:
        """Analyze user behavior patterns and anomalies"""
        
        # Get user events
        user_events = self._get_user_events(user_id, start_date, end_date)
        
        if not user_events:
            return {
                'user_id': user_id,
                'analysis_period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'behavior_score': 0,
                'patterns': {},
                'anomalies': [],
                'recommendations': []
            }
        
        # Analyze behavior patterns
        patterns = self._analyze_user_behavior_patterns(user_events)
        
        # Detect anomalies
        anomalies = self._detect_user_behavior_anomalies(user_events)
        
        # Generate insights and recommendations
        insights = self._generate_user_insights(user_events, patterns, anomalies)
        
        # Calculate behavior score
        behavior_score = self._calculate_behavior_score(user_events, patterns, anomalies)
        
        return {
            'user_id': user_id,
            'analysis_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'behavior_score': behavior_score,
            'patterns': patterns,
            'anomalies': [anomaly.to_dict() for anomaly in anomalies],
            'insights': [insight.to_dict() for insight in insights],
            'risk_factors': self._identify_risk_factors(user_events),
            'activity_summary': self._summarize_user_activity(user_events),
            'recommendations': self._generate_user_recommendations(anomalies, patterns)
        }
    
    def analyze_compliance_status(self,
                                regulation: str,
                                start_date: datetime,
                                end_date: datetime) -> Dict[str, Any]:
        """Analyze compliance status for specific regulation"""
        
        # Get compliance events
        compliance_events = self._get_compliance_events(regulation, start_date, end_date)
        
        # Analyze compliance metrics
        compliance_metrics = self._analyze_compliance_metrics(compliance_events, regulation)
        
        # Check compliance requirements
        requirements_status = self._check_compliance_requirements(compliance_events, regulation)
        
        # Detect compliance violations
        violations = self._detect_compliance_violations(compliance_events, regulation)
        
        # Generate compliance insights
        insights = self._generate_compliance_insights(compliance_events, violations, regulation)
        
        return {
            'regulation': regulation,
            'analysis_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'compliance_score': self._calculate_compliance_score(compliance_metrics, violations),
            'metrics': compliance_metrics,
            'requirements_status': requirements_status,
            'violations': violations,
            'insights': [insight.to_dict() for insight in insights],
            'recommendations': self._generate_compliance_recommendations(violations, requirements_status),
            'audit_readiness': self._assess_audit_readiness(compliance_events, regulation)
        }
    
    def generate_comprehensive_report(self,
                                    start_date: datetime,
                                    end_date: datetime,
                                    report_type: str = "executive") -> Dict[str, Any]:
        """Generate comprehensive audit report"""
        
        if report_type == "executive":
            return self._generate_executive_report(start_date, end_date)
        elif report_type == "technical":
            return self._generate_technical_report(start_date, end_date)
        elif report_type == "compliance":
            return self._generate_compliance_report(start_date, end_date)
        elif report_type == "security":
            return self._generate_security_report(start_date, end_date)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time audit metrics"""
        
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        db: Session = SessionLocal()
        try:
            # Recent events
            recent_events = db.query(AuditEvent).filter(
                AuditEvent.timestamp >= last_hour
            ).count()
            
            # Security events in last hour
            security_events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= last_hour,
                    AuditEvent.severity.in_(['high', 'critical'])
                )
            ).count()
            
            # Failed login attempts in last hour
            failed_logins = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= last_hour,
                    AuditEvent.event_type == AuditEventTypes.LOGIN_FAILURE
                )
            ).count()
            
            # Unusual activity indicators
            unique_users_hour = db.query(func.count(func.distinct(AuditEvent.user_id))).filter(
                AuditEvent.timestamp >= last_hour
            ).scalar() or 0
            
            # High-risk events
            high_risk_events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= last_hour,
                    AuditEvent.severity == 'critical'
                )
            ).count()
            
            return {
                'timestamp': now.isoformat(),
                'metrics': {
                    'events_last_hour': recent_events,
                    'security_events_last_hour': security_events,
                    'failed_logins_last_hour': failed_logins,
                    'unique_users_last_hour': unique_users_hour,
                    'high_risk_events_last_hour': high_risk_events,
                    'security_alert_level': self._calculate_security_alert_level(
                        security_events, failed_logins, high_risk_events
                    )
                },
                'trends': {
                    'hour_over_hour_change': self._calculate_hour_over_hour_change(last_hour),
                    'daily_average': self._calculate_daily_average(last_day),
                    'baseline_comparison': self._compare_to_baseline(last_hour)
                }
            }
            
        finally:
            db.close()
    
    def predict_future_trends(self,
                            prediction_period_days: int = 30) -> Dict[str, Any]:
        """Predict future audit trends based on historical data"""
        
        # Get historical data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)  # Use last 90 days for prediction
        
        historical_events = self._get_all_events(start_date, end_date)
        
        if not historical_events:
            return {
                'prediction_period_days': prediction_period_days,
                'predictions': {},
                'confidence': 0.0,
                'methodology': 'insufficient_data'
            }
        
        # Analyze trends and patterns
        trends = self._analyze_historical_trends(historical_events)
        
        # Make predictions
        predictions = self._generate_predictions(trends, prediction_period_days)
        
        return {
            'prediction_period_days': prediction_period_days,
            'historical_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'predictions': predictions,
            'confidence': self._calculate_prediction_confidence(trends),
            'methodology': 'time_series_analysis_with_seasonality',
            'assumptions': [
                'Historical patterns continue',
                'No major system changes',
                'No significant external threats'
            ]
        }
    
    def _get_security_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get security-related events"""
        
        db: Session = SessionLocal()
        try:
            events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date,
                    or_(
                        AuditEvent.severity.in_(['high', 'critical']),
                        AuditEvent.event_type.like('security.%'),
                        AuditEvent.event_type.like('login.%'),
                        AuditEvent.event_type.like('access.%')
                    )
                )
            ).all()
            
            return [self._serialize_event(event) for event in events]
            
        finally:
            db.close()
    
    def _get_user_events(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get events for specific user"""
        
        db: Session = SessionLocal()
        try:
            events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.user_id == user_id,
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).order_by(AuditEvent.timestamp).all()
            
            return [self._serialize_event(event) for event in events]
            
        finally:
            db.close()
    
    def _get_compliance_events(self, regulation: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get compliance-related events"""
        
        db: Session = SessionLocal()
        try:
            events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date,
                    AuditEvent.compliance_tags.contains([regulation.lower()])
                )
            ).all()
            
            return [self._serialize_event(event) for event in events]
            
        finally:
            db.close()
    
    def _get_all_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get all events in time period"""
        
        db: Session = SessionLocal()
        try:
            events = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                )
            ).all()
            
            return [self._serialize_event(event) for event in events]
            
        finally:
            db.close()
    
    def _serialize_event(self, event: AuditEvent) -> Dict[str, Any]:
        """Serialize audit event for analysis"""
        return {
            'event_id': str(event.event_id),
            'event_type': event.event_type,
            'user_id': event.user_id,
            'resource_type': event.resource_type,
            'resource_id': event.resource_id,
            'severity': event.severity,
            'outcome': event.outcome,
            'timestamp': event.timestamp,
            'ip_address': event.ip_address,
            'session_id': event.session_id,
            'details': event.details
        }
    
    def _calculate_security_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate security metrics from events"""
        
        if not events:
            return {}
        
        # Count by severity
        severity_counts = Counter(event['severity'] for event in events)
        
        # Count by event type
        event_type_counts = Counter(event['event_type'] for event in events)
        
        # Count by outcome
        outcome_counts = Counter(event['outcome'] for event in events)
        
        # Analyze temporal patterns
        hourly_distribution = Counter(event['timestamp'].hour for event in events)
        
        # Geographic analysis
        ip_analysis = self._analyze_ip_patterns(events)
        
        return {
            'total_events': len(events),
            'severity_distribution': dict(severity_counts),
            'event_type_distribution': dict(event_type_counts),
            'outcome_distribution': dict(outcome_counts),
            'temporal_distribution': dict(hourly_distribution),
            'geographic_analysis': ip_analysis,
            'security_score_components': self._calculate_security_score_components(events)
        }
    
    def _analyze_ip_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze IP address patterns"""
        
        ip_events = defaultdict(list)
        for event in events:
            if event.get('ip_address'):
                ip_events[event['ip_address']].append(event)
        
        analysis = {
            'unique_ips': len(ip_events),
            'most_active_ips': [],
            'suspicious_ips': [],
            'geographic_distribution': {}
        }
        
        # Most active IPs
        ip_counts = {ip: len(events) for ip, events in ip_events.items()}
        analysis['most_active_ips'] = sorted(
            ip_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        
        # Suspicious IPs (high activity, many failed logins, etc.)
        for ip, events in ip_events.items():
            failed_logins = sum(1 for event in events if event['event_type'] == AuditEventTypes.LOGIN_FAILURE)
            if failed_logins > 3:
                analysis['suspicious_ips'].append({
                    'ip': ip,
                    'failed_logins': failed_logins,
                    'total_events': len(events)
                })
        
        return analysis
    
    def _calculate_security_score_components(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate individual components of security score"""
        
        if not events:
            return {}
        
        # Critical events penalty
        critical_events = sum(1 for event in events if event['severity'] == 'critical')
        
        # Failed attempts penalty
        failed_attempts = sum(1 for event in events if event['outcome'] == 'failure')
        
        # Security events bonus (more security events = better monitoring)
        security_events = sum(1 for event in events if event['event_type'].startswith('security.'))
        
        # Unauthorized access attempts
        unauthorized_attempts = sum(
            1 for event in events 
            if event['event_type'] in [AuditEventTypes.UNAUTHORIZED_ACCESS, AuditEventTypes.ACCESS_DENIED]
        )
        
        return {
            'critical_events_impact': -min(critical_events * 10, 50),  # Max -50 points
            'failed_attempts_impact': -min(failed_attempts * 2, 30),   # Max -30 points
            'security_monitoring_bonus': min(security_events * 2, 20),  # Max +20 points
            'unauthorized_access_impact': -min(unauthorized_attempts * 15, 45)  # Max -45 points
        }
    
    def _detect_security_anomalies(self, events: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> List[Insight]:
        """Detect security anomalies"""
        
        anomalies = []
        
        if not events:
            return anomalies
        
        # Detect event volume spikes
        volume_anomaly = self._detect_volume_spike(events, start_date, end_date)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        # Detect unusual login patterns
        login_anomaly = self._detect_login_anomalies(events)
        if login_anomaly:
            anomalies.append(login_anomaly)
        
        # Detect off-hours activity spikes
        off_hours_anomaly = self._detect_off_hours_activity(events)
        if off_hours_anomaly:
            anomalies.append(off_hours_anomaly)
        
        # Detect privilege escalation attempts
        privilege_anomaly = self._detect_privilege_escalation(events)
        if privilege_anomaly:
            anomalies.append(privilege_anomaly)
        
        # Detect suspicious IP activity
        ip_anomaly = self._detect_suspicious_ip_activity(events)
        if ip_anomaly:
            anomalies.append(ip_anomaly)
        
        return anomalies
    
    def _detect_volume_spike(self, events: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Optional[Insight]:
        """Detect security event volume spikes"""
        
        if len(events) < 10:  # Need minimum events for analysis
            return None
        
        # Group events by hour
        hourly_counts = defaultdict(int)
        for event in events:
            hour_key = event['timestamp'].strftime('%Y-%m-%d-%H')
            hourly_counts[hour_key] += 1
        
        if not hourly_counts:
            return None
        
        # Calculate baseline and spike
        values = list(hourly_counts.values())
        baseline = statistics.mean(values)
        
        # Check for significant spike
        max_count = max(values)
        if max_count > baseline * (1 + self.thresholds['security_event_spike']):
            spike_hour = max(hourly_counts, key=hourly_counts.get)
            
            return Insight(
                insight_id=f"volume_spike_{spike_hour}",
                type=InsightType.SECURITY_TREND,
                title="Security Event Volume Spike Detected",
                description=f"Security event volume increased significantly in hour {spike_hour}",
                severity="high",
                confidence=0.8,
                affected_entities=[spike_hour],
                recommendations=[
                    "Investigate the spike in security events",
                    "Review system logs for the identified period",
                    "Check for potential security incidents"
                ],
                evidence={
                    'spike_hour': spike_hour,
                    'event_count': max_count,
                    'baseline_average': baseline,
                    'spike_multiplier': max_count / baseline
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _detect_login_anomalies(self, events: List[Dict[str, Any]]) -> Optional[Insight]:
        """Detect unusual login patterns"""
        
        login_events = [event for event in events if event['event_type'] in [
            AuditEventTypes.LOGIN_SUCCESS, AuditEventTypes.LOGIN_FAILURE, AuditEventTypes.LOGIN_LOCKED
        ]]
        
        if not login_events:
            return None
        
        # Check for multiple failed logins
        failed_logins = [event for event in login_events if event['event_type'] == AuditEventTypes.LOGIN_FAILURE]
        
        if len(failed_logins) >= self.thresholds['failed_login_threshold']:
            # Group by IP
            ip_failures = Counter(event.get('ip_address') for event in failed_logins if event.get('ip_address'))
            
            if ip_failures:
                top_ip = ip_failures.most_common(1)[0]
                
                return Insight(
                    insight_id="login_anomaly_multiple_failures",
                    type=InsightType.THREAT_INDICATOR,
                    title="Multiple Login Failures Detected",
                    description=f"Detected {len(failed_logins)} failed login attempts, potentially indicating brute force attack",
                    severity="high",
                    confidence=0.9,
                    affected_entities=[top_ip[0]],
                    recommendations=[
                        "Block suspicious IP addresses",
                        "Implement additional authentication measures",
                        "Review affected user accounts"
                    ],
                    evidence={
                        'total_failed_logins': len(failed_logins),
                        'suspicious_ip': top_ip[0],
                        'attempts_from_ip': top_ip[1],
                        'time_window': f"{min(e['timestamp'] for e in failed_logins)} to {max(e['timestamp'] for e in failed_logins)}"
                    },
                    detected_at=datetime.utcnow()
                )
        
        return None
    
    def _detect_off_hours_activity(self, events: List[Dict[str, Any]]) -> Optional[Insight]:
        """Detect unusual off-hours activity"""
        
        off_hours_events = [
            event for event in events 
            if event['timestamp'].hour in self.thresholds['unusual_access_hours']
        ]
        
        if len(off_hours_events) > len(events) * 0.3:  # More than 30% off-hours
            users_involved = set(event['user_id'] for event in off_hours_events if event.get('user_id'))
            
            return Insight(
                insight_id="off_hours_activity_spike",
                type=InsightType.USER_BEHAVIOR,
                title="Unusual Off-Hours Activity",
                description=f"Detected high level of off-hours activity with {len(off_hours_events)} events",
                severity="medium",
                confidence=0.7,
                affected_entities=list(users_involved),
                recommendations=[
                    "Review off-hours access patterns",
                    "Implement time-based access controls",
                    "Investigate unusual user accounts"
                ],
                evidence={
                    'off_hours_events': len(off_hours_events),
                    'total_events': len(events),
                    'percentage_off_hours': round(len(off_hours_events) / len(events) * 100, 1),
                    'users_involved': list(users_involved)
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _detect_privilege_escalation(self, events: List[Dict[str, Any]]) -> Optional[Insight]:
        """Detect privilege escalation attempts"""
        
        privilege_events = [
            event for event in events
            if event['event_type'] in [
                AuditEventTypes.PRIVILEGE_ESCALATION,
                AuditEventTypes.PERMISSION_GRANTED,
                AuditEventTypes.ROLE_ASSIGNED
            ]
        ]
        
        failed_privilege_events = [
            event for event in privilege_events if event['outcome'] == 'failure'
        ]
        
        if len(failed_privilege_events) >= self.thresholds['privilege_escalation_attempts']:
            users_involved = set(event['user_id'] for event in failed_privilege_events if event.get('user_id'))
            
            return Insight(
                insight_id="privilege_escalation_attempts",
                type=InsightType.SECURITY_TREND,
                title="Multiple Privilege Escalation Attempts",
                description=f"Detected {len(failed_privilege_events)} failed privilege escalation attempts",
                severity="high",
                confidence=0.85,
                affected_entities=list(users_involved),
                recommendations=[
                    "Review user permission assignments",
                    "Implement additional authorization checks",
                    "Monitor affected users closely"
                ],
                evidence={
                    'failed_attempts': len(failed_privilege_events),
                    'users_involved': list(users_involved),
                    'event_types': list(set(event['event_type'] for event in failed_privilege_events))
                },
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _detect_suspicious_ip_activity(self, events: List[Dict[str, Any]]) -> Optional[Insight]:
        """Detect suspicious IP activity patterns"""
        
        ip_events = defaultdict(list)
        for event in events:
            if event.get('ip_address'):
                ip_events[event['ip_address']].append(event)
        
        suspicious_ips = []
        for ip, ip_events_list in ip_events.items():
            # Check for activity from many different users (bot/script behavior)
            unique_users = set(event.get('user_id') for event in ip_events_list if event.get('user_id'))
            
            # Check for high failure rate
            failures = sum(1 for event in ip_events_list if event['outcome'] == 'failure')
            total_events = len(ip_events_list)
            failure_rate = failures / total_events if total_events > 0 else 0
            
            if len(unique_users) > 5 or failure_rate > 0.7:
                suspicious_ips.append({
                    'ip': ip,
                    'unique_users': len(unique_users),
                    'total_events': total_events,
                    'failure_rate': failure_rate,
                    'suspicion_score': len(unique_users) + (failure_rate * 100)
                })
        
        if suspicious_ips:
            most_suspicious = sorted(suspicious_ips, key=lambda x: x['suspicion_score'], reverse=True)[0]
            
            return Insight(
                insight_id="suspicious_ip_activity",
                type=InsightType.THREAT_INDICATOR,
                title="Suspicious IP Activity Detected",
                description=f"IP {most_suspicious['ip']} shows suspicious activity patterns",
                severity="high",
                confidence=0.8,
                affected_entities=[most_suspicious['ip']],
                recommendations=[
                    "Block suspicious IP addresses",
                    "Implement IP-based rate limiting",
                    "Review access logs for this IP"
                ],
                evidence=most_suspicious,
                detected_at=datetime.utcnow()
            )
        
        return None
    
    def _calculate_security_score(self, metrics: Dict[str, Any], anomalies: List[Insight]) -> float:
        """Calculate overall security score (0-100)"""
        
        if not metrics:
            return 0.0
        
        score = 100.0  # Start with perfect score
        
        # Deduct points for critical events
        if 'security_score_components' in metrics:
            components = metrics['security_score_components']
            for component, impact in components.items():
                score += impact  # Impact is negative for negative components
        
        # Deduct points for anomalies
        for anomaly in anomalies:
            if anomaly.severity == 'critical':
                score -= 25
            elif anomaly.severity == 'high':
                score -= 15
            elif anomaly.severity == 'medium':
                score -= 10
            else:
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _analyze_security_trends(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze security trends over time"""
        
        # Group events by day
        daily_counts = defaultdict(int)
        for event in events:
            day_key = event['timestamp'].strftime('%Y-%m-%d')
            daily_counts[day_key] += 1
        
        if not daily_counts:
            return {}
        
        # Calculate trend
        days = sorted(daily_counts.keys())
        values = [daily_counts[day] for day in days]
        
        if len(values) >= 2:
            # Simple trend calculation
            trend = "increasing" if values[-1] > values[0] else "decreasing"
            trend_strength = abs(values[-1] - values[0]) / max(values) if max(values) > 0 else 0
        else:
            trend = "insufficient_data"
            trend_strength = 0.0
        
        return {
            'daily_distribution': dict(daily_counts),
            'trend': trend,
            'trend_strength': trend_strength,
            'peak_day': max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
            'total_days': len(daily_counts)
        }
    
    def _analyze_event_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze event type distribution"""
        
        if not events:
            return {}
        
        event_types = Counter(event['event_type'] for event in events)
        severities = Counter(event['severity'] for event in events)
        outcomes = Counter(event['outcome'] for event in events)
        
        return {
            'by_event_type': dict(event_types),
            'by_severity': dict(severities),
            'by_outcome': dict(outcomes),
            'most_common_event_type': event_types.most_common(1)[0] if event_types else None,
            'severity_distribution_pct': {
                k: round(v / len(events) * 100, 1) 
                for k, v in severities.items()
            }
        }
    
    def _analyze_geographic_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze geographic access patterns"""
        
        # This would integrate with geolocation services
        # For now, return placeholder analysis
        ip_addresses = set(event.get('ip_address') for event in events if event.get('ip_address'))
        
        return {
            'unique_ip_addresses': len(ip_addresses),
            'geographic_distribution': 'geolocation_analysis_pending',
            'suspicious_geographic_patterns': []
        }
    
    def _analyze_temporal_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal access patterns"""
        
        if not events:
            return {}
        
        # Hour distribution
        hourly_counts = Counter(event['timestamp'].hour for event in events)
        
        # Day of week distribution
        daily_counts = Counter(event['timestamp'].weekday() for event in events)
        
        return {
            'hourly_distribution': dict(hourly_counts),
            'daily_distribution': dict(daily_counts),
            'peak_hour': hourly_counts.most_common(1)[0] if hourly_counts else None,
            'peak_day': daily_counts.most_common(1)[0] if daily_counts else None,
            'business_hours_activity': self._calculate_business_hours_activity(hourly_counts)
        }
    
    def _calculate_business_hours_activity(self, hourly_counts: Counter) -> float:
        """Calculate percentage of activity during business hours (9-17)"""
        
        business_hours = list(range(9, 18))  # 9 AM to 5 PM
        business_activity = sum(hourly_counts.get(hour, 0) for hour in business_hours)
        total_activity = sum(hourly_counts.values())
        
        return round(business_activity / total_activity * 100, 1) if total_activity > 0 else 0.0
    
    def _generate_security_insights(self, events: List[Dict[str, Any]], anomalies: List[Insight]) -> List[Insight]:
        """Generate security-related insights"""
        
        insights = []
        
        # Add high-confidence anomalies as insights
        for anomaly in anomalies:
            if anomaly.confidence >= 0.8:
                insights.append(anomaly)
        
        # Generate additional insights based on event patterns
        if events:
            # Check for emerging threats
            recent_security_events = [event for event in events if 'security' in event['event_type']]
            if len(recent_security_events) > 10:
                insights.append(Insight(
                    insight_id="elevated_security_activity",
                    type=InsightType.SECURITY_TREND,
                    title="Elevated Security Activity",
                    description=f"Detected {len(recent_security_events)} security events requiring attention",
                    severity="medium",
                    confidence=0.7,
                    affected_entities=[],
                    recommendations=[
                        "Review recent security events",
                        "Assess current security posture",
                        "Consider additional monitoring"
                    ],
                    evidence={'security_events_count': len(recent_security_events)},
                    detected_at=datetime.utcnow()
                ))
        
        return insights
    
    def _calculate_security_alert_level(self, security_events: int, failed_logins: int, high_risk_events: int) -> str:
        """Calculate real-time security alert level"""
        
        if high_risk_events > 0 or security_events > 50 or failed_logins > 20:
            return "critical"
        elif security_events > 20 or failed_logins > 10:
            return "high"
        elif security_events > 5 or failed_logins > 3:
            return "medium"
        else:
            return "low"
    
    def _calculate_hour_over_hour_change(self, last_hour: datetime) -> float:
        """Calculate hour-over-hour change in events"""
        
        hour_before = last_hour - timedelta(hours=1)
        
        db: Session = SessionLocal()
        try:
            current_hour_count = db.query(AuditEvent).filter(
                AuditEvent.timestamp >= last_hour
            ).count()
            
            previous_hour_count = db.query(AuditEvent).filter(
                and_(
                    AuditEvent.timestamp >= hour_before,
                    AuditEvent.timestamp < last_hour
                )
            ).count()
            
            if previous_hour_count == 0:
                return float('inf') if current_hour_count > 0 else 0.0
            
            return round((current_hour_count - previous_hour_count) / previous_hour_count * 100, 1)
            
        finally:
            db.close()
    
    def _calculate_daily_average(self, last_day: datetime) -> float:
        """Calculate daily average events"""
        
        db: Session = SessionLocal()
        try:
            count = db.query(AuditEvent).filter(
                AuditEvent.timestamp >= last_day
            ).count()
            
            return count
            
        finally:
            db.close()
    
    def _compare_to_baseline(self, start_time: datetime) -> Dict[str, float]:
        """Compare current metrics to historical baseline"""
        
        # This would compare current activity to historical patterns
        return {
            'baseline_deviation': 0.0,
            'confidence': 0.5
        }
    
    def _analyze_user_behavior_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        
        if not events:
            return {}
        
        patterns = {
            'activity_hours': [],
            'frequent_resources': [],
            'login_patterns': [],
            'access_patterns': []
        }
        
        # Activity hours
        activity_hours = Counter(event['timestamp'].hour for event in events)
        patterns['activity_hours'] = activity_hours.most_common(5)
        
        # Frequent resources
        resources = Counter(event['resource_type'] for event in events)
        patterns['frequent_resources'] = resources.most_common(5)
        
        # Login patterns
        login_events = [event for event in events if event['event_type'].startswith('login')]
        if login_events:
            patterns['login_patterns'] = {
                'total_logins': len(login_events),
                'successful_logins': sum(1 for event in login_events if event['outcome'] == 'success'),
                'failed_logins': sum(1 for event in login_events if event['outcome'] == 'failure'),
                'unique_ips': len(set(event.get('ip_address') for event in login_events if event.get('ip_address')))
            }
        
        return patterns
    
    def _detect_user_behavior_anomalies(self, events: List[Dict[str, Any]]) -> List[Insight]:
        """Detect user behavior anomalies"""
        
        anomalies = []
        
        if not events:
            return anomalies
        
        # Detect unusual activity hours
        activity_hours = [event['timestamp'].hour for event in events]
        off_hours_count = sum(1 for hour in activity_hours if hour in self.thresholds['unusual_access_hours'])
        
        if off_hours_count > len(events) * 0.3:
            anomalies.append(Insight(
                insight_id="unusual_activity_hours",
                type=InsightType.USER_BEHAVIOR,
                title="Unusual Activity Hours",
                description=f"User active during unusual hours ({off_hours_count} events)",
                severity="medium",
                confidence=0.7,
                affected_entities=[events[0]['user_id']] if events else [],
                recommendations=["Review user access patterns", "Verify legitimate business need"],
                evidence={'off_hours_events': off_hours_count, 'total_events': len(events)},
                detected_at=datetime.utcnow()
            ))
        
        return anomalies
    
    def _generate_user_insights(self, events: List[Dict[str, Any]], patterns: Dict[str, Any], anomalies: List[Insight]) -> List[Insight]:
        """Generate user behavior insights"""
        
        insights = []
        
        # Add anomalies as insights if confidence is high
        for anomaly in anomalies:
            if anomaly.confidence >= 0.7:
                insights.append(anomaly)
        
        # Generate compliance-related insights
        if events:
            compliance_events = [event for event in events if event.get('compliance_tags')]
            if compliance_events:
                insights.append(Insight(
                    insight_id="compliance_activity",
                    type=InsightType.COMPLIANCE_STATUS,
                    title="Compliance Activity Detected",
                    description=f"User had {len(compliance_events)} compliance-related activities",
                    severity="low",
                    confidence=0.9,
                    affected_entities=[events[0]['user_id']] if events else [],
                    recommendations=["Review compliance activities", "Ensure proper documentation"],
                    evidence={'compliance_events_count': len(compliance_events)},
                    detected_at=datetime.utcnow()
                ))
        
        return insights
    
    def _calculate_behavior_score(self, events: List[Dict[str, Any]], patterns: Dict[str, Any], anomalies: List[Insight]) -> float:
        """Calculate user behavior score (0-100)"""
        
        if not events:
            return 0.0
        
        score = 100.0
        
        # Deduct for anomalies
        for anomaly in anomalies:
            if anomaly.severity == 'critical':
                score -= 30
            elif anomaly.severity == 'high':
                score -= 20
            elif anomaly.severity == 'medium':
                score -= 10
            else:
                score -= 5
        
        # Deduct for failed operations
        failed_events = sum(1 for event in events if event['outcome'] == 'failure')
        if failed_events > 0:
            score -= min(failed_events * 2, 20)
        
        return max(0.0, min(100.0, score))
    
    def _identify_risk_factors(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify risk factors for user"""
        
        risk_factors = []
        
        if not events:
            return risk_factors
        
        # High failure rate
        failed_events = sum(1 for event in events if event['outcome'] == 'failure')
        if failed_events > len(events) * 0.2:
            risk_factors.append({
                'factor': 'high_failure_rate',
                'description': f'User has {failed_events} failed operations',
                'risk_level': 'medium',
                'value': f'{failed_events}/{len(events)}'
            })
        
        # Multiple IP addresses
        ip_addresses = set(event.get('ip_address') for event in events if event.get('ip_address'))
        if len(ip_addresses) > 5:
            risk_factors.append({
                'factor': 'multiple_ip_addresses',
                'description': f'User accessed from {len(ip_addresses)} different IP addresses',
                'risk_level': 'medium',
                'value': str(len(ip_addresses))
            })
        
        # Off-hours activity
        off_hours = sum(1 for event in events if event['timestamp'].hour in self.thresholds['unusual_access_hours'])
        if off_hours > len(events) * 0.3:
            risk_factors.append({
                'factor': 'off_hours_activity',
                'description': f'User has {off_hours} off-hours activities',
                'risk_level': 'low',
                'value': f'{off_hours}/{len(events)}'
            })
        
        return risk_factors
    
    def _summarize_user_activity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize user activity"""
        
        if not events:
            return {}
        
        return {
            'total_events': len(events),
            'unique_resource_types': len(set(event['resource_type'] for event in events)),
            'activity_span_days': (max(event['timestamp'] for event in events) - 
                                 min(event['timestamp'] for event in events)).days + 1,
            'most_active_day': Counter(event['timestamp'].date() for event in events).most_common(1)[0],
            'success_rate': round(sum(1 for event in events if event['outcome'] == 'success') / len(events) * 100, 1)
        }
    
    def _generate_user_recommendations(self, anomalies: List[Insight], patterns: Dict[str, Any]) -> List[str]:
        """Generate user-specific recommendations"""
        
        recommendations = []
        
        for anomaly in anomalies:
            recommendations.extend(anomaly.recommendations)
        
        # Add general recommendations
        if patterns.get('activity_hours'):
            recommendations.append("Review user's working hours and access patterns")
        
        if patterns.get('frequent_resources'):
            recommendations.append("Monitor access to sensitive resources")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _analyze_compliance_metrics(self, events: List[Dict[str, Any]], regulation: str) -> Dict[str, Any]:
        """Analyze compliance metrics"""
        
        if not events:
            return {}
        
        metrics = {
            'total_compliance_events': len(events),
            'event_types': list(set(event['event_type'] for event in events)),
            'compliant_events': sum(1 for event in events if event['outcome'] == 'success'),
            'non_compliant_events': sum(1 for event in events if event['outcome'] == 'failure'),
            'last_compliance_check': max(event['timestamp'] for event in events) if events else None
        }
        
        # Regulation-specific metrics
        if regulation.lower() == 'gdpr':
            metrics['gdpr_specific'] = {
                'data_access_events': sum(1 for event in events if 'data_access' in event['event_type']),
                'consent_events': sum(1 for event in events if 'consent' in event['event_type']),
                'right_to_be_forgotten': sum(1 for event in events if 'right_to_be_forgotten' in event['event_type'])
            }
        elif regulation.lower() == 'sox':
            metrics['sox_specific'] = {
                'control_tests': sum(1 for event in events if 'control' in event['event_type']),
                'financial_events': sum(1 for event in events if event['resource_type'] == 'financial')
            }
        
        return metrics
    
    def _check_compliance_requirements(self, events: List[Dict[str, Any]], regulation: str) -> Dict[str, Any]:
        """Check compliance requirements status"""
        
        requirements_status = {
            'regulation': regulation,
            'requirements_met': [],
            'requirements_pending': [],
            'requirements_failed': [],
            'overall_status': 'unknown'
        }
        
        if not events:
            requirements_status['overall_status'] = 'no_data'
            return requirements_status
        
        # Check specific requirements based on regulation
        if regulation.lower() == 'gdpr':
            # Check GDPR requirements
            data_access_events = [e for e in events if 'data_access' in e['event_type']]
            consent_events = [e for e in events if 'consent' in e['event_type']]
            
            if data_access_events:
                requirements_status['requirements_met'].append('data_access_logged')
            else:
                requirements_status['requirements_pending'].append('data_access_logged')
            
            if consent_events:
                requirements_status['requirements_met'].append('consent_tracked')
            else:
                requirements_status['requirements_pending'].append('consent_tracked')
        
        # Determine overall status
        if requirements_status['requirements_failed']:
            requirements_status['overall_status'] = 'non_compliant'
        elif requirements_status['requirements_pending']:
            requirements_status['overall_status'] = 'partial_compliance'
        else:
            requirements_status['overall_status'] = 'compliant'
        
        return requirements_status
    
    def _detect_compliance_violations(self, events: List[Dict[str, Any]], regulation: str) -> List[Dict[str, Any]]:
        """Detect compliance violations"""
        
        violations = []
        
        if not events:
            return violations
        
        # Check for unauthorized data access
        unauthorized_access = [e for e in events if e['outcome'] == 'failure' and 'access' in e['event_type']]
        if unauthorized_access:
            violations.append({
                'type': 'unauthorized_data_access',
                'description': f'Detected {len(unauthorized_access)} unauthorized access attempts',
                'severity': 'high',
                'events': len(unauthorized_access),
                'regulation_impact': regulation.upper()
            })
        
        # Check for missing audit trails
        # This would involve comparing expected events vs actual events
        
        return violations
    
    def _generate_compliance_insights(self, events: List[Dict[str, Any]], violations: List[Dict[str, Any]], regulation: str) -> List[Insight]:
        """Generate compliance insights"""
        
        insights = []
        
        # Add violations as high-priority insights
        for violation in violations:
            insights.append(Insight(
                insight_id=f"compliance_violation_{violation['type']}",
                type=InsightType.COMPLIANCE_STATUS,
                title=f"Compliance Violation: {violation['type']}",
                description=violation['description'],
                severity=violation['severity'],
                confidence=0.9,
                affected_entities=[regulation],
                recommendations=[
                    f"Address {violation['type']} compliance violation",
                    f"Review {regulation} compliance requirements",
                    "Implement corrective measures"
                ],
                evidence=violation,
                detected_at=datetime.utcnow()
            ))
        
        return insights
    
    def _calculate_compliance_score(self, metrics: Dict[str, Any], violations: List[Dict[str, Any]]) -> float:
        """Calculate compliance score (0-100)"""
        
        if not metrics:
            return 0.0
        
        score = 100.0
        
        # Deduct for violations
        for violation in violations:
            if violation['severity'] == 'high':
                score -= 30
            elif violation['severity'] == 'medium':
                score -= 20
            else:
                score -= 10
        
        # Deduct for failed events
        if 'non_compliant_events' in metrics:
            failed_rate = metrics['non_compliant_events'] / max(metrics['total_compliance_events'], 1)
            score -= failed_rate * 50
        
        return max(0.0, min(100.0, score))
    
    def _generate_compliance_recommendations(self, violations: List[Dict[str, Any]], requirements_status: Dict[str, Any]) -> List[str]:
        """Generate compliance recommendations"""
        
        recommendations = []
        
        # Address violations
        for violation in violations:
            recommendations.append(f"Address {violation['type']} violation")
        
        # Address requirements
        for requirement in requirements_status.get('requirements_pending', []):
            recommendations.append(f"Implement {requirement} requirement")
        
        # General recommendations
        recommendations.extend([
            "Conduct regular compliance audits",
            "Update compliance documentation",
            "Train staff on compliance requirements"
        ])
        
        return list(set(recommendations))
    
    def _assess_audit_readiness(self, events: List[Dict[str, Any]], regulation: str) -> Dict[str, Any]:
        """Assess audit readiness"""
        
        readiness = {
            'overall_readiness': 'unknown',
            'strengths': [],
            'gaps': [],
            'recommendations': []
        }
        
        if not events:
            readiness['overall_readiness'] = 'insufficient_data'
            readiness['gaps'].append('Insufficient audit trail data')
            return readiness
        
        # Check data completeness
        completeness_score = self._assess_data_completeness(events)
        
        # Check data freshness
        freshness_score = self._assess_data_freshness(events)
        
        # Check data integrity
        integrity_score = self._assess_data_integrity(events)
        
        # Calculate overall readiness
        overall_score = (completeness_score + freshness_score + integrity_score) / 3
        
        if overall_score >= 80:
            readiness['overall_readiness'] = 'ready'
            readiness['strengths'].append('Complete audit trail')
            readiness['strengths'].append('Recent data')
            readiness['strengths'].append('Data integrity maintained')
        elif overall_score >= 60:
            readiness['overall_readiness'] = 'mostly_ready'
            readiness['gaps'].append('Some data gaps identified')
        else:
            readiness['overall_readiness'] = 'not_ready'
            readiness['gaps'].append('Significant audit trail gaps')
            readiness['gaps'].append('Data integrity concerns')
        
        readiness['scores'] = {
            'completeness': completeness_score,
            'freshness': freshness_score,
            'integrity': integrity_score,
            'overall': overall_score
        }
        
        return readiness
    
    def _assess_data_completeness(self, events: List[Dict[str, Any]]) -> float:
        """Assess completeness of audit data"""
        
        if not events:
            return 0.0
        
        # Check required fields
        required_fields = ['event_type', 'user_id', 'timestamp', 'outcome']
        complete_events = 0
        
        for event in events:
            if all(field in event and event[field] for field in required_fields):
                complete_events += 1
        
        return (complete_events / len(events)) * 100
    
    def _assess_data_freshness(self, events: List[Dict[str, Any]]) -> float:
        """Assess freshness of audit data"""
        
        if not events:
            return 0.0
        
        now = datetime.utcnow()
        most_recent_event = max(event['timestamp'] for event in events)
        
        days_old = (now - most_recent_event).days
        
        if days_old == 0:
            return 100.0
        elif days_old <= 1:
            return 90.0
        elif days_old <= 7:
            return 80.0
        elif days_old <= 30:
            return 60.0
        else:
            return max(0.0, 100.0 - (days_old * 2))
    
    def _assess_data_integrity(self, events: List[Dict[str, Any]]) -> float:
        """Assess integrity of audit data"""
        
        if not events:
            return 0.0
        
        # Check for data consistency and anomalies
        consistency_checks = 0
        total_checks = 0
        
        # Check timestamp consistency
        timestamps = [event['timestamp'] for event in events]
        if all(isinstance(ts, datetime) for ts in timestamps):
            consistency_checks += 1
        total_checks += 1
        
        # Check for duplicate events
        event_ids = [event.get('event_id') for event in events if event.get('event_id')]
        if len(event_ids) == len(set(event_ids)):
            consistency_checks += 1
        total_checks += 1
        
        return (consistency_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    def _generate_executive_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate executive summary report"""
        
        # Get high-level metrics
        security_analysis = self.analyze_security_trends(start_date, end_date)
        
        return {
            'report_type': 'executive',
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'summary': {
                'security_posture': self._get_security_posture_summary(security_analysis),
                'compliance_status': 'assessed',
                'key_risks': self._identify_key_risks(security_analysis),
                'recommendations': self._generate_executive_recommendations(security_analysis)
            },
            'metrics': {
                'security_score': security_analysis.get('security_score', 0),
                'total_security_events': security_analysis.get('metrics', {}).get('total_events', 0),
                'anomalies_detected': len(security_analysis.get('anomalies', [])),
                'insights_generated': len(security_analysis.get('insights', []))
            },
            'trends': security_analysis.get('trends', {})
        }
    
    def _generate_technical_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate technical audit report"""
        
        return {
            'report_type': 'technical',
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'technical_analysis': {
                'security_trends': self.analyze_security_trends(start_date, end_date),
                'system_metrics': 'detailed_technical_metrics',
                'anomaly_details': 'technical_anomaly_analysis',
                'correlation_analysis': 'event_correlation_details'
            }
        }
    
    def _generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance audit report"""
        
        regulations = ['gdpr', 'sox', 'pci_dss']
        compliance_analysis = {}
        
        for regulation in regulations:
            compliance_analysis[regulation] = self.analyze_compliance_status(
                regulation, start_date, end_date
            )
        
        return {
            'report_type': 'compliance',
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'compliance_analysis': compliance_analysis,
            'overall_compliance_score': self._calculate_overall_compliance_score(compliance_analysis)
        }
    
    def _generate_security_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate security audit report"""
        
        return {
            'report_type': 'security',
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'security_analysis': self.analyze_security_trends(start_date, end_date),
            'real_time_metrics': self.get_real_time_metrics(),
            'threat_intelligence': 'threat_intelligence_summary'
        }
    
    def _get_security_posture_summary(self, security_analysis: Dict[str, Any]) -> str:
        """Get security posture summary for executives"""
        
        score = security_analysis.get('security_score', 0)
        
        if score >= 90:
            return "Strong security posture with excellent monitoring"
        elif score >= 75:
            return "Good security posture with minor areas for improvement"
        elif score >= 60:
            return "Adequate security posture requiring attention to identified issues"
        elif score >= 40:
            return "Weak security posture with significant vulnerabilities"
        else:
            return "Critical security posture requiring immediate action"
    
    def _identify_key_risks(self, security_analysis: Dict[str, Any]) -> List[str]:
        """Identify key risks for executive summary"""
        
        risks = []
        
        anomalies = security_analysis.get('anomalies', [])
        for anomaly in anomalies:
            if anomaly.get('severity') in ['high', 'critical']:
                risks.append(anomaly.get('title', 'Security anomaly detected'))
        
        return risks[:5]  # Return top 5 risks
    
    def _generate_executive_recommendations(self, security_analysis: Dict[str, Any]) -> List[str]:
        """Generate executive-level recommendations"""
        
        recommendations = []
        
        score = security_analysis.get('security_score', 0)
        
        if score < 70:
            recommendations.append("Implement immediate security improvements")
            recommendations.append("Increase security monitoring and alerting")
        
        anomalies = security_analysis.get('anomalies', [])
        critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
        
        if critical_anomalies:
            recommendations.append("Address critical security incidents immediately")
        
        recommendations.append("Conduct regular security assessments")
        recommendations.append("Review and update security policies")
        
        return recommendations
    
    def _calculate_overall_compliance_score(self, compliance_analysis: Dict[str, float]) -> float:
        """Calculate overall compliance score across regulations"""
        
        if not compliance_analysis:
            return 0.0
        
        scores = [analysis.get('compliance_score', 0) for analysis in compliance_analysis.values()]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _analyze_historical_trends(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze historical trends for prediction"""
        
        # This would implement time series analysis
        return {
            'trend_analysis': 'time_series_analysis_results',
            'seasonality': 'seasonal_patterns',
            'baseline': 'historical_baseline'
        }
    
    def _generate_predictions(self, trends: Dict[str, Any], prediction_period_days: int) -> Dict[str, Any]:
        """Generate future predictions based on trends"""
        
        return {
            'predicted_security_events': 'forecast_based_on_trends',
            'predicted_compliance_events': 'forecast_based_on_trends',
            'predicted_risk_level': 'risk_level_forecast',
            'confidence_intervals': 'prediction_confidence_intervals'
        }
    
    def _calculate_prediction_confidence(self, trends: Dict[str, Any]) -> float:
        """Calculate confidence in predictions"""
        
        return 0.7  # Placeholder confidence score