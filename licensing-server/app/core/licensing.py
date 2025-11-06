import uuid
import hashlib
import platform
import psutil
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings


def get_hardware_fingerprint() -> str:
    """Generate hardware fingerprint for license validation"""
    # Get system info
    system_info = {
        'platform': platform.system(),
        'machine': platform.machine(),
        'processor': platform.processor(),
    }
    
    # Get CPU info
    try:
        cpu_count = psutil.cpu_count(logical=False)
        system_info['cpu_count'] = cpu_count
    except:
        pass
    
    # Create fingerprint hash
    fingerprint_string = '|'.join(str(v) for v in system_info.values())
    fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    return fingerprint


def create_license_token(
    license_id: str,
    user_id: str,
    tier: str,
    hardware_fingerprint: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a license JWT token"""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.LICENSE_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": license_id,
        "user_id": user_id,
        "tier": tier,
        "hardware_fingerprint": hardware_fingerprint,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "license"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_license_token(token: str, hardware_fingerprint: str) -> dict:
    """Verify and decode license token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "license":
            raise ValueError("Invalid token type")
        
        # Verify hardware fingerprint
        if payload.get("hardware_fingerprint") != hardware_fingerprint:
            raise ValueError("Hardware fingerprint mismatch")
        
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid license token: {str(e)}")


def get_tier_limits(tier: str) -> dict:
    """Get usage limits for a license tier"""
    limits = {
        "free": {
            "docs_per_month": settings.FREE_TIER_DOCS_PER_MONTH,
            "features": ["basic_ocr", "basic_extraction"],
            "concurrent_jobs": 1
        },
        "pro": {
            "docs_per_month": settings.PRO_TIER_DOCS_PER_MONTH,
            "features": ["advanced_ocr", "llm_extraction", "toconline_integration"],
            "concurrent_jobs": 5
        },
        "enterprise": {
            "docs_per_month": settings.ENTERPRISE_TIER_DOCS_PER_MONTH,
            "features": ["all"],
            "concurrent_jobs": -1,  # Unlimited
            "custom_integrations": True
        }
    }
    
    return limits.get(tier, limits["free"])
