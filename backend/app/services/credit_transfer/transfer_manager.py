"""
Credit Transfer Manager

Service for managing credit transfers between users and teams.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditTransfer, CreditBalance, CreditTransaction, CreditTransactionType, 
    CreditStatus, CreditPolicy
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_policies import CreditPoliciesService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CreditTransferManager:
    """
    Service for managing credit transfers
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.policy_service = CreditPoliciesService(db)
    
    def initiate_transfer(self, from_user_id: int, to_user_id: int, credit_amount: float,
                        reason: str = "Credit transfer", organization_id: Optional[int] = None,
                        reference_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiate a credit transfer
        """
        try:
            # Validate transfer
            validation_result = self._validate_transfer(
                from_user_id, to_user_id, credit_amount, organization_id
            )
            
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Check if approval is required
            approval_required = validation_result["requires_approval"]
            
            # Create transfer record
            transfer_id = f"transfer_{from_user_id}_{to_user_id}_{datetime.utcnow().timestamp()}"
            
            transfer = CreditTransfer(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                from_organization_id=organization_id if validation_result["is_organization_transfer"] else None,
                to_organization_id=organization_id,  # Same organization for now
                transfer_id=transfer_id,
                credit_amount=credit_amount,
                reason=reason,
                reference_id=reference_id,
                requires_approval=approval_required,
                status="pending" if approval_required else "approved"
            )
            
            self.db.add(transfer)
            self.db.commit()
            self.db.refresh(transfer)
            
            if not approval_required:
                # Execute transfer immediately
                execution_result = self._execute_transfer(transfer.id)
                return execution_result
            else:
                # Transfer requires approval
                logger.info(f"Transfer {transfer_id} created and requires approval")
                
                return {
                    "success": True,
                    "transfer_id": transfer_id,
                    "status": "pending_approval",
                    "requires_approval": True,
                    "message": "Transfer requires approval before execution"
                }
                
        except Exception as e:
            logger.error(f"Error initiating transfer: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _validate_transfer(self, from_user_id: int, to_user_id: int, 
                          credit_amount: float, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate transfer parameters and policies
        """
        # Basic validation
        if from_user_id == to_user_id:
            return {"valid": False, "error": "Cannot transfer credits to same user"}
        
        if credit_amount <= 0:
            return {"valid": False, "error": "Credit amount must be positive"}
        
        if credit_amount > 100000:  # Reasonable limit
            return {"valid": False, "error": "Credit amount exceeds maximum transfer limit"}
        
        # Check source user balance
        if not self.credit_manager.check_sufficient_credits(from_user_id, credit_amount, organization_id):
            return {"valid": False, "error": "Insufficient credits for transfer"}
        
        # Check destination user exists
        # In a real implementation, this would check user database
        # For now, we'll assume user exists if they have a balance
        dest_balance = self.credit_manager.get_balance(to_user_id, organization_id)
        if not dest_balance:
            # Create balance for destination user if needed
            self.credit_manager.get_or_create_balance(to_user_id, organization_id)
        
        # Check transfer policies
        transfer_policies = self.policy_service.get_applicable_policies(
            "transfer", from_user_id, organization_id
        )
        
        if transfer_policies:
            policy = transfer_policies[0]  # Apply highest priority policy
            config = policy.config or {}
            
            # Check maximum transfer amount
            max_transfer = config.get("max_transfer_amount", float('inf'))
            if credit_amount > max_transfer:
                return {
                    "valid": False, 
                    "error": f"Transfer amount exceeds policy limit of {max_transfer} credits"
                }
            
            # Check if approval is required
            requires_approval = config.get("require_approval", False)
            transfer_fee_percentage = config.get("transfer_fee_percentage", 0)
            
            # Calculate transfer fee
            transfer_fee = credit_amount * (transfer_fee_percentage / 100)
            
            # Check if destination is organization
            is_organization_transfer = organization_id is not None
            
            return {
                "valid": True,
                "requires_approval": requires_approval,
                "transfer_fee": transfer_fee,
                "is_organization_transfer": is_organization_transfer,
                "policy_applied": policy.name
            }
        
        # No specific policy found, use defaults
        return {
            "valid": True,
            "requires_approval": False,
            "transfer_fee": 0,
            "is_organization_transfer": organization_id is not None,
            "policy_applied": "default"
        }
    
    def _execute_transfer(self, transfer_id: int) -> Dict[str, Any]:
        """
        Execute an approved transfer
        """
        try:
            # Get transfer record
            transfer = self.db.query(CreditTransfer).filter(
                CreditTransfer.id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status != "approved":
                return {"success": False, "error": f"Transfer status is {transfer.status}, cannot execute"}
            
            # Calculate total amount including fees
            transfer_fee = self._calculate_transfer_fee(transfer)
            total_required = transfer.credit_amount + transfer_fee
            
            # Check source user still has sufficient credits
            if not self.credit_manager.check_sufficient_credits(
                transfer.from_user_id, total_required, transfer.from_organization_id
            ):
                transfer.status = "failed"
                transfer.completed_at = datetime.utcnow()
                self.db.commit()
                return {"success": False, "error": "Insufficient credits to complete transfer"}
            
            # Execute transfer
            success = self.credit_manager.allocate_credits_to_user(
                from_user_id=transfer.from_user_id,
                to_user_id=transfer.to_user_id,
                credit_amount=transfer.credit_amount,
                description=f"Transfer: {transfer.reason}",
                organization_id=transfer.from_organization_id
            )
            
            if success:
                # Update transfer status
                transfer.status = "completed"
                transfer.completed_at = datetime.utcnow()
                
                # Create transaction records
                from_transaction = self.credit_manager.deduct_credits(
                    user_id=transfer.from_user_id,
                    credit_amount=transfer_fee,
                    transaction_type=CreditTransactionType.TRANSFER_OUT,
                    description=f"Transfer fee for transfer {transfer.transfer_id}",
                    reference_type="transfer_fee",
                    reference_id=transfer.transfer_id,
                    organization_id=transfer.from_organization_id
                )
                
                self.db.commit()
                
                logger.info(f"Transfer {transfer.transfer_id} completed successfully")
                
                return {
                    "success": True,
                    "transfer_id": transfer.transfer_id,
                    "status": "completed",
                    "credit_amount": transfer.credit_amount,
                    "transfer_fee": transfer_fee,
                    "completed_at": transfer.completed_at.isoformat()
                }
            else:
                transfer.status = "failed"
                transfer.completed_at = datetime.utcnow()
                self.db.commit()
                return {"success": False, "error": "Failed to execute transfer"}
                
        except Exception as e:
            logger.error(f"Error executing transfer {transfer_id}: {e}")
            
            # Mark transfer as failed
            try:
                transfer = self.db.query(CreditTransfer).filter(
                    CreditTransfer.id == transfer_id
                ).first()
                
                if transfer:
                    transfer.status = "failed"
                    transfer.completed_at = datetime.utcnow()
                    self.db.commit()
            except:
                pass
            
            return {"success": False, "error": str(e)}
    
    def _calculate_transfer_fee(self, transfer: CreditTransfer) -> float:
        """
        Calculate transfer fee based on policies
        """
        # Get applicable transfer policies
        policies = self.policy_service.get_applicable_policies(
            "transfer", transfer.from_user_id, transfer.from_organization_id
        )
        
        if not policies:
            return 0
        
        policy = policies[0]
        config = policy.config or {}
        
        fee_percentage = config.get("transfer_fee_percentage", 0)
        return transfer.credit_amount * (fee_percentage / 100)
    
    def approve_transfer(self, transfer_id: int, approved_by: int) -> Dict[str, Any]:
        """
        Approve a pending transfer
        """
        try:
            transfer = self.db.query(CreditTransfer).filter(
                CreditTransfer.transfer_id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status != "pending":
                return {"success": False, "error": f"Transfer status is {transfer.status}, cannot approve"}
            
            if not transfer.requires_approval:
                return {"success": False, "error": "Transfer does not require approval"}
            
            # Approve transfer
            transfer.status = "approved"
            transfer.approved_by = approved_by
            transfer.approved_at = datetime.utcnow()
            
            self.db.commit()
            
            # Execute transfer immediately after approval
            execution_result = self._execute_transfer(transfer.id)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error approving transfer {transfer_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def reject_transfer(self, transfer_id: int, rejected_by: int, 
                       rejection_reason: str = "Transfer rejected") -> Dict[str, Any]:
        """
        Reject a pending transfer
        """
        try:
            transfer = self.db.query(CreditTransfer).filter(
                CreditTransfer.transfer_id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status != "pending":
                return {"success": False, "error": f"Transfer status is {transfer.status}, cannot reject"}
            
            # Reject transfer
            transfer.status = "rejected"
            transfer.completed_at = datetime.utcnow()
            transfer.rejection_reason = rejection_reason
            transfer.approved_by = rejected_by  # Using approved_by field for who rejected
            transfer.approved_at = datetime.utcnow()  # Using approved_at for when rejected
            
            self.db.commit()
            
            logger.info(f"Transfer {transfer_id} rejected by user {rejected_by}")
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "status": "rejected",
                "rejection_reason": rejection_reason,
                "rejected_at": transfer.completed_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error rejecting transfer {transfer_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_transfer(self, transfer_id: int, cancelled_by: int) -> Dict[str, Any]:
        """
        Cancel a pending transfer
        """
        try:
            transfer = self.db.query(CreditTransfer).filter(
                CreditTransfer.transfer_id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status not in ["pending", "approved"]:
                return {"success": False, "error": f"Transfer status is {transfer.status}, cannot cancel"}
            
            # Check if user can cancel (originator or admin)
            if transfer.from_user_id != cancelled_by:
                # In a real implementation, check if user has admin privileges
                pass
            
            # Cancel transfer
            transfer.status = "canceled"
            transfer.completed_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Transfer {transfer_id} canceled by user {cancelled_by}")
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "status": "canceled",
                "canceled_at": transfer.completed_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error canceling transfer {transfer_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_transfer_details(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a transfer
        """
        transfer = self.db.query(CreditTransfer).filter(
            CreditTransfer.transfer_id == transfer_id
        ).first()
        
        if not transfer:
            return None
        
        return {
            "transfer_id": transfer.transfer_id,
            "from_user_id": transfer.from_user_id,
            "to_user_id": transfer.to_user_id,
            "from_organization_id": transfer.from_organization_id,
            "to_organization_id": transfer.to_organization_id,
            "credit_amount": transfer.credit_amount,
            "reason": transfer.reason,
            "reference_id": transfer.reference_id,
            "status": {
                "status": transfer.status,
                "requires_approval": transfer.requires_approval,
                "approved_by": transfer.approved_by,
                "approved_at": transfer.approved_at.isoformat() if transfer.approved_at else None,
                "rejection_reason": transfer.rejection_reason
            },
            "timing": {
                "created_at": transfer.created_at.isoformat(),
                "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None
            },
            "transaction_records": {
                "from_transaction_id": transfer.from_transaction_id,
                "to_transaction_id": transfer.to_transaction_id
            }
        }
    
    def get_user_transfers(self, user_id: int, limit: int = 50,
                          transfer_type: str = "all",
                          organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get transfers for a user (incoming and outgoing)
        """
        if transfer_type == "outgoing":
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.from_user_id == user_id
            )
        elif transfer_type == "incoming":
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.to_user_id == user_id
            )
        else:  # all
            query = self.db.query(CreditTransfer).filter(
                or_(
                    CreditTransfer.from_user_id == user_id,
                    CreditTransfer.to_user_id == user_id
                )
            )
        
        if organization_id:
            query = query.filter(
                or_(
                    CreditTransfer.from_organization_id == organization_id,
                    CreditTransfer.to_organization_id == organization_id
                )
            )
        
        transfers = query.order_by(desc(CreditTransfer.created_at)).limit(limit).all()
        
        return [
            {
                "transfer_id": transfer.transfer_id,
                "direction": "outgoing" if transfer.from_user_id == user_id else "incoming",
                "other_party_id": transfer.to_user_id if transfer.from_user_id == user_id else transfer.from_user_id,
                "credit_amount": transfer.credit_amount,
                "reason": transfer.reason,
                "status": transfer.status,
                "requires_approval": transfer.requires_approval,
                "created_at": transfer.created_at.isoformat(),
                "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None
            }
            for transfer in transfers
        ]
    
    def get_pending_approvals(self, user_id: int, organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get transfers pending approval for user
        """
        query = self.db.query(CreditTransfer).filter(
            CreditTransfer.status == "pending",
            CreditTransfer.requires_approval == True
        )
        
        # Filter for transfers user can approve
        if organization_id:
            query = query.filter(
                CreditTransfer.to_organization_id == organization_id
            )
        
        # In a real implementation, this would filter based on approval permissions
        # For now, assume all pending transfers can be approved by organization members
        pending_transfers = query.order_by(desc(CreditTransfer.created_at)).limit(50).all()
        
        return [
            {
                "transfer_id": transfer.transfer_id,
                "from_user_id": transfer.from_user_id,
                "to_user_id": transfer.to_user_id,
                "credit_amount": transfer.credit_amount,
                "reason": transfer.reason,
                "created_at": transfer.created_at.isoformat(),
                "age_hours": (datetime.utcnow() - transfer.created_at).total_seconds() / 3600
            }
            for transfer in pending_transfers
        ]
    
    def bulk_transfer(self, from_user_id: int, recipients: List[Dict[str, Any]],
                    organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute bulk transfer to multiple recipients
        """
        try:
            total_required = sum(recipient["credit_amount"] for recipient in recipients)
            
            # Validate total transfer
            if not self.credit_manager.check_sufficient_credits(from_user_id, total_required, organization_id):
                return {"success": False, "error": "Insufficient credits for bulk transfer"}
            
            # Execute individual transfers
            transfer_results = []
            successful_transfers = 0
            failed_transfers = 0
            
            for recipient in recipients:
                result = self.initiate_transfer(
                    from_user_id=from_user_id,
                    to_user_id=recipient["user_id"],
                    credit_amount=recipient["credit_amount"],
                    reason=recipient.get("reason", "Bulk transfer"),
                    organization_id=organization_id,
                    reference_id=recipient.get("reference_id")
                )
                
                transfer_results.append({
                    "user_id": recipient["user_id"],
                    "credit_amount": recipient["credit_amount"],
                    "result": result
                })
                
                if result["success"]:
                    successful_transfers += 1
                else:
                    failed_transfers += 1
            
            return {
                "success": successful_transfers > 0,
                "total_recipients": len(recipients),
                "successful_transfers": successful_transfers,
                "failed_transfers": failed_transfers,
                "total_credits_transferred": sum(
                    result["credit_amount"] for result in transfer_results 
                    if result["result"]["success"]
                ),
                "transfer_results": transfer_results
            }
            
        except Exception as e:
            logger.error(f"Error in bulk transfer: {e}")
            return {"success": False, "error": str(e)}
    
    def get_transfer_analytics(self, user_id: Optional[int] = None, 
                             days: int = 30) -> Dict[str, Any]:
        """
        Get transfer analytics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get transfer data
        query = self.db.query(CreditTransfer).filter(
            CreditTransfer.created_at >= start_date,
            CreditTransfer.created_at <= end_date
        )
        
        if user_id:
            query = query.filter(
                or_(
                    CreditTransfer.from_user_id == user_id,
                    CreditTransfer.to_user_id == user_id
                )
            )
        
        transfers = query.all()
        
        if not transfers:
            return {
                "period_days": days,
                "total_transfers": 0,
                "total_credits_transferred": 0,
                "transfer_patterns": {}
            }
        
        # Analyze transfers
        total_transfers = len(transfers)
        total_credits_transferred = sum(t.credit_amount for t in transfers)
        
        # Status breakdown
        status_breakdown = {}
        for transfer in transfers:
            status = transfer.status
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        # Calculate approval rate
        pending_transfers = status_breakdown.get("pending", 0)
        completed_transfers = status_breakdown.get("completed", 0)
        approval_rate = (completed_transfers / max(pending_transfers + completed_transfers, 1)) * 100
        
        # Average transfer size
        average_transfer_size = total_credits_transferred / total_transfers if total_transfers > 0 else 0
        
        # Most active transfer pairs
        transfer_pairs = {}
        for transfer in transfers:
            if transfer.status == "completed":
                pair = f"{min(transfer.from_user_id, transfer.to_user_id)}-{max(transfer.from_user_id, transfer.to_user_id)}"
                transfer_pairs[pair] = transfer_pairs.get(pair, 0) + 1
        
        # Get top transfer pairs
        top_pairs = sorted(transfer_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "summary": {
                "total_transfers": total_transfers,
                "total_credits_transferred": total_credits_transferred,
                "average_transfer_size": average_transfer_size,
                "approval_rate": approval_rate
            },
            "status_breakdown": status_breakdown,
            "top_transfer_pairs": [
                {"user_pair": pair, "transfer_count": count}
                for pair, count in top_pairs
            ],
            "daily_activity": self._get_daily_transfer_activity(transfers)
        }
    
    def _get_daily_transfer_activity(self, transfers: List[CreditTransfer]) -> Dict[str, int]:
        """
        Get daily transfer activity
        """
        daily_counts = {}
        for transfer in transfers:
            day = transfer.created_at.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1
        
        return daily_counts


# Utility functions
def get_credit_transfer_manager(db: Session = None) -> CreditTransferManager:
    """
    Get CreditTransferManager instance
    """
    if db is None:
        db = next(get_db())
    return CreditTransferManager(db)


def initiate_credit_transfer(from_user_id: int, to_user_id: int, credit_amount: float,
                           reason: str = "Credit transfer", db: Session = None) -> Dict[str, Any]:
    """
    Quick function to initiate credit transfer
    """
    manager = get_credit_transfer_manager(db)
    return manager.initiate_transfer(from_user_id, to_user_id, credit_amount, reason)