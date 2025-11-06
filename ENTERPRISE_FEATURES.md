# Enterprise Features Documentation

## Overview

The Fernando Platform has been enhanced with comprehensive enterprise features including multi-tenancy, advanced user management, batch processing, export/import capabilities, audit trails, rate limiting, and job scheduling.

## Table of Contents

1. [Multi-Tenant Support](#multi-tenant-support)
2. [Advanced User Management](#advanced-user-management)
3. [Batch Processing & Queue Management](#batch-processing--queue-management)
4. [Export/Import Functionality](#exportimport-functionality)
5. [Audit Trails & Compliance](#audit-trails--compliance)
6. [API Rate Limiting](#api-rate-limiting)
7. [Role-Based Access Control](#role-based-access-control)
8. [Job Scheduling & Automation](#job-scheduling--automation)

## Multi-Tenant Support

### Overview
Full data isolation between tenants using `tenant_id` across all database tables.

### Features
- Complete data isolation between tenants
- Tenant-specific configurations and limits
- Quota management per tenant
- Tenant-based access control

### API Endpoints

#### Create Tenant
```bash
POST /api/v1/enterprise/tenants
Authorization: Bearer {token}

{
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Main tenant for Acme Corp",
    "subscription_plan": "professional",
    "max_users": 50,
    "max_jobs_per_month": 5000,
    "max_storage_gb": 25
}
```

#### List Tenants
```bash
GET /api/v1/enterprise/tenants
Authorization: Bearer {token}
```

#### Get Tenant Details
```bash
GET /api/v1/enterprise/tenants/{tenant_id}
Authorization: Bearer {token}
```

#### Update Tenant
```bash
PUT /api/v1/enterprise/tenants/{tenant_id}
Authorization: Bearer {token}

{
    "subscription_plan": "enterprise",
    "max_users": 100,
    "max_jobs_per_month": 10000,
    "features": {
        "advanced_analytics": true,
        "api_access": true
    }
}
```

## Advanced User Management

### Overview
Enhanced user management with groups, permissions, and hierarchical access control.

### Features
- Group-based permissions
- Direct user permissions (overrides groups)
- User status management (active, disabled, pending)
- Multi-factor authentication support
- Account lockout protection

### Group Management

#### Create Group
```bash
POST /api/v1/enterprise/groups
Authorization: Bearer {token}

{
    "name": "Department Managers",
    "description": "Managers with department oversight",
    "parent_group_id": null
}
```

#### Add User to Group
```bash
POST /api/v1/enterprise/groups/{group_id}/members
Authorization: Bearer {token}

{
    "user_id": "uuid-user-id"
}
```

### Permission Management

#### Check User Permissions
```bash
GET /api/v1/enterprise/users/{user_id}/permissions
Authorization: Bearer {token}
```

#### Check Specific Permission
```bash
POST /api/v1/enterprise/permissions/check
Authorization: Bearer {token}

{
    "user_id": "uuid-user-id",
    "permission_name": "job.approve"
}
```

#### Available Permissions
- `job.create`, `job.read`, `job.update`, `job.delete`, `job.approve`
- `document.create`, `document.read`, `document.update`, `document.delete`
- `user.read`, `user.create`, `user.update`, `user.delete`
- `admin.tenant`, `admin.groups`, `admin.reports`, `admin.system`
- `export.create`, `export.read`, `export.manage`
- `audit.read`, `audit.read_all`

## Batch Processing & Queue Management

### Overview
Advanced job queue management with batch processing capabilities and multiple priority queues.

### Features
- Multiple job queues with different priorities
- Batch job processing
- Worker management
- Queue statistics and monitoring

### Batch Operations

#### Create Batch Job
```bash
POST /api/v1/queue/batches
Authorization: Bearer {token}

{
    "job_ids": ["uuid1", "uuid2", "uuid3"],
    "batch_name": "Monthly Processing Batch"
}
```

#### Get Batch Status
```bash
GET /api/v1/queue/batches/{batch_id}
Authorization: Bearer {token}
```

### Queue Management

#### Start/Stop Queue Workers
```bash
POST /api/v1/queue/start-worker/default
Authorization: Bearer {admin-token}

POST /api/v1/queue/stop-worker/default
Authorization: Bearer {admin-token}
```

#### Create Custom Queue
```bash
POST /api/v1/queue/queues
Authorization: Bearer {admin-token}

{
    "name": "high-priority",
    "description": "High priority processing queue",
    "max_concurrent_jobs": 3,
    "max_retries": 1,
    "timeout_seconds": 1800
}
```

#### Get Queue Statistics
```bash
GET /api/v1/queue/statistics
Authorization: Bearer {token}
```

## Export/Import Functionality

### Overview
Comprehensive export/import capabilities supporting multiple formats (CSV, Excel, JSON, PDF).

### Export Features
- Multiple data types (jobs, documents, extractions, audit logs)
- Various formats (CSV, Excel, JSON, PDF)
- Custom filters and date ranges
- Batch export processing

#### Create Export Job
```bash
POST /api/v1/export-import/exports
Authorization: Bearer {token}

{
    "export_type": "jobs",
    "export_format": "excel",
    "filters": {
        "status": ["completed", "failed"],
        "date_from": "2024-01-01",
        "date_to": "2024-12-31"
    }
}
```

#### Execute Export
```bash
POST /api/v1/export-import/exports/{export_id}/execute
Authorization: Bearer {token}
```

#### Download Export File
```bash
GET /api/v1/export-import/exports/{export_id}/download
Authorization: Bearer {token}
```

### Import Features
- Bulk import of jobs and users
- Template generation
- Validation and error reporting
- Progress tracking

#### Import Data
```bash
POST /api/v1/export-import/imports?import_type=jobs
Authorization: Bearer {admin-token}
Content-Type: multipart/form-data

file: [CSV file upload]
```

#### Get Import Template
```bash
GET /api/v1/export-import/templates/jobs
Authorization: Bearer {token}
```

## Audit Trails & Compliance

### Overview
Comprehensive audit logging with compliance reporting capabilities.

### Features
- Complete audit trail for all actions
- Risk level assessment
- Compliance tagging (GDPR, SOX, HIPAA)
- Automated compliance reports

#### Create Audit Log
```bash
POST /api/v1/enterprise/audit/log
Authorization: Bearer {token}

{
    "action": "update",
    "resource_type": "job",
    "resource_id": "uuid-job-id",
    "old_values": {"status": "pending"},
    "new_values": {"status": "approved"},
    "risk_level": "medium",
    "compliance_tags": ["GDPR"]
}
```

#### Get Audit Logs
```bash
GET /api/v1/enterprise/audit/logs?limit=100&offset=0
Authorization: Bearer {token}
```

#### Get Compliance Summary
```bash
GET /api/v1/enterprise/compliance/summary?period_days=30
Authorization: Bearer {token}
```

### Audit Log Fields
- `audit_id`: Unique identifier
- `user_id`: User who performed the action
- `action`: Type of action (create, update, delete, login, etc.)
- `resource_type`: Type of resource affected
- `resource_id`: Specific resource ID
- `old_values`: Previous state (for updates)
- `new_values`: New state (for updates)
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `risk_level`: Risk assessment (low, medium, high, critical)
- `compliance_tags`: Compliance framework tags

## API Rate Limiting

### Overview
Configurable rate limiting per tenant and endpoint with quota management.

### Features
- Per-endpoint rate limits
- Burst protection
- Quota tracking
- Usage analytics

#### Check Rate Limit Status
```bash
GET /api/v1/enterprise/rate-limit/jobs
Authorization: Bearer {token}
```

#### Create Rate Limit Rule
```bash
POST /api/v1/enterprise/rate-limit
Authorization: Bearer {admin-token}

{
    "endpoint_pattern": "jobs",
    "requests_per_hour": 500,
    "requests_per_day": 10000,
    "burst_limit": 50
}
```

### Default Rate Limits
- General API: 100 requests/minute
- File upload: 10 requests/minute
- Export: 5 requests/hour
- Admin endpoints: 50 requests/minute

## Role-Based Access Control

### Overview
Enhanced RBAC with resource-specific permissions and scope control.

### Permission Scopes
- `own`: Access to own resources only
- `tenant`: Access to all tenant resources
- `all`: System-wide access (system admins only)

### Default Roles
- **User**: Basic access to own jobs and documents
- **Reviewer**: Can approve jobs and view tenant data
- **Auditor**: Read-only access to audit logs and compliance reports
- **Admin**: Full system administration access

### Permission Inheritance
1. Direct user permissions (highest priority)
2. Group permissions
3. Default role permissions
4. Deny by default

## Job Scheduling & Automation

### Overview
Advanced scheduling capabilities with recurring tasks and automation.

### Features
- Cron-based scheduling
- Recurring task execution
- Task history and logging
- Manual task triggers

#### Create Scheduled Task
```bash
POST /api/v1/queue/scheduled-tasks
Authorization: Bearer {admin-token}

{
    "name": "Daily Report Generation",
    "task_type": "report",
    "schedule_cron": "0 9 * * *",  # Daily at 9 AM
    "config": {
        "report_type": "daily_summary",
        "email_recipients": ["admin@company.com"]
    }
}
```

#### List Scheduled Tasks
```bash
GET /api/v1/queue/scheduled-tasks
Authorization: Bearer {token}
```

#### Manually Run Task
```bash
POST /api/v1/queue/scheduled-tasks/{task_id}/run
Authorization: Bearer {admin-token}
```

### Supported Task Types
- `export`: Generate and send exports
- `cleanup`: Clean up old files and data
- `report`: Generate compliance reports
- `webhook`: Trigger external webhooks

## Migration Guide

### Running the Migration
```bash
cd /workspace/fernando/backend
python migrate_enterprise.py
```

### Migration Steps
1. Creates enterprise tables
2. Adds tenant_id columns to existing tables
3. Creates database indexes for performance
4. Initializes default permissions and groups
5. Creates default tenant for existing data

### Post-Migration
After migration, all existing users and jobs will be assigned to the default tenant for backward compatibility.

## Security Considerations

### Data Isolation
- All queries automatically filter by tenant_id
- Cross-tenant access is prevented at the database level
- Tenant boundaries are enforced in all API endpoints

### Permission Validation
- Every API endpoint validates user permissions
- Permission checks are cached for performance
- Failed permission checks are logged for audit

### Rate Limiting
- Rate limits are enforced per tenant
- Burst protection prevents abuse
- Rate limit violations are logged

## Performance Optimization

### Database Indexes
All enterprise tables include appropriate indexes:
- tenant_id indexes for multi-tenant queries
- Created_at indexes for time-based queries
- Status indexes for filtering

### Caching
- Permission checks are cached
- Quota usage is cached
- Rate limit counters are cached

### Batch Operations
- Bulk database operations for better performance
- Async processing for long-running tasks
- Queue-based processing for scalability

## Monitoring & Observability

### Health Checks
```bash
GET /api/v1/system/status
```

### Key Metrics
- Queue statistics
- Quota usage per tenant
- Rate limit violations
- Audit log volume
- Error rates

### Logging
- All enterprise actions are logged
- Security events are flagged
- Performance metrics are tracked

## Future Enhancements

### Planned Features
- Real-time notifications
- Advanced analytics dashboard
- Integration APIs for third-party systems
- Mobile application support
- Advanced reporting templates

### Extensibility
- Plugin architecture for custom features
- Custom field support
- Workflow automation
- API versioning support

## Support and Troubleshooting

### Common Issues

#### Permission Denied
- Check user roles and group memberships
- Verify tenant assignment
- Review permission inheritance

#### Rate Limit Exceeded
- Check rate limit status endpoint
- Reduce request frequency
- Consider upgrading plan

#### Migration Issues
- Backup database before running migration
- Check database connection
- Review error logs

### Getting Help
- Check API documentation at `/docs`
- Review audit logs for security issues
- Monitor system status endpoint
- Contact system administrator for permission issues
