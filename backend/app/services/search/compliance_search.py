"""
Compliance Search Service for Regulatory Compliance
Provides specialized searching and analysis for regulatory compliance requirements
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..elk import ElasticsearchClient

logger = logging.getLogger(__name__)


class Regulation(Enum):
    """Supported regulatory frameworks"""
    GDPR = "GDPR"
    SOX = "SOX"
    PCI_DSS = "PCI-DSS"
    HIPAA = "HIPAA"
    ISO27001 = "ISO27001"
    NIST_CSF = "NIST-CSF"
    CCPA = "CCPA"
    FEDRAMP = "FEDRAMP"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"
    EXEMPT = "exempt"
    PENDING = "pending"


class ControlCategory(Enum):
    """Compliance control categories"""
    ACCESS_CONTROL = "access_control"
    AUDIT_LOGGING = "audit_logging"
    DATA_PROTECTION = "data_protection"
    INCIDENT_RESPONSE = "incident_response"
    RISK_MANAGEMENT = "risk_management"
    VENDOR_MANAGEMENT = "vendor_management"
    PHYSICAL_SECURITY = "physical_security"
    BUSINESS_CONTINUITY = "business_continuity"


@dataclass
class ComplianceSearchQuery:
    """Advanced compliance search query"""
    regulation: Regulation
    control_category: ControlCategory = None
    status_filter: List[ComplianceStatus] = None
    severity_filter: List[str] = None
    date_range: Tuple[datetime, datetime] = None
    requirement_ids: List[str] = None
    assessor_filter: List[str] = None
    evidence_required: bool = None
    remediation_required: bool = None
    score_threshold: float = None
    page_size: int = 100
    include_details: bool = True


@dataclass
class ComplianceGap:
    """Compliance gap analysis"""
    control_id: str
    regulation: str
    requirement: str
    gap_description: str
    severity: str
    remediation_effort: str
    estimated_cost: str
    timeline: str
    risk_impact: str
    dependencies: List[str]


class ComplianceSearchService:
    """Specialized service for compliance search and analysis"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Initialize compliance search service
        
        Args:
            es_client: Elasticsearch client
        """
        self.es_client = es_client
        
        # Regulatory frameworks and their requirements
        self.regulation_frameworks = {
            Regulation.GDPR: {
                'name': 'General Data Protection Regulation',
                'controls': {
                    ControlCategory.ACCESS_CONTROL: [
                        'art-25', 'art-28', 'art-32', 'art-33', 'art-34'
                    ],
                    ControlCategory.AUDIT_LOGGING: [
                        'art-24', 'art-30', 'art-33', 'art-34'
                    ],
                    ControlCategory.DATA_PROTECTION: [
                        'art-5', 'art-17', 'art-20', 'art-21', 'art-25'
                    ]
                },
                'required_evidence': [
                    'data_processing_purpose',
                    'legal_basis',
                    'consent_records',
                    'data_retention_policy',
                    'breach_notification_procedure'
                ]
            },
            Regulation.SOX: {
                'name': 'Sarbanes-Oxley Act',
                'controls': {
                    ControlCategory.ACCESS_CONTROL: [
                        '302', '404', '906'
                    ],
                    ControlCategory.AUDIT_LOGGING: [
                        '302', '404', '906'
                    ],
                    ControlCategory.DATA_PROTECTION: [
                        '302', '404', '906'
                    ]
                },
                'required_evidence': [
                    'access_control_matrix',
                    'segregation_of_duties',
                    'change_management_procedures',
                    'audit_trail_logs',
                    'financial_system_controls'
                ]
            },
            Regulation.PCI_DSS: {
                'name': 'Payment Card Industry Data Security Standard',
                'controls': {
                    ControlCategory.ACCESS_CONTROL: [
                        'req-7', 'req-8', 'req-9'
                    ],
                    ControlCategory.AUDIT_LOGGING: [
                        'req-10', 'req-12'
                    ],
                    ControlCategory.DATA_PROTECTION: [
                        'req-3', 'req-4', 'req-6'
                    ]
                },
                'required_evidence': [
                    'cardholder_data_inventory',
                    'encryption_procedures',
                    'vulnerability_scans',
                    'security_incidents_log',
                    'compliance_validation'
                ]
            }
        }
        
        # Risk scoring matrix
        self.risk_matrix = {
            ('high', 'critical'): {'score': 0.1, 'priority': 'urgent'},
            ('high', 'high'): {'score': 0.3, 'priority': 'high'},
            ('medium', 'high'): {'score': 0.5, 'priority': 'medium'},
            ('medium', 'medium'): {'score': 0.7, 'priority': 'medium'},
            ('low', 'medium'): {'score': 0.8, 'priority': 'low'},
            ('low', 'low'): {'score': 0.9, 'priority': 'low'}
        }
    
    def search_compliance_logs(self, query: ComplianceSearchQuery) -> Dict[str, Any]:
        """
        Search compliance logs with regulatory filtering
        
        Args:
            query: Compliance search query
            
        Returns:
            Search results with compliance analysis
        """
        try:
            # Build Elasticsearch query
            search_query = self._build_compliance_query(query)
            
            # Add compliance-specific aggregations
            aggregations = {
                'compliance_overview': {
                    'terms': {
                        'field': 'regulation',
                        'size': 10
                    }
                },
                'control_categories': {
                    'terms': {
                        'field': 'control',
                        'size': 50
                    }
                },
                'status_distribution': {
                    'terms': {
                        'field': 'status',
                        'size': 10
                    }
                },
                'score_analysis': {
                    'avg': {
                        'field': 'compliance_score'
                    }
                },
                'compliance_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1w'
                    }
                },
                'severity_breakdown': {
                    'terms': {
                        'field': 'severity',
                        'size': 10
                    }
                }
            }
            
            # Execute search
            response = self.es_client.advanced_search(
                index_types=['compliance_logs'],
                query=search_query,
                aggregations=aggregations,
                size=query.page_size
            )
            
            # Process results
            results = self._process_compliance_results(response, query)
            
            logger.info(f"Compliance search completed: {len(results['controls'])} controls found")
            return results
            
        except Exception as e:
            logger.error(f"Compliance search failed: {e}")
            raise
    
    def _build_compliance_query(self, query: ComplianceSearchQuery) -> Dict:
        """Build Elasticsearch query from compliance search criteria"""
        must_conditions = []
        filter_conditions = []
        
        # Regulation filter
        must_conditions.append({
            'term': {'regulation': query.regulation.value}
        })
        
        # Control category filter
        if query.control_category:
            must_conditions.append({
                'term': {'control_category': query.control_category.value}
            })
        
        # Status filter
        if query.status_filter:
            status_values = [status.value for status in query.status_filter]
            must_conditions.append({
                'terms': {'status': status_values}
            })
        
        # Severity filter
        if query.severity_filter:
            must_conditions.append({
                'terms': {'severity': query.severity_filter}
            })
        
        # Date range filter
        if query.date_range:
            start_time, end_time = query.date_range
            filter_conditions.append({
                'range': {
                    'timestamp': {
                        'gte': start_time,
                        'lte': end_time
                    }
                }
            })
        
        # Requirement IDs filter
        if query.requirement_ids:
            must_conditions.append({
                'terms': {'requirement': query.requirement_ids}
            })
        
        # Assessor filter
        if query.assessor_filter:
            must_conditions.append({
                'terms': {'assessor': query.assessor_filter}
            })
        
        # Evidence required filter
        if query.evidence_required is not None:
            must_conditions.append({
                'exists': {'field': 'evidence'} if query.evidence_required
                else {
                    'bool': {
                        'must_not': {'exists': {'field': 'evidence'}}
                    }
                }
            })
        
        # Remediation required filter
        if query.remediation_required is not None:
            must_conditions.append({
                'exists': {'field': 'remediation'} if query.remediation_required
                else {
                    'bool': {
                        'must_not': {'exists': {'field': 'remediation'}}
                    }
                }
            })
        
        # Score threshold filter
        if query.score_threshold is not None:
            filter_conditions.append({
                'range': {
                    'compliance_score': {
                        'lte': query.score_threshold
                    }
                }
            })
        
        # Build final query
        query_dict = {'bool': {'must': must_conditions, 'filter': filter_conditions}}
        
        # Default to match_all if no specific filters
        if not must_conditions and not filter_conditions:
            query_dict = {'match_all': {}}
        
        return query_dict
    
    def _process_compliance_results(self, response: Dict, query: ComplianceSearchQuery) -> Dict:
        """Process compliance search results"""
        controls = []
        for hit in response['hits']['hits']:
            control = hit['_source']
            
            processed_control = {
                'control_id': control.get('control'),
                'requirement': control.get('requirement'),
                'regulation': control.get('regulation'),
                'status': control.get('status'),
                'severity': control.get('severity'),
                'compliance_score': control.get('compliance_score', 0),
                'assessor': control.get('assessor'),
                'audit_period': control.get('audit_period'),
                'evidence': control.get('evidence') if query.include_details else None,
                'findings': control.get('findings') if query.include_details else None,
                'remediation': control.get('remediation') if query.include_details else None,
                'timestamp': control.get('timestamp')
            }
            controls.append(processed_control)
        
        # Process aggregations
        aggregations = response.get('aggregations', {})
        
        analysis = {
            'total_controls': len(controls),
            'compliance_score': aggregations.get('score_analysis', {}).get('value', 0),
            'status_breakdown': self._analyze_status_breakdown(aggregations),
            'regulatory_overview': self._analyze_regulatory_overview(aggregations),
            'severity_distribution': self._analyze_severity_distribution(aggregations),
            'compliance_trend': self._analyze_compliance_trend(aggregations),
            'gaps_analysis': self._identify_compliance_gaps(controls),
            'recommendations': self._generate_compliance_recommendations(controls, query.regulation)
        }
        
        return {
            'controls': controls,
            'analysis': analysis,
            'aggregations': aggregations,
            'total': response['hits']['total']['value']
        }
    
    def _analyze_status_breakdown(self, aggregations: Dict) -> Dict:
        """Analyze compliance status distribution"""
        status_buckets = aggregations.get('status_distribution', {}).get('buckets', [])
        
        breakdown = {}
        for bucket in status_buckets:
            status = bucket['key']
            count = bucket['doc_count']
            breakdown[status] = {
                'count': count,
                'percentage': 0  # Will be calculated
            }
        
        total = sum(item['count'] for item in breakdown.values())
        if total > 0:
            for status in breakdown:
                breakdown[status]['percentage'] = (breakdown[status]['count'] / total) * 100
        
        return breakdown
    
    def _analyze_regulatory_overview(self, aggregations: Dict) -> Dict:
        """Analyze regulatory framework distribution"""
        regulation_buckets = aggregations.get('compliance_overview', {}).get('buckets', [])
        
        overview = {}
        for bucket in regulation_buckets:
            regulation = bucket['key']
            count = bucket['doc_count']
            overview[regulation] = count
        
        return overview
    
    def _analyze_severity_distribution(self, aggregations: Dict) -> Dict:
        """Analyze severity level distribution"""
        severity_buckets = aggregations.get('severity_breakdown', {}).get('buckets', [])
        
        distribution = {}
        for bucket in severity_buckets:
            severity = bucket['key']
            count = bucket['doc_count']
            distribution[severity] = count
        
        return distribution
    
    def _analyze_compliance_trend(self, aggregations: Dict) -> List[Dict]:
        """Analyze compliance trend over time"""
        timeline_buckets = aggregations.get('compliance_timeline', {}).get('buckets', [])
        
        trend = []
        for bucket in timeline_buckets:
            trend.append({
                'timestamp': bucket['key'],
                'control_count': bucket['doc_count'],
                'key_as_string': bucket.get('key_as_string', '')
            })
        
        return trend
    
    def _identify_compliance_gaps(self, controls: List[Dict]) -> List[ComplianceGap]:
        """Identify compliance gaps in controls"""
        gaps = []
        
        # Find non-compliant controls
        non_compliant = [c for c in controls if c.get('status') in ['non_compliant', 'partially_compliant']]
        
        for control in non_compliant:
            gap = ComplianceGap(
                control_id=control.get('control_id', ''),
                regulation=control.get('regulation', ''),
                requirement=control.get('requirement', ''),
                gap_description=f"Control {control.get('control_id')} is {control.get('status')}",
                severity=control.get('severity', 'medium'),
                remediation_effort=self._estimate_remediation_effort(control),
                estimated_cost=self._estimate_remediation_cost(control),
                timeline=self._estimate_remediation_timeline(control),
                risk_impact=self._assess_risk_impact(control),
                dependencies=self._identify_dependencies(control)
            )
            gaps.append(gap)
        
        return gaps
    
    def _estimate_remediation_effort(self, control: Dict) -> str:
        """Estimate remediation effort for a control"""
        severity = control.get('severity', 'medium')
        
        effort_mapping = {
            'low': '1-2 weeks',
            'medium': '2-4 weeks',
            'high': '1-3 months',
            'critical': '3-6 months'
        }
        
        return effort_mapping.get(severity, '2-4 weeks')
    
    def _estimate_remediation_cost(self, control: Dict) -> str:
        """Estimate remediation cost for a control"""
        severity = control.get('severity', 'medium')
        
        cost_mapping = {
            'low': '$1,000 - $5,000',
            'medium': '$5,000 - $25,000',
            'high': '$25,000 - $100,000',
            'critical': '$100,000+'
        }
        
        return cost_mapping.get(severity, '$5,000 - $25,000')
    
    def _estimate_remediation_timeline(self, control: Dict) -> str:
        """Estimate remediation timeline for a control"""
        return self._estimate_remediation_effort(control)
    
    def _assess_risk_impact(self, control: Dict) -> str:
        """Assess risk impact of a compliance gap"""
        severity = control.get('severity', 'medium')
        status = control.get('status', '')
        
        if severity == 'critical' or status == 'non_compliant':
            return 'High - Immediate action required'
        elif severity == 'high':
            return 'Medium - Action required within 30 days'
        else:
            return 'Low - Monitor and address within quarter'
    
    def _identify_dependencies(self, control: Dict) -> List[str]:
        """Identify dependencies for remediation"""
        # This is a simplified implementation
        # In practice, this would analyze control relationships
        return ['security_team_approval', 'budget_approval', 'technical_implementation']
    
    def _generate_compliance_recommendations(self, controls: List[Dict], regulation: Regulation) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        # Get framework-specific recommendations
        framework = self.regulation_frameworks.get(regulation)
        if framework:
            recommendations.extend(framework.get('recommendations', []))
        
        # Analyze current status
        non_compliant_count = len([c for c in controls if c.get('status') == 'non_compliant'])
        partially_compliant_count = len([c for c in controls if c.get('status') == 'partially_compliant'])
        
        if non_compliant_count > 0:
            recommendations.append(f"Address {non_compliant_count} non-compliant controls immediately")
        
        if partially_compliant_count > 5:
            recommendations.append("Prioritize completing partially compliant controls")
        
        # Score-based recommendations
        avg_score = sum(c.get('compliance_score', 0) for c in controls) / len(controls) if controls else 0
        if avg_score < 70:
            recommendations.append("Overall compliance score is below threshold - implement comprehensive improvement plan")
        elif avg_score < 85:
            recommendations.append("Compliance score can be improved - focus on high-impact gaps")
        
        # General recommendations
        recommendations.extend([
            "Schedule regular compliance assessments",
            "Implement automated compliance monitoring",
            "Maintain detailed evidence documentation",
            "Train staff on compliance requirements"
        ])
        
        return recommendations
    
    def assess_regulatory_readiness(self, regulation: Regulation, assessment_date: datetime = None) -> Dict[str, Any]:
        """
        Assess regulatory readiness for a specific framework
        
        Args:
            regulation: Regulatory framework to assess
            assessment_date: Assessment date (defaults to now)
            
        Returns:
            Regulatory readiness assessment
        """
        assessment_date = assessment_date or datetime.utcnow()
        
        # Get framework details
        framework = self.regulation_frameworks.get(regulation)
        if not framework:
            raise ValueError(f"Regulation framework not supported: {regulation}")
        
        # Search for all controls related to this regulation
        criteria = ComplianceSearchQuery(
            regulation=regulation,
            date_range=(assessment_date - timedelta(days=365), assessment_date),
            page_size=1000
        )
        
        results = self.search_compliance_logs(criteria)
        
        # Calculate readiness metrics
        total_controls = len(results['controls'])
        compliant_controls = len([c for c in results['controls'] if c.get('status') == 'compliant'])
        readiness_percentage = (compliant_controls / total_controls) * 100 if total_controls > 0 else 0
        
        # Identify gaps
        critical_gaps = [gap for gap in results['analysis']['gaps_analysis'] if gap.severity == 'critical']
        high_gaps = [gap for gap in results['analysis']['gaps_analysis'] if gap.severity == 'high']
        
        # Generate readiness assessment
        readiness_assessment = {
            'regulation': regulation.value,
            'framework_name': framework['name'],
            'assessment_date': assessment_date,
            'readiness_score': readiness_percentage,
            'readiness_level': self._determine_readiness_level(readiness_percentage),
            'total_controls': total_controls,
            'compliant_controls': compliant_controls,
            'non_compliant_controls': len([c for c in results['controls'] if c.get('status') == 'non_compliant']),
            'partially_compliant_controls': len([c for c in results['controls'] if c.get('status') == 'partially_compliant']),
            'critical_gaps': len(critical_gaps),
            'high_priority_gaps': len(high_gaps),
            'required_controls': framework['controls'],
            'evidence_requirements': framework['required_evidence'],
            'recommendations': results['analysis']['recommendations'],
            'remediation_roadmap': self._create_remediation_roadmap(results['analysis']['gaps_analysis']),
            'certification_readiness': self._assess_certification_readiness(readiness_percentage, len(critical_gaps))
        }
        
        return readiness_assessment
    
    def _determine_readiness_level(self, readiness_score: float) -> str:
        """Determine readiness level based on score"""
        if readiness_score >= 95:
            return 'Certified Ready'
        elif readiness_score >= 85:
            return 'Audit Ready'
        elif readiness_score >= 70:
            return 'Near Ready'
        elif readiness_score >= 50:
            return 'Partially Ready'
        else:
            return 'Not Ready'
    
    def _create_remediation_roadmap(self, gaps: List[ComplianceGap]) -> List[Dict]:
        """Create remediation roadmap for compliance gaps"""
        roadmap = []
        
        # Sort gaps by severity and priority
        severity_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
        sorted_gaps = sorted(gaps, key=lambda g: severity_order.get(g.severity, 5))
        
        current_phase = 0
        current_quarter = 1
        
        for gap in sorted_gaps:
            # Assign to phases based on severity
            if gap.severity == 'critical':
                phase = 1
                quarter = 1
            elif gap.severity == 'high':
                phase = 2 if current_phase < 2 else 3
                quarter = 1 if quarter <= 2 else 2
            else:
                phase = 3
                quarter = 2 if current_quarter == 1 else 3
            
            roadmap.append({
                'phase': phase,
                'quarter': quarter,
                'control_id': gap.control_id,
                'requirement': gap.requirement,
                'effort': gap.remediation_effort,
                'timeline': gap.timeline,
                'priority': gap.severity,
                'dependencies': gap.dependencies
            })
            
            current_phase = max(current_phase, phase)
            current_quarter = max(current_quarter, quarter)
        
        return roadmap
    
    def _assess_certification_readiness(self, readiness_score: float, critical_gaps: int) -> str:
        """Assess certification readiness"""
        if readiness_score >= 95 and critical_gaps == 0:
            return 'Ready for Certification'
        elif readiness_score >= 85 and critical_gaps <= 2:
            return 'Ready for Pre-Audit'
        elif readiness_score >= 70:
            return 'Preparation Phase'
        else:
            return 'Gap Remediation Required'
    
    def generate_compliance_report(self, 
                                 regulation: Regulation,
                                 report_type: str = 'executive',
                                 time_period: timedelta = timedelta(days=90)) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report
        
        Args:
            regulation: Regulatory framework
            report_type: Type of report (executive, technical, audit)
            time_period: Time period to analyze
            
        Returns:
            Generated compliance report
        """
        # Get compliance data
        end_date = datetime.utcnow()
        start_date = end_date - time_period
        
        criteria = ComplianceSearchQuery(
            regulation=regulation,
            date_range=(start_date, end_date),
            page_size=1000,
            include_details=True
        )
        
        results = self.search_compliance_logs(criteria)
        
        # Generate report based on type
        if report_type == 'executive':
            report = self._generate_executive_report(results, regulation, time_period)
        elif report_type == 'technical':
            report = self._generate_technical_report(results, regulation, time_period)
        elif report_type == 'audit':
            report = self._generate_audit_report(results, regulation, time_period)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        return report
    
    def _generate_executive_report(self, results: Dict, regulation: Regulation, time_period: timedelta) -> Dict[str, Any]:
        """Generate executive-level compliance report"""
        analysis = results['analysis']
        
        return {
            'report_type': 'executive',
            'regulation': regulation.value,
            'period': f"{time_period.days} days",
            'summary': {
                'overall_score': analysis['compliance_score'],
                'status': 'Compliant' if analysis['compliance_score'] >= 85 else 'Non-Compliant',
                'total_controls': analysis['total_controls'],
                'critical_issues': len([gap for gap in analysis['gaps_analysis'] if gap.severity == 'critical'])
            },
            'key_metrics': {
                'controls_audited': analysis['total_controls'],
                'compliance_rate': f"{analysis['compliance_score']:.1f}%",
                'gaps_identified': len(analysis['gaps_analysis']),
                'recommendations': len(analysis['recommendations'])
            },
            'executive_summary': self._create_executive_summary(analysis, regulation),
            'recommendations': analysis['recommendations'][:5],  # Top 5 recommendations
            'next_steps': self._generate_next_steps(analysis['gaps_analysis']),
            'generated_at': datetime.utcnow()
        }
    
    def _generate_technical_report(self, results: Dict, regulation: Regulation, time_period: timedelta) -> Dict[str, Any]:
        """Generate technical compliance report"""
        analysis = results['analysis']
        controls = results['controls']
        
        return {
            'report_type': 'technical',
            'regulation': regulation.value,
            'period': f"{time_period.days} days",
            'detailed_analysis': {
                'control_breakdown': analysis['status_breakdown'],
                'severity_distribution': analysis['severity_distribution'],
                'compliance_trends': analysis['compliance_trend'],
                'regulatory_overview': analysis['regulatory_overview']
            },
            'technical_findings': {
                'total_controls': analysis['total_controls'],
                'detailed_gaps': [self._serialize_gap(gap) for gap in analysis['gaps_analysis']],
                'control_details': controls[:50]  # First 50 controls
            },
            'technical_recommendations': analysis['recommendations'],
            'implementation_details': self._generate_implementation_details(analysis['gaps_analysis']),
            'generated_at': datetime.utcnow()
        }
    
    def _generate_audit_report(self, results: Dict, regulation: Regulation, time_period: timedelta) -> Dict[str, Any]:
        """Generate audit-focused compliance report"""
        analysis = results['analysis']
        controls = results['controls']
        
        return {
            'report_type': 'audit',
            'regulation': regulation.value,
            'period': f"{time_period.days} days",
            'audit_scope': {
                'total_controls_reviewed': analysis['total_controls'],
                'audit_methodology': 'Risk-based control testing',
                'sample_size': min(len(controls), 100),
                'testing_period': time_period.days
            },
            'audit_findings': {
                'compliant_controls': len([c for c in controls if c.get('status') == 'compliant']),
                'non_compliant_controls': len([c for c in controls if c.get('status') == 'non_compliant']),
                'partially_compliant': len([c for c in controls if c.get('status') == 'partially_compliant']),
                'critical_gaps': [self._serialize_gap(gap) for gap in analysis['gaps_analysis'] if gap.severity == 'critical']
            },
            'evidence_tracking': self._analyze_evidence_tracking(controls),
            'audit_recommendations': analysis['recommendations'],
            'compliance_certification': self._assess_certification_readiness(analysis['compliance_score'], len(analysis['gaps_analysis'])),
            'generated_at': datetime.utcnow()
        }
    
    def _create_executive_summary(self, analysis: Dict, regulation: Regulation) -> str:
        """Create executive summary text"""
        total_controls = analysis['total_controls']
        compliance_score = analysis['compliance_score']
        gaps_count = len(analysis['gaps_analysis'])
        
        summary = f"""
        Compliance assessment for {regulation.value} shows a {compliance_score:.1f}% compliance score across {total_controls} controls. 
        {gaps_count} gaps have been identified that require attention. 
        
        The overall compliance posture is {'Strong' if compliance_score >= 85 else 'Needs Improvement' if compliance_score >= 70 else 'Critical'}.
        """
        
        return summary.strip()
    
    def _generate_next_steps(self, gaps: List[ComplianceGap]) -> List[str]:
        """Generate immediate next steps"""
        critical_gaps = [gap for gap in gaps if gap.severity == 'critical']
        
        steps = []
        if critical_gaps:
            steps.append("Immediately address critical compliance gaps")
            steps.append("Implement emergency remediation procedures for high-risk controls")
        
        steps.extend([
            "Schedule stakeholder review of compliance assessment",
            "Allocate budget and resources for gap remediation",
            "Establish compliance monitoring and reporting cadence",
            "Update compliance policies and procedures"
        ])
        
        return steps
    
    def _serialize_gap(self, gap: ComplianceGap) -> Dict:
        """Serialize compliance gap for reporting"""
        return {
            'control_id': gap.control_id,
            'requirement': gap.requirement,
            'gap_description': gap.gap_description,
            'severity': gap.severity,
            'remediation_effort': gap.remediation_effort,
            'estimated_cost': gap.estimated_cost,
            'timeline': gap.timeline,
            'risk_impact': gap.risk_impact,
            'dependencies': gap.dependencies
        }
    
    def _generate_implementation_details(self, gaps: List[ComplianceGap]) -> Dict:
        """Generate implementation details for technical report"""
        return {
            'remediation_phases': self._create_remediation_roadmap(gaps),
            'resource_requirements': self._calculate_resource_requirements(gaps),
            'timeline_projections': self._generate_timeline_projections(gaps),
            'risk_mitigation': self._generate_risk_mitigation_plans(gaps)
        }
    
    def _calculate_resource_requirements(self, gaps: List[ComplianceGap]) -> Dict:
        """Calculate resource requirements for gap remediation"""
        total_cost = 0
        total_effort = 0
        resource_breakdown = {
            'security_engineers': 0,
            'compliance_officers': 0,
            'developers': 0,
            'project_managers': 0
        }
        
        for gap in gaps:
            # Simplified resource calculation
            if gap.severity == 'critical':
                total_cost += 50000
                total_effort += 120  # days
                resource_breakdown['security_engineers'] += 2
                resource_breakdown['compliance_officers'] += 1
            elif gap.severity == 'high':
                total_cost += 25000
                total_effort += 60
                resource_breakdown['developers'] += 2
                resource_breakdown['project_managers'] += 1
        
        return {
            'estimated_cost': total_cost,
            'total_effort_days': total_effort,
            'resource_breakdown': resource_breakdown,
            'recommended_team_size': sum(resource_breakdown.values())
        }
    
    def _generate_timeline_projections(self, gaps: List[ComplianceGap]) -> Dict:
        """Generate timeline projections"""
        return {
            'immediate_actions': '0-30 days',
            'short_term_remediation': '30-90 days',
            'medium_term_implementation': '90-180 days',
            'long_term_optimization': '180-365 days'
        }
    
    def _generate_risk_mitigation_plans(self, gaps: List[ComplianceGap]) -> List[Dict]:
        """Generate risk mitigation plans"""
        plans = []
        
        for gap in gaps:
            plan = {
                'control_id': gap.control_id,
                'risk_level': gap.severity,
                'mitigation_strategy': f"Implement {gap.requirement} controls",
                'timeline': gap.timeline,
                'success_metrics': f"Achieve {gap.severity} severity rating",
                'contingency_plans': ['Manual controls', 'Compensating controls']
            }
            plans.append(plan)
        
        return plans
    
    def _analyze_evidence_tracking(self, controls: List[Dict]) -> Dict:
        """Analyze evidence tracking completeness"""
        controls_with_evidence = [c for c in controls if c.get('evidence')]
        controls_with_findings = [c for c in controls if c.get('findings')]
        controls_with_remediation = [c for c in controls if c.get('remediation')]
        
        total_controls = len(controls)
        
        return {
            'evidence_completeness': {
                'with_evidence': len(controls_with_evidence),
                'without_evidence': total_controls - len(controls_with_evidence),
                'percentage': (len(controls_with_evidence) / total_controls) * 100 if total_controls > 0 else 0
            },
            'findings_documentation': {
                'with_findings': len(controls_with_findings),
                'without_findings': total_controls - len(controls_with_findings),
                'percentage': (len(controls_with_findings) / total_controls) * 100 if total_controls > 0 else 0
            },
            'remediation_tracking': {
                'with_remediation': len(controls_with_remediation),
                'without_remediation': total_controls - len(controls_with_remediation),
                'percentage': (len(controls_with_remediation) / total_controls) * 100 if total_controls > 0 else 0
            }
        }
