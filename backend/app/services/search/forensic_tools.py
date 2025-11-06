"""
Forensic Investigation Tools for Security Incident Analysis
Provides advanced tools for digital forensics and security incident investigation
"""

import logging
import json
import hashlib
import statistics
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter

from ..elk import ElasticsearchClient

logger = logging.getLogger(__name__)


class IncidentStatus(Enum):
    """Security incident status"""
    ACTIVE = "active"
    CONTAINED = "contained"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class ThreatActorType(Enum):
    """Threat actor classifications"""
    INDIVIDUAL = "individual"
    ORGANIZED_CRIME = "organized_crime"
    NATION_STATE = "nation_state"
    INSIDER = "insider"
    SCRIPT_KIDDIE = "script_kiddie"
    UNKNOWN = "unknown"


class AttackVector(Enum):
    """Attack vector classifications"""
    PHISHING = "phishing"
    MALWARE = "malware"
    EXPLOIT = "exploit"
    SOCIAL_ENGINEERING = "social_engineering"
    PHYSICAL = "physical"
    SUPPLY_CHAIN = "supply_chain"
    ZERO_DAY = "zero_day"


@dataclass
class SecurityIncident:
    """Security incident data structure"""
    incident_id: str
    title: str
    description: str
    severity: str
    status: IncidentStatus
    first_seen: datetime
    last_seen: datetime
    affected_systems: List[str]
    threat_actors: List[ThreatActorType]
    attack_vectors: List[AttackVector]
    indicators: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    evidence: List[str]
    investigation_notes: List[str]
    remediation_actions: List[Dict[str, Any]]
    impact_assessment: Dict[str, Any]
    confidence_score: float


@dataclass
class IOC:
    """Indicator of Compromise"""
    ioc_type: str  # ip, domain, hash, url, etc.
    value: str
    confidence: str  # high, medium, low
    first_seen: datetime
    last_seen: datetime
    context: Dict[str, Any]
    threat_family: str
    kill_chain_phase: str


@dataclass
class ForensicTimeline:
    """Forensic investigation timeline entry"""
    timestamp: datetime
    event_type: str
    source: str
    description: str
    evidence: List[str]
    confidence: float
    related_iocs: List[str]
    investigation_notes: str


class ForensicInvestigationService:
    """Advanced forensic investigation and security incident analysis"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Initialize forensic investigation service
        
        Args:
            es_client: Elasticsearch client
        """
        self.es_client = es_client
        
        # Kill chain phases for attack analysis
        self.kill_chain_phases = [
            'reconnaissance',
            'weaponization', 
            'delivery',
            'exploitation',
            'installation',
            'command_control',
            'actions_objectives'
        ]
        
        # MITRE ATT&CK technique mappings
        self.mitre_techniques = {
            'initial_access': ['T1078', 'T1192', 'T1193', 'T1194', 'T1195'],
            'execution': ['T1059', 'T1053', 'T1204'],
            'persistence': ['T1098', 'T1053', 'T1060'],
            'privilege_escalation': ['T1055', 'T1068', 'T1053'],
            'defense_evasion': ['T1070', 'T1140', 'T1202'],
            'credential_access': ['T1003', 'T1110', 'T1213'],
            'discovery': ['T1087', 'T1046', 'T1018'],
            'lateral_movement': ['T1021', 'T1076', 'T1091'],
            'collection': ['T1005', 'T1560', 'T1056'],
            'exfiltration': ['T1020', 'T1041', 'T1567'],
            'impact': ['T1485', 'T1486', 'T1490']
        }
        
        # Threat intelligence feeds for IOC enrichment
        self.threat_feeds = {
            'malware_hashes': set(),  # Would be populated from threat feeds
            'malicious_ips': set(),   # Would be populated from threat feeds
            'malicious_domains': set() # Would be populated from threat feeds
        }
    
    def create_incident(self, 
                       title: str,
                       description: str,
                       severity: str = 'medium',
                       initial_indicators: List[Dict] = None) -> SecurityIncident:
        """
        Create new security incident for investigation
        
        Args:
            title: Incident title
            description: Incident description
            severity: Initial severity level
            initial_indicators: Initial IOCs or indicators
            
        Returns:
            Created security incident
        """
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{hash(title) % 10000:04d}"
        
        incident = SecurityIncident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.INVESTIGATING,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            affected_systems=[],
            threat_actors=[],
            attack_vectors=[],
            indicators=initial_indicators or [],
            timeline=[],
            evidence=[],
            investigation_notes=[],
            remediation_actions=[],
            impact_assessment={},
            confidence_score=0.0
        )
        
        # Add initial timeline entry
        timeline_entry = {
            'timestamp': datetime.utcnow(),
            'event_type': 'incident_created',
            'description': f"Security incident created: {title}",
            'analyst': 'system',
            'confidence': 1.0
        }
        incident.timeline.append(timeline_entry)
        
        logger.info(f"Created security incident: {incident_id}")
        return incident
    
    def enrich_incident_with_logs(self, incident: SecurityIncident, time_window: timedelta) -> SecurityIncident:
        """
        Enrich incident with log data and analysis
        
        Args:
            incident: Security incident to enrich
            time_window: Time window to analyze
            
        Returns:
            Enriched security incident
        """
        try:
            # Calculate time range around incident
            end_time = incident.last_seen
            start_time = incident.first_seen - time_window
            
            # Search across all relevant log indices
            log_indices = ['audit_logs', 'security_logs', 'application_logs', 'user_activity_logs']
            
            # Build time-based query
            query = {
                'bool': {
                    'must': [
                        {
                            'range': {
                                'timestamp': {
                                    'gte': start_time,
                                    'lte': end_time
                                }
                            }
                        }
                    ]
                }
            }
            
            # Add indicator-based queries if available
            for indicator in incident.indicators:
                if 'ip_address' in indicator:
                    query['bool']['must'].append({
                        'term': {'ip_address': indicator['ip_address']}
                    })
                elif 'user_id' in indicator:
                    query['bool']['must'].append({
                        'term': {'user_id': indicator['user_id']}
                    })
            
            # Execute search
            response = self.es_client.advanced_search(
                index_types=log_indices,
                query=query,
                size=1000
            )
            
            # Process results
            enriched_indicators = self._analyze_log_data(response['hits']['hits'], incident)
            
            # Update incident with enriched data
            incident.indicators.extend(enriched_indicators)
            incident.affected_systems = list(set([i.get('affected_system') for i in enriched_indicators if i.get('affected_system')]))
            
            # Generate timeline
            incident.timeline = self._build_incident_timeline(incident, response['hits']['hits'])
            
            # Calculate confidence score
            incident.confidence_score = self._calculate_incident_confidence(incident)
            
            logger.info(f"Enriched incident {incident.incident_id} with {len(enriched_indicators)} additional indicators")
            return incident
            
        except Exception as e:
            logger.error(f"Failed to enrich incident {incident.incident_id}: {e}")
            raise
    
    def _analyze_log_data(self, hits: List[Dict], incident: SecurityIncident) -> List[Dict]:
        """Analyze log data to extract additional indicators"""
        indicators = []
        ip_counter = Counter()
        user_counter = Counter()
        system_counter = Counter()
        
        # Analyze hits for patterns
        for hit in hits:
            source = hit['_source']
            
            # Extract IPs and count occurrences
            if 'ip_address' in source:
                ip_counter[source['ip_address']] += 1
            if 'source_ip' in source:
                ip_counter[source['source_ip']] += 1
            
            # Extract users and count activities
            if 'user_id' in source:
                user_counter[source['user_id']] += 1
            
            # Track affected systems
            if 'hostname' in source:
                system_counter[source['hostname']] += 1
            
            # Look for suspicious patterns
            if self._is_suspicious_event(source):
                indicator = {
                    'type': 'suspicious_activity',
                    'value': source,
                    'source_index': hit['_index'],
                    'confidence': self._assess_event_confidence(source),
                    'context': {
                        'event_type': source.get('event_type', 'unknown'),
                        'timestamp': source.get('timestamp'),
                        'anomaly_score': self._calculate_anomaly_score(source)
                    }
                }
                indicators.append(indicator)
        
        # Convert counters to high-confidence indicators
        for ip, count in ip_counter.items():
            if count > 5:  # Threshold for suspicious IP activity
                indicators.append({
                    'type': 'frequent_ip',
                    'value': ip,
                    'count': count,
                    'confidence': 'high' if count > 20 else 'medium',
                    'context': {'activity_count': count}
                })
        
        for user, count in user_counter.items():
            if count > 50:  # Threshold for suspicious user activity
                indicators.append({
                    'type': 'active_user',
                    'value': user,
                    'count': count,
                    'confidence': 'medium',
                    'context': {'activity_count': count}
                })
        
        return indicators
    
    def _is_suspicious_event(self, event: Dict) -> bool:
        """Determine if an event is suspicious"""
        suspicious_indicators = [
            event.get('level') == 'ERROR',
            event.get('severity') in ['high', 'critical'],
            event.get('status_code', 0) >= 400,
            event.get('blocked', False) == True,
            'malware' in str(event.get('event_type', '')).lower(),
            'exploit' in str(event.get('event_type', '')).lower(),
            event.get('threat_score', 0) > 7.0
        ]
        
        return any(suspicious_indicators)
    
    def _assess_event_confidence(self, event: Dict) -> str:
        """Assess confidence level of an event"""
        confidence_score = 0
        
        # High confidence indicators
        if event.get('severity') == 'critical':
            confidence_score += 3
        if event.get('blocked', False):
            confidence_score += 2
        if event.get('threat_score', 0) > 8.0:
            confidence_score += 2
        
        # Medium confidence indicators
        if event.get('level') == 'ERROR':
            confidence_score += 1
        if event.get('severity') == 'high':
            confidence_score += 1
        if event.get('status_code', 0) >= 500:
            confidence_score += 1
        
        # Low confidence indicators
        if event.get('status_code', 0) >= 400:
            confidence_score += 0.5
        
        if confidence_score >= 3:
            return 'high'
        elif confidence_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_anomaly_score(self, event: Dict) -> float:
        """Calculate anomaly score for an event"""
        score = 0.0
        
        # Severity-based scoring
        severity_scores = {'low': 1, 'medium': 3, 'high': 6, 'critical': 10}
        score += severity_scores.get(event.get('severity', 'low'), 1)
        
        # Error-based scoring
        if event.get('level') == 'ERROR':
            score += 3
        if event.get('status_code', 0) >= 500:
            score += 5
        elif event.get('status_code', 0) >= 400:
            score += 2
        
        # Threat-based scoring
        if event.get('blocked', False):
            score += 8
        
        threat_score = event.get('threat_score', 0)
        if threat_score > 0:
            score += threat_score
        
        # Normalize score to 0-10 range
        return min(score, 10.0)
    
    def _build_incident_timeline(self, incident: SecurityIncident, hits: List[Dict]) -> List[Dict]:
        """Build comprehensive timeline for incident"""
        timeline_events = []
        
        # Add existing incident events
        for event in incident.timeline:
            timeline_events.append({
                'timestamp': event.get('timestamp', datetime.utcnow()),
                'event_type': event.get('event_type', 'incident'),
                'description': event.get('description', ''),
                'source': 'incident_record',
                'confidence': event.get('confidence', 1.0),
                'related_iocs': [],
                'investigation_notes': ''
            })
        
        # Add log events
        for hit in hits:
            source = hit['_source']
            
            # Create timeline event
            timeline_event = {
                'timestamp': datetime.fromisoformat(source['timestamp'].replace('Z', '+00:00')) if isinstance(source['timestamp'], str) else source['timestamp'],
                'event_type': source.get('event_type', 'log_event'),
                'description': f"Log event: {source.get('message', 'No message')}",
                'source': hit['_index'],
                'confidence': self._assess_event_confidence(source),
                'related_iocs': [source.get('ip_address', ''), source.get('user_id', '')],
                'investigation_notes': f"Index: {hit['_index']}, Type: {source.get('event_type', 'unknown')}"
            }
            
            timeline_events.append(timeline_event)
        
        # Sort by timestamp
        timeline_events.sort(key=lambda x: x['timestamp'])
        
        return timeline_events
    
    def _calculate_incident_confidence(self, incident: SecurityIncident) -> float:
        """Calculate overall confidence score for incident"""
        if not incident.indicators:
            return 0.0
        
        confidence_weights = {'high': 1.0, 'medium': 0.6, 'low': 0.3}
        
        total_weighted_confidence = 0.0
        total_weight = 0
        
        for indicator in incident.indicators:
            confidence = indicator.get('confidence', 'low')
            weight = confidence_weights.get(confidence, 0.3)
            total_weighted_confidence += weight
            total_weight += 1
        
        return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def correlate_threat_indicators(self, iocs: List[IOC]) -> Dict[str, Any]:
        """
        Correlate threat indicators to identify threat actor patterns
        
        Args:
            iocs: List of IOCs to correlate
            
        Returns:
            Correlation analysis results
        """
        # Group IOCs by type
        ips = [ioc for ioc in iocs if ioc.ioc_type == 'ip']
        domains = [ioc for ioc in iocs if ioc.ioc_type == 'domain']
        hashes = [ioc for ioc in iocs if ioc.ioc_type == 'hash']
        urls = [ioc for ioc in iocs if ioc.ioc_type == 'url']
        
        # Analyze temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(iocs)
        
        # Analyze geographic patterns
        geo_analysis = self._analyze_geographic_patterns(ips)
        
        # Identify threat actor behavior
        behavior_analysis = self._analyze_behavior_patterns(iocs)
        
        # Calculate threat actor confidence
        actor_confidence = self._calculate_actor_confidence(iocs, behavior_analysis)
        
        # Generate correlation report
        correlation_report = {
            'ioc_summary': {
                'total_iocs': len(iocs),
                'ip_addresses': len(ips),
                'domains': len(domains),
                'hashes': len(hashes),
                'urls': len(urls)
            },
            'temporal_analysis': temporal_analysis,
            'geographic_analysis': geo_analysis,
            'behavior_analysis': behavior_analysis,
            'threat_actor_assessment': actor_confidence,
            'correlation_score': self._calculate_correlation_score(iocs, temporal_analysis, geo_analysis),
            'recommendations': self._generate_correlation_recommendations(iocs, behavior_analysis)
        }
        
        return correlation_report
    
    def _analyze_temporal_patterns(self, iocs: List[IOC]) -> Dict[str, Any]:
        """Analyze temporal patterns in IOCs"""
        if not iocs:
            return {}
        
        # Extract timestamps
        timestamps = [ioc.last_seen for ioc in iocs if ioc.last_seen]
        timestamps.sort()
        
        if len(timestamps) < 2:
            return {'pattern': 'insufficient_data'}
        
        # Calculate intervals
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        # Analyze patterns
        avg_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        # Determine pattern type
        if std_interval / avg_interval < 0.5 if avg_interval > 0 else False:
            pattern = 'regular_intervals'
        elif max(intervals) < 300:  # 5 minutes
            pattern = 'rapid_fire'
        elif min(intervals) > 3600:  # 1 hour
            pattern = 'sporadic_activity'
        else:
            pattern = 'irregular_intervals'
        
        return {
            'pattern': pattern,
            'avg_interval_seconds': avg_interval,
            'std_interval_seconds': std_interval,
            'first_activity': timestamps[0],
            'last_activity': timestamps[-1],
            'activity_span_hours': (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        }
    
    def _analyze_geographic_patterns(self, ips: List[IOC]) -> Dict[str, Any]:
        """Analyze geographic patterns in IP IOCs"""
        if not ips:
            return {}
        
        # Group by location (simplified - would use geolocation data)
        locations = defaultdict(list)
        for ioc in ips:
            location = ioc.context.get('location', 'unknown')
            locations[location].append(ioc)
        
        # Analyze distribution
        location_counts = {loc: len(iocs) for loc, iocs in locations.items()}
        primary_location = max(location_counts.items(), key=lambda x: x[1])
        
        # Calculate diversity
        unique_locations = len(locations)
        total_iocs = len(ips)
        geographic_diversity = unique_locations / total_iocs if total_iocs > 0 else 0
        
        return {
            'unique_locations': unique_locations,
            'primary_location': primary_location[0],
            'primary_location_count': primary_location[1],
            'geographic_diversity': geographic_diversity,
            'location_distribution': dict(location_counts),
            'distribution_analysis': 'concentrated' if geographic_diversity < 0.3 else 'distributed'
        }
    
    def _analyze_behavior_patterns(self, iocs: List[IOC]) -> Dict[str, Any]:
        """Analyze threat actor behavior patterns"""
        # Analyze kill chain coverage
        kill_chain_coverage = defaultdict(int)
        for ioc in iocs:
            phase = ioc.kill_chain_phase
            kill_chain_coverage[phase] += 1
        
        # Analyze threat family distribution
        threat_families = Counter([ioc.threat_family for ioc in iocs if ioc.threat_family])
        
        # Analyze confidence levels
        confidence_levels = Counter([ioc.confidence for ioc in iocs])
        
        return {
            'kill_chain_coverage': dict(kill_chain_coverage),
            'kill_chain_completeness': len([phase for phase in self.kill_chain_phases if phase in kill_chain_coverage]),
            'primary_threat_family': threat_families.most_common(1)[0][0] if threat_families else 'unknown',
            'threat_family_diversity': len(threat_families),
            'confidence_distribution': dict(confidence_levels),
            'behavior_sophistication': self._assess_behavior_sophistication(kill_chain_coverage, len(threat_families))
        }
    
    def _assess_behavior_sophistication(self, kill_chain_coverage: Dict, threat_family_count: int) -> str:
        """Assess sophistication level of threat actor behavior"""
        coverage_score = len(kill_chain_coverage)
        
        if coverage_score >= 5 and threat_family_count == 1:
            return 'highly_sophisticated'
        elif coverage_score >= 3 and threat_family_count <= 2:
            return 'moderately_sophisticated'
        elif coverage_score >= 2:
            return 'low_sophistication'
        else:
            return 'basic_activity'
    
    def _calculate_actor_confidence(self, iocs: List[IOC], behavior_analysis: Dict) -> Dict[str, Any]:
        """Calculate confidence in threat actor assessment"""
        # Base confidence from IOC quality
        ioc_confidence = statistics.mean([
            {'high': 0.9, 'medium': 0.6, 'low': 0.3}.get(ioc.confidence, 0.3)
            for ioc in iocs
        ])
        
        # Adjust for behavior sophistication
        sophistication_multiplier = {
            'highly_sophisticated': 1.2,
            'moderately_sophisticated': 1.0,
            'low_sophistication': 0.8,
            'basic_activity': 0.6
        }.get(behavior_analysis.get('behavior_sophistication'), 0.6)
        
        final_confidence = min(ioc_confidence * sophistication_multiplier, 1.0)
        
        return {
            'confidence_score': final_confidence,
            'confidence_level': self._get_confidence_level(final_confidence),
            'assessment_basis': {
                'ioc_quality': ioc_confidence,
                'behavior_sophistication': behavior_analysis.get('behavior_sophistication'),
                'total_iocs': len(iocs)
            }
        }
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level string from numeric score"""
        if score >= 0.8:
            return 'very_high'
        elif score >= 0.6:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        elif score >= 0.2:
            return 'low'
        else:
            return 'very_low'
    
    def _calculate_correlation_score(self, iocs: List[IOC], temporal_analysis: Dict, geo_analysis: Dict) -> float:
        """Calculate overall correlation score for IOCs"""
        base_score = 0.5
        
        # Temporal correlation boost
        if temporal_analysis.get('pattern') in ['regular_intervals', 'rapid_fire']:
            base_score += 0.2
        
        # Geographic correlation boost
        if geo_analysis.get('geographic_diversity', 0) < 0.5:  # Concentrated
            base_score += 0.1
        
        # IOC quantity boost
        if len(iocs) >= 10:
            base_score += 0.1
        elif len(iocs) >= 5:
            base_score += 0.05
        
        return min(base_score, 1.0)
    
    def _generate_correlation_recommendations(self, iocs: List[IOC], behavior_analysis: Dict) -> List[str]:
        """Generate recommendations based on correlation analysis"""
        recommendations = []
        
        # Recommendations based on behavior analysis
        coverage = behavior_analysis.get('kill_chain_completeness', 0)
        if coverage >= 5:
            recommendations.append("Advanced persistent threat detected - implement immediate containment measures")
        elif coverage >= 3:
            recommendations.append("Multi-stage attack detected - enhance monitoring and detection capabilities")
        
        # Recommendations based on IOC types
        ioc_types = Counter([ioc.ioc_type for ioc in iocs])
        if ioc_types.get('hash', 0) >= 3:
            recommendations.append("Multiple malware samples detected - conduct malware analysis and threat hunting")
        
        # Recommendations based on threat family
        family_diversity = behavior_analysis.get('threat_family_diversity', 0)
        if family_diversity > 3:
            recommendations.append("Multiple threat families detected - investigate potential coordinated attack")
        
        # General recommendations
        recommendations.extend([
            "Implement network segmentation based on affected systems",
            "Deploy additional monitoring for correlated indicators",
            "Review and update threat intelligence feeds",
            "Conduct vulnerability assessment on affected systems"
        ])
        
        return recommendations
    
    def generate_forensic_report(self, incident: SecurityIncident, format_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Generate comprehensive forensic investigation report
        
        Args:
            incident: Security incident to report on
            format_type: Report format (comprehensive, executive, technical)
            
        Returns:
            Generated forensic report
        """
        report = {
            'incident_id': incident.incident_id,
            'title': incident.title,
            'report_type': format_type,
            'generated_at': datetime.utcnow(),
            'summary': {
                'status': incident.status.value,
                'severity': incident.severity,
                'confidence_score': incident.confidence_score,
                'total_indicators': len(incident.indicators),
                'affected_systems': len(incident.affected_systems),
                'timeline_events': len(incident.timeline)
            },
            'incident_details': {
                'description': incident.description,
                'first_seen': incident.first_seen,
                'last_seen': incident.last_seen,
                'duration_hours': (incident.last_seen - incident.first_seen).total_seconds() / 3600,
                'threat_actors': [actor.value for actor in incident.threat_actors],
                'attack_vectors': [vector.value for vector in incident.attack_vectors]
            },
            'technical_analysis': {
                'indicators_of_compromise': incident.indicators,
                'forensic_timeline': [asdict(event) for event in incident.timeline],
                'evidence_collection': incident.evidence,
                'impact_assessment': incident.impact_assessment
            },
            'investigation_findings': {
                'analysis_methodology': self._get_analysis_methodology(incident),
                'key_findings': self._extract_key_findings(incident),
                'attack_pattern_analysis': self._analyze_attack_patterns(incident),
                'attribution_assessment': self._assess_attribution(incident)
            },
            'recommendations': self._generate_forensic_recommendations(incident),
            'appendices': {
                'mitre_attack_mapping': self._map_mitre_techniques(incident),
                'threat_intelligence': self._enrich_with_threat_intelligence(incident),
                'forensic_artifacts': self._identify_forensic_artifacts(incident)
            }
        }
        
        return report
    
    def _get_analysis_methodology(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Document analysis methodology used"""
        return {
            'approach': 'digital_forensics_incident_response',
            'tools_used': [
                'elasticsearch_analysis',
                'log_correlation',
                'temporal_analysis',
                'pattern_recognition',
                'threat_intelligence_enrichment'
            ],
            'methodology_framework': 'NIST_SP_800-61',
            'analysis_depth': 'comprehensive' if len(incident.indicators) > 10 else 'standard'
        }
    
    def _extract_key_findings(self, incident: SecurityIncident) -> List[Dict]:
        """Extract key findings from incident analysis"""
        findings = []
        
        # High-confidence findings
        high_confidence_indicators = [i for i in incident.indicators if i.get('confidence') == 'high']
        if high_confidence_indicators:
            findings.append({
                'finding_type': 'high_confidence_iocs',
                'description': f"Found {len(high_confidence_indicators)} high-confidence indicators of compromise",
                'evidence': high_confidence_indicators[:5],
                'confidence': 'high'
            })
        
        # Temporal patterns
        if incident.confidence_score > 0.7:
            findings.append({
                'finding_type': 'coordinated_activity',
                'description': 'Evidence suggests coordinated or automated attack activity',
                'confidence': 'medium'
            })
        
        # Attack vector analysis
        if incident.attack_vectors:
            findings.append({
                'finding_type': 'attack_vectors',
                'description': f"Identified attack vectors: {', '.join([v.value for v in incident.attack_vectors])}",
                'confidence': 'high'
            })
        
        return findings
    
    def _analyze_attack_patterns(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Analyze attack patterns and techniques"""
        # Map to MITRE ATT&CK framework
        mitre_mapping = self._map_mitre_techniques(incident)
        
        # Analyze kill chain progression
        kill_chain_phases = self._analyze_kill_chain_progression(incident)
        
        # Assess attack sophistication
        sophistication_score = self._assess_attack_sophistication(incident)
        
        return {
            'mitre_attack_mapping': mitre_mapping,
            'kill_chain_analysis': kill_chain_phases,
            'sophistication_score': sophistication_score,
            'attack_pattern': self._classify_attack_pattern(incident),
            'attack_timeline': self._create_attack_timeline(incident)
        }
    
    def _assess_attribution(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Assess threat actor attribution"""
        attribution = {
            'confidence': 'low',
            'assessment_basis': [],
            'candidate_actors': [],
            'exclusions': []
        }
        
        # Base assessment on indicators
        if incident.threat_actors:
            attribution['candidate_actors'] = [actor.value for actor in incident.threat_actors]
            attribution['confidence'] = 'medium'
            attribution['assessment_basis'].append('Direct threat actor indicators')
        
        # Geographic analysis
        if incident.indicators:
            geo_indicators = [i for i in incident.indicators if 'location' in i.get('context', {})]
            if geo_indicators:
                attribution['assessment_basis'].append('Geographic indicators')
        
        # Behavior-based assessment
        if len(incident.indicators) > 20:
            attribution['confidence'] = 'high'
            attribution['assessment_basis'].append('Extensive behavioral analysis')
        
        return attribution
    
    def _generate_forensic_recommendations(self, incident: SecurityIncident) -> List[str]:
        """Generate forensic investigation recommendations"""
        recommendations = []
        
        # Immediate actions
        recommendations.extend([
            "Implement immediate containment measures",
            "Preserve forensic evidence for further analysis",
            "Monitor for continued malicious activity",
            "Update detection rules based on IOCs"
        ])
        
        # Incident-specific recommendations
        if incident.severity in ['high', 'critical']:
            recommendations.append("Escalate to incident response team")
        
        if incident.threat_actors:
            recommendations.append("Engage threat intelligence team for actor analysis")
        
        # Long-term recommendations
        recommendations.extend([
            "Conduct post-incident review and lessons learned",
            "Update security controls based on attack vectors used",
            "Enhance monitoring capabilities for similar patterns",
            "Review and update incident response procedures"
        ])
        
        return recommendations
    
    def _map_mitre_techniques(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Map incident to MITRE ATT&CK techniques"""
        # Simplified mapping based on event types
        technique_mapping = {}
        
        for event in incident.timeline:
            event_type = event.get('event_type', '')
            
            # Map event types to MITRE techniques (simplified)
            if 'login' in event_type.lower():
                technique_mapping.setdefault('initial_access', []).append('T1078 - Valid Accounts')
            elif 'exploit' in event_type.lower():
                technique_mapping.setdefault('execution', []).append('T1059 - Command and Scripting Interpreter')
            elif 'persistence' in event_type.lower():
                technique_mapping.setdefault('persistence', []).append('T1053 - Scheduled Task/Job')
        
        return technique_mapping
    
    def _enrich_with_threat_intelligence(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Enrich incident with threat intelligence data"""
        ti_enrichment = {
            'matching_threat_feeds': [],
            'threat_families': [],
            'campaign_associations': [],
            'attribution_intelligence': []
        }
        
        # Check against threat feeds (simplified)
        for indicator in incident.indicators:
            value = indicator.get('value', '')
            if value in self.threat_feeds['malicious_ips']:
                ti_enrichment['matching_threat_feeds'].append(value)
        
        return ti_enrichment
    
    def _identify_forensic_artifacts(self, incident: SecurityIncident) -> List[Dict]:
        """Identify relevant forensic artifacts"""
        artifacts = []
        
        # System artifacts
        artifacts.extend([
            {'type': 'log_files', 'location': '/var/log/', 'relevance': 'high'},
            {'type': 'memory_dumps', 'location': 'system_memory', 'relevance': 'medium'},
            {'type': 'network_connections', 'location': 'netstat_output', 'relevance': 'high'},
            {'type': 'process_list', 'location': 'ps_output', 'relevance': 'medium'}
        ])
        
        return artifacts
    
    def _analyze_kill_chain_progression(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Analyze kill chain progression for the incident"""
        phase_timeline = {}
        
        for event in incident.timeline:
            # Determine which kill chain phase this event belongs to
            # This is a simplified classification
            event_type = event.get('event_type', '').lower()
            
            if 'recon' in event_type:
                phase = 'reconnaissance'
            elif 'delivery' in event_type:
                phase = 'delivery'
            elif 'exploit' in event_type:
                phase = 'exploitation'
            elif 'install' in event_type:
                phase = 'installation'
            elif 'command' in event_type:
                phase = 'command_control'
            elif 'action' in event_type:
                phase = 'actions_objectives'
            else:
                phase = 'unknown'
            
            if phase not in phase_timeline:
                phase_timeline[phase] = []
            phase_timeline[phase].append(event)
        
        # Determine completeness
        completed_phases = [phase for phase in phase_timeline.keys() if phase != 'unknown']
        kill_chain_completeness = len(completed_phases) / len(self.kill_chain_phases)
        
        return {
            'phase_timeline': phase_timeline,
            'completed_phases': completed_phases,
            'completeness_score': kill_chain_completeness,
            'progression_assessment': 'advanced' if kill_chain_completeness > 0.7 else 'basic'
        }
    
    def _assess_attack_sophistication(self, incident: SecurityIncident) -> float:
        """Assess sophistication level of the attack"""
        score = 0.0
        
        # Base score from number of IOCs
        score += min(len(incident.indicators) / 20, 0.3)
        
        # Score from confidence
        score += incident.confidence_score * 0.4
        
        # Score from attack vectors
        score += len(incident.attack_vectors) * 0.1
        
        # Score from timeline complexity
        score += min(len(incident.timeline) / 100, 0.2)
        
        return min(score, 1.0)
    
    def _classify_attack_pattern(self, incident: SecurityIncident) -> str:
        """Classify attack pattern type"""
        # Simplified classification
        if incident.confidence_score > 0.8 and len(incident.indicators) > 15:
            return 'advanced_persistent_threat'
        elif len(incident.attack_vectors) > 2:
            return 'multi_vector_attack'
        elif incident.attack_vectors and AttackVector.SOCIAL_ENGINEERING in incident.attack_vectors:
            return 'social_engineering_attack'
        elif any('malware' in str(indicator.get('value', '')).lower() for indicator in incident.indicators):
            return 'malware_campaign'
        else:
            return 'opportunistic_attack'
    
    def _create_attack_timeline(self, incident: SecurityIncident) -> List[Dict]:
        """Create detailed attack timeline"""
        timeline = []
        
        for i, event in enumerate(incident.timeline, 1):
            timeline.append({
                'sequence': i,
                'timestamp': event.get('timestamp'),
                'event_type': event.get('event_type'),
                'description': event.get('description'),
                'phase': self._determine_kill_chain_phase(event),
                'evidence_strength': event.get('confidence', 0.0)
            })
        
        return timeline
    
    def _determine_kill_chain_phase(self, event: Dict) -> str:
        """Determine kill chain phase for an event"""
        event_type = event.get('event_type', '').lower()
        
        for phase in self.kill_chain_phases:
            if phase in event_type:
                return phase
        
        return 'unknown'
