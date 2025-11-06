"""
Audit Event Definitions and Categorization

Provides standardized event definitions and categorization for audit trails.
"""

from enum import Enum
from typing import Dict, List, Optional


class EventCategory(Enum):
    """Major categories of audit events"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIGURATION = "system_configuration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    USER_MANAGEMENT = "user_management"
    BUSINESS_OPERATIONS = "business_operations"
    SYSTEM_MAINTENANCE = "system_maintenance"
    INTEGRATION = "integration"
    DOCUMENT_PROCESSING = "document_processing"
    BILLING = "billing"
    LICENSING = "licensing"
    REPORTING = "reporting"


class EventSeverity(Enum):
    """Event severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventOutcome(Enum):
    """Event outcomes"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ComplianceRegulation(Enum):
    """Compliance regulations"""
    GDPR = "gdpr"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    CCPA = "ccpa"
    ISO_27001 = "iso_27001"
    SOC_2 = "soc_2"
    NIST = "nist"


class AuditEventTypes:
    """Comprehensive audit event type definitions"""
    
    # Authentication Events
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILURE = "login.failure"
    LOGIN_LOCKED = "login.locked"
    LOGOUT = "logout"
    LOGOUT_FORCED = "logout.forced"
    PASSWORD_CHANGE = "password.change"
    PASSWORD_RESET = "password.reset"
    PASSWORD_EXPIRED = "password.expired"
    MULTI_FACTOR_AUTH_SUCCESS = "mfa.success"
    MULTI_FACTOR_AUTH_FAILURE = "mfa.failure"
    SESSION_EXPIRED = "session.expired"
    SESSION_TERMINATED = "session.terminated"
    
    # Authorization Events
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_REMOVED = "role.removed"
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PRIVILEGE_ESCALATION = "privilege.escalation"
    UNAUTHORIZED_ACCESS_ATTEMPT = "access.unauthorized_attempt"
    
    # Data Access Events
    DATA_READ = "data.read"
    DATA_EXPORT = "data.export"
    DATA_DOWNLOAD = "data.download"
    DATA_PRINT = "data.print"
    DATA_SHARED = "data.shared"
    API_ACCESS = "api.access"
    REPORT_GENERATED = "report.generated"
    BULK_DATA_ACCESS = "data.access.bulk"
    
    # Data Modification Events
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_RESTORED = "data.restored"
    BULK_DATA_CREATED = "data.created.bulk"
    BULK_DATA_UPDATED = "data.updated.bulk"
    BULK_DATA_DELETED = "data.deleted.bulk"
    
    # System Configuration Events
    CONFIGURATION_CHANGED = "config.changed"
    SYSTEM_SETTINGS_UPDATED = "system.settings_updated"
    SECURITY_SETTINGS_CHANGED = "security.settings_changed"
    BACKUP_CREATED = "backup.created"
    BACKUP_RESTORED = "backup.restored"
    MAINTENANCE_MODE_ENABLED = "maintenance.enabled"
    MAINTENANCE_MODE_DISABLED = "maintenance.disabled"
    SYSTEM_RESTART = "system.restart"
    
    # Security Events
    SECURITY_INCIDENT = "security.incident"
    MALWARE_DETECTED = "security.malware_detected"
    INTRUSION_ATTEMPT = "security.intrusion_attempt"
    DDOS_ATTACK = "security.ddos_attack"
    BRUTE_FORCE_ATTACK = "security.brute_force"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    DATA_BREACH = "security.data_breach"
    COMPLIANCE_VIOLATION = "compliance.violation"
    
    # Compliance Events
    GDPR_DATA_ACCESS = "compliance.gdpr.data_access"
    GDPR_CONSENT_GIVEN = "compliance.gdpr.consent_given"
    GDPR_CONSENT_WITHDRAWN = "compliance.gdpr.consent_withdrawn"
    GDPR_DATA_PORTABILITY = "compliance.gdpr.data_portability"
    GDPR_RIGHT_TO_BE_FORGOTTEN = "compliance.gdpr.right_to_be_forgotten"
    SOX_CONTROL_TEST = "compliance.sox.control_test"
    PCI_DSS_VALIDATION = "compliance.pci.validation"
    
    # User Management Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_PROFILE_CHANGED = "user.profile_changed"
    USER_STATUS_CHANGED = "user.status_changed"
    USER_IMPORTED = "user.imported"
    USER_EXPORED = "user.exported"
    BULK_USER_OPERATIONS = "user.bulk_operations"
    
    # Business Operations Events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_APPROVED = "document.approved"
    DOCUMENT_REJECTED = "document.rejected"
    DOCUMENT_ARCHIVED = "document.archived"
    EXTRACTION_COMPLETED = "extraction.completed"
    EXTRACTION_ERROR = "extraction.error"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # Billing Events
    SUBSCRIPTION_CREATED = "billing.subscription_created"
    SUBSCRIPTION_UPDATED = "billing.subscription_updated"
    SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    PAYMENT_PROCESSED = "billing.payment_processed"
    PAYMENT_FAILED = "billing.payment_failed"
    INVOICE_GENERATED = "billing.invoice_generated"
    INVOICE_SENT = "billing.invoice_sent"
    REFUND_PROCESSED = "billing.refund_processed"
    
    # Licensing Events
    LICENSE_ACTIVATED = "license.activated"
    LICENSE_DEACTIVATED = "license.deactivated"
    LICENSE_RENEWED = "license.renewed"
    LICENSE_EXPIRED = "license.expired"
    LICENSE_VIOLATION = "license.violation"
    USAGE_LIMIT_EXCEEDED = "license.usage_limit_exceeded"
    
    # Integration Events
    EXTERNAL_API_CALLED = "integration.api_called"
    WEBHOOK_DELIVERED = "integration.webhook_delivered"
    WEBHOOK_FAILED = "integration.webhook_failed"
    DATA_SYNC_STARTED = "integration.sync_started"
    DATA_SYNC_COMPLETED = "integration.sync_completed"
    DATA_SYNC_FAILED = "integration.sync_failed"
    
    # Document Processing Events
    OCR_STARTED = "document.ocr_started"
    OCR_COMPLETED = "document.ocr_completed"
    OCR_FAILED = "document.ocr_failed"
    AI_PROCESSING_STARTED = "document.ai_processing_started"
    AI_PROCESSING_COMPLETED = "document.ai_processing_completed"
    AI_PROCESSING_FAILED = "document.ai_processing_failed"
    VALIDATION_FAILED = "document.validation_failed"
    
    # Reporting Events
    REPORT_VIEWED = "report.viewed"
    REPORT_SCHEDULED = "report.scheduled"
    REPORT_EXPORED = "report.exported"
    ANALYTICS_GENERATED = "report.analytics_generated"


class EventDefinition:
    """Definition of an audit event type"""
    
    def __init__(self,
                 event_type: str,
                 category: EventCategory,
                 description: str,
                 severity: EventSeverity,
                 compliance_regulations: Optional[List[ComplianceRegulation]] = None,
                 retention_period_days: int = 2555,  # 7 years default
                 requires_investigation: bool = False,
                 risk_score: int = 0):
        
        self.event_type = event_type
        self.category = category
        self.description = description
        self.severity = severity
        self.compliance_regulations = compliance_regulations or []
        self.retention_period_days = retention_period_days
        self.requires_investigation = requires_investigation
        self.risk_score = risk_score
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'event_type': self.event_type,
            'category': self.category.value,
            'description': self.description,
            'severity': self.severity.value,
            'compliance_regulations': [reg.value for reg in self.compliance_regulations],
            'retention_period_days': self.retention_period_days,
            'requires_investigation': self.requires_investigation,
            'risk_score': self.risk_score
        }


# Comprehensive event definitions registry
EVENT_DEFINITIONS: Dict[str, EventDefinition] = {
    # Authentication Events
    AuditEventTypes.LOGIN_SUCCESS: EventDefinition(
        AuditEventTypes.LOGIN_SUCCESS,
        EventCategory.AUTHENTICATION,
        "User successfully logged in",
        EventSeverity.INFO,
        retention_period_days=1095  # 3 years
    ),
    
    AuditEventTypes.LOGIN_FAILURE: EventDefinition(
        AuditEventTypes.LOGIN_FAILURE,
        EventCategory.AUTHENTICATION,
        "User failed to log in",
        EventSeverity.MEDIUM,
        retention_period_days=1825  # 5 years for security
    ),
    
    AuditEventTypes.LOGIN_LOCKED: EventDefinition(
        AuditEventTypes.LOGIN_LOCKED,
        EventCategory.AUTHENTICATION,
        "User account locked due to multiple failed attempts",
        EventSeverity.HIGH,
        requires_investigation=True,
        risk_score=75,
        retention_period_days=2555  # 7 years for security incidents
    ),
    
    AuditEventTypes.LOGOUT: EventDefinition(
        AuditEventTypes.LOGOUT,
        EventCategory.AUTHENTICATION,
        "User logged out",
        EventSeverity.INFO,
        retention_period_days=365  # 1 year
    ),
    
    AuditEventTypes.PASSWORD_CHANGE: EventDefinition(
        AuditEventTypes.PASSWORD_CHANGE,
        EventCategory.AUTHENTICATION,
        "User changed password",
        EventSeverity.MEDIUM,
        retention_period_days=1825  # 5 years
    ),
    
    AuditEventTypes.PASSWORD_RESET: EventDefinition(
        AuditEventTypes.PASSWORD_RESET,
        EventCategory.AUTHENTICATION,
        "Password reset requested/completed",
        EventSeverity.MEDIUM,
        retention_period_days=1825  # 5 years
    ),
    
    # Authorization Events
    AuditEventTypes.PERMISSION_GRANTED: EventDefinition(
        AuditEventTypes.PERMISSION_GRANTED,
        EventCategory.AUTHORIZATION,
        "Permission granted to user",
        EventSeverity.MEDIUM,
        retention_period_days=2555  # 7 years for compliance
    ),
    
    AuditEventTypes.PERMISSION_REVOKED: EventDefinition(
        AuditEventTypes.PERMISSION_REVOKED,
        EventCategory.AUTHORIZATION,
        "Permission revoked from user",
        EventSeverity.HIGH,
        retention_period_days=2555  # 7 years for compliance
    ),
    
    AuditEventTypes.ACCESS_DENIED: EventDefinition(
        AuditEventTypes.ACCESS_DENIED,
        EventCategory.AUTHORIZATION,
        "Access denied to user",
        EventSeverity.MEDIUM,
        retention_period_days=1825  # 5 years
    ),
    
    # Data Access Events
    AuditEventTypes.DATA_READ: EventDefinition(
        AuditEventTypes.DATA_READ,
        EventCategory.DATA_ACCESS,
        "Data was accessed/read",
        EventSeverity.INFO,
        compliance_regulations=[ComplianceRegulation.GDPR, ComplianceRegulation.SOX],
        retention_period_days=2555  # 7 years for GDPR/SOX compliance
    ),
    
    AuditEventTypes.DATA_EXPORT: EventDefinition(
        AuditEventTypes.DATA_EXPORT,
        EventCategory.DATA_ACCESS,
        "Data was exported",
        EventSeverity.HIGH,
        compliance_regulations=[ComplianceRegulation.GDPR, ComplianceRegulation.SOX],
        requires_investigation=True if False else False,  # Investigate large exports
        retention_period_days=2555  # 7 years for compliance
    ),
    
    AuditEventTypes.API_ACCESS: EventDefinition(
        AuditEventTypes.API_ACCESS,
        EventCategory.DATA_ACCESS,
        "API was accessed",
        EventSeverity.INFO,
        retention_period_days=1095  # 3 years
    ),
    
    # Data Modification Events
    AuditEventTypes.DATA_CREATED: EventDefinition(
        AuditEventTypes.DATA_CREATED,
        EventCategory.DATA_MODIFICATION,
        "Data was created",
        EventSeverity.INFO,
        retention_period_days=1825  # 5 years
    ),
    
    AuditEventTypes.DATA_UPDATED: EventDefinition(
        AuditEventTypes.DATA_UPDATED,
        EventCategory.DATA_MODIFICATION,
        "Data was updated",
        EventSeverity.MEDIUM,
        retention_period_days=2555  # 7 years for audit trail
    ),
    
    AuditEventTypes.DATA_DELETED: EventDefinition(
        AuditEventTypes.DATA_DELETED,
        EventCategory.DATA_MODIFICATION,
        "Data was deleted",
        EventSeverity.HIGH,
        compliance_regulations=[ComplianceRegulation.GDPR],
        retention_period_days=2555  # 7 years for compliance
    ),
    
    # Security Events
    AuditEventTypes.SECURITY_INCIDENT: EventDefinition(
        AuditEventTypes.SECURITY_INCIDENT,
        EventCategory.SECURITY,
        "Security incident detected",
        EventSeverity.CRITICAL,
        requires_investigation=True,
        risk_score=100,
        retention_period_days=4380  # 12 years for security incidents
    ),
    
    AuditEventTypes.DATA_BREACH: EventDefinition(
        AuditEventTypes.DATA_BREACH,
        EventCategory.SECURITY,
        "Data breach detected",
        EventSeverity.CRITICAL,
        compliance_regulations=[ComplianceRegulation.GDPR, ComplianceRegulation.SOX],
        requires_investigation=True,
        risk_score=100,
        retention_period_days=4380  # 12 years for breach notifications
    ),
    
    AuditEventTypes.MALWARE_DETECTED: EventDefinition(
        AuditEventTypes.MALWARE_DETECTED,
        EventCategory.SECURITY,
        "Malware detected in system",
        EventSeverity.CRITICAL,
        requires_investigation=True,
        risk_score=95,
        retention_period_days=4380  # 12 years for security incidents
    ),
    
    AuditEventTypes.UNAUTHORIZED_ACCESS: EventDefinition(
        AuditEventTypes.UNAUTHORIZED_ACCESS,
        EventCategory.SECURITY,
        "Unauthorized access attempt detected",
        EventSeverity.HIGH,
        requires_investigation=True,
        risk_score=80,
        retention_period_days=2555  # 7 years
    ),
    
    # Compliance Events
    AuditEventTypes.GDPR_DATA_ACCESS: EventDefinition(
        AuditEventTypes.GDPR_DATA_ACCESS,
        EventCategory.COMPLIANCE,
        "GDPR data access logged",
        EventSeverity.MEDIUM,
        compliance_regulations=[ComplianceRegulation.GDPR],
        retention_period_days=2555,  # 7 years for GDPR
        retention_period_days=2555
    ),
    
    AuditEventTypes.GDPR_CONSENT_GIVEN: EventDefinition(
        AuditEventTypes.GDPR_CONSENT_GIVEN,
        EventCategory.COMPLIANCE,
        "GDPR consent given by data subject",
        EventSeverity.INFO,
        compliance_regulations=[ComplianceRegulation.GDPR],
        retention_period_days=2555  # 7 years for GDPR
    ),
    
    AuditEventTypes.GDPR_RIGHT_TO_BE_FORGOTTEN: EventDefinition(
        AuditEventTypes.GDPR_RIGHT_TO_BE_FORGOTTEN,
        EventCategory.COMPLIANCE,
        "GDPR right to be forgotten request processed",
        EventSeverity.HIGH,
        compliance_regulations=[ComplianceRegulation.GDPR],
        retention_period_days=2555  # 7 years for GDPR
    ),
    
    # Business Operations Events
    AuditEventTypes.DOCUMENT_UPLOADED: EventDefinition(
        AuditEventTypes.DOCUMENT_UPLOADED,
        EventCategory.DOCUMENT_PROCESSING,
        "Document was uploaded",
        EventSeverity.INFO,
        retention_period_days=1825  # 5 years
    ),
    
    AuditEventTypes.DOCUMENT_PROCESSED: EventDefinition(
        AuditEventTypes.DOCUMENT_PROCESSED,
        EventCategory.DOCUMENT_PROCESSING,
        "Document processing completed",
        EventSeverity.INFO,
        retention_period_days=1825  # 5 years
    ),
    
    AuditEventTypes.EXTRACTION_COMPLETED: EventDefinition(
        AuditEventTypes.EXTRACTION_COMPLETED,
        EventCategory.DOCUMENT_PROCESSING,
        "Data extraction completed",
        EventSeverity.INFO,
        retention_period_days=1825  # 5 years
    ),
    
    # Billing Events
    AuditEventTypes.SUBSCRIPTION_CREATED: EventDefinition(
        AuditEventTypes.SUBSCRIPTION_CREATED,
        EventCategory.BILLING,
        "Subscription was created",
        EventSeverity.INFO,
        compliance_regulations=[ComplianceRegulation.SOX],
        retention_period_days=2190  # 6 years for SOX
    ),
    
    AuditEventTypes.PAYMENT_PROCESSED: EventDefinition(
        AuditEventTypes.PAYMENT_PROCESSED,
        EventCategory.BILLING,
        "Payment was processed",
        EventSeverity.INFO,
        compliance_regulations=[ComplianceRegulation.SOX, ComplianceRegulation.PCI_DSS],
        retention_period_days=2190  # 6 years for SOX, 1 year for PCI-DSS
    ),
    
    AuditEventTypes.PAYMENT_FAILED: EventDefinition(
        AuditEventTypes.PAYMENT_FAILED,
        EventCategory.BILLING,
        "Payment processing failed",
        EventSeverity.MEDIUM,
        compliance_regulations=[ComplianceRegulation.SOX],
        retention_period_days=2190  # 6 years for SOX
    ),
    
    # User Management Events
    AuditEventTypes.USER_CREATED: EventDefinition(
        AuditEventTypes.USER_CREATED,
        EventCategory.USER_MANAGEMENT,
        "User account was created",
        EventSeverity.MEDIUM,
        retention_period_days=2555  # 7 years for audit trail
    ),
    
    AuditEventTypes.USER_DELETED: EventDefinition(
        AuditEventTypes.USER_DELETED,
        EventCategory.USER_MANAGEMENT,
        "User account was deleted",
        EventSeverity.HIGH,
        compliance_regulations=[ComplianceRegulation.GDPR],
        retention_period_days=2555  # 7 years for compliance
    ),
}


def get_event_definition(event_type: str) -> Optional[EventDefinition]:
    """Get event definition by type"""
    return EVENT_DEFINITIONS.get(event_type)


def get_events_by_category(category: EventCategory) -> List[EventDefinition]:
    """Get all event definitions for a category"""
    return [
        definition for definition in EVENT_DEFINITIONS.values()
        if definition.category == category
    ]


def get_events_by_severity(severity: EventSeverity) -> List[EventDefinition]:
    """Get all event definitions for a severity level"""
    return [
        definition for definition in EVENT_DEFINITIONS.values()
        if definition.severity == severity
    ]


def get_compliance_events(regulation: ComplianceRegulation) -> List[EventDefinition]:
    """Get all event definitions for a compliance regulation"""
    return [
        definition for definition in EVENT_DEFINITIONS.values()
        if regulation in definition.compliance_regulations
    ]


def get_high_risk_events(min_risk_score: int = 70) -> List[EventDefinition]:
    """Get all high-risk event definitions"""
    return [
        definition for definition in EVENT_DEFINITIONS.values()
        if definition.risk_score >= min_risk_score
    ]


def calculate_event_risk_score(event_type: str,
                             context: Dict[str, any] = None) -> int:
    """Calculate risk score for an event based on type and context"""
    
    if event_type not in EVENT_DEFINITIONS:
        return 0
    
    base_score = EVENT_DEFINITIONS[event_type].risk_score
    
    # Adjust score based on context
    if context:
        # Increase score for off-hours activities
        if context.get('is_off_hours', False):
            base_score += 20
        
        # Increase score for unusual IP addresses
        if context.get('is_suspicious_ip', False):
            base_score += 30
        
        # Increase score for bulk operations
        if context.get('is_bulk_operation', False):
            base_score += 25
        
        # Increase score for high-value resources
        if context.get('resource_value') == 'high':
            base_score += 20
        
        # Increase score for privileged users
        if context.get('user_role') in ['admin', 'super_user', 'security_officer']:
            base_score += 15
    
    return min(base_score, 100)  # Cap at 100


def should_investigate_event(event_type: str,
                           context: Dict[str, any] = None) -> bool:
    """Determine if an event should trigger an investigation"""
    
    definition = EVENT_DEFINITIONS.get(event_type)
    if not definition:
        return False
    
    # Base investigation requirement
    if definition.requires_investigation:
        return True
    
    # Check risk score
    risk_score = calculate_event_risk_score(event_type, context)
    return risk_score >= 80


def get_retention_period(event_type: str) -> int:
    """Get retention period for an event type"""
    
    definition = EVENT_DEFINITIONS.get(event_type)
    if definition:
        return definition.retention_period_days
    
    return 2555  # Default 7 years


def validate_event_type(event_type: str) -> bool:
    """Validate if event type is defined"""
    return event_type in EVENT_DEFINITIONS