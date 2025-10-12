"""Add income and recurring expense tables

Revision ID: new_migration_001
Revises: 4cc7711dc5e2
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric


# revision identifiers, used by Alembic.
revision = 'new_migration_001'
down_revision = '4cc7711dc5e2'
branch_labels = None
depends_on = None


def upgrade():
    # Create income table
    op.create_table('income',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('amount', Numeric(precision=10, scale=2), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_income_date'), 'income', ['date'], unique=False)

    # Create recurring_expense table
    op.create_table('recurring_expense',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('amount', Numeric(precision=10, scale=2), nullable=False),
        sa.Column('frequency', sa.String(length=20), nullable=False),
        sa.Column('next_due', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes to existing tables for better performance
    with op.batch_alter_table('expense', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_expense_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_expense_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_expense_payment_method'), ['payment_method'], unique=False)

    with op.batch_alter_table('budget', schema=None) as batch_op:
        batch_op.create_index('idx_month_year', ['month', 'year'], unique=False)


def downgrade():
    # Drop indexes from budget
    with op.batch_alter_table('budget', schema=None) as batch_op:
        batch_op.drop_index('idx_month_year')

    # Drop indexes from expense
    with op.batch_alter_table('expense', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_expense_payment_method'))
        batch_op.drop_index(batch_op.f('ix_expense_category'))
        batch_op.drop_index(batch_op.f('ix_expense_date'))

    # Drop recurring_expense table
    op.drop_table('recurring_expense')

    # Drop income table
    op.drop_index(op.f('ix_income_date'), table_name='income')
    op.drop_table('income')