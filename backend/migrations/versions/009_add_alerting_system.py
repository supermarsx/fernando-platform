"""Add comprehensive alerting system

Revision ID: 009_add_alerting_system
Revises: 
Create Date: 2025-11-06 05:47:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_add_alerting_system'
down_revision = '008_add_revenue_operations'
branch_labels = None
depends_on = None


def upgrade():
    """Create alerting system tables."""
    
    # Alert Rules table
    op.create_table('alert_rules',
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('alert_type', postgresql.ENUM('system', 'application', 'business', 'security', 'custom', name='alerttype'), nullable=False),
        sa.Column('severity', postgresql.ENUM('critical', 'high', 'medium', 'low', 'info', name='alertseverity'), nullable=False),
        sa.Column('condition', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('threshold_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('query_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('channels', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('recipients', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('evaluation_frequency', sa.Integer(), nullable=True),
        sa.Column('sustained_duration', sa.Integer(), nullable=True),
        sa.Column('cooldown_period', sa.Integer(), nullable=True),
        sa.Column('escalation_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('rule_id')
    )
    
    # Alerts table
    op.create_table('alerts',
        sa.Column('alert_id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'acknowledged', 'resolved', 'suppressed', 'escalated', name='alertstatus'), nullable=False),
        sa.Column('severity', postgresql.ENUM('critical', 'high', 'medium', 'low', 'info', name='alertseverity'), nullable=False),
        sa.Column('alert_type', postgresql.ENUM('system', 'application', 'business', 'security', 'custom', name='alerttype'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('labels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.String(), nullable=True),
        sa.Column('resolved_by', sa.String(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('notifications_sent', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_count', sa.Integer(), nullable=True),
        sa.Column('last_notification_sent', sa.DateTime(), nullable=True),
        sa.Column('escalation_level', sa.Integer(), nullable=True),
        sa.Column('escalated_at', sa.DateTime(), nullable=True),
        sa.Column('escalation_action', postgresql.ENUM('notify_manager', 'page_oncall', 'create_incident', 'escalate_channel', name='escalationaction'), nullable=True),
        sa.Column('dedup_key', sa.String(), nullable=True),
        sa.Column('runbook_url', sa.String(), nullable=True),
        sa.Column('source_system', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.rule_id'], ),
        sa.PrimaryKeyConstraint('alert_id')
    )
    
    # Create index on dedup_key for faster deduplication queries
    op.create_index('ix_alerts_dedup_key', 'alerts', ['dedup_key'], unique=False)
    
    # Alert Notifications table
    op.create_table('alert_notifications',
        sa.Column('notification_id', sa.String(), nullable=False),
        sa.Column('alert_id', sa.String(), nullable=False),
        sa.Column('channel', postgresql.ENUM('email', 'slack', 'discord', 'webhook', 'sms', 'push', name='alertchannel'), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.alert_id'], ),
        sa.PrimaryKeyConstraint('notification_id')
    )
    
    # Escalation Policies table
    op.create_table('escalation_policies',
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('escalation_levels', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('escalation_rules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('auto_resolution', sa.Boolean(), nullable=True),
        sa.Column('escalation_timeouts', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('policy_id')
    )
    
    # On-Call Schedules table
    op.create_table('oncall_schedules',
        sa.Column('schedule_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rotation_type', sa.String(), nullable=True),
        sa.Column('participants', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('working_hours', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('holidays', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('escalation_chain', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('schedule_id')
    )
    
    # Alert Templates table
    op.create_table('alert_templates',
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('channel', postgresql.ENUM('email', 'slack', 'discord', 'webhook', 'sms', 'push', name='alertchannel'), nullable=False),
        sa.Column('alert_type', postgresql.ENUM('system', 'application', 'business', 'security', 'custom', name='alerttype'), nullable=True),
        sa.Column('severity', postgresql.ENUM('critical', 'high', 'medium', 'low', 'info', name='alertseverity'), nullable=True),
        sa.Column('subject_template', sa.String(), nullable=True),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('template_type', sa.String(), nullable=True),
        sa.Column('format_type', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('template_id')
    )
    
    # Metric Thresholds table
    op.create_table('metric_thresholds',
        sa.Column('threshold_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('operator', sa.String(), nullable=False),
        sa.Column('warning_threshold', sa.Float(), nullable=True),
        sa.Column('critical_threshold', sa.Float(), nullable=True),
        sa.Column('time_window', sa.Integer(), nullable=True),
        sa.Column('aggregation_method', sa.String(), nullable=True),
        sa.Column('evaluation_period', sa.Integer(), nullable=True),
        sa.Column('labels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('threshold_id')
    )


def downgrade():
    """Drop alerting system tables."""
    
    op.drop_table('metric_thresholds')
    op.drop_table('alert_templates')
    op.drop_table('oncall_schedules')
    op.drop_table('escalation_policies')
    op.drop_table('alert_notifications')
    op.drop_table('alerts')
    op.drop_table('alert_rules')
    
    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS escalationaction')
    op.execute('DROP TYPE IF EXISTS alertchannel')
    op.execute('DROP TYPE IF EXISTS alertstatus')
    op.execute('DROP TYPE IF EXISTS alertseverity')
    op.execute('DROP TYPE IF EXISTS alerttype')