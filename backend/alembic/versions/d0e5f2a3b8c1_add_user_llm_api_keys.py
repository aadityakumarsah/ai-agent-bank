"""add user llm api keys table

Revision ID: d0e5f2a3b8c1
Revises: c8d4b2a5e6f1
Create Date: 2026-09-07 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e5f2a3b8c1'
down_revision = 'c8d4b2a5e6f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_api_keys_user_provider'),
    )


def downgrade() -> None:
    op.drop_table('user_api_keys')