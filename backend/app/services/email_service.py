"""
Email Notification Service

Handles automated email notifications for billing events including:
- Invoice notifications
- Payment confirmations
- Payment failures
- Subscription updates
- Trial expiration reminders
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jinja2 import Template

from app.core.config import settings
from app.models.billing import Invoice, Payment, Subscription, SubscriptionPlan


class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
        self.enabled = settings.EMAIL_NOTIFICATIONS_ENABLED
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """Send an email via SMTP"""
        if not self.enabled:
            print(f"[EMAIL DISABLED] Would send: {subject} to {to_email}")
            return True
        
        if not self.smtp_user or not self.smtp_password:
            print("[EMAIL] SMTP credentials not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"[EMAIL] Sent: {subject} to {to_email}")
            return True
        
        except Exception as e:
            print(f"[EMAIL] Failed to send email: {e}")
            return False
    
    # ============================================================================
    # INVOICE NOTIFICATIONS
    # ============================================================================
    
    def send_invoice_created(
        self,
        user_email: str,
        user_name: str,
        invoice: Invoice
    ) -> bool:
        """Send notification when new invoice is created"""
        subject = f"New Invoice {invoice.invoice_number}"
        
        html_body = self._render_invoice_created_template(user_name, invoice)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_invoice_paid(
        self,
        user_email: str,
        user_name: str,
        invoice: Invoice,
        payment: Payment
    ) -> bool:
        """Send confirmation when invoice is paid"""
        subject = f"Payment Confirmation - Invoice {invoice.invoice_number}"
        
        html_body = self._render_invoice_paid_template(user_name, invoice, payment)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_invoice_overdue(
        self,
        user_email: str,
        user_name: str,
        invoice: Invoice
    ) -> bool:
        """Send reminder when invoice is overdue"""
        subject = f"Overdue Invoice Reminder - {invoice.invoice_number}"
        
        html_body = self._render_invoice_overdue_template(user_name, invoice)
        
        return self.send_email(user_email, subject, html_body)
    
    # ============================================================================
    # PAYMENT NOTIFICATIONS
    # ============================================================================
    
    def send_payment_failed(
        self,
        user_email: str,
        user_name: str,
        invoice: Invoice,
        payment: Payment
    ) -> bool:
        """Send notification when payment fails"""
        subject = f"Payment Failed - Invoice {invoice.invoice_number}"
        
        html_body = self._render_payment_failed_template(user_name, invoice, payment)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_payment_refunded(
        self,
        user_email: str,
        user_name: str,
        payment: Payment,
        refund_amount: float
    ) -> bool:
        """Send notification when payment is refunded"""
        subject = f"Refund Processed - {refund_amount} {payment.currency}"
        
        html_body = self._render_payment_refunded_template(user_name, payment, refund_amount)
        
        return self.send_email(user_email, subject, html_body)
    
    # ============================================================================
    # SUBSCRIPTION NOTIFICATIONS
    # ============================================================================
    
    def send_subscription_created(
        self,
        user_email: str,
        user_name: str,
        subscription: Subscription,
        plan: SubscriptionPlan
    ) -> bool:
        """Send welcome email when subscription is created"""
        subject = f"Welcome to {plan.name}!"
        
        html_body = self._render_subscription_created_template(user_name, subscription, plan)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_trial_ending_soon(
        self,
        user_email: str,
        user_name: str,
        subscription: Subscription,
        days_remaining: int
    ) -> bool:
        """Send reminder when trial is ending soon"""
        subject = f"Your trial ends in {days_remaining} days"
        
        html_body = self._render_trial_ending_template(user_name, subscription, days_remaining)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_subscription_renewed(
        self,
        user_email: str,
        user_name: str,
        subscription: Subscription,
        plan: SubscriptionPlan
    ) -> bool:
        """Send notification when subscription is renewed"""
        subject = f"Subscription Renewed - {plan.name}"
        
        html_body = self._render_subscription_renewed_template(user_name, subscription, plan)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_subscription_canceled(
        self,
        user_email: str,
        user_name: str,
        subscription: Subscription,
        plan: SubscriptionPlan
    ) -> bool:
        """Send confirmation when subscription is canceled"""
        subject = "Subscription Cancellation Confirmed"
        
        html_body = self._render_subscription_canceled_template(user_name, subscription, plan)
        
        return self.send_email(user_email, subject, html_body)
    
    def send_subscription_upgraded(
        self,
        user_email: str,
        user_name: str,
        subscription: Subscription,
        old_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan
    ) -> bool:
        """Send notification when subscription is upgraded"""
        subject = f"Subscription Upgraded to {new_plan.name}"
        
        html_body = self._render_subscription_upgraded_template(user_name, subscription, old_plan, new_plan)
        
        return self.send_email(user_email, subject, html_body)
    
    # ============================================================================
    # EMAIL TEMPLATES
    # ============================================================================
    
    def _render_invoice_created_template(self, user_name: str, invoice: Invoice) -> str:
        """Render invoice created email template"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #667eea; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .invoice-details { background: white; padding: 15px; margin: 15px 0; }
                .amount { font-size: 24px; font-weight: bold; color: #667eea; }
                .button { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Invoice</h1>
                </div>
                <div class="content">
                    <p>Hello {{ user_name }},</p>
                    <p>A new invoice has been generated for your account.</p>
                    
                    <div class="invoice-details">
                        <p><strong>Invoice Number:</strong> {{ invoice.invoice_number }}</p>
                        <p><strong>Issue Date:</strong> {{ invoice.issue_date.strftime('%B %d, %Y') }}</p>
                        <p><strong>Due Date:</strong> {{ invoice.due_date.strftime('%B %d, %Y') }}</p>
                        <p><strong>Amount Due:</strong> <span class="amount">{{ invoice.total_amount }} {{ invoice.currency }}</span></p>
                    </div>
                    
                    <a href="https://app.fernando.com/invoices/{{ invoice.id }}" class="button">View Invoice</a>
                    
                    <p>Please ensure payment is made by the due date to avoid service interruption.</p>
                </div>
                <div class="footer">
                    <p>Fernando Platform | support@fernando.com</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return template.render(user_name=user_name, invoice=invoice)
    
    def _render_invoice_paid_template(self, user_name: str, invoice: Invoice, payment: Payment) -> str:
        """Render invoice paid confirmation email template"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #48bb78; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .payment-details { background: white; padding: 15px; margin: 15px 0; }
                .success-icon { font-size: 48px; text-align: center; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Successful</h1>
                </div>
                <div class="content">
                    <div class="success-icon">✓</div>
                    <p>Hello {{ user_name }},</p>
                    <p>Thank you! Your payment has been processed successfully.</p>
                    
                    <div class="payment-details">
                        <p><strong>Invoice:</strong> {{ invoice.invoice_number }}</p>
                        <p><strong>Amount Paid:</strong> {{ payment.amount }} {{ payment.currency }}</p>
                        <p><strong>Payment Date:</strong> {{ payment.processed_at.strftime('%B %d, %Y') }}</p>
                        <p><strong>Payment ID:</strong> {{ payment.payment_id }}</p>
                    </div>
                    
                    <p>A receipt has been sent to your email address.</p>
                </div>
                <div class="footer">
                    <p>Fernando Platform | support@fernando.com</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return template.render(user_name=user_name, invoice=invoice, payment=payment)
    
    def _render_payment_failed_template(self, user_name: str, invoice: Invoice, payment: Payment) -> str:
        """Render payment failed email template"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #f56565; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .button { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Failed</h1>
                </div>
                <div class="content">
                    <p>Hello {{ user_name }},</p>
                    <p>We were unable to process your payment for invoice {{ invoice.invoice_number }}.</p>
                    
                    <p><strong>Reason:</strong> {{ payment.failure_reason }}</p>
                    <p><strong>Amount:</strong> {{ invoice.amount_due }} {{ invoice.currency }}</p>
                    
                    <a href="https://app.fernando.com/invoices/{{ invoice.id }}" class="button">Retry Payment</a>
                    
                    <p>Please update your payment method or try again.</p>
                </div>
                <div class="footer">
                    <p>Fernando Platform | support@fernando.com</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return template.render(user_name=user_name, invoice=invoice, payment=payment)
    
    def _render_subscription_created_template(self, user_name: str, subscription: Subscription, plan: SubscriptionPlan) -> str:
        """Render subscription created welcome email"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #667eea; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {{ plan.name }}!</h1>
                </div>
                <div class="content">
                    <p>Hello {{ user_name }},</p>
                    <p>Thank you for subscribing to {{ plan.name }}. Your subscription is now active!</p>
                    
                    <h3>Your Plan Details:</h3>
                    <ul>
                        {% if subscription.trial_end %}
                        <li><strong>Trial Period:</strong> Until {{ subscription.trial_end.strftime('%B %d, %Y') }}</li>
                        {% endif %}
                        <li><strong>Billing Cycle:</strong> {{ subscription.billing_cycle }}</li>
                        <li><strong>Next Billing Date:</strong> {{ subscription.next_billing_date.strftime('%B %d, %Y') }}</li>
                        <li><strong>Amount:</strong> {{ subscription.base_amount }} {{ subscription.currency }}</li>
                    </ul>
                    
                    <p>Start using your new features today!</p>
                </div>
                <div class="footer">
                    <p>Fernando Platform | support@fernando.com</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return template.render(user_name=user_name, subscription=subscription, plan=plan)
    
    def _render_trial_ending_template(self, user_name: str, subscription: Subscription, days_remaining: int) -> str:
        """Render trial ending reminder email"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your Trial Ends Soon</h1>
                </div>
                <div class="content">
                    <p>Hello {{ user_name }},</p>
                    <p>Your trial period will end in <strong>{{ days_remaining }} days</strong>.</p>
                    <p>To continue enjoying our services, make sure your payment method is up to date.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        return template.render(user_name=user_name, subscription=subscription, days_remaining=days_remaining)
    
    # Placeholder templates for other methods
    def _render_invoice_overdue_template(self, user_name: str, invoice: Invoice) -> str:
        return f"<html><body><p>Hello {user_name}, your invoice {invoice.invoice_number} is overdue.</p></body></html>"
    
    def _render_payment_refunded_template(self, user_name: str, payment: Payment, refund_amount: float) -> str:
        return f"<html><body><p>Hello {user_name}, a refund of {refund_amount} {payment.currency} has been processed.</p></body></html>"
    
    def _render_subscription_renewed_template(self, user_name: str, subscription: Subscription, plan: SubscriptionPlan) -> str:
        return f"<html><body><p>Hello {user_name}, your {plan.name} subscription has been renewed.</p></body></html>"
    
    def _render_subscription_canceled_template(self, user_name: str, subscription: Subscription, plan: SubscriptionPlan) -> str:
        return f"<html><body><p>Hello {user_name}, your subscription has been canceled.</p></body></html>"
    
    def _render_subscription_upgraded_template(self, user_name: str, subscription: Subscription, old_plan: SubscriptionPlan, new_plan: SubscriptionPlan) -> str:
        return f"<html><body><p>Hello {user_name}, your subscription has been upgraded from {old_plan.name} to {new_plan.name}.</p></body></html>"


# ============================================================================
# NOTIFICATION TRIGGERS
# ============================================================================

class BillingNotificationService:
    """Service to trigger billing notifications"""
    
    def __init__(self, db):
        self.db = db
        self.email_service = EmailService()
    
    def notify_invoice_created(self, invoice: Invoice):
        """Send notification when invoice is created"""
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == invoice.user_id).first()
        if user:
            self.email_service.send_invoice_created(
                user_email=user.email,
                user_name=user.full_name,
                invoice=invoice
            )
    
    def notify_invoice_paid(self, invoice: Invoice, payment: Payment):
        """Send notification when invoice is paid"""
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == invoice.user_id).first()
        if user:
            self.email_service.send_invoice_paid(
                user_email=user.email,
                user_name=user.full_name,
                invoice=invoice,
                payment=payment
            )
    
    def notify_payment_failed(self, invoice: Invoice, payment: Payment):
        """Send notification when payment fails"""
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == invoice.user_id).first()
        if user:
            self.email_service.send_payment_failed(
                user_email=user.email,
                user_name=user.full_name,
                invoice=invoice,
                payment=payment
            )
    
    def notify_subscription_created(self, subscription: Subscription):
        """Send welcome email when subscription is created"""
        from app.models.user import User
        user = self.db.query(User).filter(User.user_id == subscription.user_id).first()
        plan = subscription.plan
        if user and plan:
            self.email_service.send_subscription_created(
                user_email=user.email,
                user_name=user.full_name,
                subscription=subscription,
                plan=plan
            )
    
    def check_and_notify_trial_ending(self):
        """Check for trials ending soon and send reminders"""
        from app.models.user import User
        
        # Find subscriptions with trials ending in 3 days
        three_days_from_now = datetime.utcnow() + timedelta(days=3)
        
        subscriptions = self.db.query(Subscription).filter(
            Subscription.status == 'trialing',
            Subscription.trial_end <= three_days_from_now,
            Subscription.trial_end >= datetime.utcnow()
        ).all()
        
        for subscription in subscriptions:
            user = self.db.query(User).filter(User.user_id == subscription.user_id).first()
            if user:
                days_remaining = (subscription.trial_end - datetime.utcnow()).days
                self.email_service.send_trial_ending_soon(
                    user_email=user.email,
                    user_name=user.full_name,
                    subscription=subscription,
                    days_remaining=days_remaining
                )
