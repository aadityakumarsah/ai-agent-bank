"""Generic human-approval endpoint + transaction state machine."""

from tests.conftest import find_service


def test_approval_flow_via_generic_endpoint(client, agent_factory):
    wallet = "wallet_approval"
    agent = agent_factory(
        client, wallet, per_tx=100.0, daily=100.0, approval=20.0
    )
    service = find_service(client, "Web Search API")

    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 75.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approval_required"
    assert body["transaction"]["status"] == "approved"
    tx_id = body["transaction"]["id"]

    # Human approves via the generic endpoint -> executes.
    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx_id}/approve")
    assert r.status_code == 200
    body = r.json()
    assert body["approved"] is True
    assert body["executed"] is True
    assert body["transaction"]["status"] == "executed"
    assert body["transaction"]["tx_hash"].startswith("mock_")

    # Approving again is an idempotent no-op, not a payment.
    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx_id}/approve")
    body = r.json()
    assert body["executed"] is True
    assert body["already_processed"] is True

    after = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert float(after["balance"]) == 25.0


def test_approve_cross_user_forbidden(client, agent_factory):
    wallet = "wallet_owner"
    other = "wallet_stranger"
    agent = agent_factory(client, wallet, per_tx=100.0, approval=20.0)
    agent_factory(client, other)  # ensure the stranger user exists
    service = find_service(client, "Web Search API")

    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 75.0},
    )
    tx_id = r.json()["transaction"]["id"]

    r = client.post(f"/api/v1/users/{other}/transactions/{tx_id}/approve")
    assert r.status_code == 404


def test_approve_rejected_transaction_conflict(client, agent_factory):
    wallet = "wallet_conflict"
    agent = agent_factory(client, wallet)
    service = find_service(client, "Premium Data API")
    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 50.0},
    )
    assert r.json()["status"] == "blocked"
    tx_id = r.json()["transaction"]["id"]

    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx_id}/approve")
    assert r.status_code == 409


def test_transaction_state_machine(client, agent_factory):
    wallet = "wallet_states"
    agent = agent_factory(client, wallet)
    service = find_service(client, "Premium Data API")

    # blocked -> rejected
    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 50.0},
    )
    blocked = r.json()["transaction"]
    assert blocked["status"] == "rejected"

    # executed
    cheap = find_service(client, "Solana RPC API")
    r = client.post(
        f"/api/v1/services/{cheap['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 0.02},
    )
    executed = r.json()["transaction"]
    assert executed["status"] == "executed"

    txs = client.get(f"/api/v1/users/{wallet}/transactions").json()
    statuses = {t["status"] for t in txs}
    assert {"rejected", "executed"} <= statuses