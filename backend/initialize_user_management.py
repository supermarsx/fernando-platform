#!/usr/bin/env python3
"""
User Management System Initialization Script

This script initializes the user management system with default data,
creates the initial admin user, and sets up the basic organizational structure.

Usage:
    python initialize_user_management.py --create-admin
    python initialize_user_management.py --create-org "My Organization"
    python initialize_user_management.py --setup-defaults
"""

import argparse
import sys
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.session import Base, get_db
from app.models.user import User
from app.models.user_management import (
    Organization, UserRole, Permission, RolePermission,
    UserRoleAssignment, UserPreferences, AccountSecurity,
    UserSession, UserActivity
)
from app.core.security import get_password_hash
from app.services.user_management import user_management_service


def create_database_tables(engine):
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully")


def create_default_organization(db_session, name="Fernando Platform", domain=None):
    """Create a default organization"""
    print(f"Creating default organization: {name}...")
    
    # Check if organization already exists
    existing_org = db_session.query(Organization).filter(Organization.name == name).first()
    if existing_org:
        print(f"✅ Organization '{name}' already exists")
        return existing_org
    
    organization = Organization(
        organization_id=str(uuid.uuid4()),
        name=name,
        description="Default organization for Fernando Platform",
        domain=domain,
        subscription_tier="enterprise",
        subscription_status="active",
        max_users=1000,
        max_documents=10000,
        max_storage_gb=100,
        features=[
            "user_management",
            "rbac",
            "audit_logging",
            "multi_tenant",
            "advanced_security",
            "api_access",
            "reporting",
            "analytics"
        ],
        status="active"
    )
    
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    
    print(f"✅ Organization '{name}' created successfully")
    return organization


def create_system_admin_user(db_session, email, password, full_name, organization_id=None):
    """Create the initial system administrator"""
    print(f"Creating system admin user: {email}...")
    
    # Check if user already exists
    existing_user = db_session.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"✅ User '{email}' already exists")
        return existing_user
    
    # Create user
    user = User(
        user_id=str(uuid.uuid4()),
        email=email.lower(),
        password_hash=get_password_hash(password),
        full_name=full_name,
        status="active",
        roles=["admin"],  # Legacy role for backward compatibility
        organization_id=organization_id,
        email_verified=True,
        phone_verified=False,
        onboarding_completed=True,
        last_login=None,
        last_password_change=datetime.utcnow(),
        mfa_enabled=False,
        department="IT",
        job_title="System Administrator"
    )
    
    db_session.add(user)
    db_session.flush()  # Get the user ID
    
    # Create user preferences
    preferences = UserPreferences(
        user_id=user.user_id,
        email_notifications={
            "login_alerts": True,
            "security_alerts": True,
            "system_updates": True,
            "marketing_emails": False,
            "user_activities": True,
            "system_maintenance": True
        },
        theme="system",
        language="en",
        timezone="UTC",
        session_timeout_minutes=120,  # Longer timeout for admins
        dashboard_layout={
            "widgets": ["user_stats", "activity_feed", "security_status", "system_health"],
            "layout": "grid"
        },
        default_view="admin_dashboard"
    )
    
    # Create security account
    security = AccountSecurity(
        user_id=user.user_id,
        password_failed_attempts=0,
        password_change_required=False,
        login_attempts=[],
        security_events=[]
    )
    
    # Assign system admin role
    admin_role = db_session.query(UserRole).filter(UserRole.name == "system_admin").first()
    if admin_role:
        role_assignment = UserRoleAssignment(
            user_id=user.user_id,
            role_id=admin_role.role_id,
            organization_id=organization_id,
            assigned_by=user.user_id,
            is_active=True
        )
        db_session.add(role_assignment)
    
    db_session.add(preferences)
    db_session.add(security)
    db_session.commit()
    db_session.refresh(user)
    
    print(f"✅ System admin user '{email}' created successfully")
    return user


def create_sample_organization(db_session, name, domain, admin_email, admin_password):
    """Create a sample organization with admin user"""
    print(f"Creating sample organization: {name}...")
    
    # Create organization
    organization = create_default_organization(db_session, name, domain)
    
    # Create admin user for this organization
    admin_user = create_system_admin_user(
        db_session, 
        admin_email, 
        admin_password, 
        "Organization Administrator",
        organization.organization_id
    )
    
    # Assign admin role for this organization
    admin_role = db_session.query(UserRole).filter(UserRole.name == "admin").first()
    if admin_role:
        org_admin_assignment = UserRoleAssignment(
            user_id=admin_user.user_id,
            role_id=admin_role.role_id,
            organization_id=organization.organization_id,
            assigned_by=admin_user.user_id,
            is_active=True
        )
        db_session.add(org_admin_assignment)
        db_session.commit()
    
    print(f"✅ Sample organization '{name}' created with admin user")
    return organization, admin_user


def create_sample_users(db_session, organization_id, count=5):
    """Create sample users for testing"""
    print(f"Creating {count} sample users...")
    
    # Get user role
    user_role = db_session.query(UserRole).filter(UserRole.name == "user").first()
    viewer_role = db_session.query(UserRole).filter(UserRole.name == "viewer").first()
    
    sample_users = [
        {
            "email": "john.doe@example.com",
            "full_name": "John Doe",
            "department": "Finance",
            "job_title": "Financial Analyst"
        },
        {
            "email": "jane.smith@example.com", 
            "full_name": "Jane Smith",
            "department": "Operations",
            "job_title": "Operations Manager"
        },
        {
            "email": "mike.wilson@example.com",
            "full_name": "Mike Wilson",
            "department": "Sales",
            "job_title": "Sales Representative"
        },
        {
            "email": "sarah.johnson@example.com",
            "full_name": "Sarah Johnson",
            "department": "HR",
            "job_title": "HR Manager"
        },
        {
            "email": "david.brown@example.com",
            "full_name": "David Brown",
            "department": "IT",
            "job_title": "Developer"
        }
    ]
    
    created_users = []
    
    for i, user_data in enumerate(sample_users[:count]):
        # Check if user already exists
        existing = db_session.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"  ⏭️  User '{user_data['email']}' already exists")
            created_users.append(existing)
            continue
        
        # Create user
        user = User(
            user_id=str(uuid.uuid4()),
            email=user_data["email"],
            password_hash=get_password_hash("password123!"),
            full_name=user_data["full_name"],
            status="active",
            roles=["user"],
            organization_id=organization_id,
            email_verified=True,
            phone_verified=False,
            onboarding_completed=True,
            last_password_change=datetime.utcnow(),
            mfa_enabled=False,
            department=user_data["department"],
            job_title=user_data["job_title"]
        )
        
        db_session.add(user)
        db_session.flush()
        
        # Create preferences
        preferences = UserPreferences(user_id=user.user_id)
        security = AccountSecurity(user_id=user.user_id)
        
        # Assign role
        if i < 3 and user_role:  # First 3 users get user role
            assignment = UserRoleAssignment(
                user_id=user.user_id,
                role_id=user_role.role_id,
                organization_id=organization_id,
                assigned_by=None,  # System assigned
                is_active=True
            )
            db_session.add(assignment)
        
        # Last user gets viewer role
        if i == 4 and viewer_role:
            assignment = UserRoleAssignment(
                user_id=user.user_id,
                role_id=viewer_role.role_id,
                organization_id=organization_id,
                assigned_by=None,
                is_active=True
            )
            db_session.add(assignment)
        
        db_session.add(preferences)
        db_session.add(security)
        
        created_users.append(user)
        print(f"  ✅ Created user: {user_data['email']}")
    
    db_session.commit()
    print(f"✅ Sample users created successfully")
    return created_users


def create_activity_logs(db_session, users):
    """Create sample activity logs for analytics"""
    print("Creating sample activity logs...")
    
    activities = [
        "login",
        "logout", 
        "document_upload",
        "document_view",
        "profile_update",
        "password_change",
        "role_assigned"
    ]
    
    for user in users:
        for i in range(10):  # 10 activities per user
            activity = UserActivity(
                user_id=user.user_id,
                organization_id=user.organization_id,
                action=activities[i % len(activities)],
                resource_type="user" if i % 3 == 0 else "document",
                resource_id=str(uuid.uuid4()) if i % 3 == 0 else None,
                details={
                    "method": "web" if i % 2 == 0 else "api",
                    "session_id": str(uuid.uuid4())
                },
                ip_address=f"192.168.1.{100 + (hash(user.user_id) % 255)}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                success=True,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            db_session.add(activity)
    
    db_session.commit()
    print("✅ Sample activity logs created successfully")


def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'sqlite:///./accounting_automation.db')


def main():
    parser = argparse.ArgumentParser(description="Initialize User Management System")
    parser.add_argument('--create-admin', action='store_true', 
                       help='Create system admin user')
    parser.add_argument('--admin-email', type=str, default='admin@fernando.com',
                       help='Admin user email')
    parser.add_argument('--admin-password', type=str, default='admin123!',
                       help='Admin user password')
    parser.add_argument('--admin-name', type=str, default='System Administrator',
                       help='Admin user full name')
    
    parser.add_argument('--create-org', type=str, nargs='?', const='Fernando Platform',
                       help='Create default organization')
    parser.add_argument('--org-domain', type=str, help='Organization domain')
    
    parser.add_argument('--setup-defaults', action='store_true',
                       help='Setup default roles, permissions, and sample data')
    parser.add_argument('--sample-users', type=int, default=5,
                       help='Number of sample users to create')
    
    parser.add_argument('--create-sample-org', nargs=3, metavar=('NAME', 'ADMIN_EMAIL', 'ADMIN_PASSWORD'),
                       help='Create sample organization with admin user')
    
    args = parser.parse_args()
    
    # Initialize database
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🚀 Initializing User Management System...")
        print(f"📊 Database: {database_url}")
        
        # Create tables
        create_database_tables(engine)
        
        # Create default organization
        organization = None
        if args.create_org:
            organization = create_default_organization(db, args.create_org, args.org_domain)
        
        # Create system admin
        admin_user = None
        if args.create_admin:
            admin_user = create_system_admin_user(
                db, 
                args.admin_email, 
                args.admin_password, 
                args.admin_name,
                organization.organization_id if organization else None
            )
        
        # Create sample organization with admin
        if args.create_sample_org:
            org_name, admin_email, admin_password = args.create_sample_org
            sample_org, sample_admin = create_sample_organization(
                db, org_name, args.org_domain, admin_email, admin_password
            )
            print(f"📋 Sample organization: {sample_org.name}")
            print(f"👤 Admin user: {admin_email}")
        
        # Setup defaults and sample data
        if args.setup_defaults:
            print("📋 Setting up default roles, permissions, and sample data...")
            
            # Get or create default organization
            if not organization:
                organization = db.query(Organization).filter(
                    Organization.name == "Fernando Platform"
                ).first()
                if not organization:
                    organization = create_default_organization(db)
            
            # Create sample users if admin exists
            if admin_user or args.create_sample_org:
                sample_users = create_sample_users(db, organization.organization_id, args.sample_users)
                create_activity_logs(db, sample_users)
            
            print("✅ Default setup completed successfully")
        
        print("\n🎉 User Management System initialization completed!")
        print("\n📋 Summary:")
        if organization:
            print(f"  📊 Organization: {organization.name}")
        if admin_user:
            print(f"  👤 Admin User: {admin_user.email}")
            print(f"  🔑 Password: {args.admin_password}")
        if args.setup_defaults:
            print(f"  👥 Sample Users: {args.sample_users} created")
            print(f"  📝 Activity Logs: Generated for analytics")
        
        print("\n🔐 Security Notes:")
        print("  - Change default passwords immediately")
        print("  - Enable MFA for admin accounts")
        print("  - Review and customize role permissions")
        print("  - Configure organization settings")
        
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())