"""
Audit Tracker Service

Comprehensive audit trail and compliance tracking for credit transfers.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from app.models.credits import (
    CreditTransfer, CreditTransferStatus, CreditTransferAudit,
    CreditTransferPermission, User, Organization, CreditBalance
)
from app.services.credits.credit_analytics import CreditAnalyticsService
from app.services.credits.credit_manager import CreditManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class AuditAction:
    """Audit action types"""
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MODIFIED = "modified"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    COMPLIANCE_CHECK = "compliance_check"
    FRAUD_ALERT = "fraud_alert"


class AuditCategory:
    """Audit categories"""
    TRANSFER = "transfer"
    PERMISSION = "permission"
    APPROVAL = "approval"
    COMPLIANCE = "compliance"
    FRAUD = "fraud"
    SYSTEM = "system"


class AuditTracker:
    """
    Service for comprehensive audit tracking of credit transfers
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics_service = CreditAnalyticsService(db)
        self.credit_manager = CreditManager(db)
    
    def create_audit_entry(
        self,
        transfer_id: Optional[int] = None,
        action: str,
        category: str,
        user_id: int,
        organization_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new audit entry
        """
        try:
            # Validate action and category
            valid_actions = [
                AuditAction.CREATED, AuditAction.APPROVED, AuditAction.REJECTED,
                AuditAction.EXECUTED, AuditAction.FAILED, AuditAction.CANCELLED,
                AuditAction.MODIFIED, AuditAction.PERMISSION_GRANTED, 
                AuditAction.PERMISSION_REVOKED, AuditAction.COMPLIANCE_CHECK,
                AuditAction.FRAUD_ALERT
            ]
            
            valid_categories = [
                AuditCategory.TRANSFER, AuditCategory.PERMISSION, 
                AuditCategory.APPROVAL, AuditCategory.COMPLIANCE,
                AuditCategory.FRAUD, AuditCategory.SYSTEM
            ]
            
            if action not in valid_actions:
                raise ValueError(f"Invalid audit action: {action}")
            
            if category not in valid_categories:
                raise ValueError(f"Invalid audit category: {category}")
            
            # Create audit entry
            audit_entry = CreditTransferAudit(
                transfer_id=transfer_id,
                action=action,
                category=category,
                user_id=user_id,
                organization_id=organization_id,
                details=details or {},
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            
            self.db.add(audit_entry)
            self.db.commit()
            self.db.refresh(audit_entry)
            
            logger.info(f"Created audit entry: {action} by user {user_id}")
            
            return {
                "success": True,
                "audit_entry": self._audit_to_dict(audit_entry),
                "message": "Audit entry created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating audit entry: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def audit_transfer_created(
        self,
        transfer: CreditTransfer,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for transfer creation
        """
        details = {
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "amount": float(transfer.amount),
            "status": transfer.status.value,
            "transfer_reason": transfer.transfer_reason,
            "permission_id": transfer.permission_id
        }
        
        return self.create_audit_entry(
            transfer_id=transfer.id,
            action=AuditAction.CREATED,
            category=AuditCategory.TRANSFER,
            user_id=user_id,
            organization_id=transfer.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def audit_transfer_approval(
        self,
        transfer: CreditTransfer,
        approver_id: int,
        approved: bool,
        approval_notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for transfer approval/rejection
        """
        action = AuditAction.APPROVED if approved else AuditAction.REJECTED
        
        details = {
            "transfer_id": transfer.id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "amount": float(transfer.amount),
            "approval_notes": approval_notes,
            "status_change": f"{transfer.status.value}_to_{transfer.status.value}"
        }
        
        return self.create_audit_entry(
            transfer_id=transfer.id,
            action=action,
            category=AuditCategory.APPROVAL,
            user_id=approver_id,
            organization_id=transfer.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def audit_transfer_execution(
        self,
        transfer: CreditTransfer,
        execution_result: Dict[str, Any],
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for transfer execution
        """
        action = AuditAction.EXECUTED if execution_result.get("success") else AuditAction.FAILED
        
        details = {
            "transfer_id": transfer.id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "amount": float(transfer.amount),
            "execution_result": execution_result,
            "from_balance_after": execution_result.get("from_balance_after"),
            "to_balance_after": execution_result.get("to_balance_after")
        }
        
        return self.create_audit_entry(
            transfer_id=transfer.id,
            action=action,
            category=AuditCategory.TRANSFER,
            user_id=user_id or transfer.from_user_id,
            organization_id=transfer.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def audit_permission_change(
        self,
        permission: CreditTransferPermission,
        action: str,
        user_id: int,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for permission changes
        """
        details = {
            "permission_id": permission.id,
            "from_user_id": permission.from_user_id,
            "to_user_id": permission.to_user_id,
            "permission_type": permission.permission_type,
            "max_amount": float(permission.max_amount) if permission.max_amount else None,
            "changes": changes or {}
        }
        
        return self.create_audit_entry(
            action=action,
            category=AuditCategory.PERMISSION,
            user_id=user_id,
            organization_id=permission.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def audit_compliance_check(
        self,
        transfer: CreditTransfer,
        compliance_result: Dict[str, Any],
        checker_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for compliance checks
        """
        details = {
            "transfer_id": transfer.id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "amount": float(transfer.amount),
            "compliance_result": compliance_result,
            "violations": compliance_result.get("violations", []),
            "approved": compliance_result.get("approved", False)
        }
        
        return self.create_audit_entry(
            transfer_id=transfer.id,
            action=AuditAction.COMPLIANCE_CHECK,
            category=AuditCategory.COMPLIANCE,
            user_id=checker_id,
            organization_id=transfer.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def audit_fraud_alert(
        self,
        transfer: CreditTransfer,
        fraud_indicators: List[Dict[str, Any]],
        alert_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit entry for fraud alerts
        """
        details = {
            "transfer_id": transfer.id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "amount": float(transfer.amount),
            "fraud_indicators": fraud_indicators,
            "alert_id": alert_id,
            "risk_score": max(indicator.get("risk_score", 0) for indicator in fraud_indicators)
        }
        
        return self.create_audit_entry(
            transfer_id=transfer.id,
            action=AuditAction.FRAUD_ALERT,
            category=AuditCategory.FRAUD,
            user_id=0,  # System-generated
            organization_id=transfer.from_organization_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_transfer_audit_trail(
        self,
        transfer_id: int,
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a specific transfer
        """
        try:
            audit_entries = self.db.query(CreditTransferAudit).filter(
                CreditTransferAudit.transfer_id == transfer_id
            ).order_by(asc(CreditTransferAudit.created_at)).all()
            
            trail = []
            for entry in audit_entries:
                audit_dict = self._audit_to_dict(entry)
                if not include_metadata:
                    audit_dict.pop("metadata", None)
                trail.append(audit_dict)
            
            return trail
            
        except Exception as e:
            logger.error(f"Error getting transfer audit trail: {str(e)}")
            return []
    
    def get_user_audit_log(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        days: int = 30,
        category: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit log for a specific user
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(CreditTransferAudit).filter(
                and_(
                    CreditTransferAudit.user_id == user_id,
                    CreditTransferAudit.created_at >= start_date
                )
            )
            
            if organization_id:
                query = query.filter(CreditTransferAudit.organization_id == organization_id)
            
            if category:
                query = query.filter(CreditTransferAudit.category == category)
            
            if action:
                query = query.filter(CreditTransferAudit.action == action)
            
            audit_entries = query.order_by(desc(CreditTransferAudit.created_at)).limit(1000).all()
            
            return [self._audit_to_dict(entry) for entry in audit_entries]
            
        except Exception as e:
            logger.error(f"Error getting user audit log: {str(e)}")
            return []
    
    def get_organization_audit_log(
        self,
        organization_id: int,
        days: int = 30,
        category: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit log for an organization
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(CreditTransferAudit).filter(
                and_(
                    CreditTransferAudit.organization_id == organization_id,
                    CreditTransferAudit.created_at >= start_date
                )
            )
            
            if category:
                query = query.filter(CreditTransferAudit.category == category)
            
            if user_id:
                query = query.filter(CreditTransferAudit.user_id == user_id)
            
            audit_entries = query.order_by(desc(CreditTransferAudit.created_at)).limit(5000).all()
            
            return [self._audit_to_dict(entry) for entry in audit_entries]
            
        except Exception as e:
            logger.error(f"Error getting organization audit log: {str(e)}")
            return []
    
    def generate_compliance_report(
        self,
        organization_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        compliance_framework: str = "SOX"
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit requirements
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=90)  # Last 90 days
            
            # Get all relevant audit entries
            query = self.db.query(CreditTransferAudit).filter(
                and_(
                    CreditTransferAudit.created_at >= start_date,
                    CreditTransferAudit.created_at <= end_date
                )
            )
            
            if organization_id:
                query = query.filter(CreditTransferAudit.organization_id == organization_id)
            
            audit_entries = query.all()
            
            # Analyze compliance metrics
            report = {
                "report_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "organization_id": organization_id,
                    "compliance_framework": compliance_framework
                },
                "summary": self._generate_compliance_summary(audit_entries),
                "control_effectiveness": self._assess_control_effectiveness(audit_entries),
                "violations": self._identify_compliance_violations(audit_entries),
                "recommendations": self._generate_compliance_recommendations(audit_entries),
                "risk_assessment": self._assess_compliance_risk(audit_entries)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return {}
    
    def detect_compliance_violations(
        self,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Detect potential compliance violations
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent audit entries
            query = self.db.query(CreditTransferAudit).filter(
                CreditTransferAudit.created_at >= start_date
            )
            
            if organization_id:
                query = query.filter(CreditTransferAudit.organization_id == organization_id)
            
            audit_entries = query.all()
            
            violations = []
            
            # Check for missing approvals
            transfer_creations = [e for e in audit_entries if e.action == AuditAction.CREATED]
            transfer_approvals = [e for e in audit_entries if e.action == AuditAction.APPROVED]
            
            for creation in transfer_creations:
                # Check if this transfer has an approval entry
                approval_exists = any(
                    a.transfer_id == creation.transfer_id 
                    for a in transfer_approvals
                )
                
                if not approval_exists:
                    violations.append({
                        "type": "missing_approval",
                        "transfer_id": creation.transfer_id,
                        "created_by": creation.user_id,
                        "created_at": creation.created_at.isoformat(),
                        "severity": "high"
                    })
            
            # Check for high-value transfers without dual approval
            high_value_threshold = 10000  # Credits
            high_value_transfers = [
                e for e in audit_entries 
                if e.action == AuditAction.CREATED and 
                e.details.get("amount", 0) >= high_value_threshold
            ]
            
            for transfer in high_value_transfers:
                # Count approvals for this transfer
                approvals = [
                    a for a in transfer_approvals 
                    if a.transfer_id == transfer.transfer_id
                ]
                
                if len(approvals) < 2:  # Require dual approval
                    violations.append({
                        "type": "insufficient_approval",
                        "transfer_id": transfer.transfer_id,
                        "amount": transfer.details.get("amount"),
                        "approval_count": len(approvals),
                        "required_approvals": 2,
                        "severity": "critical"
                    })
            
            # Check for suspicious IP addresses
            ip_frequency = {}
            for entry in audit_entries:
                ip = entry.ip_address
                if ip:
                    ip_frequency[ip] = ip_frequency.get(ip, 0) + 1
            
            suspicious_ips = {ip: count for ip, count in ip_frequency.items() if count > 100}
            if suspicious_ips:
                violations.append({
                    "type": "high_frequency_ip",
                    "suspicious_ips": suspicious_ips,
                    "threshold": 100,
                    "severity": "medium"
                })
            
            return violations
            
        except Exception as e:
            logger.error(f"Error detecting compliance violations: {str(e)}")
            return []
    
    def generate_audit_statistics(
        self,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate audit activity statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(CreditTransferAudit).filter(
                CreditTransferAudit.created_at >= start_date
            )
            
            if organization_id:
                query = query.filter(CreditTransferAudit.organization_id == organization_id)
            
            audit_entries = query.all()
            
            # Calculate statistics
            total_entries = len(audit_entries)
            
            # Action distribution
            action_distribution = {}
            for action in [AuditAction.CREATED, AuditAction.APPROVED, AuditAction.REJECTED, 
                          AuditAction.EXECUTED, AuditAction.FAILED]:
                count = len([e for e in audit_entries if e.action == action])
                if count > 0:
                    action_distribution[action] = count
            
            # Category distribution
            category_distribution = {}
            for category in [AuditCategory.TRANSFER, AuditCategory.PERMISSION, 
                            AuditCategory.APPROVAL, AuditCategory.COMPLIANCE, 
                            AuditCategory.FRAUD, AuditCategory.SYSTEM]:
                count = len([e for e in audit_entries if e.category == category])
                if count > 0:
                    category_distribution[category] = count
            
            # User activity
            user_activity = {}
            for entry in audit_entries:
                user_id = entry.user_id
                user_activity[user_id] = user_activity.get(user_id, 0) + 1
            
            # Top active users
            top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Daily activity
            daily_activity = {}
            for entry in audit_entries:
                date_key = entry.created_at.date().isoformat()
                daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
            
            return {
                "period_days": days,
                "total_audit_entries": total_entries,
                "action_distribution": action_distribution,
                "category_distribution": category_distribution,
                "user_activity": dict(top_users),
                "daily_activity": daily_activity,
                "unique_users": len(user_activity),
                "organization_id": organization_id
            }
            
        except Exception as e:
            logger.error(f"Error generating audit statistics: {str(e)}")
            return {}
    
    def export_audit_data(
        self,
        organization_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export audit data for external systems
        """
        try:
            # Set default date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get audit data
            query = self.db.query(CreditTransferAudit).filter(
                and_(
                    CreditTransferAudit.created_at >= start_date,
                    CreditTransferAudit.created_at <= end_date
                )
            )
            
            if organization_id:
                query = query.filter(CreditTransferAudit.organization_id == organization_id)
            
            audit_entries = query.order_by(desc(CreditTransferAudit.created_at)).all()
            
            # Format data based on requested format
            if format.lower() == "json":
                export_data = {
                    "export_metadata": {
                        "exported_at": datetime.utcnow().isoformat(),
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat()
                        },
                        "organization_id": organization_id,
                        "total_records": len(audit_entries),
                        "format": "json"
                    },
                    "audit_entries": [self._audit_to_dict(entry) for entry in audit_entries]
                }
            else:
                # CSV format would be implemented here
                export_data = {
                    "error": f"Format {format} not supported yet",
                    "supported_formats": ["json"]
                }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting audit data: {str(e)}")
            return {"error": str(e)}
    
    def verify_audit_integrity(
        self,
        organization_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Verify audit trail integrity and completeness
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get transfers from the database
            transfer_query = self.db.query(CreditTransfer).filter(
                CreditTransfer.created_at >= start_date
            )
            
            if organization_id:
                transfer_query = transfer_query.filter(
                    CreditTransfer.from_organization_id == organization_id
                )
            
            transfers = transfer_query.all()
            
            # Check audit trail completeness
            integrity_issues = []
            total_transfers = len(transfers)
            audited_transfers = 0
            
            for transfer in transfers:
                # Check if transfer has audit entries
                audit_count = self.db.query(CreditTransferAudit).filter(
                    CreditTransferAudit.transfer_id == transfer.id
                ).count()
                
                if audit_count == 0:
                    integrity_issues.append({
                        "type": "missing_audit_trail",
                        "transfer_id": transfer.id,
                        "severity": "high"
                    })
                else:
                    audited_transfers += 1
                
                # Check for required audit actions
                expected_actions = self._get_expected_audit_actions(transfer)
                actual_actions = self.db.query(CreditTransferAudit.action).filter(
                    CreditTransferAudit.transfer_id == transfer.id
                ).distinct().all()
                actual_action_set = {action[0] for action in actual_actions}
                
                missing_actions = expected_actions - actual_action_set
                if missing_actions:
                    integrity_issues.append({
                        "type": "incomplete_audit_trail",
                        "transfer_id": transfer.id,
                        "missing_actions": list(missing_actions),
                        "severity": "medium"
                    })
            
            # Calculate integrity score
            audit_coverage = (audited_transfers / total_transfers * 100) if total_transfers > 0 else 100
            integrity_score = audit_coverage - (len(integrity_issues) * 5)  # Deduct 5 points per issue
            
            return {
                "integrity_score": max(integrity_score, 0),
                "audit_coverage_percentage": audit_coverage,
                "total_transfers": total_transfers,
                "audited_transfers": audited_transfers,
                "integrity_issues": integrity_issues,
                "verification_period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error verifying audit integrity: {str(e)}")
            return {
                "integrity_score": 0,
                "error": str(e)
            }
    
    def _generate_compliance_summary(self, audit_entries: List[CreditTransferAudit]) -> Dict[str, Any]:
        """
        Generate compliance summary from audit entries
        """
        try:
            total_entries = len(audit_entries)
            
            # Count by category
            compliance_entries = [e for e in audit_entries if e.category == AuditCategory.COMPLIANCE]
            fraud_entries = [e for e in audit_entries if e.category == AuditCategory.FRAUD]
            transfer_entries = [e for e in audit_entries if e.category == AuditCategory.TRANSFER]
            approval_entries = [e for e in audit_entries if e.category == AuditCategory.APPROVAL]
            
            return {
                "total_audit_entries": total_entries,
                "compliance_checks": len(compliance_entries),
                "fraud_alerts": len(fraud_entries),
                "transfer_activities": len(transfer_entries),
                "approval_activities": len(approval_entries),
                "compliance_rate": (len(compliance_entries) / total_entries * 100) if total_entries > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance summary: {str(e)}")
            return {}
    
    def _assess_control_effectiveness(self, audit_entries: List[CreditTransferAudit]) -> Dict[str, Any]:
        """
        Assess effectiveness of controls based on audit data
        """
        try:
            # Check approval patterns
            approved_transfers = [e for e in audit_entries if e.action == AuditAction.APPROVED]
            rejected_transfers = [e for e in audit_entries if e.action == AuditAction.REJECTED]
            failed_transfers = [e for e in audit_entries if e.action == AuditAction.FAILED]
            
            total_attempts = len(approved_transfers) + len(rejected_transfers) + len(failed_transfers)
            
            if total_attempts > 0:
                approval_rate = len(approved_transfers) / total_attempts * 100
                rejection_rate = len(rejected_transfers) / total_attempts * 100
                failure_rate = len(failed_transfers) / total_attempts * 100
            else:
                approval_rate = rejection_rate = failure_rate = 0
            
            return {
                "approval_rate": round(approval_rate, 2),
                "rejection_rate": round(rejection_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "control_effectiveness_score": round(100 - failure_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error assessing control effectiveness: {str(e)}")
            return {}
    
    def _identify_compliance_violations(self, audit_entries: List[CreditTransferAudit]) -> List[Dict[str, Any]]:
        """
        Identify specific compliance violations from audit data
        """
        violations = []
        
        try:
            # Check for fraud alerts
            fraud_alerts = [e for e in audit_entries if e.action == AuditAction.FRAUD_ALERT]
            for alert in fraud_alerts:
                violations.append({
                    "type": "fraud_alert",
                    "severity": "high",
                    "details": alert.details,
                    "timestamp": alert.created_at.isoformat()
                })
            
            # Check for failed compliance checks
            failed_compliance = [e for e in audit_entries 
                               if e.action == AuditAction.COMPLIANCE_CHECK and 
                               not e.details.get("approved", True)]
            for check in failed_compliance:
                violations.append({
                    "type": "compliance_check_failed",
                    "severity": "medium",
                    "details": check.details,
                    "timestamp": check.created_at.isoformat()
                })
            
            return violations
            
        except Exception as e:
            logger.error(f"Error identifying compliance violations: {str(e)}")
            return violations
    
    def _generate_compliance_recommendations(self, audit_entries: List[CreditTransferAudit]) -> List[str]:
        """
        Generate compliance recommendations based on audit data
        """
        recommendations = []
        
        try:
            # Analyze patterns and generate recommendations
            fraud_alerts = [e for e in audit_entries if e.action == AuditAction.FRAUD_ALERT]
            if len(fraud_alerts) > 5:
                recommendations.append("High number of fraud alerts detected. Consider implementing additional fraud prevention controls.")
            
            failed_compliance = [e for e in audit_entries 
                               if e.action == AuditAction.COMPLIANCE_CHECK and 
                               not e.details.get("approved", True)]
            if len(failed_compliance) > len(audit_entries) * 0.1:  # More than 10% failed
                recommendations.append("High compliance failure rate. Review compliance procedures and staff training.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating compliance recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def _assess_compliance_risk(self, audit_entries: List[CreditTransferAudit]) -> Dict[str, Any]:
        """
        Assess overall compliance risk
        """
        try:
            risk_score = 0
            risk_factors = []
            
            # Fraud risk
            fraud_alerts = [e for e in audit_entries if e.action == AuditAction.FRAUD_ALERT]
            if len(fraud_alerts) > len(audit_entries) * 0.05:  # More than 5% fraud alerts
                risk_score += 30
                risk_factors.append("High fraud alert frequency")
            
            # Compliance failure risk
            failed_compliance = [e for e in audit_entries 
                               if e.action == AuditAction.COMPLIANCE_CHECK and 
                               not e.details.get("approved", True)]
            if len(failed_compliance) > len(audit_entries) * 0.1:  # More than 10% failed
                risk_score += 25
                risk_factors.append("High compliance failure rate")
            
            # Transfer failure risk
            failed_transfers = [e for e in audit_entries if e.action == AuditAction.FAILED]
            if len(failed_transfers) > len(audit_entries) * 0.2:  # More than 20% failed
                risk_score += 20
                risk_factors.append("High transfer failure rate")
            
            # Determine risk level
            if risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "total_entries_analyzed": len(audit_entries)
            }
            
        except Exception as e:
            logger.error(f"Error assessing compliance risk: {str(e)}")
            return {"risk_score": 0, "risk_level": "unknown", "risk_factors": []}
    
    def _get_expected_audit_actions(self, transfer: CreditTransfer) -> set:
        """
        Get expected audit actions for a transfer
        """
        expected = {AuditAction.CREATED}
        
        if transfer.status in [CreditTransferStatus.APPROVED, CreditTransferStatus.REJECTED]:
            expected.add(AuditAction.APPROVED if transfer.status == CreditTransferStatus.APPROVED else AuditAction.REJECTED)
        
        if transfer.status == CreditTransferStatus.COMPLETED:
            expected.add(AuditAction.EXECUTED)
        elif transfer.status == CreditTransferStatus.FAILED:
            expected.add(AuditAction.FAILED)
        
        return expected
    
    def _audit_to_dict(self, audit: CreditTransferAudit) -> Dict[str, Any]:
        """
        Convert audit model to dictionary
        """
        return {
            "id": audit.id,
            "transfer_id": audit.transfer_id,
            "action": audit.action,
            "category": audit.category,
            "user_id": audit.user_id,
            "organization_id": audit.organization_id,
            "details": audit.details,
            "metadata": audit.metadata,
            "ip_address": audit.ip_address,
            "user_agent": audit.user_agent,
            "created_at": audit.created_at.isoformat() if audit.created_at else None
        }