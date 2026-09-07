"""add policy monthly limit

Revision ID: c8d4b2a5e6f1
Revises: b7f2a4d1c3e9
Create Date: 2026-09-07 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d4b2a5e6f1'
down_revision = 'b7f2a4d1c3e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('policies', sa.Column('max_per_month', sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    op.drop_column('policies', 'max_per_month')