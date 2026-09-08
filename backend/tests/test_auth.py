"""Tests for wallet-ownership auth, JWT issuance, and production guardrails."""

import hashlib
import pytest
from fastapi.testclient import TestClient


def _make_wallet(tag: str):
    """Deterministic real keypair for a test, returning (pubkey_b58, messaging)."""
    from solders.keypair import Keypair

    seed = hashlib.sha256(tag.encode()).digest()
    kp = Keypair.from_seed(seed)
    return str(kp.pubkey()), kp


def _sign_message(kp, message: str) -> str:

    sig = kp.sign_message(message.encode("utf-8"))
    return str(sig)


def test_nonce_flow_roundtrip(client: TestClient):
    wallet, _ = _make_wallet("nonce-roundtrip")
    r = client.post("/api/v1/auth/nonce", json={"wallet_address": wallet})
    assert r.status_code == 200
    body = r.json()
    assert body["wallet_address"] == wallet
    assert body["nonce"]
    assert "Sign this message to authenticate" in body["message"]
    assert "Nonce: " in body["message"]


def test_verify_issues_jwt_for_valid_signature(client: TestClient):
    wallet, kp = _make_wallet("verify-valid")
    nonce = client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
    sig = _sign_message(kp, nonce["message"])
    r = client.post(
        "/api/v1/auth/verify",
        json={
            "wallet_address": wallet,
            "message": nonce["message"],
            "signature": sig,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["wallet_address"] == wallet
    assert body["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["wallet_address"] == wallet


def test_verify_rejects_wrong_signature(client: TestClient):
    wallet, kp = _make_wallet("verify-wrong")
    _, other_kp = _make_wallet("verify-wrong-other")
    nonce = client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
    # Signed by a *different* wallet's keypair -> must be rejected.
    bad_sig = _sign_message(other_kp, nonce["message"])

    r = client.post(
        "/api/v1/auth/verify",
        json={"wallet_address": wallet, "message": nonce["message"], "signature": bad_sig},
    )
    assert r.status_code == 401


def test_verify_rejects_stale_or_replayed_nonce(client: TestClient):
    wallet, kp = _make_wallet("verify-stale")
    nonce = client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
    sig = _sign_message(kp, nonce["message"])
    # Tamper with the message (drop the Nonce line) -> 400.
    bad_message = nonce["message"].replace("Nonce: ", "Nounce: ")
    r = client.post(
        "/api/v1/auth/verify",
        json={"wallet_address": wallet, "message": bad_message, "signature": sig},
    )
    assert r.status_code in (400, 401)


def test_me_requires_token(client: TestClient):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_readiness_ok(client: TestClient):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


class TestRequireAuthMode:
    """When REQUIRE_AUTH=true, wallet-scoped routes reject unauthenticated or
    mismatched-wallet calls but accept a valid Bearer for the right wallet."""

    @pytest.fixture()
    def auth_client(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", True, raising=False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
        yield client
        monkeypatch.setattr(settings, "REQUIRE_AUTH", False, raising=False)

    def test_protected_route_requires_token(self, auth_client):
        r = auth_client.get("/api/v1/users/SomeWallet")
        assert r.status_code == 401

    def test_protected_route_accepts_token_for_own_wallet(self, auth_client):
        wallet, kp = _make_wallet("auth-mode-wallet")
        nonce = auth_client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
        sig = _sign_message(kp, nonce["message"])
        tok = auth_client.post(
            "/api/v1/auth/verify",
            json={"wallet_address": wallet, "message": nonce["message"], "signature": sig},
        ).json()["access_token"]
        r = auth_client.get(f"/api/v1/users/{wallet}/agents", headers={"Authorization": f"Bearer {tok}"})
        # verify() creates the user, so /{wallet} exists and agents list is 200.
        assert r.status_code == 200

    def test_mismatched_wallet_rejected(self, auth_client):
        wallet, kp = _make_wallet("auth-mode-owner")
        other_wallet, _ = _make_wallet("auth-mode-other")
        nonce = auth_client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
        sig = _sign_message(kp, nonce["message"])
        tok = auth_client.post(
            "/api/v1/auth/verify",
            json={"wallet_address": wallet, "message": nonce["message"], "signature": sig},
        ).json()["access_token"]
        r = auth_client.get(f"/api/v1/users/{other_wallet}/agents", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403


@pytest.mark.parametrize(
    "env,should_raise",
    [
        ("development", False),
        ("test", False),
        ("production", True),  # SECRET_KEY default + DEMO_MODE unset -> raises
    ],
)
def test_production_config_validation_fast_fails(env, should_raise, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@localhost:5432/db")
    monkeypatch.setenv("USE_REAL_PAYMENT", "true")
    monkeypatch.setenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    monkeypatch.setenv("SOLANA_PRIVATE_KEY", "x" * 88)
    monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", "z")
    monkeypatch.setenv("REDIS_URL", "redis://upstash:6379")
    monkeypatch.setenv("DEMO_MODE", "false")

    from app.core.config import Settings

    s = Settings()
    if should_raise:
        with pytest.raises(RuntimeError):
            s.verify_production_config()
    else:
        s.verify_production_config()  # should not raise