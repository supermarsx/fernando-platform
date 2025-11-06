"""
Credit Manager Service

Core service for credit management, including balance tracking,
transactions, and credit operations.
"""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.credits import (
    CreditBalance, CreditTransaction, CreditTransactionType, CreditStatus,
    LLMUsageRecord, CreditPolicy
)
from app.models.user import User
from app.db.session import get_db


logger = logging.getLogger(__name__)


class CreditManager:
    """
    Core credit management service
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_balance(self, user_id: int, organization_id: Optional[int] = None) -> CreditBalance:
        """
        Get existing credit balance or create new one
        """
        # Try to get existing balance
        query = self.db.query(CreditBalance).filter(
            CreditBalance.user_id == user_id
        )
        
        if organization_id:
            query = query.filter(CreditBalance.organization_id == organization_id)
        else:
            query = query.filter(CreditBalance.organization_id.is_(None))
        
        balance = query.first()
        
        if not balance:
            balance = CreditBalance(
                user_id=user_id,
                organization_id=organization_id,
                total_credits=0.0,
                available_credits=0.0,
                reserved_credits=0.0,
                pending_credits=0.0
            )
            self.db.add(balance)
            self.db.commit()
            self.db.refresh(balance)
            logger.info(f"Created new credit balance for user {user_id}")
        
        return balance
    
    def get_balance(self, user_id: int, organization_id: Optional[int] = None) -> Optional[CreditBalance]:
        """
        Get current credit balance
        """
        query = self.db.query(CreditBalance).filter(
            CreditBalance.user_id == user_id,
            CreditBalance.is_active == True
        )
        
        if organization_id:
            query = query.filter(CreditBalance.organization_id == organization_id)
        else:
            query = query.filter(CreditBalance.organization_id.is_(None))
        
        return query.first()
    
    def check_sufficient_credits(self, user_id: int, required_credits: float,
                               organization_id: Optional[int] = None) -> bool:
        """
        Check if user has sufficient credits
        """
        balance = self.get_balance(user_id, organization_id)
        if not balance:
            return False
        
        return balance.available_credits >= required_credits
    
    def reserve_credits(self, user_id: int, credit_amount: float,
                       organization_id: Optional[int] = None) -> bool:
        """
        Reserve credits for a pending operation
        """
        try:
            balance = self.get_or_create_balance(user_id, organization_id)
            
            if balance.available_credits < credit_amount:
                logger.warning(f"Insufficient credits for user {user_id}: need {credit_amount}, have {balance.available_credits}")
                return False
            
            # Reserve credits
            balance.available_credits -= credit_amount
            balance.reserved_credits += credit_amount
            balance.last_activity_at = datetime.utcnow()
            
            # Log transaction
            transaction = CreditTransaction(
                balance_id=balance.id,
                user_id=user_id,
                organization_id=organization_id,
                transaction_id=f"reserve_{user_id}_{datetime.utcnow().timestamp()}",
                transaction_type=CreditTransactionType.USAGE,
                status=CreditStatus.PENDING,
                credit_amount=-credit_amount,
                balance_before=balance.available_credits + balance.reserved_credits + credit_amount,
                balance_after=balance.available_credits,
                description=f"Reserved {credit_amount} credits for pending operation"
            )
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"Reserved {credit_amount} credits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reserving credits for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def deduct_credits(self, user_id: int, credit_amount: float, 
                      transaction_type: CreditTransactionType = CreditTransactionType.USAGE,
                      description: str = "Credit usage",
                      reference_type: Optional[str] = None,
                      reference_id: Optional[str] = None,
                      organization_id: Optional[int] = None) -> bool:
        """
        Deduct credits from user balance
        """
        try:
            balance = self.get_or_create_balance(user_id, organization_id)
            
            if balance.available_credits < credit_amount:
                logger.error(f"Insufficient credits for deduction: need {credit_amount}, have {balance.available_credits}")
                return False
            
            # Update balance
            balance.available_credits -= credit_amount
            balance.total_credits_used += credit_amount
            balance.credits_used_today += credit_amount
            
            # Update monthly/yearly usage
            now = datetime.utcnow()
            if balance.last_activity_at and balance.last_activity_at.month != now.month:
                balance.credits_used_this_month = credit_amount
            else:
                balance.credits_used_this_month += credit_amount
            
            if balance.last_activity_at and balance.last_activity_at.year != now.year:
                balance.credits_used_this_year = credit_amount
            else:
                balance.credits_used_this_year += credit_amount
            
            balance.last_activity_at = now
            
            # Create transaction
            transaction = CreditTransaction(
                balance_id=balance.id,
                user_id=user_id,
                organization_id=organization_id,
                transaction_id=f"deduct_{user_id}_{now.timestamp()}",
                transaction_type=transaction_type,
                status=CreditStatus.COMPLETED,
                credit_amount=-credit_amount,
                balance_before=balance.available_credits + credit_amount,
                balance_after=balance.available_credits,
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
                completed_at=now
            )
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"Deducted {credit_amount} credits from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deducting credits for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def add_credits(self, user_id: int, credit_amount: float,
                   transaction_type: CreditTransactionType = CreditTransactionType.BONUS,
                   description: str = "Credit addition",
                   expires_at: Optional[datetime] = None,
                   organization_id: Optional[int] = None) -> bool:
        """
        Add credits to user balance
        """
        try:
            balance = self.get_or_create_balance(user_id, organization_id)
            
            # Update balance
            balance.total_credits += credit_amount
            balance.available_credits += credit_amount
            balance.total_credits_earned += credit_amount
            balance.last_activity_at = datetime.utcnow()
            
            # Create transaction
            transaction = CreditTransaction(
                balance_id=balance.id,
                user_id=user_id,
                organization_id=organization_id,
                transaction_id=f"add_{user_id}_{datetime.utcnow().timestamp()}",
                transaction_type=transaction_type,
                status=CreditStatus.COMPLETED,
                credit_amount=credit_amount,
                balance_before=balance.available_credits - credit_amount,
                balance_after=balance.available_credits,
                description=description,
                expires_at=expires_at,
                completed_at=datetime.utcnow()
            )
            
            self.db.add(transaction)
            self.db.commit()
            
            logger.info(f"Added {credit_amount} credits to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding credits for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def release_reserved_credits(self, user_id: int, credit_amount: float,
                               organization_id: Optional[int] = None) -> bool:
        """
        Release reserved credits back to available balance
        """
        try:
            balance = self.get_or_create_balance(user_id, organization_id)
            
            if balance.reserved_credits < credit_amount:
                logger.error(f"Cannot release more credits than reserved: need {credit_amount}, reserved {balance.reserved_credits}")
                return False
            
            # Release credits
            balance.reserved_credits -= credit_amount
            balance.available_credits += credit_amount
            balance.last_activity_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Released {credit_amount} credits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing credits for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def get_transaction_history(self, user_id: int, limit: int = 100,
                               transaction_type: Optional[CreditTransactionType] = None,
                               organization_id: Optional[int] = None) -> List[CreditTransaction]:
        """
        Get transaction history for user
        """
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id
        )
        
        if organization_id:
            query = query.filter(CreditTransaction.organization_id == organization_id)
        
        if transaction_type:
            query = query.filter(CreditTransaction.transaction_type == transaction_type)
        
        return query.order_by(desc(CreditTransaction.created_at)).limit(limit).all()
    
    def get_usage_statistics(self, user_id: int, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed usage statistics for user
        """
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Base query for usage transactions
        query = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.transaction_type == CreditTransactionType.USAGE,
            CreditTransaction.created_at >= start_date,
            CreditTransaction.created_at <= end_date
        )
        
        if organization_id:
            query = query.filter(CreditTransaction.organization_id == organization_id)
        
        transactions = query.all()
        
        total_used = sum(abs(t.credit_amount) for t in transactions)
        transaction_count = len(transactions)
        
        # Calculate daily averages
        days = (end_date - start_date).days + 1
        avg_daily = total_used / days if days > 0 else 0
        
        return {
            "total_credits_used": total_used,
            "transaction_count": transaction_count,
            "average_daily_usage": avg_daily,
            "period_start": start_date,
            "period_end": end_date,
            "days_in_period": days
        }
    
    def apply_expiration_policy(self, user_id: int) -> List[CreditTransaction]:
        """
        Apply credit expiration policies to user's credits
        """
        # Get expired credit transactions
        expired_transactions = self.db.query(CreditTransaction).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.expires_at <= datetime.utcnow(),
            CreditTransaction.expires_at.isnot(None),
            CreditTransaction.status == CreditStatus.COMPLETED,
            CreditTransaction.is_expired == False
        ).all()
        
        expired_list = []
        
        for transaction in expired_transactions:
            if transaction.credit_amount > 0:  # Only expire positive credit amounts
                try:
                    balance = self.db.query(CreditBalance).filter(
                        CreditBalance.id == transaction.balance_id
                    ).first()
                    
                    if balance and balance.available_credits >= transaction.credit_amount:
                        # Deduct expired credits
                        balance.available_credits -= transaction.credit_amount
                        balance.total_credits -= transaction.credit_amount
                        balance.expired_credits_this_month += transaction.credit_amount
                        
                        # Mark transaction as expired
                        transaction.is_expired = True
                        transaction.expired_at = datetime.utcnow()
                        transaction.status = CreditStatus.FAILED
                        
                        expired_list.append(transaction)
                        
                        logger.info(f"Expired {transaction.credit_amount} credits for user {user_id}")
                
                except Exception as e:
                    logger.error(f"Error expiring credits for user {user_id}: {e}")
        
        self.db.commit()
        return expired_list
    
    def get_credit_summary(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive credit summary for user
        """
        balance = self.get_balance(user_id, organization_id)
        if not balance:
            return {
                "has_balance": False,
                "total_credits": 0,
                "available_credits": 0,
                "reserved_credits": 0,
                "pending_credits": 0
            }
        
        # Get recent transactions
        recent_transactions = self.get_transaction_history(user_id, limit=10, organization_id=organization_id)
        
        # Get usage stats
        usage_stats = self.get_usage_statistics(user_id, organization_id=organization_id)
        
        return {
            "has_balance": True,
            "total_credits": balance.total_credits,
            "available_credits": balance.available_credits,
            "reserved_credits": balance.reserved_credits,
            "pending_credits": balance.pending_credits,
            "credits_used_today": balance.credits_used_today,
            "credits_used_this_month": balance.credits_used_this_month,
            "credits_used_this_year": balance.credits_used_this_year,
            "total_credits_earned": balance.total_credits_earned,
            "total_credits_used": balance.total_credits_used,
            "next_expiration_date": balance.next_expiration_date,
            "is_suspended": balance.is_suspended,
            "recent_transactions": len(recent_transactions),
            "usage_statistics": usage_stats,
            "last_activity_at": balance.last_activity_at
        }


# Utility functions for easy integration
def get_credit_manager(db: Session = None) -> CreditManager:
    """
    Get a CreditManager instance
    """
    if db is None:
        db = next(get_db())
    return CreditManager(db)


def check_user_credits(user_id: int, required_credits: float, db: Session = None) -> bool:
    """
    Quick function to check if user has sufficient credits
    """
    manager = get_credit_manager(db)
    return manager.check_sufficient_credits(user_id, required_credits)


def deduct_user_credits(user_id: int, credit_amount: float, description: str = "Credit usage", 
                       db: Session = None) -> bool:
    """
    Quick function to deduct credits from user
    """
    manager = get_credit_manager(db)
    return manager.deduct_credits(user_id, credit_amount, description=description)


def add_user_credits(user_id: int, credit_amount: float, description: str = "Credit addition",
                    db: Session = None) -> bool:
    """
    Quick function to add credits to user
    """
    manager = get_credit_manager(db)
    return manager.add_credits(user_id, credit_amount, description=description)