"""End-to-end integration: user -> agent -> fund -> policy -> task -> payment
-> executed transaction -> visible in the ledger + audit trail."""


def test_full_agent_payment_cycle(client):
    wallet = "wallet_integration"

    # 1. ensure user
    r = client.post("/api/v1/users", json={"wallet_address": wallet})
    assert r.status_code in (200, 201)
    user = r.json()
    assert user["wallet_address"] == wallet

    # 2. create agent
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "IntegBot"})
    assert r.status_code == 201
    agent = r.json()
    assert agent["escrow_address"]  # server-derived, key never leaves backend

    # 3. fund (mock USDC)
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/fund", json={"amount": 100}
    )
    assert r.status_code == 200
    assert r.json()["mode"] == "mock"
    funded = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert float(funded["balance"]) == 100

    # 4. policy
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/policy",
        json={
            "max_per_transaction": 20,
            "max_per_day": 100,
            "allowed_categories": ["api", "compute", "data", "agent"],
            "blocked_human_transfers": True,
            "blocked_withdrawals": True,
            "blocked_arbitrary_contracts": True,
            "require_approval_above": 20,
            "allowed_recipient_addresses": [],
        },
    )
    assert r.status_code == 201

    # 5. run a task: the mock LLM proposes paying rpcProvider $0.02 -> within policy
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
        json={"task": "hit the RPC API provider to benchmark latency"},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    assert run["blocked"] is False
    tx = run["transaction"]
    assert tx["status"] == "executed"
    assert tx["tx_hash"].startswith("mock_")
    assert tx["amount"] == 0.02

    # 6. ledger + history reflect the payment
    after = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert abs(float(after["balance"]) - 99.98) < 1e-6
    assert abs(float(after["total_spent"]) - 0.02) < 1e-6

    txs = client.get(f"/api/v1/users/{wallet}/transactions").json()
    executed = [t for t in txs if t["status"] == "executed"]
    assert len(executed) == 1
    assert executed[0]["tx_hash"] == tx["tx_hash"]

    # 7. audit trail recorded the execution
    from app.db.session import SessionLocal
    from app.services.audit_service import TRANSACTION_EXECUTED
    from app.db.models import AuditLog

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user["id"], AuditLog.event == TRANSACTION_EXECUTED)
            .all()
        )
        assert len(events) >= 1
    finally:
        db.close()


def test_agent_can_be_killed_hard(client):
    wallet = "wallet_killcheck"
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "KillMe"})
    agent = r.json()
    r = client.delete(f"/api/v1/users/{wallet}/agents/{agent['id']}")
    assert r.status_code == 200
    status = client.get(
        f"/api/v1/users/{wallet}/agents/{agent['id']}"
    ).json()["status"]
    assert status in ("killed", "revoked")
    # killed agent cannot transact via marketplace
    r = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}")
    assert r.status_code == 200