import os
import tempfile

# Environment must be configured BEFORE any app module is imported so the
# settings singleton + engine pick up a throwaway sqlite DB.
os.environ.setdefault("DEMO_MODE", "true")
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='aibank-test-')}/aibank.db"
os.environ["USE_REAL_PAYMENT"] = "false"
os.environ.pop("SOLANA_RPC_URL", None)
os.environ.pop("SOLANA_PRIVATE_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GOOGLE_AI_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

pytest_plugins = []


@pytest.fixture()
def client():
    """TestClient as a context manager so startup (init_db + seeding) runs."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    from app.db.session import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


def make_agent(
    client: TestClient,
    wallet: str,
    name: str = "TestBot",
    balance: float = 100.0,
    per_tx: float = 20.0,
    daily: float = 100.0,
    approval: float = 20.0,
    categories=(("api", "compute", "data", "agent")),
):
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": name})
    assert r.status_code == 201, r.text
    agent = r.json()
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/fund",
        json={"amount": balance},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/policy",
        json={
            "max_per_transaction": per_tx,
            "max_per_day": daily,
            "allowed_categories": list(categories),
            "blocked_human_transfers": True,
            "blocked_withdrawals": True,
            "blocked_arbitrary_contracts": True,
            "require_approval_above": approval,
            "allowed_recipient_addresses": [],
        },
    )
    assert r.status_code == 201, r.text
    return client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()


@pytest.fixture()
def agent_factory():
    return make_agent


def find_service(client: TestClient, name: str) -> dict:
    services = client.get("/api/v1/services").json()
    for s in services:
        if s["name"] == name:
            return s
    raise AssertionError(f"service {name} not found in {[s['name'] for s in services]}")