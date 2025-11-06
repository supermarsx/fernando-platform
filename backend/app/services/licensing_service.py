from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import secrets
import hashlib
from app.models.license import (
    License, LicenseTierModel, LicenseAssignment, 
    LicenseUsage, LicenseAuditLog, LicenseTier
)
from app.schemas.license_schemas import (
    LicenseCreate, LicenseUpdate, LicenseStatus,
    LicenseValidationRequest, LicenseValidationResponse,
    LicenseUsageCreate, LicenseAuditLogCreate
)
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel, TelemetryMixin
from app.middleware.telemetry_decorators import (
    license_telemetry, business_telemetry, track_revenue_event,
    record_business_metric, increment_metric
)


class LicensingService(TelemetryMixin):
    """Service for managing licenses, validation, and feature gating"""
    
    def __init__(self, db: Session):
        self.db = db
        self.log_telemetry_event(
            "license.service_initialized", 
            TelemetryEvent.LICENSE_CREATED,
            level=TelemetryLevel.INFO
        )
    
    def generate_license_key(self) -> str:
        """Generate a unique license key"""
        random_bytes = secrets.token_bytes(16)
        key_hash = hashlib.sha256(random_bytes).hexdigest()[:32].upper()
        
        # Format as XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
        formatted = '-'.join([key_hash[i:i+4] for i in range(0, 32, 4)])
        return formatted
    
    @license_telemetry("create_license")
    def create_license(
        self, 
        license_data: LicenseCreate,
        created_by_user_id: Optional[int] = None
    ) -> License:
        """Create a new license"""
        # Generate unique license key
        license_key = self.generate_license_key()
        
        # Create license
        license = License(
            license_key=license_key,
            tier_id=license_data.tier_id,
            organization_name=license_data.organization_name,
            organization_email=license_data.organization_email,
            expires_at=license_data.expires_at,
            max_activations=license_data.max_activations,
            metadata=license_data.metadata or {},
            status="active"
        )
        
        self.db.add(license)
        self.db.commit()
        self.db.refresh(license)
        
        # Create audit log
        self._create_audit_log(
            license_id=license.license_id,
            user_id=created_by_user_id,
            action="created",
            description=f"License created for {license_data.organization_name}"
        )
        
        # Log business metrics
        self.record_business_kpi(
            "licenses.created.count", 
            1.0,
            {
                "tier_id": str(license_data.tier_id),
                "organization_name": license_data.organization_name
            }
        )
        
        # Return license with business metrics for telemetry
        return {
            "license": license,
            "business_metric": "licenses.created.count",
            "metric_value": 1.0
        }
    
    @license_telemetry("validate_license")
    def validate_license(
        self, 
        validation_request: LicenseValidationRequest
    ) -> LicenseValidationResponse:
        """Validate a license key and return license details"""
        license = self.db.query(License).filter(
            License.license_key == validation_request.license_key
        ).first()
        
        if not license:
            return LicenseValidationResponse(
                valid=False,
                message="Invalid license key"
            )
        
        # Check if license is active
        if license.status != "active":
            return LicenseValidationResponse(
                valid=False,
                message=f"License is {license.status}"
            )
        
        # Check expiration
        if license.expires_at < datetime.utcnow():
            license.status = "expired"
            self.db.commit()
            return LicenseValidationResponse(
                valid=False,
                message="License has expired"
            )
        
        # Check hardware fingerprint if provided
        if validation_request.hardware_fingerprint:
            if license.hardware_fingerprint and license.hardware_fingerprint != validation_request.hardware_fingerprint:
                return LicenseValidationResponse(
                    valid=False,
                    message="Hardware fingerprint mismatch"
                )
            
            # Set hardware fingerprint on first validation
            if not license.hardware_fingerprint:
                license.hardware_fingerprint = validation_request.hardware_fingerprint
                license.current_activations = 1
            
        # Update last validated timestamp
        license.last_validated_at = datetime.utcnow()
        self.db.commit()
        
        # Get tier information
        tier = license.tier
        
        # Check if license is expiring soon (within 30 days)
        days_until_expiry = (license.expires_at - datetime.utcnow()).days
        if days_until_expiry <= 30:
            self.log_telemetry_event(
                "license.expiry_warning",
                TelemetryEvent.LICENSE_EXPIRY_WARNING,
                TelemetryLevel.WARNING,
                additional_data={
                    "license_id": license.license_id,
                    "days_until_expiry": days_until_expiry,
                    "expires_at": license.expires_at.isoformat()
                }
            )
        
        # Record validation metrics
        self.record_business_kpi(
            "licenses.validation.count", 
            1.0,
            {"validation_result": "valid", "tier_id": str(license.tier_id)}
        )
        
        if days_until_expiry <= 30:
            self.record_business_kpi(
                "licenses.expiry_warnings.count", 
                1.0,
                {"tier_id": str(license.tier_id)}
            )
        
        return LicenseValidationResponse(
            valid=True,
            license=license,
            message="License is valid",
            features=tier.features if tier else {},
            limits={
                "max_documents_per_month": tier.max_documents_per_month if tier else 0,
                "max_users": tier.max_users if tier else 0,
                "max_storage_gb": tier.max_storage_gb if tier else 0,
                "documents_used_this_month": license.documents_processed_this_month,
                "documents_remaining": max(0, (tier.max_documents_per_month if tier else 0) - license.documents_processed_this_month)
            },
            business_metric="licenses.validation.count",
            metric_value=1.0
        )
    
    def check_feature_access(
        self, 
        license_id: int, 
        feature_name: str
    ) -> bool:
        """Check if a license has access to a specific feature"""
        license = self.db.query(License).filter(
            License.license_id == license_id,
            License.status == "active"
        ).first()
        
        if not license or not license.tier:
            return False
        
        # Check if license is expired
        if license.expires_at < datetime.utcnow():
            return False
        
        # Check feature in tier features
        return license.tier.features.get(feature_name, False)
    
    @license_telemetry("check_usage_limit")
    def check_usage_limit(
        self, 
        license_id: int, 
        limit_type: str = "documents"
    ) -> Dict[str, Any]:
        """Check if license has reached usage limits"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license or not license.tier:
            return {"allowed": False, "reason": "Invalid license"}
        
        # Reset monthly counter if needed
        if license.last_reset_at.month != datetime.utcnow().month:
            license.documents_processed_this_month = 0
            license.last_reset_at = datetime.utcnow()
            self.db.commit()
        
        if limit_type == "documents":
            max_docs = license.tier.max_documents_per_month
            current_docs = license.documents_processed_this_month
            
            if current_docs >= max_docs:
                return {
                    "allowed": False,
                    "reason": "Monthly document limit reached",
                    "current": current_docs,
                    "limit": max_docs
                }
            
            result = {
                "allowed": current_docs < max_docs,
                "current": current_docs,
                "limit": max_docs,
                "remaining": max_docs - current_docs,
                "business_metric": f"licenses.usage_check.{limit_type}",
                "metric_value": 1.0 if current_docs < max_docs else 0.0
            }
            
            # Record usage limit check
            self.record_business_kpi(
                f"licenses.usage_check.{limit_type}",
                1.0 if current_docs < max_docs else 0.0,
                {
                    "license_id": str(license_id),
                    "usage_within_limit": str(current_docs < max_docs),
                    "current_usage": str(current_docs),
                    "usage_limit": str(max_docs)
                }
            )
            
            return result
        
        # Record general usage check
        self.record_business_kpi(
            "licenses.usage_check.general",
            1.0,
            {"license_id": str(license_id)}
        )
        
        return {"allowed": True, "business_metric": "licenses.usage_check.general", "metric_value": 1.0}
    
    @license_telemetry("increment_usage")
    def increment_usage(
        self, 
        license_id: int, 
        usage_type: str = "documents",
        count: int = 1,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Increment license usage counters"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license:
            return
        
        if usage_type == "documents":
            license.documents_processed_this_month += count
        
        # Log usage
        usage_log = LicenseUsage(
            license_id=license_id,
            user_id=user_id,
            feature_used=usage_type,
            usage_count=count,
            metadata=metadata or {}
        )
        
        self.db.add(usage_log)
        self.db.commit()
        
        # Record usage increment metrics
        self.record_business_kpi(
            "licenses.usage_increment.count",
            float(count),
            {
                "license_id": str(license_id),
                "usage_type": usage_type,
                "user_id": str(user_id) if user_id else "system"
            }
        )
        
        # Record resource consumption
        if usage_type == "documents":
            self.record_business_kpi(
                "licenses.documents_processed.count",
                float(count),
                {"license_id": str(license_id)}
            )
    
    @license_telemetry("renew_license")
    def renew_license(
        self, 
        license_id: int, 
        renewal_months: int = 12,
        renewed_by_user_id: Optional[int] = None
    ) -> License:
        """Renew a license"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license:
            raise ValueError("License not found")
        
        # Extend expiration date
        if license.expires_at < datetime.utcnow():
            # If expired, start from now
            license.expires_at = datetime.utcnow() + timedelta(days=renewal_months * 30)
        else:
            # If still valid, extend from current expiration
            license.expires_at = license.expires_at + timedelta(days=renewal_months * 30)
        
        # Reactivate if expired
        if license.status == "expired":
            license.status = "active"
        
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            license_id=license_id,
            user_id=renewed_by_user_id,
            action="renewed",
            description=f"License renewed for {renewal_months} months"
        )
        
        # Record renewal metrics
        self.record_business_kpi(
            "licenses.renewed.count", 
            1.0,
            {
                "renewal_months": str(renewal_months),
                "license_id": str(license_id),
                "tier_id": str(license.tier_id)
            }
        )
        
        return {
            "license": license,
            "business_metric": "licenses.renewed.count",
            "metric_value": 1.0
        }
    
    @license_telemetry("upgrade_license")
    def upgrade_license(
        self, 
        license_id: int, 
        new_tier_id: int,
        upgraded_by_user_id: Optional[int] = None
    ) -> License:
        """Upgrade a license to a new tier"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license:
            raise ValueError("License not found")
        
        old_tier_id = license.tier_id
        license.tier_id = new_tier_id
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            license_id=license_id,
            user_id=upgraded_by_user_id,
            action="upgraded",
            description=f"License upgraded from tier {old_tier_id} to tier {new_tier_id}"
        )
        
        # Record upgrade metrics
        self.record_business_kpi(
            "licenses.upgraded.count", 
            1.0,
            {
                "from_tier_id": str(old_tier_id),
                "to_tier_id": str(new_tier_id),
                "license_id": str(license_id)
            }
        )
        
        return {
            "license": license,
            "business_metric": "licenses.upgraded.count",
            "metric_value": 1.0
        }
    
    @license_telemetry("suspend_license")
    def suspend_license(
        self, 
        license_id: int,
        reason: str,
        suspended_by_user_id: Optional[int] = None
    ) -> License:
        """Suspend a license"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license:
            raise ValueError("License not found")
        
        license.status = "suspended"
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            license_id=license_id,
            user_id=suspended_by_user_id,
            action="suspended",
            description=reason
        )
        
        # Record suspension metrics
        self.record_business_kpi(
            "licenses.suspended.count", 
            1.0,
            {
                "license_id": str(license_id),
                "reason": reason
            }
        )
        
        return {
            "license": license,
            "business_metric": "licenses.suspended.count",
            "metric_value": 1.0
        }
    
    @license_telemetry("revoke_license")
    def revoke_license(
        self, 
        license_id: int,
        reason: str,
        revoked_by_user_id: Optional[int] = None
    ) -> License:
        """Revoke a license"""
        license = self.db.query(License).filter(
            License.license_id == license_id
        ).first()
        
        if not license:
            raise ValueError("License not found")
        
        license.status = "revoked"
        self.db.commit()
        
        # Create audit log
        self._create_audit_log(
            license_id=license_id,
            user_id=revoked_by_user_id,
            action="revoked",
            description=reason
        )
        
        # Record revocation metrics
        self.record_business_kpi(
            "licenses.revoked.count", 
            1.0,
            {
                "license_id": str(license_id),
                "reason": reason
            }
        )
        
        return {
            "license": license,
            "business_metric": "licenses.revoked.count",
            "metric_value": 1.0
        }
    
    def get_license_analytics(self) -> Dict[str, Any]:
        """Get licensing analytics"""
        total_licenses = self.db.query(License).count()
        active_licenses = self.db.query(License).filter(License.status == "active").count()
        expired_licenses = self.db.query(License).filter(License.status == "expired").count()
        suspended_licenses = self.db.query(License).filter(License.status == "suspended").count()
        revoked_licenses = self.db.query(License).filter(License.status == "revoked").count()
        
        # Licenses by tier
        tiers = self.db.query(LicenseTierModel).all()
        licenses_by_tier = {}
        for tier in tiers:
            count = self.db.query(License).filter(License.tier_id == tier.tier_id).count()
            licenses_by_tier[tier.name] = count
        
        return {
            "total_licenses": total_licenses,
            "active_licenses": active_licenses,
            "expired_licenses": expired_licenses,
            "suspended_licenses": suspended_licenses,
            "revoked_licenses": revoked_licenses,
            "licenses_by_tier": licenses_by_tier
        }
    
    def _create_audit_log(
        self,
        license_id: int,
        action: str,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create an audit log entry"""
        audit_log = LicenseAuditLog(
            license_id=license_id,
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        self.db.add(audit_log)
        self.db.commit()


def initialize_default_tiers(db: Session):
    """Initialize default license tiers if they don't exist"""
    existing_tiers = db.query(LicenseTierModel).count()
    
    if existing_tiers > 0:
        return
    
    tiers = [
        {
            "name": "basic",
            "display_name": "Basic",
            "description": "Perfect for small businesses getting started with automation",
            "price_monthly": 29.99,
            "price_yearly": 299.99,
            "max_documents_per_month": 100,
            "max_users": 3,
            "max_storage_gb": 5,
            "features": {
                "document_processing": True,
                "ocr_extraction": True,
                "llm_extraction": True,
                "batch_processing": False,
                "api_access": False,
                "custom_integrations": False,
                "priority_support": False,
                "advanced_analytics": False
            }
        },
        {
            "name": "professional",
            "display_name": "Professional",
            "description": "Advanced features for growing businesses",
            "price_monthly": 99.99,
            "price_yearly": 999.99,
            "max_documents_per_month": 1000,
            "max_users": 10,
            "max_storage_gb": 50,
            "features": {
                "document_processing": True,
                "ocr_extraction": True,
                "llm_extraction": True,
                "batch_processing": True,
                "api_access": True,
                "custom_integrations": False,
                "priority_support": False,
                "advanced_analytics": True
            }
        },
        {
            "name": "enterprise",
            "display_name": "Enterprise",
            "description": "Unlimited features for large organizations",
            "price_monthly": 299.99,
            "price_yearly": 2999.99,
            "max_documents_per_month": 999999,
            "max_users": 999,
            "max_storage_gb": 999,
            "features": {
                "document_processing": True,
                "ocr_extraction": True,
                "llm_extraction": True,
                "batch_processing": True,
                "api_access": True,
                "custom_integrations": True,
                "priority_support": True,
                "advanced_analytics": True,
                "white_label": True,
                "dedicated_support": True
            }
        }
    ]
    
    for tier_data in tiers:
        tier = LicenseTierModel(**tier_data)
        db.add(tier)
    
    db.commit()
