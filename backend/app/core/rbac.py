"""
Role-Based Access Control (RBAC) Implementation

Provides comprehensive permission checking, resource-level access control,
and dynamic permission assignment for the Fernando platform.
"""

from typing import List, Dict, Set, Optional, Any, Callable
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from app.models.user_management import (
    User, Organization, UserRole, Permission, RolePermission,
    UserRoleAssignment, UserActivity, AccountSecurity
)
from app.models.user import User as LegacyUser
from app.core.config import settings


class PermissionChecker:
    """Manages permission checking and caching"""
    
    def __init__(self):
        self._permission_cache: Dict[str, Set[str]] = {}  # Cache by (user_id, org_id)
        self._cache_timeout = timedelta(minutes=5)
        self._last_cache_update: Dict[str, datetime] = {}
    
    def get_user_permissions(
        self, 
        user: User, 
        organization_id: Optional[str] = None,
        db: Session = None
    ) -> Set[str]:
        """Get all permissions for a user in a specific organization"""
        cache_key = f"{user.user_id}:{organization_id or 'global'}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._permission_cache.get(cache_key, set())
        
        # Get user role assignments
        if not db:
            raise ValueError("Database session required for permission resolution")
        
        query = db.query(RolePermission.permission_id).join(
            UserRoleAssignment, RolePermission.role_id == UserRoleAssignment.role_id
        ).filter(
            UserRoleAssignment.user_id == user.user_id,
            UserRoleAssignment.is_active == True
        )
        
        if organization_id:
            query = query.filter(
                (UserRoleAssignment.organization_id == organization_id) |
                (UserRoleAssignment.organization_id.is_(None))  # Global roles
            )
        else:
            query = query.filter(UserRoleAssignment.organization_id.is_(None))
        
        permission_ids = [p[0] for p in query.all()]
        
        # Get permission names
        permissions = db.query(Permission.name).filter(
            Permission.permission_id.in_(permission_ids)
        ).all()
        
        permission_names = {p[0] for p in permissions}
        
        # Cache the result
        self._permission_cache[cache_key] = permission_names
        self._last_cache_update[cache_key] = datetime.utcnow()
        
        return permission_names
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached permissions are still valid"""
        if cache_key not in self._permission_cache:
            return False
        
        last_update = self._last_cache_update.get(cache_key)
        if not last_update:
            return False
        
        return datetime.utcnow() - last_update < self._cache_timeout
    
    def invalidate_user_cache(self, user_id: str, organization_id: Optional[str] = None):
        """Invalidate permission cache for a user"""
        cache_key = f"{user_id}:{organization_id or 'global'}"
        if cache_key in self._permission_cache:
            del self._permission_cache[cache_key]
            del self._last_cache_update[cache_key]
    
    def check_permission(
        self, 
        user: User, 
        permission: str, 
        resource: Optional[str] = None,
        organization_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Check if user has specific permission"""
        if not user:
            return False
        
        # System admins have all permissions
        if self._is_system_admin(user, db):
            return True
        
        # Get user permissions
        user_permissions = self.get_user_permissions(user, organization_id, db)
        
        # Check for exact permission match
        if permission in user_permissions:
            return True
        
        # Check for wildcard permissions (e.g., "users.*" matches "users.read")
        for user_perm in user_permissions:
            if self._permission_matches_wildcard(permission, user_perm):
                return True
        
        return False
    
    def _is_system_admin(self, user: User, db: Session) -> bool:
        """Check if user is a system administrator"""
        # Check for admin role in any organization
        admin_assignment = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user.user_id,
            UserRoleAssignment.role_id == db.query(UserRole.role_id).filter(
                UserRole.name == "admin"
            ).scalar()
        ).first()
        
        return admin_assignment is not None
    
    def _permission_matches_wildcard(self, target: str, pattern: str) -> bool:
        """Check if target permission matches wildcard pattern"""
        if not pattern.endswith('.*'):
            return False
        
        base = pattern[:-2]  # Remove '.*'
        return target.startswith(f"{base}.")


class ResourceAccessChecker:
    """Resource-level access control"""
    
    @staticmethod
    def check_resource_ownership(
        user: User, 
        resource_user_id: str, 
        organization_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Check if user owns or has access to resource"""
        if not user or not resource_user_id:
            return False
        
        # User can always access their own resources
        if user.user_id == resource_user_id:
            return True
        
        # Check if user is in the same organization
        if organization_id and user.organization_id == organization_id:
            # Check if user has admin or manager role in the organization
            checker = PermissionChecker()
            return (
                checker.check_permission(user, "users.read", organization_id=organization_id, db=db) or
                checker.check_permission(user, "users.manage", organization_id=organization_id, db=db)
            )
        
        # Check for global admin permissions
        checker = PermissionChecker()
        return checker.check_permission(user, "users.admin", db=db)
    
    @staticmethod
    def check_organization_access(
        user: User, 
        target_organization_id: str,
        db: Session
    ) -> bool:
        """Check if user can access resources in specific organization"""
        if not user or not target_organization_id:
            return False
        
        # Users can access their own organization
        if user.organization_id == target_organization_id:
            return True
        
        # System admins can access any organization
        checker = PermissionChecker()
        return checker.check_permission(user, "organizations.admin", db=db)


class RBACManager:
    """Main RBAC manager for role and permission operations"""
    
    def __init__(self):
        self.permission_checker = PermissionChecker()
    
    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        organization_id: Optional[str] = None,
        assigned_by: str = None,
        expires_at: Optional[datetime] = None,
        db: Session = None
    ) -> UserRoleAssignment:
        """Assign a role to a user"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if assignment already exists
        existing = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.organization_id == organization_id
        ).first()
        
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.assigned_at = datetime.utcnow()
                existing.assigned_by = assigned_by
                existing.expires_at = expires_at
                db.commit()
                db.refresh(existing)
            return existing
        
        # Create new assignment
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            assigned_by=assigned_by,
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        
        # Invalidate permission cache
        self.permission_checker.invalidate_user_cache(user_id, organization_id)
        
        # Log activity
        self._log_role_assignment(assignment, "assigned", assigned_by, db)
        
        return assignment
    
    def revoke_role_from_user(
        self,
        user_id: str,
        role_id: str,
        organization_id: Optional[str] = None,
        revoked_by: str = None,
        db: Session = None
    ) -> bool:
        """Revoke a role from a user"""
        if not db:
            raise ValueError("Database session required")
        
        assignment = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.organization_id == organization_id
        ).first()
        
        if not assignment:
            return False
        
        assignment.is_active = False
        db.commit()
        
        # Invalidate permission cache
        self.permission_checker.invalidate_user_cache(user_id, organization_id)
        
        # Log activity
        self._log_role_assignment(assignment, "revoked", revoked_by, db)
        
        return True
    
    def create_role(
        self,
        name: str,
        description: str = None,
        level: int = 0,
        created_by: str = None,
        db: Session = None
    ) -> UserRole:
        """Create a new role"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if role already exists
        existing = db.query(UserRole).filter(UserRole.name == name).first()
        if existing:
            raise ValueError(f"Role '{name}' already exists")
        
        role = UserRole(
            name=name,
            description=description,
            level=level,
            is_system_role=False
        )
        
        db.add(role)
        db.commit()
        db.refresh(role)
        
        return role
    
    def grant_permission_to_role(
        self,
        role_id: str,
        permission_id: str,
        granted_by: str = None,
        db: Session = None
    ) -> RolePermission:
        """Grant a permission to a role"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if grant already exists
        existing = db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        
        if existing:
            return existing
        
        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
            granted_by=granted_by,
            granted_at=datetime.utcnow()
        )
        
        db.add(role_permission)
        db.commit()
        db.refresh(role_permission)
        
        # Invalidate all user permission caches for this role
        self._invalidate_role_cache(role_id, db)
        
        return role_permission
    
    def create_permission(
        self,
        name: str,
        description: str,
        resource: str,
        action: str,
        conditions: Dict[str, Any] = None,
        db: Session = None
    ) -> Permission:
        """Create a new permission"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if permission already exists
        existing = db.query(Permission).filter(Permission.name == name).first()
        if existing:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(
            name=name,
            description=description,
            resource=resource,
            action=action,
            conditions=conditions or {}
        )
        
        db.add(permission)
        db.commit()
        db.refresh(permission)
        
        return permission
    
    def _invalidate_role_cache(self, role_id: str, db: Session):
        """Invalidate permission cache for all users with a specific role"""
        assignments = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.is_active == True
        ).all()
        
        for assignment in assignments:
            self.permission_checker.invalidate_user_cache(
                assignment.user_id, 
                assignment.organization_id
            )
    
    def _log_role_assignment(
        self, 
        assignment: UserRoleAssignment, 
        action: str, 
        actor_id: str, 
        db: Session
    ):
        """Log role assignment activity"""
        activity = UserActivity(
            user_id=assignment.user_id,
            organization_id=assignment.organization_id,
            action=f"role_{action}",
            resource_type="role",
            resource_id=assignment.role_id,
            details={
                "assignment_id": assignment.assignment_id,
                "action": action,
                "role_id": assignment.role_id,
                "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None
            },
            ip_address=None,  # Will be set by middleware
            success=True
        )
        
        db.add(activity)
        db.commit()


# Permission checking decorators
def require_permission(
    permission: str, 
    resource: Optional[str] = None,
    organization_param: str = "organization_id"
):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from dependency
            from app.core.security import get_current_user
            from fastapi import Depends, Request
            
            # This will be called from FastAPI context
            request = kwargs.get('request')
            if not request:
                # Try to get from function arguments
                for arg_name in ['request', 'current_user', 'user']:
                    if arg_name in kwargs:
                        request = kwargs[arg_name]
                        break
            
            if not request or not hasattr(request, 'state'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request context not available"
                )
            
            user = getattr(request.state, 'user', None)
            db = getattr(request.state, 'db', None)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )
            
            # Get organization ID from parameters
            organization_id = kwargs.get(organization_param)
            
            # Check permission
            checker = PermissionChecker()
            if not checker.check_permission(user, permission, resource, organization_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(role_name: str, organization_param: str = "organization_id"):
    """Decorator to require specific role for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from app.core.security import get_current_user
            from fastapi import Request
            
            request = kwargs.get('request')
            if not request or not hasattr(request, 'state'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request context not available"
                )
            
            user = getattr(request.state, 'user', None)
            db = getattr(request.state, 'db', None)
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check if user has required role
            organization_id = kwargs.get(organization_param)
            
            checker = PermissionChecker()
            if not checker.check_permission(user, f"roles.{role_name}", organization_id=organization_id, db=db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role_name}' required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_ownership(resource_user_param: str = "user_id"):
    """Decorator to require ownership or admin access to resource"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request or not hasattr(request, 'state'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request context not available"
                )
            
            user = getattr(request.state, 'user', None)
            db = getattr(request.state, 'db', None)
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get target user ID
            target_user_id = kwargs.get(resource_user_param)
            organization_id = user.organization_id
            
            # Check ownership
            if not ResourceAccessChecker.check_resource_ownership(
                user, target_user_id, organization_id, db
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient access to resource"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global RBAC manager instance
rbac_manager = RBACManager()
permission_checker = PermissionChecker()


# Utility functions
def get_user_permissions_summary(user: User, db: Session) -> Dict[str, Any]:
    """Get comprehensive permissions summary for a user"""
    organization_roles = []
    global_roles = []
    
    # Get organization-specific roles
    org_assignments = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == user.user_id,
        UserRoleAssignment.organization_id == user.organization_id,
        UserRoleAssignment.is_active == True
    ).all()
    
    for assignment in org_assignments:
        if assignment.organization_id:
            organization_roles.append({
                "role_id": assignment.role_id,
                "role_name": assignment.role.name if assignment.role else "Unknown",
                "assigned_at": assignment.assigned_at.isoformat(),
                "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None
            })
    
    # Get global roles
    global_assignments = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == user.user_id,
        UserRoleAssignment.organization_id.is_(None),
        UserRoleAssignment.is_active == True
    ).all()
    
    for assignment in global_assignments:
        global_roles.append({
            "role_id": assignment.role_id,
            "role_name": assignment.role.name if assignment.role else "Unknown",
            "assigned_at": assignment.assigned_at.isoformat(),
            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None
        })
    
    # Get permissions
    permissions = permission_checker.get_user_permissions(
        user, user.organization_id, db
    )
    
    return {
        "user_id": user.user_id,
        "organization_roles": organization_roles,
        "global_roles": global_roles,
        "permissions": list(permissions),
        "organization_id": user.organization_id
    }