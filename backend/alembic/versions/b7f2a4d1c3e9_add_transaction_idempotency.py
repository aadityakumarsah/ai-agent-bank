"""add transaction idempotency key

Revision ID: b7f2a4d1c3e9
Revises: 9f2c4b1a3d8a
Create Date: 2026-09-07 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7f2a4d1c3e9'
down_revision = '9f2c4b1a3d8a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('idempotency_key', sa.String(), nullable=True))
    op.create_index(
        'ix_transactions_idempotency_key',
        'transactions',
        ['idempotency_key'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_transactions_idempotency_key', table_name='transactions')
    op.drop_column('transactions', 'idempotency_key')