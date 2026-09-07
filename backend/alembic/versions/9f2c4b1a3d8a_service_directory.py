"""service directory marketplace

Revision ID: 9f2c4b1a3d8a
Revises: e70155e7e787
Create Date: 2026-09-07 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '9f2c4b1a3d8a'
down_revision = 'e70155e7e787'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'service_directory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('api', 'compute', 'data', 'ai_model', 'storage', 'other_agent', name='servicecategory'), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('wallet_address', sa.String(), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('requires_payment', sa.Boolean(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', name='servicerisklevel'), nullable=True),
        sa.Column('is_demo', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_service_directory_id'), 'service_directory', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_service_directory_id'), table_name='service_directory')
    op.drop_table('service_directory')
