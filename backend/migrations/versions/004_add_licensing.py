"""
Add licensing tables

This migration adds comprehensive licensing management support including:
- License tiers (Basic, Professional, Enterprise)
- License records with validation and expiration
- License assignments to users
- License usage tracking
- License audit logs for compliance

Run this migration to enable licensing features.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '004_add_licensing'
down_revision = '003_add_enterprise_features'
branch_labels = None
depends_on = None


def upgrade():
    # Create license_tiers table
    op.create_table(
        'license_tiers',
        sa.Column('tier_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price_monthly', sa.Float(), nullable=False),
        sa.Column('price_yearly', sa.Float(), nullable=False),
        sa.Column('max_documents_per_month', sa.Integer(), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=False),
        sa.Column('max_storage_gb', sa.Integer(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('tier_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_license_tiers_tier_id', 'license_tiers', ['tier_id'])
    
    # Create licenses table
    op.create_table(
        'licenses',
        sa.Column('license_id', sa.Integer(), nullable=False),
        sa.Column('license_key', sa.String(), nullable=False),
        sa.Column('tier_id', sa.Integer(), nullable=False),
        sa.Column('organization_name', sa.String(), nullable=False),
        sa.Column('organization_email', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('active', 'expired', 'suspended', 'revoked', name='license_status'), default='active'),
        sa.Column('issued_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_validated_at', sa.DateTime(), nullable=True),
        sa.Column('hardware_fingerprint', sa.String(), nullable=True),
        sa.Column('max_activations', sa.Integer(), default=1),
        sa.Column('current_activations', sa.Integer(), default=0),
        sa.Column('documents_processed_this_month', sa.Integer(), default=0),
        sa.Column('last_reset_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tier_id'], ['license_tiers.tier_id'], ),
        sa.PrimaryKeyConstraint('license_id'),
        sa.UniqueConstraint('license_key')
    )
    op.create_index('ix_licenses_license_id', 'licenses', ['license_id'])
    op.create_index('ix_licenses_license_key', 'licenses', ['license_key'])
    
    # Create license_assignments table
    op.create_table(
        'license_assignments',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('license_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('deactivated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.license_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['deactivated_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('assignment_id')
    )
    op.create_index('ix_license_assignments_assignment_id', 'license_assignments', ['assignment_id'])
    
    # Create license_usage table
    op.create_table(
        'license_usage',
        sa.Column('usage_id', sa.Integer(), nullable=False),
        sa.Column('license_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('feature_used', sa.String(), nullable=False),
        sa.Column('usage_count', sa.Integer(), default=1),
        sa.Column('usage_timestamp', sa.DateTime(), default=sa.func.now()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.license_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('usage_id')
    )
    op.create_index('ix_license_usage_usage_id', 'license_usage', ['usage_id'])
    
    # Create license_audit_logs table
    op.create_table(
        'license_audit_logs',
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('license_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.license_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index('ix_license_audit_logs_audit_id', 'license_audit_logs', ['audit_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_license_audit_logs_audit_id', table_name='license_audit_logs')
    op.drop_table('license_audit_logs')
    
    op.drop_index('ix_license_usage_usage_id', table_name='license_usage')
    op.drop_table('license_usage')
    
    op.drop_index('ix_license_assignments_assignment_id', table_name='license_assignments')
    op.drop_table('license_assignments')
    
    op.drop_index('ix_licenses_license_key', table_name='licenses')
    op.drop_index('ix_licenses_license_id', table_name='licenses')
    op.drop_table('licenses')
    
    op.drop_index('ix_license_tiers_tier_id', table_name='license_tiers')
    op.drop_table('license_tiers')
