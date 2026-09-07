"""One-click demo scenarios: every control demonstrated, idempotent + audited."""


def _run(client, scenario, client_request_id=None):
    return client.post(
        f"/api/v1/demo/scenarios/{scenario}/run",
        json={"client_request_id": client_request_id},
    )


def _approve(client, scenario, client_request_id=None):
    return client.post(
        f"/api/v1/demo/scenarios/{scenario}/approve",
        json={"client_request_id": client_request_id},
    )


def test_scenarios_listed(client):
    r = client.get("/api/v1/demo/scenarios")
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["scenarios"]}
    assert {"success", "blocked-spend", "blocked-transfer", "approval"} <= ids


def test_success_scenario_auto_approved_and_pays(client):
    r = _run(client, "success", "s1")
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "completed"
    assert body["approved"] is True
    assert body["transaction"]["status"] == "executed"
    assert body["transaction"]["amount"] == 0.02
    assert body["transaction"]["tx_hash"].startswith("mock_")
    assert body["proof"]["simulated"] is True
    assert body["agent"]["balance"] == 99.98


def test_success_scenario_is_idempotent_on_double_click(client):
    rid = "s1-dup"
    first = _run(client, "success", rid).json()
    second = _run(client, "success", rid).json()
    assert second["transaction"]["id"] == first["transaction"]["id"]
    assert second["flow"] == "completed"


def test_blocked_spend_scenario(client):
    r = _run(client, "blocked-spend", "b1")
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "blocked"
    assert body["transaction"]["status"] == "rejected"
    assert "per-transaction" in (body["reason"] or "")
    assert body["agent"]["balance"] == 100  # nothing moved


def test_blocked_transfer_scenario(client):
    r = _run(client, "blocked-transfer", "b2")
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "blocked"
    assert body["transaction"]["status"] == "rejected"
    low = (body["reason"] or "").lower()
    assert "human" in low or "untrusted" in low


def test_approval_scenario_pauses_until_human_approves(client):
    rid = "a1"
    r = _run(client, "approval", rid)
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "approval_required"
    assert body["transaction"]["status"] == "approved"
    assert body["can_approve"] is True
    assert body["transaction"]["tx_hash"] is None

    # Approve it as the human -> executes exactly once, idempotently.
    r = _approve(client, "approval", rid)
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "completed"
    assert body["transaction"]["status"] == "executed"
    assert body["transaction"]["amount"] == 75.0
    tx_id = body["transaction"]["id"]
    assert body["agent"]["balance"] == 25.0

    r = _approve(client, "approval", rid)
    second = r.json()
    assert second["transaction"]["id"] == tx_id
    assert second["transaction"]["status"] == "executed"


def test_approve_before_run_is_clean_error(client):
    r = _approve(client, "approval", "never-run")
    assert r.status_code == 400
    body = r.json()
    assert "not been run" in body["detail"] or "Run the scenario" in body["detail"]


def test_each_run_is_fresh_and_repeatable(client):
    # A second "success" run with a new request-id spends exactly 0.02 again
    # after the deterministic reset to $100.
    r = _run(client, "success", "s-repeat")
    assert r.status_code == 200
    assert r.json()["agent"]["balance"] == 99.98


def test_failed_execution_labels_everything_mock(client):
    r = _run(client, "success", "s-label")
    body = r.json()
    proof = body["proof"]
    assert proof["mode"] == "mock"
    assert proof["simulated"] is True
    assert body["transaction"]["tx_hash"].startswith("mock_")