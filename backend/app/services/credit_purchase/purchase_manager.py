"""
Credit Purchase Manager

Service for handling credit package purchases and allocation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.credits import (
    CreditPackage, CreditPurchaseTransaction, CreditBalance, 
    CreditTransaction, CreditTransactionType, CreditStatus
)
from app.models.billing import PaymentMethodModel, PaymentStatus, PaymentMethod
from app.services.credits.credit_manager import CreditManager
from app.services.credits.credit_policies import CreditPoliciesService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CreditPurchaseManager:
    """
    Service for managing credit package purchases
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_manager = CreditManager(db)
        self.policy_service = CreditPoliciesService(db)
    
    def get_available_packages(self, user_tier: str = "all", 
                             organization_only: bool = False,
                             region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available credit packages for purchase
        """
        query = self.db.query(CreditPackage).filter(
            CreditPackage.status == "active"
        )
        
        # Filter by user tier if specified
        if user_tier != "all":
            query = query.filter(
                or_(
                    CreditPackage.target_user_tier == user_tier,
                    CreditPackage.target_user_tier.is_(None)
                )
            )
        
        # Filter by organization restriction
        if organization_only:
            query = query.filter(CreditPackage.organization_only == True)
        
        # Filter by region if specified
        if region:
            # This would need to be implemented with region restrictions
            pass
        
        packages = query.order_by(CreditPackage.price_usd.asc()).all()
        
        result = []
        for package in packages:
            # Calculate discount
            discount_amount = package.credits_amount * (package.discount_percentage / 100) if package.discount_percentage > 0 else 0
            effective_credits = package.credits_amount + package.credits_amount * (package.discount_percentage / 100)
            
            result.append({
                "id": package.id,
                "name": package.name,
                "description": package.description,
                "base_credits": package.credits_amount,
                "bonus_credits": discount_amount,
                "total_credits": effective_credits,
                "price_usd": package.price_usd,
                "price_eur": package.price_eur,
                "price_gbp": package.price_gbp,
                "currency": package.currency,
                "discount_percentage": package.discount_percentage,
                "validity_days": package.validity_days,
                "is_bulk_discount": package.is_bulk_discount,
                "features": {
                    "priority_support": package.includes_priority_support,
                    "advanced_analytics": package.includes_advanced_analytics,
                    "api_access": package.includes_api_access
                },
                "target_tier": package.target_user_tier,
                "organization_only": package.organization_only,
                "is_featured": package.is_featured,
                "is_limited_time": package.is_limited_time,
                "limited_time_end": package.limited_time_end.isoformat() if package.limited_time_end else None,
                "max_daily_usage": package.max_daily_usage,
                "max_monthly_usage": package.max_monthly_usage,
                "cost_per_credit": package.price_usd / effective_credits if effective_credits > 0 else 0,
                "savings_amount": package.price_usd * (package.discount_percentage / 100) if package.discount_percentage > 0 else 0
            })
        
        return result
    
    def initiate_purchase(self, user_id: int, package_id: int, quantity: int = 1,
                         payment_method_id: Optional[int] = None,
                         organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Initiate a credit purchase
        """
        try:
            # Get package
            package = self.db.query(CreditPackage).filter(
                CreditPackage.id == package_id,
                CreditPackage.status == "active"
            ).first()
            
            if not package:
                return {"success": False, "error": "Package not found or inactive"}
            
            # Validate quantity
            if quantity < 1 or quantity > 100:  # Reasonable limits
                return {"success": False, "error": "Invalid quantity"}
            
            # Calculate pricing
            subtotal = package.price_usd * quantity
            discount_amount = subtotal * (package.discount_percentage / 100) if package.discount_percentage > 0 else 0
            total_before_tax = subtotal - discount_amount
            
            # Calculate tax (would integrate with tax service in real implementation)
            tax_rate = 0.0  # Default no tax
            tax_amount = total_before_tax * tax_rate
            total_amount = total_before_tax + tax_amount
            
            # Calculate credits
            bonus_per_package = package.credits_amount * (package.discount_percentage / 100)
            total_credits = (package.credits_amount + bonus_per_package) * quantity
            
            # Create purchase transaction
            purchase_id = f"purchase_{user_id}_{package_id}_{datetime.utcnow().timestamp()}"
            expires_at = datetime.utcnow() + timedelta(days=package.validity_days)
            
            purchase = CreditPurchaseTransaction(
                user_id=user_id,
                package_id=package_id,
                organization_id=organization_id,
                purchase_id=purchase_id,
                quantity=quantity,
                total_credits=total_credits,
                bonus_credits=bonus_per_package * quantity,
                unit_price=package.price_usd,
                subtotal=subtotal,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                currency=package.currency,
                expires_at=expires_at,
                status="pending",
                payment_status="pending"
            )
            
            self.db.add(purchase)
            self.db.commit()
            self.db.refresh(purchase)
            
            # Get or create balance
            balance = self.credit_manager.get_or_create_balance(user_id, organization_id)
            purchase.balance_id = balance.id
            self.db.commit()
            
            logger.info(f"Initiated purchase {purchase_id} for user {user_id}")
            
            return {
                "success": True,
                "purchase_id": purchase_id,
                "purchase_transaction_id": purchase.id,
                "package_details": {
                    "name": package.name,
                    "base_credits": package.credits_amount,
                    "bonus_credits": bonus_per_package * quantity,
                    "total_credits": total_credits
                },
                "pricing": {
                    "subtotal": subtotal,
                    "discount_amount": discount_amount,
                    "tax_amount": tax_amount,
                    "total_amount": total_amount,
                    "currency": package.currency,
                    "cost_per_credit": total_amount / total_credits if total_credits > 0 else 0
                },
                "validity": {
                    "expires_at": expires_at.isoformat(),
                    "validity_days": package.validity_days
                },
                "payment_required": total_amount > 0
            }
            
        except Exception as e:
            logger.error(f"Error initiating purchase: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def process_payment(self, purchase_id: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process payment for a purchase
        """
        try:
            # Get purchase transaction
            purchase = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.purchase_id == purchase_id
            ).first()
            
            if not purchase:
                return {"success": False, "error": "Purchase not found"}
            
            if purchase.status != "pending":
                return {"success": False, "error": "Purchase is not pending"}
            
            # In a real implementation, this would integrate with payment processors
            # For now, we'll simulate payment processing
            
            payment_successful = payment_data.get("payment_successful", False)
            
            if payment_successful:
                # Update purchase status
                purchase.status = "completed"
                purchase.payment_status = "succeeded"
                purchase.activated_at = datetime.utcnow()
                
                # Add credits to user's balance
                credits_added = self.credit_manager.add_credits(
                    user_id=purchase.user_id,
                    credit_amount=purchase.total_credits,
                    transaction_type=CreditTransactionType.PURCHASE,
                    description=f"Credit purchase: {purchase.package.name}",
                    expires_at=purchase.expires_at,
                    organization_id=purchase.organization_id
                )
                
                if credits_added:
                    logger.info(f"Purchase {purchase_id} completed successfully")
                    
                    # Schedule expiration notifications
                    self._schedule_expiration_notifications(purchase)
                    
                    return {
                        "success": True,
                        "credits_added": purchase.total_credits,
                        "expires_at": purchase.expires_at.isoformat(),
                        "message": "Purchase completed successfully"
                    }
                else:
                    purchase.status = "failed"
                    purchase.payment_status = "failed"
                    self.db.commit()
                    return {"success": False, "error": "Failed to add credits"}
            else:
                # Payment failed
                purchase.status = "failed"
                purchase.payment_status = "failed"
                purchase.refunded_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "success": False, 
                    "error": "Payment failed",
                    "failure_reason": payment_data.get("failure_reason", "Payment was declined")
                }
            
        except Exception as e:
            logger.error(f"Error processing payment for {purchase_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def get_purchase_history(self, user_id: int, limit: int = 50,
                           organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get purchase history for user
        """
        query = self.db.query(CreditPurchaseTransaction).filter(
            CreditPurchaseTransaction.user_id == user_id
        )
        
        if organization_id:
            query = query.filter(CreditPurchaseTransaction.organization_id == organization_id)
        
        purchases = query.order_by(CreditPurchaseTransaction.created_at.desc()).limit(limit).all()
        
        result = []
        for purchase in purchases:
            result.append({
                "purchase_id": purchase.purchase_id,
                "package_name": purchase.package.name if purchase.package else "Unknown",
                "quantity": purchase.quantity,
                "total_credits": purchase.total_credits,
                "bonus_credits": purchase.bonus_credits,
                "amount_paid": purchase.total_amount,
                "currency": purchase.currency,
                "status": purchase.status,
                "payment_status": purchase.payment_status,
                "activated_at": purchase.activated_at.isoformat() if purchase.activated_at else None,
                "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
                "created_at": purchase.created_at.isoformat(),
                "refunded_at": purchase.refunded_at.isoformat() if purchase.refunded_at else None
            })
        
        return result
    
    def get_purchase_details(self, purchase_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific purchase
        """
        purchase = self.db.query(CreditPurchaseTransaction).filter(
            CreditPurchaseTransaction.purchase_id == purchase_id
        ).first()
        
        if not purchase:
            return None
        
        return {
            "purchase_id": purchase.purchase_id,
            "user_id": purchase.user_id,
            "organization_id": purchase.organization_id,
            "package": {
                "id": purchase.package.id,
                "name": purchase.package.name,
                "description": purchase.package.description,
                "base_credits": purchase.package.credits_amount,
                "validity_days": purchase.package.validity_days
            },
            "purchase_details": {
                "quantity": purchase.quantity,
                "total_credits": purchase.total_credits,
                "bonus_credits": purchase.bonus_credits,
                "unit_price": purchase.unit_price,
                "subtotal": purchase.subtotal,
                "discount_amount": purchase.discount_amount,
                "tax_amount": purchase.tax_amount,
                "total_amount": purchase.total_amount,
                "currency": purchase.currency
            },
            "status": {
                "purchase_status": purchase.status,
                "payment_status": purchase.payment_status,
                "activated_at": purchase.activated_at.isoformat() if purchase.activated_at else None,
                "refunded_at": purchase.refunded_at.isoformat() if purchase.refunded_at else None
            },
            "validity": {
                "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
                "is_expired": purchase.expires_at < datetime.utcnow() if purchase.expires_at else False
            },
            "timestamps": {
                "created_at": purchase.created_at.isoformat(),
                "updated_at": purchase.updated_at.isoformat() if purchase.updated_at else None
            }
        }
    
    def refund_purchase(self, purchase_id: str, reason: str = "Customer request") -> Dict[str, Any]:
        """
        Process a refund for a purchase
        """
        try:
            # Get purchase
            purchase = self.db.query(CreditPurchaseTransaction).filter(
                CreditPurchaseTransaction.purchase_id == purchase_id
            ).first()
            
            if not purchase:
                return {"success": False, "error": "Purchase not found"}
            
            if purchase.status != "completed":
                return {"success": False, "error": "Cannot refund uncompleted purchase"}
            
            # Check if already refunded
            if purchase.refunded_at:
                return {"success": False, "error": "Purchase already refunded"}
            
            # Calculate refund amount (full refund for simplicity)
            refund_amount = purchase.total_amount
            
            # Deduct credits from balance
            credits_deducted = self.credit_manager.deduct_credits(
                user_id=purchase.user_id,
                credit_amount=purchase.total_credits,
                transaction_type=CreditTransactionType.REFUND,
                description=f"Refund: {purchase.package.name} - {reason}",
                reference_type="refund",
                reference_id=purchase_id,
                organization_id=purchase.organization_id
            )
            
            if credits_deducted:
                # Update purchase status
                purchase.status = "refunded"
                purchase.refunded_at = datetime.utcnow()
                
                # Create refund transaction record
                refund_transaction = CreditTransaction(
                    balance_id=purchase.balance_id,
                    user_id=purchase.user_id,
                    organization_id=purchase.organization_id,
                    transaction_id=f"refund_{purchase_id}_{datetime.utcnow().timestamp()}",
                    transaction_type=CreditTransactionType.REFUND,
                    status=CreditStatus.COMPLETED,
                    credit_amount=-purchase.total_credits,
                    balance_before=0,  # Will be updated by credit_manager
                    balance_after=0,   # Will be updated by credit_manager
                    description=f"Refund: {purchase.package.name} - {reason}",
                    reference_type="refund",
                    reference_id=purchase_id,
                    completed_at=datetime.utcnow()
                )
                
                self.db.add(refund_transaction)
                self.db.commit()
                
                logger.info(f"Processed refund for purchase {purchase_id}")
                
                return {
                    "success": True,
                    "refund_amount": refund_amount,
                    "credits_refunded": purchase.total_credits,
                    "refunded_at": purchase.refunded_at.isoformat()
                }
            else:
                return {"success": False, "error": "Failed to deduct credits for refund"}
            
        except Exception as e:
            logger.error(f"Error processing refund for {purchase_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _schedule_expiration_notifications(self, purchase: CreditPurchaseTransaction):
        """
        Schedule expiration notifications for purchased credits
        """
        # This would integrate with the notification service
        # For now, just log that notifications should be scheduled
        logger.info(f"Should schedule expiration notifications for purchase {purchase.purchase_id}")
    
    def get_package_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics on package purchases
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get purchase data
        purchases = self.db.query(CreditPurchaseTransaction).filter(
            CreditPurchaseTransaction.created_at >= start_date,
            CreditPurchaseTransaction.created_at <= end_date,
            CreditPurchaseTransaction.status == "completed"
        ).all()
        
        if not purchases:
            return {
                "period_days": days,
                "total_purchases": 0,
                "total_revenue": 0,
                "total_credits_sold": 0,
                "package_performance": []
            }
        
        # Calculate analytics
        total_purchases = len(purchases)
        total_revenue = sum(p.total_amount for p in purchases)
        total_credits_sold = sum(p.total_credits for p in purchases)
        
        # Package performance
        package_performance = {}
        for purchase in purchases:
            package_name = purchase.package.name if purchase.package else "Unknown"
            if package_name not in package_performance:
                package_performance[package_name] = {
                    "purchase_count": 0,
                    "total_revenue": 0,
                    "total_credits": 0,
                    "total_quantity": 0
                }
            
            package_performance[package_name]["purchase_count"] += 1
            package_performance[package_name]["total_revenue"] += purchase.total_amount
            package_performance[package_name]["total_credits"] += purchase.total_credits
            package_performance[package_name]["total_quantity"] += purchase.quantity
        
        # Convert to list and sort by revenue
        package_list = [
            {
                "package_name": name,
                **data,
                "avg_purchase_value": data["total_revenue"] / data["purchase_count"],
                "avg_credits_per_purchase": data["total_credits"] / data["purchase_count"]
            }
            for name, data in package_performance.items()
        ]
        
        package_list.sort(key=lambda x: x["total_revenue"], reverse=True)
        
        return {
            "period_days": days,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "total_credits_sold": total_credits_sold,
            "average_purchase_value": total_revenue / total_purchases if total_purchases > 0 else 0,
            "average_credits_per_purchase": total_credits_sold / total_purchases if total_purchases > 0 else 0,
            "package_performance": package_list
        }
    
    def initialize_default_packages(self):
        """
        Initialize default credit packages
        """
        # Check if packages already exist
        existing_packages = self.db.query(CreditPackage).count()
        if existing_packages > 0:
            return
        
        packages = [
            {
                "name": "Starter Package",
                "description": "Perfect for getting started with LLM usage",
                "credits_amount": 10000,
                "price_usd": 50.00,
                "validity_days": 365,
                "target_user_tier": "starter",
                "is_featured": True,
                "includes_priority_support": False,
                "includes_advanced_analytics": False,
                "includes_api_access": True
            },
            {
                "name": "Professional Package",
                "description": "Ideal for professionals and small teams",
                "credits_amount": 100000,
                "price_usd": 400.00,
                "validity_days": 365,
                "target_user_tier": "professional",
                "discount_percentage": 20,  # 20% bulk discount
                "is_featured": True,
                "includes_priority_support": True,
                "includes_advanced_analytics": True,
                "includes_api_access": True
            },
            {
                "name": "Enterprise Package",
                "description": "For large-scale operations and enterprises",
                "credits_amount": 1000000,
                "price_usd": 3000.00,
                "validity_days": 365,
                "target_user_tier": "enterprise",
                "is_bulk_discount": True,
                "includes_priority_support": True,
                "includes_advanced_analytics": True,
                "includes_api_access": True
            },
            {
                "name": "Custom Enterprise",
                "description": "Custom credit packages for enterprise clients",
                "credits_amount": 5000000,
                "price_usd": 12000.00,
                "validity_days": 365,
                "target_user_tier": "enterprise",
                "organization_only": True,
                "includes_priority_support": True,
                "includes_advanced_analytics": True,
                "includes_api_access": True
            }
        ]
        
        for package_data in packages:
            package = CreditPackage(**package_data)
            self.db.add(package)
        
        self.db.commit()
        logger.info("Initialized default credit packages")


# Utility functions
def get_credit_purchase_manager(db: Session = None) -> CreditPurchaseManager:
    """
    Get CreditPurchaseManager instance
    """
    if db is None:
        db = next(get_db())
    return CreditPurchaseManager(db)


def get_available_packages(user_tier: str = "all", db: Session = None) -> List[Dict[str, Any]]:
    """
    Quick function to get available packages
    """
    manager = get_credit_purchase_manager(db)
    return manager.get_available_packages(user_tier)