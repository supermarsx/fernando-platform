"""
Audit Logger Implementation

Provides comprehensive audit trail logging for enterprise compliance and regulatory requirements.
"""

import json
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from sqlalchemy.orm import Session
from app.models.logging import AuditLog, AuditEvent, AuditTrail, ComplianceLog
from app.models.user import User
from app.db.session import SessionLocal
from .structured_logger import structured_logger, LogCategory


class AuditEventType(Enum):
    """Types of audit events for categorization"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    SYSTEM_CONFIG = "system_config"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    REPORT_GENERATED = "report_generated"
    SECURITY_INCIDENT = "security_incident"
    COMPLIANCE_CHECK = "compliance_check"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    API_ACCESS = "api_access"
    BULK_OPERATION = "bulk_operation"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditOutcome(Enum):
    """Outcome of audit events"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    WARNING = "warning"
    UNKNOWN = "unknown"


class AuditLogger:
    """Enterprise-grade audit logger for comprehensive audit trails"""
    
    def __init__(self):
        self.structured_logger = structured_logger.with_context(
            category="audit"
        )
    
    def log_audit_event(self, 
                       event_type: AuditEventType,
                       resource_type: str,
                       resource_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       outcome: AuditOutcome = AuditOutcome.SUCCESS,
                       severity: AuditSeverity = AuditSeverity.MEDIUM,
                       description: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       session_id: Optional[str] = None,
                       compliance_tags: Optional[List[str]] = None,
                       compliance_retention_period: Optional[int] = None) -> str:
        """
        Log a comprehensive audit event
        
        Args:
            event_type: Type of audit event
            resource_type: Type of resource being acted upon
            resource_id: ID of the specific resource
            user_id: ID of the user performing the action
            outcome: Success/failure status
            severity: Severity level of the event
            description: Human-readable description
            details: Additional event details
            ip_address: Source IP address
            user_agent: User agent string
            session_id: User session ID
            compliance_tags: Compliance-related tags
            compliance_retention_period: Retention period in days
            
        Returns:
            audit_event_id: Unique identifier for the audit event
        """
        
        # Generate unique audit event ID
        audit_event_id = secrets.token_hex(16)
        
        # Create audit event data
        audit_data = {
            'audit_event_id': audit_event_id,
            'event_type': event_type.value,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'user_id': user_id,
            'outcome': outcome.value,
            'severity': severity.value,
            'description': description or self._generate_description(event_type, resource_type),
            'details': details or {},
            'ip_address': ip_address,
            'user_agent': user_agent,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'compliance_tags': compliance_tags or [],
            'compliance_retention_period': compliance_retention_period,
            'audit_chain_hash': None  # Will be set after storing
        }
        
        # Calculate integrity hash
        audit_data['event_hash'] = self._calculate_event_hash(audit_data)
        
        # Store in database
        self._store_audit_event(audit_data)
        
        # Log using structured logger
        self.structured_logger.audit(
            f"Audit event: {event_type.value}",
            audit_event_id=audit_event_id,
            event_type=event_type.value,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            outcome=outcome.value,
            severity=severity.value,
            **details or {}
        )
        
        return audit_event_id
    
    def log_user_action(self, 
                       action: str,
                       user_id: str,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       session_id: Optional[str] = None) -> str:
        """Log user action for audit trail"""
        return self.log_audit_event(
            event_type=AuditEventType.UPDATE,
            resource_type=resource_type or "user_action",
            resource_id=resource_id,
            user_id=user_id,
            description=f"User action: {action}",
            details={'action': action, **(details or {})},
            ip_address=ip_address,
            session_id=session_id,
            compliance_tags=['user_activity', 'gdpr_lawful_basis_legitimate_interest']
        )
    
    def log_data_access(self,
                       operation: str,  # read, create, update, delete
                       data_type: str,
                       record_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None) -> str:
        """Log data access for compliance (GDPR Article 30)"""
        return self.log_audit_event(
            event_type=AuditEventType(operation.upper()),
            resource_type=data_type,
            resource_id=record_id,
            user_id=user_id,
            description=f"Data access: {operation} {data_type}",
            details=details,
            ip_address=ip_address,
            compliance_tags=['gdpr_data_access', 'gdpr_article_30'],
            compliance_retention_period=2190  # 6 years for GDPR
        )
    
    def log_security_event(self,
                          event_type: str,
                          severity: AuditSeverity,
                          description: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None) -> str:
        """Log security-related events"""
        return self.log_audit_event(
            event_type=AuditEventType.SECURITY_INCIDENT,
            resource_type="security",
            user_id=user_id,
            outcome=AuditOutcome.FAILURE if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL] else AuditOutcome.WARNING,
            severity=severity,
            description=description,
            details=details,
            ip_address=ip_address,
            compliance_tags=['security', 'sox_controls'],
            compliance_retention_period=2555  # 7 years for SOX
        )
    
    def log_compliance_event(self,
                           regulation: str,
                           requirement: str,
                           status: str,
                           details: Optional[Dict[str, Any]] = None) -> str:
        """Log compliance-related events"""
        return self.log_audit_event(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            resource_type="compliance",
            description=f"Compliance check: {regulation} - {requirement}",
            details={
                'regulation': regulation,
                'requirement': requirement,
                'status': status,
                **(details or {})
            },
            compliance_tags=[regulation.lower(), 'compliance'],
            compliance_retention_period=2555  # 7 years for regulatory compliance
        )
    
    def log_system_configuration(self,
                               configuration_type: str,
                               changes: Dict[str, Any],
                               user_id: Optional[str] = None) -> str:
        """Log system configuration changes"""
        return self.log_audit_event(
            event_type=AuditEventType.SYSTEM_CONFIG,
            resource_type="system_configuration",
            user_id=user_id,
            description=f"System configuration change: {configuration_type}",
            details={'configuration_type': configuration_type, 'changes': changes},
            compliance_tags=['system_config', 'change_management'],
            severity=AuditSeverity.HIGH
        )
    
    def log_api_access(self,
                      endpoint: str,
                      method: str,
                      user_id: Optional[str] = None,
                      outcome: AuditOutcome = AuditOutcome.SUCCESS,
                      details: Optional[Dict[str, Any]] = None) -> str:
        """Log API access events"""
        return self.log_audit_event(
            event_type=AuditEventType.API_ACCESS,
            resource_type="api",
            user_id=user_id,
            outcome=outcome,
            description=f"API access: {method} {endpoint}",
            details={'endpoint': endpoint, 'method': method, **(details or {})},
            compliance_tags=['api_access', 'system_monitoring']
        )
    
    def log_bulk_operation(self,
                          operation_type: str,
                          affected_records: int,
                          user_id: str,
                          details: Optional[Dict[str, Any]] = None) -> str:
        """Log bulk operations"""
        severity = AuditSeverity.HIGH if affected_records > 1000 else AuditSeverity.MEDIUM
        return self.log_audit_event(
            event_type=AuditEventType.BULK_OPERATION,
            resource_type="bulk_operation",
            user_id=user_id,
            severity=severity,
            description=f"Bulk {operation_type}: {affected_records} records affected",
            details={'operation_type': operation_type, 'affected_records': affected_records, **(details or {})},
            compliance_tags=['bulk_operations', 'change_management']
        )
    
    def _generate_description(self, event_type: AuditEventType, resource_type: str) -> str:
        """Generate a standard description for audit events"""
        descriptions = {
            AuditEventType.CREATE: f"Created {resource_type}",
            AuditEventType.READ: f"Accessed {resource_type}",
            AuditEventType.UPDATE: f"Updated {resource_type}",
            AuditEventType.DELETE: f"Deleted {resource_type}",
            AuditEventType.LOGIN: f"User login for {resource_type}",
            AuditEventType.LOGOUT: f"User logout from {resource_type}",
            AuditEventType.SECURITY_INCIDENT: f"Security incident in {resource_type}",
            AuditEventType.COMPLIANCE_CHECK: f"Compliance check for {resource_type}",
            AuditEventType.API_ACCESS: f"API access to {resource_type}",
            AuditEventType.BULK_OPERATION: f"Bulk operation on {resource_type}",
        }
        return descriptions.get(event_type, f"Event {event_type.value} on {resource_type}")
    
    def _calculate_event_hash(self, audit_data: Dict[str, Any]) -> str:
        """Calculate tamper-evident hash for audit event"""
        # Create a copy without the hash field
        hash_data = {k: v for k, v in audit_data.items() if k != 'event_hash'}
        
        # Sort keys and create hashable string
        hash_string = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def _store_audit_event(self, audit_data: Dict[str, Any]) -> None:
        """Store audit event in database"""
        db: Session = SessionLocal()
        try:
            # Create AuditEvent record
            audit_event = AuditEvent(
                event_id=audit_data['audit_event_id'],
                event_type=audit_data['event_type'],
                resource_type=audit_data['resource_type'],
                resource_id=audit_data['resource_id'],
                user_id=audit_data['user_id'],
                outcome=audit_data['outcome'],
                severity=audit_data['severity'],
                description=audit_data['description'],
                details=audit_data['details'],
                ip_address=audit_data.get('ip_address'),
                user_agent=audit_data.get('user_agent'),
                session_id=audit_data.get('session_id'),
                timestamp=datetime.fromisoformat(audit_data['timestamp'].replace('Z', '+00:00')),
                event_hash=audit_data['event_hash'],
                compliance_tags=audit_data['compliance_tags'],
                retention_period_days=audit_data.get('compliance_retention_period')
            )
            
            db.add(audit_event)
            
            # Update audit trail chain
            self._update_audit_trail(audit_data, db)
            
            # Store compliance log if required
            if audit_data.get('compliance_tags'):
                self._store_compliance_log(audit_data, db)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            self.structured_logger.error(
                f"Failed to store audit event: {str(e)}",
                error=str(e),
                audit_event_id=audit_data['audit_event_id']
            )
        finally:
            db.close()
    
    def _update_audit_trail(self, audit_data: Dict[str, Any], db: Session) -> None:
        """Update audit trail with chain of custody"""
        # Get the most recent audit trail entry
        last_trail = db.query(AuditTrail).order_by(AuditTrail.created_at.desc()).first()
        
        trail_entry = AuditTrail(
            audit_event_id=audit_data['audit_event_id'],
            previous_hash=last_trail.chain_hash if last_trail else None,
            chain_hash=None,  # Will be calculated after adding to db
            created_at=datetime.utcnow(),
            compliance_metadata={
                'regulation_standards': audit_data.get('compliance_tags', []),
                'retention_period': audit_data.get('compliance_retention_period'),
            }
        )
        
        # Calculate chain hash
        if last_trail:
            chain_data = f"{audit_data['event_hash']}{last_trail.chain_hash}"
        else:
            chain_data = audit_data['event_hash']
        
        trail_entry.chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()
        trail_entry.previous_hash = last_trail.chain_hash if last_trail else None
        
        db.add(trail_entry)
    
    def _store_compliance_log(self, audit_data: Dict[str, Any], db: Session) -> None:
        """Store compliance-specific log entry"""
        compliance_log = ComplianceLog(
            audit_event_id=audit_data['audit_event_id'],
            regulation_standard=audit_data['compliance_tags'][0] if audit_data['compliance_tags'] else 'general',
            compliance_status='compliant',
            checked_at=datetime.fromisoformat(audit_data['timestamp'].replace('Z', '+00:00')),
            retention_until=datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).replace(year=datetime.utcnow().year + 7),  # Default 7 years
            metadata={
                'compliance_tags': audit_data['compliance_tags'],
                'retention_period': audit_data.get('compliance_retention_period'),
                'audit_trail_verified': True
            }
        )
        
        db.add(compliance_log)
    
    def verify_audit_trail_integrity(self) -> Dict[str, Any]:
        """Verify integrity of audit trail chain"""
        db: Session = SessionLocal()
        try:
            # Get all trail entries ordered by creation time
            trail_entries = db.query(AuditTrail).order_by(AuditTrail.created_at).all()
            
            integrity_results = {
                'total_events': len(trail_entries),
                'verified_events': 0,
                'corrupted_events': 0,
                'chain_valid': True,
                'corruption_details': []
            }
            
            previous_hash = None
            
            for trail in trail_entries:
                # Verify chain hash
                if previous_hash:
                    expected_hash = hashlib.sha256(
                        f"{trail.audit_event.event_hash}{previous_hash}".encode()
                    ).hexdigest()
                    
                    if trail.chain_hash != expected_hash:
                        integrity_results['chain_valid'] = False
                        integrity_results['corrupted_events'] += 1
                        integrity_results['corruption_details'].append({
                            'event_id': trail.audit_event_id,
                            'expected_hash': expected_hash,
                            'actual_hash': trail.chain_hash,
                            'corruption_type': 'chain_hash_mismatch'
                        })
                    else:
                        integrity_results['verified_events'] += 1
                else:
                    # First entry - verify hash exists
                    if trail.chain_hash:
                        integrity_results['verified_events'] += 1
                    else:
                        integrity_results['corrupted_events'] += 1
                        integrity_results['corruption_details'].append({
                            'event_id': trail.audit_event_id,
                            'corruption_type': 'missing_chain_hash'
                        })
                
                previous_hash = trail.chain_hash
            
            # Log integrity check results
            self.structured_logger.info(
                f"Audit trail integrity check completed",
                **integrity_results
            )
            
            return integrity_results
            
        finally:
            db.close()
    
    def search_audit_events(self,
                           user_id: Optional[str] = None,
                           event_type: Optional[AuditEventType] = None,
                           resource_type: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           severity: Optional[AuditSeverity] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Search audit events with filters"""
        db: Session = SessionLocal()
        try:
            query = db.query(AuditEvent)
            
            if user_id:
                query = query.filter(AuditEvent.user_id == user_id)
            if event_type:
                query = query.filter(AuditEvent.event_type == event_type.value)
            if resource_type:
                query = query.filter(AuditEvent.resource_type == resource_type)
            if severity:
                query = query.filter(AuditEvent.severity == severity.value)
            if start_date:
                query = query.filter(AuditEvent.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditEvent.timestamp <= end_date)
            
            events = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            
            return [self._serialize_audit_event(event) for event in events]
            
        finally:
            db.close()
    
    def _serialize_audit_event(self, event: AuditEvent) -> Dict[str, Any]:
        """Serialize audit event for API responses"""
        return {
            'audit_event_id': event.event_id,
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
            'retention_period_days': event.retention_period_days
        }


# Global audit logger instance
audit_logger = AuditLogger()