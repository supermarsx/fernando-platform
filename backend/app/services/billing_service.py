"""
Billing Service

Comprehensive billing and subscription management service with:
- Subscription lifecycle management
- Invoice generation and management
- Payment processing
- Usage tracking and overage calculations
- Proration handling
- Tax calculation
- Analytics and reporting
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Any, Tuple
import secrets
import calendar
import time

from app.models.billing import (
    SubscriptionPlan, Subscription, Invoice, Payment, PaymentMethodModel,
    UsageRecord, BillingEvent, TaxRate,
    SubscriptionStatus, InvoiceStatus, PaymentStatus, BillingCycle, PaymentMethod
)
from app.models.credit import (
    CreditAccount, CreditTransaction, CreditPolicy, CreditTransactionType
)
from app.schemas.billing_schemas import (
    SubscriptionPlanCreate, SubscriptionCreate, InvoiceCreate,
    PaymentCreate, UsageRecordCreate, InvoiceLineItem
)
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel, TelemetryMixin
from app.middleware.telemetry_decorators import (
    billing_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric, timer_metric
)


class BillingService(TelemetryMixin):
    """
    Service for managing billing, subscriptions, and payments
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.log_telemetry_event(
            "billing.service_initialized", 
            TelemetryEvent.SUBSCRIPTION_CREATED,
            level=TelemetryLevel.INFO
        )
    
    # ============================================================================
    # CREDIT INTEGRATION METHODS
    # ============================================================================
    
    def create_subscription_with_credits(
        self, 
        user_id: int, 
        subscription_data: SubscriptionCreate,
        credit_allocation: Optional[float] = None
    ) -> Subscription:
        """
        Create a subscription with initial credit allocation
        
        Args:
            user_id: User ID
            subscription_data: Subscription creation data
            credit_allocation: Initial credit allocation (overrides plan default)
        
        Returns:
            Created subscription
        """
        # Create subscription
        subscription = self.create_subscription(user_id, subscription_data)
        
        # Get credit allocation from plan or parameter
        if credit_allocation is None:
            plan = self.get_subscription_plan(subscription_data.plan_id)
            if plan and plan.features:
                credit_allocation = plan.features.get("monthly_credits", 1000.0)
            else:
                credit_allocation = 1000.0  # Default allocation
        
        # Create credit account if it doesn't exist
        from app.services.credit_service import CreditService
        credit_service = CreditService(self.db)
        
        credit_account = credit_service.get_credit_account(user_id)
        if not credit_account:
            from app.schemas.credit_schemas import CreditAccountCreate
            credit_account = credit_service.create_credit_account(
                CreditAccountCreate(user_id=user_id)
            )
        
        # Allocate initial credits
        credit_service.add_credits(
            user_id=user_id,
            amount=credit_allocation,
            transaction_type=CreditTransactionType.ALLOCATION,
            description=f"Initial credit allocation for {plan.name if plan else 'subscription'}",
            reference_id=str(subscription.id),
            reference_type="subscription",
            metadata={
                "subscription_id": subscription.id,
                "plan_id": subscription_data.plan_id,
                "allocation_source": "subscription_creation"
            }
        )
        
        # Log credit allocation
        self.log_telemetry_event(
            "billing.credits_allocated",
            TelemetryEvent.SUBSCRIPTION_CREATED,
            level=TelemetryLevel.INFO,
            user_id=user_id,
            metadata={
                "subscription_id": subscription.id,
                "credit_allocation": credit_allocation,
                "plan_id": subscription_data.plan_id
            }
        )
        
        return subscription
    
    def process_credit_purchase(
        self,
        user_id: int,
        amount: float,
        payment_method_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process credit purchase through billing system
        
        Args:
            user_id: User ID
            amount: Credit amount to purchase
            payment_method_id: Payment method to use
            description: Purchase description
        
        Returns:
            Purchase result with credit account balance
        """
        # Validate credit amount
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        if amount > 10000:  # Max purchase limit
            raise ValueError("Credit amount exceeds maximum limit")
        
        # Get or create payment method
        payment_method = None
        if payment_method_id:
            payment_method = self.db.query(PaymentMethodModel).filter(
                and_(
                    PaymentMethodModel.id == payment_method_id,
                    PaymentMethodModel.user_id == user_id,
                    PaymentMethodModel.is_default == True
                )
            ).first()
        
        if not payment_method:
            raise ValueError("Valid payment method required")
        
        # Create invoice for credit purchase
        invoice = self.create_credit_purchase_invoice(user_id, amount)
        
        # Process payment
        payment = self.process_payment(
            user_id=user_id,
            payment_data=PaymentCreate(
                invoice_id=invoice.id,
                amount=amount,
                payment_method_id=payment_method_id,
                status=PaymentStatus.PENDING,
                metadata={
                    "type": "credit_purchase",
                    "credit_amount": amount
                }
            )
        )
        
        # If payment successful, allocate credits
        if payment.status == PaymentStatus.COMPLETED:
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)
            
            credit_service.add_credits(
                user_id=user_id,
                amount=amount,
                transaction_type=CreditTransactionType.PURCHASE,
                description=description or f"Credit purchase of {amount} credits",
                reference_id=str(invoice.id),
                reference_type="invoice",
                metadata={
                    "invoice_id": invoice.id,
                    "payment_id": payment.id,
                    "purchase_method": "billing_system"
                }
            )
            
            # Get updated balance
            credit_account = credit_service.get_credit_account(user_id)
            
            # Log successful purchase
            self.log_telemetry_event(
                "billing.credit_purchase_completed",
                TelemetryEvent.PAYMENT_PROCESSED,
                level=TelemetryLevel.INFO,
                user_id=user_id,
                metadata={
                    "purchase_amount": amount,
                    "invoice_id": invoice.id,
                    "payment_id": payment.id,
                    "new_balance": credit_account.current_balance if credit_account else 0
                }
            )
            
            return {
                "success": True,
                "invoice_id": invoice.id,
                "payment_id": payment.id,
                "credit_amount": amount,
                "new_balance": credit_account.current_balance if credit_account else 0,
                "transaction_id": f"purchase_{payment.id}"
            }
        
        else:
            # Payment failed
            self.log_telemetry_event(
                "billing.credit_purchase_failed",
                TelemetryEvent.PAYMENT_FAILED,
                level=TelemetryLevel.WARNING,
                user_id=user_id,
                metadata={
                    "purchase_amount": amount,
                    "invoice_id": invoice.id,
                    "payment_status": payment.status.value
                }
            )
            
            return {
                "success": False,
                "invoice_id": invoice.id,
                "payment_id": payment.id,
                "error": f"Payment failed with status: {payment.status.value}"
            }
    
    def create_credit_purchase_invoice(self, user_id: int, credit_amount: float) -> Invoice:
        """
        Create invoice for credit purchase
        
        Args:
            user_id: User ID
            credit_amount: Credit amount being purchased
        
        Returns:
            Created invoice
        """
        # Calculate price per credit
        price_per_credit = 0.01  # $0.01 per credit
        
        # Calculate totals
        subtotal = credit_amount * price_per_credit
        tax_rate = self._get_applicable_tax_rate(user_id)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Create invoice
        invoice_data = InvoiceCreate(
            user_id=user_id,
            invoice_number=f"CREDIT-{int(time.time())}",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            currency="USD",
            due_date=datetime.utcnow() + timedelta(days=30),
            status=InvoiceStatus.DRAFT
        )
        
        # Add line item for credit purchase
        line_items = [
            InvoiceLineItem(
                description=f"Credit Purchase - {credit_amount:,.0f} credits",
                quantity=credit_amount,
                unit_price=price_per_credit,
                total_amount=subtotal
            )
        ]
        invoice_data.line_items = line_items
        
        invoice = self.create_invoice(invoice_data)
        
        # Update status to SENT
        invoice.status = InvoiceStatus.SENT
        self.db.commit()
        
        return invoice
    
    def apply_credit_usage_to_billing(
        self,
        user_id: int,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Dict[str, Any]:
        """
        Apply credit usage to billing calculations
        
        Args:
            user_id: User ID
            billing_period_start: Start of billing period
            billing_period_end: End of billing period
        
        Returns:
            Billing summary with credit adjustments
        """
        from app.services.credit_service import CreditService
        credit_service = CreditService(self.db)
        
        # Get credit usage for period
        usage_summary = credit_service.get_usage_summary(
            user_id=user_id,
            start_date=billing_period_start,
            end_date=billing_period_end
        )
        
        # Get subscription for user
        subscription = self.get_user_active_subscription(user_id)
        if not subscription:
            return {"error": "No active subscription found"}
        
        # Calculate base subscription cost
        plan = self.get_subscription_plan(subscription.plan_id)
        base_cost = plan.monthly_price if plan else 0
        
        # Calculate credit usage cost
        credit_cost = usage_summary.total_cost
        
        # Calculate adjustments
        credit_adjustment = 0
        overage_cost = 0
        
        # Check if subscription includes credits
        if plan and plan.features:
            included_credits = plan.features.get("monthly_credits", 0)
            if credit_cost <= included_credits:
                credit_adjustment = -credit_cost  # Full credit
            else:
                overage_cost = credit_cost - included_credits
                credit_adjustment = -included_credits  # Partial credit
        
        # Final billing amount
        final_amount = base_cost + overage_cost + (subscription.current_usage_cost or 0)
        
        # Update subscription usage cost
        subscription.current_usage_cost = credit_cost
        self.db.commit()
        
        return {
            "billing_period": {
                "start": billing_period_start.isoformat(),
                "end": billing_period_end.isoformat()
            },
            "base_subscription_cost": base_cost,
            "credit_usage": {
                "total_cost": credit_cost,
                "total_transactions": usage_summary.total_transactions,
                "included_in_subscription": plan.features.get("monthly_credits", 0) if plan and plan.features else 0
            },
            "billing_adjustments": {
                "credit_adjustment": credit_adjustment,
                "overage_cost": overage_cost
            },
            "final_billing_amount": final_amount,
            "net_cost_after_credits": final_amount
        }
    
    def generate_credit_revenue_report(
        self,
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate revenue report focusing on credit operations
        
        Args:
            start_date: Report start date
            end_date: Report end date
            organization_id: Optional organization filter
        
        Returns:
            Credit revenue report data
        """
        # Get all credit transactions in period
        from app.models.credit import CreditTransaction, CreditAccount
        
        query = self.db.query(CreditTransaction).join(
            CreditAccount, CreditTransaction.account_id == CreditAccount.id
        ).filter(
            and_(
                CreditTransaction.created_at >= start_date,
                CreditTransaction.created_at <= end_date,
                CreditTransaction.transaction_type.in_([
                    CreditTransactionType.PURCHASE,
                    CreditTransactionType.USAGE_DEDUCTION
                ])
            )
        )
        
        if organization_id:
            query = query.filter(CreditAccount.organization_id == organization_id)
        
        transactions = query.all()
        
        # Calculate revenue metrics
        purchase_transactions = [
            t for t in transactions 
            if t.transaction_type == CreditTransactionType.PURCHASE
        ]
        
        usage_transactions = [
            t for t in transactions 
            if t.transaction_type == CreditTransactionType.USAGE_DEDUCTION
        ]
        
        total_purchases = sum(t.amount for t in purchase_transactions)
        total_usage_deduction = sum(abs(t.amount) for t in usage_transactions)
        
        # Calculate revenue by period
        revenue_by_day = {}
        for transaction in purchase_transactions:
            day = transaction.created_at.date().isoformat()
            if day not in revenue_by_day:
                revenue_by_day[day] = 0
            revenue_by_day[day] += transaction.amount
        
        # Top customers by credit purchases
        customer_purchases = {}
        for transaction in purchase_transactions:
            customer_id = transaction.account.user_id
            if customer_id not in customer_purchases:
                customer_purchases[customer_id] = {
                    "total_purchases": 0,
                    "transaction_count": 0,
                    "last_purchase": None
                }
            
            customer_purchases[customer_id]["total_purchases"] += transaction.amount
            customer_purchases[customer_id]["transaction_count"] += 1
            
            if (not customer_purchases[customer_id]["last_purchase"] or 
                transaction.created_at > customer_purchases[customer_id]["last_purchase"]):
                customer_purchases[customer_id]["last_purchase"] = transaction.created_at
        
        # Top customers by usage
        customer_usage = {}
        for transaction in usage_transactions:
            customer_id = transaction.account.user_id
            if customer_id not in customer_usage:
                customer_usage[customer_id] = {
                    "total_usage_cost": 0,
                    "usage_transactions": 0,
                    "avg_cost_per_transaction": 0
                }
            
            customer_usage[customer_id]["total_usage_cost"] += abs(transaction.amount)
            customer_usage[customer_id]["usage_transactions"] += 1
        
        # Calculate average cost per transaction
        for customer_id in customer_usage:
            data = customer_usage[customer_id]
            if data["usage_transactions"] > 0:
                data["avg_cost_per_transaction"] = data["total_usage_cost"] / data["usage_transactions"]
        
        # Credit utilization metrics
        total_allocated_credits = sum(t.amount for t in purchase_transactions)
        total_consumed_credits = sum(abs(t.amount) for t in usage_transactions)
        utilization_rate = (total_consumed_credits / total_allocated_credits * 100) if total_allocated_credits > 0 else 0
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_credit_purchases": total_purchases,
                "total_credit_usage": total_usage_deduction,
                "net_credit_flow": total_purchases - total_usage_deduction,
                "total_purchase_transactions": len(purchase_transactions),
                "total_usage_transactions": len(usage_transactions),
                "credit_utilization_rate": round(utilization_rate, 2)
            },
            "revenue_breakdown": {
                "by_day": revenue_by_day,
                "avg_daily_revenue": sum(revenue_by_day.values()) / len(revenue_by_day) if revenue_by_day else 0,
                "peak_day": max(revenue_by_day, key=revenue_by_day.get) if revenue_by_day else None,
                "peak_day_revenue": max(revenue_by_day.values()) if revenue_by_day else 0
            },
            "customer_analysis": {
                "total_customers_with_purchases": len(customer_purchases),
                "total_customers_with_usage": len(customer_usage),
                "top_customers_by_purchases": sorted(
                    [{"customer_id": k, **v} for k, v in customer_purchases.items()],
                    key=lambda x: x["total_purchases"],
                    reverse=True
                )[:10],
                "top_customers_by_usage": sorted(
                    [{"customer_id": k, **v} for k, v in customer_usage.items()],
                    key=lambda x: x["total_usage_cost"],
                    reverse=True
                )[:10]
            },
            "credit_flow": {
                "total_allocated": total_allocated_credits,
                "total_consumed": total_consumed_credits,
                "remaining_credits": total_allocated_credits - total_consumed_credits,
                "average_daily_consumption": total_consumed_credits / max(1, (end_date - start_date).days)
            }
        }
    
    def _get_applicable_tax_rate(self, user_id: int) -> float:
        """Get applicable tax rate for user"""
        # This would typically check user's location, tax rules, etc.
        # For now, return a default rate
        return 0.08  # 8% default tax rate
    
    # ============================================================================
    # CREDIT-BASED INVOICING
    # ============================================================================
    
    def generate_credit_based_invoice(
        self,
        user_id: int,
        subscription_id: int,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Invoice:
        """
        Generate invoice with detailed credit usage breakdown
        
        Args:
            user_id: User ID
            subscription_id: Subscription ID
            billing_period_start: Start of billing period
            billing_period_end: End of billing period
        
        Returns:
            Generated invoice with credit line items
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        plan = subscription.plan
        
        # Get credit usage summary
        credit_usage = self.apply_credit_usage_to_billing(
            user_id, billing_period_start, billing_period_end
        )
        
        # Build invoice line items
        line_items = []
        subtotal = 0
        
        # Base subscription charge
        line_items.append({
            "description": f"{plan.name} - {subscription.billing_cycle.value.capitalize()} Subscription",
            "quantity": 1,
            "unit_price": subscription.base_amount,
            "amount": subscription.base_amount,
            "category": "base_subscription"
        })
        subtotal += subscription.base_amount
        
        # Credit allocation line item (if subscription includes credits)
        if plan.features and plan.features.get("monthly_credits", 0) > 0:
            included_credits = plan.features["monthly_credits"]
            line_items.append({
                "description": f"Monthly Credit Allocation - {included_credits:,.0f} credits included",
                "quantity": included_credits,
                "unit_price": 0.0,  # Included in base subscription
                "amount": 0.0,
                "category": "credit_included"
            })
        
        # Credit usage breakdown by service/model
        if credit_usage["credit_usage"]["total_cost"] > 0:
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)
            
            usage_breakdown = credit_service.get_usage_breakdown_by_model(
                user_id, billing_period_start, billing_period_end
            )
            
            for model_usage in usage_breakdown:
                cost = model_usage.get("total_cost", 0)
                if cost > 0:
                    line_items.append({
                        "description": f"LLM Usage - {model_usage['model']} ({model_usage['requests']} requests)",
                        "quantity": model_usage.get("total_tokens", 0),
                        "unit_price": cost / max(1, model_usage.get("total_tokens", 1)),
                        "amount": cost,
                        "category": "llm_usage",
                        "metadata": {
                            "model": model_usage["model"],
                            "requests": model_usage["requests"],
                            "tokens": model_usage.get("total_tokens", 0)
                        }
                    })
                    subtotal += cost
        
        # Overage charges (if any)
        if credit_usage["billing_adjustments"]["overage_cost"] > 0:
            overage = credit_usage["billing_adjustments"]["overage_cost"]
            line_items.append({
                "description": "Credit Overage Charges",
                "quantity": 1,
                "unit_price": overage,
                "amount": overage,
                "category": "credit_overage"
            })
            subtotal += overage
        
        # Credit adjustments (negative values = credits)
        if credit_usage["billing_adjustments"]["credit_adjustment"] != 0:
            adjustment = credit_usage["billing_adjustments"]["credit_adjustment"]
            line_items.append({
                "description": "Credit Adjustment",
                "quantity": 1,
                "unit_price": adjustment,
                "amount": adjustment,
                "category": "credit_adjustment"
            })
            subtotal += adjustment
        
        # Calculate tax
        tax_rate = self._get_applicable_tax_rate(user_id)
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # Generate invoice
        invoice_number = self._generate_invoice_number()
        
        invoice = Invoice(
            invoice_number=invoice_number,
            subscription_id=subscription.id,
            user_id=user_id,
            status=InvoiceStatus.DRAFT,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=0,
            total_amount=total_amount,
            amount_paid=0,
            amount_due=total_amount,
            currency=subscription.currency,
            line_items=line_items,
            due_date=billing_period_end + timedelta(days=30),
            period_start=billing_period_start,
            period_end=billing_period_end,
            tax_rate=tax_rate
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        
        # Log invoice creation
        self.log_telemetry_event(
            "billing.credit_based_invoice_created",
            TelemetryEvent.INVOICE_CREATED,
            level=TelemetryLevel.INFO,
            user_id=user_id,
            metadata={
                "invoice_id": invoice.id,
                "subscription_id": subscription_id,
                "billing_period": f"{billing_period_start.date()} to {billing_period_end.date()}",
                "total_amount": total_amount,
                "credit_usage_amount": credit_usage["credit_usage"]["total_cost"],
                "line_items_count": len(line_items)
            }
        )
        
        return invoice
    
    def get_credit_revenue_analytics(self, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive credit revenue analytics
        
        Args:
            organization_id: Optional organization filter
        
        Returns:
            Credit revenue analytics data
        """
        from app.services.credit_service import CreditService
        
        # Base query for credit transactions
        base_query = self.db.query(CreditTransaction).join(
            CreditAccount, CreditTransaction.account_id == CreditAccount.id
        )
        
        if organization_id:
            base_query = base_query.filter(CreditAccount.organization_id == organization_id)
        
        # Time periods for analysis
        now = datetime.utcnow()
        periods = {
            "today": (now.replace(hour=0, minute=0, second=0, microsecond=0), now),
            "week": (now - timedelta(days=7), now),
            "month": (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now),
            "quarter": (now.replace(month=((now.month - 1) // 3) * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0), now),
            "year": (now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0), now)
        }
        
        # Revenue metrics by period
        revenue_by_period = {}
        for period_name, (start_date, end_date) in periods.items():
            period_query = base_query.filter(
                CreditTransaction.created_at >= start_date,
                CreditTransaction.created_at <= end_date
            )
            
            purchases = period_query.filter(
                CreditTransaction.transaction_type == CreditTransactionType.PURCHASE
            ).all()
            
            total_revenue = sum(t.amount for t in purchases)
            transaction_count = len(purchases)
            avg_transaction_value = total_revenue / transaction_count if transaction_count > 0 else 0
            
            revenue_by_period[period_name] = {
                "total_revenue": round(total_revenue, 2),
                "transaction_count": transaction_count,
                "average_transaction_value": round(avg_transaction_value, 2)
            }
        
        # Credit utilization analytics
        credit_flow_query = base_query.filter(
            CreditTransaction.created_at >= periods["month"][0],
            CreditTransaction.created_at <= periods["month"][1]
        )
        
        allocations = credit_flow_query.filter(
            CreditTransaction.transaction_type == CreditTransactionType.ALLOCATION
        ).all()
        
        usage_deductions = credit_flow_query.filter(
            CreditTransaction.transaction_type == CreditTransactionType.USAGE_DEDUCTION
        ).all()
        
        total_allocated = sum(t.amount for t in allocations)
        total_used = sum(abs(t.amount) for t in usage_deductions)
        utilization_rate = (total_used / total_allocated * 100) if total_allocated > 0 else 0
        
        # Top credit consumers
        credit_consumers = self.db.query(
            CreditAccount.user_id,
            func.sum(func.abs(CreditTransaction.amount)).label("total_used"),
            func.count(CreditTransaction.id).label("transaction_count")
        ).join(
            CreditTransaction, CreditAccount.id == CreditTransaction.account_id
        ).filter(
            CreditTransaction.transaction_type == CreditTransactionType.USAGE_DEDUCTION,
            CreditTransaction.created_at >= periods["month"][0],
            CreditTransaction.created_at <= periods["month"][1]
        ).group_by(CreditAccount.user_id).order_by(
            func.sum(func.abs(CreditTransaction.amount)).desc()
        ).limit(10).all()
        
        # Customer lifetime value from credits
        customer_clv = self.db.query(
            CreditAccount.user_id,
            func.sum(CreditTransaction.amount).label("total_purchased"),
            func.count(func.distinct(CreditTransaction.id)).label("purchase_frequency"),
            func.min(CreditTransaction.created_at).label("first_purchase"),
            func.max(CreditTransaction.created_at).label("last_purchase")
        ).join(
            CreditTransaction, CreditAccount.id == CreditTransaction.account_id
        ).filter(
            CreditTransaction.transaction_type == CreditTransactionType.PURCHASE
        ).group_by(CreditAccount.user_id).order_by(
            func.sum(CreditTransaction.amount).desc()
        ).limit(20).all()
        
        # Revenue trends (last 30 days daily breakdown)
        daily_revenue = {}
        for i in range(30):
            day_start = now - timedelta(days=i)
            day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_revenue = base_query.filter(
                CreditTransaction.created_at >= day_start,
                CreditTransaction.created_at < day_end,
                CreditTransaction.transaction_type == CreditTransactionType.PURCHASE
            ).all()
            
            total_day_revenue = sum(t.amount for t in day_revenue)
            daily_revenue[day_start.date().isoformat()] = round(total_day_revenue, 2)
        
        return {
            "analytics_generated_at": now.isoformat(),
            "revenue_by_period": revenue_by_period,
            "credit_utilization": {
                "total_allocated_this_month": round(total_allocated, 2),
                "total_used_this_month": round(total_used, 2),
                "utilization_rate": round(utilization_rate, 2),
                "remaining_credits": round(total_allocated - total_used, 2)
            },
            "top_credit_consumers": [
                {
                    "user_id": consumer.user_id,
                    "total_credits_used": round(consumer.total_used, 2),
                    "transaction_count": consumer.transaction_count
                }
                for consumer in credit_consumers
            ],
            "customer_lifetime_value": [
                {
                    "user_id": customer.user_id,
                    "total_purchased": round(customer.total_purchased, 2),
                    "purchase_frequency": customer.purchase_frequency,
                    "first_purchase": customer.first_purchase.isoformat() if customer.first_purchase else None,
                    "last_purchase": customer.last_purchase.isoformat() if customer.last_purchase else None,
                    "avg_purchase_value": round(customer.total_purchased / max(1, customer.purchase_frequency), 2)
                }
                for customer in customer_clv
            ],
            "daily_revenue_trend": dict(sorted(daily_revenue.items()))
        }
    
    def forecast_credit_revenue(self, days_ahead: int = 90) -> Dict[str, Any]:
        """
        Forecast credit revenue based on historical patterns
        
        Args:
            days_ahead: Number of days to forecast
        
        Returns:
            Revenue forecast data
        """
        from app.services.usage_tracking.forecasting_engine import ForecastingEngine
        
        now = datetime.utcnow()
        
        # Get historical revenue data (last 90 days)
        start_date = now - timedelta(days=90)
        
        historical_data = self.generate_credit_revenue_report(
            start_date=start_date,
            end_date=now
        )
        
        # Get forecasting engine
        forecasting_engine = ForecastingEngine(self.db)
        
        # Generate revenue forecast
        forecast = forecasting_engine.forecast_credit_revenue(
            historical_data=historical_data["revenue_breakdown"]["by_day"],
            forecast_days=days_ahead
        )
        
        # Calculate key metrics
        total_forecast_revenue = sum(forecast["daily_forecasts"].values())
        avg_daily_forecast = total_forecast_revenue / len(forecast["daily_forecasts"])
        
        # Confidence intervals
        confidence_80_lower = []
        confidence_80_upper = []
        confidence_95_lower = []
        confidence_95_upper = []
        
        for date, forecast_value in forecast["daily_forecasts"].items():
            # Simplified confidence intervals (in production, use proper statistical methods)
            variance = forecast_value * 0.1  # 10% variance assumption
            confidence_80_lower.append(forecast_value - (variance * 1.28))
            confidence_80_upper.append(forecast_value + (variance * 1.28))
            confidence_95_lower.append(forecast_value - (variance * 1.96))
            confidence_95_upper.append(forecast_value + (variance * 1.96))
        
        return {
            "forecast_period": {
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=days_ahead)).isoformat(),
                "days_ahead": days_ahead
            },
            "forecast_summary": {
                "total_forecast_revenue": round(total_forecast_revenue, 2),
                "average_daily_revenue": round(avg_daily_forecast, 2),
                "growth_rate": forecast.get("growth_rate", 0),
                "seasonal_factor": forecast.get("seasonal_factor", 1.0)
            },
            "confidence_intervals": {
                "80_percent": {
                    "lower_bound": round(sum(confidence_80_lower) / len(confidence_80_lower), 2),
                    "upper_bound": round(sum(confidence_80_upper) / len(confidence_80_upper), 2)
                },
                "95_percent": {
                    "lower_bound": round(sum(confidence_95_lower) / len(confidence_95_lower), 2),
                    "upper_bound": round(sum(confidence_95_upper) / len(confidence_95_upper), 2)
                }
            },
            "daily_forecasts": forecast["daily_forecasts"],
            "model_performance": {
                "accuracy_score": forecast.get("accuracy_score", 0.85),
                "r_squared": forecast.get("r_squared", 0.78),
                "mae": forecast.get("mae", 0.0)
            }
        }
    
    def get_subscription_credit_balance(
        self,
        user_id: int,
        subscription_id: int
    ) -> Dict[str, Any]:
        """
        Get subscription credit balance and usage summary
        
        Args:
            user_id: User ID
            subscription_id: Subscription ID
        
        Returns:
            Credit balance and usage summary
        """
        from app.services.credit_service import CreditService
        
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        plan = subscription.plan
        credit_service = CreditService(self.db)
        
        # Get current credit balance
        credit_account = credit_service.get_credit_account(user_id)
        current_balance = credit_account.current_balance if credit_account else 0
        
        # Get usage for current period
        usage_summary = credit_service.get_usage_summary(
            user_id=user_id,
            start_date=subscription.current_period_start,
            end_date=subscription.current_period_end
        )
        
        # Calculate available credits
        included_credits = plan.features.get("monthly_credits", 0) if plan and plan.features else 0
        credits_used = usage_summary.total_usage
        available_credits = included_credits - credits_used + current_balance
        
        # Calculate daily burn rate
        days_in_period = (subscription.current_period_end - subscription.current_period_start).days
        days_elapsed = (datetime.utcnow() - subscription.current_period_start).days
        daily_burn_rate = credits_used / max(1, days_elapsed)
        
        # Estimate days until depletion
        projected_depletion_date = None
        if daily_burn_rate > 0 and available_credits > 0:
            depletion_days = available_credits / daily_burn_rate
            projected_depletion_date = datetime.utcnow() + timedelta(days=depletion_days)
        
        return {
            "subscription_id": subscription_id,
            "current_period": {
                "start": subscription.current_period_start.isoformat(),
                "end": subscription.current_period_end.isoformat(),
                "days_elapsed": days_elapsed,
                "days_remaining": max(0, days_in_period - days_elapsed)
            },
            "credit_balance": {
                "current_balance": round(current_balance, 2),
                "included_in_subscription": included_credits,
                "credits_used_this_period": round(credits_used, 2),
                "available_credits": round(available_credits, 2)
            },
            "usage_metrics": {
                "total_transactions": usage_summary.total_transactions,
                "total_cost": round(usage_summary.total_cost, 2),
                "average_cost_per_transaction": round(
                    usage_summary.total_cost / max(1, usage_summary.total_transactions), 4
                )
            },
            "burn_rate_analysis": {
                "daily_burn_rate": round(daily_burn_rate, 2),
                "projected_depletion_date": projected_depletion_date.isoformat() if projected_depletion_date else None,
                "requires_attention": available_credits < (included_credits * 0.1)  # Alert when < 10% remaining
            }
        }
    
    # ============================================================================
    # SUBSCRIPTION PLAN MANAGEMENT
    # ============================================================================
    
    def create_subscription_plan(self, plan_data: SubscriptionPlanCreate) -> SubscriptionPlan:
        """Create a new subscription plan"""
        plan = SubscriptionPlan(**plan_data.dict())
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan
    
    def get_subscription_plan(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID"""
        return self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active == True
        ).first()
    
    def list_subscription_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        """List all subscription plans"""
        query = self.db.query(SubscriptionPlan)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)
        return query.order_by(SubscriptionPlan.monthly_price).all()
    
    # ============================================================================
    # SUBSCRIPTION LIFECYCLE MANAGEMENT
    # ============================================================================
    
    @billing_telemetry("create_subscription")
    def create_subscription(
        self, 
        user_id: int, 
        subscription_data: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription for a user"""
        plan = self.get_subscription_plan(subscription_data.plan_id)
        if not plan:
            raise ValueError("Subscription plan not found")
        
        # Calculate dates
        start_date = datetime.utcnow()
        
        # Trial period
        trial_start = None
        trial_end = None
        if subscription_data.trial_enabled and plan.trial_days > 0:
            trial_start = start_date
            trial_end = start_date + timedelta(days=plan.trial_days)
            status = SubscriptionStatus.TRIALING
            first_billing_date = trial_end
        else:
            status = SubscriptionStatus.ACTIVE
            first_billing_date = start_date
        
        # Calculate period dates based on billing cycle
        period_start, period_end = self._calculate_billing_period(
            first_billing_date,
            subscription_data.billing_cycle
        )
        
        # Calculate base amount
        base_amount = self._get_plan_price(plan, subscription_data.billing_cycle)
        
        # Generate subscription ID
        subscription_id = self._generate_subscription_id()
        
        # Create subscription
        subscription = Subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            plan_id=plan.id,
            status=status,
            billing_cycle=subscription_data.billing_cycle,
            start_date=start_date,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            auto_renew=subscription_data.auto_renew,
            next_billing_date=period_end,
            base_amount=base_amount,
            currency=plan.currency,
            payment_method_id=subscription_data.payment_method_id,
            documents_used_this_period=0,
            api_calls_used_this_period=0,
            additional_users_this_period=0
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            subscription_id=subscription.id,
            event_type="subscription_created",
            description=f"Subscription created for plan {plan.name}",
            new_value={"plan_id": plan.id, "billing_cycle": subscription_data.billing_cycle.value}
        )
        
        # Create initial invoice if not trialing
        if status == SubscriptionStatus.ACTIVE:
            self._create_subscription_invoice(subscription)
        
        # Record subscription creation metrics
        self.record_business_kpi(
            "subscriptions.created.count", 
            1.0,
            {
                "plan_id": str(plan.id),
                "billing_cycle": subscription_data.billing_cycle.value,
                "user_id": str(user_id),
                "has_trial": str(trial_start is not None)
            }
        )
        
        # Record revenue metrics
        if status == SubscriptionStatus.ACTIVE:
            self.record_business_kpi(
                "revenue.monthly_recurring", 
                float(base_amount),
                {"plan_id": str(plan.id), "currency": subscription.currency}
            )
        
        return {
            "subscription": subscription,
            "business_metric": "subscriptions.created.count",
            "metric_value": 1.0
        }
    
    def cancel_subscription(
        self,
        subscription_id: int,
        user_id: int,
        cancel_immediately: bool = False,
        reason: Optional[str] = None
    ) -> Subscription:
        """Cancel a subscription"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        if subscription.status == SubscriptionStatus.CANCELED:
            raise ValueError("Subscription already canceled")
        
        canceled_at = datetime.utcnow()
        
        if cancel_immediately:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.end_date = canceled_at
            subscription.auto_renew = False
        else:
            # Cancel at end of current period
            subscription.auto_renew = False
            subscription.end_date = subscription.current_period_end
        
        subscription.canceled_at = canceled_at
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            subscription_id=subscription.id,
            event_type="subscription_canceled",
            description=f"Subscription canceled. Reason: {reason or 'Not specified'}",
            new_value={"canceled_immediately": cancel_immediately, "reason": reason}
        )
        
        return subscription
    
    def pause_subscription(
        self,
        subscription_id: int,
        user_id: int,
        pause_until: Optional[datetime] = None
    ) -> Subscription:
        """Pause a subscription"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        subscription.status = SubscriptionStatus.PAUSED
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            subscription_id=subscription.id,
            event_type="subscription_paused",
            description="Subscription paused",
            new_value={"pause_until": pause_until.isoformat() if pause_until else None}
        )
        
        return subscription
    
    def resume_subscription(self, subscription_id: int, user_id: int) -> Subscription:
        """Resume a paused subscription"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.PAUSED
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found or not paused")
        
        subscription.status = SubscriptionStatus.ACTIVE
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            subscription_id=subscription.id,
            event_type="subscription_resumed",
            description="Subscription resumed"
        )
        
        return subscription
    
    def upgrade_subscription(
        self,
        subscription_id: int,
        user_id: int,
        new_plan_id: int,
        prorate: bool = True
    ) -> Tuple[Subscription, Optional[float]]:
        """
        Upgrade/downgrade subscription to a different plan
        Returns: (updated_subscription, prorated_amount)
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        new_plan = self.get_subscription_plan(new_plan_id)
        if not new_plan:
            raise ValueError("New plan not found")
        
        old_plan = subscription.plan
        
        # Calculate proration if applicable
        prorated_amount = None
        if prorate:
            prorated_amount = self._calculate_proration(
                subscription,
                old_plan,
                new_plan
            )
        
        # Update subscription
        subscription.plan_id = new_plan_id
        subscription.base_amount = self._get_plan_price(new_plan, subscription.billing_cycle)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            subscription_id=subscription.id,
            event_type="subscription_upgraded",
            description=f"Subscription changed from {old_plan.name} to {new_plan.name}",
            old_value={"plan_id": old_plan.id, "base_amount": self._get_plan_price(old_plan, subscription.billing_cycle)},
            new_value={"plan_id": new_plan.id, "base_amount": subscription.base_amount, "prorated_amount": prorated_amount}
        )
        
        # Create proration invoice if applicable
        if prorated_amount and prorated_amount > 0:
            self._create_proration_invoice(subscription, prorated_amount)
        
        return subscription, prorated_amount
    
    # ============================================================================
    # USAGE TRACKING
    # ============================================================================
    
    def record_usage(
        self,
        subscription_id: int,
        user_id: int,
        resource_type: str,
        quantity: int = 1,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record usage for billing purposes"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Get unit price from plan
        plan = subscription.plan
        unit_price = None
        
        if resource_type == "document":
            unit_price = plan.overage_document_price
            subscription.documents_used_this_period += quantity
        elif resource_type == "api_call":
            unit_price = plan.overage_api_call_price
            subscription.api_calls_used_this_period += quantity
        elif resource_type == "user":
            unit_price = plan.overage_user_price
            subscription.additional_users_this_period += quantity
        
        # Create usage record
        usage_record = UsageRecord(
            subscription_id=subscription_id,
            user_id=user_id,
            resource_type=resource_type,
            quantity=quantity,
            unit_price=unit_price,
            description=description,
            reference_id=reference_id,
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end,
            metadata=metadata
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record
    
    def get_usage_summary(self, subscription_id: int) -> Dict[str, Any]:
        """Get usage summary for a subscription"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        plan = subscription.plan
        
        # Calculate overages
        documents_overage = max(0, subscription.documents_used_this_period - (plan.max_documents_per_month or float('inf')))
        api_calls_overage = max(0, subscription.api_calls_used_this_period - (plan.max_api_calls_per_month or float('inf')))
        users_overage = max(0, subscription.additional_users_this_period - (plan.max_users or float('inf')))
        
        # Calculate overage charges
        documents_overage_charge = documents_overage * plan.overage_document_price
        api_calls_overage_charge = api_calls_overage * plan.overage_api_call_price
        users_overage_charge = users_overage * plan.overage_user_price
        
        total_overage_charge = documents_overage_charge + api_calls_overage_charge + users_overage_charge
        
        return {
            "subscription_id": subscription.subscription_id,
            "period_start": subscription.current_period_start,
            "period_end": subscription.current_period_end,
            "documents": {
                "used": subscription.documents_used_this_period,
                "included": plan.max_documents_per_month,
                "overage": documents_overage,
                "overage_charge": documents_overage_charge
            },
            "api_calls": {
                "used": subscription.api_calls_used_this_period,
                "included": plan.max_api_calls_per_month,
                "overage": api_calls_overage,
                "overage_charge": api_calls_overage_charge
            },
            "users": {
                "used": subscription.additional_users_this_period,
                "included": plan.max_users,
                "overage": users_overage,
                "overage_charge": users_overage_charge
            },
            "total_overage_charge": total_overage_charge
        }
    
    # ============================================================================
    # INVOICE MANAGEMENT
    # ============================================================================
    
    def _create_subscription_invoice(self, subscription: Subscription) -> Invoice:
        """Create invoice for subscription renewal"""
        plan = subscription.plan
        
        # Get usage summary for overage charges
        usage_summary = self.get_usage_summary(subscription.id)
        
        # Build line items
        line_items = [
            {
                "description": f"{plan.name} - {subscription.billing_cycle.value.capitalize()} Subscription",
                "quantity": 1,
                "unit_price": subscription.base_amount,
                "amount": subscription.base_amount
            }
        ]
        
        # Add overage charges
        subtotal = subscription.base_amount
        
        if usage_summary['documents']['overage'] > 0:
            overage_amount = usage_summary['documents']['overage_charge']
            line_items.append({
                "description": f"Document Processing Overage ({usage_summary['documents']['overage']} documents)",
                "quantity": usage_summary['documents']['overage'],
                "unit_price": plan.overage_document_price,
                "amount": overage_amount
            })
            subtotal += overage_amount
        
        if usage_summary['api_calls']['overage'] > 0:
            overage_amount = usage_summary['api_calls']['overage_charge']
            line_items.append({
                "description": f"API Call Overage ({usage_summary['api_calls']['overage']} calls)",
                "quantity": usage_summary['api_calls']['overage'],
                "unit_price": plan.overage_api_call_price,
                "amount": overage_amount
            })
            subtotal += overage_amount
        
        if usage_summary['users']['overage'] > 0:
            overage_amount = usage_summary['users']['overage_charge']
            line_items.append({
                "description": f"Additional User Overage ({usage_summary['users']['overage']} users)",
                "quantity": usage_summary['users']['overage'],
                "unit_price": plan.overage_user_price,
                "amount": overage_amount
            })
            subtotal += overage_amount
        
        # Calculate tax
        tax_rate = self._get_applicable_tax_rate(subscription.user_id)
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # Generate invoice number
        invoice_number = self._generate_invoice_number()
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            status=InvoiceStatus.PENDING,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=0,
            total_amount=total_amount,
            amount_paid=0,
            amount_due=total_amount,
            currency=subscription.currency,
            line_items=line_items,
            due_date=subscription.current_period_end,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            tax_rate=tax_rate
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        
        # Log event
        self._log_billing_event(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            invoice_id=invoice.id,
            event_type="invoice_created",
            description=f"Invoice {invoice_number} created",
            new_value={"invoice_id": invoice.id, "amount": total_amount}
        )
        
        return invoice
    
    def _create_proration_invoice(self, subscription: Subscription, prorated_amount: float) -> Invoice:
        """Create invoice for proration charges"""
        invoice_number = self._generate_invoice_number()
        
        line_items = [{
            "description": "Plan Change Proration",
            "quantity": 1,
            "unit_price": prorated_amount,
            "amount": prorated_amount
        }]
        
        tax_rate = self._get_applicable_tax_rate(subscription.user_id)
        tax_amount = prorated_amount * tax_rate
        total_amount = prorated_amount + tax_amount
        
        invoice = Invoice(
            invoice_number=invoice_number,
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            status=InvoiceStatus.PENDING,
            subtotal=prorated_amount,
            tax_amount=tax_amount,
            discount_amount=0,
            total_amount=total_amount,
            amount_paid=0,
            amount_due=total_amount,
            currency=subscription.currency,
            line_items=line_items,
            due_date=datetime.utcnow() + timedelta(days=7),
            tax_rate=tax_rate
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        
        return invoice
    
    def get_invoice(self, invoice_id: int, user_id: int) -> Optional[Invoice]:
        """Get invoice by ID"""
        return self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.user_id == user_id
        ).first()
    
    def list_invoices(
        self,
        user_id: int,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50
    ) -> List[Invoice]:
        """List invoices for a user"""
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)
        
        if status:
            query = query.filter(Invoice.status == status)
        
        return query.order_by(Invoice.created_at.desc()).limit(limit).all()
    
    # ============================================================================
    # PAYMENT PROCESSING
    # ============================================================================
    
    def process_payment(
        self,
        invoice_id: int,
        user_id: int,
        payment_method: PaymentMethod,
        payment_method_id: Optional[int] = None,
        transaction_id: Optional[str] = None
    ) -> Payment:
        """Process a payment for an invoice"""
        invoice = self.get_invoice(invoice_id, user_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Invoice already paid")
        
        payment_id = self._generate_payment_id()
        
        payment = Payment(
            payment_id=payment_id,
            invoice_id=invoice_id,
            user_id=user_id,
            payment_method_id=payment_method_id,
            amount=invoice.amount_due,
            currency=invoice.currency,
            status=PaymentStatus.PROCESSING,
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Simulate payment processing (in production, integrate with payment gateway)
        payment.status = PaymentStatus.SUCCEEDED
        payment.processed_at = datetime.utcnow()
        
        # Update invoice
        invoice.amount_paid = invoice.amount_due
        invoice.amount_due = 0
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        
        self.db.commit()
        
        # Log event
        self._log_billing_event(
            user_id=user_id,
            invoice_id=invoice_id,
            payment_id=payment.id,
            event_type="payment_succeeded",
            description=f"Payment of {payment.amount} {payment.currency} succeeded",
            new_value={"payment_id": payment.id, "amount": payment.amount}
        )
        
        return payment
    
    # ============================================================================
    # ANALYTICS
    # ============================================================================
    
    def get_billing_analytics(self) -> Dict[str, Any]:
        """Get comprehensive billing analytics"""
        # Active subscriptions
        active_subscriptions = self.db.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).scalar()
        
        # Trialing subscriptions
        trialing_subscriptions = self.db.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.TRIALING
        ).scalar()
        
        # Canceled subscriptions (this month)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        canceled_subscriptions = self.db.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.CANCELED,
            Subscription.canceled_at >= month_start
        ).scalar()
        
        # MRR (Monthly Recurring Revenue)
        mrr = self.db.query(func.sum(Subscription.base_amount)).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.billing_cycle == BillingCycle.MONTHLY
        ).scalar() or 0
        
        # Add quarterly and annual as monthly equivalent
        quarterly_mrr = (self.db.query(func.sum(Subscription.base_amount)).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.billing_cycle == BillingCycle.QUARTERLY
        ).scalar() or 0) / 3
        
        annual_mrr = (self.db.query(func.sum(Subscription.base_amount)).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.billing_cycle == BillingCycle.ANNUALLY
        ).scalar() or 0) / 12
        
        total_mrr = mrr + quarterly_mrr + annual_mrr
        arr = total_mrr * 12
        
        # Total revenue (paid invoices)
        total_revenue = self.db.query(func.sum(Invoice.amount_paid)).filter(
            Invoice.status == InvoiceStatus.PAID
        ).scalar() or 0
        
        # Invoice stats
        total_invoices = self.db.query(func.count(Invoice.id)).scalar()
        paid_invoices = self.db.query(func.count(Invoice.id)).filter(
            Invoice.status == InvoiceStatus.PAID
        ).scalar()
        
        outstanding_amount = self.db.query(func.sum(Invoice.amount_due)).filter(
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE])
        ).scalar() or 0
        
        overdue_invoices = self.db.query(func.count(Invoice.id)).filter(
            Invoice.status == InvoiceStatus.OVERDUE
        ).scalar()
        
        # ARPU (Average Revenue Per User)
        total_users = self.db.query(func.count(func.distinct(Subscription.user_id))).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
        ).scalar() or 1
        
        arpu = total_revenue / total_users if total_users > 0 else 0
        
        # Churn rate (canceled / (active + canceled))
        total_subs = active_subscriptions + canceled_subscriptions
        churn_rate = (canceled_subscriptions / total_subs * 100) if total_subs > 0 else 0
        
        return {
            "total_revenue": round(total_revenue, 2),
            "monthly_recurring_revenue": round(total_mrr, 2),
            "annual_recurring_revenue": round(arr, 2),
            "active_subscriptions": active_subscriptions,
            "trialing_subscriptions": trialing_subscriptions,
            "canceled_subscriptions": canceled_subscriptions,
            "churn_rate": round(churn_rate, 2),
            "average_revenue_per_user": round(arpu, 2),
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
            "outstanding_amount": round(outstanding_amount, 2),
            "overdue_invoices": overdue_invoices
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _calculate_billing_period(
        self,
        start_date: datetime,
        billing_cycle: BillingCycle
    ) -> Tuple[datetime, datetime]:
        """Calculate billing period start and end dates"""
        period_start = start_date
        
        if billing_cycle == BillingCycle.MONTHLY:
            period_end = period_start + relativedelta(months=1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            period_end = period_start + relativedelta(months=3)
        elif billing_cycle == BillingCycle.ANNUALLY:
            period_end = period_start + relativedelta(years=1)
        else:
            period_end = period_start + relativedelta(months=1)
        
        return period_start, period_end
    
    def _get_plan_price(self, plan: SubscriptionPlan, billing_cycle: BillingCycle) -> float:
        """Get plan price based on billing cycle"""
        if billing_cycle == BillingCycle.MONTHLY:
            return plan.monthly_price
        elif billing_cycle == BillingCycle.QUARTERLY:
            return plan.quarterly_price or (plan.monthly_price * 3)
        elif billing_cycle == BillingCycle.ANNUALLY:
            return plan.annual_price or (plan.monthly_price * 12)
        return plan.monthly_price
    
    def _calculate_proration(
        self,
        subscription: Subscription,
        old_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan
    ) -> float:
        """Calculate proration amount for plan change"""
        # Calculate remaining days in current period
        now = datetime.utcnow()
        total_days = (subscription.current_period_end - subscription.current_period_start).days
        remaining_days = (subscription.current_period_end - now).days
        
        # Calculate unused amount from old plan
        old_price = self._get_plan_price(old_plan, subscription.billing_cycle)
        unused_amount = (old_price / total_days) * remaining_days
        
        # Calculate new plan cost for remaining period
        new_price = self._get_plan_price(new_plan, subscription.billing_cycle)
        new_period_cost = (new_price / total_days) * remaining_days
        
        # Proration is the difference
        proration = max(0, new_period_cost - unused_amount)
        
        return round(proration, 2)
    
    def _get_applicable_tax_rate(self, user_id: int) -> float:
        """Get applicable tax rate for user (simplified)"""
        # In production, this would check user's location and apply appropriate tax
        # For now, return default EU VAT rate
        return 0.23  # 23% VAT (Portuguese rate)
    
    def _generate_subscription_id(self) -> str:
        """Generate unique subscription ID"""
        return f"sub_{secrets.token_hex(16)}"
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        year = datetime.utcnow().year
        month = datetime.utcnow().month
        count = self.db.query(func.count(Invoice.id)).filter(
            func.extract('year', Invoice.created_at) == year,
            func.extract('month', Invoice.created_at) == month
        ).scalar() + 1
        return f"INV-{year}{month:02d}-{count:05d}"
    
    def _generate_payment_id(self) -> str:
        """Generate unique payment ID"""
        return f"pay_{secrets.token_hex(16)}"
    
    def _log_billing_event(
        self,
        user_id: int,
        event_type: str,
        description: str,
        subscription_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None
    ):
        """Log billing event for audit trail"""
        event = BillingEvent(
            user_id=user_id,
            subscription_id=subscription_id,
            invoice_id=invoice_id,
            payment_id=payment_id,
            event_type=event_type,
            description=description,
            old_value=old_value,
            new_value=new_value
        )
        self.db.add(event)
        self.db.commit()
