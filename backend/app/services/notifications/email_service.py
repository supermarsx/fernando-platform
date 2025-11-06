"""
Email Notification Service
Handles email templates, delivery, and management
"""

import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import json
from dataclasses import dataclass
import jinja2

from app.models.notifications import EmailNotification, EmailTemplate, Notification
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class EmailConfiguration:
    """Email service configuration"""
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_address: str = "noreply@fernandoplatform.com"
    from_name: str = "Fernando Platform"
    max_retries: int = 3
    retry_delay: int = 60  # seconds

class EmailService:
    """Handles email notification delivery and management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = self._load_email_configuration()
        self.jinja_env = jinja2.Environment(
            loader=jinja2.DictLoader({}),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Default templates
        self._setup_default_templates()
        
        # SMTP connection pool (simplified)
        self.smtp_pool = []
        self.max_pool_size = 5
    
    def _load_email_configuration(self) -> EmailConfiguration:
        """Load email service configuration"""
        return EmailConfiguration(
            smtp_host=getattr(settings, 'SMTP_HOST', 'smtp.gmail.com'),
            smtp_port=getattr(settings, 'SMTP_PORT', 587),
            username=getattr(settings, 'SMTP_USERNAME', ''),
            password=getattr(settings, 'SMTP_PASSWORD', ''),
            use_tls=getattr(settings, 'SMTP_USE_TLS', True),
            use_ssl=getattr(settings, 'SMTP_USE_SSL', False),
            from_address=getattr(settings, 'EMAIL_FROM_ADDRESS', 'noreply@fernandoplatform.com'),
            from_name=getattr(settings, 'EMAIL_FROM_NAME', 'Fernando Platform')
        )
    
    def _setup_default_templates(self):
        """Setup default email templates"""
        
        # Welcome email template
        welcome_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to Fernando Platform</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }
        .header { text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }
        .content { line-height: 1.6; color: #333; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Fernando Platform! 🎉</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            <p>Welcome to the Fernando Platform! We're excited to have you join our community of users.</p>
            
            <p>Here's what you can do with your account:</p>
            <ul>
                <li>Upload and process accounting documents</li>
                <li>Access AI-powered verification workflows</li>
                <li>Manage your subscription and billing</li>
                <li>Track your usage and analytics</li>
            </ul>
            
            <p><a href="{{ dashboard_url }}" class="button">Go to Dashboard</a></p>
            
            <p>If you have any questions, our support team is here to help!</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The Fernando Platform Team</p>
            <p><small>This email was sent to {{ user_email }}. If you didn't create an account, please contact support.</small></p>
        </div>
    </div>
</body>
</html>
        """
        
        # Document processing notification template
        document_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Document Processing Update</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }
        .header { text-align: center; border-bottom: 2px solid #28a745; padding-bottom: 20px; margin-bottom: 30px; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .content { line-height: 1.6; color: #333; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }
        .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
        .status-completed { background-color: #d4edda; color: #155724; }
        .status-failed { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Document Processing Update 📄</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            <p>Your document has been processed with the following results:</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Document Details</h3>
                <p><strong>Document ID:</strong> {{ document_id }}</p>
                <p><strong>Document Type:</strong> {{ document_type }}</p>
                <p><strong>Status:</strong> <span class="status-badge status-{{ status_class }}">{{ status }}</span></p>
                
                {% if processing_time %}
                <p><strong>Processing Time:</strong> {{ processing_time }}ms</p>
                {% endif %}
                
                {% if confidence_score %}
                <p><strong>Confidence Score:</strong> {{ confidence_score }}%</p>
                {% endif %}
                
                {% if error_message %}
                <p><strong>Error:</strong> <span class="error">{{ error_message }}</span></p>
                {% endif %}
            </div>
            
            <p><a href="{{ dashboard_url }}/documents/{{ document_id }}" class="button">View Document</a></p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The Fernando Platform Team</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Payment notification template
        payment_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Payment Notification</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }
        .header { text-align: center; border-bottom: 2px solid #17a2b8; padding-bottom: 20px; margin-bottom: 30px; }
        .content { line-height: 1.6; color: #333; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }
        .amount { font-size: 24px; font-weight: bold; color: #28a745; }
        .payment-success { color: #28a745; }
        .payment-failed { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Payment Notification 💳</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            
            {% if payment_status == 'success' %}
            <p class="payment-success">✅ Your payment has been processed successfully!</p>
            {% elif payment_status == 'failed' %}
            <p class="payment-failed">❌ Your payment could not be processed.</p>
            {% endif %}
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Payment Details</h3>
                <p><strong>Amount:</strong> <span class="amount">{{ amount }} {{ currency }}</span></p>
                <p><strong>Payment ID:</strong> {{ payment_id }}</p>
                <p><strong>Date:</strong> {{ payment_date }}</p>
                <p><strong>Method:</strong> {{ payment_method }}</p>
                
                {% if subscription_id %}
                <p><strong>Subscription:</strong> {{ subscription_id }}</p>
                {% endif %}
                
                {% if failure_reason %}
                <p><strong>Failure Reason:</strong> {{ failure_reason }}</p>
                {% endif %}
            </div>
            
            {% if payment_status == 'success' %}
            <p>Thank you for your payment! Your service continues uninterrupted.</p>
            {% else %}
            <p>Please update your payment information to continue using our services.</p>
            <p><a href="{{ billing_url }}" class="button">Update Payment</a></p>
            {% endif %}
        </div>
        <div class="footer">
            <p>Best regards,<br>The Fernando Platform Team</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Store templates
        self.templates = {
            "welcome": welcome_template,
            "document_processing": document_template,
            "payment_notification": payment_template
        }
    
    async def send_email(
        self,
        user_id: str,
        subject: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        to_email: Optional[str] = None,
        from_email: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email notification"""
        
        try:
            # Get user email if not provided
            if not to_email:
                to_email = await self._get_user_email(user_id)
                if not to_email:
                    raise ValueError(f"Could not find email address for user {user_id}")
            
            # Prepare email content
            email_content = await self._prepare_email_content(
                template_id, subject, message, data or {}
            )
            
            # Create email record
            email_record = EmailNotification(
                id=f"email_{user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=user_id,
                to_email=to_email,
                subject=email_content["subject"],
                body_text=email_content["text"],
                body_html=email_content["html"],
                template_id=template_id,
                status="pending",
                created_at=datetime.utcnow(),
                retry_count=0
            )
            
            self.db.add(email_record)
            self.db.commit()
            
            # Send email
            result = await self._send_smtp_email(
                to_email,
                email_content["subject"],
                email_content["html"],
                email_content["text"],
                attachments,
                from_email
            )
            
            # Update status
            if result["success"]:
                email_record.status = "sent"
                email_record.sent_at = datetime.utcnow()
                email_record.message_id = result.get("message_id")
            else:
                email_record.status = "failed"
                email_record.error_message = result["error"]
            
            self.db.commit()
            
            logger.info(f"Email sent to {to_email}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}
    
    async def _prepare_email_content(
        self,
        template_id: Optional[str],
        subject: str,
        message: str,
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare email content using template or plain text"""
        
        # Default context data
        context = {
            "user_name": data.get("user_name", "User"),
            "user_email": data.get("user_email", ""),
            "dashboard_url": getattr(settings, 'FRONTEND_URL', 'https://dashboard.fernandoplatform.com'),
            "billing_url": getattr(settings, 'FRONTEND_URL', 'https://dashboard.fernandoplatform.com') + "/billing"
        }
        
        # Add template-specific context
        context.update(data)
        
        if template_id and template_id in self.templates:
            # Use template
            template = self.jinja_env.from_string(self.templates[template_id])
            html_content = template.render(context)
            
            # Generate plain text version (simplified)
            text_content = self._html_to_text(html_content)
            
        else:
            # Use plain text
            html_content = self._format_plain_text_as_html(message, context)
            text_content = message
        
        return {
            "subject": subject,
            "html": html_content,
            "text": text_content
        }
    
    async def _send_smtp_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP"""
        
        try:
            # Prepare message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.config.from_address
            msg['To'] = to_email
            
            # Add text part
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            await self._smtp_send(msg)
            
            return {
                "success": True,
                "to": to_email,
                "subject": subject,
                "message_id": msg.get('Message-ID')
            }
            
        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _smtp_send(self, msg: MIMEMultipart):
        """Send email via SMTP with connection management"""
        
        # Get or create SMTP connection
        smtp_server = await self._get_smtp_connection()
        
        try:
            # Send email
            smtp_server.send_message(msg)
            
        finally:
            # Return connection to pool or close
            await self._return_smtp_connection(smtp_server)
    
    async def _get_smtp_connection(self):
        """Get SMTP connection from pool"""
        
        if self.smtp_pool:
            return self.smtp_pool.pop()
        
        # Create new connection
        return await self._create_smtp_connection()
    
    async def _create_smtp_connection(self):
        """Create new SMTP connection"""
        
        if self.config.use_ssl:
            context = ssl.create_default_context()
            return smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                context=context
            )
        else:
            server = smtplib.SMTP(
                self.config.smtp_host,
                self.config.smtp_port
            )
            server.starttls()
            return server
    
    async def _return_smtp_connection(self, server):
        """Return SMTP connection to pool"""
        
        if len(self.smtp_pool) < self.max_pool_size:
            self.smtp_pool.append(server)
        else:
            try:
                server.quit()
            except:
                pass
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message"""
        
        filename = attachment.get("filename", "attachment")
        content = attachment.get("content", "")
        content_type = attachment.get("content_type", "application/octet-stream")
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(content.encode('utf-8') if isinstance(content, str) else content)
        encoders.encode_base64(part)
        
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}'
        )
        
        msg.attach(part)
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        
        import re
        # Simple HTML to text conversion
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _format_plain_text_as_html(self, message: str, context: Dict[str, Any]) -> str:
        """Format plain text message as HTML"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Notification</title>
        </head>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px;">
                    <h1>Fernando Platform</h1>
                </div>
                <div style="line-height: 1.6; color: #333;">
                    <p>Hello {context.get('user_name', 'User')},</p>
                    <div style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 5px;">
                        {message.replace(chr(10), '<br>')}
                    </div>
                    <p>Best regards,<br>The Fernando Platform Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user's email address"""
        
        from app.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.email if user else None
    
    async def send_bulk_emails(
        self,
        email_list: List[Dict[str, Any]],
        template_id: Optional[str] = None,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Send bulk emails efficiently"""
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        # Process in batches
        for i in range(0, len(email_list), batch_size):
            batch = email_list[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = []
            for email_data in batch:
                task = asyncio.create_task(
                    self.send_email(
                        user_id=email_data["user_id"],
                        subject=email_data["subject"],
                        message=email_data["message"],
                        data=email_data.get("data", {}),
                        template_id=template_id,
                        to_email=email_data.get("to_email")
                    )
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    logger.error(f"Bulk email error: {result}")
                elif result.get("success", False):
                    results["success"] += 1
                else:
                    results["failed"] += 1
        
        return results
    
    async def create_email_template(
        self,
        name: str,
        subject: str,
        html_template: str,
        text_template: Optional[str] = None,
        variables: Optional[List[str]] = None
    ) -> EmailTemplate:
        """Create a new email template"""
        
        template = EmailTemplate(
            id=f"template_{name}_{int(datetime.utcnow().timestamp())}",
            name=name,
            subject=subject,
            html_content=html_template,
            text_content=text_template,
            variables=variables or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(template)
        self.db.commit()
        
        # Add to template cache
        self.templates[name] = html_template
        
        logger.info(f"Created email template: {name}")
        return template
    
    async def get_email_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get email delivery statistics"""
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query conditions
        conditions = [
            EmailNotification.created_at >= start_date,
            EmailNotification.created_at <= end_date
        ]
        
        # Basic counts
        total_emails = self.db.query(func.count(EmailNotification.id)).filter(
            and_(*conditions)
        ).scalar() or 0
        
        sent_emails = self.db.query(func.count(EmailNotification.id)).filter(
            and_(*conditions, EmailNotification.status == 'sent')
        ).scalar() or 0
        
        failed_emails = self.db.query(func.count(EmailNotification.id)).filter(
            and_(*conditions, EmailNotification.status == 'failed')
        ).scalar() or 0
        
        # Template usage
        template_usage = self.db.query(
            EmailNotification.template_id,
            func.count(EmailNotification.id).label('count')
        ).filter(
            and_(*conditions, EmailNotification.template_id.isnot(None))
        ).group_by(
            EmailNotification.template_id
        ).all()
        
        template_stats = {usage.template_id or 'plain': usage.count for usage in template_usage}
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_emails": total_emails,
            "sent_emails": sent_emails,
            "failed_emails": failed_emails,
            "success_rate": round((sent_emails / total_emails * 100), 2) if total_emails > 0 else 0,
            "template_usage": template_stats
        }
    
    async def validate_email_deliverability(self, email_address: str) -> Dict[str, Any]:
        """Validate if email address is deliverable"""
        
        try:
            # Basic email format validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            if not re.match(email_pattern, email_address):
                return {
                    "valid": False,
                    "reason": "Invalid email format",
                    "deliverable": False
                }
            
            # Extract domain
            domain = email_address.split('@')[1]
            
            # Check if domain has MX records (simplified)
            # In production, you might want to use a proper DNS lookup
            deliverable = domain.lower() not in [
                'mailinator.com',
                '10minutemail.com',
                'tempmail.org'
            ]
            
            return {
                "valid": True,
                "reason": "Email format valid",
                "deliverable": deliverable
            }
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "deliverable": False
            }
    
    async def cleanup_old_emails(self, days_to_keep: int = 90) -> int:
        """Clean up old email records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(EmailNotification).filter(
            EmailNotification.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old email records")
        return deleted_count
    
    async def shutdown(self):
        """Shutdown email service"""
        
        # Close SMTP connections
        for server in self.smtp_pool:
            try:
                server.quit()
            except:
                pass
        
        self.smtp_pool.clear()
        logger.info("Email service shutdown complete")