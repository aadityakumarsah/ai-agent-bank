"""Deterministic policy engine behaviours."""
from decimal import Decimal
from uuid import uuid4

from app.db.models import User, Agent, Policy, PolicyCategory, Transaction, TransactionStatus, TransactionType
from app.services.policy_engine import PolicyEngine


def _seed_agent(db, max_per_tx=20, max_per_day=100, categories="[\"api\",\"compute\"]",
                require_above=None, allowed_recipients="[]"):
    wallet = f"wallet_policy_{uuid4().hex[:10]}"
    user = User(wallet_address=wallet)
    db.add(user)
    db.flush()
    agent = Agent(name="PolicyUnit", user_id=user.id, balance=Decimal("100"))
    db.add(agent)
    db.flush()
    policy = Policy(
        agent_id=agent.id,
        user_id=user.id,
        max_per_transaction=Decimal(str(max_per_tx)),
        max_per_day=Decimal(str(max_per_day)),
        allowed_categories=categories,
        blocked_human_transfers=True,
        blocked_withdrawals=True,
        blocked_arbitrary_contracts=True,
        require_approval_above=Decimal(str(require_above)) if require_above is not None else None,
        allowed_recipient_addresses=allowed_recipients,
    )
    db.add(policy)
    db.commit()
    db.refresh(agent)
    return agent


def test_per_transaction_limit(db):
    agent = _seed_agent(db)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 50, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is False
    assert any(c["name"] == "Per-transaction limit" and not c["passed"] for c in res.checks)


def test_daily_limit(db):
    agent = _seed_agent(db, max_per_tx=100, max_per_day=100)
    # pre-spend $90 today
    db.add(Transaction(
        agent_id=agent.id, user_id=agent.user_id, amount=Decimal("90"),
        transaction_type=TransactionType.payment, status=TransactionStatus.executed,
        recipient_address="apiProvider", recipient_name="API",
        category=PolicyCategory.api,
    ))
    db.commit()
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 50, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is False
    assert "Daily limit" in res.reason


def test_category_gate(db):
    agent = _seed_agent(db)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 2, "data", "dataProvider", "Data Provider", db
    )
    assert res.allowed is False
    assert "not allowed" in res.reason


def test_human_transfer_blocked(db):
    agent = _seed_agent(db)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 15, "api", "unknown_human_abc", "Human wallet", db
    )
    assert res.allowed is False
    assert "Human transfers are disabled" in res.reason


def test_approval_threshold(db):
    agent = _seed_agent(db, max_per_tx=100, require_above=20)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 75, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is False
    assert res.requires_approval is True
    assert "requires human approval" in res.reason.lower()


def test_trusted_provider_auto_allowed(db):
    agent = _seed_agent(db)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 0.02, "compute", "rpcProvider", "RPC Provider", db
    )
    assert res.allowed is True
    assert any(c["name"] == "Recipient trusted" and c["passed"] for c in res.checks)