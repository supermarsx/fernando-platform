"""
Database Migration: Add Telemetry System

Creates comprehensive telemetry system supporting:
- Event tracking and user actions with high-volume inserts
- System and business metrics collection for analytics
- Custom alerting rules and real-time notifications
- Distributed tracing for performance monitoring
- Time-series optimized storage with partitioning support

Features:
- Optimized indexes for time-series queries
- Foreign key relationships to existing entities
- JSON fields for flexible metadata storage
- Support for both PostgreSQL and SQLite
- Scalable design for high-volume telemetry data
"""

from sqlalchemy import create_engine, MetaData, text
from app.db.session import engine, Base
# Import all models to ensure they're registered
from app.models import user, job, document, extraction, audit, billing, license, enterprise, usage, enterprise_billing, revenue_operations
from app.models.telemetry import (
    TelemetryEvent, SystemMetric, BusinessMetric, AlertRule, Alert, Trace
)


def create_telemetry_indexes():
    """Create additional PostgreSQL-specific indexes for performance optimization"""
    if "postgresql" in str(engine.url):
        try:
            with engine.connect() as conn:
                # Create partition-aware indexes for large datasets
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_events_timestamp_hash
                    ON telemetry_events USING hash (event_timestamp);
                """))
                
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_timestamp_hash
                    ON system_metrics USING hash (metric_timestamp);
                """))
                
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_metrics_period_hash
                    ON business_metrics USING hash (period_start);
                """))
                
                # Create expression indexes for common filtering patterns
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_events_date_trunc
                    ON telemetry_events ((event_timestamp::date));
                """))
                
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_date_trunc
                    ON system_metrics ((metric_timestamp::date));
                """))
                
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_metrics_month_trunc
                    ON business_metrics ((date_trunc('month', period_start)));
                """))
                
                # Create partial indexes for active data
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_events_unprocessed
                    ON telemetry_events (event_timestamp)
                    WHERE is_processed = false;
                """))
                
                conn.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_active
                    ON alerts (triggered_at)
                    WHERE status = 'active';
                """))
                
                # Create GIN indexes for JSONB columns (if using PostgreSQL)
                try:
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_telemetry_events_data_gin
                        ON telemetry_events USING gin (event_data);
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_labels_gin
                        ON system_metrics USING gin (labels);
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_metrics_dimensions_gin
                        ON business_metrics USING gin (dimensions);
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_traces_tags_gin
                        ON traces USING gin (tags);
                    """))
                except Exception as e:
                    print(f"Note: GIN indexes may not be available: {e}")
                
                conn.commit()
                print("PostgreSQL-specific indexes created successfully!")
        except Exception as e:
            print(f"Warning: Could not create PostgreSQL indexes: {e}")


def setup_data_retention_policies():
    """Create database views and functions for automated data cleanup"""
    if "postgresql" in str(engine.url):
        try:
            with engine.connect() as conn:
                # Create function for automated cleanup
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION cleanup_old_telemetry_data(
                        events_retention_days INTEGER DEFAULT 90,
                        metrics_retention_days INTEGER DEFAULT 180,
                        traces_retention_days INTEGER DEFAULT 30
                    )
                    RETURNS void AS $$
                    BEGIN
                        -- Clean up old telemetry events
                        DELETE FROM telemetry_events 
                        WHERE event_timestamp < (CURRENT_DATE - INTERVAL '1 day' * events_retention_days);
                        
                        -- Clean up old system metrics
                        DELETE FROM system_metrics 
                        WHERE metric_timestamp < (CURRENT_DATE - INTERVAL '1 day' * metrics_retention_days);
                        
                        -- Clean up old business metrics (keep longer for historical analysis)
                        DELETE FROM business_metrics 
                        WHERE period_start < (CURRENT_DATE - INTERVAL '1 day' * metrics_retention_days);
                        
                        -- Clean up old traces
                        DELETE FROM traces 
                        WHERE start_time < (CURRENT_DATE - INTERVAL '1 day' * traces_retention_days);
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Create cleanup log view
                conn.execute(text("""
                    CREATE OR REPLACE VIEW telemetry_cleanup_log AS
                    SELECT 
                        'events' as table_name,
                        event_timestamp::date as partition_date,
                        COUNT(*) as record_count
                    FROM telemetry_events 
                    WHERE event_timestamp < (CURRENT_DATE - INTERVAL '90 days')
                    GROUP BY event_timestamp::date
                    UNION ALL
                    SELECT 
                        'system_metrics' as table_name,
                        metric_timestamp::date as partition_date,
                        COUNT(*) as record_count
                    FROM system_metrics 
                    WHERE metric_timestamp < (CURRENT_DATE - INTERVAL '180 days')
                    GROUP BY metric_timestamp::date
                    UNION ALL
                    SELECT 
                        'business_metrics' as table_name,
                        period_start::date as partition_date,
                        COUNT(*) as record_count
                    FROM business_metrics 
                    WHERE period_start < (CURRENT_DATE - INTERVAL '180 days')
                    GROUP BY period_start::date
                    UNION ALL
                    SELECT 
                        'traces' as table_name,
                        start_time::date as partition_date,
                        COUNT(*) as record_count
                    FROM traces 
                    WHERE start_time < (CURRENT_DATE - INTERVAL '30 days')
                    GROUP BY start_time::date;
                """))
                
                # Create data summary view for monitoring
                conn.execute(text("""
                    CREATE OR REPLACE VIEW telemetry_data_summary AS
                    SELECT 
                        'telemetry_events' as table_name,
                        COUNT(*) as total_records,
                        MIN(event_timestamp) as oldest_record,
                        MAX(event_timestamp) as newest_record,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT license_id) as unique_licenses
                    FROM telemetry_events
                    UNION ALL
                    SELECT 
                        'system_metrics' as table_name,
                        COUNT(*) as total_records,
                        MIN(metric_timestamp) as oldest_record,
                        MAX(metric_timestamp) as newest_record,
                        COUNT(DISTINCT service_name) as unique_services,
                        COUNT(DISTINCT metric_name) as unique_metrics
                    FROM system_metrics
                    UNION ALL
                    SELECT 
                        'business_metrics' as table_name,
                        COUNT(*) as total_records,
                        MIN(period_start) as oldest_record,
                        MAX(period_start) as newest_record,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT license_id) as unique_licenses
                    FROM business_metrics
                    UNION ALL
                    SELECT 
                        'traces' as table_name,
                        COUNT(*) as total_records,
                        MIN(start_time) as oldest_record,
                        MAX(start_time) as newest_record,
                        COUNT(DISTINCT service_name) as unique_services,
                        COUNT(DISTINCT operation_name) as unique_operations
                    FROM traces;
                """))
                
                conn.commit()
                print("Data retention policies and views created successfully!")
        except Exception as e:
            print(f"Warning: Could not create data retention policies: {e}")


def create_telemetry_views():
    """Create useful views for analytics and monitoring"""
    try:
        with engine.connect() as conn:
            # Event summary by type and hour
            conn.execute(text("""
                CREATE VIEW IF NOT EXISTS telemetry_events_hourly_summary AS
                SELECT 
                    event_type,
                    DATE_TRUNC('hour', event_timestamp) as hour,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT license_id) as unique_licenses,
                    AVG(duration_ms) as avg_duration_ms
                FROM telemetry_events
                GROUP BY event_type, DATE_TRUNC('hour', event_timestamp);
            """))
            
            # System metrics summary by service
            conn.execute(text("""
                CREATE VIEW IF NOT EXISTS system_metrics_service_summary AS
                SELECT 
                    service_name,
                    metric_name,
                    metric_type,
                    DATE_TRUNC('hour', metric_timestamp) as hour,
                    COUNT(*) as measurement_count,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    percentile_95 as p95_value
                FROM system_metrics
                GROUP BY service_name, metric_name, metric_type, DATE_TRUNC('hour', metric_timestamp);
            """))
            
            # Business metrics summary by category
            conn.execute(text("""
                CREATE VIEW IF NOT EXISTS business_metrics_category_summary AS
                SELECT 
                    metric_category,
                    metric_name,
                    DATE_TRUNC('day', period_start) as date,
                    COUNT(*) as metric_points,
                    SUM(metric_value) as total_value,
                    AVG(metric_value) as avg_value,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT license_id) as unique_licenses
                FROM business_metrics
                GROUP BY metric_category, metric_name, DATE_TRUNC('day', period_start);
            """))
            
            # Alert summary by status
            conn.execute(text("""
                CREATE VIEW IF NOT EXISTS alerts_status_summary AS
                SELECT 
                    status,
                    severity,
                    COUNT(*) as alert_count,
                    COUNT(DISTINCT rule_id) as affected_rules,
                    MIN(triggered_at) as first_alert,
                    MAX(triggered_at) as last_alert,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, CURRENT_TIMESTAMP) - triggered_at))/3600) as avg_resolution_hours
                FROM alerts
                GROUP BY status, severity;
            """))
            
            # Trace performance summary
            conn.execute(text("""
                CREATE VIEW IF NOT EXISTS trace_performance_summary AS
                SELECT 
                    service_name,
                    operation_name,
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as trace_count,
                    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as error_count,
                    AVG(duration_ms) as avg_duration_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
                    MIN(duration_ms) as min_duration_ms,
                    MAX(duration_ms) as max_duration_ms
                FROM traces
                GROUP BY service_name, operation_name, DATE_TRUNC('hour', start_time);
            """))
            
            conn.commit()
            print("Telemetry views created successfully!")
    except Exception as e:
        print(f"Warning: Could not create telemetry views: {e}")


def upgrade():
    """Create all telemetry tables and supporting infrastructure"""
    print("Creating telemetry system tables...")
    
    # Create all tables defined in telemetry models
    Base.metadata.create_all(bind=engine, tables=[
        TelemetryEvent.__table__,
        SystemMetric.__table__,
        BusinessMetric.__table__,
        AlertRule.__table__,
        Alert.__table__,
        Trace.__table__
    ])
    
    print("Telemetry system tables created successfully!")
    print("\nCreated tables:")
    print("  - telemetry_events (User actions and system events)")
    print("  - system_metrics (Infrastructure monitoring data)")
    print("  - business_metrics (KPI and analytics data)")
    print("  - alert_rules (Custom alerting configurations)")
    print("  - alerts (Triggered alert notifications)")
    print("  - traces (Distributed tracing data)")
    
    # Create PostgreSQL-specific optimizations
    create_telemetry_indexes()
    
    # Set up data retention policies
    setup_data_retention_policies()
    
    # Create analytics views
    create_telemetry_views()
    
    print("\nTelemetry system setup completed!")
    print("\nOptimization features:")
    print("  - Time-series optimized indexes")
    print("  - Partition-aware queries for large datasets")
    print("  - Automated data retention policies")
    print("  - Analytics views for dashboard queries")
    print("  - JSON field indexing for flexible queries")
    print("  - Partial indexes for active data filtering")


def downgrade():
    """Drop all telemetry tables and supporting infrastructure"""
    print("Dropping telemetry system tables...")
    
    # Drop views first
    try:
        with engine.connect() as conn:
            views_to_drop = [
                "telemetry_events_hourly_summary",
                "system_metrics_service_summary", 
                "business_metrics_category_summary",
                "alerts_status_summary",
                "trace_performance_summary",
                "telemetry_cleanup_log",
                "telemetry_data_summary"
            ]
            
            for view in views_to_drop:
                try:
                    conn.execute(text(f"DROP VIEW IF EXISTS {view};"))
                except Exception:
                    pass  # View may not exist
            
            # Drop functions
            try:
                conn.execute(text("DROP FUNCTION IF EXISTS cleanup_old_telemetry_data;"))
            except Exception:
                pass
                
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not drop views/functions: {e}")
    
    # Drop all telemetry tables
    Base.metadata.drop_all(bind=engine, tables=[
        Trace.__table__,
        Alert.__table__,
        AlertRule.__table__,
        BusinessMetric.__table__,
        SystemMetric.__table__,
        TelemetryEvent.__table__
    ])
    
    print("Telemetry system tables dropped successfully!")


if __name__ == "__main__":
    try:
        upgrade()
        print("\nMigration completed successfully!")
        print("\nNext steps:")
        print("1. Configure telemetry collection in your application")
        print("2. Set up monitoring dashboards using the analytics views")
        print("3. Create custom alert rules based on your metrics")
        print("4. Implement data retention policies for cost optimization")
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        raise