"""
Usage Tracking & Metering System Migration

Adds tables for comprehensive usage tracking, quota management,
analytics, forecasting, and fraud detection.
"""

from sqlalchemy import create_engine, MetaData
from app.models.usage import Base as UsageBase
from app.db.session import engine
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """
    Create all usage tracking tables
    """
    logger.info("Creating usage tracking tables...")
    
    try:
        # Import all usage models to ensure they're registered
        from app.models import usage
        
        # Create all tables
        UsageBase.metadata.create_all(bind=engine)
        
        logger.info("✓ Usage tracking tables created successfully")
        
        # List of tables created
        tables_created = [
            "usage_metrics",
            "usage_quotas",
            "usage_aggregations",
            "usage_alerts",
            "usage_forecasts",
            "usage_anomalies",
            "usage_reports",
            "usage_thresholds"
        ]
        
        for table in tables_created:
            logger.info(f"  - {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating usage tracking tables: {str(e)}")
        raise


def downgrade():
    """
    Drop all usage tracking tables
    """
    logger.info("Dropping usage tracking tables...")
    
    try:
        from app.models import usage
        
        # Drop all tables
        UsageBase.metadata.drop_all(bind=engine)
        
        logger.info("✓ Usage tracking tables dropped successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error dropping usage tracking tables: {str(e)}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("Usage Tracking & Metering System Migration")
    print("=" * 60)
    print()
    
    # Run upgrade
    upgrade()
    
    print()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
