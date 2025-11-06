"""
User Management API Endpoints

Provides comprehensive REST API for user management operations including
CRUD operations, role management, organization management, and user activity tracking.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.models.user_management import (
    User as ExtendedUser, Organization, UserRole, Permission,
    UserRoleAssignment, UserSession, UserInvitation, UserActivity,
    UserPreferences, AccountSecurity
)
from app.models.user import User as LegacyUser
from app.core.security import get_current_user, get_password_hash, verify_password
from app.core.rbac import (
    require_permission, require_role, require_ownership,
    permission_checker, rbac_manager, ResourceAccessChecker
)
from app.services.user_management import user_management_service
from app.schemas.user_management_schemas import (
    UserCreateRequest, UserUpdateRequest, UserResponse, UserListResponse,
    UserStatisticsResponse, RoleCreateRequest, RoleResponse,
    PermissionResponse, UserSessionResponse, UserActivityResponse,
    UserInvitationRequest, UserInvitationResponse, InvitationAcceptRequest,
    PasswordChangeRequest, PasswordResetRequest, OrganizationCreateRequest,
    OrganizationResponse, OrganizationUpdateRequest
)


router = APIRouter(prefix="/api/v1/users", tags=["user-management"])


# User CRUD Operations
@router.post("/", response_model=UserResponse)
@require_permission("users.create")
async def create_user(
    request: UserCreateRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """Create a new user"""
    user = user_management_service.create_user(
        email=request.email,
        full_name=request.full_name,
        password=request.password,
        organization_id=request.organization_id or current_user.organization_id,
        roles=request.roles,
        created_by=current_user.user_id,
        db=db
    )
    
    return UserResponse.from_orm(user)


@router.get("/{user_id}", response_model=UserResponse)
@require_ownership("user_id")
async def get_user(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    user = user_management_service.get_user_by_id(user_id, include_relationships=True, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
@require_ownership("user_id")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user information"""
    updates = request.dict(exclude_unset=True)
    user = user_management_service.update_user(
        user_id=user_id,
        updates=updates,
        updated_by=current_user.user_id,
        db=db
    )
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}")
@require_permission("users.delete")
async def delete_user(
    user_id: str,
    permanent: bool = Query(False, description="Permanently delete user"),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete/deactivate user"""
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    success = user_management_service.delete_user(
        user_id=user_id,
        deleted_by=current_user.user_id,
        permanent=permanent,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/deactivate")
@require_permission("users.deactivate")
async def deactivate_user(
    user_id: str,
    reason: str = Query("Manual deactivation"),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate user account"""
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    success = user_management_service.deactivate_user(
        user_id=user_id,
        reason=reason,
        deactivated_by=current_user.user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/reactivate")
@require_permission("users.reactivate")
async def reactivate_user(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate user account"""
    success = user_management_service.reactivate_user(
        user_id=user_id,
        reactivated_by=current_user.user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User reactivated successfully"}


@router.get("/", response_model=UserListResponse)
@require_permission("users.read")
async def list_users(
    organization_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users with filtering and pagination"""
    # Use current user's organization if not specified
    if not organization_id:
        organization_id = current_user.organization_id
    
    users, total = user_management_service.list_users(
        organization_id=organization_id,
        status=status,
        role=role,
        search=search,
        page=page,
        per_page=per_page,
        db=db
    )
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


# User Statistics and Analytics
@router.get("/{user_id}/statistics", response_model=UserStatisticsResponse)
@require_ownership("user_id")
async def get_user_statistics(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive user statistics"""
    statistics = user_management_service.get_user_statistics(
        user_id=user_id,
        organization_id=current_user.organization_id,
        db=db
    )
    
    return UserStatisticsResponse(**statistics)


@router.get("/{user_id}/activity", response_model=List[UserActivityResponse])
@require_ownership("user_id")
async def get_user_activity(
    user_id: str,
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user activity history"""
    activities = user_management_service.get_user_activity(
        user_id=user_id,
        organization_id=current_user.organization_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        db=db
    )
    
    return [UserActivityResponse.from_orm(activity) for activity in activities]


@router.get("/{user_id}/sessions", response_model=List[UserSessionResponse])
@require_ownership("user_id")
async def get_user_sessions(
    user_id: str,
    active_only: bool = Query(False),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user sessions"""
    sessions = user_management_service.get_user_sessions(
        user_id=user_id,
        active_only=active_only,
        db=db
    )
    
    return [UserSessionResponse.from_orm(session) for session in sessions]


# Password Management
@router.post("/{user_id}/change-password")
@require_ownership("user_id")
async def change_password(
    user_id: str,
    request: PasswordChangeRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    success = user_management_service.change_password(
        user_id=user_id,
        old_password=request.old_password,
        new_password=request.new_password,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid old password"
        )
    
    return {"message": "Password changed successfully"}


@router.post("/{user_id}/reset-password")
@require_permission("users.reset_password")
async def reset_password(
    user_id: str,
    request: PasswordResetRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset user password (admin function)"""
    success = user_management_service.reset_password(
        user_id=user_id,
        new_password=request.new_password,
        reset_by=current_user.user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}


# User Invitations
@router.post("/invite", response_model=UserInvitationResponse)
@require_permission("users.invite")
async def invite_user(
    request: UserInvitationRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a user to join the organization"""
    invitation = user_management_service.invite_user(
        email=request.email,
        role_id=request.role_id,
        organization_id=current_user.organization_id,
        invited_by=current_user.user_id,
        message=request.message,
        expires_in_days=request.expires_in_days,
        db=db
    )
    
    return UserInvitationResponse.from_orm(invitation)


@router.get("/invitations/pending", response_model=List[UserInvitationResponse])
@require_permission("users.invite")
async def get_pending_invitations(
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending invitations"""
    invitations = db.query(UserInvitation).filter(
        UserInvitation.organization_id == current_user.organization_id,
        UserInvitation.status == "pending"
    ).all()
    
    return [UserInvitationResponse.from_orm(invitation) for invitation in invitations]


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    request: InvitationAcceptRequest,
    db: Session = Depends(get_db)
):
    """Accept a user invitation"""
    user, invitation = user_management_service.accept_invitation(
        token=token,
        full_name=request.full_name,
        password=request.password,
        db=db
    )
    
    return {"message": "Invitation accepted successfully", "user_id": user.user_id}


@router.post("/invitations/{invitation_id}/cancel")
@require_permission("users.invite")
async def cancel_invitation(
    invitation_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending invitation"""
    invitation = db.query(UserInvitation).filter(
        UserInvitation.invitation_id == invitation_id,
        UserInvitation.organization_id == current_user.organization_id,
        UserInvitation.status == "pending"
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    invitation.status = "cancelled"
    db.commit()
    
    return {"message": "Invitation cancelled successfully"}


@router.get("/invitations", response_model=List[UserInvitationResponse])
@require_permission("users.invite")
async def get_all_invitations(
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by invitation status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get all invitations with pagination and filtering"""
    query = db.query(UserInvitation).filter(
        UserInvitation.organization_id == current_user.organization_id
    )
    
    if status:
        query = query.filter(UserInvitation.status == status)
    
    # Get total count for pagination
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    invitations = query.offset(offset).limit(limit).all()
    
    return [UserInvitationResponse.from_orm(invitation) for invitation in invitations]


@router.post("/invitations/{invitation_id}/resend")
@require_permission("users.invite")
async def resend_invitation(
    invitation_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend an invitation"""
    invitation = db.query(UserInvitation).filter(
        UserInvitation.invitation_id == invitation_id,
        UserInvitation.organization_id == current_user.organization_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    if invitation.status not in ["pending", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend invitation in current status"
        )
    
    # Generate new token and reset expiration
    invitation.token = str(uuid.uuid4())
    invitation.status = "pending"
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    invitation.resent_at = datetime.utcnow()
    invitation.resent_by = current_user.user_id
    
    db.commit()
    
    return {"message": "Invitation resent successfully"}


@router.delete("/invitations/{invitation_id}")
@require_permission("users.invite")
async def delete_invitation(
    invitation_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an invitation"""
    invitation = db.query(UserInvitation).filter(
        UserInvitation.invitation_id == invitation_id,
        UserInvitation.organization_id == current_user.organization_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    if invitation.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete accepted invitation"
        )
    
    db.delete(invitation)
    db.commit()
    
    return {"message": "Invitation deleted successfully"}


@router.get("/invitations/stats")
@require_permission("users.invite")
async def get_invitation_statistics(
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get invitation statistics and analytics"""
    organization_id = current_user.organization_id
    
    # Get all invitations for the organization
    invitations = db.query(UserInvitation).filter(
        UserInvitation.organization_id == organization_id
    ).all()
    
    # Calculate basic counts
    total_invitations = len(invitations)
    pending_invitations = len([i for i in invitations if i.status == "pending"])
    accepted_invitations = len([i for i in invitations if i.status == "accepted"])
    expired_invitations = len([i for i in invitations if i.status == "expired"])
    cancelled_invitations = len([i for i in invitations if i.status == "cancelled"])
    
    # Calculate acceptance rate
    acceptance_rate = (accepted_invitations / total_invitations * 100) if total_invitations > 0 else 0
    
    # Calculate average response time for accepted invitations
    response_times = []
    for invitation in invitations:
        if invitation.status == "accepted" and invitation.accepted_at:
            response_time = (invitation.accepted_at - invitation.created_at).total_seconds() / 3600
            response_times.append(response_time)
    
    avg_response_time_hours = sum(response_times) / len(response_times) if response_times else 0
    
    # Calculate recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    invitations_last_30d = len([i for i in invitations if i.created_at >= thirty_days_ago])
    
    # Calculate weekly activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    invitations_last_7d = len([i for i in invitations if i.created_at >= seven_days_ago])
    
    # Calculate monthly activity (current month)
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    invitations_this_month = len([i for i in invitations if i.created_at >= current_month])
    
    # Calculate top invited roles
    role_counts = {}
    for invitation in invitations:
        if invitation.role_id:
            role = db.query(UserRole).filter(UserRole.role_id == invitation.role_id).first()
            role_name = role.name if role else f"Unknown ({invitation.role_id})"
            role_counts[role_name] = role_counts.get(role_name, 0) + 1
    
    # Calculate monthly trends (last 12 months)
    monthly_trend = []
    for i in range(12):
        month_date = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
        month_name = month_date.strftime("%Y-%m")
        month_invitations = [inv for inv in invitations 
                           if inv.created_at.year == month_date.year and 
                              inv.created_at.month == month_date.month]
        
        month_count = len(month_invitations)
        month_accepted = len([inv for inv in month_invitations if inv.status == "accepted"])
        
        monthly_trend.append({
            "month": month_name,
            "count": month_count,
            "accepted": month_accepted
        })
    
    monthly_trend.reverse()  # Show oldest to newest
    
    stats = {
        "total_invitations": total_invitations,
        "pending_invitations": pending_invitations,
        "accepted_invitations": accepted_invitations,
        "expired_invitations": expired_invitations,
        "cancelled_invitations": cancelled_invitations,
        "acceptance_rate": round(acceptance_rate, 2),
        "avg_response_time_hours": round(avg_response_time_hours, 2),
        "invitations_last_30d": invitations_last_30d,
        "invitations_last_7d": invitations_last_7d,
        "invitations_this_month": invitations_this_month,
        "top_invited_roles": role_counts,
        "monthly_trend": monthly_trend
    }
    
    return stats


# Role and Permission Management
@router.get("/roles/available", response_model=List[RoleResponse])
@require_permission("roles.read")
async def get_available_roles(
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available roles"""
    roles = db.query(UserRole).all()
    return [RoleResponse.from_orm(role) for role in roles]


@router.post("/roles", response_model=RoleResponse)
@require_permission("roles.create")
async def create_role(
    request: RoleCreateRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new role"""
    role = rbac_manager.create_role(
        name=request.name,
        description=request.description,
        level=request.level,
        created_by=current_user.user_id,
        db=db
    )
    
    return RoleResponse.from_orm(role)


@router.post("/{user_id}/roles/{role_id}")
@require_permission("roles.assign")
async def assign_role_to_user(
    user_id: str,
    role_id: str,
    organization_id: Optional[str] = Query(None),
    expires_at: Optional[datetime] = Query(None),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a role to a user"""
    # Use current user's organization if not specified
    if not organization_id:
        organization_id = current_user.organization_id
    
    assignment = rbac_manager.assign_role_to_user(
        user_id=user_id,
        role_id=role_id,
        organization_id=organization_id,
        assigned_by=current_user.user_id,
        expires_at=expires_at,
        db=db
    )
    
    return {"message": "Role assigned successfully", "assignment_id": assignment.assignment_id}


@router.delete("/{user_id}/roles/{role_id}")
@require_permission("roles.revoke")
async def revoke_role_from_user(
    user_id: str,
    role_id: str,
    organization_id: Optional[str] = Query(None),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a role from a user"""
    # Use current user's organization if not specified
    if not organization_id:
        organization_id = current_user.organization_id
    
    success = rbac_manager.revoke_role_from_user(
        user_id=user_id,
        role_id=role_id,
        organization_id=organization_id,
        revoked_by=current_user.user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found"
        )
    
    return {"message": "Role revoked successfully"}


@router.get("/{user_id}/permissions", response_model=Dict[str, Any])
@require_ownership("user_id")
async def get_user_permissions(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user permissions summary"""
    user = user_management_service.get_user_by_id(user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    permissions_summary = user_management_service._log_activity  # This would call get_user_permissions_summary
    
    return {
        "user_id": user_id,
        "organization_id": current_user.organization_id,
        "permissions": list(permission_checker.get_user_permissions(
            user, current_user.organization_id, db
        ))
    }


# Session Management
@router.post("/sessions/{session_id}/terminate")
async def terminate_session(
    session_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate a user session"""
    success = user_management_service.terminate_session(
        session_id=session_id,
        terminated_by=current_user.user_id,
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {"message": "Session terminated successfully"}


# User Search and Bulk Operations
@router.post("/bulk-actions")
@require_permission("users.bulk")
async def bulk_user_actions(
    action: str,
    user_ids: List[str],
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform bulk actions on users"""
    if action not in ["activate", "deactivate", "delete"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'activate', 'deactivate', or 'delete'"
        )
    
    results = []
    
    for user_id in user_ids:
        try:
            if action == "activate":
                success = user_management_service.reactivate_user(
                    user_id=user_id,
                    reactivated_by=current_user.user_id,
                    db=db
                )
            elif action == "deactivate":
                success = user_management_service.deactivate_user(
                    user_id=user_id,
                    reason="Bulk deactivation",
                    deactivated_by=current_user.user_id,
                    db=db
                )
            elif action == "delete":
                success = user_management_service.delete_user(
                    user_id=user_id,
                    deleted_by=current_user.user_id,
                    permanent=False,
                    db=db
                )
            
            results.append({
                "user_id": user_id,
                "success": success,
                "message": f"User {action}d successfully" if success else f"Failed to {action} user"
            })
        except Exception as e:
            results.append({
                "user_id": user_id,
                "success": False,
                "message": str(e)
            })
    
    return {"results": results}


@router.get("/search/suggestions")
@require_permission("users.read")
async def search_users_suggestions(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user search suggestions"""
    search_term = f"%{query.lower()}%"
    
    users = db.query(ExtendedUser).filter(
        ExtendedUser.organization_id == current_user.organization_id,
        ExtendedUser.status == "active",
        or_(
            ExtendedUser.email.ilike(search_term),
            ExtendedUser.full_name.ilike(search_term)
        )
    ).limit(limit).all()
    
    return [
        {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "display_text": f"{user.full_name} ({user.email})"
        }
        for user in users
    ]


# User Preferences and Settings
@router.get("/{user_id}/preferences")
@require_ownership("user_id")
async def get_user_preferences(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id
    ).first()
    
    if not preferences:
        return {}
    
    return {
        "theme": preferences.theme,
        "language": preferences.language,
        "timezone": preferences.timezone,
        "email_notifications": preferences.email_notifications,
        "two_factor_enabled": preferences.two_factor_enabled,
        "session_timeout_minutes": preferences.session_timeout_minutes
    }


# Current User Profile
@router.get("/me/profile")
async def get_current_user_profile(
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with permissions and activity summary"""
    permissions = list(permission_checker.get_user_permissions(
        current_user, current_user.organization_id, db
    ))
    
    # Get recent activity
    recent_activity = user_management_service.get_user_activity(
        user_id=current_user.user_id,
        organization_id=current_user.organization_id,
        limit=10,
        db=db
    )
    
    # Get active sessions
    active_sessions = user_management_service.get_user_sessions(
        user_id=current_user.user_id,
        active_only=True,
        db=db
    )
    
    return {
        "user": UserResponse.from_orm(current_user),
        "permissions": permissions,
        "recent_activity": [
            {
                "action": activity.action,
                "timestamp": activity.created_at.isoformat(),
                "details": activity.details
            }
            for activity in recent_activity
        ],
        "active_sessions": len(active_sessions),
        "organization_id": current_user.organization_id
    }


@router.put("/me/preferences")
async def update_current_user_preferences(
    preferences: Dict[str, Any],
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user preferences"""
    user_preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.user_id
    ).first()
    
    if not user_preferences:
        user_preferences = UserPreferences(user_id=current_user.user_id)
        db.add(user_preferences)
    
    # Update allowed preferences
    updatable_prefs = [
        "theme", "language", "timezone", "email_notifications",
        "session_timeout_minutes"
    ]
    
    for key, value in preferences.items():
        if key in updatable_prefs:
            setattr(user_preferences, key, value)
    
    db.commit()
    
    return {"message": "Preferences updated successfully"}


# Organization Management Endpoints
@router.get("/organizations", response_model=List[OrganizationResponse])
@require_permission("organizations.read")
async def list_organizations(
    status: Optional[str] = Query(None),
    subscription_tier: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List organizations with filtering and pagination"""
    query = db.query(Organization)
    
    if status:
        query = query.filter(Organization.status == status)
    
    if subscription_tier:
        query = query.filter(Organization.subscription_tier == subscription_tier)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    organizations = query.order_by(desc(Organization.created_at)).offset(offset).limit(per_page).all()
    
    return [OrganizationResponse.from_orm(org) for org in organizations]


@router.post("/organizations", response_model=OrganizationResponse)
@require_permission("organizations.create")
async def create_organization(
    request: OrganizationCreateRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    # Check if domain is already taken
    if request.domain:
        existing = db.query(Organization).filter(Organization.domain == request.domain).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    organization = Organization(
        organization_id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        domain=request.domain,
        subscription_tier=request.subscription_tier,
        max_users=request.max_users,
        max_documents=request.max_documents,
        max_storage_gb=request.max_storage_gb,
        billing_email=request.billing_email,
        billing_address=request.billing_address,
        tax_id=request.tax_id,
        features=[
            "user_management", "rbac", "audit_logging", 
            "multi_tenant", "advanced_security", "api_access"
        ],
        status="active"
    )
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return OrganizationResponse.from_orm(organization)


@router.get("/organizations/{organization_id}", response_model=OrganizationResponse)
@require_permission("organizations.read")
async def get_organization(
    organization_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organization by ID"""
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse.from_orm(organization)


@router.put("/organizations/{organization_id}", response_model=OrganizationResponse)
@require_permission("organizations.update")
async def update_organization(
    organization_id: str,
    request: OrganizationUpdateRequest,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update organization"""
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update allowed fields
    updatable_fields = [
        "name", "description", "domain", "subscription_tier", 
        "max_users", "max_documents", "max_storage_gb", "settings", 
        "features", "billing_email", "billing_address", "tax_id"
    ]
    
    for field, value in request.dict(exclude_unset=True).items():
        if field in updatable_fields:
            setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(organization)
    
    return OrganizationResponse.from_orm(organization)


@router.delete("/organizations/{organization_id}")
@require_permission("organizations.delete")
async def delete_organization(
    organization_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete organization (soft delete)"""
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if there are active users in this organization
    active_users = db.query(ExtendedUser).filter(
        ExtendedUser.organization_id == organization_id,
        ExtendedUser.status == "active"
    ).count()
    
    if active_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete organization with active users. Deactivate users first."
        )
    
    organization.status = "deleted"
    organization.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Organization deleted successfully"}


@router.get("/organizations/{organization_id}/users", response_model=UserListResponse)
@require_permission("users.read")
async def get_organization_users(
    organization_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users in a specific organization"""
    users, total = user_management_service.list_users(
        organization_id=organization_id,
        status=status,
        role=role,
        search=search,
        page=page,
        per_page=per_page,
        db=db
    )
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/organizations/{organization_id}/statistics")
@require_permission("organizations.read")
async def get_organization_statistics(
    organization_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organization statistics"""
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get organization stats
    total_users = db.query(ExtendedUser).filter(
        ExtendedUser.organization_id == organization_id
    ).count()
    
    active_users = db.query(ExtendedUser).filter(
        ExtendedUser.organization_id == organization_id,
        ExtendedUser.status == "active"
    ).count()
    
    recent_activities = db.query(UserActivity).filter(
        UserActivity.organization_id == organization_id,
        UserActivity.created_at >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    # Get role distribution
    role_stats = {}
    roles = db.query(UserRoleAssignment).join(
        UserRole, UserRoleAssignment.role_id == UserRole.role_id
    ).filter(
        UserRoleAssignment.organization_id == organization_id,
        UserRoleAssignment.is_active == True
    ).all()
    
    for assignment in roles:
        role_name = assignment.role.name if assignment.role else "unknown"
        role_stats[role_name] = role_stats.get(role_name, 0) + 1
    
    return {
        "organization_id": organization_id,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "recent_activities_30d": recent_activities,
        "role_distribution": role_stats,
        "subscription_tier": organization.subscription_tier,
        "subscription_status": organization.subscription_status,
        "max_users": organization.max_users,
        "usage_percentage": (total_users / organization.max_users * 100) if organization.max_users > 0 else 0,
        "features_enabled": len(organization.features or []),
        "created_at": organization.created_at.isoformat()
    }


# Advanced Security and MFA Endpoints
@router.post("/{user_id}/enable-mfa")
@require_ownership("user_id")
async def enable_mfa(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable two-factor authentication for user"""
    security = db.query(AccountSecurity).filter(
        AccountSecurity.user_id == user_id
    ).first()
    
    if not security:
        security = AccountSecurity(user_id=user_id)
        db.add(security)
    
    # In a real implementation, you would generate TOTP secret and QR code
    # For now, we'll just mark MFA as enabled
    import secrets
    security.two_factor_secret = secrets.token_hex(20)  # Mock TOTP secret
    security.two_factor_enabled_at = datetime.utcnow()
    security.two_factor_enabled = True
    
    db.commit()
    
    # Log activity
    user_management_service._log_activity(
        user_id=user_id,
        organization_id=current_user.organization_id,
        action="mfa_enabled",
        resource_type="user",
        resource_id=user_id,
        db=db
    )
    
    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/{user_id}/disable-mfa")
@require_ownership("user_id")
async def disable_mfa(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable two-factor authentication for user"""
    security = db.query(AccountSecurity).filter(
        AccountSecurity.user_id == user_id
    ).first()
    
    if not security or not security.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    security.two_factor_enabled = False
    security.two_factor_secret = None
    security.two_factor_backup_codes = None
    security.two_factor_enabled_at = None
    
    db.commit()
    
    # Log activity
    user_management_service._log_activity(
        user_id=user_id,
        organization_id=current_user.organization_id,
        action="mfa_disabled",
        resource_type="user",
        resource_id=user_id,
        db=db
    )
    
    return {"message": "Two-factor authentication disabled successfully"}


@router.get("/{user_id}/security-status")
@require_ownership("user_id")
async def get_user_security_status(
    user_id: str,
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive security status for user"""
    user = user_management_service.get_user_by_id(user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    security = user.account_security
    if not security:
        return {
            "mfa_enabled": False,
            "password_last_changed": user.last_password_change.isoformat() if user.last_password_change else None,
            "recent_login_attempts": [],
            "security_events": [],
            "account_locked": False,
            "password_weak": False
        }
    
    # Check password age
    password_age_days = None
    if user.last_password_change:
        password_age_days = (datetime.utcnow() - user.last_password_change).days
    
    password_weak = password_age_days and password_age_days > 90
    
    # Check for recent failed login attempts
    recent_failed_attempts = 0
    if security.login_attempts:
        for attempt in security.login_attempts[-10:]:  # Last 10 attempts
            if not attempt.get('success', False):
                attempt_time = datetime.fromisoformat(attempt.get('timestamp'))
                if (datetime.utcnow() - attempt_time).days < 1:
                    recent_failed_attempts += 1
    
    return {
        "mfa_enabled": security.two_factor_enabled or False,
        "password_last_changed": user.last_password_change.isoformat() if user.last_password_change else None,
        "password_age_days": password_age_days,
        "recent_failed_login_attempts": recent_failed_attempts,
        "account_locked": security.password_locked_until and security.password_locked_until > datetime.utcnow(),
        "password_weak": password_weak,
        "security_events": security.security_events[-5:] if security.security_events else [],  # Last 5 events
        "last_login_ip": security.last_login_ip,
        "last_login_at": security.last_login_at.isoformat() if security.last_login_at else None
    }


# Audit Log Management
@router.get("/audit-logs", response_model=List[AuditLogResponse])
@require_permission("audit.read")
async def get_audit_logs(
    user_id: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: ExtendedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit logs with filtering and pagination"""
    query = db.query(AuditLog)
    
    # Apply filters
    if user_id:
        query = query.filter(AuditLog.actor_user_id == user_id)
    
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    elif current_user.organization_id:
        # Non-admin users can only see their organization's logs
        query = query.filter(AuditLog.organization_id == current_user.organization_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Apply pagination
    offset = (page - 1) * per_page
    audit_logs = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(per_page).all()
    
    return [
        AuditLogResponse(
            audit_id=log.audit_id,
            actor_user_id=log.actor_user_id,
            actor_ip=log.actor_ip,
            actor_user_agent=log.actor_user_agent,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_values=log.old_values,
            new_values=log.new_values,
            changed_fields=log.changed_fields,
            organization_id=log.organization_id,
            session_id=log.session_id,
            success=log.success,
            error_message=log.error_message,
            timestamp=log.timestamp,
            correlation_id=getattr(log, 'correlation_id', None)
        )
        for log in audit_logs
    ]