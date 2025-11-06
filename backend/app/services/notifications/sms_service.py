"""
SMS Notification Service
Handles SMS notifications via Twilio and other providers
"""

import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import json
from dataclasses import dataclass
import httpx

from app.models.notifications import SMSNotification, UserPhoneNumber
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class SMSProvider:
    """SMS provider configuration"""
    name: str
    api_url: str
    api_key: str
    from_number: str
    enabled: bool = True
    rate_limit_per_minute: int = 100
    max_message_length: int = 1600

@dataclass
class SMSMessage:
    """SMS message structure"""
    to: str
    from_number: str
    message: str
    message_type: str = "text"
    priority: str = "normal"
    delivery_receipt: bool = True

class SMSService:
    """Handles SMS notification delivery and management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.providers = self._load_sms_providers()
        self.message_templates = self._load_message_templates()
        self.rate_limits = {}  # Simple in-memory rate limiting
        
        # Message queue for async processing
        self.message_queue = asyncio.Queue(maxsize=500)
        self.processing_task = None
        self.start_processing()
    
    def _load_sms_providers(self) -> List[SMSProvider]:
        """Load SMS provider configurations"""
        
        providers = []
        
        # Twilio configuration
        twilio_enabled = getattr(settings, 'TWILIO_ENABLED', False)
        if twilio_enabled:
            providers.append(SMSProvider(
                name="twilio",
                api_url="https://api.twilio.com/2010-04-01",
                api_key=getattr(settings, 'TWILIO_API_KEY', ''),
                from_number=getattr(settings, 'TWILIO_PHONE_NUMBER', ''),
                enabled=True,
                rate_limit_per_minute=getattr(settings, 'TWILIO_RATE_LIMIT', 100),
                max_message_length=1600
            ))
        
        # AWS SNS configuration
        aws_enabled = getattr(settings, 'AWS_SNS_ENABLED', False)
        if aws_enabled:
            providers.append(SMSProvider(
                name="aws_sns",
                api_url="https://sns.us-east-1.amazonaws.com",
                api_key=getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
                from_number=getattr(settings, 'AWS_SNS_SENDER_ID', 'FernandoPlatform'),
                enabled=True,
                rate_limit_per_minute=getattr(settings, 'AWS_SNS_RATE_LIMIT', 100),
                max_message_length=160
            ))
        
        # Vonage configuration (if available)
        vonage_enabled = getattr(settings, 'VONAGE_ENABLED', False)
        if vonage_enabled:
            providers.append(SMSProvider(
                name="vonage",
                api_url="https://rest.nexmo.com/sms/json",
                api_key=getattr(settings, 'VONAGE_API_KEY', ''),
                from_number=getattr(settings, 'VONAGE_FROM_NUMBER', 'FernandoPlatform'),
                enabled=True,
                rate_limit_per_minute=getattr(settings, 'VONAGE_RATE_LIMIT', 100),
                max_message_length=1600
            ))
        
        return providers
    
    def _load_message_templates(self) -> Dict[str, Dict[str, str]]:
        """Load SMS message templates"""
        
        return {
            "welcome": {
                "title": "Welcome to Fernando! 🎉",
                "message": "Welcome to Fernando Platform! Your account is ready. Visit {dashboard_url} to get started.",
                "variables": ["dashboard_url"]
            },
            "document_processing": {
                "title": "Document Ready",
                "message": "Your document {document_id} has been processed. Status: {status}. View details: {dashboard_url}/documents/{document_id}",
                "variables": ["document_id", "status", "dashboard_url"]
            },
            "verification_assigned": {
                "title": "New Verification Task",
                "message": "New document assigned for verification: {document_id}. Priority: {priority}. Estimated time: {estimated_time} minutes.",
                "variables": ["document_id", "priority", "estimated_time"]
            },
            "payment_success": {
                "title": "Payment Confirmed",
                "message": "Payment of {amount} {currency} processed successfully. Thank you!",
                "variables": ["amount", "currency"]
            },
            "payment_failed": {
                "title": "Payment Failed",
                "message": "Payment failed: {reason}. Please update your payment method at {billing_url}",
                "variables": ["reason", "billing_url"]
            },
            "security_alert": {
                "title": "Security Alert",
                "message": "Security alert: {alert_type}. If this wasn't you, contact support immediately.",
                "variables": ["alert_type"]
            },
            "system_maintenance": {
                "title": "Scheduled Maintenance",
                "message": "System maintenance scheduled for {start_time}. Expected duration: {duration}. Service may be unavailable.",
                "variables": ["start_time", "duration"]
            },
            "usage_limit_warning": {
                "title": "Usage Limit Warning",
                "message": "You've used {used} of {limit} {resource_type}. Current usage: {percentage}%. Consider upgrading your plan.",
                "variables": ["used", "limit", "resource_type", "percentage"]
            }
        }
    
    def start_processing(self):
        """Start background message processing"""
        
        if not self.processing_task:
            self.processing_task = asyncio.create_task(self._process_message_queue())
            logger.info("Started SMS message processing")
    
    async def send_sms(
        self,
        user_id: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        to_phone: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Send SMS notification"""
        
        try:
            # Get user's phone number if not provided
            if not to_phone:
                to_phone = await self._get_user_phone_number(user_id)
                if not to_phone:
                    raise ValueError(f"Could not find phone number for user {user_id}")
            
            # Validate phone number
            if not self._validate_phone_number(to_phone):
                raise ValueError(f"Invalid phone number: {to_phone}")
            
            # Prepare message content
            message_content = await self._prepare_message_content(
                template_id, message, data or {}
            )
            
            # Create SMS record
            sms_record = SMSNotification(
                id=f"sms_{user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=user_id,
                to_phone=to_phone,
                message=message_content,
                template_id=template_id,
                status="pending",
                created_at=datetime.utcnow(),
                priority=priority,
                retry_count=0
            )
            
            self.db.add(sms_record)
            self.db.commit()
            
            # Add to queue for processing
            await self.message_queue.put({
                "sms_id": sms_record.id,
                "to_phone": to_phone,
                "message": message_content,
                "priority": priority
            })
            
            logger.info(f"SMS queued for {to_phone}: {sms_record.id}")
            return {
                "success": True,
                "sms_id": sms_record.id,
                "status": "queued"
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_message_queue(self):
        """Process SMS message queue"""
        
        while True:
            try:
                # Get message from queue with timeout
                message_data = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=30
                )
                
                # Process message
                result = await self._send_sms_message(message_data)
                
                # Update SMS record
                sms_record = self.db.query(SMSNotification).filter(
                    SMSNotification.id == message_data["sms_id"]
                ).first()
                
                if sms_record:
                    if result["success"]:
                        sms_record.status = "sent"
                        sms_record.sent_at = datetime.utcnow()
                        sms_record.provider_message_id = result.get("provider_message_id")
                    else:
                        sms_record.status = "failed"
                        sms_record.error_message = result["error"]
                    
                    self.db.commit()
                
                # Mark queue task as done
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing SMS queue: {e}")
                await asyncio.sleep(1)
    
    async def _send_sms_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS message via provider"""
        
        to_phone = message_data["to_phone"]
        message = message_data["message"]
        priority = message_data["priority"]
        
        # Try providers in order
        for provider in self.providers:
            if not provider.enabled:
                continue
            
            # Check rate limiting
            if not await self._check_rate_limit(provider, to_phone):
                continue
            
            try:
                # Send via provider
                result = await self._send_via_provider(provider, to_phone, message, priority)
                
                if result["success"]:
                    logger.info(f"SMS sent via {provider.name} to {to_phone}")
                    return result
                
            except Exception as e:
                logger.error(f"Error sending SMS via {provider.name}: {e}")
                continue
        
        # All providers failed
        return {
            "success": False,
            "error": "All SMS providers failed"
        }
    
    async def _send_via_provider(
        self,
        provider: SMSProvider,
        to_phone: str,
        message: str,
        priority: str
    ) -> Dict[str, Any]:
        """Send SMS via specific provider"""
        
        if provider.name == "twilio":
            return await self._send_via_twilio(provider, to_phone, message)
        elif provider.name == "aws_sns":
            return await self._send_via_aws_sns(provider, to_phone, message)
        elif provider.name == "vonage":
            return await self._send_via_vonage(provider, to_phone, message)
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider.name}"
            }
    
    async def _send_via_twilio(
        self,
        provider: SMSProvider,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Twilio requires Basic Auth
                auth = (provider.api_key, '')  # API Key as username, empty password
                
                # Prepare message data
                data = {
                    "To": to_phone,
                    "From": provider.from_number,
                    "Body": message
                }
                
                response = await client.post(
                    f"{provider.api_url}/Accounts/SEND/Messages.json",
                    data=data,
                    auth=auth
                )
                
                if response.status_code == 201:
                    result = response.json()
                    return {
                        "success": True,
                        "provider_message_id": result.get("sid"),
                        "status": result.get("status"),
                        "provider": "twilio"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Twilio API error: {response.status_code} - {response.text}",
                        "provider": "twilio"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Twilio send error: {str(e)}",
                "provider": "twilio"
            }
    
    async def _send_via_aws_sns(
        self,
        provider: SMSProvider,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """Send SMS via AWS SNS"""
        
        try:
            # Note: This is a simplified AWS SNS implementation
            # In production, you'd use boto3 for proper AWS SDK integration
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # AWS SNS requires proper authentication headers
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                # Prepare message data
                data = {
                    "Action": "Publish",
                    "Version": "2010-03-31",
                    "Message": message,
                    "PhoneNumber": to_phone,
                    "MessageAttributes.entry.1.Name": "SenderID",
                    "MessageAttributes.entry.1.Value.StringValue": provider.from_number,
                    "MessageAttributes.entry.1.Type": "String"
                }
                
                response = await client.post(
                    provider.api_url,
                    data=data,
                    headers=headers,
                    auth=('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY')  # Placeholder
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_message_id": "SNS_" + str(int(datetime.utcnow().timestamp())),
                        "status": "sent",
                        "provider": "aws_sns"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"AWS SNS error: {response.status_code} - {response.text}",
                        "provider": "aws_sns"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"AWS SNS send error: {str(e)}",
                "provider": "aws_sns"
            }
    
    async def _send_via_vonage(
        self,
        provider: SMSProvider,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """Send SMS via Vonage (Nexmo)"""
        
        try:
            # Note: This is a simplified Vonage implementation
            # You'd need to split API key and secret if using old format
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "api_key": provider.api_key,
                    "to": to_phone,
                    "from": provider.from_number,
                    "text": message
                }
                
                response = await client.get(
                    provider.api_url,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "messages" in result and len(result["messages"]) > 0:
                        msg = result["messages"][0]
                        if msg.get("status") == "0":  # Success
                            return {
                                "success": True,
                                "provider_message_id": msg.get("message-id"),
                                "status": "sent",
                                "provider": "vonage"
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Vonage error: {msg.get('status-text', 'Unknown error')}",
                                "provider": "vonage"
                            }
                
                return {
                    "success": False,
                    "error": f"Vonage API error: {response.status_code}",
                    "provider": "vonage"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Vonage send error: {str(e)}",
                "provider": "vonage"
            }
    
    async def _prepare_message_content(
        self,
        template_id: Optional[str],
        message: str,
        data: Dict[str, Any]
    ) -> str:
        """Prepare SMS message content using template or plain text"""
        
        # Default values for SMS templates
        default_context = {
            "dashboard_url": getattr(settings, 'FRONTEND_URL', 'https://dashboard.fernandoplatform.com'),
            "billing_url": getattr(settings, 'FRONTEND_URL', 'https://dashboard.fernandoplatform.com') + "/billing"
        }
        
        context = {**default_context, **data}
        
        if template_id and template_id in self.message_templates:
            # Use template
            template = self.message_templates[template_id]
            message_content = template["message"].format(**context)
        else:
            # Use provided message
            message_content = message
        
        # Ensure message length is within limits
        max_length = max(p.max_message_length for p in self.providers)
        if len(message_content) > max_length:
            message_content = message_content[:max_length-3] + "..."
        
        return message_content
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        
        # Simple validation - in production, use a proper library like libphonenumber
        import re
        
        # Remove all non-digit characters
        cleaned = re.sub(r'[^\d+]', '', phone_number)
        
        # Check for valid patterns
        patterns = [
            r'^\+1[0-9]{10}$',  # US/Canada
            r'^\+[0-9]{10,15}$',  # International
            r'^[0-9]{10}$'  # US/Canada without country code
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned):
                return True
        
        return False
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for sending"""
        
        # Remove all non-digit characters
        import re
        cleaned = re.sub(r'[^\d]', '', phone_number)
        
        # Add +1 if it's a 10-digit US/Canada number
        if len(cleaned) == 10:
            cleaned = '1' + cleaned
        
        return '+' + cleaned
    
    async def _get_user_phone_number(self, user_id: str) -> Optional[str]:
        """Get user's phone number"""
        
        user_phone = self.db.query(UserPhoneNumber).filter(
            UserPhoneNumber.user_id == user_id
        ).first()
        
        if user_phone:
            return self._format_phone_number(user_phone.phone_number)
        
        return None
    
    async def _check_rate_limit(self, provider: SMSProvider, phone_number: str) -> bool:
        """Check rate limiting for provider and phone number"""
        
        now = datetime.utcnow()
        minute_start = now.replace(second=0, microsecond=0)
        
        # Create rate limit key
        key = f"{provider.name}:{phone_number}:{minute_start.isoformat()}"
        
        # Check current count
        current_count = self.rate_limits.get(key, 0)
        
        if current_count >= provider.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for {phone_number} via {provider.name}")
            return False
        
        # Increment count
        self.rate_limits[key] = current_count + 1
        
        return True
    
    async def send_bulk_sms(
        self,
        sms_list: List[Dict[str, Any]],
        template_id: Optional[str] = None,
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Send bulk SMS messages"""
        
        results = {"success": 0, "failed": 0, "queued": 0}
        
        # Process in batches
        for i in range(0, len(sms_list), batch_size):
            batch = sms_list[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = []
            for sms_data in batch:
                task = asyncio.create_task(
                    self.send_sms(
                        user_id=sms_data["user_id"],
                        message=sms_data["message"],
                        data=sms_data.get("data", {}),
                        template_id=template_id,
                        to_phone=sms_data.get("to_phone"),
                        priority=sms_data.get("priority", "normal")
                    )
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                elif result.get("success", False):
                    if result.get("status") == "queued":
                        results["queued"] += 1
                    else:
                        results["success"] += 1
                else:
                    results["failed"] += 1
        
        return results
    
    async def get_sms_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get SMS delivery statistics"""
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query conditions
        conditions = [
            SMSNotification.created_at >= start_date,
            SMSNotification.created_at <= end_date
        ]
        
        # Basic counts
        total_sms = self.db.query(func.count(SMSNotification.id)).filter(
            and_(*conditions)
        ).scalar() or 0
        
        sent_sms = self.db.query(func.count(SMSNotification.id)).filter(
            and_(*conditions, SMSNotification.status == 'sent')
        ).scalar() or 0
        
        failed_sms = self.db.query(func.count(SMSNotification.id)).filter(
            and_(*conditions, SMSNotification.status == 'failed')
        ).scalar() or 0
        
        pending_sms = self.db.query(func.count(SMSNotification.id)).filter(
            and_(*conditions, SMSNotification.status == 'pending')
        ).scalar() or 0
        
        # Provider usage
        provider_usage = self.db.query(
            SMSNotification.provider,
            func.count(SMSNotification.id).label('count')
        ).filter(
            and_(*conditions, SMSNotification.provider.isnot(None))
        ).group_by(
            SMSNotification.provider
        ).all()
        
        provider_stats = {usage.provider or 'unknown': usage.count for usage in provider_usage}
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_sms": total_sms,
            "sent_sms": sent_sms,
            "failed_sms": failed_sms,
            "pending_sms": pending_sms,
            "success_rate": round((sent_sms / total_sms * 100), 2) if total_sms > 0 else 0,
            "provider_usage": provider_stats,
            "available_providers": [p.name for p in self.providers if p.enabled]
        }
    
    async def register_user_phone_number(
        self,
        user_id: str,
        phone_number: str,
        verified: bool = False,
        primary: bool = True
    ) -> UserPhoneNumber:
        """Register a phone number for a user"""
        
        # Format phone number
        formatted_number = self._format_phone_number(phone_number)
        
        # Check if number already exists
        existing = self.db.query(UserPhoneNumber).filter(
            UserPhoneNumber.phone_number == formatted_number
        ).first()
        
        if existing and existing.user_id != user_id:
            raise ValueError(f"Phone number {formatted_number} is already registered to another user")
        
        if existing:
            # Update existing registration
            existing.verified = verified
            existing.primary = primary
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing
        
        # Create new registration
        phone_record = UserPhoneNumber(
            user_id=user_id,
            phone_number=formatted_number,
            verified=verified,
            primary=primary,
            created_at=datetime.utcnow()
        )
        
        self.db.add(phone_record)
        self.db.commit()
        
        logger.info(f"Registered phone number {formatted_number} for user {user_id}")
        return phone_record
    
    async def cleanup_old_sms(self, days_to_keep: int = 90) -> int:
        """Clean up old SMS records"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(SMSNotification).filter(
            SMSNotification.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old SMS records")
        return deleted_count
    
    async def shutdown(self):
        """Shutdown SMS service"""
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("SMS service shutdown complete")