"""
Create billing and subscription tables

Revision ID: 005_add_billing
Revises: 004_add_licensing
Create Date: 2025-11-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005_add_billing'
down_revision = '004_add_licensing'
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('license_tier_id', sa.Integer(), nullable=False),
        sa.Column('monthly_price', sa.Float(), nullable=False),
        sa.Column('quarterly_price', sa.Float(), nullable=True),
        sa.Column('annual_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('max_documents_per_month', sa.Integer(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_api_calls_per_month', sa.Integer(), nullable=True),
        sa.Column('overage_document_price', sa.Float(), nullable=False, server_default='0.10'),
        sa.Column('overage_user_price', sa.Float(), nullable=False, server_default='5.00'),
        sa.Column('overage_api_call_price', sa.Float(), nullable=False, server_default='0.01'),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('trial_days', sa.Integer(), nullable=False, server_default='14'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['license_tier_id'], ['license_tiers.id'], ondelete='CASCADE')
    )
    op.create_index('ix_subscription_plans_license_tier_id', 'subscription_plans', ['license_tier_id'])
    
    # Create payment_methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('card_exp_month', sa.Integer(), nullable=True),
        sa.Column('card_exp_year', sa.Integer(), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('bank_account_last4', sa.String(4), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_payment_method_id', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )
    op.create_index('ix_payment_methods_user_id', 'payment_methods', ['user_id'])
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.String(64), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('license_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('billing_cycle', sa.String(20), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('trial_start', sa.DateTime(), nullable=True),
        sa.Column('trial_end', sa.DateTime(), nullable=True),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('last_billing_date', sa.DateTime(), nullable=True),
        sa.Column('documents_used_this_period', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_calls_used_this_period', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('additional_users_this_period', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('base_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('payment_method_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], ondelete='SET NULL')
    )
    op.create_index('ix_subscriptions_subscription_id', 'subscriptions', ['subscription_id'], unique=True)
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(64), nullable=False, unique=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.Column('tax_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('discount_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('amount_paid', sa.Float(), nullable=False, server_default='0'),
        sa.Column('amount_due', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('line_items', sa.JSON(), nullable=True),
        sa.Column('issue_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('voided_at', sa.DateTime(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('tax_rate', sa.Float(), nullable=False, server_default='0'),
        sa.Column('tax_jurisdiction', sa.String(100), nullable=True),
        sa.Column('tax_id_number', sa.String(50), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.String(64), nullable=False, unique=True),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('payment_method_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('transaction_id', sa.String(200), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('refunded_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('refunded_at', sa.DateTime(), nullable=True),
        sa.Column('refund_reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], ondelete='SET NULL')
    )
    op.create_index('ix_payments_payment_id', 'payments', ['payment_id'], unique=True)
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])
    
    # Create usage_records table
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('billing_period_start', sa.DateTime(), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(), nullable=False),
        sa.Column('billed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL')
    )
    op.create_index('ix_usage_records_subscription_id', 'usage_records', ['subscription_id'])
    op.create_index('ix_usage_records_timestamp', 'usage_records', ['timestamp'])
    
    # Create billing_events table
    op.create_table(
        'billing_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )
    op.create_index('ix_billing_events_created_at', 'billing_events', ['created_at'])
    
    # Create tax_rates table
    op.create_table(
        'tax_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country', sa.String(2), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('jurisdiction_name', sa.String(200), nullable=True),
        sa.Column('tax_type', sa.String(50), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('applies_to_digital_services', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('applies_to_physical_goods', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_until', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tax_rates_country', 'tax_rates', ['country'])
    
    # Insert default subscription plans
    op.execute("""
        INSERT INTO subscription_plans (name, description, license_tier_id, monthly_price, quarterly_price, annual_price, 
                                       max_documents_per_month, max_users, max_api_calls_per_month, features, trial_days)
        SELECT 
            'Basic Plan',
            'Perfect for small businesses and freelancers',
            id,
            29.00,
            79.00,
            299.00,
            100,
            3,
            1000,
            '{"support": "email", "priority": "normal", "features": ["basic_ocr", "document_extraction", "export_json"]}',
            14
        FROM license_tiers WHERE name = 'Basic'
        UNION ALL
        SELECT 
            'Professional Plan',
            'Ideal for growing businesses with increased processing needs',
            id,
            99.00,
            269.00,
            999.00,
            1000,
            10,
            10000,
            '{"support": "priority", "priority": "high", "features": ["advanced_ocr", "llm_extraction", "batch_processing", "api_access", "custom_workflows"]}',
            14
        FROM license_tiers WHERE name = 'Professional'
        UNION ALL
        SELECT 
            'Enterprise Plan',
            'Comprehensive solution for large organizations',
            id,
            299.00,
            799.00,
            2999.00,
            NULL,
            NULL,
            NULL,
            '{"support": "dedicated", "priority": "urgent", "features": ["unlimited_processing", "dedicated_support", "custom_integrations", "sla_guarantee", "white_label"]}',
            30
        FROM license_tiers WHERE name = 'Enterprise'
    """)
    
    # Insert default tax rates
    op.execute("""
        INSERT INTO tax_rates (country, region, jurisdiction_name, tax_type, rate, effective_from, is_active)
        VALUES 
        ('PT', NULL, 'Portugal', 'VAT', 0.23, '2025-01-01', 1),
        ('ES', NULL, 'Spain', 'VAT', 0.21, '2025-01-01', 1),
        ('FR', NULL, 'France', 'VAT', 0.20, '2025-01-01', 1),
        ('DE', NULL, 'Germany', 'VAT', 0.19, '2025-01-01', 1),
        ('IT', NULL, 'Italy', 'VAT', 0.22, '2025-01-01', 1),
        ('US', 'CA', 'California', 'sales_tax', 0.0725, '2025-01-01', 1),
        ('US', 'NY', 'New York', 'sales_tax', 0.04, '2025-01-01', 1)
    """)


def downgrade():
    op.drop_table('billing_events')
    op.drop_table('usage_records')
    op.drop_table('payments')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    op.drop_table('payment_methods')
    op.drop_table('tax_rates')
    op.drop_table('subscription_plans')
