"""Marketplace directory + x402-style flow + killer/failed demos."""

from tests.conftest import find_service


def test_list_services_seeded(client):
    r = client.get("/api/v1/services")
    assert r.status_code == 200
    services = r.json()
    assert len(services) >= 7
    assert all(s["is_demo"] for s in services)


def test_request_paid_service_returns_payment_required(client, agent_factory):
    service = find_service(client, "Web Search API")
    agent = agent_factory(client, "wallet_mkt_request")
    r = client.post(
        f"/api/v1/services/{service['id']}/request",
        json={"agent_id": agent["id"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "payment_required"
    assert body["http_status_hint"] == 402
    assert body["payment_info"]["amount"] > 0
    # explicit non-compliance note so we never claim real x402 support
    assert "x402_note" in body


def test_killer_demo_completes_and_pays(client, agent_factory):
    agent = agent_factory(client, "wallet_killer_demo")
    r = client.post(
        "/api/v1/services/demo/killer",
        json={"agent_id": agent["id"], "requested_amount": 0.02},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "completed"
    assert body["approved"] is True
    assert body["transaction"]["status"] == "executed"
    assert body["transaction"]["tx_hash"].startswith("mock_")
    assert body["proof"]["simulated"] is True
    # ledger was charged: balance dropped from $100 by $0.02
    after = client.get(f"/api/v1/users/wallet_killer_demo/agents/{agent['id']}").json()
    assert abs(float(after["balance"]) - 99.98) < 0.0001

    # Re-run with the SAME args -> dedupe: same tx, no second payment.
    r2 = client.post(
        "/api/v1/services/demo/killer",
        json={"agent_id": agent["id"], "requested_amount": 0.02},
    )
    body2 = r2.json()
    assert body2["flow"] == "completed"
    assert body2["transaction"]["id"] == body["transaction"]["id"]
    assert body2["transaction"]["status"] == "executed"


def test_failed_demo_blocked(client, agent_factory):
    agent = agent_factory(client, "wallet_failed_demo")
    r = client.post(
        "/api/v1/services/demo/failed",
        json={"agent_id": agent["id"], "requested_amount": 50.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "blocked"
    assert body["transaction"]["status"] == "rejected"
    assert "per-transaction" in (body["reason"] or "")
    # Zero USDC flowed
    agent_after = client.get(
        f"/api/v1/users/wallet_failed_demo/agents/{agent['id']}"
    ).json()
    assert float(agent_after["balance"]) == float(agent["balance"])


def test_pay_endpoint_idempotent_double_submit(client, agent_factory):
    service = find_service(client, "Solana RPC API")
    agent = agent_factory(client, "wallet_double_submit")
    first = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 0.02},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["status"] == "paid"

    second = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 0.02},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["transaction"]["id"] == first_body["transaction"]["id"]
    assert second_body.get("already_processed") is True

    # only one executed row exists for that (agent, service, amount) triple
    txs = client.get("/api/v1/users/wallet_double_submit/transactions").json()
    executed = [t for t in txs if t["status"] == "executed"]
    assert len(executed) == 1


def test_pay_endpoint_blocks_over_limit(client, agent_factory):
    service = find_service(client, "Premium Data API")
    agent = agent_factory(client, "wallet_pay_blocked")
    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 50.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "blocked"
    assert body["transaction"]["status"] == "rejected"


def test_insufficient_balance_never_pays(client, agent_factory):
    service = find_service(client, "Solana RPC API")
    agent = agent_factory(client, "wallet_poor_agent", balance=0.01)
    r = client.post(
        f"/api/v1/services/{service['id']}/payment",
        json={"agent_id": agent["id"], "requested_amount": 1.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["transaction"]["status"] == "failed"
    assert "Insufficient balance" in body["reason"]
    # nothing charged
    agent_after = client.get(
        f"/api/v1/users/wallet_poor_agent/agents/{agent['id']}"
    ).json()
    assert float(agent_after["balance"]) == 0.01