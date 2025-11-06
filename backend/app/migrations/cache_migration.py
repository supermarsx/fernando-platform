"""
Cache Database Migrations

Database migration for creating cache-related tables.
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.session import Base
from app.models.cache import (
    CacheStatistics, CacheInvalidationRule, CachePerformanceMetrics,
    CacheHealthStatus, CacheWarmupJob, CacheEventLog
)


def create_cache_tables():
    """Create all cache-related database tables."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        # Create all cache tables
        CacheStatistics.__table__.create(bind=engine, checkfirst=True)
        CacheInvalidationRule.__table__.create(bind=engine, checkfirst=True)
        CachePerformanceMetrics.__table__.create(bind=engine, checkfirst=True)
        CacheHealthStatus.__table__.create(bind=engine, checkfirst=True)
        CacheWarmupJob.__table__.create(bind=engine, checkfirst=True)
        CacheEventLog.__table__.create(bind=engine, checkfirst=True)
        
        print("Cache tables created successfully")
        
        # Create indexes for better performance
        with engine.connect() as conn:
            # Cache statistics indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_stats_type 
                ON cache_statistics (cache_type)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_stats_tenant 
                ON cache_statistics (tenant_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_stats_updated 
                ON cache_statistics (updated_at)
            """))
            
            # Cache performance metrics indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_perf_timestamp 
                ON cache_performance_metrics (timestamp)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_perf_type_time 
                ON cache_performance_metrics (cache_type, timestamp)
            """))
            
            # Cache event log indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_event_timestamp 
                ON cache_event_log (timestamp)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_event_type 
                ON cache_event_log (event_type, timestamp)
            """))
            
            # Cache health status indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_health_component 
                ON cache_health_status (component_name)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cache_health_status 
                ON cache_health_status (status)
            """))
            
            conn.commit()
        
        print("Cache indexes created successfully")
        
        return True
        
    except Exception as e:
        print(f"Error creating cache tables: {e}")
        return False


def insert_default_cache_invalidation_rules():
    """Insert default cache invalidation rules."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        default_rules = [
            {
                "rule_name": "document_updated_invalidation",
                "description": "Invalidate cache when document is updated",
                "cache_types": ["document", "ocr", "llm"],
                "key_patterns": ["doc:*", "ocr:*", "llm:*"],
                "trigger_events": ["document.updated", "extraction.updated"],
                "invalidation_mode": "lazy",
                "delay_seconds": 30,
                "priority": 1
            },
            {
                "rule_name": "user_logout_invalidation",
                "description": "Invalidate user session cache on logout",
                "cache_types": ["session"],
                "key_patterns": ["session:*"],
                "trigger_events": ["user.logout"],
                "invalidation_mode": "eager",
                "delay_seconds": 0,
                "priority": 2
            },
            {
                "rule_name": "tenant_config_change",
                "description": "Invalidate tenant-specific cache on config changes",
                "cache_types": ["billing", "subscription", "license"],
                "key_patterns": ["billing:*", "subscription:*", "license:*"],
                "trigger_events": ["tenant.config.updated", "billing.updated"],
                "invalidation_mode": "eager",
                "delay_seconds": 0,
                "priority": 3
            }
        ]
        
        with engine.connect() as conn:
            for rule_data in default_rules:
                # Check if rule already exists
                result = conn.execute(text("""
                    SELECT id FROM cache_invalidation_rules WHERE rule_name = :rule_name
                """), {"rule_name": rule_data["rule_name"]})
                
                if not result.fetchone():
                    # Insert new rule
                    conn.execute(text("""
                        INSERT INTO cache_invalidation_rules (
                            rule_name, description, cache_types, key_patterns,
                            trigger_events, invalidation_mode, delay_seconds, priority,
                            is_active, created_at, updated_at
                        ) VALUES (
                            :rule_name, :description, :cache_types, :key_patterns,
                            :trigger_events, :invalidation_mode, :delay_seconds, :priority,
                            true, NOW(), NOW()
                        )
                    """), rule_data)
            
            conn.commit()
        
        print("Default cache invalidation rules inserted successfully")
        return True
        
    except Exception as e:
        print(f"Error inserting default rules: {e}")
        return False


def create_cache_warmup_jobs():
    """Create default cache warmup jobs."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        warmup_jobs = [
            {
                "job_name": "dashboard_data_warmup",
                "description": "Warm up frequently accessed dashboard data",
                "cache_type": "dashboard",
                "selection_strategy": "frequency",
                "batch_size": 50,
                "max_concurrent": 5,
                "interval_minutes": 30,
                "is_recurring": True
            },
            {
                "job_name": "reference_data_warmup",
                "description": "Warm up reference and master data",
                "cache_type": "reference",
                "selection_strategy": "timestamp",
                "batch_size": 100,
                "max_concurrent": 10,
                "interval_minutes": 60,
                "is_recurring": True
            },
            {
                "job_name": "user_preferences_warmup",
                "description": "Warm up user preferences and settings",
                "cache_type": "user_preferences",
                "selection_strategy": "frequency",
                "batch_size": 20,
                "max_concurrent": 3,
                "interval_minutes": 15,
                "is_recurring": True
            }
        ]
        
        with engine.connect() as conn:
            for job_data in warmup_jobs:
                # Check if job already exists
                result = conn.execute(text("""
                    SELECT id FROM cache_warmup_jobs WHERE job_name = :job_name
                """), {"job_name": job_data["job_name"]})
                
                if not result.fetchone():
                    # Insert new job
                    conn.execute(text("""
                        INSERT INTO cache_warmup_jobs (
                            job_name, description, cache_type, selection_strategy,
                            batch_size, max_concurrent, interval_minutes, is_recurring,
                            status, created_at, updated_at
                        ) VALUES (
                            :job_name, :description, :cache_type, :selection_strategy,
                            :batch_size, :max_concurrent, :interval_minutes, :is_recurring,
                            'pending', NOW(), NOW()
                        )
                    """), job_data)
            
            conn.commit()
        
        print("Default cache warmup jobs created successfully")
        return True
        
    except Exception as e:
        print(f"Error creating warmup jobs: {e}")
        return False


def initialize_cache_system():
    """Initialize the complete cache system."""
    print("Initializing Redis cache system...")
    
    # Create database tables
    if create_cache_tables():
        print("✓ Cache database tables created")
    else:
        print("✗ Failed to create cache database tables")
        return False
    
    # Insert default invalidation rules
    if insert_default_cache_invalidation_rules():
        print("✓ Default cache invalidation rules inserted")
    else:
        print("✗ Failed to insert cache invalidation rules")
        return False
    
    # Create warmup jobs
    if create_cache_warmup_jobs():
        print("✓ Cache warmup jobs created")
    else:
        print("✗ Failed to create cache warmup jobs")
        return False
    
    print("Cache system initialization completed successfully!")
    return True


if __name__ == "__main__":
    initialize_cache_system()
