"""real provider marketplace: providers, service_listings, purchase_intents

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-08

Adds the real "agent buys things" primitives:
  * providers        — wallets that register real, payable service integrations
  * service_listings — payable services a provider advertises (with a params
                       JSON schema the adapter validates)
  * purchase_intents — the full lifecycle of an agent purchase, from quote to
                       verified provider result, linked to its ledger payment.
"""
import sqlalchemy as sa

from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("adapter", sa.String(), nullable=False),
        sa.Column("api_base_url", sa.String(length=512), nullable=False),
        sa.Column("category", sa.Enum("api", "compute", "data", "ai_model", "storage", "other_agent", name="servicecategory"), nullable=True),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("supports", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("pending", "active", "suspended", name="providerstatus"), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_providers_id"), "providers", ["id"], unique=False)
    op.create_index(op.f("ix_providers_name"), "providers", ["name"], unique=True)

    op.create_table(
        "service_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Enum("api", "compute", "data", "ai_model", "storage", "other_agent", name="servicecategory"), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column("requires_payment", sa.Boolean(), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", name="listingstatus"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "name", name="uq_listing_provider_name"),
    )
    op.create_index(op.f("ix_service_listings_id"), "service_listings", ["id"], unique=False)

    op.create_table(
        "purchase_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_run_id", sa.Integer(), sa.ForeignKey("task_runs.id"), nullable=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("service_listings.id"), nullable=False),
        sa.Column("status", sa.Enum("quoting", "pending_approval", "paying", "awaiting_provider", "completed", "failed", "cancelled", name="purchaseintentstatus"), nullable=True),
        sa.Column("request_payload", sa.Text(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("provider_ref", sa.String(length=512), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_intents_id"), "purchase_intents", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_intents_idempotency_key"), "purchase_intents", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_intents_idempotency_key"), table_name="purchase_intents")
    op.drop_index(op.f("ix_purchase_intents_id"), table_name="purchase_intents")
    op.drop_table("purchase_intents")
    op.drop_index(op.f("ix_service_listings_id"), table_name="service_listings")
    op.drop_table("service_listings")
    op.drop_index(op.f("ix_providers_name"), table_name="providers")
    op.drop_index(op.f("ix_providers_id"), table_name="providers")
    op.drop_table("providers")