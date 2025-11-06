# Telemetry System Implementation Guide

## Overview

The Fernando platform includes a comprehensive telemetry system for monitoring, analytics, and observability. This system supports high-volume data collection, real-time alerting, and powerful analytics capabilities.

## Architecture

### Core Components

1. **Telemetry Events** - User actions and system events
2. **System Metrics** - Infrastructure monitoring data
3. **Business Metrics** - KPI and analytics data
4. **Alert Rules** - Custom alerting configurations
5. **Alerts** - Triggered alert notifications
6. **Distributed Tracing** - Request tracking and performance monitoring

## Database Schema

### Telemetry Events (`telemetry_events`)

**Purpose**: Store individual events and user actions for analytics and debugging.

**Key Features**:
- High-volume insert optimization
- Time-series indexing
- Flexible JSON payload
- User and license attribution
- Event categorization and tagging

**Common Use Cases**:
```python
# Track user login
telemetry_event = TelemetryEvent(
    event_type=EventType.USER_ACTION,
    event_name="user_login",
    event_category="authentication",
    user_id=user_id,
    license_id=license_id,
    event_data={"method": "email", "success": True},
    source="web"
)

# Track API usage
telemetry_event = TelemetryEvent(
    event_type=EventType.API_EVENT,
    event_name="document_process",
    event_category="processing",
    event_data={"document_id": doc_id, "processing_time": 2.5},
    duration_ms=2500,
    source="api",
    source_ip=request.client.host
)
```

### System Metrics (`system_metrics`)

**Purpose**: Store system performance metrics and infrastructure monitoring data.

**Key Features**:
- Time-series optimized storage
- Multiple metric types (counter, gauge, histogram, timer)
- Resource attribution (service, host, instance)
- Percentile calculations

**Common Use Cases**:
```python
# CPU usage metric
system_metric = SystemMetric(
    metric_name="cpu_usage",
    metric_type=MetricType.GAUGE,
    service_name="api",
    host_name="server-01",
    metric_value=85.5,
    metric_unit="percentage"
)

# Response time histogram
system_metric = SystemMetric(
    metric_name="response_time",
    metric_type=MetricType.HISTOGRAM,
    service_name="api",
    metric_value=245.0,
    percentile_50=150.0,
    percentile_90=280.0,
    percentile_95=350.0,
    percentile_99=450.0,
    metric_unit="milliseconds"
)
```

### Business Metrics (`business_metrics`)

**Purpose**: Store business-related metrics for KPI tracking and analytics.

**Key Features**:
- Time-period aggregation
- Financial and operational KPIs
- Customer attribution
- Multi-dimensional analysis

**Common Use Cases**:
```python
# Daily active users
business_metric = BusinessMetric(
    metric_name="daily_active_users",
    metric_category="user_engagement",
    license_id=license_id,
    metric_value=1250,
    metric_unit="count",
    period_start=datetime(2024, 1, 1, 0, 0),
    period_end=datetime(2024, 1, 1, 23, 59),
    period_type="daily"
)

# Revenue per user
business_metric = BusinessMetric(
    metric_name="revenue_per_user",
    metric_category="revenue",
    metric_value=49.99,
    metric_unit="usd",
    currency="USD",
    period_start=datetime(2024, 1, 1, 0, 0),
    period_end=datetime(2024, 1, 31, 23, 59),
    period_type="monthly",
    calculation_method="average"
)
```

### Alert Rules (`alert_rules`)

**Purpose**: Store custom alerting rules for proactive monitoring.

**Key Features**:
- Flexible condition configuration
- Multiple notification channels
- Severity levels
- Time window evaluation

**Common Use Cases**:
```python
# CPU usage alert
alert_rule = AlertRule(
    rule_name="High CPU Usage",
    rule_type="metric_threshold",
    source_type="system_metric",
    condition_config={
        "metric": "cpu_usage",
        "operator": ">",
        "threshold": 80,
        "time_window_minutes": 5
    },
    severity=SeverityLevel.WARNING,
    notification_channels=["email", "slack"],
    notification_config={
        "email": ["ops-team@company.com"],
        "slack": {"channel": "#alerts"}
    },
    license_id=license_id
)
```

### Alerts (`alerts`)

**Purpose**: Store triggered alerts from monitoring rules.

**Key Features**:
- Alert lifecycle management
- Assignment and resolution tracking
- Impact assessment
- Notification tracking

### Distributed Tracing (`traces`)

**Purpose**: Store distributed tracing data for request tracking and performance analysis.

**Key Features**:
- Hierarchical trace structure
- Service attribution
- Error tracking
- Performance metrics

**Common Use Cases**:
```python
# API request trace
trace = Trace(
    trace_id=trace_id,
    span_id=span_id,
    service_name="api",
    operation_name="process_document",
    http_method="POST",
    http_url="/api/documents/process",
    http_status_code=200,
    duration_ms=1200,
    user_id=user_id,
    tags={"endpoint": "/documents/process", "user_type": "premium"}
)
```

## Performance Optimizations

### Indexing Strategy

1. **Time-series indexes** - Optimized for temporal queries
2. **Composite indexes** - Support for common query patterns
3. **Partial indexes** - Focus on active/filtered data
4. **Hash indexes** - For equality queries on timestamps
5. **GIN indexes** - JSON field searching (PostgreSQL)

### Data Retention

Default retention policies:
- **Telemetry Events**: 90 days
- **System Metrics**: 180 days
- **Business Metrics**: 180 days (longer for historical analysis)
- **Traces**: 30 days

Use the cleanup function:
```python
# PostgreSQL
cleanup_old_telemetry_data(
    events_retention_days=90,
    metrics_retention_days=180,
    traces_retention_days=30
)
```

## Analytics Views

Pre-built views for common analytics:

### Event Summary
```sql
SELECT * FROM telemetry_events_hourly_summary
WHERE event_type = 'user_action'
  AND hour >= NOW() - INTERVAL '24 hours';
```

### System Performance
```sql
SELECT * FROM system_metrics_service_summary
WHERE service_name = 'api'
  AND hour >= NOW() - INTERVAL '1 hour'
ORDER BY hour DESC;
```

### Business KPIs
```sql
SELECT * FROM business_metrics_category_summary
WHERE metric_category = 'revenue'
  AND date >= CURRENT_DATE - INTERVAL '30 days';
```

### Alert Status
```sql
SELECT * FROM alerts_status_summary
WHERE status = 'active'
ORDER BY severity DESC, triggered_at DESC;
```

## Best Practices

### Event Collection

1. **Use appropriate event types** - Categorize events correctly
2. **Include relevant context** - Add metadata for analysis
3. **Batch inserts** - Group events for better performance
4. **Use async processing** - Don't block application threads

```python
# Good practice example
def track_user_action(user_id: str, action: str, context: dict):
    event = TelemetryEvent(
        event_type=EventType.USER_ACTION,
        event_name=action,
        event_category="user_interaction",
        user_id=user_id,
        event_data=context,
        source="web"
    )
    # Add to batch for async processing
    telemetry_batch.append(event)
```

### Metric Collection

1. **Use appropriate metric types** - Counter, gauge, histogram, timer
2. **Include units** - Always specify measurement units
3. **Add dimensions** - Use tags/labels for filtering
4. **Aggregate appropriately** - Use correct aggregation methods

### Alert Configuration

1. **Set reasonable thresholds** - Avoid alert fatigue
2. **Use appropriate severity** - Match alert importance
3. **Configure notifications** - Set up multiple channels
4. **Test alert rules** - Ensure they work as expected

### Query Optimization

1. **Use time-based filtering** - Always include time ranges
2. **Leverage indexes** - Query patterns should match index definitions
3. **Use materialized views** - For complex aggregations
4. **Limit result sets** - Use pagination for large datasets

```python
# Optimized query example
from datetime import datetime, timedelta

# Get recent events for a user
events = db.query(TelemetryEvent).filter(
    TelemetryEvent.user_id == user_id,
    TelemetryEvent.event_timestamp >= datetime.utcnow() - timedelta(days=7)
).order_by(TelemetryEvent.event_timestamp.desc()).limit(100).all()
```

## Integration Examples

### FastAPI Middleware

```python
from fastapi import Request, Response
import time

@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Record timing
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Track API event
    await track_telemetry_event(
        event_type=EventType.API_EVENT,
        event_name=f"{request.method}_{request.url.path}",
        event_data={
            "status_code": response.status_code,
            "method": request.method,
            "path": str(request.url.path)
        },
        duration_ms=duration_ms,
        source="api",
        user_id=get_current_user_id(request)
    )
    
    return response
```

### Scheduled Metrics Collection

```python
import psutil
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def collect_system_metrics():
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    
    # Disk usage
    disk = psutil.disk_usage('/')
    
    # Store metrics
    await save_system_metric(
        metric_name="cpu_usage",
        metric_type=MetricType.GAUGE,
        service_name="main",
        metric_value=cpu_percent,
        metric_unit="percentage"
    )
    
    await save_system_metric(
        metric_name="memory_usage",
        metric_type=MetricType.GAUGE,
        service_name="main",
        metric_value=memory.percent,
        metric_unit="percentage"
    )

# Schedule collection every minute
scheduler = AsyncIOScheduler()
scheduler.add_job(collect_system_metrics, 'interval', minutes=1)
scheduler.start()
```

## Monitoring Dashboard Queries

### User Activity Dashboard

```sql
SELECT 
    event_category,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users,
    DATE_TRUNC('hour', event_timestamp) as hour
FROM telemetry_events
WHERE event_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY event_category, DATE_TRUNC('hour', event_timestamp)
ORDER BY hour DESC, event_count DESC;
```

### System Performance Dashboard

```sql
SELECT 
    service_name,
    metric_name,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    percentile_95 as p95_value
FROM system_metrics
WHERE metric_timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY service_name, metric_name
ORDER BY avg_value DESC;
```

### Business Metrics Dashboard

```sql
SELECT 
    metric_name,
    metric_category,
    SUM(metric_value) as total_value,
    COUNT(DISTINCT license_id) as active_licenses
FROM business_metrics
WHERE period_start >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY metric_name, metric_category
ORDER BY total_value DESC;
```

## Error Handling and Monitoring

### Alert for High Error Rates

```python
alert_rule = AlertRule(
    rule_name="High Error Rate",
    rule_type="event_frequency",
    source_type="telemetry_event",
    condition_config={
        "event_type": "error_event",
        "threshold": 10,
        "time_window_minutes": 5
    },
    severity=SeverityLevel.ERROR,
    license_id=license_id
)
```

### Performance Degradation Alert

```python
alert_rule = AlertRule(
    rule_name="Slow Response Times",
    rule_type="metric_threshold",
    source_type="system_metric",
    condition_config={
        "metric": "response_time",
        "operator": ">",
        "threshold": 1000,
        "aggregation": "p95"
    },
    severity=SeverityLevel.WARNING,
    license_id=license_id
)
```

## Data Export and Analytics

### Export to Data Warehouse

```python
def export_telemetry_data(start_date: datetime, end_date: datetime):
    # Export events
    events = db.query(TelemetryEvent).filter(
        TelemetryEvent.event_timestamp.between(start_date, end_date)
    ).all()
    
    # Export metrics
    metrics = db.query(SystemMetric).filter(
        SystemMetric.metric_timestamp.between(start_date, end_date)
    ).all()
    
    # Save to data warehouse or analytics platform
    save_to_warehouse("events", [event.to_dict() for event in events])
    save_to_warehouse("metrics", [metric.to_dict() for metric in metrics])
```

## Conclusion

The telemetry system provides comprehensive observability for the Fernando platform. By following the best practices outlined in this guide, you can:

- Monitor system health and performance
- Track business metrics and KPIs
- Detect issues proactively with alerts
- Debug problems with distributed tracing
- Optimize performance with detailed analytics

The system is designed to scale with your application's growth while maintaining query performance and data retention efficiency.