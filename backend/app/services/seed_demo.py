"""
Demo data seeding for AI Agent Bank (DEMO_MODE only).

When the app boots in demo mode it provisions a recognizable demo user and three
agents with realistic, clearly-labelled simulated history so the dashboard,
activity feed and approvals pages tell a coherent story the moment you connect
with the demo wallet.

Every transaction here carries a ``mock_`` hash (never mistaken for an on-chain
signature) or no hash at all (blocked / awaiting approval), and is gated so this
never runs against a real production database: ``DEMO_MODE=false`` skips it, and
once the seed has run it never rewrites the data (idempotent).
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Agent,
    AgentStatus,
    Policy,
    PolicyCategory,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.services.audit_service import AGENT_FUNDED, audit_service
from app.services.demo_scenarios import DEMO_WALLET

logger = logging.getLogger(__name__)

DEMO_AGENT_NAMES = ("ResearchBot", "ComputeBot", "DataBot")


def seed_demo_data(db: Session) -> int:
    """Provision the demo user + agents + simulated history. Returns 0 if skipped
    (demo mode off or already seeded), else the number of agents created."""
    if not settings.DEMO_MODE:
        return 0

    user = db.query(User).filter(User.wallet_address == DEMO_WALLET).first()
    if user is None:
        user = User(wallet_address=DEMO_WALLET)
        db.add(user)
        db.flush()

    existing = (
        db.query(Agent)
        .filter(
            Agent.user_id == user.id,
            Agent.name.in_(list(DEMO_AGENT_NAMES)),
        )
        .first()
    )
    if existing is not None:
        return 0  # already seeded — never rewrite demo history

    now = datetime.now(timezone.utc)
    created = 0

    def policy_for(agent_id: int, per_tx: str, daily: str, monthly: str, approval: str) -> None:
        db.add(
            Policy(
                agent_id=agent_id,
                user_id=user.id,
                max_per_transaction=Decimal(per_tx),
                max_per_day=Decimal(daily),
                max_per_month=Decimal(monthly),
                allowed_categories='["api", "compute", "data", "agent"]',
                blocked_human_transfers=True,
                blocked_withdrawals=True,
                blocked_arbitrary_contracts=True,
                require_approval_above=Decimal(approval),
                allowed_recipient_addresses="[]",
            )
        )

    def record_tx(
        agent_id: int,
        amount: str,
        recipient: str,
        recipient_name: str,
        category: PolicyCategory,
        description: str,
        status: TransactionStatus,
        *,
        idempotency_key: str,
        rejection_reason: str | None = None,
        tx_hash: str | None = None,
    ) -> None:
        db.add(
            Transaction(
                agent_id=agent_id,
                user_id=user.id,
                amount=Decimal(amount),
                currency="USDC",
                transaction_type=TransactionType.payment,
                status=status,
                recipient_address=recipient,
                recipient_name=recipient_name,
                category=category,
                description=description,
                idempotency_key=idempotency_key,
                rejection_reason=rejection_reason,
                tx_hash=tx_hash,
                executed_at=now if status == TransactionStatus.executed else None,
            )
        )

    # --- ResearchBot: the $20 / $100 / $1,000 / approval-$20 policy from the
    # demo story, with a realistic spend trail (RPC test, search, a paused
    # approval and one blocked attack).
    research = Agent(
        name="ResearchBot",
        description=(
            "Autonomous research assistant. Discovers and tests Solana RPC "
            "providers and pays for API access within strict policy limits."
        ),
        user_id=user.id,
        balance=Decimal("499.93"),
        total_spent=Decimal("0.07"),
        status=AgentStatus.active,
    )
    db.add(research)
    db.flush()
    policy_for(research.id, "20", "100", "1000", "20")
    record_tx(
        research.id, "0.02", "rpcProvider", "RPC Compute Provider", PolicyCategory.compute,
        "Purchase Solana RPC access to test their API", TransactionStatus.executed,
        idempotency_key="seed:rpc-test", tx_hash="mock_seed_rpc_q1w2e3",
    )
    record_tx(
        research.id, "0.05", "apiProvider", "Web Search API", PolicyCategory.api,
        "Web search for RPC provider comparison", TransactionStatus.executed,
        idempotency_key="seed:search", tx_hash="mock_seed_search_k2l3m4",
    )
    record_tx(
        research.id, "25", "dataProvider", "Data Provider", PolicyCategory.data,
        "Premium market data subscription — awaiting human approval",
        TransactionStatus.approved, idempotency_key="seed:data-approval",
    )
    record_tx(
        research.id, "300", "unknownWallet", "Unknown Human Wallet", PolicyCategory.api,
        "Transfer $300 to an unknown wallet", TransactionStatus.rejected,
        idempotency_key="seed:attack",
        rejection_reason=(
            "Transaction exceeds per-transaction limit. Requested $300 but allowed $20."
        ),
    )
    audit_service.log(
        db, user_id=user.id, agent_id=research.id, event=AGENT_FUNDED, actor="human",
        detail={"amount": 500.0, "mode": "mock", "simulated": True},
    )
    created += 1

    # --- ComputeBot: batch-compute runner, heavier allowances.
    compute = Agent(
        name="ComputeBot",
        description=(
            "Batch-compute runner. Rents ephemeral compute for heavy jobs and "
            "pays providers from its own policy-bound escrow."
        ),
        user_id=user.id,
        balance=Decimal("119.60"),
        total_spent=Decimal("0.40"),
        status=AgentStatus.active,
    )
    db.add(compute)
    db.flush()
    policy_for(compute.id, "50", "200", "2000", "100")
    record_tx(
        compute.id, "0.40", "computeProvider", "Compute Provider", PolicyCategory.compute,
        "Rent compute for batch job", TransactionStatus.executed,
        idempotency_key="seed:compute", tx_hash="mock_seed_compute_z3x4c5",
    )
    created += 1

    # --- DataBot: market-data analyst, high-category spend within approval gates.
    data = Agent(
        name="DataBot",
        description=(
            "Market data analyst. Buys premium feeds with human approval above "
            "its $50 threshold."
        ),
        user_id=user.id,
        balance=Decimal("200.00"),
        total_spent=Decimal("50.00"),
        status=AgentStatus.active,
    )
    db.add(data)
    db.flush()
    policy_for(data.id, "100", "250", "500", "50")
    record_tx(
        data.id, "50", "dataProvider", "Data Provider", PolicyCategory.data,
        "Premium market data snapshot", TransactionStatus.executed,
        idempotency_key="seed:data-snapshot", tx_hash="mock_seed_data_7x8y9z",
    )
    created += 1

    db.commit()
    logger.info("seeded demo data: user=%s agents=%d", DEMO_WALLET, created)
    return created