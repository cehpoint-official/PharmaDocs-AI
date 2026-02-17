"""Add subscription and payment models

Revision ID: 202501011200
Revises: 8878c4182c0a
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql, postgresql, sqlite

# revision identifiers, used by Alembic.
revision = '202501011200'
down_revision = '8878c4182c0a'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('razorpay_customer_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='active'))
        batch_op.add_column(sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('documents_limit', sa.Integer(), nullable=False, server_default='5'))

    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_plan_id', sa.String(length=255), nullable=True),
        sa.Column('plan_name', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True, default=False),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('trial_start', sa.DateTime(), nullable=True),
        sa.Column('trial_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_charge_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_order_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, default='inr'),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.String(length=500), nullable=True),
        sa.Column('refunded_amount', sa.Integer(), nullable=False, default=0),
        sa.Column('failure_reason', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create subscription_plans table
    op.create_table('subscription_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, default='usd'),
        sa.Column('billing_interval', sa.String(length=20), nullable=False, default='month'),
        sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
        sa.Column('documents_per_month', sa.Integer(), nullable=False),
        sa.Column('storage_mb', sa.Integer(), nullable=False),
        sa.Column('api_requests_per_day', sa.Integer(), nullable=False),
        sa.Column('features', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Insert default subscription plans
    op.execute("""
        INSERT INTO subscription_plans (name, display_name, description, price, currency, documents_per_month, storage_mb, api_requests_per_day, features, sort_order)
        VALUES 
        ('free', 'Free', 'Perfect for getting started with basic pharmaceutical documentation', 0, 'inr', 5, 100, 10, '["basic_reports", "email_support"]', 1),
        ('basic', 'Basic', 'Ideal for small pharmaceutical companies and individual researchers', 49900, 'inr', 50, 1000, 100, '["basic_reports", "advanced_reports", "email_support", "priority_support"]', 2),
        ('premium', 'Premium', 'Complete solution for large pharmaceutical companies', 149900, 'inr', -1, 10000, 1000, '["all_reports", "custom_templates", "priority_support", "phone_support", "api_access"]', 3)
    """)

    # Create indexes for better performance
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_razorpay_subscription_id'), 'subscriptions', ['razorpay_subscription_id'], unique=False)
    op.create_index(op.f('ix_payments_user_id'), 'payments', ['user_id'], unique=False)
    op.create_index(op.f('ix_payments_stripe_payment_intent_id'), 'payments', ['stripe_payment_intent_id'], unique=False)
    op.create_index(op.f('ix_payments_razorpay_order_id'), 'payments', ['razorpay_order_id'], unique=False)
    op.create_index(op.f('ix_users_stripe_customer_id'), 'users', ['stripe_customer_id'], unique=False)
    op.create_index(op.f('ix_users_razorpay_customer_id'), 'users', ['razorpay_customer_id'], unique=False)

def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_users_razorpay_customer_id'), table_name='users')
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')
    op.drop_index(op.f('ix_payments_razorpay_order_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_stripe_payment_intent_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_user_id'), table_name='payments')
    op.drop_index(op.f('ix_subscriptions_razorpay_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')

    # Drop tables
    op.drop_table('subscription_plans')
    op.drop_table('payments')
    op.drop_table('subscriptions')

    # Remove columns from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('documents_limit')
        batch_op.drop_column('trial_ends_at')
        batch_op.drop_column('subscription_status')
        batch_op.drop_column('razorpay_customer_id')
        batch_op.drop_column('stripe_customer_id')