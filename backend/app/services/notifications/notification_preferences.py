"""
Notification Preferences Service
Handles user notification preference management
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.notifications import (
    NotificationPreference, 
    NotificationChannel, 
    UserNotificationSettings,
    NotificationTemplate
)

logger = logging.getLogger(__name__)

class NotificationPreferenceService:
    """Handles user notification preferences and settings"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Default preference templates
        self.default_preferences = self._load_default_preferences()
    
    def _load_default_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Load default notification preferences"""
        
        return {
            # Document Processing Preferences
            "document_processing": {
                "enabled": True,
                "channels": ["push", "email"],
                "priority": "normal",
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC"
                },
                "frequency": "immediate",  # immediate, hourly, daily
                "conditions": {
                    "process_only_failures": False,
                    "min_confidence_threshold": 0.8
                }
            },
            
            # Verification Workflow Preferences
            "verification": {
                "enabled": True,
                "channels": ["email", "push"],
                "priority": "high",
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC"
                },
                "frequency": "immediate",
                "conditions": {
                    "notify_on_assignment": True,
                    "notify_on_completion": True,
                    "notify_on_escalation": True,
                    "priority_filter": ["high", "urgent"]  # Only notify for high/urgent tasks
                }
            },
            
            # Billing Preferences
            "billing": {
                "enabled": True,
                "channels": ["email", "push", "sms"],
                "priority": "high",
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC"
                },
                "frequency": "immediate",
                "conditions": {
                    "notify_payment_success": True,
                    "notify_payment_failed": True,
                    "notify_subscription_changes": True,
                    "notify_usage_warnings": True,
                    "notify_billing_issues": True
                }
            },
            
            # Security Preferences
            "security": {
                "enabled": True,
                "channels": ["email", "sms", "push"],
                "priority": "critical",
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC"
                },
                "frequency": "immediate",
                "conditions": {
                    "notify_login_failures": True,
                    "notify_suspicious_activity": True,
                    "notify_password_changes": True,
                    "notify_two_factor_changes": True,
                    "risk_threshold": 0.7  # Only notify for high-risk events
                }
            },
            
            # System Preferences
            "system": {
                "enabled": True,
                "channels": ["push"],
                "priority": "normal",
                "quiet_hours": {
                    "enabled": True,
                    "start": "22:00",
                    "end": "06:00",
                    "timezone": "UTC"
                },
                "frequency": "immediate",
                "conditions": {
                    "notify_maintenance": True,
                    "notify_performance_alerts": True,
                    "notify_outages": True,
                    "notify_feature_updates": False,
                    "severity_filter": ["high", "critical"]
                }
            },
            
            # Marketing Preferences
            "marketing": {
                "enabled": False,
                "channels": ["email"],
                "priority": "low",
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "08:00",
                    "timezone": "UTC"
                },
                "frequency": "daily",
                "conditions": {
                    "notify_new_features": True,
                    "notify_tips": False,
                    "notify_newsletter": True,
                    "frequency_limit": 1  # Max 1 per day
                }
            }
        }
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences"""
        
        # Get user preferences from database
        preferences = self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).all()
        
        # Get global user settings
        user_settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).first()
        
        # Build preferences dictionary
        user_prefs = {}
        
        # Add individual notification type preferences
        for pref in preferences:
            user_prefs[pref.notification_type] = {
                "enabled": pref.enabled,
                "channels": json.loads(pref.channels) if pref.channels else [],
                "priority": pref.priority,
                "frequency": pref.frequency,
                "quiet_hours": json.loads(pref.quiet_hours) if pref.quiet_hours else {},
                "conditions": json.loads(pref.conditions) if pref.conditions else {}
            }
        
        # Apply defaults for missing preferences
        for notification_type, default_config in self.default_preferences.items():
            if notification_type not in user_prefs:
                user_prefs[notification_type] = default_config
        
        # Add global settings
        user_prefs["global"] = {
            "enabled_channels": json.loads(user_settings.enabled_channels) if user_settings else ["push"],
            "timezone": user_settings.timezone if user_settings else "UTC",
            "language": user_settings.language if user_settings else "en",
            "do_not_disturb": user_settings.do_not_disturb if user_settings else False,
            "notification_sound": user_settings.notification_sound if user_settings else True,
            "notification_badge": user_settings.notification_badge if user_settings else True,
            "notification_history_days": user_settings.notification_history_days if user_settings else 30
        }
        
        return user_prefs
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user notification preferences"""
        
        try:
            # Update individual notification type preferences
            for notification_type, config in preferences.items():
                if notification_type == "global":
                    continue
                
                # Find existing preference or create new
                existing = self.db.query(NotificationPreference).filter(
                    and_(
                        NotificationPreference.user_id == user_id,
                        NotificationPreference.notification_type == notification_type
                    )
                ).first()
                
                if existing:
                    # Update existing
                    existing.enabled = config.get("enabled", True)
                    existing.channels = json.dumps(config.get("channels", []))
                    existing.priority = config.get("priority", "normal")
                    existing.frequency = config.get("frequency", "immediate")
                    existing.quiet_hours = json.dumps(config.get("quiet_hours", {}))
                    existing.conditions = json.dumps(config.get("conditions", {}))
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    new_pref = NotificationPreference(
                        user_id=user_id,
                        notification_type=notification_type,
                        enabled=config.get("enabled", True),
                        channels=json.dumps(config.get("channels", [])),
                        priority=config.get("priority", "normal"),
                        frequency=config.get("frequency", "immediate"),
                        quiet_hours=json.dumps(config.get("quiet_hours", {})),
                        conditions=json.dumps(config.get("conditions", {})),
                        created_at=datetime.utcnow()
                    )
                    self.db.add(new_pref)
            
            # Update global settings
            if "global" in preferences:
                global_config = preferences["global"]
                
                user_settings = self.db.query(UserNotificationSettings).filter(
                    UserNotificationSettings.user_id == user_id
                ).first()
                
                if user_settings:
                    # Update existing
                    user_settings.enabled_channels = json.dumps(global_config.get("enabled_channels", ["push"]))
                    user_settings.timezone = global_config.get("timezone", "UTC")
                    user_settings.language = global_config.get("language", "en")
                    user_settings.do_not_disturb = global_config.get("do_not_disturb", False)
                    user_settings.notification_sound = global_config.get("notification_sound", True)
                    user_settings.notification_badge = global_config.get("notification_badge", True)
                    user_settings.notification_history_days = global_config.get("notification_history_days", 30)
                    user_settings.updated_at = datetime.utcnow()
                else:
                    # Create new
                    new_settings = UserNotificationSettings(
                        user_id=user_id,
                        enabled_channels=json.dumps(global_config.get("enabled_channels", ["push"])),
                        timezone=global_config.get("timezone", "UTC"),
                        language=global_config.get("language", "en"),
                        do_not_disturb=global_config.get("do_not_disturb", False),
                        notification_sound=global_config.get("notification_sound", True),
                        notification_badge=global_config.get("notification_badge", True),
                        notification_history_days=global_config.get("notification_history_days", 30),
                        created_at=datetime.utcnow()
                    )
                    self.db.add(new_settings)
            
            self.db.commit()
            logger.info(f"Updated notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            self.db.rollback()
            return False
    
    async def reset_user_preferences(self, user_id: str) -> bool:
        """Reset user preferences to defaults"""
        
        try:
            # Delete existing preferences
            self.db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).delete()
            
            self.db.query(UserNotificationSettings).filter(
                UserNotificationSettings.user_id == user_id
            ).delete()
            
            self.db.commit()
            logger.info(f"Reset notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting user preferences: {e}")
            self.db.rollback()
            return False
    
    async def get_preferences_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of user notification preferences"""
        
        preferences = await self.get_user_preferences(user_id)
        
        # Count enabled notification types
        enabled_types = 0
        total_types = len(preferences) - 1  # Exclude global
        
        for notification_type, config in preferences.items():
            if notification_type != "global" and config.get("enabled", False):
                enabled_types += 1
        
        # Count enabled channels
        global_config = preferences.get("global", {})
        enabled_channels = global_config.get("enabled_channels", [])
        
        # Get quiet hours status
        quiet_hours_enabled = any(
            config.get("quiet_hours", {}).get("enabled", False)
            for config in preferences.values()
            if notification_type != "global"
        )
        
        return {
            "total_notification_types": total_types,
            "enabled_notification_types": enabled_types,
            "enabled_channels": enabled_channels,
            "quiet_hours_enabled": quiet_hours_enabled,
            "do_not_disturb": global_config.get("do_not_disturb", False),
            "timezone": global_config.get("timezone", "UTC"),
            "language": global_config.get("language", "en")
        }
    
    async def check_quiet_hours(
        self,
        user_id: str,
        notification_type: str
    ) -> Tuple[bool, str]:
        """Check if notification should be sent based on quiet hours"""
        
        preferences = await self.get_user_preferences(user_id)
        
        # Check global DND setting
        if preferences.get("global", {}).get("do_not_disturb", False):
            return True, "Global do not disturb enabled"
        
        # Check notification type specific quiet hours
        type_config = preferences.get(notification_type, {})
        quiet_hours = type_config.get("quiet_hours", {})
        
        if not quiet_hours.get("enabled", False):
            return False, "Quiet hours not enabled"
        
        # Get current time in user's timezone
        import pytz
        from datetime import time
        
        user_timezone = pytz.timezone(quiet_hours.get("timezone", "UTC"))
        now = datetime.now(user_timezone)
        current_time = now.time()
        
        # Parse quiet hours
        try:
            start_time = datetime.strptime(quiet_hours.get("start", "22:00"), "%H:%M").time()
            end_time = datetime.strptime(quiet_hours.get("end", "08:00"), "%H:%M").time()
        except ValueError:
            return False, "Invalid quiet hours format"
        
        # Check if current time is in quiet hours
        if start_time <= end_time:
            # Same day quiet hours (e.g., 22:00 to 08:00)
            in_quiet_hours = start_time <= current_time <= end_time
        else:
            # Cross-day quiet hours (e.g., 22:00 to 08:00 next day)
            in_quiet_hours = current_time >= start_time or current_time <= end_time
        
        return in_quiet_hours, "Within quiet hours"
    
    async def is_notification_enabled(
        self,
        user_id: str,
        notification_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Check if a notification type is enabled for a user"""
        
        preferences = await self.get_user_preferences(user_id)
        type_config = preferences.get(notification_type, {})
        
        # Check if notification type is enabled
        if not type_config.get("enabled", True):
            return False, "Notification type disabled"
        
        # Check quiet hours
        in_quiet_hours, quiet_reason = await self.check_quiet_hours(user_id, notification_type)
        if in_quiet_hours:
            return False, quiet_reason
        
        # Check conditions
        conditions = type_config.get("conditions", {})
        if context:
            condition_result, condition_reason = await self._check_conditions(
                notification_type, conditions, context
            )
            if not condition_result:
                return False, condition_reason
        
        return True, "Notification enabled"
    
    async def _check_conditions(
        self,
        notification_type: str,
        conditions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check notification conditions against context"""
        
        if notification_type == "document_processing":
            # Check confidence threshold
            confidence = context.get("confidence_score", 1.0)
            threshold = conditions.get("min_confidence_threshold", 0.8)
            
            if confidence < threshold:
                return False, f"Confidence score {confidence} below threshold {threshold}"
            
            # Check if only failures should be notified
            if conditions.get("process_only_failures", False):
                status = context.get("status", "")
                if status != "failed":
                    return False, "Only failures configured to be notified"
        
        elif notification_type == "verification":
            # Check priority filter
            priority = context.get("priority", "normal")
            priority_filter = conditions.get("priority_filter", [])
            
            if priority_filter and priority not in priority_filter:
                return False, f"Priority {priority} not in filter"
        
        elif notification_type == "security":
            # Check risk threshold
            risk_score = context.get("risk_score", 0.0)
            threshold = conditions.get("risk_threshold", 0.7)
            
            if risk_score < threshold:
                return False, f"Risk score {risk_score} below threshold {threshold}"
        
        elif notification_type == "system":
            # Check severity filter
            severity = context.get("severity", "normal")
            severity_filter = conditions.get("severity_filter", [])
            
            if severity_filter and severity not in severity_filter:
                return False, f"Severity {severity} not in filter"
        
        return True, "Conditions met"
    
    async def bulk_update_preferences(
        self,
        user_ids: List[str],
        preferences: Dict[str, Any]
    ) -> Dict[str, int]:
        """Bulk update preferences for multiple users"""
        
        results = {"success": 0, "failed": 0, "total": len(user_ids)}
        
        for user_id in user_ids:
            try:
                success = await self.update_user_preferences(user_id, preferences)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error bulk updating preferences for user {user_id}: {e}")
                results["failed"] += 1
        
        return results
    
    async def get_preference_statistics(self) -> Dict[str, Any]:
        """Get global preference statistics"""
        
        # Get total users with preferences
        total_users = self.db.query(UserNotificationSettings.user_id).distinct().count()
        
        # Get preference counts
        type_counts = {}
        channel_counts = {}
        
        preferences = self.db.query(NotificationPreference).all()
        
        for pref in preferences:
            # Count notification types
            type_counts[pref.notification_type] = type_counts.get(pref.notification_type, 0) + 1
            
            # Count channels
            channels = json.loads(pref.channels) if pref.channels else []
            for channel in channels:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        return {
            "total_users_with_preferences": total_users,
            "notification_type_distribution": type_counts,
            "channel_preference_distribution": channel_counts,
            "most_used_channels": sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    async def export_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Export user preferences in JSON format"""
        
        preferences = await self.get_user_preferences(user_id)
        summary = await self.get_preferences_summary(user_id)
        
        export_data = {
            "user_id": user_id,
            "exported_at": datetime.utcnow().isoformat(),
            "preferences": preferences,
            "summary": summary
        }
        
        return export_data
    
    async def import_user_preferences(
        self,
        user_id: str,
        preferences_data: Dict[str, Any]
    ) -> bool:
        """Import user preferences from JSON data"""
        
        try:
            if "preferences" in preferences_data:
                success = await self.update_user_preferences(
                    user_id, 
                    preferences_data["preferences"]
                )
                return success
            else:
                return False
        except Exception as e:
            logger.error(f"Error importing preferences for user {user_id}: {e}")
            return False
    
    async def create_preference_template(
        self,
        name: str,
        preferences: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """Create a preference template for reuse"""
        
        # Store template in database or cache
        # For now, we'll add it to the default preferences
        self.default_preferences[name] = {
            **preferences,
            "template": True,
            "description": description or f"Template: {name}",
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Created preference template: {name}")
        return name
    
    async def apply_preference_template(
        self,
        user_id: str,
        template_name: str
    ) -> bool:
        """Apply a preference template to a user"""
        
        if template_name not in self.default_preferences:
            return False
        
        template = self.default_preferences[template_name]
        
        # Apply template preferences
        user_prefs = {k: v for k, v in template.items() if not k.startswith('_')}
        
        return await self.update_user_preferences(user_id, user_prefs)