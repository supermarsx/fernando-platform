"""
Credit Policies Service

Service for managing credit expiration, rollover, and transfer policies.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.credits import (
    CreditPolicy, CreditTransaction, CreditTransactionType, CreditStatus,
    CreditBalance, CreditExpirationSchedule
)
from app.services.credits.credit_manager import CreditManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CreditPoliciesService:
    """
    Service for managing credit policies including expiration, rollover, and transfers
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
    
    def get_applicable_policies(self, policy_type: str, user_id: int, 
                              organization_id: Optional[int] = None) -> List[CreditPolicy]:
        """
        Get all policies applicable to a user for a specific policy type
        """
        # Get base policies
        query = self.db.query(CreditPolicy).filter(
            CreditPolicy.policy_type == policy_type,
            CreditPolicy.is_active == True,
            CreditPolicy.effective_from <= datetime.utcnow()
        )
        
        # Add expiration date filter
        query = query.filter(
            or_(
                CreditPolicy.effective_until.is_(None),
                CreditPolicy.effective_until >= datetime.utcnow()
            )
        )
        
        policies = query.all()
        
        # Filter based on user/organization targeting
        applicable_policies = []
        for policy in policies:
            if self._policy_applies_to_user(policy, user_id, organization_id):
                applicable_policies.append(policy)
        
        # Sort by priority (lower number = higher priority)
        applicable_policies.sort(key=lambda p: p.priority)
        
        return applicable_policies
    
    def _policy_applies_to_user(self, policy: CreditPolicy, user_id: int, 
                              organization_id: Optional[int] = None) -> bool:
        """
        Check if a policy applies to a specific user
        """
        config = policy.config or {}
        
        # Check user tier restrictions
        user_tier = config.get("applies_to_user_tier", "all")
        if user_tier != "all":
            # This would need to be implemented with actual user tier data
            # For now, we'll assume all users have access
            pass
        
        # Check organization type restrictions
        org_type = config.get("applies_to_organization_type", "all")
        if org_type != "all":
            # This would need to be implemented with actual organization data
            pass
        
        # Check organization-only restriction
        if policy.organization_only and not organization_id:
            return False
        
        return True
    
    def process_credit_expirations(self, user_id: Optional[int] = None, 
                                 organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Process all credit expirations for specified users
        """
        try:
            # Get expiring transactions
            query = self.db.query(CreditTransaction).filter(
                CreditTransaction.expires_at <= datetime.utcnow(),
                CreditTransaction.expires_at.isnot(None),
                CreditTransaction.status == CreditStatus.COMPLETED,
                CreditTransaction.is_expired == False,
                CreditTransaction.credit_amount > 0
            )
            
            if user_id:
                query = query.filter(CreditTransaction.user_id == user_id)
            
            if organization_id:
                query = query.filter(CreditTransaction.organization_id == organization_id)
            
            expiring_transactions = query.all()
            
            processed_count = 0
            total_expired_credits = 0
            failed_expirations = []
            
            for transaction in expiring_transactions:
                try:
                    # Get applicable expiration policies
                    expiration_policies = self.get_applicable_policies(
                        "expiration", transaction.user_id, transaction.organization_id
                    )
                    
                    # Apply policies to determine if credits should expire
                    should_expire, reason = self._should_expire_credits(transaction, expiration_policies)
                    
                    if should_expire:
                        # Expire the credits
                        if self._expire_credits(transaction):
                            processed_count += 1
                            total_expired_credits += transaction.credit_amount
                            
                            # Create expiration schedule record for tracking
                            schedule = CreditExpirationSchedule(
                                balance_id=transaction.balance_id,
                                transaction_id=transaction.id,
                                user_id=transaction.user_id,
                                credit_amount=transaction.credit_amount,
                                expires_at=transaction.expires_at,
                                is_expired=True,
                                expired_at=datetime.utcnow(),
                                processing_status="completed"
                            )
                            self.db.add(schedule)
                        else:
                            failed_expirations.append({
                                "transaction_id": transaction.id,
                                "user_id": transaction.user_id,
                                "reason": "Failed to deduct credits"
                            })
                    else:
                        # Credits should not expire - extend them
                        self._extend_credits(transaction, reason)
                
                except Exception as e:
                    failed_expirations.append({
                        "transaction_id": transaction.id,
                        "user_id": transaction.user_id,
                        "reason": str(e)
                    })
                    logger.error(f"Error processing expiration for transaction {transaction.id}: {e}")
            
            self.db.commit()
            
            return {
                "processed_count": processed_count,
                "total_expired_credits": total_expired_credits,
                "failed_expirations": failed_expirations,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error processing credit expirations: {e}")
            self.db.rollback()
            return {"error": str(e)}
    
    def _should_expire_credits(self, transaction: CreditTransaction, 
                             policies: List[CreditPolicy]) -> tuple[bool, str]:
        """
        Determine if credits should expire based on policies
        """
        if not policies:
            # No expiration policy - don't expire
            return False, "No expiration policy configured"
        
        # Apply highest priority policy
        policy = policies[0]
        config = policy.config or {}
        
        # Check for grace period extension
        grace_period_days = config.get("grace_period_days", 0)
        if grace_period_days > 0:
            expiry_date = transaction.expires_at
            grace_end = expiry_date + timedelta(days=grace_period_days)
            if datetime.utcnow() <= grace_end:
                return False, f"Grace period until {grace_end.isoformat()}"
        
        # Check for rollover to different user/organization
        if config.get("allow_rollover_to_organization") and transaction.organization_id:
            return False, "Credits rolled over to organization"
        
        # Check for rollover to different time period
        rollover_days = config.get("rollover_days", 0)
        if rollover_days > 0:
            return False, f"Credits rolled over for {rollover_days} days"
        
        # Default: expire credits
        return True, "Expiration policy applied"
    
    def _expire_credits(self, transaction: CreditTransaction) -> bool:
        """
        Actually expire the credits by deducting them from balance
        """
        try:
            # Get the balance
            balance = self.db.query(CreditBalance).filter(
                CreditBalance.id == transaction.balance_id
            ).first()
            
            if not balance:
                return False
            
            # Check if user has enough credits available (credits should be available if not used)
            if balance.available_credits < transaction.credit_amount:
                logger.warning(f"Insufficient credits to expire for transaction {transaction.id}")
                # Still mark as expired to prevent future issues
                transaction.is_expired = True
                transaction.expired_at = datetime.utcnow()
                return True
            
            # Deduct credits
            balance.available_credits -= transaction.credit_amount
            balance.total_credits -= transaction.credit_amount
            balance.expired_credits_this_month += transaction.credit_amount
            balance.last_activity_at = datetime.utcnow()
            
            # Mark transaction as expired
            transaction.is_expired = True
            transaction.expired_at = datetime.utcnow()
            
            # Create expiration transaction
            expiration_transaction = CreditTransaction(
                balance_id=balance.id,
                user_id=transaction.user_id,
                organization_id=transaction.organization_id,
                transaction_id=f"expire_{transaction.id}_{datetime.utcnow().timestamp()}",
                transaction_type=CreditTransactionType.EXPIRATION,
                status=CreditStatus.COMPLETED,
                credit_amount=-transaction.credit_amount,
                balance_before=balance.available_credits + transaction.credit_amount,
                balance_after=balance.available_credits,
                description=f"Credits expired: {transaction.description}",
                reference_type="expiration",
                reference_id=str(transaction.id),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(expiration_transaction)
            return True
            
        except Exception as e:
            logger.error(f"Error expiring credits for transaction {transaction.id}: {e}")
            return False
    
    def _extend_credits(self, transaction: CreditTransaction, reason: str):
        """
        Extend credits that shouldn't expire
        """
        try:
            # Extend expiration date
            transaction.expires_at = datetime.utcnow() + timedelta(days=30)  # Default 30-day extension
            transaction.description = f"{transaction.description} (Extended: {reason})"
            
            # Log the extension
            logger.info(f"Extended credits for transaction {transaction.id}: {reason}")
            
        except Exception as e:
            logger.error(f"Error extending credits for transaction {transaction.id}: {e}")
    
    def schedule_expiration_notifications(self, days_before: int = 7) -> Dict[str, Any]:
        """
        Schedule notifications for credits expiring in X days
        """
        notification_date = datetime.utcnow() + timedelta(days=days_before)
        
        # Get transactions expiring on the notification date
        expiring_transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.expires_at >= notification_date.replace(hour=0, minute=0, second=0),
            CreditTransaction.expires_at <= notification_date.replace(hour=23, minute=59, second=59),
            CreditTransaction.expires_at.isnot(None),
            CreditTransaction.status == CreditStatus.COMPLETED,
            CreditTransaction.is_expired == False
        ).all()
        
        notification_scheduled = 0
        for transaction in expiring_transactions:
            # Create expiration schedule entry
            schedule = CreditExpirationSchedule(
                balance_id=transaction.balance_id,
                transaction_id=transaction.id,
                user_id=transaction.user_id,
                credit_amount=transaction.credit_amount,
                expires_at=transaction.expires_at,
                processing_status="pending"
            )
            
            # Set notification flags based on days_before
            if days_before == 7:
                schedule.notification_7_days_sent = False  # Will be set to True when sent
            elif days_before == 3:
                schedule.notification_3_days_sent = False
            elif days_before == 1:
                schedule.notification_1_day_sent = False
            
            self.db.add(schedule)
            notification_scheduled += 1
        
        self.db.commit()
        
        return {
            "notifications_scheduled": notification_scheduled,
            "expiration_date": notification_date.date().isoformat(),
            "days_before_expiry": days_before
        }
    
    def apply_rollover_policies(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Apply rollover policies for credits approaching expiration
        """
        try:
            # Get applicable rollover policies
            rollover_policies = self.get_applicable_policies(
                "rollover", user_id, organization_id
            )
            
            if not rollover_policies:
                return {"message": "No rollover policies applicable"}
            
            # Get credits that are close to expiration and eligible for rollover
            cutoff_date = datetime.utcnow() + timedelta(days=7)  # Next 7 days
            expiring_credits = self.db.query(CreditTransaction).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.expires_at <= cutoff_date,
                CreditTransaction.expires_at >= datetime.utcnow(),
                CreditTransaction.expires_at.isnot(None),
                CreditTransaction.status == CreditStatus.COMPLETED,
                CreditTransaction.is_expired == False,
                CreditTransaction.credit_amount > 0
            )
            
            if organization_id:
                expiring_credits = expiring_credits.filter(
                    CreditTransaction.organization_id == organization_id
                )
            
            expiring_credits = expiring_credits.all()
            
            rolled_over_credits = 0
            total_credits_rolled = 0
            
            for transaction in expiring_credits:
                for policy in rollover_policies:
                    config = policy.config or {}
                    
                    # Check if rollover applies
                    rollover_percentage = config.get("rollover_percentage", 100)
                    max_rollover_credits = config.get("max_rollover_credits", float('inf'))
                    
                    # Calculate rollover amount
                    rollover_amount = min(
                        transaction.credit_amount * (rollover_percentage / 100),
                        max_rollover_credits
                    )
                    
                    if rollover_amount > 0:
                        # Extend expiration
                        extension_days = config.get("extension_days", 30)
                        transaction.expires_at += timedelta(days=extension_days)
                        
                        # Create rollover transaction
                        rollover_transaction = CreditTransaction(
                            balance_id=transaction.balance_id,
                            user_id=transaction.user_id,
                            organization_id=transaction.organization_id,
                            transaction_id=f"rollover_{transaction.id}_{datetime.utcnow().timestamp()}",
                            transaction_type=CreditTransactionType.ROLLOVER,
                            status=CreditStatus.COMPLETED,
                            credit_amount=rollover_amount,
                            balance_before=0,  # This is an extension, not a new balance change
                            balance_after=0,
                            description=f"Credits rolled over: {transaction.description}",
                            reference_type="rollover",
                            reference_id=str(transaction.id),
                            completed_at=datetime.utcnow()
                        )
                        
                        self.db.add(rollover_transaction)
                        rolled_over_credits += 1
                        total_credits_rolled += rollover_amount
                        
                        logger.info(f"Rolled over {rollover_amount} credits for user {user_id}")
                        break  # Only apply highest priority policy
            
            self.db.commit()
            
            return {
                "rolled_over_transactions": rolled_over_credits,
                "total_credits_rolled": total_credits_rolled,
                "policies_applied": len(rollover_policies)
            }
            
        except Exception as e:
            logger.error(f"Error applying rollover policies for user {user_id}: {e}")
            self.db.rollback()
            return {"error": str(e)}
    
    def create_policy(self, name: str, policy_type: str, config: Dict[str, Any],
                     applies_to_user_tier: str = "all",
                     applies_to_organization_type: str = "all",
                     organization_only: bool = False,
                     priority: int = 100) -> CreditPolicy:
        """
        Create a new credit policy
        """
        policy = CreditPolicy(
            name=name,
            description=config.get("description", ""),
            policy_type=policy_type,
            config=config,
            applies_to_user_tier=applies_to_user_tier,
            applies_to_organization_type=applies_to_organization_type,
            organization_only=organization_only,
            priority=priority,
            is_active=True,
            effective_from=datetime.utcnow()
        )
        
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Created policy: {name} (type: {policy_type})")
        return policy
    
    def get_expiration_summary(self, user_id: int, days_ahead: int = 30,
                             organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get summary of upcoming credit expirations
        """
        end_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        # Get expiring transactions
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.expires_at <= end_date,
            CreditTransaction.expires_at >= datetime.utcnow(),
            CreditTransaction.expires_at.isnot(None),
            CreditTransaction.status == CreditStatus.COMPLETED,
            CreditTransaction.is_expired == False,
            CreditTransaction.credit_amount > 0
        )
        
        if organization_id:
            query = query.filter(CreditTransaction.organization_id == organization_id)
        
        expiring_transactions = query.all()
        
        # Group by expiration date
        expiration_summary = {}
        for transaction in expiring_transactions:
            exp_date = transaction.expires_at.date().isoformat()
            if exp_date not in expiration_summary:
                expiration_summary[exp_date] = {
                    "date": exp_date,
                    "total_credits": 0,
                    "transaction_count": 0,
                    "transactions": []
                }
            
            expiration_summary[exp_date]["total_credits"] += transaction.credit_amount
            expiration_summary[exp_date]["transaction_count"] += 1
            expiration_summary[exp_date]["transactions"].append({
                "transaction_id": transaction.id,
                "description": transaction.description,
                "credit_amount": transaction.credit_amount,
                "expires_at": transaction.expires_at.isoformat()
            })
        
        # Sort by date
        sorted_summary = sorted(expiration_summary.values(), key=lambda x: x["date"])
        
        # Calculate totals
        total_expiring_credits = sum(day["total_credits"] for day in sorted_summary)
        
        return {
            "user_id": user_id,
            "organization_id": organization_id,
            "days_ahead": days_ahead,
            "total_expiring_credits": total_expiring_credits,
            "expiring_days_count": len(sorted_summary),
            "expiration_schedule": sorted_summary,
            "generated_at": datetime.utcnow()
        }
    
    def initialize_default_policies(self):
        """
        Initialize default credit policies
        """
        # Default expiration policy (1 year)
        if not self.db.query(CreditPolicy).filter(CreditPolicy.policy_type == "expiration").first():
            self.create_policy(
                name="Default Expiration Policy",
                policy_type="expiration",
                config={
                    "description": "Standard credit expiration after 1 year",
                    "expiration_days": 365,
                    "grace_period_days": 7,
                    "notification_days_before": [7, 3, 1]
                },
                priority=100
            )
        
        # Default rollover policy (for high-tier users)
        if not self.db.query(CreditPolicy).filter(CreditPolicy.policy_type == "rollover").first():
            self.create_policy(
                name="Professional Rollover Policy",
                policy_type="rollover",
                config={
                    "description": "Roll over unused credits for professional users",
                    "rollover_percentage": 75,
                    "max_rollover_credits": 10000,
                    "extension_days": 90
                },
                applies_to_user_tier="professional",
                priority=50
            )
        
        # Default transfer policy
        if not self.db.query(CreditPolicy).filter(CreditPolicy.policy_type == "transfer").first():
            self.create_policy(
                name="Standard Transfer Policy",
                policy_type="transfer",
                config={
                    "description": "Allow credit transfers between users",
                    "max_transfer_amount": 5000,
                    "require_approval": False,
                    "transfer_fee_percentage": 0
                },
                priority=100
            )
        
        logger.info("Initialized default credit policies")


# Utility functions
def get_credit_policies_service(db: Session = None) -> CreditPoliciesService:
    """
    Get CreditPoliciesService instance
    """
    if db is None:
        db = next(get_db())
    return CreditPoliciesService(db)


def process_expirations(user_id: int = None, db: Session = None) -> Dict[str, Any]:
    """
    Quick function to process credit expirations
    """
    service = get_credit_policies_service(db)
    return service.process_credit_expirations(user_id)