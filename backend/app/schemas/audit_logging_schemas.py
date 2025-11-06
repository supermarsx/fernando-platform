"""
Pydantic schemas for audit logging API endpoints

This module defines request/response models for audit logging API operations
including log search, audit trails, compliance reports, and analytics.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class LogLevel(str, Enum):
    """Log severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """Audit action types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS = "access"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    CONFIGURATION_CHANGE = "configuration_change"


class ComplianceRegulation(str, Enum):
    """Compliance regulations"""
    GDPR = "gdpr"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    CCPA = "ccpa"


class ComplianceStatus(str, Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


class LogEntryBase(BaseModel):
    """Base log entry schema"""
    level: LogLevel
    message: str = Field(..., min_length=1, max_length=1000)
    source: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    resource_type: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LogEntryCreate(LogEntryBase):
    """Schema for creating log entries"""
    pass


class LogEntryResponse(LogEntryBase):
    """Schema for log entry responses"""
    log_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditTrailBase(BaseModel):
    """Base audit trail schema"""
    action: AuditAction
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    result: str = Field(default="success", regex="^(success|failure|error)$")
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditTrailCreate(AuditTrailBase):
    """Schema for creating audit trail entries"""
    pass


class AuditTrailResponse(AuditTrailBase):
    """Schema for audit trail responses"""
    audit_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComplianceLogBase(BaseModel):
    """Base compliance log schema"""
    compliance_type: str = Field(..., min_length=1, max_length=50)
    regulation: ComplianceRegulation
    event_type: str = Field(..., min_length=1, max_length=100)
    subject_id: Optional[str] = None
    data_categories: Optional[List[str]] = None
    legal_basis: Optional[str] = None
    retention_period: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceLogCreate(ComplianceLogBase):
    """Schema for creating compliance log entries"""
    pass


class ComplianceLogResponse(ComplianceLogBase):
    """Schema for compliance log responses"""
    compliance_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LogSearchRequest(BaseModel):
    """Schema for log search requests"""
    query: Optional[str] = Field(None, description="Full-text search query")
    levels: Optional[List[LogLevel]] = None
    categories: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="created_at", regex="^(created_at|level|source|category)$")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")


class LogSearchResponse(BaseModel):
    """Schema for log search responses"""
    logs: List[LogEntryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
    aggregations: Optional[Dict[str, Any]] = None


class AuditSearchRequest(BaseModel):
    """Schema for audit trail search requests"""
    query: Optional[str] = Field(None, description="Full-text search query")
    actions: Optional[List[AuditAction]] = None
    resource_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    result: Optional[str] = Field(None, regex="^(success|failure|error)$")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="created_at", regex="^(created_at|action|resource_type|user_id)$")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")


class AuditSearchResponse(BaseModel):
    """Schema for audit trail search responses"""
    audits: List[AuditTrailResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
    aggregations: Optional[Dict[str, Any]] = None


class ComplianceReportRequest(BaseModel):
    """Schema for compliance report requests"""
    regulation: ComplianceRegulation
    start_date: datetime
    end_date: datetime
    include_violations: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)
    format: str = Field(default="json", regex="^(json|pdf|csv)$")


class ComplianceReportResponse(BaseModel):
    """Schema for compliance report responses"""
    report_id: str
    regulation: ComplianceRegulation
    status: ComplianceStatus
    compliance_score: float
    generated_at: datetime
    period: Dict[str, datetime]
    findings: Dict[str, Any]
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    total_records_analyzed: int


class DataSubjectRequestType(str, Enum):
    """Types of data subject requests under GDPR"""
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class DataSubjectRequestCreate(BaseModel):
    """Schema for creating data subject requests"""
    subject_id: str = Field(..., min_length=1, max_length=255)
    request_type: DataSubjectRequestType
    metadata: Optional[Dict[str, Any]] = None


class DataSubjectRequestResponse(BaseModel):
    """Schema for data subject request responses"""
    request_id: str
    subject_id: str
    request_type: DataSubjectRequestType
    status: str
    request_date: datetime
    completed_date: Optional[datetime]
    response_data: Dict[str, Any]
    processor_notes: str

    class Config:
        from_attributes = True


class LogAnalyticsRequest(BaseModel):
    """Schema for log analytics requests"""
    start_date: datetime
    end_date: datetime
    group_by: str = Field(default="day", regex="^(hour|day|week|month)$")
    metrics: List[str] = Field(default=["count"], description="Metrics to include: count, avg_level, unique_users, error_rate")
    filters: Optional[Dict[str, Any]] = None


class LogAnalyticsResponse(BaseModel):
    """Schema for log analytics responses"""
    period: Dict[str, datetime]
    time_series: List[Dict[str, Any]]
    summary: Dict[str, Any]
    top_categories: List[Dict[str, Any]]
    top_sources: List[Dict[str, Any]]
    error_rate: float
    unique_users_count: int


class ComplianceDashboardRequest(BaseModel):
    """Schema for compliance dashboard requests"""
    regulation: Optional[ComplianceRegulation] = None
    include_trends: bool = Field(default=True)
    include_alerts: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)


class ComplianceDashboardResponse(BaseModel):
    """Schema for compliance dashboard responses"""
    generated_at: datetime
    regulation: Optional[ComplianceRegulation]
    metrics: Dict[str, Any]
    trends: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    compliance_status: Dict[str, str]
    data_subject_requests: Dict[str, Any]
    violations_summary: Dict[str, Any]
    recommendations: List[str]


class SystemHealthResponse(BaseModel):
    """Schema for logging system health response"""
    status: str = Field(regex="^(healthy|degraded|unhealthy)$")
    timestamp: datetime
    components: Dict[str, str]
    metrics: Dict[str, Any]
    recent_issues: List[Dict[str, Any]]


class RetentionPolicyRequest(BaseModel):
    """Schema for retention policy requests"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    log_types: List[str] = Field(..., description="Types of logs: log_entry, audit_trail, compliance_log, forensic_log")
    retention_days: int = Field(..., ge=1, le=36525)
    archive_before_delete: bool = Field(default=True)
    encryption_required: bool = Field(default=False)
    conditions: Optional[Dict[str, Any]] = None


class RetentionPolicyResponse(BaseModel):
    """Schema for retention policy responses"""
    policy_id: str
    name: str
    description: Optional[str]
    log_types: List[str]
    retention_days: int
    archive_before_delete: bool
    encryption_required: bool
    conditions: Optional[Dict[str, Any]]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class LogExportRequest(BaseModel):
    """Schema for log export requests"""
    export_type: str = Field(..., regex="^(logs|audits|compliance|forensic)$")
    format: str = Field(..., regex="^(json|csv|pdf)$")
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = Field(default=True)


class LogExportResponse(BaseModel):
    """Schema for log export responses"""
    export_id: str
    export_type: str
    format: str
    status: str
    file_url: Optional[str]
    record_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# Additional utility schemas
class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool


class HealthCheckResponse(BaseModel):
    """Schema for health check responses"""
    service: str = "audit-logging"
    status: str = Field(regex="^(healthy|degraded|unhealthy)$")
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = {}
