"""Status endpoint, request-id middleware, validation errors, structured errors."""


def test_status_reports_demo_mode(client):
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["demo_mode"] is True
    assert body["payment_mode"] == "mock"
    assert body["llm_provider"] == "mock"
    assert "demo_scenarios" in body


def test_request_id_header_present(client):
    r = client.get("/api/v1/status")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) >= 8


def test_unknown_agent_friendly_404(client):
    r = client.post(
        "/api/v1/services/demo/killer",
        json={"agent_id": 999999},
    )
    assert r.status_code == 404
    assert "detail" in r.json()


def test_validation_error_is_clean(client):
    r = client.post(
        "/api/v1/users",
        json={},  # missing wallet_address
    )
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], str)
    assert "errors" in body
    assert "internal" not in body.get("detail", "")


def test_unknown_scenario_friendly_400(client):
    r = client.post("/api/v1/demo/scenarios/nope/run", json={})
    assert r.status_code == 400
    body = r.json()
    assert "error" in body or "code" in body
    assert "Unknown demo scenario" in body["detail"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"