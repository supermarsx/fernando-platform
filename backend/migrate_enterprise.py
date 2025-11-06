#!/usr/bin/env python3
"""
Database migration script for enterprise features
Run this script to add all enterprise tables to the existing database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.models.enterprise import (
    Tenant, UserEnterprise, Group, GroupMember, Permission,
    GroupPermission, UserPermission, JobQueue, QuotaUsage,
    ExportJob, AuditTrail, ScheduledTask, TaskRun, RateLimit,
    ComplianceReport
)
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.db.session import Base, SessionLocal
from app.core.config import settings


def create_enterprise_tables():
    """Create all enterprise tables"""
    print("Creating enterprise tables...")
    
    # Create tables
    Base.metadata.create_all(bind=engine, tables=[
        Tenant.__table__,
        UserEnterprise.__table__,
        Group.__table__,
        GroupMember.__table__,
        Permission.__table__,
        GroupPermission.__table__,
        UserPermission.__table__,
        JobQueue.__table__,
        QuotaUsage.__table__,
        ExportJob.__table__,
        AuditTrail.__table__,
        ScheduledTask.__table__,
        TaskRun.__table__,
        RateLimit.__table__,
        ComplianceReport.__table__
    ])
    
    print("Enterprise tables created successfully!")


def update_existing_tables():
    """Add tenant_id columns to existing tables"""
    print("Updating existing tables for multi-tenancy...")
    
    # Update users table
    try:
        engine.execute(text("ALTER TABLE users ADD COLUMN tenant_id VARCHAR"))
        print("✓ Added tenant_id to users table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ tenant_id column already exists in users table")
        else:
            print(f"✗ Error updating users table: {e}")
    
    # Update jobs table
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN tenant_id VARCHAR"))
        print("✓ Added tenant_id to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ tenant_id column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN assigned_to VARCHAR"))
        print("✓ Added assigned_to to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ assigned_to column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN estimated_duration INTEGER"))
        print("✓ Added estimated_duration to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ estimated_duration column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN actual_duration INTEGER"))
        print("✓ Added actual_duration to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ actual_duration column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0"))
        print("✓ Added retry_count to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ retry_count column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN job_metadata TEXT"))
        print("✓ Added job_metadata to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ job_metadata column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN error_details TEXT"))
        print("✓ Added error_details to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ error_details column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE jobs ADD COLUMN progress_percentage INTEGER DEFAULT 0"))
        print("✓ Added progress_percentage to jobs table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ progress_percentage column already exists in jobs table")
        else:
            print(f"✗ Error updating jobs table: {e}")
    
    # Update documents table
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN tenant_id VARCHAR"))
        print("✓ Added tenant_id to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ tenant_id column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN file_size_bytes INTEGER DEFAULT 0"))
        print("✓ Added file_size_bytes to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ file_size_bytes column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN is_confidential BOOLEAN DEFAULT 0"))
        print("✓ Added is_confidential to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ is_confidential column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN retention_period_days INTEGER DEFAULT 365"))
        print("✓ Added retention_period_days to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ retention_period_days column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN tags TEXT"))
        print("✓ Added tags to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ tags column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN doc_metadata TEXT"))
        print("✓ Added doc_metadata to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ doc_metadata column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN processed_at DATETIME"))
        print("✓ Added processed_at to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ processed_at column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")
    
    try:
        engine.execute(text("ALTER TABLE documents ADD COLUMN archived_at DATETIME"))
        print("✓ Added archived_at to documents table")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ archived_at column already exists in documents table")
        else:
            print(f"✗ Error updating documents table: {e}")


def initialize_default_data():
    """Initialize default enterprise data"""
    print("Initializing default enterprise data...")
    
    db = SessionLocal()
    try:
        from app.services.enterprise_service import EnterpriseService
        
        enterprise_service = EnterpriseService(db)
        
        # Initialize default permissions (this is called in the service constructor)
        print("✓ Default permissions initialized")
        
        # Create default system tenant if none exists
        default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not default_tenant:
            default_tenant = enterprise_service.create_tenant(
                name="Default Organization",
                slug="default",
                description="Default system tenant for single-tenant deployments",
                subscription_plan="basic",
                max_users=100,
                max_jobs_per_month=10000,
                max_storage_gb=50
            )
            print("✓ Default tenant created")
        
        # Update existing users to belong to default tenant
        if default_tenant:
            users_without_tenant = db.query(User).filter(
                (User.tenant_id.is_(None)) | (User.tenant_id == "")
            ).all()
            
            for user in users_without_tenant:
                user.tenant_id = default_tenant.tenant_id
                print(f"✓ Assigned user {user.email} to default tenant")
            
            db.commit()
        
        # Update existing jobs to belong to default tenant
        if default_tenant:
            jobs_without_tenant = db.query(Job).filter(
                (Job.tenant_id.is_(None)) | (Job.tenant_id == "")
            ).all()
            
            for job in jobs_without_tenant:
                job.tenant_id = default_tenant.tenant_id
            
            db.commit()
            print(f"✓ Assigned {len(jobs_without_tenant)} jobs to default tenant")
        
        print("Default enterprise data initialized successfully!")
        
    except Exception as e:
        print(f"✗ Error initializing default data: {e}")
        db.rollback()
    finally:
        db.close()


def create_indexes():
    """Create database indexes for performance"""
    print("Creating database indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_tenant_id ON jobs(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_audit_trail_tenant_id ON audit_trail(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_export_jobs_tenant_id ON export_jobs(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_export_jobs_status ON export_jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_tenant_id ON scheduled_tasks(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_task_runs_task_id ON task_runs(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_rate_limits_tenant_id ON rate_limits(tenant_id)",
    ]
    
    for index_sql in indexes:
        try:
            engine.execute(text(index_sql))
            print(f"✓ Created index: {index_sql.split()[-2]}")  # Get index name
        except Exception as e:
            print(f"✗ Error creating index: {e}")


def main():
    """Main migration function"""
    print("Starting enterprise database migration...")
    print("=" * 50)
    
    global engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        
        # Create enterprise tables
        create_enterprise_tables()
        
        # Update existing tables
        update_existing_tables()
        
        # Create indexes
        create_indexes()
        
        # Initialize default data
        initialize_default_data()
        
        print("=" * 50)
        print("✅ Enterprise migration completed successfully!")
        print("\nNew enterprise features available:")
        print("• Multi-tenant support with data isolation")
        print("• Advanced user management with groups and permissions")
        print("• Enhanced batch processing with queue management")
        print("• Export/import functionality (CSV, Excel, JSON)")
        print("• Advanced audit trails and compliance reporting")
        print("• API rate limiting and quota management")
        print("• Role-based access control enhancements")
        print("• Advanced job scheduling and automation")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
