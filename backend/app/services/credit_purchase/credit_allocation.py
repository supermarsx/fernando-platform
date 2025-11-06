"""
Credit Allocation Service

Automatic credit allocation to users and teams.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.credits import (
    CreditBalance, CreditTransaction, CreditTransactionType, CreditStatus,
    CreditPurchaseTransaction
)
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_purchase.purchase_manager import CreditPurchaseManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CreditAllocationService:
    """
    Service for automatic credit allocation to users and teams
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.purchase_manager = CreditPurchaseManager(db)
    
    def allocate_credits_to_user(self, from_user_id: int, to_user_id: int,
                               credit_amount: float, description: str = "Credit allocation",
                               organization_id: Optional[int] = None,
                               expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Allocate credits from one user to another
        """
        try:
            # Check if source user has sufficient credits
            if not self.credit_manager.check_sufficient_credits(from_user_id, credit_amount, organization_id):
                return {"success": False, "error": "Insufficient credits to allocate"}
            
            # Deduct credits from source user
            deduction_success = self.credit_manager.deduct_credits(
                user_id=from_user_id,
                credit_amount=credit_amount,
                transaction_type=CreditTransactionType.TRANSFER_OUT,
                description=f"Allocation to user {to_user_id}: {description}",
                reference_type="allocation",
                organization_id=organization_id
            )
            
            if not deduction_success:
                return {"success": False, "error": "Failed to deduct credits from source user"}
            
            # Add credits to destination user
            addition_success = self.credit_manager.add_credits(
                user_id=to_user_id,
                credit_amount=credit_amount,
                transaction_type=CreditTransactionType.TRANSFER_IN,
                description=f"Allocation from user {from_user_id}: {description}",
                expires_at=expires_at,
                organization_id=organization_id
            )
            
            if not addition_success:
                # Rollback deduction if addition fails
                self.credit_manager.add_credits(
                    user_id=from_user_id,
                    credit_amount=credit_amount,
                    transaction_type=CreditTransactionType.REVERSAL,
                    description=f"Reversed allocation to user {to_user_id} due to allocation failure",
                    organization_id=organization_id
                )
                return {"success": False, "error": "Failed to add credits to destination user"}
            
            logger.info(f"Allocated {credit_amount} credits from user {from_user_id} to user {to_user_id}")
            
            return {
                "success": True,
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "credit_amount": credit_amount,
                "description": description,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "allocated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error allocating credits: {e}")
            return {"success": False, "error": str(e)}
    
    def allocate_credits_to_team(self, from_user_id: int, team_member_ids: List[int],
                               credit_amounts: List[float], description: str = "Team allocation",
                               organization_id: Optional[int] = None,
                               expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Allocate credits to multiple team members
        """
        try:
            if len(team_member_ids) != len(credit_amounts):
                return {"success": False, "error": "Number of team members must match number of credit amounts"}
            
            total_required = sum(credit_amounts)
            
            # Check if source user has sufficient credits
            if not self.credit_manager.check_sufficient_credits(from_user_id, total_required, organization_id):
                return {"success": False, "error": "Insufficient credits for team allocation"}
            
            allocation_results = []
            total_allocated = 0
            
            # Allocate credits to each team member
            for user_id, amount in zip(team_member_ids, credit_amounts):
                if amount > 0:
                    result = self.allocate_credits_to_user(
                        from_user_id=from_user_id,
                        to_user_id=user_id,
                        credit_amount=amount,
                        description=f"Team allocation: {description}",
                        organization_id=organization_id,
                        expires_at=expires_at
                    )
                    
                    if result["success"]:
                        allocation_results.append(result)
                        total_allocated += amount
                    else:
                        allocation_results.append({
                            "success": False,
                            "user_id": user_id,
                            "error": result["error"]
                        })
            
            # Update source user balance to reflect total allocation
            if total_allocated > 0:
                self.credit_manager.deduct_credits(
                    user_id=from_user_id,
                    credit_amount=total_allocated,
                    transaction_type=CreditTransactionType.TRANSFER_OUT,
                    description=f"Total team allocation: {description}",
                    reference_type="team_allocation",
                    organization_id=organization_id
                )
            
            successful_allocations = len([r for r in allocation_results if r.get("success")])
            
            return {
                "success": successful_allocations > 0,
                "from_user_id": from_user_id,
                "total_allocated": total_allocated,
                "total_required": total_required,
                "successful_allocations": successful_allocations,
                "failed_allocations": len(allocation_results) - successful_allocations,
                "allocation_results": allocation_results,
                "description": description,
                "allocated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in team allocation: {e}")
            return {"success": False, "error": str(e)}
    
    def allocate_credits_to_organization(self, from_user_id: int, organization_id: int,
                                       credit_amount: float, description: str = "Organization allocation",
                                       expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Allocate credits to organization pool
        """
        try:
            # Check if source user has sufficient credits
            if not self.credit_manager.check_sufficient_credits(from_user_id, credit_amount, organization_id):
                return {"success": False, "error": "Insufficient credits to allocate to organization"}
            
            # For organization allocation, credits go to the organization balance
            # This would need organization balance management
            organization_balance = self.credit_manager.get_or_create_balance(
                user_id=organization_id,  # Using organization_id as user_id for org balance
                organization_id=organization_id
            )
            
            # Deduct from source user
            deduction_success = self.credit_manager.deduct_credits(
                user_id=from_user_id,
                credit_amount=credit_amount,
                transaction_type=CreditTransactionType.TRANSFER_OUT,
                description=f"Allocation to organization {organization_id}: {description}",
                reference_type="organization_allocation",
                organization_id=organization_id
            )
            
            if not deduction_success:
                return {"success": False, "error": "Failed to deduct credits from source user"}
            
            # Add to organization balance
            addition_success = self.credit_manager.add_credits(
                user_id=organization_id,  # Organization as user
                credit_amount=credit_amount,
                transaction_type=CreditTransactionType.TRANSFER_IN,
                description=f"Allocation from user {from_user_id}: {description}",
                expires_at=expires_at,
                organization_id=organization_id
            )
            
            if not addition_success:
                # Rollback
                self.credit_manager.add_credits(
                    user_id=from_user_id,
                    credit_amount=credit_amount,
                    transaction_type=CreditTransactionType.REVERSAL,
                    description=f"Reversed organization allocation due to failure",
                    organization_id=organization_id
                )
                return {"success": False, "error": "Failed to add credits to organization"}
            
            logger.info(f"Allocated {credit_amount} credits from user {from_user_id} to organization {organization_id}")
            
            return {
                "success": True,
                "from_user_id": from_user_id,
                "organization_id": organization_id,
                "credit_amount": credit_amount,
                "description": description,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "allocated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error allocating credits to organization: {e}")
            return {"success": False, "error": str(e)}
    
    def auto_allocate_from_purchase(self, purchase_id: str, allocation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically allocate credits from a purchase based on rules
        """
        try:
            # Get purchase transaction
            purchase = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.purchase_id == purchase_id
            ).first()
            
            if not purchase:
                return {"success": False, "error": "Purchase not found"}
            
            if purchase.status != "completed":
                return {"success": False, "error": "Purchase not completed"}
            
            total_credits = purchase.total_credits
            allocation_type = allocation_rules.get("type", "team")
            
            if allocation_type == "team":
                return self._auto_allocate_to_team(purchase, allocation_rules)
            elif allocation_type == "organization":
                return self._auto_allocate_to_organization(purchase, allocation_rules)
            elif allocation_type == "equal_split":
                return self._auto_allocate_equal_split(purchase, allocation_rules)
            else:
                return {"success": False, "error": "Invalid allocation type"}
                
        except Exception as e:
            logger.error(f"Error in auto allocation: {e}")
            return {"success": False, "error": str(e)}
    
    def _auto_allocate_to_team(self, purchase: CreditPurchaseTransaction, 
                             rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-allocate to team based on rules
        """
        team_members = rules.get("team_members", [])
        if not team_members:
            return {"success": False, "error": "No team members specified"}
        
        allocation_per_member = purchase.total_credits / len(team_members)
        allocation_amounts = [allocation_per_member] * len(team_members)
        
        return self.allocate_credits_to_team(
            from_user_id=purchase.user_id,
            team_member_ids=team_members,
            credit_amounts=allocation_amounts,
            description=f"Auto-allocation from purchase {purchase.purchase_id}",
            organization_id=purchase.organization_id,
            expires_at=purchase.expires_at
        )
    
    def _auto_allocate_to_organization(self, purchase: CreditPurchaseTransaction,
                                     rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-allocate to organization based on rules
        """
        organization_id = rules.get("organization_id", purchase.organization_id)
        if not organization_id:
            return {"success": False, "error": "No organization specified"}
        
        return self.allocate_credits_to_organization(
            from_user_id=purchase.user_id,
            organization_id=organization_id,
            credit_amount=purchase.total_credits,
            description=f"Auto-allocation from purchase {purchase.purchase_id}",
            expires_at=purchase.expires_at
        )
    
    def _auto_allocate_equal_split(self, purchase: CreditPurchaseTransaction,
                                 rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-allocate equal split to specified users
        """
        recipients = rules.get("recipients", [])
        if not recipients:
            return {"success": False, "error": "No recipients specified"}
        
        allocation_per_person = purchase.total_credits / len(recipients)
        allocation_amounts = [allocation_per_person] * len(recipients)
        
        # Treat recipients as team members
        return self.allocate_credits_to_team(
            from_user_id=purchase.user_id,
            team_member_ids=recipients,
            credit_amounts=allocation_amounts,
            description=f"Equal split allocation from purchase {purchase.purchase_id}",
            organization_id=purchase.organization_id,
            expires_at=purchase.expires_at
        )
    
    def get_allocation_history(self, user_id: int, limit: int = 50,
                             organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get allocation history for user
        """
        # Get transfer transactions (both outgoing and incoming)
        outgoing_transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type.in_([CreditTransactionType.TRANSFER_OUT]),
            CreditTransaction.status == CreditStatus.COMPLETED
        ).order_by(CreditTransaction.created_at.desc()).limit(limit // 2).all()
        
        incoming_transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == CreditTransactionType.TRANSFER_IN,
            CreditTransaction.status == CreditStatus.COMPLETED
        ).order_by(CreditTransaction.created_at.desc()).limit(limit // 2).all()
        
        # Format results
        allocation_history = []
        
        for transaction in outgoing_transactions:
            allocation_history.append({
                "transaction_id": transaction.transaction_id,
                "type": "outgoing",
                "credit_amount": -transaction.credit_amount,  # Negative because it's outgoing
                "description": transaction.description,
                "reference_type": transaction.reference_type,
                "reference_id": transaction.reference_id,
                "to_user_id": getattr(transaction, 'destination_user_id', None),
                "organization_id": transaction.organization_id,
                "created_at": transaction.created_at.isoformat()
            })
        
        for transaction in incoming_transactions:
            allocation_history.append({
                "transaction_id": transaction.transaction_id,
                "type": "incoming",
                "credit_amount": transaction.credit_amount,
                "description": transaction.description,
                "reference_type": transaction.reference_type,
                "reference_id": transaction.reference_id,
                "from_user_id": getattr(transaction, 'source_user_id', None),
                "organization_id": transaction.organization_id,
                "created_at": transaction.created_at.isoformat()
            })
        
        # Sort by creation date
        allocation_history.sort(key=lambda x: x["created_at"], reverse=True)
        
        return allocation_history[:limit]
    
    def calculate_allocation_statistics(self, user_id: int, days: int = 30,
                                      organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate allocation statistics for user
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get transfer transactions in period
        transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type.in_([
                CreditTransactionType.TRANSFER_IN, 
                CreditTransactionType.TRANSFER_OUT
            ]),
            CreditTransaction.status == CreditStatus.COMPLETED,
            CreditTransaction.created_at >= start_date,
            CreditTransaction.created_at <= end_date
        )
        
        if organization_id:
            transactions = transactions.filter(CreditTransaction.organization_id == organization_id)
        
        transactions = transactions.all()
        
        # Calculate statistics
        outgoing_transactions = [t for t in transactions if t.transaction_type == CreditTransactionType.TRANSFER_OUT]
        incoming_transactions = [t for t in transactions if t.transaction_type == CreditTransactionType.TRANSFER_IN]
        
        total_allocated_out = sum(-t.credit_amount for t in outgoing_transactions if t.credit_amount < 0)
        total_allocated_in = sum(t.credit_amount for t in incoming_transactions if t.credit_amount > 0)
        net_allocation = total_allocated_in - total_allocated_out
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "outgoing_allocations": {
                "count": len(outgoing_transactions),
                "total_credits": total_allocated_out,
                "average_per_allocation": total_allocated_out / len(outgoing_transactions) if outgoing_transactions else 0
            },
            "incoming_allocations": {
                "count": len(incoming_transactions),
                "total_credits": total_allocated_in,
                "average_per_allocation": total_allocated_in / len(incoming_transactions) if incoming_transactions else 0
            },
            "net_allocation": net_allocation,
            "net_allocation_per_day": net_allocation / days if days > 0 else 0
        }
    
    def setup_recurring_allocation(self, from_user_id: int, to_user_id: int,
                                 credit_amount: float, frequency: str = "monthly",
                                 description: str = "Recurring allocation",
                                 organization_id: Optional[int] = None,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Setup recurring credit allocation
        """
        try:
            if start_date is None:
                start_date = datetime.utcnow()
            
            # Create allocation schedule entry (would need separate table in real implementation)
            schedule_id = f"schedule_{from_user_id}_{to_user_id}_{datetime.utcnow().timestamp()}"
            
            # For now, just log the schedule
            logger.info(f"Setup recurring allocation: {schedule_id}")
            
            # Execute first allocation immediately
            first_allocation = self.allocate_credits_to_user(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                credit_amount=credit_amount,
                description=f"Initial recurring allocation: {description}",
                organization_id=organization_id
            )
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "credit_amount": credit_amount,
                "frequency": frequency,
                "description": description,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat() if end_date else None,
                "first_allocation": first_allocation,
                "setup_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error setting up recurring allocation: {e}")
            return {"success": False, "error": str(e)}


# Utility functions
def get_credit_allocation_service(db: Session = None) -> CreditAllocationService:
    """
    Get CreditAllocationService instance
    """
    if db is None:
        db = next(get_db())
    return CreditAllocationService(db)


def allocate_credits(from_user_id: int, to_user_id: int, credit_amount: float, 
                   description: str = "Credit allocation", db: Session = None) -> Dict[str, Any]:
    """
    Quick function to allocate credits between users
    """
    service = get_credit_allocation_service(db)
    return service.allocate_credits_to_user(from_user_id, to_user_id, credit_amount, description)