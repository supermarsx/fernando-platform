"""
Dunning Management Service

Handles failed payment recovery through:
- Automatic payment retry with exponential backoff
- Dunning email campaigns (reminders, warnings, final notice)
- Subscription pause/cancellation workflows
- Payment method update requests
- Grace period management

Helps recover revenue from failed payments and reduce involuntary churn.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.models.billing import (
    Payment, Invoice, Subscription, PaymentStatus,
    InvoiceStatus, SubscriptionStatus
)
from app.services.email_service import EmailService


class DunningManagementService:
    """Service for managing failed payment recovery"""
    
    def __init__(self, db: Session):
        self.db = db
        self.enabled = settings.DUNNING_ENABLED
        self.retry_attempts = settings.DUNNING_RETRY_ATTEMPTS
        self.retry_delays = [int(d) for d in settings.DUNNING_RETRY_DELAYS_DAYS.split(',')]
        self.email_enabled = settings.DUNNING_EMAIL_ENABLED
        self.email_service = EmailService() if self.email_enabled else None
    
    # ============================================================================
    # FAILED PAYMENT HANDLING
    # ============================================================================
    
    def handle_failed_payment(
        self,
        payment_id: int,
        invoice_id: int,
        user_id: int,
        failure_reason: str
    ) -> Dict[str, Any]:
        """
        Handle a failed payment and initiate dunning process
        
        Returns dunning plan and next actions
        """
        
        if not self.enabled:
            return {"dunning_enabled": False, "status": "skipped"}
        
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not payment or not invoice:
            return {"status": "error", "reason": "payment_or_invoice_not_found"}
        
        # Count previous retry attempts for this invoice
        retry_count = self.db.query(Payment).filter(
            Payment.invoice_id == invoice_id,
            Payment.status == PaymentStatus.FAILED
        ).count()
        
        # Determine if we should retry
        should_retry = retry_count < self.retry_attempts
        
        # Update invoice status
        invoice.status = InvoiceStatus.OVERDUE
        
        # Check if this is a subscription payment
        subscription = None
        if invoice.subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == invoice.subscription_id
            ).first()
            
            if subscription:
                # Mark subscription as past due
                subscription.status = SubscriptionStatus.PAST_DUE
        
        self.db.commit()
        
        # Send notification email
        if self.email_enabled and self.email_service:
            self._send_payment_failed_email(
                user_id=user_id,
                invoice=invoice,
                failure_reason=failure_reason,
                retry_count=retry_count
            )
        
        # Schedule retry if applicable
        next_retry = None
        if should_retry:
            delay_days = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
            next_retry = datetime.utcnow() + timedelta(days=delay_days)
            
            # Create dunning schedule entry
            self._create_dunning_schedule(
                invoice_id=invoice_id,
                user_id=user_id,
                retry_attempt=retry_count + 1,
                scheduled_date=next_retry
            )
        else:
            # Final attempt failed - cancel subscription if applicable
            if subscription:
                self._handle_final_payment_failure(subscription, invoice)
        
        return {
            "status": "processed",
            "retry_count": retry_count,
            "should_retry": should_retry,
            "next_retry": next_retry.isoformat() if next_retry else None,
            "invoice_status": invoice.status.value,
            "subscription_status": subscription.status.value if subscription else None
        }
    
    def _handle_final_payment_failure(
        self,
        subscription: Subscription,
        invoice: Invoice
    ) -> None:
        """Handle final payment failure after all retries exhausted"""
        
        # Cancel subscription
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.utcnow()
        
        # Mark invoice as uncollectible
        invoice.status = InvoiceStatus.UNCOLLECTIBLE
        
        self.db.commit()
        
        # Send final notice email
        if self.email_enabled and self.email_service:
            self.email_service.send_subscription_cancelled_due_to_payment_failure(
                user_id=subscription.user_id,
                subscription=subscription,
                invoice=invoice
            )
        
        # Log event
        from app.models.billing import BillingEvent
        event = BillingEvent(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            invoice_id=invoice.id,
            event_type="subscription_cancelled_payment_failure",
            description="Subscription cancelled due to payment failure after all retry attempts",
            metadata={
                "final_invoice_id": invoice.id,
                "amount_due": float(invoice.amount_due)
            }
        )
        self.db.add(event)
        self.db.commit()
    
    # ============================================================================
    # RETRY MANAGEMENT
    # ============================================================================
    
    def _create_dunning_schedule(
        self,
        invoice_id: int,
        user_id: int,
        retry_attempt: int,
        scheduled_date: datetime
    ) -> None:
        """Create dunning schedule entry for automated retry"""
        
        from app.models.billing import BillingEvent
        
        event = BillingEvent(
            user_id=user_id,
            invoice_id=invoice_id,
            event_type="dunning_retry_scheduled",
            description=f"Payment retry #{retry_attempt} scheduled",
            metadata={
                "retry_attempt": retry_attempt,
                "scheduled_date": scheduled_date.isoformat(),
                "total_attempts": self.retry_attempts
            }
        )
        
        self.db.add(event)
        self.db.commit()
    
    def process_scheduled_retries(self) -> Dict[str, Any]:
        """
        Process all scheduled payment retries that are due
        
        Should be called periodically by a background task/cron job
        """
        
        if not self.enabled:
            return {"dunning_enabled": False, "processed": 0}
        
        from app.models.billing import BillingEvent
        
        # Find all scheduled retries that are due
        now = datetime.utcnow()
        
        scheduled_events = self.db.query(BillingEvent).filter(
            BillingEvent.event_type == "dunning_retry_scheduled",
            BillingEvent.created_at <= now  # Use created_at + offset for scheduled_date
        ).all()
        
        results = []
        processed_count = 0
        
        for event in scheduled_events:
            metadata = event.metadata or {}
            invoice_id = event.invoice_id
            
            if not invoice_id:
                continue
            
            # Attempt to retry payment
            retry_result = self.retry_invoice_payment(invoice_id, event.user_id)
            results.append(retry_result)
            
            if retry_result["status"] == "success":
                processed_count += 1
        
        return {
            "processed": processed_count,
            "total_scheduled": len(scheduled_events),
            "results": results
        }
    
    def retry_invoice_payment(
        self,
        invoice_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Retry payment for an invoice using stored payment method
        
        Returns payment result
        """
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"status": "error", "reason": "invoice_not_found"}
        
        if invoice.status == InvoiceStatus.PAID:
            return {"status": "skipped", "reason": "invoice_already_paid"}
        
        # Get subscription to find payment method
        subscription = None
        if invoice.subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == invoice.subscription_id
            ).first()
        
        if not subscription or not subscription.payment_method_id:
            return {"status": "error", "reason": "no_payment_method"}
        
        # Attempt to charge payment method
        try:
            from app.services.billing_service import BillingService
            billing_service = BillingService(self.db)
            
            # This would call the actual payment processing
            # For now, we'll create a pending payment record
            
            payment = Payment(
                payment_id=f"retry_{invoice_id}_{datetime.utcnow().timestamp()}",
                invoice_id=invoice_id,
                user_id=user_id,
                amount=invoice.amount_due,
                currency=invoice.currency,
                status=PaymentStatus.PENDING,
                payment_method_id=subscription.payment_method_id
            )
            
            self.db.add(payment)
            self.db.commit()
            
            # In production, actually process the payment here
            # For now, mark as processing
            
            return {
                "status": "initiated",
                "payment_id": payment.id,
                "invoice_id": invoice_id,
                "amount": float(invoice.amount_due)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e),
                "invoice_id": invoice_id
            }
    
    # ============================================================================
    # EMAIL NOTIFICATIONS
    # ============================================================================
    
    def _send_payment_failed_email(
        self,
        user_id: int,
        invoice: Invoice,
        failure_reason: str,
        retry_count: int
    ) -> None:
        """Send payment failure notification email"""
        
        if not self.email_service:
            return
        
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return
        
        # Determine email type based on retry count
        if retry_count == 0:
            # First failure - friendly reminder
            subject = "Payment Failed - Please Update Your Payment Method"
            message_type = "initial_failure"
        elif retry_count < self.retry_attempts - 1:
            # Mid-dunning - more urgent
            subject = f"Payment Retry {retry_count + 1} Failed - Action Required"
            message_type = "retry_failure"
        else:
            # Final attempt - critical
            subject = "Final Payment Attempt Failed - Subscription Will Be Cancelled"
            message_type = "final_failure"
        
        # Calculate next retry date
        next_retry = None
        if retry_count < self.retry_attempts:
            delay_days = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
            next_retry = datetime.utcnow() + timedelta(days=delay_days)
        
        # Send email
        self.email_service.send_payment_failure_notification(
            email=user.email,
            name=user.full_name,
            invoice_number=invoice.invoice_number,
            amount=invoice.amount_due,
            currency=invoice.currency,
            failure_reason=failure_reason,
            retry_count=retry_count + 1,
            total_retries=self.retry_attempts,
            next_retry_date=next_retry,
            message_type=message_type
        )
    
    def send_payment_method_update_request(
        self,
        user_id: int,
        subscription_id: int
    ) -> bool:
        """Send email requesting payment method update"""
        
        if not self.email_service:
            return False
        
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == user_id).first()
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not user or not subscription:
            return False
        
        self.email_service.send_payment_method_update_request(
            email=user.email,
            name=user.full_name,
            subscription=subscription
        )
        
        return True
    
    # ============================================================================
    # GRACE PERIOD MANAGEMENT
    # ============================================================================
    
    def apply_grace_period(
        self,
        subscription_id: int,
        grace_days: int = 7
    ) -> Dict[str, Any]:
        """
        Apply grace period to subscription after payment failure
        
        Subscription remains active but marked as past_due
        """
        
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            return {"status": "error", "reason": "subscription_not_found"}
        
        # Mark as past due but don't cancel yet
        subscription.status = SubscriptionStatus.PAST_DUE
        
        # Set grace period end date in metadata
        grace_end = datetime.utcnow() + timedelta(days=grace_days)
        
        if not subscription.metadata:
            subscription.metadata = {}
        
        subscription.metadata["grace_period_end"] = grace_end.isoformat()
        subscription.metadata["grace_days"] = grace_days
        
        self.db.commit()
        
        # Log event
        from app.models.billing import BillingEvent
        event = BillingEvent(
            user_id=subscription.user_id,
            subscription_id=subscription_id,
            event_type="grace_period_applied",
            description=f"Grace period of {grace_days} days applied to subscription",
            metadata={
                "grace_days": grace_days,
                "grace_end": grace_end.isoformat()
            }
        )
        self.db.add(event)
        self.db.commit()
        
        return {
            "status": "success",
            "grace_period_days": grace_days,
            "grace_period_end": grace_end.isoformat(),
            "subscription_status": subscription.status.value
        }
    
    def check_grace_periods(self) -> Dict[str, Any]:
        """
        Check all subscriptions in grace period and cancel those whose period has expired
        
        Should be called by daily cron job
        """
        
        from app.models.billing import BillingEvent
        
        # Find subscriptions in grace period
        past_due_subscriptions = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.PAST_DUE
        ).all()
        
        expired_count = 0
        now = datetime.utcnow()
        
        for subscription in past_due_subscriptions:
            if not subscription.metadata:
                continue
            
            grace_end_str = subscription.metadata.get("grace_period_end")
            if not grace_end_str:
                continue
            
            grace_end = datetime.fromisoformat(grace_end_str)
            
            if now > grace_end:
                # Grace period expired - cancel subscription
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = now
                
                # Log event
                event = BillingEvent(
                    user_id=subscription.user_id,
                    subscription_id=subscription.id,
                    event_type="subscription_cancelled_grace_expired",
                    description="Subscription cancelled after grace period expiration",
                    metadata={
                        "grace_period_end": grace_end_str,
                        "cancelled_at": now.isoformat()
                    }
                )
                self.db.add(event)
                
                expired_count += 1
        
        self.db.commit()
        
        return {
            "checked": len(past_due_subscriptions),
            "expired": expired_count
        }
    
    # ============================================================================
    # REPORTING
    # ============================================================================
    
    def get_dunning_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get dunning statistics for reporting
        
        Includes recovery rates, retry success, etc.
        """
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Count failed payments
        failed_payments = self.db.query(Payment).filter(
            Payment.status == PaymentStatus.FAILED,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).count()
        
        # Count recovered payments (succeeded after previous failures)
        recovered_payments = self.db.query(Payment).filter(
            Payment.status == PaymentStatus.SUCCEEDED,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
            Payment.payment_id.like('retry_%')
        ).count()
        
        # Count overdue invoices
        overdue_invoices = self.db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.OVERDUE,
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).count()
        
        # Count uncollectible invoices
        uncollectible_invoices = self.db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.UNCOLLECTIBLE,
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).count()
        
        # Calculate recovery rate
        total_failures = failed_payments
        recovery_rate = (recovered_payments / total_failures * 100) if total_failures > 0 else 0
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "failed_payments": failed_payments,
            "recovered_payments": recovered_payments,
            "recovery_rate_percentage": round(recovery_rate, 2),
            "overdue_invoices": overdue_invoices,
            "uncollectible_invoices": uncollectible_invoices,
            "total_at_risk_revenue": self._calculate_at_risk_revenue(start_date, end_date)
        }
    
    def _calculate_at_risk_revenue(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate total revenue at risk from overdue invoices"""
        
        from sqlalchemy import func
        
        result = self.db.query(
            func.sum(Invoice.amount_due)
        ).filter(
            Invoice.status.in_([InvoiceStatus.OVERDUE, InvoiceStatus.PAST_DUE]),
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).scalar()
        
        return float(result) if result else 0.0
