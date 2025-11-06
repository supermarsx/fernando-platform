"""
Credit System Database Migration

This migration creates all necessary tables for the credit system including:
- Credit accounts and balances
- Credit transactions
- Credit policies and packages
- Credit usage logs and reservations
- Credit alerts and forecasting

Migration: 001_credit_system_tables
Created: 2025-11-06
Author: Fernando Platform Credit System Integration
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Create credit system tables"""
    
    # ============================================================================
    # CREDIT ACCOUNTS TABLE
    # ============================================================================
    
    op.create_table('credit_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('organization_id', sa.Integer(), nullable=True, comment='Organization ID'),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('reserved_balance', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('total_earned', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('total_spent', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_accounts_user_id', 'user_id'),
        sa.Index('ix_credit_accounts_organization_id', 'organization_id'),
        sa.Index('ix_credit_accounts_status', 'status')
    )
    
    # ============================================================================
    # CREDIT TRANSACTIONS TABLE
    # ============================================================================
    
    op.create_table('credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(255), nullable=True),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_transactions_account_id', 'account_id'),
        sa.Index('ix_credit_transactions_user_id', 'user_id'),
        sa.Index('ix_credit_transactions_type', 'transaction_type'),
        sa.Index('ix_credit_transactions_created_at', 'created_at'),
        sa.Index('ix_credit_transactions_reference', 'reference_id', 'reference_type')
    )
    
    # ============================================================================
    # CREDIT POLICIES TABLE
    # ============================================================================
    
    op.create_table('credit_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('policy_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('monthly_allocation', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('auto_replenish', sa.Boolean(), nullable=False, default=False),
        sa.Column('minimum_balance', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('maximum_balance', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('cost_per_unit', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_policies_account_id', 'account_id'),
        sa.Index('ix_credit_policies_type', 'policy_type'),
        sa.Index('ix_credit_policies_active', 'is_active')
    )
    
    # ============================================================================
    # CREDIT PACKAGES TABLE
    # ============================================================================
    
    op.create_table('credit_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('credit_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('discount_percentage', sa.Numeric(precision=5, scale=2), nullable=False, default=0.0),
        sa.Column('is_popular', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_packages_active', 'is_active'),
        sa.Index('ix_credit_packages_popular', 'is_popular'),
        sa.Index('ix_credit_packages_sort', 'sort_order')
    )
    
    # ============================================================================
    # CREDIT USAGE LOGS TABLE
    # ============================================================================
    
    op.create_table('credit_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('service_type', sa.String(100), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=True),
        sa.Column('operation_type', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('request_metadata', sa.JSON(), nullable=True),
        sa.Column('response_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_usage_logs_account_id', 'account_id'),
        sa.Index('ix_credit_usage_logs_user_id', 'user_id'),
        sa.Index('ix_credit_usage_logs_service', 'service_type'),
        sa.Index('ix_credit_usage_logs_model', 'model_name'),
        sa.Index('ix_credit_usage_logs_created_at', 'created_at')
    )
    
    # ============================================================================
    # CREDIT RESERVATIONS TABLE
    # ============================================================================
    
    op.create_table('credit_reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('purpose', sa.String(255), nullable=False),
        sa.Column('reference_id', sa.String(255), nullable=True),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_reservations_account_id', 'account_id'),
        sa.Index('ix_credit_reservations_user_id', 'user_id'),
        sa.Index('ix_credit_reservations_status', 'status'),
        sa.Index('ix_credit_reservations_expires', 'expires_at'),
        sa.Index('ix_credit_reservations_reference', 'reference_id', 'reference_type')
    )
    
    # ============================================================================
    # CREDIT ALERTS TABLE
    # ============================================================================
    
    op.create_table('credit_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_alerts_account_id', 'account_id'),
        sa.Index('ix_credit_alerts_user_id', 'user_id'),
        sa.Index('ix_credit_alerts_type', 'alert_type'),
        sa.Index('ix_credit_alerts_severity', 'severity'),
        sa.Index('ix_credit_alerts_read', 'is_read'),
        sa.Index('ix_credit_alerts_resolved', 'is_resolved')
    )
    
    # ============================================================================
    # CREDIT TRANSFERS TABLE
    # ============================================================================
    
    op.create_table('credit_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_account_id', sa.Integer(), nullable=False),
        sa.Column('to_account_id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.String(255), nullable=False, comment='Source User ID'),
        sa.Column('to_user_id', sa.String(255), nullable=False, comment='Target User ID'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('transfer_fee', sa.Numeric(precision=10, scale=2), nullable=False, default=0.0),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_transfers_from_account', 'from_account_id'),
        sa.Index('ix_credit_transfers_to_account', 'to_account_id'),
        sa.Index('ix_credit_transfers_from_user', 'from_user_id'),
        sa.Index('ix_credit_transfers_to_user', 'to_user_id'),
        sa.Index('ix_credit_transfers_status', 'status'),
        sa.Index('ix_credit_transfers_created_at', 'created_at')
    )
    
    # ============================================================================
    # CREDIT FORECASTS TABLE
    # ============================================================================
    
    op.create_table('credit_forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('predicted_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('confidence_level', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('forecast_period_days', sa.Integer(), nullable=False),
        sa.Column('historical_data_days', sa.Integer(), nullable=False),
        sa.Column('factors_considered', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_forecasts_account_id', 'account_id'),
        sa.Index('ix_credit_forecasts_user_id', 'user_id'),
        sa.Index('ix_credit_forecasts_date', 'forecast_date'),
        sa.Index('ix_credit_forecasts_confidence', 'confidence_level')
    )
    
    # ============================================================================
    # CREDIT ANALYTICS TABLE
    # ============================================================================
    
    op.create_table('credit_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User ID (UUID string)'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('total_usage_cost', sa.Numeric(precision=15, scale=2), nullable=False, default=0.0),
        sa.Column('total_transactions', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_cost_per_transaction', sa.Numeric(precision=10, scale=6), nullable=False, default=0.0),
        sa.Column('peak_usage_day', sa.Date(), nullable=True),
        sa.Column('peak_usage_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('service_breakdown', sa.JSON(), nullable=True),
        sa.Column('user_behavior_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('efficiency_metrics', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['account_id'], ['credit_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_credit_analytics_account_id', 'account_id'),
        sa.Index('ix_credit_analytics_user_id', 'user_id'),
        sa.Index('ix_credit_analytics_period', 'period_start', 'period_end'),
        sa.Index('ix_credit_analytics_type', 'period_type')
    )
    
    # ============================================================================
    # ADD TRIGGERS FOR UPDATED_AT
    # ============================================================================
    
    # Function to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Add triggers for tables with updated_at columns
    tables_with_updated_at = [
        'credit_accounts',
        'credit_policies',
        'credit_packages'
    ]
    
    for table_name in tables_with_updated_at:
        op.execute(f"""
            CREATE TRIGGER update_{table_name}_updated_at 
            BEFORE UPDATE ON {table_name} 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade():
    """Drop credit system tables in reverse order"""
    
    # Drop tables in reverse order to handle foreign key dependencies
    tables_to_drop = [
        'credit_analytics',
        'credit_forecasts', 
        'credit_transfers',
        'credit_alerts',
        'credit_reservations',
        'credit_usage_logs',
        'credit_packages',
        'credit_policies',
        'credit_transactions',
        'credit_accounts'
    ]
    
    for table_name in tables_to_drop:
        op.drop_table(table_name)
    
    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")


# ============================================================================
# ADD INITIAL DATA
# ============================================================================

def create_initial_credit_packages():
    """Create initial credit packages"""
    
    packages = [
        {
            'name': 'Starter Pack',
            'description': 'Perfect for light usage and testing',
            'credit_amount': 100.0,
            'price': 1.00,
            'discount_percentage': 0.0,
            'is_popular': False,
            'sort_order': 1
        },
        {
            'name': 'Professional Pack',
            'description': 'Ideal for regular business use',
            'credit_amount': 1000.0,
            'price': 8.50,
            'discount_percentage': 15.0,
            'is_popular': True,
            'sort_order': 2
        },
        {
            'name': 'Enterprise Pack',
            'description': 'Best value for heavy usage',
            'credit_amount': 5000.0,
            'price': 37.50,
            'discount_percentage': 25.0,
            'is_popular': False,
            'sort_order': 3
        },
        {
            'name': 'Unlimited Pack',
            'description': 'Unlimited credits for large organizations',
            'credit_amount': 25000.0,
            'price': 150.00,
            'discount_percentage': 40.0,
            'is_popular': False,
            'sort_order': 4
        }
    ]
    
    # This would be executed separately after the migration
    return packages


if __name__ == '__main__':
    # This allows running the migration directly for testing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Example usage:
    # from migrations.001_create_credit_system_tables import create_initial_credit_packages
    # packages = create_initial_credit_packages()
    
    print("Credit system migration script created successfully!")
    print("Run with: alembic upgrade head")
    print("Run with: alembic downgrade -1")