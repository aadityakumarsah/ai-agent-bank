"""Part 10: approval-required task flow, human reject, monthly limit and the
execution-time daily/monthly re-check guard."""

from decimal import Decimal

from app.db.models import (
    Agent,
    Policy,
    PolicyCategory,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.services.payment_flow import attempt_execution
from app.services.policy_engine import PolicyEngine


_counter = [0]


def _seed_agent(db, max_per_tx=20, max_per_day=100, max_per_month=None,
                categories="[\"api\",\"compute\",\"data\",\"agent\"]",
                require_above=None):
    _counter[0] += 1
    user = User(wallet_address=f"wallet_part10_{_counter[0]}")
    db.add(user)
    db.flush()
    agent = Agent(name=f"Part10Bot{_counter[0]}", user_id=user.id, balance=Decimal("100"))
    db.add(agent)
    db.flush()
    policy = Policy(
        agent_id=agent.id,
        user_id=user.id,
        max_per_transaction=Decimal(str(max_per_tx)),
        max_per_day=Decimal(str(max_per_day)),
        max_per_month=Decimal(str(max_per_month)) if max_per_month is not None else None,
        allowed_categories=categories,
        blocked_human_transfers=True,
        blocked_withdrawals=True,
        blocked_arbitrary_contracts=True,
        require_approval_above=Decimal(str(require_above)) if require_above is not None else None,
        allowed_recipient_addresses="[]",
    )
    db.add(policy)
    db.commit()
    db.refresh(agent)
    return agent


def _pre_spend(db, agent, amount):
    db.add(Transaction(
        agent_id=agent.id, user_id=agent.user_id, amount=Decimal(str(amount)),
        transaction_type=TransactionType.payment, status=TransactionStatus.executed,
        recipient_address="apiProvider", recipient_name="API Provider",
        category=PolicyCategory.api,
    ))
    db.commit()


def test_task_approval_required_then_reject(client):
    wallet = "wallet_p10_approve"
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "ResearchBot"})
    agent = r.json()
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/fund", json={"amount": 100}
    )
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/policy",
        json={
            "max_per_transaction": 100,
            "max_per_day": 100,
            "allowed_categories": ["api", "compute", "data", "agent"],
            "blocked_human_transfers": True,
            "blocked_withdrawals": True,
            "blocked_arbitrary_contracts": True,
            "require_approval_above": 20,
            "allowed_recipient_addresses": [],
        },
    )

    # Task -> mock LLM proposes a $75 API purchase -> above the $20 threshold
    # -> the payment pauses WITHOUT moving money.
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
        json={"task": "Buy a $75 deep-research report from the Web Search API."},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "waiting_for_approval"
    assert run["decision"]["requires_approval"] is True
    tx = run["transaction"]
    assert tx["status"] == "approved"
    assert tx["amount"] == 75.0
    assert tx["tx_hash"] is None  # no money moved yet

    # Human rejects -> marked rejected, balance untouched.
    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx['id']}/reject")
    assert r.status_code == 200
    body = r.json()
    assert body["rejected"] is True
    assert body["transaction"]["status"] == "rejected"

    after = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert float(after["balance"]) == 100.0


def test_task_approval_then_human_approve(client):
    wallet = "wallet_p10_human"
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "ResearchBot"})
    agent = r.json()
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/fund", json={"amount": 100}
    )
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/policy",
        json={
            "max_per_transaction": 100,
            "max_per_day": 100,
            "allowed_categories": ["api", "compute", "data", "agent"],
            "blocked_human_transfers": True,
            "blocked_withdrawals": True,
            "blocked_arbitrary_contracts": True,
            "require_approval_above": 20,
            "allowed_recipient_addresses": [],
        },
    )

    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
        json={"task": "Buy a $75 deep-research report from the Web Search API."},
    )
    tx = r.json()["transaction"]

    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx['id']}/approve")
    assert r.status_code == 200
    assert r.json()["executed"] is True
    assert r.json()["transaction"]["status"] == "executed"

    after = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert abs(float(after["balance"]) - 25.0) < 1e-6


def test_reject_executed_conflict(client):
    wallet = "wallet_p10_rejectexec"
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "Bot"})
    agent = r.json()
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/fund", json={"amount": 100}
    )
    client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/policy",
        json={
            "max_per_transaction": 100,
            "max_per_day": 100,
            "allowed_categories": ["api"],
            "require_approval_above": None,
            "allowed_recipient_addresses": [],
        },
    )
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
        json={"task": "Buy a $75 deep-research report from the Web Search API."},
    )
    assert r.json()["status"] == "completed"
    tx = r.json()["transaction"]
    assert tx["status"] == "executed"

    # An executed payment can never be rejected.
    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx['id']}/reject")
    assert r.status_code == 409


def test_monthly_limit_blocks(db):
    agent = _seed_agent(db, max_per_tx=100, max_per_day=1000, max_per_month=10)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 60, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is False
    assert "Monthly limit" in res.reason


def test_monthly_limit_counts_history(db):
    agent = _seed_agent(db, max_per_tx=100, max_per_day=1000, max_per_month=10)
    _pre_spend(db, agent, 7)
    res = PolicyEngine().evaluate_transaction(
        agent, agent.policies, 5, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is False
    assert "Monthly limit" in res.reason

    agent2 = _seed_agent(db, max_per_tx=100, max_per_day=1000, max_per_month=10)
    _pre_spend(db, agent2, 3)
    res = PolicyEngine().evaluate_transaction(
        agent2, agent2.policies, 5, "api", "apiProvider", "API Provider", db
    )
    assert res.allowed is True


def test_execution_time_daily_recheck_blocks(db):
    """The execution-time guard re-verifies daily spend even if a separate
    evaluation passed earlier — closes a concurrent-approval race."""
    agent = _seed_agent(db, max_per_tx=100, max_per_day=10)
    _pre_spend(db, agent, 8)

    tx = Transaction(
        agent_id=agent.id, user_id=agent.user_id, amount=Decimal("5"),
        transaction_type=TransactionType.payment, status=TransactionStatus.pending,
        recipient_address="apiProvider", recipient_name="API Provider",
        category=PolicyCategory.api,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    result = attempt_execution(db, agent, tx, to_name="API Provider")
    assert result["executed"] is False
    assert "Daily limit exceeded at execution time" in result["reason"]
    assert tx.status == TransactionStatus.failed


def test_execution_time_within_daily_recheck_succeeds(db):
    agent = _seed_agent(db, max_per_tx=100, max_per_day=10)
    _pre_spend(db, agent, 2)

    tx = Transaction(
        agent_id=agent.id, user_id=agent.user_id, amount=Decimal("5"),
        transaction_type=TransactionType.payment, status=TransactionStatus.pending,
        recipient_address="rpcProvider", recipient_name="RPC Compute Provider",
        category=PolicyCategory.compute,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    result = attempt_execution(db, agent, tx, to_name="RPC Compute Provider")
    assert result["executed"] is True
    assert tx.status == TransactionStatus.executed
    assert tx.tx_hash.startswith("mock_")


DEMO_WALLET = "DemoWallet11111111111111111111111111111111"


def test_demo_data_seeded(client):
    """DEMO_MODE boot seeds a coherent demo user + agents + labelled history."""
    agents = client.get(f"/api/v1/users/{DEMO_WALLET}/agents").json()
    names = {a["name"] for a in agents}
    assert {"ResearchBot", "ComputeBot", "DataBot"} <= names

    compute = next(a for a in agents if a["name"] == "ComputeBot")
    assert compute["policies"]["max_per_month"] == 2000.0
    assert compute["policies"]["max_per_transaction"] == 50.0

    # Seeded executed history is unambiguous demo data: always mock hashes.
    txs = client.get(f"/api/v1/users/{DEMO_WALLET}/transactions").json()
    executed = [t for t in txs if t["status"] == "executed"]
    assert executed
    assert all(t["tx_hash"].startswith("mock_") for t in executed)


def test_demo_seed_is_idempotent(client):
    before = client.get(f"/api/v1/users/{DEMO_WALLET}/agents").json()
    from app.db.session import SessionLocal
    from app.services.seed_demo import seed_demo_data

    db = SessionLocal()
    try:
        assert seed_demo_data(db) == 0
    finally:
        db.close()
    after = client.get(f"/api/v1/users/{DEMO_WALLET}/agents").json()
    assert len(before) == len(after)