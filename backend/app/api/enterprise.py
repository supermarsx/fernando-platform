from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.services.enterprise_service import EnterpriseService
from app.models.user import User
from app.models.enterprise import Tenant, UserEnterprise, Group, Permission

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tenant"""
    enterprise_service = EnterpriseService(db)
    
    # Check if user has admin permissions
    if current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create tenants"
        )
    
    tenant = enterprise_service.create_tenant(
        name=tenant_data["name"],
        slug=tenant_data["slug"],
        description=tenant_data.get("description"),
        subscription_plan=tenant_data.get("subscription_plan", "basic"),
        max_users=tenant_data.get("max_users", 10),
        max_jobs_per_month=tenant_data.get("max_jobs_per_month", 1000),
        max_storage_gb=tenant_data.get("max_storage_gb", 5)
    )
    
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status
    }


@router.get("/tenants")
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all tenants (admin only)"""
    if not current_user.roles or "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    tenants = db.query(Tenant).offset(offset).limit(limit).all()
    
    return [
        {
            "tenant_id": t.tenant_id,
            "name": t.name,
            "slug": t.slug,
            "status": t.status,
            "subscription_plan": t.subscription_plan,
            "created_at": t.created_at.isoformat()
        }
        for t in tenants
    ]


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tenant details"""
    # Check if user belongs to this tenant or is admin
    if current_user.tenant_id != tenant_id and "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "slug": tenant.slug,
        "description": tenant.description,
        "status": tenant.status,
        "subscription_plan": tenant.subscription_plan,
        "features": tenant.features,
        "settings": tenant.settings,
        "created_at": tenant.created_at.isoformat()
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update tenant settings"""
    enterprise_service = EnterpriseService(db)
    
    # Check permissions
    if current_user.tenant_id != tenant_id and "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields
    for field, value in updates.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)
    
    tenant.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Tenant updated successfully"}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user permissions"""
    enterprise_service = EnterpriseService(db)
    
    # Check if user can view permissions
    if current_user.user_id != user_id and "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    permissions = enterprise_service.get_user_permissions(user_id, current_user.tenant_id)
    
    return {"permissions": permissions}


@router.post("/permissions/check")
async def check_permission(
    permission_data: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has specific permission"""
    enterprise_service = EnterpriseService(db)
    
    user_id = permission_data.get("user_id", current_user.user_id)
    permission_name = permission_data.get("permission_name")
    
    if not permission_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="permission_name is required"
        )
    
    has_permission = enterprise_service.has_permission(
        user_id, current_user.tenant_id, permission_name
    )
    
    return {"has_permission": has_permission}


@router.get("/quota/check")
async def check_quota_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check current tenant quota usage"""
    enterprise_service = EnterpriseService(db)
    
    quota_status = enterprise_service.check_quota_limits(current_user.tenant_id)
    
    return quota_status


@router.post("/audit/log")
async def create_audit_log(
    audit_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create audit log entry"""
    enterprise_service = EnterpriseService(db)
    
    enterprise_service.create_audit_log(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action=audit_data["action"],
        resource_type=audit_data["resource_type"],
        resource_id=audit_data.get("resource_id"),
        old_values=audit_data.get("old_values"),
        new_values=audit_data.get("new_values"),
        ip_address=audit_data.get("ip_address"),
        user_agent=audit_data.get("user_agent"),
        risk_level=audit_data.get("risk_level", "low"),
        compliance_tags=audit_data.get("compliance_tags", [])
    )
    
    return {"message": "Audit log created successfully"}


@router.get("/audit/logs")
async def get_audit_logs(
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering"""
    enterprise_service = EnterpriseService(db)
    
    logs = enterprise_service.get_audit_logs(
        tenant_id=current_user.tenant_id,
        user_id=user_id,
        resource_type=resource_type,
        risk_level=risk_level,
        limit=limit,
        offset=offset
    )
    
    return [
        {
            "audit_id": log.audit_id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "risk_level": log.risk_level,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
            "compliance_tags": log.compliance_tags
        }
        for log in logs
    ]


@router.get("/compliance/summary")
async def get_compliance_summary(
    period_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get compliance summary for reporting period"""
    enterprise_service = EnterpriseService(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    summary = enterprise_service.get_compliance_summary(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return summary


@router.get("/rate-limit/{endpoint}")
async def get_rate_limit_status(
    endpoint: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check rate limiting status for an endpoint"""
    enterprise_service = EnterpriseService(db)
    
    status = enterprise_service.get_rate_limit_status(
        tenant_id=current_user.tenant_id,
        endpoint=endpoint
    )
    
    return status


@router.post("/rate-limit")
async def create_rate_limit(
    rate_limit_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create rate limit rule"""
    from app.models.enterprise import RateLimit
    
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    rate_limit = RateLimit(
        tenant_id=current_user.tenant_id,
        endpoint_pattern=rate_limit_data["endpoint_pattern"],
        requests_per_hour=rate_limit_data.get("requests_per_hour", 1000),
        requests_per_day=rate_limit_data.get("requests_per_day", 10000),
        burst_limit=rate_limit_data.get("burst_limit", 50)
    )
    
    db.add(rate_limit)
    db.commit()
    
    return {"message": "Rate limit created successfully"}


@router.get("/groups")
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all groups in tenant"""
    groups = db.query(Group).filter(Group.tenant_id == current_user.tenant_id).all()
    
    return [
        {
            "group_id": g.group_id,
            "name": g.name,
            "description": g.description,
            "is_system": g.is_system,
            "member_count": len(g.members),
            "created_at": g.created_at.isoformat()
        }
        for g in groups
    ]


@router.get("/permissions")
async def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available permissions"""
    # Only admins can view all permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    permissions = db.query(Permission).all()
    
    return [
        {
            "permission_id": p.permission_id,
            "name": p.name,
            "description": p.description,
            "resource": p.resource,
            "action": p.action,
            "scope": p.scope
        }
        for p in permissions
    ]
