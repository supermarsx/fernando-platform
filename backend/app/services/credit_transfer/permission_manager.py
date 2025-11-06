"""
Permission Manager Service

Credit transfer permissions and approval management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditTransfer, CreditTransferStatus, CreditTransferPermission,
    CreditPermissionType, CreditStatus, User, Organization, OrganizationMember
)
from app.services.credits.credit_manager import CreditManager
from app.services.user.user_service import UserService
from app.services.organization.organization_service import OrganizationService
from app.services.notification.notification_service import NotificationService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for credit transfers"""
    NONE = "none"
    VIEW = "view"
    REQUEST = "request"
    APPROVE = "approve"
    ADMIN = "admin"
    FULL = "full"


class PermissionManager:
    """
    Service for managing credit transfer permissions and approvals
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.user_service = UserService(db)
        self.org_service = OrganizationService(db)
        self.notification_service = NotificationService(db)
    
    def create_permission(
        self,
        from_user_id: int,
        to_user_id: int,
        permission_type: str,
        from_organization_id: Optional[int] = None,
        to_organization_id: Optional[int] = None,
        max_amount: Optional[Decimal] = None,
        max_frequency: Optional[int] = None,
        time_limit_hours: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
        created_by: int = None
    ) -> Dict[str, Any]:
        """
        Create a new credit transfer permission
        """
        try:
            # Validate permission parameters
            valid_types = ["allow_transfer", "require_approval", "rate_limit", "conditional_transfer"]
            if permission_type not in valid_types:
                raise ValueError(f"Invalid permission type. Must be one of: {valid_types}")
            
            # Check if users exist
            from_user = self.db.query(User).filter(User.id == from_user_id).first()
            to_user = self.db.query(User).filter(User.id == to_user_id).first()
            
            if not from_user or not to_user:
                raise ValueError("One or both users do not exist")
            
            # Check organization membership if provided
            if from_organization_id:
                from_member = self.org_service.get_member(from_user_id, from_organization_id)
                if not from_member:
                    raise ValueError("From user is not a member of the specified organization")
            
            if to_organization_id:
                to_member = self.org_service.get_member(to_user_id, to_organization_id)
                if not to_member:
                    raise ValueError("To user is not a member of the specified organization")
            
            # Create permission
            permission = CreditTransferPermission(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                from_organization_id=from_organization_id,
                to_organization_id=to_organization_id,
                permission_type=permission_type,
                max_amount=max_amount,
                max_frequency=max_frequency,
                time_limit_hours=time_limit_hours,
                conditions=conditions or {},
                is_active=True,
                created_by=created_by or from_user_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(permission)
            self.db.commit()
            self.db.refresh(permission)
            
            logger.info(f"Created {permission_type} permission from user {from_user_id} to user {to_user_id}")
            
            return {
                "success": True,
                "permission": self._permission_to_dict(permission),
                "message": "Permission created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating permission: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_permissions(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        permission_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user
        """
        try:
            query = self.db.query(CreditTransferPermission).filter(
                or_(
                    CreditTransferPermission.from_user_id == user_id,
                    CreditTransferPermission.to_user_id == user_id
                )
            )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransferPermission.from_organization_id == organization_id,
                        CreditTransferPermission.to_organization_id == organization_id,
                        CreditTransferPermission.from_organization_id.is_(None),
                        CreditTransferPermission.to_organization_id.is_(None)
                    )
                )
            
            if permission_type:
                query = query.filter(CreditTransferPermission.permission_type == permission_type)
            
            if is_active is not None:
                query = query.filter(CreditTransferPermission.is_active == is_active)
            
            permissions = query.order_by(desc(CreditTransferPermission.created_at)).all()
            
            return [self._permission_to_dict(permission) for permission in permissions]
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return []
    
    def check_transfer_permission(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if a transfer is allowed based on permissions
        """
        try:
            # Get relevant permissions
            permissions = self.get_user_permissions(
                from_user_id, organization_id, is_active=True
            )
            
            relevant_permissions = []
            for permission in permissions:
                if (permission["to_user_id"] == to_user_id or 
                    permission["to_user_id"] is None):
                    relevant_permissions.append(permission)
            
            if not relevant_permissions:
                return {
                    "allowed": False,
                    "reason": "No transfer permissions found",
                    "requires_approval": True,
                    "permission_level": PermissionLevel.NONE.value
                }
            
            # Check each permission
            for permission in relevant_permissions:
                permission_type = permission["permission_type"]
                max_amount = permission.get("max_amount")
                
                # Check amount limit
                if max_amount and amount > max_amount:
                    return {
                        "allowed": False,
                        "reason": f"Amount exceeds permission limit of {max_amount}",
                        "requires_approval": True,
                        "permission_level": PermissionLevel.REQUEST.value
                    }
                
                # Check time limit
                if permission.get("time_limit_hours"):
                    created_at = datetime.fromisoformat(permission["created_at"])
                    hours_elapsed = (datetime.utcnow() - created_at).total_seconds() / 3600
                    if hours_elapsed > permission["time_limit_hours"]:
                        return {
                            "allowed": False,
                            "reason": "Permission has expired",
                            "requires_approval": True,
                            "permission_level": PermissionLevel.NONE.value
                        }
                
                # Check frequency limit
                if permission.get("max_frequency"):
                    recent_transfers = self._count_recent_transfers(
                        from_user_id, to_user_id, permission.get("max_frequency")
                    )
                    if recent_transfers >= permission["max_frequency"]:
                        return {
                            "allowed": False,
                            "reason": "Frequency limit exceeded",
                            "requires_approval": True,
                            "permission_level": PermissionLevel.REQUEST.value
                        }
                
                # Determine permission level and approval requirements
                if permission_type == "allow_transfer":
                    return {
                        "allowed": True,
                        "reason": "Direct transfer allowed",
                        "requires_approval": False,
                        "permission_level": PermissionLevel.FULL.value,
                        "permission_id": permission["id"]
                    }
                elif permission_type == "require_approval":
                    return {
                        "allowed": False,
                        "reason": "Transfer requires approval",
                        "requires_approval": True,
                        "permission_level": PermissionLevel.REQUEST.value,
                        "permission_id": permission["id"]
                    }
                elif permission_type == "rate_limit":
                    return {
                        "allowed": False,
                        "reason": "Rate limited transfer requires approval",
                        "requires_approval": True,
                        "permission_level": PermissionLevel.VIEW.value,
                        "permission_id": permission["id"]
                    }
                elif permission_type == "conditional_transfer":
                    # Check conditions
                    conditions = permission.get("conditions", {})
                    if self._check_transfer_conditions(amount, conditions):
                        return {
                            "allowed": True,
                            "reason": "Conditional transfer allowed",
                            "requires_approval": False,
                            "permission_level": PermissionLevel.FULL.value,
                            "permission_id": permission["id"]
                        }
                    else:
                        return {
                            "allowed": False,
                            "reason": "Transfer conditions not met",
                            "requires_approval": True,
                            "permission_level": PermissionLevel.REQUEST.value,
                            "permission_id": permission["id"]
                        }
            
            return {
                "allowed": False,
                "reason": "Insufficient permissions",
                "requires_approval": True,
                "permission_level": PermissionLevel.NONE.value
            }
            
        except Exception as e:
            logger.error(f"Error checking transfer permission: {str(e)}")
            return {
                "allowed": False,
                "reason": f"Permission check failed: {str(e)}",
                "requires_approval": True,
                "permission_level": PermissionLevel.NONE.value
            }
    
    def request_transfer_approval(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        reason: str,
        organization_id: Optional[int] = None,
        requested_by: int = None
    ) -> Dict[str, Any]:
        """
        Request approval for a credit transfer
        """
        try:
            # Check permissions
            permission_result = self.check_transfer_permission(
                from_user_id, to_user_id, amount, organization_id
            )
            
            if permission_result["allowed"]:
                return {
                    "success": False,
                    "error": "Transfer is already allowed, no approval needed"
                }
            
            # Get the relevant permission
            permission_id = permission_result.get("permission_id")
            if not permission_id:
                return {
                    "success": False,
                    "error": "No permission found to request approval against"
                }
            
            # Create pending transfer request
            transfer = CreditTransfer(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                from_organization_id=organization_id,
                to_organization_id=organization_id,  # Same org for now
                amount=amount,
                status=CreditTransferStatus.PENDING_APPROVAL,
                transfer_reason=reason,
                permission_id=permission_id,
                created_by=requested_by or from_user_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(transfer)
            self.db.commit()
            self.db.refresh(transfer)
            
            # Notify approvers
            self._notify_transfer_request(transfer)
            
            logger.info(f"Created transfer approval request {transfer.id} from user {from_user_id} to user {to_user_id}")
            
            return {
                "success": True,
                "transfer": self._transfer_to_dict(transfer),
                "message": "Transfer approval request created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error requesting transfer approval: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def approve_transfer(
        self,
        transfer_id: int,
        approver_id: int,
        approval_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a pending transfer
        """
        try:
            transfer = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.id == transfer_id,
                    CreditTransfer.status == CreditTransferStatus.PENDING_APPROVAL
                )
            ).first()
            
            if not transfer:
                return {
                    "success": False,
                    "error": "Transfer not found or not in pending approval status"
                }
            
            # Check if approver has permission
            can_approve = self._check_approval_permission(approver_id, transfer)
            if not can_approve:
                return {
                    "success": False,
                    "error": "Approver does not have permission to approve this transfer"
                }
            
            # Update transfer status
            transfer.status = CreditTransferStatus.APPROVED
            transfer.approved_by = approver_id
            transfer.approved_at = datetime.utcnow()
            transfer.approval_notes = approval_notes
            
            # Execute the transfer
            transfer_result = self.credit_manager.transfer_credits(
                from_user_id=transfer.from_user_id,
                to_user_id=transfer.to_user_id,
                amount=transfer.amount,
                reason=transfer.transfer_reason,
                organization_id=transfer.from_organization_id
            )
            
            if not transfer_result["success"]:
                transfer.status = CreditTransferStatus.FAILED
                transfer.failure_reason = transfer_result.get("error", "Transfer execution failed")
                self.db.commit()
                
                return {
                    "success": False,
                    "error": f"Transfer execution failed: {transfer_result.get('error')}"
                }
            
            # Notify involved parties
            self._notify_transfer_approval(transfer, approved=True)
            
            logger.info(f"Approved and executed transfer {transfer_id} by user {approver_id}")
            
            return {
                "success": True,
                "transfer": self._transfer_to_dict(transfer),
                "execution_result": transfer_result,
                "message": "Transfer approved and executed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error approving transfer: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def reject_transfer(
        self,
        transfer_id: int,
        approver_id: int,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Reject a pending transfer
        """
        try:
            transfer = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.id == transfer_id,
                    CreditTransfer.status == CreditTransferStatus.PENDING_APPROVAL
                )
            ).first()
            
            if not transfer:
                return {
                    "success": False,
                    "error": "Transfer not found or not in pending approval status"
                }
            
            # Check if approver has permission
            can_approve = self._check_approval_permission(approver_id, transfer)
            if not can_approve:
                return {
                    "success": False,
                    "error": "Approver does not have permission to reject this transfer"
                }
            
            # Update transfer status
            transfer.status = CreditTransferStatus.REJECTED
            transfer.approved_by = approver_id
            transfer.approved_at = datetime.utcnow()
            transfer.approval_notes = rejection_reason
            
            self.db.commit()
            
            # Notify involved parties
            self._notify_transfer_approval(transfer, approved=False)
            
            logger.info(f"Rejected transfer {transfer_id} by user {approver_id}: {rejection_reason}")
            
            return {
                "success": True,
                "transfer": self._transfer_to_dict(transfer),
                "message": "Transfer rejected successfully"
            }
            
        except Exception as e:
            logger.error(f"Error rejecting transfer: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pending_approvals(
        self,
        approver_id: int,
        organization_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transfers pending approval for a user
        """
        try:
            # Get transfers that can be approved by this user
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.status == CreditTransferStatus.PENDING_APPROVAL
            )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_organization_id == organization_id,
                        CreditTransfer.to_organization_id == organization_id
                    )
                )
            
            transfers = query.order_by(desc(CreditTransfer.created_at)).all()
            
            # Filter by approval permission
            approvals = []
            for transfer in transfers:
                if self._check_approval_permission(approver_id, transfer):
                    approvals.append(self._transfer_to_dict(transfer))
            
            return approvals
            
        except Exception as e:
            logger.error(f"Error getting pending approvals: {str(e)}")
            return []
    
    def update_permission(
        self,
        permission_id: int,
        user_id: int,
        **updates
    ) -> Dict[str, Any]:
        """
        Update an existing permission
        """
        try:
            permission = self.db.query(CreditTransferPermission).filter(
                and_(
                    CreditTransferPermission.id == permission_id,
                    CreditTransferPermission.created_by == user_id
                )
            ).first()
            
            if not permission:
                return {
                    "success": False,
                    "error": "Permission not found"
                }
            
            # Validate updates
            if "max_amount" in updates and updates["max_amount"] and updates["max_amount"] <= 0:
                raise ValueError("Max amount must be positive")
            
            if "max_frequency" in updates and updates["max_frequency"] and updates["max_frequency"] <= 0:
                raise ValueError("Max frequency must be positive")
            
            if "time_limit_hours" in updates and updates["time_limit_hours"] and updates["time_limit_hours"] <= 0:
                raise ValueError("Time limit hours must be positive")
            
            # Update allowed fields
            allowed_fields = [
                "permission_type", "max_amount", "max_frequency", 
                "time_limit_hours", "conditions", "is_active"
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(permission, field, value)
            
            permission.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(permission)
            
            logger.info(f"Updated permission {permission_id} by user {user_id}")
            
            return {
                "success": True,
                "permission": self._permission_to_dict(permission),
                "message": "Permission updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating permission: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_permission(self, permission_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete a permission
        """
        try:
            permission = self.db.query(CreditTransferPermission).filter(
                and_(
                    CreditTransferPermission.id == permission_id,
                    CreditTransferPermission.created_by == user_id
                )
            ).first()
            
            if not permission:
                return {
                    "success": False,
                    "error": "Permission not found"
                }
            
            # Check if there are any active transfers using this permission
            active_transfers = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.permission_id == permission_id,
                    CreditTransfer.status.in_([
                        CreditTransferStatus.PENDING,
                        CreditTransferStatus.PENDING_APPROVAL
                    ])
                )
            ).count()
            
            if active_transfers > 0:
                return {
                    "success": False,
                    "error": "Cannot delete permission with active transfers. Deactivate instead."
                }
            
            self.db.delete(permission)
            self.db.commit()
            
            logger.info(f"Deleted permission {permission_id} by user {user_id}")
            
            return {
                "success": True,
                "message": "Permission deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting permission: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_transfer_conditions(self, amount: Decimal, conditions: Dict[str, Any]) -> bool:
        """
        Check if transfer meets specified conditions
        """
        try:
            # Example conditions check
            if "minimum_amount" in conditions and amount < Decimal(str(conditions["minimum_amount"])):
                return False
            
            if "maximum_amount" in conditions and amount > Decimal(str(conditions["maximum_amount"])):
                return False
            
            if "require_business_hours" in conditions and conditions["require_business_hours"]:
                current_hour = datetime.utcnow().hour
                if not (9 <= current_hour <= 17):  # 9 AM to 5 PM UTC
                    return False
            
            # Add more condition checks as needed
            return True
            
        except Exception as e:
            logger.error(f"Error checking transfer conditions: {str(e)}")
            return False
    
    def _count_recent_transfers(self, from_user_id: int, to_user_id: int, hours: int = 24) -> int:
        """
        Count transfers between users in the last N hours
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            count = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.from_user_id == from_user_id,
                    CreditTransfer.to_user_id == to_user_id,
                    CreditTransfer.status == CreditTransferStatus.COMPLETED,
                    CreditTransfer.created_at >= start_time
                )
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting recent transfers: {str(e)}")
            return 0
    
    def _check_approval_permission(self, approver_id: int, transfer: CreditTransfer) -> bool:
        """
        Check if user has permission to approve the transfer
        """
        try:
            # Organization administrators can approve transfers within their org
            if transfer.from_organization_id:
                member = self.org_service.get_member(approver_id, transfer.from_organization_id)
                if member and member.role in ["admin", "owner"]:
                    return True
            
            if transfer.to_organization_id:
                member = self.org_service.get_member(approver_id, transfer.to_organization_id)
                if member and member.role in ["admin", "owner"]:
                    return True
            
            # The recipient can approve transfers to themselves
            if transfer.to_user_id == approver_id:
                return True
            
            # System administrators (this would be implemented based on your auth system)
            # For now, return False
            return False
            
        except Exception as e:
            logger.error(f"Error checking approval permission: {str(e)}")
            return False
    
    def _notify_transfer_request(self, transfer: CreditTransfer):
        """
        Notify approvers of transfer request
        """
        try:
            # Get potential approvers
            approvers = []
            
            # Organization admins
            if transfer.from_organization_id:
                org_members = self.org_service.get_organization_members(transfer.from_organization_id)
                for member in org_members:
                    if member.role in ["admin", "owner"]:
                        approvers.append(member.user_id)
            
            # The recipient
            approvers.append(transfer.to_user_id)
            
            # Remove duplicates
            approvers = list(set(approvers))
            
            # Send notifications
            for approver_id in approvers:
                self.notification_service.send_notification(
                    user_id=approver_id,
                    notification_type="transfer_request",
                    title="Credit Transfer Request",
                    message=f"A transfer of {transfer.amount} credits is pending your approval",
                    data={
                        "transfer_id": transfer.id,
                        "from_user_id": transfer.from_user_id,
                        "amount": str(transfer.amount),
                        "reason": transfer.transfer_reason
                    }
                )
                
        except Exception as e:
            logger.error(f"Error notifying transfer request: {str(e)}")
    
    def _notify_transfer_approval(self, transfer: CreditTransfer, approved: bool):
        """
        Notify involved parties of transfer approval/rejection
        """
        try:
            # Notify the requester
            self.notification_service.send_notification(
                user_id=transfer.created_by,
                notification_type="transfer_response",
                title="Credit Transfer Response",
                message=f"Transfer of {transfer.amount} credits has been {'approved' if approved else 'rejected'}",
                data={
                    "transfer_id": transfer.id,
                    "status": transfer.status.value,
                    "approved": approved,
                    "notes": transfer.approval_notes
                }
            )
            
        except Exception as e:
            logger.error(f"Error notifying transfer approval: {str(e)}")
    
    def _permission_to_dict(self, permission: CreditTransferPermission) -> Dict[str, Any]:
        """
        Convert permission model to dictionary
        """
        return {
            "id": permission.id,
            "from_user_id": permission.from_user_id,
            "to_user_id": permission.to_user_id,
            "from_organization_id": permission.from_organization_id,
            "to_organization_id": permission.to_organization_id,
            "permission_type": permission.permission_type,
            "max_amount": float(permission.max_amount) if permission.max_amount else None,
            "max_frequency": permission.max_frequency,
            "time_limit_hours": permission.time_limit_hours,
            "conditions": permission.conditions,
            "is_active": permission.is_active,
            "created_by": permission.created_by,
            "created_at": permission.created_at.isoformat() if permission.created_at else None,
            "updated_at": permission.updated_at.isoformat() if permission.updated_at else None
        }
    
    def _transfer_to_dict(self, transfer: CreditTransfer) -> Dict[str, Any]:
        """
        Convert transfer model to dictionary
        """
        return {
            "id": transfer.id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "from_organization_id": transfer.from_organization_id,
            "to_organization_id": transfer.to_organization_id,
            "amount": float(transfer.amount),
            "status": transfer.status.value,
            "transfer_reason": transfer.transfer_reason,
            "permission_id": transfer.permission_id,
            "approved_by": transfer.approved_by,
            "approved_at": transfer.approved_at.isoformat() if transfer.approved_at else None,
            "approval_notes": transfer.approval_notes,
            "failure_reason": transfer.failure_reason,
            "created_by": transfer.created_by,
            "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
            "updated_at": transfer.updated_at.isoformat() if transfer.updated_at else None
        }