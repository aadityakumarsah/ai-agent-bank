"""add audit_logs, agent violation_count, task_runs memory, revoked enum

Revision ID: a1b2c3d4e5f6
Revises: d0e5f2a3b8c1
Create Date: 2026-09-08

Resolves the model/migration drift that would crash a freshly migrated
production Postgres at runtime (e.g. every audit write hitting a missing
``audit_logs`` table).
"""
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "d0e5f2a3b8c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. agents.violation_count (deterministic risk input for the risk engine)
    try:
        op.add_column("agents", sa.Column("violation_count", sa.Integer(), nullable=True))
    except Exception:
        pass  # already present (e.g. created via create_all in dev/tests)

    # 2. task_runs.memory (JSON agent memory)
    try:
        op.add_column("task_runs", sa.Column("memory", sa.Text(), nullable=True))
    except Exception:
        pass

    # 3. audit_logs — the big one; append-only financial/control trail.
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(32), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_event"), "audit_logs", ["event"], unique=False)

    # 4. Extend the AgentStatus Postgres enum to include 'revoked'.
    if bind.dialect.name != "sqlite":
        try:
            op.execute("ALTER TYPE agentstatus ADD VALUE IF NOT EXISTS 'revoked'")
        except Exception:
            pass


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_event"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    try:
        op.drop_column("task_runs", "memory")
    except Exception:
        pass
    try:
        op.drop_column("agents", "violation_count")
    except Exception:
        pass
