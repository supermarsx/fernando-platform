# Licensing Management System - Complete Implementation Guide

## Overview

The Fernando Platform now includes a comprehensive licensing management system that supports multiple license tiers, feature gating, usage tracking, and enterprise billing integration.

## License Tiers

### 1. Basic Tier
- **Price**: $29.99/month or $299.99/year
- **Documents**: 100 per month
- **Users**: Up to 3
- **Storage**: 5 GB
- **Features**:
  - Document processing
  - OCR extraction
  - LLM extraction
  - Standard support

### 2. Professional Tier
- **Price**: $99.99/month or $999.99/year
- **Documents**: 1,000 per month
- **Users**: Up to 10
- **Storage**: 50 GB
- **Features**:
  - All Basic features
  - Batch processing
  - API access
  - Advanced analytics
  - Priority email support

### 3. Enterprise Tier
- **Price**: $299.99/month or $2,999.99/year
- **Documents**: Unlimited
- **Users**: Unlimited
- **Storage**: Unlimited
- **Features**:
  - All Professional features
  - Custom integrations
  - Priority support
  - White label options
  - Dedicated account manager

## Backend Implementation

### Database Schema

The licensing system adds the following tables:

1. **license_tiers**: Defines available license tiers with features and limits
2. **licenses**: Stores individual license records
3. **license_assignments**: Maps licenses to users
4. **license_usage**: Tracks feature usage for billing and analytics
5. **license_audit_logs**: Compliance and audit trail

### API Endpoints

All licensing endpoints are prefixed with `/api/v1/licenses`:

#### License Tier Management (Admin Only)
- `GET /tiers` - List all license tiers
- `POST /tiers` - Create new license tier
- `PUT /tiers/{tier_id}` - Update license tier

#### License Management
- `GET /licenses` - List all licenses (Admin)
- `POST /licenses` - Create new license (Admin)
- `GET /licenses/{license_id}` - Get license details
- `PUT /licenses/{license_id}` - Update license (Admin)
- `POST /licenses/validate` - Validate license key
- `POST /licenses/{license_id}/renew` - Renew license (Admin)
- `POST /licenses/{license_id}/upgrade` - Upgrade license tier (Admin)
- `POST /licenses/{license_id}/suspend` - Suspend license (Admin)
- `POST /licenses/{license_id}/revoke` - Revoke license (Admin)

#### Analytics
- `GET /licenses/analytics/overview` - Get licensing analytics (Admin)

#### Initialization
- `POST /licenses/initialize-tiers` - Initialize default license tiers (Admin)

### Licensing Service

The `LicensingService` class provides:

**Core Functions:**
- `create_license()` - Generate new license with unique key
- `validate_license()` - Validate license key and check expiration
- `check_feature_access()` - Verify feature availability for license
- `check_usage_limit()` - Validate usage limits (documents, users, storage)
- `increment_usage()` - Track feature usage
- `renew_license()` - Extend license validity
- `upgrade_license()` - Change license tier
- `suspend_license()` - Temporarily disable license
- `revoke_license()` - Permanently disable license
- `get_license_analytics()` - Generate analytics reports

**License Key Format:**
```
XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
```
- 32 character SHA-256 hash
- Formatted in 8 groups of 4 characters
- Unique and cryptographically secure

### Feature Gating

Features are controlled through the `features` JSON field in license tiers:

```json
{
  "document_processing": true,
  "ocr_extraction": true,
  "llm_extraction": true,
  "batch_processing": true,
  "api_access": true,
  "custom_integrations": false,
  "priority_support": false,
  "advanced_analytics": true
}
```

**Usage in Code:**
```python
from app.services.licensing_service import LicensingService

licensing_service = LicensingService(db)

# Check feature access
has_access = licensing_service.check_feature_access(
    license_id=license_id,
    feature_name="batch_processing"
)

if not has_access:
    raise HTTPException(
        status_code=403,
        detail="This feature is not available in your license tier"
    )
```

### Usage Tracking

Track feature usage for billing and analytics:

```python
licensing_service.increment_usage(
    license_id=license_id,
    usage_type="documents",
    count=1,
    user_id=current_user.user_id,
    metadata={"document_id": doc_id}
)
```

### Offline Validation

Licenses support offline validation through hardware fingerprinting:

```python
validation_request = LicenseValidationRequest(
    license_key="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
    hardware_fingerprint="sha256_hash_of_hardware_id"
)

result = licensing_service.validate_license(validation_request)
```

## Frontend Implementation

### Admin License Management UI

Located at `/admin/licenses`, provides:

- **License Dashboard**: Overview of all licenses with statistics
- **License Search**: Filter by organization, status, tier
- **License Actions**:
  - View details
  - Edit license info
  - Renew license
  - Upgrade/downgrade tier
  - Suspend/revoke license
- **Usage Analytics**: Document usage, user count tracking
- **Export Functionality**: Export license data for reporting

### License Status Component

The `LicenseStatusCard` component displays:
- Current tier and status
- Expiration countdown
- Document usage (current month)
- User count
- Warning notifications for approaching limits

**Usage:**
```tsx
import { LicenseStatusCard } from '@/components/LicenseStatusCard';

<LicenseStatusCard
  license={{
    tier_name: "professional",
    tier_display: "Professional",
    status: "active",
    expires_at: "2026-01-01T00:00:00Z",
    documents_used: 450,
    documents_limit: 1000,
    users_count: 5,
    users_limit: 10
  }}
/>
```

## Database Migration

Run the licensing migration to create tables:

```bash
cd /workspace/fernando/backend
alembic upgrade head
```

Or initialize directly through the API:
```bash
curl -X POST http://localhost:8000/api/v1/licenses/initialize-tiers \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Usage Examples

### 1. Create a New License (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/licenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "tier_id": 2,
    "organization_name": "Acme Corporation",
    "organization_email": "admin@acme.com",
    "expires_at": "2026-01-01T00:00:00Z",
    "max_activations": 3,
    "metadata": {
      "contact_person": "John Doe",
      "department": "Finance"
    }
  }'
```

### 2. Validate a License

```bash
curl -X POST http://localhost:8000/api/v1/licenses/validate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
    "hardware_fingerprint": "optional_hw_fingerprint"
  }'
```

### 3. Renew a License (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/licenses/123/renew \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "license_id": 123,
    "renewal_period_months": 12
  }'
```

### 4. Upgrade License Tier (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/licenses/123/upgrade \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "license_id": 123,
    "new_tier_id": 3
  }'
```

### 5. Get License Analytics (Admin)

```bash
curl -X GET http://localhost:8000/api/v1/licenses/analytics/overview \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Integration with Application Features

### Document Processing with License Validation

```python
from app.services.licensing_service import LicensingService

@router.post("/api/v1/jobs/upload")
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's license
    license = get_user_license(db, current_user.user_id)
    
    # Check usage limits
    licensing_service = LicensingService(db)
    usage_check = licensing_service.check_usage_limit(
        license_id=license.license_id,
        limit_type="documents"
    )
    
    if not usage_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Document limit reached: {usage_check['reason']}"
        )
    
    # Process document
    job = process_document(file)
    
    # Increment usage counter
    licensing_service.increment_usage(
        license_id=license.license_id,
        usage_type="documents",
        count=1,
        user_id=current_user.user_id
    )
    
    return job
```

### Feature Gating Middleware

```python
def require_license_feature(feature_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get license from request context
            license = get_current_license()
            
            licensing_service = LicensingService(db)
            has_access = licensing_service.check_feature_access(
                license_id=license.license_id,
                feature_name=feature_name
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature_name}' not available in your license tier"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@router.post("/api/v1/jobs/batch")
@require_license_feature("batch_processing")
async def batch_process_documents(...):
    # This endpoint only accessible to Professional/Enterprise tiers
    pass
```

## Compliance and Audit

All licensing actions are automatically logged in `license_audit_logs`:

- License creation
- License validation attempts
- License renewals
- Tier upgrades/downgrades
- License suspensions/revocations
- Usage limit violations

Access audit logs:
```sql
SELECT * FROM license_audit_logs
WHERE license_id = 123
ORDER BY timestamp DESC;
```

## Monitoring and Alerts

Set up monitoring for:

1. **Expiring Licenses**: Alert 30 days before expiration
2. **Usage Limit Approaching**: Alert at 80% and 90% thresholds
3. **Suspended Licenses**: Daily report of suspended licenses
4. **Failed Validations**: Monitor for potential issues

## Best Practices

1. **License Key Security**: Store license keys securely, never in client-side code
2. **Regular Validation**: Validate licenses on each API request or daily
3. **Usage Tracking**: Track all billable features accurately
4. **Audit Compliance**: Regularly review audit logs for compliance
5. **Expiration Notifications**: Send renewal reminders 60, 30, and 7 days before expiration
6. **Tier Recommendations**: Suggest upgrades when users approach limits

## Troubleshooting

### Common Issues

**"License has expired"**
- Solution: Renew license through admin panel or API

**"Monthly document limit reached"**
- Solution: Upgrade to higher tier or wait for monthly reset

**"Feature not available in your license tier"**
- Solution: Upgrade license tier to access feature

**"Hardware fingerprint mismatch"**
- Solution: Reset hardware fingerprint or increase max_activations

## Future Enhancements

Planned features:
- Automated renewal with payment integration
- License pooling for organizations
- Trial license generation
- Usage-based billing
- Custom license terms and restrictions
- License transfer between organizations
- Multi-factor license validation

## Files Created

### Backend
- `/workspace/fernando/backend/app/models/license.py`
- `/workspace/fernando/backend/app/schemas/license_schemas.py`
- `/workspace/fernando/backend/app/services/licensing_service.py`
- `/workspace/fernando/backend/app/api/licenses.py`
- `/workspace/fernando/backend/migrations/versions/004_add_licensing.py`

### Frontend
- `/workspace/fernando/frontend/accounting-frontend/src/pages/LicenseManagementPage.tsx`
- `/workspace/fernando/frontend/accounting-frontend/src/components/LicenseStatusCard.tsx`

### Updated Files
- `/workspace/fernando/backend/app/main.py` - Added licensing routes and initialization
- `/workspace/fernando/frontend/accounting-frontend/src/App.tsx` - Added license management route

## Support

For licensing questions or issues:
- Admin Dashboard: `/admin/licenses`
- API Documentation: `/docs`
- Contact: support@fernando.com
