"""
User Management System Database Migration

This migration creates the database schema for the comprehensive user management system
including RBAC, organization management, user sessions, activity tracking, and audit logging.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers
revision = '001_user_management_system'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema to support user management system"""
    
    # Create UserRoles table
    op.create_table('user_roles',
        sa.Column('role_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String, nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('level', sa.Integer, nullable=False, default=0),
        sa.Column('is_system_role', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    op.create_index('ix_user_roles_name', 'user_roles', ['name'], unique=True)
    
    # Create Permissions table
    op.create_table('permissions',
        sa.Column('permission_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String, nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('resource', sa.String, nullable=False),
        sa.Column('action', sa.String, nullable=False),
        sa.Column('conditions', sa.JSON, nullable=True)
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)
    op.create_index('ix_permissions_resource', 'permissions', ['resource'])
    
    # Create RolePermissions table (many-to-many)
    op.create_table('role_permissions',
        sa.Column('role_id', sa.String, nullable=False, primary_key=True),
        sa.Column('permission_id', sa.String, nullable=False, primary_key=True),
        sa.Column('granted_by', sa.String, nullable=True),
        sa.Column('granted_at', sa.DateTime, nullable=False, default=datetime.utcnow)
    )
    op.create_foreign_key('fk_role_permissions_role', 'role_permissions', 'user_roles', ['role_id'], ['role_id'])
    op.create_foreign_key('fk_role_permissions_permission', 'role_permissions', 'permissions', ['permission_id'], ['permission_id'])
    op.create_unique_constraint('uq_role_permission', 'role_permissions', ['role_id', 'permission_id'])
    
    # Create Organizations table
    op.create_table('organizations',
        sa.Column('organization_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('domain', sa.String, nullable=True, unique=True),
        sa.Column('subscription_tier', sa.String, nullable=False, default='basic'),
        sa.Column('subscription_status', sa.String, nullable=False, default='active'),
        sa.Column('max_users', sa.Integer, nullable=False, default=10),
        sa.Column('max_documents', sa.Integer, nullable=False, default=1000),
        sa.Column('max_storage_gb', sa.Integer, nullable=False, default=10),
        sa.Column('settings', sa.JSON, nullable=False, default={}),
        sa.Column('features', sa.JSON, nullable=False, default=[]),
        sa.Column('billing_email', sa.String, nullable=True),
        sa.Column('billing_address', sa.Text, nullable=True),
        sa.Column('tax_id', sa.String, nullable=True),
        sa.Column('status', sa.String, nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_domain', 'organizations', ['domain'], unique=True)
    
    # Add new columns to existing users table
    op.add_column('users', sa.Column('organization_id', sa.String, nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean, nullable=False, default=False))
    op.add_column('users', sa.Column('phone_verified', sa.Boolean, nullable=False, default=False))
    op.add_column('users', sa.Column('phone', sa.String, nullable=True))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean, nullable=False, default=False))
    op.add_column('users', sa.Column('last_login', sa.DateTime, nullable=True))
    op.add_column('users', sa.Column('last_password_change', sa.DateTime, nullable=False, default=datetime.utcnow))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean, nullable=False, default=False))
    op.add_column('users', sa.Column('api_key', sa.String, nullable=True, unique=True))
    op.add_column('users', sa.Column('api_key_expires_at', sa.DateTime, nullable=True))
    op.add_column('users', sa.Column('api_key_last_used', sa.DateTime, nullable=True))
    op.add_column('users', sa.Column('department', sa.String, nullable=True))
    op.add_column('users', sa.Column('job_title', sa.String, nullable=True))
    op.add_column('users', sa.Column('profile_image_url', sa.String, nullable=True))
    op.add_column('users', sa.Column('bio', sa.Text, nullable=True))
    
    # Create foreign key for organization
    op.create_foreign_key('fk_users_organization', 'users', 'organizations', ['organization_id'], ['organization_id'])
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    
    # Create UserRoleAssignments table
    op.create_table('user_role_assignments',
        sa.Column('assignment_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.String, nullable=False),
        sa.Column('role_id', sa.String, nullable=False),
        sa.Column('organization_id', sa.String, nullable=True),
        sa.Column('assigned_by', sa.String, nullable=True),
        sa.Column('assigned_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True)
    )
    op.create_foreign_key('fk_user_role_assignments_user', 'user_role_assignments', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('fk_user_role_assignments_role', 'user_role_assignments', 'user_roles', ['role_id'], ['role_id'])
    op.create_foreign_key('fk_user_role_assignments_organization', 'user_role_assignments', 'organizations', ['organization_id'], ['organization_id'])
    op.create_foreign_key('fk_user_role_assignments_assigned_by', 'user_role_assignments', 'users', ['assigned_by'], ['user_id'])
    op.create_unique_constraint('uq_user_role_org', 'user_role_assignments', ['user_id', 'role_id', 'organization_id'])
    op.create_index('ix_user_role_user_org', 'user_role_assignments', ['user_id', 'organization_id'])
    
    # Create UserSessions table
    op.create_table('user_sessions',
        sa.Column('session_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.String, nullable=False),
        sa.Column('organization_id', sa.String, nullable=True),
        sa.Column('ip_address', sa.String, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('device_info', sa.JSON, nullable=True),
        sa.Column('location', sa.JSON, nullable=True),
        sa.Column('login_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('last_activity_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('logout_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('mfa_verified', sa.Boolean, nullable=False, default=False),
        sa.Column('risk_score', sa.Integer, nullable=False, default=0)
    )
    op.create_foreign_key('fk_user_sessions_user', 'user_sessions', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('fk_user_sessions_organization', 'user_sessions', 'organizations', ['organization_id'], ['organization_id'])
    op.create_index('ix_user_sessions_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('ix_user_sessions_expires', 'user_sessions', ['expires_at'])
    
    # Create UserInvitations table
    op.create_table('user_invitations',
        sa.Column('invitation_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('organization_id', sa.String, nullable=False),
        sa.Column('email', sa.String, nullable=False),
        sa.Column('role_id', sa.String, nullable=True),
        sa.Column('invited_by', sa.String, nullable=False),
        sa.Column('token', sa.String, nullable=False, unique=True),
        sa.Column('status', sa.String, nullable=False, default='pending'),
        sa.Column('expires_at', sa.DateTime, nullable=False, default=lambda: datetime.utcnow() + sa.text("INTERVAL '7 days'")),
        sa.Column('accepted_at', sa.DateTime, nullable=True),
        sa.Column('accepted_user_id', sa.String, nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow)
    )
    op.create_foreign_key('fk_user_invitations_organization', 'user_invitations', 'organizations', ['organization_id'], ['organization_id'])
    op.create_foreign_key('fk_user_invitations_role', 'user_invitations', 'user_roles', ['role_id'], ['role_id'])
    op.create_foreign_key('fk_user_invitations_invited_by', 'user_invitations', 'users', ['invited_by'], ['user_id'])
    op.create_foreign_key('fk_user_invitations_accepted_user', 'user_invitations', 'users', ['accepted_user_id'], ['user_id'])
    op.create_index('ix_user_invitations_token', 'user_invitations', ['token'], unique=True)
    op.create_index('ix_user_invitations_email_status', 'user_invitations', ['email', 'status'])
    
    # Create UserActivities table
    op.create_table('user_activities',
        sa.Column('activity_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.String, nullable=False),
        sa.Column('organization_id', sa.String, nullable=True),
        sa.Column('action', sa.String, nullable=False),
        sa.Column('resource_type', sa.String, nullable=True),
        sa.Column('resource_id', sa.String, nullable=True),
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('ip_address', sa.String, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('session_id', sa.String, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow)
    )
    op.create_foreign_key('fk_user_activities_user', 'user_activities', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key('fk_user_activities_organization', 'user_activities', 'organizations', ['organization_id'], ['organization_id'])
    op.create_foreign_key('fk_user_activities_session', 'user_activities', 'user_sessions', ['session_id'], ['session_id'])
    op.create_index('ix_user_activities_user_created', 'user_activities', ['user_id', 'created_at'])
    op.create_index('ix_user_activities_org_created', 'user_activities', ['organization_id', 'created_at'])
    
    # Create UserPreferences table
    op.create_table('user_preferences',
        sa.Column('preference_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.String, nullable=False, unique=True),
        sa.Column('email_notifications', sa.JSON, nullable=False, default={
            'login_alerts': True,
            'security_alerts': True,
            'system_updates': False,
            'marketing_emails': False
        }),
        sa.Column('theme', sa.String, nullable=False, default='system'),
        sa.Column('language', sa.String, nullable=False, default='en'),
        sa.Column('timezone', sa.String, nullable=False, default='UTC'),
        sa.Column('date_format', sa.String, nullable=False, default='YYYY-MM-DD'),
        sa.Column('two_factor_enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('session_timeout_minutes', sa.Integer, nullable=False, default=30),
        sa.Column('password_last_changed', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('dashboard_layout', sa.JSON, nullable=True, default={}),
        sa.Column('default_view', sa.String, nullable=False, default='dashboard'),
        sa.Column('api_key_enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('api_key_last_used', sa.DateTime, nullable=True)
    )
    op.create_foreign_key('fk_user_preferences_user', 'user_preferences', 'users', ['user_id'], ['user_id'])
    
    # Create AccountSecurity table
    op.create_table('account_security',
        sa.Column('security_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('user_id', sa.String, nullable=False, unique=True),
        sa.Column('password_failed_attempts', sa.Integer, nullable=False, default=0),
        sa.Column('password_last_failed_at', sa.DateTime, nullable=True),
        sa.Column('password_locked_until', sa.DateTime, nullable=True),
        sa.Column('password_change_required', sa.Boolean, nullable=False, default=False),
        sa.Column('two_factor_secret', sa.String, nullable=True),
        sa.Column('two_factor_backup_codes', sa.JSON, nullable=True),
        sa.Column('two_factor_enabled_at', sa.DateTime, nullable=True),
        sa.Column('two_factor_last_used', sa.DateTime, nullable=True),
        sa.Column('login_attempts', sa.JSON, nullable=False, default=[]),
        sa.Column('last_login_ip', sa.String, nullable=True),
        sa.Column('last_login_at', sa.DateTime, nullable=True),
        sa.Column('security_events', sa.JSON, nullable=False, default=[])
    )
    op.create_foreign_key('fk_account_security_user', 'account_security', 'users', ['user_id'], ['user_id'])
    
    # Create AuditLogs table
    op.create_table('audit_logs',
        sa.Column('audit_id', sa.String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('actor_user_id', sa.String, nullable=True),
        sa.Column('actor_ip', sa.String, nullable=True),
        sa.Column('actor_user_agent', sa.Text, nullable=True),
        sa.Column('action', sa.String, nullable=False),
        sa.Column('resource_type', sa.String, nullable=False),
        sa.Column('resource_id', sa.String, nullable=True),
        sa.Column('old_values', sa.JSON, nullable=True),
        sa.Column('new_values', sa.JSON, nullable=True),
        sa.Column('changed_fields', sa.JSON, nullable=True),
        sa.Column('organization_id', sa.String, nullable=True),
        sa.Column('session_id', sa.String, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('correlation_id', sa.String, nullable=True)
    )
    op.create_foreign_key('fk_audit_logs_user', 'audit_logs', 'users', ['actor_user_id'], ['user_id'])
    op.create_foreign_key('fk_audit_logs_organization', 'audit_logs', 'organizations', ['organization_id'], ['organization_id'])
    op.create_foreign_key('fk_audit_logs_session', 'audit_logs', 'user_sessions', ['session_id'], ['session_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_actor_resource', 'audit_logs', ['actor_user_id', 'resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_correlation', 'audit_logs', ['correlation_id'])
    
    # Insert default system roles
    op.execute("""
        INSERT INTO user_roles (role_id, name, description, level, is_system_role) VALUES
        ('system-admin', 'system_admin', 'System Administrator - Full system access', 10, true),
        ('admin', 'admin', 'Organization Administrator - Full organization access', 7, true),
        ('manager', 'manager', 'Manager - Department and team management', 4, true),
        ('user', 'user', 'Standard User - Basic access to assigned resources', 1, true),
        ('viewer', 'viewer', 'View-only access to read resources', 0, true)
    """)
    
    # Insert default permissions
    op.execute("""
        INSERT INTO permissions (permission_id, name, description, resource, action) VALUES
        -- User management permissions
        ('users-create', 'users.create', 'Create new users', 'users', 'create'),
        ('users-read', 'users.read', 'Read user information', 'users', 'read'),
        ('users-update', 'users.update', 'Update user information', 'users', 'update'),
        ('users-delete', 'users.delete', 'Delete users', 'users', 'delete'),
        ('users-admin', 'users.admin', 'Full user management access', 'users', 'admin'),
        ('users-deactivate', 'users.deactivate', 'Deactivate user accounts', 'users', 'deactivate'),
        ('users-reactivate', 'users.reactivate', 'Reactivate user accounts', 'users', 'reactivate'),
        ('users-invite', 'users.invite', 'Invite users to organization', 'users', 'invite'),
        ('users-reset-password', 'users.reset_password', 'Reset user passwords', 'users', 'reset_password'),
        ('users-bulk', 'users.bulk', 'Perform bulk operations on users', 'users', 'bulk'),
        
        -- Role management permissions
        ('roles-create', 'roles.create', 'Create new roles', 'roles', 'create'),
        ('roles-read', 'roles.read', 'Read role information', 'roles', 'read'),
        ('roles-update', 'roles.update', 'Update role information', 'roles', 'update'),
        ('roles-delete', 'roles.delete', 'Delete roles', 'roles', 'delete'),
        ('roles-assign', 'roles.assign', 'Assign roles to users', 'roles', 'assign'),
        ('roles-revoke', 'roles.revoke', 'Revoke roles from users', 'roles', 'revoke'),
        
        -- Document permissions
        ('documents-create', 'documents.create', 'Create new documents', 'documents', 'create'),
        ('documents-read', 'documents.read', 'Read document information', 'documents', 'read'),
        ('documents-update', 'documents.update', 'Update document information', 'documents', 'update'),
        ('documents-delete', 'documents.delete', 'Delete documents', 'documents', 'delete'),
        ('documents-admin', 'documents.admin', 'Full document management access', 'documents', 'admin'),
        ('documents-upload', 'documents.upload', 'Upload new documents', 'documents', 'upload'),
        ('documents-review', 'documents.review', 'Review document processing', 'documents', 'review'),
        ('documents-export', 'documents.export', 'Export document data', 'documents', 'export'),
        
        -- Organization permissions
        ('organizations-read', 'organizations.read', 'Read organization information', 'organizations', 'read'),
        ('organizations-update', 'organizations.update', 'Update organization information', 'organizations', 'update'),
        ('organizations-admin', 'organizations.admin', 'Full organization management access', 'organizations', 'admin'),
        
        -- Billing permissions
        ('billing-read', 'billing.read', 'Read billing information', 'billing', 'read'),
        ('billing-update', 'billing.update', 'Update billing information', 'billing', 'update'),
        ('billing-admin', 'billing.admin', 'Full billing management access', 'billing', 'admin'),
        
        -- Report permissions
        ('reports-read', 'reports.read', 'Read reports', 'reports', 'read'),
        ('reports-create', 'reports.create', 'Create reports', 'reports', 'create'),
        ('reports-export', 'reports.export', 'Export reports', 'reports', 'export'),
        
        -- Settings permissions
        ('settings-read', 'settings.read', 'Read system settings', 'settings', 'read'),
        ('settings-update', 'settings.update', 'Update system settings', 'settings', 'update'),
        ('settings-admin', 'settings.admin', 'Full settings management access', 'settings', 'admin')
    """)
    
    # Assign default permissions to system roles
    # System Admin gets all permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
        SELECT 'system-admin', permission_id, 'system', CURRENT_TIMESTAMP
        FROM permissions
    """)
    
    # Admin gets most permissions
    admin_permissions = [
        'users-create', 'users-read', 'users-update', 'users-delete', 'users-admin',
        'users-deactivate', 'users-reactivate', 'users-invite', 'users-bulk',
        'roles-read', 'roles-assign', 'roles-revoke',
        'documents-create', 'documents-read', 'documents-update', 'documents-delete', 'documents-admin',
        'documents-upload', 'documents-review', 'documents-export',
        'organizations-read', 'organizations-update',
        'billing-read', 'billing-update', 'billing-admin',
        'reports-read', 'reports-create', 'reports-export',
        'settings-read', 'settings-update'
    ]
    
    for perm_id in admin_permissions:
        op.execute(f"""
            INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
            VALUES ('admin', '{perm_id}', 'system', CURRENT_TIMESTAMP)
        """)
    
    # Manager gets standard permissions
    manager_permissions = [
        'users-read', 'users-update',
        'roles-read',
        'documents-create', 'documents-read', 'documents-update',
        'documents-upload', 'documents-review',
        'organizations-read',
        'billing-read',
        'reports-read', 'reports-create', 'reports-export',
        'settings-read'
    ]
    
    for perm_id in manager_permissions:
        op.execute(f"""
            INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
            VALUES ('manager', '{perm_id}', 'system', CURRENT_TIMESTAMP)
        """)
    
    # User gets basic permissions
    user_permissions = [
        'users-read', 'users-update',  # Can update own profile
        'documents-create', 'documents-read', 'documents-update',
        'documents-upload',
        'organizations-read',
        'reports-read', 'reports-create',
        'settings-read'
    ]
    
    for perm_id in user_permissions:
        op.execute(f"""
            INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
            VALUES ('user', '{perm_id}', 'system', CURRENT_TIMESTAMP)
        """)
    
    # Viewer gets read-only permissions
    viewer_permissions = [
        'users-read',
        'documents-read',
        'organizations-read',
        'reports-read',
        'settings-read'
    ]
    
    for perm_id in viewer_permissions:
        op.execute(f"""
            INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
            VALUES ('viewer', '{perm_id}', 'system', CURRENT_TIMESTAMP)
        """)

def downgrade():
    """Downgrade database schema - WARNING: This will delete all user management data"""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('audit_logs')
    op.drop_table('account_security')
    op.drop_table('user_preferences')
    op.drop_table('user_activities')
    op.drop_table('user_invitations')
    op.drop_table('user_sessions')
    op.drop_table('user_role_assignments')
    
    # Remove new columns from users table
    op.drop_column('users', 'bio')
    op.drop_column('users', 'profile_image_url')
    op.drop_column('users', 'job_title')
    op.drop_column('users', 'department')
    op.drop_column('users', 'api_key_last_used')
    op.drop_column('users', 'api_key_expires_at')
    op.drop_column('users', 'api_key')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'phone_verified')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'organization_id')
    
    # Drop remaining tables
    op.drop_table('organizations')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('user_roles')