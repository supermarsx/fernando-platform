"""
Compliance Logger Implementation

Provides specialized logging for regulatory compliance (GDPR, SOX, PCI-DSS, etc.)
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from sqlalchemy.orm import Session
from app.models.logging import ComplianceLog, DataSubjectRecord, RetentionPolicy
from app.db.session import SessionLocal
from .structured_logger import structured_logger, LogCategory


class ComplianceRegulation(Enum):
    """Supported compliance regulations"""
    GDPR = "gdpr"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    CCPA = "ccpa"
    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"


class DataSubjectType(Enum):
    """Types of data subjects"""
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    PARTNER = "partner"
    CONTRACTOR = "contractor"
    PROSPECT = "prospect"
    SUPPLIER = "supplier"


class DataProcessingPurpose(Enum):
    """GDPR data processing purposes"""
    CONSENT = "consent"
    CONTRACT_PERFORMANCE = "contract_performance"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategory(Enum):
    """Categories of personal data"""
    IDENTITY = "identity"
    CONTACT = "contact"
    FINANCIAL = "financial"
    HEALTH = "health"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    BIOMETRIC = "biometric"
    LOCATION = "location"


class RightToBeForgottenStatus(Enum):
    """Status of right to be forgotten requests"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"


class ComplianceLogger:
    """Enterprise compliance logger for regulatory requirements"""
    
    def __init__(self):
        self.structured_logger = structured_logger.with_context(
            category="compliance"
        )
    
    def log_gdpr_data_access(self,
                           data_subject_id: str,
                           operation: str,  # read, update, delete, export
                           data_types: List[str],
                           lawful_basis: DataProcessingPurpose,
                           processing_purpose: str,
                           user_id: Optional[str] = None,
                           system_processing: bool = False) -> str:
        """
        Log GDPR Article 6 compliance data access
        
        Args:
            data_subject_id: ID of the data subject (never log actual personal data)
            operation: Type of operation performed
            data_types: Categories of data accessed
            lawful_basis: GDPR Article 6 lawful basis
            processing_purpose: Specific purpose for processing
            user_id: ID of user performing the access
            system_processing: Whether this is automated system processing
        """
        
        compliance_log_id = self._generate_compliance_id()
        
        # Log the data access
        self.structured_logger.data_access(
            message=f"GDPR data access logged for compliance",
            operation=operation,
            data_types=data_types,
            lawful_basis=lawful_basis.value,
            processing_purpose=processing_purpose,
            system_processing=system_processing,
            compliance_log_id=compliance_log_id,
            regulation="GDPR",
            article_reference="Article 6, Article 30"
        )
        
        # Store compliance record
        self._store_compliance_record(
            regulation=ComplianceRegulation.GDPR,
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            operation=operation,
            lawful_basis=lawful_basis.value,
            processing_purpose=processing_purpose,
            data_categories=data_types,
            user_id=user_id,
            article_references=["Article 6", "Article 30"],
            retention_period_days=2555  # 7 years for GDPR compliance
        )
        
        return compliance_log_id
    
    def log_gdpr_consent(self,
                        data_subject_id: str,
                        consent_type: str,
                        consent_status: str,  # given, withdrawn, expired
                        data_categories: List[str],
                        purpose_description: str,
                        user_id: Optional[str] = None,
                        consent_method: str = "online_form") -> str:
        """Log GDPR consent management (Article 7)"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"GDPR consent logged: {consent_type}",
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            consent_type=consent_type,
            consent_status=consent_status,
            data_categories=data_categories,
            purpose_description=purpose_description,
            consent_method=consent_method,
            regulation="GDPR",
            article_reference="Article 7"
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.GDPR,
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            operation=f"consent_{consent_status}",
            lawful_basis=DataProcessingPurpose.CONSENT.value,
            processing_purpose=purpose_description,
            data_categories=data_categories,
            user_id=user_id,
            article_references=["Article 7"],
            retention_period_days=2555
        )
        
        return compliance_log_id
    
    def log_gdpr_data_portability(self,
                                 data_subject_id: str,
                                 data_types: List[str],
                                 export_format: str,  # json, xml, csv
                                 delivery_method: str,  # email, download, api
                                 user_id: Optional[str] = None) -> str:
        """Log GDPR Article 20 data portability requests"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"GDPR data portability request processed",
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            data_types=data_types,
            export_format=export_format,
            delivery_method=delivery_method,
            regulation="GDPR",
            article_reference="Article 20"
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.GDPR,
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            operation="data_export_portability",
            lawful_basis=DataProcessingPurpose.CONTRACT_PERFORMANCE.value,
            processing_purpose="Data portability request",
            data_categories=data_types,
            user_id=user_id,
            article_references=["Article 20"],
            retention_period_days=2555
        )
        
        return compliance_log_id
    
    def log_right_to_be_forgotten(self,
                                 data_subject_id: str,
                                 request_reason: str,
                                 data_categories: List[str],
                                 status: RightToBeForgottenStatus,
                                 processing_steps: Optional[List[str]] = None,
                                 user_id: Optional[str] = None) -> str:
        """Log GDPR Article 17 right to be forgotten requests"""
        
        compliance_log_id = self._generate_compliance_id()
        
        # Store data subject record for tracking
        self._store_data_subject_record(
            data_subject_id=data_subject_id,
            request_type="right_to_be_forgotten",
            request_reason=request_reason,
            status=status.value,
            processing_steps=processing_steps or [],
            user_id=user_id
        )
        
        self.structured_logger.compliance(
            f"GDPR right to be forgotten: {status.value}",
            compliance_log_id=compliance_log_id,
            data_subject_id=data_subject_id,
            request_reason=request_reason,
            data_categories=data_categories,
            status=status.value,
            processing_steps=processing_steps,
            regulation="GDPR",
            article_reference="Article 17"
        )
        
        return compliance_log_id
    
    def log_sox_compliance(self,
                          control_id: str,
                          control_description: str,
                          test_date: datetime,
                          tester_id: str,
                          test_result: str,  # pass, fail, warning
                          findings: Optional[List[str]] = None,
                          remediation_actions: Optional[List[str]] = None) -> str:
        """Log SOX compliance controls testing"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"SOX control test: {control_id}",
            compliance_log_id=compliance_log_id,
            control_id=control_id,
            control_description=control_description,
            test_date=test_date.isoformat(),
            tester_id=tester_id,
            test_result=test_result,
            findings=findings,
            remediation_actions=remediation_actions,
            regulation="SOX",
            control_framework="COSO"
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.SOX,
            compliance_log_id=compliance_log_id,
            data_subject_id=tester_id,  # SOX tracks internal users
            operation=f"control_test_{test_result}",
            lawful_basis="legal_obligation",
            processing_purpose=f"SOX compliance control testing: {control_description}",
            data_categories=["operational"],
            user_id=tester_id,
            article_references=[f"Control {control_id}"],
            retention_period_days=2920  # 8 years for SOX
        )
        
        return compliance_log_id
    
    def log_pci_dss_compliance(self,
                              requirement: str,
                              validation_method: str,  # scan, assessment, attestation
                              validation_date: datetime,
                              validator_id: str,
                              result: str,  # compliant, non_compliant, partially_compliant
                              findings: Optional[List[str]] = None) -> str:
        """Log PCI-DSS compliance validation"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"PCI-DSS validation: {requirement}",
            compliance_log_id=compliance_log_id,
            requirement=requirement,
            validation_method=validation_method,
            validation_date=validation_date.isoformat(),
            validator_id=validator_id,
            result=result,
            findings=findings,
            regulation="PCI-DSS",
            requirement_id=requirement
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.PCI_DSS,
            compliance_log_id=compliance_log_id,
            data_subject_id=validator_id,
            operation=f"pci_validation_{result}",
            lawful_basis="legal_obligation",
            processing_purpose=f"PCI-DSS requirement {requirement} validation",
            data_categories=["payment_card"],
            user_id=validator_id,
            article_references=[f"PCI-DSS {requirement}"],
            retention_period_days=2555  # 7 years for PCI-DSS
        )
        
        return compliance_log_id
    
    def log_data_breach_notification(self,
                                   incident_id: str,
                                   breach_type: str,  # unauthorized_access, accidental_disclosure, system_compromise
                                   affected_data_types: List[str],
                                   affected_individuals: int,
                                   discovery_date: datetime,
                                   notification_date: Optional[datetime] = None,
                                   notification_method: Optional[str] = None,
                                   regulator_notified: bool = False) -> str:
        """Log data breach notifications for regulatory compliance"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"Data breach notification logged",
            compliance_log_id=compliance_log_id,
            incident_id=incident_id,
            breach_type=breach_type,
            affected_data_types=affected_data_types,
            affected_individuals=affected_individuals,
            discovery_date=discovery_date.isoformat(),
            notification_date=notification_date.isoformat() if notification_date else None,
            notification_method=notification_method,
            regulator_notified=regulator_notified,
            regulation="GDPR",
            article_reference="Articles 33, 34",
            severity="critical"
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.GDPR,
            compliance_log_id=compliance_log_id,
            data_subject_id=f"breach_{incident_id}",
            operation="data_breach_notification",
            lawful_basis="legal_obligation",
            processing_purpose="Data breach notification and management",
            data_categories=affected_data_types,
            user_id="system",
            article_references=["Article 33", "Article 34"],
            retention_period_days=4380,  # 12 years for breach notifications
            critical_incident=True
        )
        
        return compliance_log_id
    
    def log_retention_policy_enforcement(self,
                                       policy_id: str,
                                       data_category: DataCategory,
                                       retention_period_days: int,
                                       records_processed: int,
                                       records_deleted: int,
                                       records_archived: int,
                                       enforcement_date: datetime,
                                       enforcement_user: Optional[str] = None) -> str:
        """Log data retention policy enforcement"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"Retention policy enforced: {policy_id}",
            compliance_log_id=compliance_log_id,
            policy_id=policy_id,
            data_category=data_category.value,
            retention_period_days=retention_period_days,
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=records_archived,
            enforcement_date=enforcement_date.isoformat(),
            enforcement_user=enforcement_user,
            regulation="GDPR",
            article_reference="Article 5(1)(e)"
        )
        
        self._store_compliance_record(
            regulation=ComplianceRegulation.GDPR,
            compliance_log_id=compliance_log_id,
            data_subject_id=f"policy_{policy_id}",
            operation="retention_policy_enforcement",
            lawful_basis="legal_obligation",
            processing_purpose="Data retention policy enforcement",
            data_categories=[data_category.value],
            user_id=enforcement_user,
            article_references=["Article 5(1)(e)"],
            retention_period_days=retention_period_days,
            compliance_metadata={
                'records_processed': records_processed,
                'records_deleted': records_deleted,
                'records_archived': records_archived
            }
        )
        
        return compliance_log_id
    
    def log_compliance_audit(self,
                           regulation: ComplianceRegulation,
                           audit_scope: List[str],
                           audit_date: datetime,
                           auditor_id: str,
                           audit_findings: Dict[str, Any],
                           compliance_status: str,  # compliant, non_compliant, partially_compliant
                           recommendations: Optional[List[str]] = None) -> str:
        """Log compliance audit results"""
        
        compliance_log_id = self._generate_compliance_id()
        
        self.structured_logger.compliance(
            f"Compliance audit completed: {regulation.value}",
            compliance_log_id=compliance_log_id,
            regulation=regulation.value,
            audit_scope=audit_scope,
            audit_date=audit_date.isoformat(),
            auditor_id=auditor_id,
            compliance_status=compliance_status,
            audit_findings=audit_findings,
            recommendations=recommendations
        )
        
        self._store_compliance_record(
            regulation=regulation,
            compliance_log_id=compliance_log_id,
            data_subject_id=auditor_id,
            operation="compliance_audit",
            lawful_basis="legal_obligation",
            processing_purpose=f"{regulation.value} compliance audit",
            data_categories=["operational"],
            user_id=auditor_id,
            article_references=audit_scope,
            retention_period_days=2920,  # 8 years for audit records
            compliance_metadata={
                'audit_findings': audit_findings,
                'compliance_status': compliance_status,
                'recommendations': recommendations
            }
        )
        
        return compliance_log_id
    
    def _generate_compliance_id(self) -> str:
        """Generate unique compliance log ID"""
        import secrets
        return f"compliance_{secrets.token_hex(12)}"
    
    def _store_compliance_record(self,
                               regulation: ComplianceRegulation,
                               compliance_log_id: str,
                               data_subject_id: str,
                               operation: str,
                               lawful_basis: str,
                               processing_purpose: str,
                               data_categories: List[str],
                               user_id: Optional[str],
                               article_references: List[str],
                               retention_period_days: int,
                               critical_incident: bool = False,
                               compliance_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store compliance record in database"""
        
        db: Session = SessionLocal()
        try:
            compliance_log = ComplianceLog(
                compliance_log_id=compliance_log_id,
                regulation_standard=regulation.value,
                data_subject_id=data_subject_id,
                operation_type=operation,
                lawful_basis=lawful_basis,
                processing_purpose=processing_purpose,
                data_categories=data_categories,
                user_id=user_id,
                article_references=article_references,
                compliance_status="compliant" if not critical_incident else "requires_review",
                checked_at=datetime.utcnow(),
                retention_until=datetime.utcnow() + timedelta(days=retention_period_days),
                metadata=compliance_metadata or {},
                critical_incident=critical_incident
            )
            
            db.add(compliance_log)
            db.commit()
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to store compliance record: {str(e)}",
                compliance_log_id=compliance_log_id,
                regulation=regulation.value,
                error=str(e)
            )
        finally:
            db.close()
    
    def _store_data_subject_record(self,
                                 data_subject_id: str,
                                 request_type: str,
                                 request_reason: str,
                                 status: str,
                                 processing_steps: List[str],
                                 user_id: Optional[str]) -> None:
        """Store data subject request record"""
        
        db: Session = SessionLocal()
        try:
            data_subject_record = DataSubjectRecord(
                data_subject_id=data_subject_id,
                request_type=request_type,
                request_reason=request_reason,
                status=status,
                requested_at=datetime.utcnow(),
                processing_steps=processing_steps,
                requester_id=user_id
            )
            
            db.add(data_subject_record)
            db.commit()
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to store data subject record: {str(e)}",
                data_subject_id=data_subject_id,
                request_type=request_type,
                error=str(e)
            )
        finally:
            db.close()
    
    def get_compliance_status(self, regulation: ComplianceRegulation, 
                            timeframe_days: int = 365) -> Dict[str, Any]:
        """Get compliance status summary for a regulation"""
        
        db: Session = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
            
            # Get compliance logs for regulation within timeframe
            logs = db.query(ComplianceLog).filter(
                ComplianceLog.regulation_standard == regulation.value,
                ComplianceLog.checked_at >= cutoff_date
            ).all()
            
            # Calculate status
            total_logs = len(logs)
            compliant_logs = len([log for log in logs if log.compliance_status == "compliant"])
            critical_incidents = len([log for log in logs if log.critical_incident])
            
            status_summary = {
                'regulation': regulation.value,
                'timeframe_days': timeframe_days,
                'total_compliance_checks': total_logs,
                'compliant_checks': compliant_logs,
                'compliance_rate': (compliant_logs / total_logs * 100) if total_logs > 0 else 0,
                'critical_incidents': critical_incidents,
                'compliance_status': 'compliant' if critical_incidents == 0 else 'requires_attention',
                'last_check': max([log.checked_at for log in logs], default=None)
            }
            
            return status_summary
            
        finally:
            db.close()
    
    def generate_compliance_report(self, regulation: ComplianceRegulation,
                                 start_date: datetime,
                                 end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for specified regulation and timeframe"""
        
        db: Session = SessionLocal()
        try:
            logs = db.query(ComplianceLog).filter(
                ComplianceLog.regulation_standard == regulation.value,
                ComplianceLog.checked_at >= start_date,
                ComplianceLog.checked_at <= end_date
            ).all()
            
            # Generate comprehensive report
            report = {
                'regulation': regulation.value,
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'total_days': (end_date - start_date).days
                },
                'summary': {
                    'total_events': len(logs),
                    'operation_types': {},
                    'compliance_status_distribution': {},
                    'data_categories_processed': {},
                    'lawful_basis_usage': {}
                },
                'detailed_events': [],
                'compliance_gaps': [],
                'recommendations': []
            }
            
            # Analyze logs for patterns
            for log in logs:
                # Operation type distribution
                op_type = log.operation_type
                report['summary']['operation_types'][op_type] = \
                    report['summary']['operation_types'].get(op_type, 0) + 1
                
                # Compliance status distribution
                status = log.compliance_status
                report['summary']['compliance_status_distribution'][status] = \
                    report['summary']['compliance_status_distribution'].get(status, 0) + 1
                
                # Data categories processed
                for category in log.data_categories:
                    report['summary']['data_categories_processed'][category] = \
                        report['summary']['data_categories_processed'].get(category, 0) + 1
                
                # Lawful basis usage
                basis = log.lawful_basis
                report['summary']['lawful_basis_usage'][basis] = \
                    report['summary']['lawful_basis_usage'].get(basis, 0) + 1
            
            # Add detailed events (limited to prevent large payloads)
            for log in logs[:100]:  # Limit to first 100 events
                event_summary = {
                    'compliance_log_id': log.compliance_log_id,
                    'operation_type': log.operation_type,
                    'processing_purpose': log.processing_purpose,
                    'compliance_status': log.compliance_status,
                    'checked_at': log.checked_at.isoformat(),
                    'data_categories': log.data_categories,
                    'critical_incident': log.critical_incident
                }
                report['detailed_events'].append(event_summary)
            
            # Identify compliance gaps
            if report['summary']['compliance_status_distribution'].get('non_compliant', 0) > 0:
                report['compliance_gaps'].append({
                    'gap_type': 'non_compliant_events',
                    'description': f"Found {report['summary']['compliance_status_distribution']['non_compliant']} non-compliant events",
                    'severity': 'high'
                })
            
            if report['summary']['operation_types'].get('data_breach_notification', 0) > 0:
                report['compliance_gaps'].append({
                    'gap_type': 'data_breach_incidents',
                    'description': f"Data breach incidents detected: {report['summary']['operation_types']['data_breach_notification']}",
                    'severity': 'critical'
                })
            
            # Generate recommendations
            if critical_incidents > 0:
                report['recommendations'].append({
                    'category': 'incident_response',
                    'priority': 'high',
                    'description': 'Review and strengthen incident response procedures',
                    'regulation_requirements': regulation.value
                })
            
            return report
            
        finally:
            db.close()


# Global compliance logger instance
compliance_logger = ComplianceLogger()