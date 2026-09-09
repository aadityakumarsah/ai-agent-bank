"""DCA plan + execution tests: API surface, scheduler happy path, policy and
balance guards, and idempotency (a cycle must never double-pay)."""

from datetime import datetime, timedelta, timezone

from app.db.models import (
    DcaExecutionStatus,
    DcaStatus,
    TransactionStatus,
    TransactionType,
)
from app.services.dca_service import dca_service

USDC_DEVNET = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"


def _create_plan(client, wallet, agent, amount=5.0, frequency="hourly"):
    r = client.post(
        f"/api/v1/users/{wallet}/dca",
        json={
            "agent_id": agent["id"],
            "token_mint": USDC_DEVNET,
            "token_symbol": "USDC",
            "token_decimals": 6,
            "amount_per_cycle": amount,
            "frequency": frequency,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _force_due(db, plan):
    plan = dca_service.get_plan(db, plan["id"])
    plan.next_run_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    db.refresh(plan)
    return plan


def test_create_plan_api(client, agent_factory):
    wallet = "DCAWalletTestRecipient"
    agent = agent_factory(client, wallet)
    plan = _create_plan(client, wallet, agent)

    assert plan["status"] == "active"
    assert plan["agent_id"] == agent["id"]
    assert plan["frequency"] == "hourly"
    assert plan["amount_per_cycle"] == 5.0
    assert plan["runs_completed"] == 0
    assert plan["next_run_at"] is not None

    r = client.get(f"/api/v1/users/{wallet}/dca")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(
        f"/api/v1/users/{wallet}/dca/{plan['id']}/status",
        json={"status": "paused"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paused"

    r = client.patch(
        f"/api/v1/users/{wallet}/dca/{plan['id']}/status",
        json={"status": "active"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    r = client.get(f"/api/v1/users/{wallet}/dca/999999")
    assert r.status_code == 404

    r = client.post(
        f"/api/v1/users/{wallet}/dca",
        json={
            "agent_id": agent["id"],
            "token_mint": USDC_DEVNET,
            "amount_per_cycle": 5,
            "frequency": "minutely",
        },
    )
    assert r.status_code == 422

    # ownership guard: another wallet cannot read this plan
    other = "AnotherWalletDCA"
    client.post("/api/v1/users", json={"wallet_address": other})
    r = client.get(f"/api/v1/users/{other}/dca/{plan['id']}")
    assert r.status_code == 403


def test_scheduler_happy_path(client, agent_factory, db):
    wallet = "DCAHappyPath"
    agent = agent_factory(client, wallet)
    plan = _create_plan(client, wallet, agent, amount=5.0)
    plan = _force_due(db, plan)

    summary = dca_service.execute_due_plans(db)
    assert summary["executed"] == 1, summary

    plan = dca_service.get_plan(db, plan.id)
    assert plan.runs_completed == 1
    assert float(plan.total_invested) == 5.0
    assert float(plan.agent.balance) == 95.0  # 100 funded - 5 invested
    assert plan.last_run_at is not None
    assert plan.next_run_at is not None

    # swap transaction recorded in the ledger
    tx = plan.agent.transactions[0]
    assert tx.transaction_type == TransactionType.swap
    assert tx.status == TransactionStatus.executed
    assert tx.idempotency_key == f"dca:{plan.id}:1"
    assert tx.tx_hash is not None

    # execution record
    executions = dca_service.list_executions(db, plan.id)
    assert len(executions) == 1
    ex = executions[0]
    assert ex.status == DcaExecutionStatus.completed
    assert float(ex.amount) == 5.0
    assert float(ex.out_amount) == 5.0
    assert ex.tx_signature is not None

    # audits
    from app.db.models import AuditLog
    events = db.query(AuditLog).filter(AuditLog.agent_id == agent["id"]).all()
    assert any(a.event == "dca_executed" for a in events)


def test_scheduler_is_idempotent(client, agent_factory, db):
    wallet = "DCAIdempotent"
    agent = agent_factory(client, wallet)
    plan = _create_plan(client, wallet, agent, amount=5.0)
    plan = _force_due(db, plan)

    first = dca_service.execute_due_plans(db)
    assert first["executed"] == 1

    balance_after_first = dca_service.get_plan(db, plan.id).agent.balance
    n_tx = len(dca_service.get_plan(db, plan.id).agent.transactions)

    second = dca_service.execute_due_plans(db)
    assert second["executed"] == 0, second

    plan = dca_service.get_plan(db, plan.id)
    assert plan.runs_completed == 1
    assert plan.agent.balance == balance_after_first  # no double debit
    assert len(plan.agent.transactions) == n_tx  # no duplicate swap tx


def test_insufficient_balance_skips(client, agent_factory, db):
    wallet = "DCABroke"
    agent = agent_factory(client, wallet, balance=10.0)
    plan = _create_plan(client, wallet, agent, amount=50.0)
    plan = _force_due(db, plan)

    summary = dca_service.execute_due_plans(db)
    assert summary["skipped"] == 1, summary

    plan = dca_service.get_plan(db, plan.id)
    assert plan.runs_completed == 0
    assert float(plan.agent.balance) == 10.0  # untouched
    assert float(plan.total_invested) == 0.0

    ex = dca_service.list_executions(db, plan.id)[0]
    assert ex.status == DcaExecutionStatus.skipped
    assert "Insufficient balance" in (ex.error or "")


def test_policy_caps_block(client, agent_factory, db):
    wallet = "DCACapped"
    # per_tx default 20, approval default 20 -> an amount of 30 breaks the cap.
    agent = agent_factory(client, wallet, per_tx=20.0, approval=20.0, balance=100.0)
    plan = _create_plan(client, wallet, agent, amount=30.0)
    plan = _force_due(db, plan)

    summary = dca_service.execute_due_plans(db)
    assert summary["failed"] == 1, summary

    plan = dca_service.get_plan(db, plan.id)
    assert plan.runs_completed == 0
    assert float(plan.agent.balance) == 100.0

    ex = dca_service.list_executions(db, plan.id)[0]
    assert ex.status == DcaExecutionStatus.failed
    assert "per-transaction cap" in (ex.error or "")


def test_daily_spend_cap_blocks(client, agent_factory, db):
    wallet = "DCADailyCap"
    agent = agent_factory(client, wallet, per_tx=50.0, approval=50.0, daily=15.0, balance=100.0)
    plan = _create_plan(client, wallet, agent, amount=10.0)
    plan = _force_due(db, plan)

    summary = dca_service.execute_due_plans(db)
    assert summary["executed"] == 1, summary

    # second due cycle hits the daily cap of 15 (10 + 10 > 15)
    plan = dca_service.get_plan(db, plan.id)
    plan.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    summary = dca_service.execute_due_plans(db)
    assert summary["failed"] == 1, summary
    plan = dca_service.get_plan(db, plan.id)
    assert plan.runs_completed == 1
    assert float(plan.agent.balance) == 90.0  # only the first cycle spent


def test_paused_plan_not_scheduled(client, agent_factory, db):
    wallet = "DCAPaused"
    agent = agent_factory(client, wallet)
    plan = _create_plan(client, wallet, agent, amount=5.0)
    r = client.patch(
        f"/api/v1/users/{wallet}/dca/{plan['id']}/status",
        json={"status": "paused"},
    )
    assert r.status_code == 200

    plan = _force_due(db, plan)
    plan.status = DcaStatus.paused
    db.commit()

    summary = dca_service.execute_due_plans(db)
    assert summary["executed"] == 0 and summary["plans_checked"] == 0, summary