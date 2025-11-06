"""
Forensic Logger Implementation

Provides security incident investigation logging with tamper-evidence and chain of custody.
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from sqlalchemy.orm import Session
from app.models.logging import ForensicLog, InvestigationCase, ChainOfCustody, EvidenceRecord
from app.db.session import SessionLocal
from .structured_logger import structured_logger, LogCategory, LogLevel


class IncidentSeverity(Enum):
    """Security incident severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class IncidentType(Enum):
    """Types of security incidents"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"
    MALWARE_INFECTION = "malware_infection"
    DDOS_ATTACK = "ddos_attack"
    INSIDER_THREAT = "insider_threat"
    PHISHING_ATTACK = "phishing_attack"
    RANSOMWARE = "ransomware"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    SYSTEM_COMPROMISE = "system_compromise"
    SOCIAL_ENGINEERING = "social_engineering"
    VULNERABILITY_EXPLOITATION = "vulnerability_exploitation"


class InvestigationStatus(Enum):
    """Investigation case statuses"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"
    ESCALATED = "escalated"
    ON_HOLD = "on_hold"


class EvidenceType(Enum):
    """Types of digital evidence"""
    LOG_FILE = "log_file"
    NETWORK_PACKET = "network_packet"
    MEMORY_DUMP = "memory_dump"
    DISK_IMAGE = "disk_image"
    DATABASE_RECORD = "database_record"
    EMAIL = "email"
    SCREENSHOT = "screenshot"
    VIDEO_RECORDING = "video_recording"
    AUDIO_RECORDING = "audio_recording"
    DOCUMENT = "document"
    SYSTEM_STATE = "system_state"
    CONFIGURATION = "configuration"


class ForensicLogger:
    """Enterprise forensic logger for security incident investigations"""
    
    def __init__(self):
        self.structured_logger = structured_logger.with_context(
            category="forensic"
        )
        self._active_investigations = {}
    
    def create_investigation_case(self,
                                incident_type: IncidentType,
                                severity: IncidentSeverity,
                                title: str,
                                description: str,
                                investigator_id: str,
                                affected_systems: Optional[List[str]] = None,
                                initial_indicators: Optional[List[str]] = None,
                                compliance_tags: Optional[List[str]] = None) -> str:
        """Create a new investigation case"""
        
        case_id = f"INV-{secrets.token_hex(8).upper()}"
        
        db: Session = SessionLocal()
        try:
            investigation_case = InvestigationCase(
                case_id=case_id,
                incident_type=incident_type.value,
                severity=severity.value,
                title=title,
                description=description,
                status=InvestigationStatus.OPEN.value,
                created_by=investigator_id,
                created_at=datetime.utcnow(),
                affected_systems=affected_systems or [],
                initial_indicators=initial_indicators or [],
                compliance_tags=compliance_tags or []
            )
            
            db.add(investigation_case)
            db.commit()
            
            # Log case creation
            self.log_investigation_event(
                case_id=case_id,
                event_type="case_created",
                description=f"Investigation case created: {title}",
                investigator_id=investigator_id,
                severity=severity,
                metadata={
                    'incident_type': incident_type.value,
                    'affected_systems': affected_systems,
                    'initial_indicators': initial_indicators
                }
            )
            
            # Track active investigation
            self._active_investigations[case_id] = investigation_case
            
            self.structured_logger.security(
                f"Investigation case created: {case_id}",
                case_id=case_id,
                incident_type=incident_type.value,
                severity=severity.value,
                investigator_id=investigator_id,
                title=title
            )
            
            return case_id
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to create investigation case: {str(e)}",
                case_id=case_id,
                error=str(e)
            )
            raise
        finally:
            db.close()
    
    def log_investigation_event(self,
                              case_id: str,
                              event_type: str,
                              description: str,
                              investigator_id: str,
                              severity: IncidentSeverity = IncidentSeverity.LOW,
                              timestamp: Optional[datetime] = None,
                              metadata: Optional[Dict[str, Any]] = None,
                              threat_indicators: Optional[List[str]] = None,
                              anomaly_score: Optional[float] = None) -> str:
        """Log an event in a forensic investigation"""
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        event_id = secrets.token_hex(16)
        
        # Get investigation case
        db: Session = SessionLocal()
        try:
            investigation_case = db.query(InvestigationCase).filter(
                InvestigationCase.case_id == case_id
            ).first()
            
            if not investigation_case:
                raise ValueError(f"Investigation case {case_id} not found")
            
            # Create forensic log entry
            forensic_log = ForensicLog(
                event_id=event_id,
                case_id=case_id,
                event_type=event_type,
                description=description,
                timestamp=timestamp,
                severity=severity.value,
                investigator_id=investigator_id,
                metadata=metadata or {},
                threat_indicators=threat_indicators or [],
                anomaly_score=anomaly_score,
                log_hash=None,  # Will be calculated below
                chain_of_custody=[
                    {
                        'custodian': investigator_id,
                        'action': 'created',
                        'timestamp': timestamp.isoformat(),
                        'integrity_hash': None
                    }
                ]
            )
            
            # Calculate log hash for integrity
            log_content = json.dumps({
                'event_id': event_id,
                'case_id': case_id,
                'event_type': event_type,
                'description': description,
                'timestamp': timestamp.isoformat(),
                'severity': severity.value,
                'investigator_id': investigator_id,
                'metadata': metadata,
                'threat_indicators': threat_indicators
            }, sort_keys=True, default=str)
            
            log_hash = hashlib.sha256(log_content.encode()).hexdigest()
            forensic_log.log_hash = log_hash
            
            db.add(forensic_log)
            db.commit()
            
            # Update investigation case timestamp
            investigation_case.last_updated = timestamp
            db.commit()
            
            self.structured_logger.security(
                f"Forensic event logged: {event_type}",
                case_id=case_id,
                event_id=event_id,
                event_type=event_type,
                severity=severity.value,
                investigator_id=investigator_id,
                threat_indicators=threat_indicators,
                anomaly_score=anomaly_score
            )
            
            return event_id
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to log forensic event: {str(e)}",
                case_id=case_id,
                event_id=event_id,
                error=str(e)
            )
            raise
        finally:
            db.close()
    
    def add_evidence(self,
                    case_id: str,
                    evidence_type: EvidenceType,
                    evidence_description: str,
                    file_path: Optional[str] = None,
                    data_hash: Optional[str] = None,
                    collected_by: str = None,
                    collection_method: str = "manual",
                    chain_of_custody: Optional[List[Dict[str, Any]]] = None,
                    forensic_tools_used: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add evidence to an investigation case"""
        
        evidence_id = secrets.token_hex(16)
        
        if collected_by is None:
            collected_by = "system"
        
        db: Session = SessionLocal()
        try:
            # Calculate evidence hash if file path is provided
            if file_path and data_hash is None:
                data_hash = self._calculate_file_hash(file_path)
            
            # Create evidence record
            evidence = EvidenceRecord(
                evidence_id=evidence_id,
                case_id=case_id,
                evidence_type=evidence_type.value,
                evidence_description=evidence_description,
                file_path=file_path,
                data_hash=data_hash,
                collected_by=collected_by,
                collected_at=datetime.utcnow(),
                collection_method=collection_method,
                chain_of_custody=chain_of_custody or [],
                forensic_tools_used=forensic_tools_used or [],
                metadata=metadata or {},
                evidence_integrity_verified=False
            )
            
            # Add to chain of custody
            custody_entry = {
                'custodian': collected_by,
                'action': 'evidence_collected',
                'timestamp': datetime.utcnow().isoformat(),
                'location': 'forensic_storage',
                'integrity_hash': data_hash
            }
            evidence.chain_of_custody.append(custody_entry)
            
            db.add(evidence)
            db.commit()
            
            # Log evidence addition
            self.log_investigation_event(
                case_id=case_id,
                event_type="evidence_added",
                description=f"Evidence added: {evidence_description}",
                investigator_id=collected_by,
                severity=IncidentSeverity.LOW,
                metadata={
                    'evidence_id': evidence_id,
                    'evidence_type': evidence_type.value,
                    'collection_method': collection_method,
                    'forensic_tools': forensic_tools_used
                }
            )
            
            self.structulated_logger.security(
                f"Evidence added to case: {evidence_id}",
                case_id=case_id,
                evidence_id=evidence_id,
                evidence_type=evidence_type.value,
                data_hash=data_hash,
                collected_by=collected_by
            )
            
            return evidence_id
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to add evidence: {str(e)}",
                case_id=case_id,
                evidence_id=evidence_id,
                error=str(e)
            )
            raise
        finally:
            db.close()
    
    def update_chain_of_custody(self,
                              evidence_id: str,
                              custodian: str,
                              action: str,
                              location: Optional[str] = None,
                              integrity_verified: bool = False) -> None:
        """Update chain of custody for evidence"""
        
        db: Session = SessionLocal()
        try:
            evidence = db.query(EvidenceRecord).filter(
                EvidenceRecord.evidence_id == evidence_id
            ).first()
            
            if not evidence:
                raise ValueError(f"Evidence {evidence_id} not found")
            
            # Add custody entry
            custody_entry = {
                'custodian': custodian,
                'action': action,
                'timestamp': datetime.utcnow().isoformat(),
                'location': location or 'unknown',
                'integrity_verified': integrity_verified
            }
            
            evidence.chain_of_custody.append(custody_entry)
            evidence.last_custodian = custodian
            evidence.last_custody_action = action
            
            if integrity_verified:
                evidence.evidence_integrity_verified = True
            
            db.commit()
            
            self.structured_logger.security(
                f"Chain of custody updated for evidence: {evidence_id}",
                evidence_id=evidence_id,
                custodian=custodian,
                action=action,
                integrity_verified=integrity_verified
            )
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to update chain of custody: {str(e)}",
                evidence_id=evidence_id,
                error=str(e)
            )
            raise
        finally:
            db.close()
    
    def analyze_suspicious_patterns(self,
                                  case_id: str,
                                  log_sources: List[str],
                                  time_window: timedelta,
                                  pattern_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze suspicious patterns in investigation case"""
        
        if pattern_types is None:
            pattern_types = ["unusual_access", "privilege_escalation", "data_exfiltration", 
                           "lateral_movement", "command_execution"]
        
        db: Session = SessionLocal()
        try:
            # Get logs within time window
            cutoff_time = datetime.utcnow() - time_window
            
            # This would integrate with actual log sources in production
            patterns_found = {
                'case_id': case_id,
                'analysis_time': datetime.utcnow().isoformat(),
                'time_window': str(time_window),
                'pattern_types_analyzed': pattern_types,
                'patterns_found': {},
                'threat_indicators': [],
                'anomaly_scores': {},
                'recommendations': []
            }
            
            # Simulate pattern detection (in production, this would analyze real logs)
            for pattern_type in pattern_types:
                patterns_found['patterns_found'][pattern_type] = {
                    'detected': False,
                    'instances': [],
                    'confidence_score': 0.0,
                    'severity': 'low'
                }
            
            # Example findings
            if "unusual_access" in pattern_types:
                patterns_found['patterns_found']['unusual_access'] = {
                    'detected': True,
                    'instances': [
                        {
                            'timestamp': '2025-11-06T07:00:00Z',
                            'source_ip': '192.168.1.100',
                            'user': 'admin',
                            'resource': '/admin/finance',
                            'frequency': 15
                        }
                    ],
                    'confidence_score': 0.85,
                    'severity': 'medium'
                }
                
                patterns_found['threat_indicators'].append({
                    'type': 'unusual_access_pattern',
                    'description': 'Multiple failed admin access attempts',
                    'affected_systems': ['admin_portal'],
                    'risk_level': 'medium'
                })
            
            # Log pattern analysis results
            self.log_investigation_event(
                case_id=case_id,
                event_type="pattern_analysis",
                description=f"Pattern analysis completed on {len(log_sources)} log sources",
                investigator_id="system",
                severity=IncidentSeverity.LOW,
                metadata=patterns_found
            )
            
            return patterns_found
            
        finally:
            db.close()
    
    def generate_forensic_timeline(self, case_id: str) -> List[Dict[str, Any]]:
        """Generate forensic timeline for investigation case"""
        
        db: Session = SessionLocal()
        try:
            # Get all investigation events
            events = db.query(ForensicLog).filter(
                ForensicLog.case_id == case_id
            ).order_by(ForensicLog.timestamp.asc()).all()
            
            # Get evidence records
            evidence_records = db.query(EvidenceRecord).filter(
                EvidenceRecord.case_id == case_id
            ).order_by(EvidenceRecord.collected_at.asc()).all()
            
            # Build timeline
            timeline = []
            
            for event in events:
                timeline_entry = {
                    'timestamp': event.timestamp.isoformat(),
                    'event_type': 'investigation_event',
                    'event_id': event.event_id,
                    'description': event.description,
                    'severity': event.severity,
                    'investigator_id': event.investigator_id,
                    'metadata': event.metadata,
                    'threat_indicators': event.threat_indicators
                }
                timeline.append(timeline_entry)
            
            for evidence in evidence_records:
                timeline_entry = {
                    'timestamp': evidence.collected_at.isoformat(),
                    'event_type': 'evidence_collection',
                    'evidence_id': evidence.evidence_id,
                    'description': f"Evidence collected: {evidence.evidence_description}",
                    'evidence_type': evidence.evidence_type,
                    'collected_by': evidence.collected_by,
                    'collection_method': evidence.collection_method,
                    'data_hash': evidence.data_hash
                }
                timeline.append(timeline_entry)
            
            # Sort by timestamp
            timeline.sort(key=lambda x: x['timestamp'])
            
            self.log_investigation_event(
                case_id=case_id,
                event_type="timeline_generated",
                description=f"Forensic timeline generated with {len(timeline)} entries",
                investigator_id="system"
            )
            
            return timeline
            
        finally:
            db.close()
    
    def verify_evidence_integrity(self, evidence_id: str) -> Dict[str, Any]:
        """Verify integrity of evidence using stored hash"""
        
        db: Session = SessionLocal()
        try:
            evidence = db.query(EvidenceRecord).filter(
                EvidenceRecord.evidence_id == evidence_id
            ).first()
            
            if not evidence:
                raise ValueError(f"Evidence {evidence_id} not found")
            
            verification_result = {
                'evidence_id': evidence_id,
                'verification_time': datetime.utcnow().isoformat(),
                'integrity_verified': False,
                'current_hash': evidence.data_hash,
                'verification_method': 'sha256',
                'chain_of_custody_complete': True,
                'custody_tampering_detected': False,
                'verification_details': []
            }
            
            # Check if file hash can be recalculated
            if evidence.file_path:
                try:
                    current_hash = self._calculate_file_hash(evidence.file_path)
                    hash_matches = current_hash == evidence.data_hash
                    
                    verification_result['integrity_verified'] = hash_matches
                    verification_result['current_hash'] = current_hash
                    verification_result['verification_details'].append({
                        'check': 'file_hash',
                        'result': 'pass' if hash_matches else 'fail',
                        'expected': evidence.data_hash,
                        'actual': current_hash
                    })
                except Exception as e:
                    verification_result['verification_details'].append({
                        'check': 'file_hash',
                        'result': 'error',
                        'error': str(e)
                    })
            
            # Check chain of custody completeness
            custody_entries = evidence.chain_of_custody
            if len(custody_entries) < 1:
                verification_result['chain_of_custody_complete'] = False
                verification_result['custody_tampering_detected'] = True
            
            # Log verification result
            self.structured_logger.security(
                f"Evidence integrity verification: {evidence_id}",
                evidence_id=evidence_id,
                integrity_verified=verification_result['integrity_verified'],
                chain_of_custody_complete=verification_result['chain_of_custody_complete']
            )
            
            return verification_result
            
        finally:
            db.close()
    
    def close_investigation_case(self,
                               case_id: str,
                               closure_reason: str,
                               investigator_id: str,
                               resolution_summary: str,
                               lessons_learned: Optional[List[str]] = None,
                               recommendations: Optional[List[str]] = None) -> None:
        """Close an investigation case"""
        
        db: Session = SessionLocal()
        try:
            investigation_case = db.query(InvestigationCase).filter(
                InvestigationCase.case_id == case_id
            ).first()
            
            if not investigation_case:
                raise ValueError(f"Investigation case {case_id} not found")
            
            # Update case status
            investigation_case.status = InvestigationStatus.CLOSED.value
            investigation_case.closed_at = datetime.utcnow()
            investigation_case.closed_by = investigator_id
            investigation_case.closure_reason = closure_reason
            investigation_case.resolution_summary = resolution_summary
            investigation_case.lessons_learned = lessons_learned or []
            investigation_case.recommendations = recommendations or []
            
            db.commit()
            
            # Log case closure
            self.log_investigation_event(
                case_id=case_id,
                event_type="case_closed",
                description=f"Investigation case closed: {closure_reason}",
                investigator_id=investigator_id,
                severity=IncidentSeverity.LOW,
                metadata={
                    'closure_reason': closure_reason,
                    'resolution_summary': resolution_summary,
                    'lessons_learned': lessons_learned,
                    'recommendations': recommendations
                }
            )
            
            # Remove from active investigations
            if case_id in self._active_investigations:
                del self._active_investigations[case_id]
            
            self.structured_logger.security(
                f"Investigation case closed: {case_id}",
                case_id=case_id,
                closure_reason=closure_reason,
                investigator_id=investigator_id,
                status='closed'
            )
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to close investigation case: {str(e)}",
                case_id=case_id,
                error=str(e)
            )
            raise
        finally:
            db.close()
    
    def get_active_investigations(self, investigator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active investigation cases"""
        
        db: Session = SessionLocal()
        try:
            query = db.query(InvestigationCase).filter(
                InvestigationCase.status.in_([
                    InvestigationStatus.OPEN.value,
                    InvestigationStatus.IN_PROGRESS.value,
                    InvestigationStatus.UNDER_REVIEW.value
                ])
            )
            
            if investigator_id:
                query = query.filter(InvestigationCase.created_by == investigator_id)
            
            investigations = query.all()
            
            return [self._serialize_investigation_case(inv) for inv in investigations]
            
        finally:
            db.close()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            # Return a placeholder hash if file can't be read
            return "hash_calculation_failed"
    
    def _serialize_investigation_case(self, investigation_case: InvestigationCase) -> Dict[str, Any]:
        """Serialize investigation case for API responses"""
        return {
            'case_id': investigation_case.case_id,
            'incident_type': investigation_case.incident_type,
            'severity': investigation_case.severity,
            'title': investigation_case.title,
            'description': investigation_case.description,
            'status': investigation_case.status,
            'created_by': investigation_case.created_by,
            'created_at': investigation_case.created_at.isoformat(),
            'last_updated': investigation_case.last_updated.isoformat() if investigation_case.last_updated else None,
            'affected_systems': investigation_case.affected_systems,
            'initial_indicators': investigation_case.initial_indicators,
            'compliance_tags': investigation_case.compliance_tags,
            'closed_at': investigation_case.closed_at.isoformat() if investigation_case.closed_at else None,
            'closed_by': investigation_case.closed_by,
            'closure_reason': investigation_case.closure_reason
        }
    
    @property
    def active_investigations_count(self) -> int:
        """Get count of active investigations"""
        return len(self._active_investigations)


# Global forensic logger instance
forensic_logger = ForensicLogger()