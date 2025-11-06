from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.enterprise import (
    Tenant, UserEnterprise, Group, GroupMember, Permission, 
    GroupPermission, UserPermission, JobQueue, QuotaUsage,
    ExportJob, AuditTrail, ScheduledTask, TaskRun, RateLimit,
    ComplianceReport
)
from app.models.user import User
from app.models.job import Job
from app.models.document import Document


class EnterpriseService:
    """Service for managing enterprise features"""
    
    def __init__(self, db: Session):
        self.db = db
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self):
        """Initialize default system permissions"""
        default_permissions = [
            # Job permissions
            ("job.create", "Create new jobs", "jobs", "create", "own"),
            ("job.read", "View jobs", "jobs", "read", "own"),
            ("job.update", "Edit job details", "jobs", "update", "own"),
            ("job.delete", "Delete jobs", "jobs", "delete", "own"),
            ("job.approve", "Approve jobs for posting", "jobs", "approve", "tenant"),
            ("job.read_all", "View all tenant jobs", "jobs", "read", "tenant"),
            
            # Document permissions
            ("document.create", "Upload documents", "documents", "create", "own"),
            ("document.read", "View documents", "documents", "read", "own"),
            ("document.update", "Edit document metadata", "documents", "update", "own"),
            ("document.delete", "Delete documents", "documents", "delete", "own"),
            ("document.read_all", "View all tenant documents", "documents", "read", "tenant"),
            
            # User management permissions
            ("user.read", "View user information", "users", "read", "tenant"),
            ("user.create", "Create new users", "users", "create", "tenant"),
            ("user.update", "Edit user details", "users", "update", "tenant"),
            ("user.delete", "Delete users", "users", "delete", "tenant"),
            
            # Admin permissions
            ("admin.tenant", "Manage tenant settings", "admin", "manage", "tenant"),
            ("admin.groups", "Manage groups and permissions", "admin", "manage", "tenant"),
            ("admin.reports", "Generate compliance reports", "admin", "manage", "tenant"),
            ("admin.system", "System administration", "admin", "manage", "all"),
            
            # Export/Import permissions
            ("export.create", "Create export jobs", "exports", "create", "own"),
            ("export.read", "View export history", "exports", "read", "own"),
            ("export.manage", "Manage all exports", "exports", "manage", "tenant"),
            
            # Audit permissions
            ("audit.read", "View audit logs", "audit", "read", "own"),
            ("audit.read_all", "View all audit logs", "audit", "read", "tenant"),
        ]
        
        for name, desc, resource, action, scope in default_permissions:
            existing = self.db.query(Permission).filter(Permission.name == name).first()
            if not existing:
                permission = Permission(
                    name=name,
                    description=desc,
                    resource=resource,
                    action=action,
                    scope=scope
                )
                self.db.add(permission)
        
        self.db.commit()
    
    def create_tenant(self, name: str, slug: str, description: str = None, 
                     subscription_plan: str = "basic", max_users: int = 10,
                     max_jobs_per_month: int = 1000, max_storage_gb: int = 5) -> Tenant:
        """Create a new tenant"""
        tenant = Tenant(
            name=name,
            slug=slug,
            description=description,
            subscription_plan=subscription_plan,
            max_users=max_users,
            max_jobs_per_month=max_jobs_per_month,
            max_storage_gb=max_storage_gb
        )
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        
        # Create default groups
        self._create_default_groups(tenant.tenant_id)
        
        # Create quota usage record
        quota = QuotaUsage(tenant_id=tenant.tenant_id)
        self.db.add(quota)
        self.db.commit()
        
        return tenant
    
    def _create_default_groups(self, tenant_id: str):
        """Create default groups for a new tenant"""
        # Administrators group
        admin_group = Group(
            tenant_id=tenant_id,
            name="Administrators",
            description="Full access to all tenant features",
            is_system=True
        )
        self.db.add(admin_group)
        self.db.flush()
        
        # Users group
        user_group = Group(
            tenant_id=tenant_id,
            name="Users",
            description="Basic user access",
            is_system=True
        )
        self.db.add(user_group)
        self.db.flush()
        
        # Auditors group
        auditor_group = Group(
            tenant_id=tenant_id,
            name="Auditors",
            description="Read-only access to audit logs and reports",
            is_system=True
        )
        self.db.add(auditor_group)
        self.db.commit()
    
    def get_user_permissions(self, user_id: str, tenant_id: str) -> List[str]:
        """Get all permissions for a user (direct + group-based)"""
        # Get direct user permissions
        user_perms = self.db.query(UserPermission.permission_id).filter(
            UserPermission.user_id == user_id
        ).all()
        
        # Get group permissions
        group_perms = self.db.query(GroupPermission.permission_id).join(GroupMember).filter(
            GroupMember.user_id == user_id
        ).all()
        
        # Combine permissions
        all_perm_ids = [p[0] for p in user_perms] + [p[0] for p in group_perms]
        
        if not all_perm_ids:
            return []
        
        # Get permission names
        permissions = self.db.query(Permission.name).filter(
            Permission.permission_id.in_(all_perm_ids)
        ).all()
        
        return [p[0] for p in permissions]
    
    def has_permission(self, user_id: str, tenant_id: str, permission_name: str) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user_id, tenant_id)
        return permission_name in permissions
    
    def check_quota_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Check if tenant has exceeded quota limits"""
        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.tenant_id == tenant_id
        ).first()
        
        if not quota:
            return {"within_limits": True, "usage": {}}
        
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return {"within_limits": False, "error": "Tenant not found"}
        
        # Check job limits
        current_month_jobs = quota.jobs_processed
        max_jobs = tenant.max_jobs_per_month
        job_limit_exceeded = current_month_jobs >= max_jobs
        
        # Check user limits
        current_users = self.db.query(UserEnterprise).filter(
            UserEnterprise.tenant_id == tenant_id,
            UserEnterprise.status == "active"
        ).count()
        max_users = tenant.max_users
        user_limit_exceeded = current_users >= max_users
        
        # Check storage limits
        storage_used_gb = quota.storage_used_mb / 1024
        max_storage = tenant.max_storage_gb
        storage_limit_exceeded = storage_used_gb >= max_storage
        
        within_limits = not (job_limit_exceeded or user_limit_exceeded or storage_limit_exceeded)
        
        return {
            "within_limits": within_limits,
            "usage": {
                "jobs": {"current": current_month_jobs, "limit": max_jobs},
                "users": {"current": current_users, "limit": max_users},
                "storage_gb": {"current": round(storage_used_gb, 2), "limit": max_storage}
            },
            "exceeded": {
                "jobs": job_limit_exceeded,
                "users": user_limit_exceeded,
                "storage": storage_limit_exceeded
            }
        }
    
    def increment_quota_usage(self, tenant_id: str, jobs: int = 0, 
                            storage_mb: float = 0, api_calls: int = 0):
        """Increment quota usage"""
        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.tenant_id == tenant_id
        ).first()
        
        if not quota:
            quota = QuotaUsage(tenant_id=tenant_id)
            self.db.add(quota)
        
        # Reset monthly counters if it's a new month
        now = datetime.utcnow()
        if (quota.current_month != now.month or quota.current_year != now.year):
            quota.current_month = now.month
            quota.current_year = now.year
            quota.jobs_processed = 0
            quota.api_calls_made = 0
        
        quota.jobs_processed += jobs
        quota.storage_used_mb += storage_mb
        quota.api_calls_made += api_calls
        
        self.db.commit()
    
    def create_audit_log(self, tenant_id: str, user_id: str, action: str,
                        resource_type: str, resource_id: str = None,
                        old_values: Dict = None, new_values: Dict = None,
                        ip_address: str = None, user_agent: str = None,
                        risk_level: str = "low", compliance_tags: List[str] = None):
        """Create audit log entry"""
        audit = AuditTrail(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            risk_level=risk_level,
            compliance_tags=compliance_tags or []
        )
        self.db.add(audit)
        self.db.commit()
    
    def get_audit_logs(self, tenant_id: str, user_id: str = None, 
                      resource_type: str = None, risk_level: str = None,
                      limit: int = 100, offset: int = 0) -> List[AuditTrail]:
        """Get audit logs with filtering"""
        query = self.db.query(AuditTrail).filter(
            AuditTrail.tenant_id == tenant_id
        )
        
        if user_id:
            query = query.filter(AuditTrail.user_id == user_id)
        if resource_type:
            query = query.filter(AuditTrail.resource_type == resource_type)
        if risk_level:
            query = query.filter(AuditTrail.risk_level == risk_level)
        
        return query.order_by(desc(AuditTrail.created_at)).offset(offset).limit(limit).all()
    
    def create_export_job(self, tenant_id: str, user_id: str, export_type: str,
                         export_format: str, job_id: str = None,
                         filters: Dict = None) -> ExportJob:
        """Create export job"""
        export_job = ExportJob(
            tenant_id=tenant_id,
            job_id=job_id,
            export_type=export_type,
            export_format=export_format,
            filters=filters or {},
            created_by=user_id
        )
        self.db.add(export_job)
        self.db.commit()
        self.db.refresh(export_job)
        
        return export_job
    
    def create_scheduled_task(self, tenant_id: str, user_id: str, name: str,
                            task_type: str, schedule_cron: str = None,
                            schedule_interval: int = None, config: Dict = None) -> ScheduledTask:
        """Create scheduled task"""
        task = ScheduledTask(
            tenant_id=tenant_id,
            name=name,
            task_type=task_type,
            schedule_cron=schedule_cron,
            schedule_interval=schedule_interval,
            config=config or {},
            created_by=user_id
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def get_rate_limit_status(self, tenant_id: str, endpoint: str) -> Dict[str, Any]:
        """Check rate limiting status for an endpoint"""
        # Find matching rate limit rule
        rate_limit = self.db.query(RateLimit).filter(
            and_(
                RateLimit.tenant_id == tenant_id,
                RateLimit.endpoint_pattern == endpoint,
                RateLimit.is_active == True
            )
        ).first()
        
        if not rate_limit:
            return {"allowed": True, "remaining": -1}
        
        # This would typically check Redis or another cache for current usage
        # For now, return basic info
        return {
            "allowed": True,
            "limit_per_hour": rate_limit.requests_per_hour,
            "limit_per_day": rate_limit.requests_per_day,
            "burst_limit": rate_limit.burst_limit
        }
    
    def get_compliance_summary(self, tenant_id: str, start_date: datetime, 
                              end_date: datetime) -> Dict[str, Any]:
        """Get compliance summary for reporting period"""
        # Count audit events by type
        audit_counts = self.db.query(
            AuditTrail.action,
            func.count(AuditTrail.audit_id)
        ).filter(
            and_(
                AuditTrail.tenant_id == tenant_id,
                AuditTrail.created_at >= start_date,
                AuditTrail.created_at <= end_date
            )
        ).group_by(AuditTrail.action).all()
        
        # Count risk events
        risk_events = self.db.query(
            AuditTrail.risk_level,
            func.count(AuditTrail.audit_id)
        ).filter(
            and_(
                AuditTrail.tenant_id == tenant_id,
                AuditTrail.created_at >= start_date,
                AuditTrail.created_at <= end_date
            )
        ).group_by(AuditTrail.risk_level).all()
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "events_by_action": dict(audit_counts),
            "events_by_risk": dict(risk_events),
            "total_events": sum(count for _, count in audit_counts) if audit_counts else 0,
            "high_risk_events": sum(count for risk, count in risk_events if risk in ["high", "critical"])
        }
