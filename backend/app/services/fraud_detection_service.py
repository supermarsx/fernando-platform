"""
Payment Fraud Detection Service

Provides comprehensive fraud detection and prevention including:
- Velocity checks (rate limiting on payment attempts)
- Amount threshold verification
- Geographic location analysis
- Device fingerprinting
- Payment pattern analysis
- Risk scoring

Helps prevent fraudulent transactions and chargebacks.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib

from app.core.config import settings
from app.models.billing import Payment, PaymentStatus
from app.models.user import User


class FraudDetectionService:
    """Service for detecting and preventing payment fraud"""
    
    def __init__(self, db: Session):
        self.db = db
        self.enabled = settings.FRAUD_DETECTION_ENABLED
        self.max_attempts_per_day = settings.MAX_PAYMENT_ATTEMPTS_PER_DAY
        self.verification_threshold = settings.MAX_PAYMENT_AMOUNT_WITHOUT_VERIFICATION
        self.velocity_check_enabled = settings.PAYMENT_VELOCITY_CHECK_ENABLED
    
    # ============================================================================
    # FRAUD RISK ASSESSMENT
    # ============================================================================
    
    def assess_payment_risk(
        self,
        user_id: int,
        amount: Decimal,
        currency: str = "EUR",
        payment_method: str = "credit_card",
        ip_address: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        billing_address: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess fraud risk for a payment attempt
        
        Returns risk score and recommendations
        """
        
        if not self.enabled:
            return {
                "risk_score": 0,
                "risk_level": "low",
                "approved": True,
                "checks": {"fraud_detection": "disabled"}
            }
        
        risk_factors = []
        risk_score = 0
        
        # Velocity check - Too many payment attempts
        velocity_check = self._check_payment_velocity(user_id)
        if not velocity_check["passed"]:
            risk_score += 30
            risk_factors.append("high_velocity")
        
        # Amount threshold check
        amount_check = self._check_amount_threshold(float(amount), currency)
        if not amount_check["passed"]:
            risk_score += 20
            risk_factors.append("high_amount")
        
        # User history check
        user_check = self._check_user_history(user_id)
        if not user_check["passed"]:
            risk_score += 15
            risk_factors.append(user_check["reason"])
        
        # Payment method risk
        method_risk = self._assess_payment_method_risk(payment_method)
        risk_score += method_risk["score"]
        if method_risk["score"] > 0:
            risk_factors.append(f"payment_method_{payment_method}")
        
        # Geographic location check (if IP provided)
        if ip_address:
            geo_check = self._check_geographic_risk(ip_address, billing_address)
            risk_score += geo_check["score"]
            if geo_check["score"] > 0:
                risk_factors.extend(geo_check.get("factors", []))
        
        # Device fingerprint check
        if device_fingerprint:
            device_check = self._check_device_fingerprint(user_id, device_fingerprint)
            if not device_check["passed"]:
                risk_score += 10
                risk_factors.append("new_device")
        
        # Failed payment history
        failed_check = self._check_failed_payment_history(user_id)
        risk_score += failed_check["score"]
        if failed_check["score"] > 0:
            risk_factors.append("previous_failures")
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "critical"
            approved = False
        elif risk_score >= 50:
            risk_level = "high"
            approved = False  # Require manual review
        elif risk_score >= 30:
            risk_level = "medium"
            approved = True  # Proceed with extra verification
        else:
            risk_level = "low"
            approved = True
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "approved": approved,
            "risk_factors": risk_factors,
            "checks": {
                "velocity": velocity_check,
                "amount": amount_check,
                "user_history": user_check,
                "payment_method": method_risk,
                "failed_payments": failed_check
            },
            "requires_verification": risk_score >= 30 or float(amount) > self.verification_threshold,
            "requires_manual_review": risk_score >= 50
        }
    
    # ============================================================================
    # INDIVIDUAL CHECKS
    # ============================================================================
    
    def _check_payment_velocity(self, user_id: int) -> Dict[str, Any]:
        """Check if user has made too many payment attempts recently"""
        
        if not self.velocity_check_enabled:
            return {"passed": True, "attempts": 0}
        
        # Count payment attempts in last 24 hours
        since = datetime.utcnow() - timedelta(days=1)
        
        attempts = self.db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.created_at >= since
        ).count()
        
        passed = attempts < self.max_attempts_per_day
        
        return {
            "passed": passed,
            "attempts": attempts,
            "max_allowed": self.max_attempts_per_day,
            "period": "24_hours"
        }
    
    def _check_amount_threshold(self, amount: float, currency: str) -> Dict[str, Any]:
        """Check if amount exceeds verification threshold"""
        
        # Convert to EUR if different currency (simplified)
        amount_eur = amount if currency == "EUR" else amount * 1.1  # Rough conversion
        
        passed = amount_eur <= self.verification_threshold
        
        return {
            "passed": passed,
            "amount": amount_eur,
            "threshold": self.verification_threshold,
            "requires_verification": not passed
        }
    
    def _check_user_history(self, user_id: int) -> Dict[str, Any]:
        """Check user's payment history for suspicious patterns"""
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"passed": False, "reason": "user_not_found"}
        
        # Check if user is new (created < 7 days ago)
        if user.created_at and (datetime.utcnow() - user.created_at).days < 7:
            return {
                "passed": False,
                "reason": "new_user",
                "account_age_days": (datetime.utcnow() - user.created_at).days
            }
        
        # Check successful payment history
        successful_payments = self.db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.SUCCEEDED
        ).count()
        
        if successful_payments == 0:
            return {
                "passed": False,
                "reason": "no_successful_payments",
                "successful_count": 0
            }
        
        return {
            "passed": True,
            "successful_payments": successful_payments,
            "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0
        }
    
    def _assess_payment_method_risk(self, payment_method: str) -> Dict[str, int]:
        """Assess risk level of payment method"""
        
        # Risk scores for different payment methods
        method_risks = {
            "cryptocurrency": 15,  # Higher risk due to irreversibility
            "bitcoin": 15,
            "ethereum": 15,
            "usdt": 15,
            "prepaid_card": 10,
            "credit_card": 0,
            "debit_card": 0,
            "bank_transfer": 0,
            "sepa_debit": 0,
            "paypal": 0
        }
        
        score = method_risks.get(payment_method.lower(), 5)
        
        return {"score": score, "payment_method": payment_method}
    
    def _check_geographic_risk(
        self,
        ip_address: str,
        billing_address: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check for geographic anomalies
        
        In production, integrate with IP geolocation service
        """
        
        # Simplified implementation - in production use MaxMind GeoIP2 or similar
        
        # High-risk countries (example list)
        high_risk_countries = ["XX", "YY"]  # Replace with actual country codes
        
        # For now, return low risk
        # In production, lookup IP location and compare with billing address
        
        return {
            "score": 0,
            "factors": [],
            "ip_country": "Unknown",
            "billing_country": billing_address.get("country") if billing_address else "Unknown"
        }
    
    def _check_device_fingerprint(
        self,
        user_id: int,
        device_fingerprint: str
    ) -> Dict[str, Any]:
        """Check if device fingerprint is recognized for user"""
        
        # In production, maintain a table of known device fingerprints per user
        # For now, hash the fingerprint and check if it's in user metadata
        
        fingerprint_hash = hashlib.sha256(device_fingerprint.encode()).hexdigest()[:16]
        
        # Check if this device has been used by user before
        # (Simplified - in production, maintain separate device_fingerprints table)
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"passed": False, "is_new_device": True}
        
        # For MVP, accept all devices
        return {"passed": True, "is_new_device": False, "fingerprint_hash": fingerprint_hash}
    
    def _check_failed_payment_history(self, user_id: int) -> Dict[str, int]:
        """Check user's failed payment history"""
        
        # Count failed payments in last 30 days
        since = datetime.utcnow() - timedelta(days=30)
        
        failed_count = self.db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.FAILED,
            Payment.created_at >= since
        ).count()
        
        # Score based on failed attempts
        if failed_count >= 5:
            score = 20
        elif failed_count >= 3:
            score = 10
        elif failed_count >= 1:
            score = 5
        else:
            score = 0
        
        return {
            "score": score,
            "failed_count": failed_count,
            "period_days": 30
        }
    
    # ============================================================================
    # FRAUD REPORTING AND LOGGING
    # ============================================================================
    
    def log_fraud_alert(
        self,
        user_id: int,
        payment_id: Optional[int],
        risk_assessment: Dict[str, Any],
        action_taken: str
    ) -> None:
        """Log fraud detection alert"""
        
        from app.models.billing import BillingEvent
        
        event = BillingEvent(
            user_id=user_id,
            payment_id=payment_id,
            event_type="fraud_alert",
            description=f"Fraud risk detected: {risk_assessment['risk_level']} ({risk_assessment['risk_score']})",
            metadata={
                "risk_assessment": risk_assessment,
                "action_taken": action_taken
            }
        )
        
        self.db.add(event)
        self.db.commit()
    
    def block_payment(
        self,
        user_id: int,
        reason: str,
        duration_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Temporarily block user from making payments
        
        Used when fraud is detected or suspected
        """
        
        # In production, implement proper payment blocking mechanism
        # For now, just log the event
        
        from app.models.billing import BillingEvent
        
        event = BillingEvent(
            user_id=user_id,
            event_type="payment_blocked",
            description=f"Payment blocked: {reason}",
            metadata={
                "reason": reason,
                "duration_hours": duration_hours,
                "blocked_until": (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat()
            }
        )
        
        self.db.add(event)
        self.db.commit()
        
        return {
            "blocked": True,
            "reason": reason,
            "duration_hours": duration_hours
        }
    
    # ============================================================================
    # VERIFICATION METHODS
    # ============================================================================
    
    def require_3ds_verification(self, payment_id: str) -> bool:
        """
        Determine if 3D Secure verification is required
        
        Based on:
        - Amount threshold
        - Risk score
        - European SCA requirements
        """
        
        # In Europe, SCA (Strong Customer Authentication) is required for most online payments
        # 3DS2 is the standard implementation
        
        # For amounts over threshold or high-risk payments, always require 3DS
        return True  # In production, implement more sophisticated logic
    
    def verify_cvv(self, card_cvv: str, stored_cvv_hash: str) -> bool:
        """
        Verify CVV (Card Verification Value)
        
        Note: Never store actual CVV, only compare hashes
        """
        
        # Hash provided CVV
        cvv_hash = hashlib.sha256(card_cvv.encode()).hexdigest()
        
        # Compare with stored hash
        return cvv_hash == stored_cvv_hash
    
    def verify_address(
        self,
        billing_address: Dict[str, Any],
        card_address: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AVS (Address Verification System) check
        
        Compares billing address with card address
        """
        
        matches = {
            "street": billing_address.get("street") == card_address.get("street"),
            "postal_code": billing_address.get("postal_code") == card_address.get("postal_code"),
            "city": billing_address.get("city") == card_address.get("city"),
            "country": billing_address.get("country") == card_address.get("country")
        }
        
        match_count = sum(matches.values())
        total_fields = len(matches)
        match_percentage = (match_count / total_fields) * 100
        
        return {
            "passed": match_percentage >= 75,  # Require 75% match
            "match_percentage": match_percentage,
            "matches": matches
        }
