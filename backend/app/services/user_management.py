"""
User Management Service

Comprehensive user management service providing CRUD operations, role management,
activity tracking, and integration with existing authentication systems.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import uuid
import secrets
import string
from passlib.context import CryptContext

from app.models.user_management import (
    User as ExtendedUser, Organization, UserRole, Permission, RolePermission,
    UserRoleAssignment, UserSession, UserInvitation, UserActivity, 
    UserPreferences, AccountSecurity, AuditLog
)
from app.models.user import User as LegacyUser
from app.core.security import get_password_hash, verify_password
from app.core.rbac import (
    rbac_manager, permission_checker, ResourceAccessChecker,
    get_user_permissions_summary
)
from app.core.config import settings


class UserManagementService:
    """Comprehensive user management service"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def create_user(
        self,
        email: str,
        full_name: str,
        password: str,
        organization_id: Optional[str] = None,
        roles: List[str] = None,
        created_by: Optional[str] = None,
        db: Session = None,
        auto_assign_default_roles: bool = True
    ) -> ExtendedUser:
        """Create a new user with extended management capabilities"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if user already exists
        existing = db.query(ExtendedUser).filter(
            or_(
                ExtendedUser.email == email,
                ExtendedUser.user_id == email  # Support legacy user_id lookups
            )
        ).first()
        
        if existing:
            raise ValueError(f"User with email '{email}' already exists")
        
        # Create new user
        user_id = str(uuid.uuid4())
        user = ExtendedUser(
            user_id=user_id,
            email=email.lower(),
            password_hash=get_password_hash(password),
            full_name=full_name,
            organization_id=organization_id,
            status="active",
            roles=["uploader"],  # Maintain backward compatibility
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            email_verified=False,
            onboarding_completed=False
        )
        
        db.add(user)
        db.flush()  # Get the user ID
        
        # Create default preferences
        preferences = UserPreferences(user_id=user_id)
        db.add(preferences)
        
        # Create security account
        security = AccountSecurity(user_id=user_id)
        db.add(security)
        
        # Assign roles if specified
        if roles:
            for role_name in roles:
                role = db.query(UserRole).filter(UserRole.name == role_name).first()
                if role:
                    rbac_manager.assign_role_to_user(
                        user_id=user_id,
                        role_id=role.role_id,
                        organization_id=organization_id,
                        assigned_by=created_by,
                        db=db
                    )
        elif auto_assign_default_roles:
            # Assign default roles based on organization settings
            default_roles = ["user"]  # Default role
            for role_name in default_roles:
                role = db.query(UserRole).filter(UserRole.name == role_name).first()
                if role:
                    rbac_manager.assign_role_to_user(
                        user_id=user_id,
                        role_id=role.role_id,
                        organization_id=organization_id,
                        assigned_by=created_by,
                        db=db
                    )
        
        db.commit()
        db.refresh(user)
        
        # Log user creation activity
        self._log_activity(
            user_id=user_id,
            organization_id=organization_id,
            action="user_created",
            resource_type="user",
            resource_id=user_id,
            details={
                "email": email,
                "full_name": full_name,
                "organization_id": organization_id,
                "auto_roles_assigned": auto_assign_default_roles
            },
            db=db
        )
        
        return user
    
    def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None,
        db: Session = None
    ) -> ExtendedUser:
        """Update user information"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Store old values for audit log
        old_values = {
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
            "organization_id": user.organization_id,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "onboarding_completed": user.onboarding_completed
        }
        
        # Update allowed fields
        updatable_fields = [
            "email", "full_name", "status", "organization_id", 
            "email_verified", "phone_verified", "onboarding_completed"
        ]
        
        for field, value in updates.items():
            if field in updatable_fields:
                if field == "email" and value:
                    # Check for email conflicts
                    existing = db.query(ExtendedUser).filter(
                        and_(
                            ExtendedUser.email == value.lower(),
                            ExtendedUser.user_id != user_id
                        )
                    ).first()
                    if existing:
                        raise ValueError(f"Email '{value}' is already in use")
                
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        # Log activity
        new_values = {
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
            "organization_id": user.organization_id,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "onboarding_completed": user.onboarding_completed
        }
        
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="user_updated",
            resource_type="user",
            resource_id=user_id,
            details={"updates": updates},
            old_values=old_values,
            new_values=new_values,
            db=db
        )
        
        return user
    
    def deactivate_user(
        self,
        user_id: str,
        reason: str = "Manual deactivation",
        deactivated_by: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """Deactivate a user account"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Update user status
        user.status = "inactive"
        user.updated_at = datetime.utcnow()
        
        # Deactivate all role assignments
        assignments = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == True
        ).all()
        
        for assignment in assignments:
            assignment.is_active = False
        
        # End all active sessions
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.logout_at = datetime.utcnow()
        
        db.commit()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="user_deactivated",
            resource_type="user",
            resource_id=user_id,
            details={
                "reason": reason,
                "deactivated_by": deactivated_by,
                "sessions_terminated": len(sessions)
            },
            db=db
        )
        
        return True
    
    def reactivate_user(
        self,
        user_id: str,
        reactivated_by: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """Reactivate a user account"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        user.status = "active"
        user.updated_at = datetime.utcnow()
        
        # Reactivate role assignments that don't have expiration
        assignments = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == False,
            or_(
                UserRoleAssignment.expires_at.is_(None),
                UserRoleAssignment.expires_at > datetime.utcnow()
            )
        ).all()
        
        for assignment in assignments:
            assignment.is_active = True
        
        db.commit()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="user_reactivated",
            resource_type="user",
            resource_id=user_id,
            details={"reactivated_by": reactivated_by},
            db=db
        )
        
        return True
    
    def delete_user(
        self,
        user_id: str,
        deleted_by: Optional[str] = None,
        permanent: bool = False,
        db: Session = None
    ) -> bool:
        """Delete a user (soft delete by default for data integrity)"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        if permanent:
            # Hard delete - remove all user data
            # This is dangerous and should be used with caution
            
            # Remove user sessions
            db.query(UserSession).filter(UserSession.user_id == user_id).delete()
            
            # Remove role assignments
            db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == user_id).delete()
            
            # Remove user preferences
            db.query(UserPreferences).filter(UserPreferences.user_id == user_id).delete()
            
            # Remove account security
            db.query(AccountSecurity).filter(AccountSecurity.user_id == user_id).delete()
            
            # Remove user activities (with caution - might be needed for audit)
            # db.query(UserActivity).filter(UserActivity.user_id == user_id).delete()
            
            # Finally remove the user
            db.delete(user)
            
        else:
            # Soft delete - mark as deleted but preserve data
            user.status = "deleted"
            user.email = f"deleted_{user_id}@deleted.local"
            user.full_name = "Deleted User"
            user.organization_id = None
            
            # Deactivate all role assignments
            assignments = db.query(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user_id
            ).all()
            
            for assignment in assignments:
                assignment.is_active = False
            
            # End all sessions
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).all()
            
            for session in sessions:
                session.is_active = False
                session.logout_at = datetime.utcnow()
        
        db.commit()
        
        # Log activity
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="user_deleted",
            resource_type="user",
            resource_id=user_id,
            details={
                "permanent": permanent,
                "deleted_by": deleted_by
            },
            db=db
        )
        
        return True
    
    def get_user_by_id(
        self,
        user_id: str,
        include_relationships: bool = False,
        db: Session = None
    ) -> Optional[ExtendedUser]:
        """Get user by ID with optional relationship loading"""
        if not db:
            raise ValueError("Database session required")
        
        query = db.query(ExtendedUser)
        
        if include_relationships:
            query = query.options(
                # Load relationships
                # ExtendedUser.organization,
                # ExtendedUser.user_role_assignments,
                # ExtendedUser.user_preferences,
                # ExtendedUser.account_security
            )
        
        return query.filter(ExtendedUser.user_id == user_id).first()
    
    def get_user_by_email(self, email: str, db: Session = None) -> Optional[ExtendedUser]:
        """Get user by email address"""
        if not db:
            raise ValueError("Database session required")
        
        return db.query(ExtendedUser).filter(
            ExtendedUser.email == email.lower()
        ).first()
    
    def list_users(
        self,
        organization_id: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        db: Session = None
    ) -> Tuple[List[ExtendedUser], int]:
        """List users with filtering and pagination"""
        if not db:
            raise ValueError("Database session required")
        
        query = db.query(ExtendedUser)
        
        # Apply filters
        if organization_id:
            query = query.filter(ExtendedUser.organization_id == organization_id)
        
        if status:
            query = query.filter(ExtendedUser.status == status)
        
        if role:
            # Filter by role assignments
            role_assignments = db.query(UserRoleAssignment.user_id).join(
                UserRole, UserRoleAssignment.role_id == UserRole.role_id
            ).filter(
                UserRole.name == role,
                UserRoleAssignment.is_active == True
            )
            query = query.filter(ExtendedUser.user_id.in_(role_assignments))
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    ExtendedUser.email.ilike(search_term),
                    ExtendedUser.full_name.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        users = query.order_by(desc(ExtendedUser.created_at)).offset(offset).limit(per_page).all()
        
        return users, total
    
    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
        db: Session = None
    ) -> bool:
        """Change user password with verification"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Verify old password
        if not verify_password(old_password, user.password_hash):
            # Log failed password change attempt
            self._log_activity(
                user_id=user_id,
                organization_id=user.organization_id,
                action="password_change_failed",
                resource_type="user",
                resource_id=user_id,
                details={"reason": "invalid_old_password"},
                success=False,
                db=db
            )
            return False
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        user.last_password_change = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # Update security preferences
        if user.account_security:
            user.account_security.password_failed_attempts = 0
            user.account_security.password_locked_until = None
            user.account_security.password_change_required = False
        
        db.commit()
        
        # Log successful password change
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="password_changed",
            resource_type="user",
            resource_id=user_id,
            db=db
        )
        
        return True
    
    def reset_password(
        self,
        user_id: str,
        new_password: str,
        reset_by: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """Reset user password (admin function)"""
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        user.last_password_change = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # Force password change on next login
        if user.account_security:
            user.account_security.password_change_required = True
        
        db.commit()
        
        # Log password reset
        self._log_activity(
            user_id=user_id,
            organization_id=user.organization_id,
            action="password_reset",
            resource_type="user",
            resource_id=user_id,
            details={"reset_by": reset_by},
            db=db
        )
        
        return True
    
    def invite_user(
        self,
        email: str,
        role_id: str,
        organization_id: str,
        invited_by: str,
        message: Optional[str] = None,
        expires_in_days: int = 7,
        db: Session = None
    ) -> UserInvitation:
        """Invite a user to join the organization"""
        if not db:
            raise ValueError("Database session required")
        
        # Check if user already exists
        existing_user = self.get_user_by_email(email, db)
        if existing_user:
            raise ValueError(f"User with email '{email}' already exists")
        
        # Check for pending invitation
        existing_invitation = db.query(UserInvitation).filter(
            UserInvitation.email == email.lower(),
            UserInvitation.organization_id == organization_id,
            UserInvitation.status == "pending"
        ).first()
        
        if existing_invitation:
            raise ValueError(f"Pending invitation already exists for '{email}'")
        
        # Generate invitation token
        token = secrets.token_urlsafe(32)
        
        # Create invitation
        invitation = UserInvitation(
            organization_id=organization_id,
            email=email.lower(),
            role_id=role_id,
            invited_by=invited_by,
            token=token,
            message=message,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            status="pending"
        )
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        # Log invitation
        self._log_activity(
            user_id=invited_by,
            organization_id=organization_id,
            action="user_invited",
            resource_type="invitation",
            resource_id=invitation.invitation_id,
            details={
                "email": email,
                "role_id": role_id,
                "expires_at": invitation.expires_at.isoformat()
            },
            db=db
        )
        
        return invitation
    
    def accept_invitation(
        self,
        token: str,
        full_name: str,
        password: str,
        db: Session = None
    ) -> Tuple[ExtendedUser, UserInvitation]:
        """Accept a user invitation"""
        if not db:
            raise ValueError("Database session required")
        
        # Get invitation
        invitation = db.query(UserInvitation).filter(
            UserInvitation.token == token,
            UserInvitation.status == "pending"
        ).first()
        
        if not invitation:
            raise ValueError("Invalid or expired invitation")
        
        if invitation.expires_at < datetime.utcnow():
            invitation.status = "expired"
            db.commit()
            raise ValueError("Invitation has expired")
        
        # Check if user already exists
        existing_user = self.get_user_by_email(invitation.email, db)
        if existing_user:
            invitation.status = "cancelled"
            db.commit()
            raise ValueError(f"User with email '{invitation.email}' already exists")
        
        # Create user
        user = self.create_user(
            email=invitation.email,
            full_name=full_name,
            password=password,
            organization_id=invitation.organization_id,
            created_by=invitation.invited_by,
            db=db,
            auto_assign_default_roles=False
        )
        
        # Assign invited role
        if invitation.role_id:
            rbac_manager.assign_role_to_user(
                user_id=user.user_id,
                role_id=invitation.role_id,
                organization_id=invitation.organization_id,
                assigned_by=invitation.invited_by,
                db=db
            )
        
        # Update invitation
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_user_id = user.user_id
        
        db.commit()
        
        # Log invitation acceptance
        self._log_activity(
            user_id=user.user_id,
            organization_id=invitation.organization_id,
            action="invitation_accepted",
            resource_type="invitation",
            resource_id=invitation.invitation_id,
            details={
                "invitation_id": invitation.invitation_id,
                "email": invitation.email
            },
            db=db
        )
        
        return user, invitation
    
    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        db: Session = None
    ) -> List[UserSession]:
        """Get user sessions"""
        if not db:
            raise ValueError("Database session required")
        
        query = db.query(UserSession).filter(UserSession.user_id == user_id)
        
        if active_only:
            query = query.filter(UserSession.is_active == True)
        
        return query.order_by(desc(UserSession.last_activity_at)).all()
    
    def terminate_session(
        self,
        session_id: str,
        terminated_by: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """Terminate a user session"""
        if not db:
            raise ValueError("Database session required")
        
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()
        
        if not session:
            return False
        
        session.is_active = False
        session.logout_at = datetime.utcnow()
        db.commit()
        
        # Log session termination
        self._log_activity(
            user_id=session.user_id,
            organization_id=session.organization_id,
            action="session_terminated",
            resource_type="session",
            resource_id=session_id,
            details={"terminated_by": terminated_by},
            db=db
        )
        
        return True
    
    def get_user_activity(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        db: Session = None
    ) -> List[UserActivity]:
        """Get user activity history"""
        if not db:
            raise ValueError("Database session required")
        
        query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
        
        if organization_id:
            query = query.filter(UserActivity.organization_id == organization_id)
        
        if action:
            query = query.filter(UserActivity.action == action)
        
        if start_date:
            query = query.filter(UserActivity.created_at >= start_date)
        
        if end_date:
            query = query.filter(UserActivity.created_at <= end_date)
        
        return query.order_by(desc(UserActivity.created_at)).limit(limit).all()
    
    def get_user_statistics(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        if not db:
            raise ValueError("Database session required")
        
        # Basic user info
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Session statistics
        total_sessions = db.query(UserSession).filter(UserSession.user_id == user_id).count()
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).count()
        
        # Activity statistics
        activity_last_24h = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        activity_last_7d = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        # Role assignments
        role_assignments = db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == True
        ).count()
        
        # Login statistics
        logins_last_24h = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
            UserActivity.action == "login",
            UserActivity.created_at >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        # Last login
        last_login = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
            UserActivity.action == "login"
        ).order_by(desc(UserActivity.created_at)).first()
        
        return {
            "user_id": user_id,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
            "organization_id": user.organization_id,
            "created_at": user.created_at.isoformat(),
            "last_login": last_login.created_at.isoformat() if last_login else None,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "activity_last_24h": activity_last_24h,
            "activity_last_7d": activity_last_7d,
            "logins_last_24h": logins_last_24h,
            "active_role_assignments": role_assignments,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "mfa_enabled": user.account_security.two_factor_enabled if user.account_security else False,
            "password_age_days": (datetime.utcnow() - user.last_password_change).days if user.last_password_change else None
        }
    
    def _log_activity(
        self,
        user_id: str,
        organization_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any] = None,
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None,
        ip_address: str = None,
        user_agent: str = None,
        session_id: str = None,
        duration_ms: int = None,
        db: Session = None
    ):
        """Log user activity"""
        if not db:
            return
        
        activity = UserActivity(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        db.add(activity)
        db.commit()
        
        # Also create audit log entry for significant actions
        significant_actions = [
            "user_created", "user_updated", "user_deleted", "user_deactivated",
            "password_changed", "password_reset", "role_assigned", "role_revoked"
        ]
        
        if action in significant_actions:
            audit_log = AuditLog(
                actor_user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                organization_id=organization_id,
                session_id=session_id,
                success=success,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_log)
            db.commit()
    
    # ============================================================================
    # CREDIT INTEGRATION METHODS
    # ============================================================================
    
    def create_user_with_credit_allocation(
        self,
        email: str,
        full_name: str,
        password: str,
        organization_id: Optional[str] = None,
        roles: List[str] = None,
        created_by: Optional[str] = None,
        db: Session = None,
        initial_credit_allocation: float = 1000.0,
        credit_policies: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create user with automatic credit account and allocation
        
        Args:
            email: User email
            full_name: User full name
            password: User password
            organization_id: Organization ID
            roles: User roles
            created_by: User who created this user
            db: Database session
            initial_credit_allocation: Initial credit allocation
            credit_policies: Credit policies to apply
        
        Returns:
            Dictionary with user and credit account info
        """
        if not db:
            raise ValueError("Database session required")
        
        # Create user first
        user = self.create_user(
            email=email,
            full_name=full_name,
            password=password,
            organization_id=organization_id,
            roles=roles,
            created_by=created_by,
            db=db,
            auto_assign_default_roles=True
        )
        
        # Create credit account
        from app.services.credit_service import CreditService
        from app.schemas.credit_schemas import CreditAccountCreate, CreditPolicyCreate
        from app.models.credit import CreditPolicyType
        
        credit_service = CreditService(db)
        
        try:
            # Create credit account
            credit_account = credit_service.create_credit_account(
                CreditAccountCreate(
                    user_id=user.user_id,  # Keep as UUID string for now
                    organization_id=organization_id,
                    auto_renew=True
                )
            )
            
            # Allocate initial credits
            credit_service.add_credits(
                user_id=user.user_id,  # Use UUID string
                amount=initial_credit_allocation,
                transaction_type="allocation",
                description=f"Initial credit allocation for new user: {email}",
                reference_id=user.user_id,
                reference_type="user_creation",
                metadata={
                    "user_id": user.user_id,
                    "created_by": created_by,
                    "allocation_source": "user_creation"
                }
            )
            
            # Create credit policies if specified
            if credit_policies:
                for policy_data in credit_policies:
                    policy = CreditPolicyCreate(
                        account_id=credit_account.id,
                        policy_type=CreditPolicyType(policy_data.get("type", "llm_tokens")),
                        name=policy_data.get("name", "Default Policy"),
                        description=policy_data.get("description"),
                        monthly_allocation=policy_data.get("monthly_allocation"),
                        auto_replenish=policy_data.get("auto_replenish", False),
                        minimum_balance=policy_data.get("minimum_balance", 0.0),
                        cost_per_unit=policy_data.get("cost_per_unit")
                    )
                    
                    credit_service.create_credit_policy(policy)
            
            # Log credit allocation
            self._log_activity(
                user_id=user.user_id,
                organization_id=organization_id,
                action="credits_allocated",
                resource_type="credit_account",
                resource_id=str(credit_account.id),
                details={
                    "user_id": user.user_id,
                    "initial_allocation": initial_credit_allocation,
                    "credit_account_id": credit_account.id,
                    "policies_created": len(credit_policies) if credit_policies else 0
                },
                db=db
            )
            
            return {
                "user": user,
                "credit_account": credit_account,
                "initial_credit_allocation": initial_credit_allocation,
                "credit_policies_created": len(credit_policies) if credit_policies else 0
            }
        
        except Exception as e:
            # If credit setup fails, roll back user creation
            db.delete(user)
            db.commit()
            raise ValueError(f"Failed to setup credit account: {str(e)}")
    
    def allocate_credits_from_organization_pool(
        self,
        organization_id: str,
        user_id: str,
        amount: float,
        allocated_by: str,
        reason: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Allocate credits from organization pool to specific user
        
        Args:
            organization_id: Organization ID
            user_id: Target user ID
            amount: Credit amount to allocate
            allocated_by: User allocating credits
            reason: Allocation reason
            db: Database session
        
        Returns:
            Allocation result
        """
        if not db:
            raise ValueError("Database session required")
        
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        
        # Get organization credit pool
        org_credit_account = credit_service.get_organization_credit_account(int(organization_id))
        if not org_credit_account:
            raise ValueError("Organization credit pool not found")
        
        # Check if organization has sufficient credits
        if org_credit_account.current_balance < amount:
            raise ValueError("Insufficient credits in organization pool")
        
        # Verify target user exists and belongs to organization
        user = db.query(ExtendedUser).filter(
            ExtendedUser.user_id == user_id,
            ExtendedUser.organization_id == organization_id
        ).first()
        
        if not user:
            raise ValueError(f"User '{user_id}' not found in organization '{organization_id}'")
        
        try:
            # Get or create user credit account
            target_user_id = int(user.user_id.replace('-', ''), 16)  # Convert UUID to int
            user_credit_account = credit_service.get_credit_account(target_user_id)
            
            if not user_credit_account:
                # Create user credit account
                user_credit_account = credit_service.create_credit_account(
                    CreditAccountCreate(
                        user_id=target_user_id,
                        organization_id=int(organization_id)
                    )
                )
            
            # Allocate credits to user
            credit_service.add_credits(
                user_id=target_user_id,
                amount=amount,
                transaction_type="allocation",
                description=reason or f"Credit allocation from organization pool to user {email}",
                reference_id=organization_id,
                reference_type="organization_pool_allocation",
                metadata={
                    "allocated_by": allocated_by,
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "source": "organization_pool"
                }
            )
            
            # Deduct from organization pool
            credit_service.deduct_credits(
                user_id=0,  # Organization account
                amount=amount,
                transaction_type="allocation",
                description=f"Credit allocation to user {email} from organization pool",
                reference_id=user_id,
                reference_type="user_allocation",
                metadata={
                    "allocated_to": user_id,
                    "allocated_by": allocated_by,
                    "organization_id": organization_id
                }
            )
            
            # Log allocation
            self._log_activity(
                user_id=allocated_by,
                organization_id=organization_id,
                action="credits_allocated_from_pool",
                resource_type="credit_pool",
                resource_id=str(org_credit_account.id),
                details={
                    "target_user_id": user_id,
                    "target_user_email": user.email,
                    "amount": amount,
                    "reason": reason,
                    "remaining_pool_balance": org_credit_account.current_balance - amount
                },
                db=db
            )
            
            return {
                "success": True,
                "organization_id": organization_id,
                "user_id": user_id,
                "user_email": user.email,
                "allocated_amount": amount,
                "user_new_balance": user_credit_account.current_balance + amount,
                "organization_pool_balance": org_credit_account.current_balance - amount,
                "allocated_by": allocated_by
            }
        
        except Exception as e:
            raise ValueError(f"Failed to allocate credits from organization pool: {str(e)}")
    
    def setup_auto_allocation_rules(
        self,
        organization_id: str,
        rules: Dict[str, Any],
        setup_by: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Setup automatic credit allocation rules for organization
        
        Args:
            organization_id: Organization ID
            rules: Auto-allocation rules configuration
            setup_by: User setting up the rules
            db: Database session
        
        Returns:
            Rules setup result
        """
        if not db:
            raise ValueError("Database session required")
        
        # Validate rules
        required_fields = ["enabled", "default_allocation", "frequency"]
        for field in required_fields:
            if field not in rules:
                raise ValueError(f"Required field '{field}' missing from rules")
        
        valid_frequencies = ["weekly", "monthly", "on_first_login", "on_role_assignment"]
        if rules["frequency"] not in valid_frequencies:
            raise ValueError(f"Invalid frequency. Must be one of: {valid_frequencies}")
        
        # Store rules in organization preferences or metadata
        org = db.query(Organization).filter(Organization.organization_id == organization_id).first()
        if not org:
            raise ValueError(f"Organization '{organization_id}' not found")
        
        # Update organization with credit allocation rules
        current_preferences = org.preferences or {}
        current_preferences["credit_allocation_rules"] = rules
        
        org.preferences = current_preferences
        org.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Log rules setup
        self._log_activity(
            user_id=setup_by,
            organization_id=organization_id,
            action="credit_allocation_rules_setup",
            resource_type="organization",
            resource_id=organization_id,
            details={
                "rules": rules,
                "setup_by": setup_by
            },
            db=db
        )
        
        return {
            "success": True,
            "organization_id": organization_id,
            "rules": rules,
            "setup_by": setup_by,
            "rules_active": rules.get("enabled", False)
        }
    
    def execute_auto_allocations(
        self,
        organization_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Execute automatic credit allocations based on organization rules
        
        Args:
            organization_id: Organization ID
            db: Database session
        
        Returns:
            Auto-allocation execution result
        """
        if not db:
            raise ValueError("Database session required")
        
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        
        # Get organization credit pool
        org_credit_account = credit_service.get_organization_credit_account(int(organization_id))
        if not org_credit_account:
            return {
                "success": False,
                "message": "No organization credit pool found",
                "allocations_executed": 0
            }
        
        # Get organization
        org = db.query(Organization).filter(Organization.organization_id == organization_id).first()
        if not org:
            return {
                "success": False,
                "message": "Organization not found",
                "allocations_executed": 0
            }
        
        # Get allocation rules
        rules = org.preferences.get("credit_allocation_rules", {})
        if not rules.get("enabled", False):
            return {
                "success": True,
                "message": "Auto-allocation disabled",
                "allocations_executed": 0
            }
        
        allocations_executed = 0
        allocation_errors = []
        
        # Get organization users
        org_users = db.query(ExtendedUser).filter(
            ExtendedUser.organization_id == organization_id,
            ExtendedUser.status == "active"
        ).all()
        
        for user in org_users:
            try:
                user_credit_account = credit_service.get_credit_account(int(user.user_id.replace('-', ''), 16))
                if not user_credit_account:
                    continue  # Skip users without credit accounts
                
                # Check if user should receive allocation based on frequency
                should_allocate = False
                
                if rules["frequency"] == "weekly":
                    # Check if user hasn't received allocation this week
                    last_allocation = db.query(UserActivity).filter(
                        UserActivity.user_id == user.user_id,
                        UserActivity.organization_id == organization_id,
                        UserActivity.action == "credits_allocated_from_pool",
                        UserActivity.created_at >= datetime.utcnow() - timedelta(days=7)
                    ).first()
                    should_allocate = last_allocation is None
                
                elif rules["frequency"] == "monthly":
                    # Check if user hasn't received allocation this month
                    last_allocation = db.query(UserActivity).filter(
                        UserActivity.user_id == user.user_id,
                        UserActivity.organization_id == organization_id,
                        UserActivity.action == "credits_allocated_from_pool",
                        UserActivity.created_at >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    ).first()
                    should_allocate = last_allocation is None
                
                elif rules["frequency"] == "on_first_login":
                    # Check if this is first time user is receiving allocation
                    allocations_count = db.query(UserActivity).filter(
                        UserActivity.user_id == user.user_id,
                        UserActivity.organization_id == organization_id,
                        UserActivity.action == "credits_allocated_from_pool"
                    ).count()
                    should_allocate = allocations_count == 0
                
                elif rules["frequency"] == "on_role_assignment":
                    # Check if user has recent role assignment
                    recent_role_assignment = db.query(UserActivity).filter(
                        UserActivity.user_id == user.user_id,
                        UserActivity.organization_id == organization_id,
                        UserActivity.action.in_(["role_assigned", "invitation_accepted"]),
                        UserActivity.created_at >= datetime.utcnow() - timedelta(days=30)
                    ).first()
                    should_allocate = recent_role_assignment is not None
                
                if should_allocate and org_credit_account.current_balance >= rules["default_allocation"]:
                    # Execute allocation
                    allocation_result = self.allocate_credits_from_organization_pool(
                        organization_id=organization_id,
                        user_id=user.user_id,
                        amount=rules["default_allocation"],
                        allocated_by="system_auto_allocation",
                        reason=f"Auto allocation ({rules['frequency']})",
                        db=db
                    )
                    
                    if allocation_result["success"]:
                        allocations_executed += 1
        
        return {
            "success": True,
            "organization_id": organization_id,
            "allocations_executed": allocations_executed,
            "rules": rules,
            "errors": allocation_errors,
            "remaining_pool_balance": org_credit_account.current_balance
        }
    
    def get_user_dashboard_credit_info(
        self,
        user_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get user dashboard credit information with recommendations
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Dashboard credit info for UI
        """
        if not db:
            raise ValueError("Database session required")
        
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        from app.services.credit_service import CreditService
        from app.services.usage_tracking.usage_analytics import UsageAnalytics
        from app.services.usage_tracking.forecasting_engine import ForecastingEngine
        
        credit_service = CreditService(db)
        usage_analytics = UsageAnalytics(db)
        forecasting_engine = ForecastingEngine(db)
        
        # Get credit account
        user_int_id = int(user.user_id.replace('-', ''), 16)
        credit_account = credit_service.get_credit_account(user_int_id)
        
        if not credit_account:
            return {
                "user_id": user_id,
                "has_credit_account": False,
                "message": "No credit account setup",
                "recommendations": ["Contact admin to setup credit account"]
            }
        
        # Get current balance and status
        current_balance = credit_account.current_balance
        balance_status = "good"
        if current_balance < 100:
            balance_status = "low"
        elif current_balance < 20:
            balance_status = "critical"
        
        # Get usage forecast
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        usage_summary = credit_service.get_usage_summary(
            user_id=user_int_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get balance projection
        balance_projection = credit_service.get_balance_projection(
            user_id=user_int_id,
            days_ahead=30
        )
        
        # Get usage patterns
        usage_patterns = usage_analytics.analyze_user_behavior(
            user_id=user_int_id,
            days_back=30
        )
        
        # Generate recommendations
        recommendations = []
        
        if current_balance < 100:
            recommendations.append({
                "type": "low_balance",
                "message": "Your credit balance is running low. Consider purchasing more credits.",
                "action": "purchase_credits",
                "suggested_amount": 500
            })
        
        if balance_projection.projected_runout_date:
            runout_date = balance_projection.projected_runout_date
            if runout_date < datetime.utcnow() + timedelta(days=7):
                recommendations.append({
                    "type": "imminent_runout",
                    "message": f"Based on your usage, credits will run out on {runout_date.strftime('%Y-%m-%d')}",
                    "action": "purchase_credits",
                    "urgency": "high"
                })
        
        # Add organization pool info if available
        org_pool_info = None
        if user.organization_id:
            org_summary = self.get_organization_credit_summary(user.organization_id, db)
            if org_summary.get("has_credit_pool"):
                org_pool_info = {
                    "available": org_summary["credit_pool"]["balance"],
                    "utilization_rate": org_summary["credit_pool"]["utilization_rate"]
                }
        
        return {
            "user_id": user_id,
            "has_credit_account": True,
            "balance": {
                "current": current_balance,
                "reserved": credit_account.reserved_balance,
                "available": current_balance - credit_account.reserved_balance,
                "status": balance_status,
                "last_updated": credit_account.last_activity.isoformat() if credit_account.last_activity else None
            },
            "usage": {
                "total_cost_30_days": usage_summary.total_cost,
                "total_transactions_30_days": usage_summary.total_transactions,
                "avg_daily_cost": usage_summary.total_cost / 30,
                "most_used_service": usage_summary.most_used_service,
                "cost_trend": "increasing" if usage_summary.total_cost > 100 else "stable"
            },
            "forecast": {
                "projected_runout_date": balance_projection.projected_runout_date.isoformat() if balance_projection.projected_runout_date else None,
                "days_until_runout": (balance_projection.projected_runout_date - datetime.utcnow()).days if balance_projection.projected_runout_date else None,
                "confidence_level": balance_projection.confidence_level,
                "recommended_purchase_amount": balance_projection.recommended_purchase_amount
            },
            "organization_pool": org_pool_info,
            "recommendations": recommendations,
            "recent_transactions": [
                {
                    "id": t.id,
                    "type": t.transaction_type,
                    "amount": t.amount,
                    "description": t.description,
                    "created_at": t.created_at.isoformat()
                }
                for t in credit_service.get_recent_transactions(
                    user_id=user_int_id, 
                    limit=5
                )
            ]
        }
        """
        Allocate credits to user (admin function)
        
        Args:
            user_id: Target user ID
            amount: Credit amount to allocate
            allocated_by: User allocating credits
            reason: Allocation reason
            db: Database session
        
        Returns:
            Allocation result
        """
        if not db:
            raise ValueError("Database session required")
        
        # Verify target user exists
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        # Get credit service
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        
        # Get or create credit account
        credit_account = credit_service.get_credit_account(user.user_id)  # Use UUID string
        if not credit_account:
            # Create credit account if doesn't exist
            credit_account = credit_service.create_credit_account(
                CreditAccountCreate(user_id=user.user_id, organization_id=user.organization_id)  # Use UUID string
            )
        
        try:
            # Allocate credits
            credit_service.add_credits(
                user_id=user.user_id,  # Use UUID string
                amount=amount,
                transaction_type="allocation",
                description=reason or f"Credit allocation by admin {allocated_by}",
                reference_id=allocated_by,
                reference_type="admin_allocation",
                metadata={
                    "allocated_by": allocated_by,
                    "user_id": user_id,
                    "reason": reason
                }
            )
            
            # Log allocation
            self._log_activity(
                user_id=allocated_by,
                organization_id=user.organization_id,
                action="credits_allocated",
                resource_type="credit_account",
                resource_id=str(credit_account.id),
                details={
                    "target_user_id": user_id,
                    "amount": amount,
                    "reason": reason,
                    "new_balance": credit_account.current_balance + amount
                },
                db=db
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "allocated_amount": amount,
                "new_balance": credit_account.current_balance + amount,
                "allocated_by": allocated_by
            }
        
        except Exception as e:
            raise ValueError(f"Failed to allocate credits: {str(e)}")
    
    def get_user_credit_summary(
        self,
        user_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive credit summary for user
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            Credit summary data
        """
        if not db:
            raise ValueError("Database session required")
        
        # Verify user exists
        user = db.query(ExtendedUser).filter(ExtendedUser.user_id == user_id).first()
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        
        from app.services.credit_service import CreditService
        from app.services.usage_tracking.usage_analytics import UsageAnalytics
        from app.services.usage_tracking.forecasting_engine import ForecastingEngine
        
        credit_service = CreditService(db)
        usage_analytics = UsageAnalytics(db)
        forecasting_engine = ForecastingEngine(db)
        
        # Get credit account
        credit_account = credit_service.get_credit_account(user.user_id)  # Use UUID string
        if not credit_account:
            return {
                "user_id": user_id,
                "has_credit_account": False,
                "message": "No credit account found"
            }
        
        # Get recent usage summary
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        usage_summary = credit_service.get_usage_summary(
            user_id=user.user_id,  # Use UUID string
            start_date=start_date,
            end_date=end_date
        )
        
        # Get balance projection
        balance_projection = credit_service.get_balance_projection(
            user_id=user.user_id,  # Use UUID string
            days_ahead=30
        )
        
        # Get active alerts
        active_alerts = credit_service.get_active_alerts(user.user_id)  # Use UUID string
        
        # Get usage patterns
        usage_patterns = usage_analytics.analyze_user_behavior(
            user_id=user.user_id,  # Use UUID string
            days_back=30
        )
        
        return {
            "user_id": user_id,
            "has_credit_account": True,
            "credit_account": {
                "id": credit_account.id,
                "balance": credit_account.current_balance,
                "reserved_balance": credit_account.reserved_balance,
                "status": credit_account.status,
                "total_earned": credit_account.total_earned,
                "total_spent": credit_account.total_spent,
                "last_activity": credit_account.last_activity.isoformat() if credit_account.last_activity else None
            },
            "usage_summary": {
                "total_cost_30_days": usage_summary.total_cost,
                "total_transactions_30_days": usage_summary.total_transactions,
                "avg_cost_per_transaction": usage_summary.avg_cost_per_transaction,
                "most_used_service": usage_summary.most_used_service,
                "cost_by_service": usage_summary.cost_by_service
            },
            "balance_projection": {
                "projected_balance_30_days": balance_projection.projected_balance,
                "projected_runout_date": balance_projection.projected_runout_date.isoformat() if balance_projection.projected_runout_date else None,
                "recommended_purchase_amount": balance_projection.recommended_purchase_amount,
                "confidence_level": balance_projection.confidence_level
            },
            "active_alerts": [
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in active_alerts
            ],
            "usage_patterns": {
                "user_score": usage_patterns.get("user_score", {}),
                "usage_frequency": usage_patterns.get("usage_frequency", {}),
                "peak_usage_hours": usage_patterns.get("peak_usage_hours", []),
                "recommendations": usage_patterns.get("recommendations", [])
            }
        }
    
    def setup_organization_credit_pool(
        self,
        organization_id: str,
        pool_size: float,
        setup_by: str,
        allocation_rules: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Setup organization-level credit pool
        
        Args:
            organization_id: Organization ID
            pool_size: Total credit pool size
            setup_by: User setting up the pool
            allocation_rules: Rules for credit allocation
            db: Database session
        
        Returns:
            Pool setup result
        """
        if not db:
            raise ValueError("Database session required")
        
        from app.services.credit_service import CreditService
        from app.schemas.credit_schemas import CreditAccountCreate
        
        credit_service = CreditService(db)
        
        try:
            # Create organization credit account
            org_credit_account = credit_service.create_credit_account(
                CreditAccountCreate(
                    user_id=0,  # System user for organization
                    organization_id=int(organization_id),
                    auto_renew=False
                )
            )
            
            # Allocate pool credits
            credit_service.add_credits(
                user_id=0,
                amount=pool_size,
                transaction_type="allocation",
                description=f"Organization credit pool allocation for org {organization_id}",
                reference_id=organization_id,
                reference_type="organization_pool",
                metadata={
                    "organization_id": organization_id,
                    "setup_by": setup_by,
                    "allocation_rules": allocation_rules,
                    "pool_type": "organization"
                }
            )
            
            # Default allocation rules
            default_rules = allocation_rules or {
                "auto_allocation": True,
                "default_user_allocation": 500.0,
                "max_user_allocation": 2000.0,
                "monthly_replenishment": True,
                "replenishment_amount": pool_size * 0.1
            }
            
            # Log organization pool setup
            self._log_activity(
                user_id=setup_by,
                organization_id=organization_id,
                action="organization_credit_pool_created",
                resource_type="credit_pool",
                resource_id=str(org_credit_account.id),
                details={
                    "organization_id": organization_id,
                    "pool_size": pool_size,
                    "allocation_rules": default_rules,
                    "pool_account_id": org_credit_account.id
                },
                db=db
            )
            
            return {
                "success": True,
                "organization_id": organization_id,
                "pool_size": pool_size,
                "pool_account_id": org_credit_account.id,
                "allocation_rules": default_rules,
                "setup_by": setup_by
            }
        
        except Exception as e:
            raise ValueError(f"Failed to setup organization credit pool: {str(e)}")
    
    def get_organization_credit_summary(
        self,
        organization_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get organization-level credit summary
        
        Args:
            organization_id: Organization ID
            db: Database session
        
        Returns:
            Organization credit summary
        """
        if not db:
            raise ValueError("Database session required")
        
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        
        # Get organization credit account
        org_credit_account = credit_service.get_organization_credit_account(int(organization_id))
        if not org_credit_account:
            return {
                "organization_id": organization_id,
                "has_credit_pool": False,
                "message": "No organization credit pool found"
            }
        
        # Get all users in organization
        org_users = db.query(ExtendedUser).filter(
            ExtendedUser.organization_id == organization_id
        ).all()
        
        # Get usage summary for organization
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        total_org_usage = 0
        total_user_transactions = 0
        org_usage_by_service = {}
        
        for user in org_users:
            try:
                user_usage = credit_service.get_usage_summary(
                    user_id=int(user.user_id),
                    start_date=start_date,
                    end_date=end_date
                )
                total_org_usage += user_usage.total_cost
                total_user_transactions += user_usage.total_transactions
                
                # Aggregate service usage
                for service, cost in user_usage.cost_by_service.items():
                    org_usage_by_service[service] = org_usage_by_service.get(service, 0) + cost
            except:
                continue  # Skip users without credit accounts
        
        return {
            "organization_id": organization_id,
            "has_credit_pool": True,
            "credit_pool": {
                "id": org_credit_account.id,
                "balance": org_credit_account.current_balance,
                "total_allocated": org_credit_account.total_earned,
                "total_utilized": org_credit_account.total_spent,
                "utilization_rate": (org_credit_account.total_spent / max(1, org_credit_account.total_earned)) * 100
            },
            "organization_usage_30_days": {
                "total_cost": total_org_usage,
                "total_transactions": total_user_transactions,
                "avg_cost_per_user": total_org_usage / max(1, len(org_users)),
                "usage_by_service": org_usage_by_service
            },
            "member_summary": {
                "total_users": len(org_users),
                "users_with_credit_accounts": len([u for u in org_users if credit_service.get_credit_account(int(u.user_id))])
            }
        }


# Global user management service instance
user_management_service = UserManagementService()