"""dollar cost averaging: dca_plans, dca_executions, swap tx type

Revision ID: c9d8e7f6a0b1
Revises: b3c4d5e6f7a8
Create Date: 2026-09-08

Adds the recurring "agent buys a token" primitives:
  * dca_plans      — a plan to periodically spend a fixed USDC amount from an
                     agent's balance to buy a token via Jupiter.
  * dca_executions — one scheduled trade attempted by a plan (due/executing/
                     completed/failed/skipped), linked to its ledger payment.
  * transactiontype gains the 'swap' value for DCA trades.
"""
import sqlalchemy as sa

from alembic import op

revision = "c9d8e7f6a0b1"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def _add_enum_value_if_postgres(op_, enum_name: str, value: str) -> None:
    """Add a value to a native Postgres enum, ignoring it on SQLite.

    Postgres < 12 does not allow ALTER TYPE ... ADD VALUE inside a transaction
    block, so it is executed with its own connection (autocommit).
    """
    import sqlalchemy as sa
    from sqlalchemy import inspect

    bind = op_.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    enum_exists = any(
        e["name"] == enum_name for e in inspector.get_enums()
    )
    if not enum_exists:
        return
    conn = bind.connect()
    try:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_enum WHERE enumlabel = :v "
                "AND enumtypid = (SELECT oid FROM pg_type WHERE typname = :t)"
            ),
            {"v": value, "t": enum_name},
        )
        if result.scalar() is None:
            conn.execute(
                sa.text(f'ALTER TYPE {enum_name} ADD VALUE \'{value}\'')
            )
    finally:
        conn.close()


def upgrade() -> None:
    _add_enum_value_if_postgres(op, "transactiontype", "swap")

    op.create_table(
        "dca_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_mint", sa.String(), nullable=False),
        sa.Column("token_symbol", sa.String(), nullable=True),
        sa.Column("token_decimals", sa.Integer(), nullable=True),
        sa.Column("amount_per_cycle", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("frequency", sa.Enum("hourly", "daily", "weekly", name="dcafrequency"), nullable=False),
        sa.Column("status", sa.Enum("active", "paused", "completed", "cancelled", name="dcastatus"), nullable=True),
        sa.Column("runs_completed", sa.Integer(), nullable=True),
        sa.Column("total_invested", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dca_plans_id"), "dca_plans", ["id"], unique=False)

    op.create_table(
        "dca_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("dca_plans.id"), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Enum("due", "executing", "completed", "failed", "skipped", name="dcaexecutionstatus"), nullable=True),
        sa.Column("amount", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("out_amount", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("out_unit", sa.String(length=24), nullable=True),
        sa.Column("token_mint", sa.String(), nullable=True),
        sa.Column("token_symbol", sa.String(), nullable=True),
        sa.Column("quote_price", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("tx_signature", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dca_executions_id"), "dca_executions", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dca_executions_id"), table_name="dca_executions")
    op.drop_table("dca_executions")
    op.drop_index(op.f("ix_dca_plans_id"), table_name="dca_plans")
    op.drop_table("dca_plans")