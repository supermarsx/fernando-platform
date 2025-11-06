# Fernando Platform Alerting System

A comprehensive, enterprise-grade alerting system for monitoring system health, application performance, business metrics, and security events.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [API Documentation](#api-documentation)
7. [Alert Types](#alert-types)
8. [Notification Channels](#notification-channels)
9. [Escalation Management](#escalation-management)
10. [Frontend Interface](#frontend-interface)
11. [Background Jobs](#background-jobs)
12. [Monitoring & Health](#monitoring--health)
13. [Best Practices](#best-practices)
14. [Troubleshooting](#troubleshooting)

## Overview

The Fernando Alerting System provides comprehensive monitoring and alerting capabilities for the entire platform. It features intelligent rule evaluation, multi-channel notifications, automated escalation, and real-time dashboard monitoring.

### Key Benefits

- **Comprehensive Coverage**: Monitor system, application, business, and security metrics
- **Intelligent Escalation**: Automatic escalation based on time, severity, and response patterns
- **Multi-Channel Notifications**: Email, Slack, Discord, webhooks, SMS, and push notifications
- **Real-time Dashboard**: Live monitoring interface with filtering and management capabilities
- **Background Processing**: Celery-based background jobs for reliable alert processing
- **Enterprise Ready**: Multi-tenant support with role-based access control

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Alert Rules   │────│  Alert Engine    │────│  Alert Manager  │
│                 │    │                  │    │                 │
│ - Conditions    │    │ - Rule           │    │ - Trigger Alerts│
│ - Thresholds    │    │   Evaluation     │    │ - Notifications │
│ - Channels      │    │ - Data Sources   │    │ - Escalation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │ Notification     │
                    │ Channels         │
                    │                  │
                    │ - Email          │
                    │ - Slack          │
                    │ - Discord        │
                    │ - Webhook        │
                    │ - SMS            │
                    │ - Push           │
                    └──────────────────┘
```

## Features

### 1. Alert Rule Management
- **Dynamic Rule Creation**: Create custom rules with flexible conditions
- **Multiple Data Sources**: System, application, business, and custom metrics
- **Threshold Configuration**: Configure critical, high, medium, and warning thresholds
- **Time-based Rules**: Evaluate rules based on business hours, weekends, etc.
- **Template System**: Reusable alert templates for consistent notifications

### 2. Multi-Channel Notifications
- **Email**: Rich HTML formatted emails with context
- **Slack**: Interactive messages with action buttons
- **Discord**: Embedded messages with color coding
- **Webhooks**: JSON payloads for external system integration
- **SMS**: Critical alerts via SMS for immediate attention
- **Push**: Mobile push notifications for on-the-go monitoring

### 3. Intelligent Escalation
- **Time-based Escalation**: Automatic escalation after defined timeouts
- **Severity-based Escalation**: Different escalation paths per severity level
- **Response-based Escalation**: Escalate if not acknowledged in time
- **On-call Schedules**: Integration with on-call rotation schedules
- **Manager Notification**: Automatic manager escalation for high-priority alerts

### 4. Real-time Dashboard
- **Live Alert Monitoring**: Real-time alert status and updates
- **Filtering & Search**: Advanced filtering by status, severity, type, and time
- **Alert Management**: Acknowledge, resolve, and suppress alerts
- **Statistics & Analytics**: Alert trends, resolution times, and performance metrics
- **Bulk Operations**: Manage multiple alerts simultaneously

### 5. Background Processing
- **Celery Integration**: Reliable background job processing
- **Scheduled Evaluations**: Automatic rule evaluation at defined intervals
- **Notification Retry**: Automatic retry of failed notifications
- **Cleanup Tasks**: Automatic cleanup of old alerts and notifications
- **Health Monitoring**: Continuous monitoring of the alerting system itself

## Installation

### 1. Database Migration

```bash
# Run the alert system migration
cd backend
alembic upgrade 009_add_alerting_system
```

### 2. Initialize Alert System

```bash
# Initialize default rules, templates, and configurations
python initialize_alert_system.py
```

### 3. Configure Background Jobs

Add to your celery configuration:

```python
# celery_app.py
from app.services.alerting.background_jobs import celery_app, beat_schedule

celery_app.conf.beat_schedule = beat_schedule
```

### 4. Start Services

```bash
# Start the FastAPI server
python main.py

# Start Celery worker
celery -A app.services.alerting.background_jobs worker --loglevel=info

# Start Celery beat scheduler
celery -A app.services.alerting.background_jobs beat --loglevel=info
```

## Configuration

### Environment Variables

```bash
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_DEFAULT_CHANNEL=#alerts

# Discord Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890

# Push Notifications
FIREBASE_SERVER_KEY=your-firebase-key
APNS_KEY=your-apns-key

# Webhook Configuration
WEBHOOK_TIMEOUT=30
WEBHOOK_RETRY_COUNT=3

# System Settings
BASE_URL=https://your-domain.com
MANAGER_EMAIL=manager@yourcompany.com
```

### Alert Rule Configuration

Create custom alert rules via the API or initialization script:

```json
{
  "name": "High CPU Usage",
  "description": "Alert when CPU usage exceeds 80%",
  "alert_type": "system",
  "severity": "high",
  "condition": {
    "type": "threshold",
    "operator": "gt",
    "value": 80.0
  },
  "threshold_config": {
    "critical": 90.0,
    "high": 80.0,
    "warning": 70.0,
    "operator": "gt"
  },
  "query_config": {
    "metric_name": "cpu_usage",
    "data_source": "system",
    "filters": {"host": "*.prod.example.com"},
    "time_window": 300
  },
  "channels": ["slack", "email"],
  "recipients": {
    "slack": ["#ops-alerts"],
    "email": ["ops-team@example.com"]
  },
  "enabled": true,
  "evaluation_frequency": 60,
  "sustained_duration": 300,
  "cooldown_period": 600,
  "escalation_rules": {
    "time_based": {"timeouts": {"level_1": 15, "level_2": 30}},
    "acknowledgment_based": {"timeout_minutes": 15}
  }
}
```

## API Documentation

### Alert Management

#### Get All Alerts
```http
GET /api/v1/alerts/
```

Query Parameters:
- `status`: Filter by status (active, acknowledged, resolved, suppressed, escalated)
- `severity`: Filter by severity (critical, high, medium, low, info)
- `alert_type`: Filter by type (system, application, business, security, custom)
- `triggered_after`: Filter by trigger time (ISO 8601)
- `search`: Search in title and message

#### Create Alert
```http
POST /api/v1/alerts/
Content-Type: application/json

{
  "title": "Test Alert",
  "message": "This is a test alert",
  "severity": "medium",
  "alert_type": "system"
}
```

#### Acknowledge Alert
```http
POST /api/v1/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "note": "Investigating the issue"
}
```

#### Resolve Alert
```http
POST /api/v1/alerts/{alert_id}/resolve
Content-Type: application/json

{
  "resolution_notes": "Issue resolved, root cause identified"
}
```

### Alert Rules

#### Get All Rules
```http
GET /api/v1/alerts/rules/
```

#### Create Rule
```http
POST /api/v1/alerts/rules/
Content-Type: application/json

{
  "name": "High Memory Usage",
  "description": "Alert when memory usage exceeds 85%",
  "alert_type": "system",
  "severity": "high",
  "condition": {"type": "threshold", "operator": "gt", "value": 85.0},
  "channels": ["slack"],
  "enabled": true
}
```

#### Test Rule
```http
POST /api/v1/alerts/rules/{rule_id}/test
```

### Statistics & Analytics

#### Get Alert Statistics
```http
GET /api/v1/alerts/statistics?time_range_hours=24
```

#### Get System Health
```http
GET /api/v1/alerts/health
```

### Evaluation & Management

#### Trigger Rule Evaluation
```http
POST /api/v1/alerts/evaluate
```

#### Bulk Alert Operations
```http
POST /api/v1/alerts/bulk_action
Content-Type: application/json

{
  "alert_ids": ["alert1", "alert2", "alert3"],
  "action": "acknowledge",
  "notes": "Bulk acknowledgment"
}
```

## Alert Types

### 1. System Alerts
Monitor infrastructure and system-level metrics:

- **CPU Usage**: High CPU utilization affecting performance
- **Memory Usage**: Memory exhaustion or high usage
- **Disk Space**: Low disk space warnings
- **Network Latency**: Network connectivity issues
- **Database Connections**: Connection pool exhaustion
- **Load Average**: System load and resource contention

### 2. Application Alerts
Monitor application performance and functionality:

- **Error Rate**: High application error rates
- **Response Time**: Slow API response times
- **Throughput**: Changes in application throughput
- **Failed Requests**: HTTP error rate monitoring
- **Service Health**: Application service availability
- **Cache Performance**: Cache hit/miss ratios

### 3. Business Alerts
Monitor business-critical metrics:

- **Revenue Drops**: Significant revenue decreases
- **Conversion Rates**: Low conversion rate alerts
- **Payment Failures**: Failed payment processing
- **Subscription Issues**: Billing and subscription problems
- **Usage Anomalies**: Unusual usage patterns
- **Customer Churn**: Customer retention metrics

### 4. Security Alerts
Monitor security events and threats:

- **Failed Login Attempts**: Brute force attack detection
- **Unusual Access Patterns**: Anomalous user behavior
- **API Abuse**: Rate limit violations
- **Data Access Anomalies**: Unusual data access patterns
- **Security Events**: Firewall and intrusion detection
- **Compliance Violations**: Regulatory compliance issues

## Notification Channels

### Email Notifications
- **Rich HTML Formatting**: Professional email templates
- **Context Information**: Detailed alert context and metrics
- **Action Buttons**: Quick acknowledge/resolve actions
- **Runbook Links**: Direct links to resolution documentation

### Slack Integration
- **Interactive Messages**: Action buttons for acknowledge/resolve
- **Channel Routing**: Route alerts to appropriate channels
- **Mention Support**: Automatic mentions for on-call personnel
- **Emoji Indicators**: Visual severity indicators

### Discord Integration
- **Embed Formatting**: Rich embed messages with color coding
- **Webhook Integration**: Easy webhook setup for Discord servers
- **Role Mentions**: Automatic mentions for relevant roles
- **Thread Support**: Organize alerts in dedicated threads

### Webhook Notifications
- **JSON Payloads**: Structured data for external systems
- **Custom Headers**: Authentication and identification headers
- **Retry Logic**: Automatic retry for failed webhooks
- **External Integration**: Connect to incident management systems

### SMS Notifications
- **Critical Alerts Only**: SMS for highest priority alerts
- **Twilio Integration**: Professional SMS delivery
- **Phone Number Management**: Organize contact lists
- **Delivery Tracking**: SMS delivery confirmation

### Push Notifications
- **Mobile Apps**: Push notifications for mobile applications
- **Firebase FCM**: Google Firebase Cloud Messaging
- **Apple APNs**: Apple Push Notification service
- **Action Buttons**: Quick actions from notifications

## Escalation Management

### Escalation Policies
Define escalation paths based on alert characteristics:

```json
{
  "name": "Standard Escalation",
  "escalation_levels": [
    {
      "level": 1,
      "delay_minutes": 15,
      "actions": ["notify_team", "page_oncall"],
      "channels": ["slack", "email"]
    },
    {
      "level": 2,
      "delay_minutes": 30,
      "actions": ["notify_manager", "escalate_channel"],
      "channels": ["email", "sms"]
    }
  ]
}
```

### On-Call Schedules
Manage on-call rotations and schedules:

- **Rotation Types**: Daily, weekly, or custom rotations
- **Timezone Support**: Handle multiple timezones
- **Working Hours**: Configure business hours and holidays
- **Escalation Chains**: Define escalation paths
- **Automatic Assignment**: Rotate on-call assignments

### Escalation Actions
- **Notify Manager**: Email managers for high-priority alerts
- **Page On-Call**: SMS/phone pages for critical alerts
- **Create Incident**: Automatically create incident tickets
- **Escalate Channel**: Notify additional channels
- **Auto-Resolution**: Auto-resolve resolved alerts

## Frontend Interface

### Dashboard Features
- **Real-time Updates**: Live alert status updates
- **Filtering & Search**: Advanced alert filtering
- **Statistics**: Alert metrics and trends
- **Bulk Operations**: Manage multiple alerts
- **Responsive Design**: Works on desktop and mobile

### Rule Management
- **Rule Creation**: Visual rule builder
- **Testing**: Test rules before activation
- **Templates**: Reusable rule templates
- **Bulk Management**: Enable/disable multiple rules

### Configuration
- **Channel Settings**: Configure notification channels
- **Escalation Policies**: Define escalation rules
- **On-Call Schedules**: Manage rotation schedules
- **System Health**: Monitor alerting system health

## Background Jobs

### Scheduled Tasks
- **Rule Evaluation**: Evaluate all enabled rules every minute
- **Notification Processing**: Process and retry failed notifications
- **Escalation Checks**: Check for escalation conditions
- **Cleanup Tasks**: Clean up old alerts and notifications
- **Health Monitoring**: Monitor alerting system health

### Job Configuration
```python
# Celery Beat Schedule
beat_schedule = {
    'evaluate-alert-rules': {
        'task': 'app.services.alerting.background_jobs.evaluate_alert_rules',
        'schedule': 60.0,  # Every minute
        'options': {'queue': 'alert_evaluation'}
    },
    'process-notifications': {
        'task': 'app.services.alerting.background_jobs.process_pending_notifications',
        'schedule': 30.0,  # Every 30 seconds
        'options': {'queue': 'notifications'}
    }
}
```

### Job Monitoring
- **Worker Status**: Monitor Celery worker health
- **Task History**: Track task execution history
- **Error Handling**: Automatic retry with exponential backoff
- **Performance Metrics**: Track job execution times

## Monitoring & Health

### System Health Checks
Monitor the alerting system itself:

- **Database Connectivity**: Ensure database connections
- **Worker Status**: Monitor Celery worker health
- **Queue Health**: Check job queue status
- **Cache Performance**: Monitor cache hit rates
- **Notification Success**: Track notification delivery rates

### Health Metrics
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "workers": "healthy",
    "redis": "healthy",
    "notifications": "healthy"
  },
  "metrics": {
    "active_rules": 45,
    "pending_notifications": 3,
    "cache_size": 128,
    "evaluation_rate": "1/min"
  }
}
```

### Alerting System Alerts
The alerting system can monitor itself:

- **Worker Failures**: Alert if Celery workers fail
- **Database Issues**: Alert on database connection problems
- **High Queue Backlog**: Alert on notification queue buildup
- **Evaluation Delays**: Alert if rule evaluation is delayed
- **Notification Failures**: Alert on high notification failure rates

## Best Practices

### Rule Configuration
1. **Specific Conditions**: Make rules as specific as possible to reduce noise
2. **Appropriate Thresholds**: Set thresholds based on historical data
3. **Sustained Duration**: Use sustained duration to avoid flapping
4. **Cooldown Periods**: Set appropriate cooldown periods to prevent alert storms
5. **Runbook Links**: Always include runbook links for resolution procedures

### Notification Management
1. **Channel Selection**: Choose appropriate channels for each alert type
2. **Recipient Management**: Regularly review and update recipient lists
3. **Quiet Hours**: Configure quiet hours to avoid unnecessary notifications
4. **Escalation Paths**: Define clear escalation paths for different severities
5. **Test Regularly**: Test notification channels regularly

### Alert Response
1. **Acknowledge Quickly**: Acknowledge alerts promptly to stop escalation
2. **Document Actions**: Always add notes when acknowledging/resolving
3. **Follow Runbooks**: Use provided runbooks for consistent resolution
4. **Update Rules**: Update rules based on false positives/negatives
5. **Regular Reviews**: Review and tune rules regularly

### System Maintenance
1. **Regular Cleanup**: Clean up old alerts and notifications
2. **Rule Review**: Review and update rules quarterly
3. **Performance Monitoring**: Monitor system performance and scale as needed
4. **Backup Configuration**: Regularly backup rule configurations
5. **Documentation**: Keep runbooks and documentation updated

## Troubleshooting

### Common Issues

#### Rules Not Triggering
- Check if rule is enabled
- Verify query configuration and data sources
- Check evaluation frequency settings
- Review condition logic
- Check sustained duration requirements

#### Notifications Not Sending
- Verify channel configuration
- Check recipient lists
- Review notification templates
- Check authentication credentials
- Monitor notification retry logs

#### Escalation Issues
- Review escalation policy configuration
- Check on-call schedule setup
- Verify escalation timeouts
- Check notification channel health
- Review escalation action definitions

#### Performance Issues
- Monitor rule evaluation times
- Check background job queue health
- Review database query performance
- Monitor notification processing rate
- Check cache hit rates

### Debug Commands

#### Check Rule Status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/alerts/rules/"
```

#### Test Rule Evaluation
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/alerts/rules/{rule_id}/test"
```

#### Check System Health
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/alerts/health"
```

#### View Recent Alerts
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/alerts/?limit=50"
```

### Log Analysis

#### Application Logs
```bash
# Check FastAPI logs
tail -f logs/app.log | grep alerting

# Check Celery worker logs
tail -f logs/celery-worker.log

# Check Celery beat logs
tail -f logs/celery-beat.log
```

#### Database Queries
```sql
-- Check recent alerts
SELECT * FROM alerts 
WHERE triggered_at >= NOW() - INTERVAL '1 hour'
ORDER BY triggered_at DESC;

-- Check notification status
SELECT channel, status, COUNT(*) 
FROM alert_notifications 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY channel, status;

-- Check rule statistics
SELECT ar.name, COUNT(a.alert_id) as alert_count
FROM alert_rules ar
LEFT JOIN alerts a ON ar.rule_id = a.rule_id
WHERE a.triggered_at >= NOW() - INTERVAL '24 hours'
GROUP BY ar.rule_id, ar.name
ORDER BY alert_count DESC;
```

### Support and Documentation

For additional support and detailed documentation:

1. **API Documentation**: Visit `/docs` endpoint for interactive API docs
2. **System Health**: Check `/api/v1/alerts/health` for system status
3. **Rule Testing**: Use the rule testing API before deployment
4. **Log Analysis**: Review application logs for detailed error information
5. **Database Queries**: Use provided SQL queries for debugging

### Getting Help

If you encounter issues with the alerting system:

1. Check the troubleshooting section above
2. Review system health status
3. Check application logs for errors
4. Test individual components (rules, notifications, escalation)
5. Contact the development team with detailed error information

---

This comprehensive alerting system provides enterprise-grade monitoring capabilities for the Fernando platform. With its intelligent rule evaluation, multi-channel notifications, and automated escalation, it ensures that critical issues are identified and addressed promptly.