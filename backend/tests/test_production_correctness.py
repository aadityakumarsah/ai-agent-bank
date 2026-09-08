"""Tests for the production-correctness slice:

1. marketplace owner checks (IDOR closed) when REQUIRE_AUTH is on
2. risk engine gating: HIGH scored transactions route to requires_approval
3. confirm_fund never trusts the client-supplied amount (on-chain source of truth)
4. get_payment_service refuses to boot on mock in production
5. verify_transaction surfaces parsed on-chain transfer fields
"""

import hashlib
import json
from datetime import datetime, timezone

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.db.models import (
    User,
    Agent,
    AgentStatus,
    Policy,
    Transaction,
    TransactionStatus,
    TransactionType,
    PolicyCategory,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _make_wallet(tag: str):
    from solders.keypair import Keypair

    seed = hashlib.sha256(tag.encode()).digest()
    kp = Keypair.from_seed(seed)
    return str(kp.pubkey()), kp


def _sign_message(kp, message: str) -> str:
    return str(kp.sign_message(message.encode("utf-8")))


def _token_for(client: TestClient, wallet: str, kp) -> str:
    nonce = client.post("/api/v1/auth/nonce", json={"wallet_address": wallet}).json()
    sig = _sign_message(kp, nonce["message"])
    body = client.post(
        "/api/v1/auth/verify",
        json={
            "wallet_address": wallet,
            "message": nonce["message"],
            "signature": sig,
        },
    )
    assert body.status_code == 200, body.text
    return body.json()["access_token"]


def _seed_risk_agent(db, wallet="risk-engine-wallet"):
    """An agent whose policy passes checks for a $150 spend but whose inputs
    push the deterministic risk score into the HIGH band."""
    user = User(wallet_address=wallet)
    db.add(user)
    db.commit()
    db.refresh(user)

    agent = Agent(name="RiskBot", user_id=user.id, balance=Decimal("5000"), status=AgentStatus.active)
    db.add(agent)
    db.commit()
    db.refresh(agent)

    policy = Policy(
        agent_id=agent.id,
        user_id=user.id,
        max_per_transaction=Decimal("10000"),
        max_per_day=Decimal("5000"),
        max_per_month=None,
        allowed_categories=json.dumps(["api"]),
        blocked_human_transfers=True,
        blocked_withdrawals=True,
        blocked_arbitrary_contracts=True,
        require_approval_above=None,
        allowed_recipient_addresses=json.dumps(["MerchantATA"]),
    )
    db.add(policy)
    db.commit()

    # 1 large executed spend (drives daily utilization toward ~90%) + 10 recent
    # small txs (drive velocity high). 4510/5000 = 90.2% utilization.
    now = datetime.now(timezone.utc)
    rows = [Transaction(
        agent_id=agent.id,
        user_id=user.id,
        amount=Decimal("4500"),
        currency="USDC",
        transaction_type=TransactionType.payment,
        status=TransactionStatus.executed,
        recipient_address="MerchantATA",
        recipient_name="Merchant",
        category=PolicyCategory.api,
        created_at=now,
        risk_score=0,
        risk_level="low",
    )]
    for i in range(10):
        rows.append(Transaction(
            agent_id=agent.id,
            user_id=user.id,
            amount=Decimal("1"),
            currency="USDC",
            transaction_type=TransactionType.payment,
            status=TransactionStatus.executed,
            recipient_address="MerchantATA",
            recipient_name="Merchant",
            category=PolicyCategory.api,
            created_at=now,
            risk_score=0,
            risk_level="low",
        ))
    db.add_all(rows)
    db.commit()
    db.refresh(agent)
    return agent, policy


# ---------------------------------------------------------------------------
# 1. Marketplace IDOR
# ---------------------------------------------------------------------------
class TestMarketplaceOwnership:
    @pytest.fixture()
    def auth_settings(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "REQUIRE_AUTH", True, raising=False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "development", raising=False)
        yield
        monkeypatch.setattr(settings, "REQUIRE_AUTH", False, raising=False)

    def _create_agent(self, client, wallet, kp, name="OwnerBot"):
        tok = _token_for(client, wallet, kp)
        r = client.post(
            f"/api/v1/users/{wallet}/agents",
            json={"name": name},
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert r.status_code == 201, r.text
        return r.json()["id"], tok

    def test_attacker_cannot_request_service_for_others_agent(
        self, client, auth_settings
    ):
        owner, owner_kp = _make_wallet("idor-owner")
        attacker, attacker_kp = _make_wallet("idor-attacker")
        agent_id, owner_tok = self._create_agent(client, owner, owner_kp)
        attacker_tok = _token_for(client, attacker, attacker_kp)

        service_id = client.get("/api/v1/services").json()[0]["id"]

        # Attacker (valid token, different wallet) asks the service to run on
        # the owner's agent → must be 403, never "payment_required".
        r = client.post(
            f"/api/v1/services/{service_id}/request",
            json={"agent_id": agent_id},
            headers={"Authorization": f"Bearer {attacker_tok}"},
        )
        assert r.status_code == 403, r.text

        # The owner themselves is allowed.
        ok = client.post(
            f"/api/v1/services/{service_id}/request",
            json={"agent_id": agent_id},
            headers={"Authorization": f"Bearer {owner_tok}"},
        )
        assert ok.status_code == 200, ok.text

    def test_attacker_cannot_pay_for_others_agent(self, client, auth_settings):
        owner, owner_kp = _make_wallet("idor-pay-owner")
        attacker, attacker_kp = _make_wallet("idor-pay-attacker")
        agent_id, _ = self._create_agent(client, owner, owner_kp)
        attacker_tok = _token_for(client, attacker, attacker_kp)

        service_id = next(
            s["id"]
            for s in client.get("/api/v1/services").json()
            if s["name"] == "Solana RPC API"
        )
        r = client.post(
            f"/api/v1/services/{service_id}/payment",
            json={"agent_id": agent_id, "requested_amount": 0.02},
            headers={"Authorization": f"Bearer {attacker_tok}"},
        )
        assert r.status_code == 403, r.text

    def test_no_token_is_401(self, client, auth_settings):
        r = client.post("/api/v1/services/1/request", json={"agent_id": 1})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 2. Risk engine gating
# ---------------------------------------------------------------------------
class TestRiskGating:
    def test_high_risk_routes_to_requires_approval(self, db, client):
        from app.services.policy_engine import policy_engine

        agent, policy = _seed_risk_agent(db, "risk-high-wallet")
        result = policy_engine.evaluate_transaction(
            agent=agent,
            policy=policy,
            amount=150.0,
            category="api",
            recipient_address="MerchantATA",
            recipient_name="Merchant",
            db=db,
        )
        assert result.risk_level == "high", result.risk_factors
        assert result.risk_score is not None and result.risk_score >= 71
        assert result.requires_approval is True
        assert result.allowed is False

    def test_small_known_payment_stays_low_risk(self, db, client):
        from app.services.policy_engine import policy_engine

        agent, policy = _seed_risk_agent(db, "risk-small-wallet")
        result = policy_engine.evaluate_transaction(
            agent=agent,
            policy=policy,
            amount=1.0,
            category="api",
            recipient_address="MerchantATA",
            recipient_name="Merchant",
            db=db,
        )
        assert result.risk_level in ("low", "medium")
        assert result.requires_approval is False
        assert result.allowed is True

    def test_high_risk_payment_persists_risk_to_ledger(self, client, agent_factory):
        service = next(
            s for s in client.get("/api/v1/services").json() if s["name"] == "Premium Data API"
        )
        agent = agent_factory(client, "risk-wallet-ledger")
        # raise the daily cap so a big payment isn't blocked by the daily limit
        client.post(
            f"/api/v1/users/risk-wallet-ledger/agents/{agent['id']}/policy",
            json={
                "max_per_transaction": 10000,
                "max_per_day": 5000,
                "allowed_categories": ["api", "compute", "data", "agent"],
                "blocked_human_transfers": True,
                "blocked_withdrawals": True,
                "blocked_arbitrary_contracts": True,
                "require_approval_above": None,
                "allowed_recipient_addresses": [],
            },
        )
        r = client.post(
            f"/api/v1/services/{service['id']}/payment",
            json={"agent_id": agent["id"], "requested_amount": 150.0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Whichever branch: the risk decision must be visible on the ledger row.
        assert body["transaction"]["status"] in ("rejected", "approval_required", "paid", "failed")
        assert body["transaction"]["risk_level"] in ("low", "medium", "high")


# ---------------------------------------------------------------------------
# 3. confirm_fund never trusts the client amount
# ---------------------------------------------------------------------------
class TestConfirmFundOnChain:
    def _stub_payment_service(self, monkeypatch, verify, usdc_mint="USDC_MINT", ata="ESCROW_ATA"):
        """Swap the module-level payment_service for a controllable fake."""
        import app.api.api_v1.agents as agents_module

        class Fake:
            def __init__(self):
                self.is_mock = False
                self.usdc_mint = usdc_mint
                self.decimals = 6
                self._verify = verify
                self._ata = ata

            def escrow_usdc_ata(self, escrow: str):
                return self._ata

            def verify_transaction(self, signature: str):
                return self._verify

        monkeypatch.setattr(agents_module, "payment_service", Fake())
        return agents_module

    @staticmethod
    def _ensure_user_and_agent(client: TestClient, wallet: str, name: str):
        client.post("/api/v1/users", json={"wallet_address": wallet})
        r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": name})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_credits_onchain_amount_not_client_amount(self, client, monkeypatch):
        agent_id = self._ensure_user_and_agent(client, "confirm-wallet", "ConfirmBot")

        self._stub_payment_service(
            monkeypatch,
            verify={
                "verified": True,
                "amount": 1_500_000,  # 1.5 USDC in raw units
                "mint": "USDC_MINT",
                "destination": "ESCROW_ATA",
            },
        )
        r = client.post(
            f"/api/v1/users/confirm-wallet/agents/{agent_id}/fund/confirm",
            json={"amount": 100.0, "signature": "sig1"},
        )
        assert r.status_code == 200, r.text
        # client lied ($100); the ledger credits the on-chain value ($1.50)
        assert abs(float(r.json()["balance"]) - 1.5) < 1e-6

    def test_wrong_mint_rejected(self, client, monkeypatch):
        agent_id = self._ensure_user_and_agent(client, "confirm-wallet2", "ConfirmBot2")
        self._stub_payment_service(
            monkeypatch,
            verify={
                "verified": True,
                "amount": 500_000,
                "mint": "OTHER_MINT",
                "destination": "ESCROW_ATA",
            },
        )
        r = client.post(
            f"/api/v1/users/confirm-wallet2/agents/{agent_id}/fund/confirm",
            json={"amount": 5.0, "signature": "sig2"},
        )
        assert r.status_code == 400
        assert "token" in r.json()["detail"].lower()

    def test_non_escrow_destination_rejected(self, client, monkeypatch):
        agent_id = self._ensure_user_and_agent(client, "confirm-wallet3", "ConfirmBot3")
        self._stub_payment_service(
            monkeypatch,
            verify={
                "verified": True,
                "amount": 500_000,
                "mint": "USDC_MINT",
                "destination": "SOMEONE_ELSE",
            },
        )
        r = client.post(
            f"/api/v1/users/confirm-wallet3/agents/{agent_id}/fund/confirm",
            json={"amount": 5.0, "signature": "sig3"},
        )
        assert r.status_code == 400
        assert "escrow" in r.json()["detail"].lower()

    def test_unparseable_transfer_rejected(self, client, monkeypatch):
        agent_id = self._ensure_user_and_agent(client, "confirm-wallet4", "ConfirmBot4")
        self._stub_payment_service(
            monkeypatch,
            verify={"verified": True},  # no amount/destination parsed
        )
        r = client.post(
            f"/api/v1/users/confirm-wallet4/agents/{agent_id}/fund/confirm",
            json={"amount": 5.0, "signature": "sig4"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 4. Fail-closed payment factory
# ---------------------------------------------------------------------------
class TestFailClosedPayment:
    def test_get_payment_service_refuses_mock_in_production(self, monkeypatch):
        from app.core.config import settings
        from app.services.payment_service import get_payment_service

        monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
        monkeypatch.setattr(settings, "USE_REAL_PAYMENT", False, raising=False)
        monkeypatch.setattr(settings, "SOLANA_RPC_URL", "", raising=False)
        monkeypatch.setattr(settings, "SOLANA_PRIVATE_KEY", "", raising=False)

        assert settings.is_production is True
        with pytest.raises(RuntimeError):
            get_payment_service()

    def test_get_payment_service_production_missing_keys_refuses(self, monkeypatch):
        from app.core.config import settings
        from app.services.payment_service import get_payment_service

        # True real-payment flag but no RPC/key → must refuse, never fall back.
        monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
        monkeypatch.setattr(settings, "USE_REAL_PAYMENT", True, raising=False)
        monkeypatch.setattr(settings, "SOLANA_RPC_URL", "", raising=False)
        monkeypatch.setattr(settings, "SOLANA_PRIVATE_KEY", "", raising=False)

        with pytest.raises(RuntimeError):
            get_payment_service()

    def test_get_payment_service_dev_allows_mock(self, monkeypatch):
        from app.core.config import settings
        from app.services.payment_service import MockPaymentService, get_payment_service

        monkeypatch.setattr(settings, "ENVIRONMENT", "development", raising=False)
        monkeypatch.setattr(settings, "USE_REAL_PAYMENT", False, raising=False)
        monkeypatch.setattr(settings, "SOLANA_RPC_URL", "", raising=False)
        monkeypatch.setattr(settings, "SOLANA_PRIVATE_KEY", "", raising=False)

        svc = get_payment_service()
        assert isinstance(svc, MockPaymentService)


# ---------------------------------------------------------------------------
# 5. verify_transaction forwards parsed on-chain transfer fields
# ---------------------------------------------------------------------------
class TestVerifyTransactionParsesTransfer:
    def test_verify_forwards_amount_mint_destination(self, monkeypatch):
        from app.services.payment_service import SolanaPaymentService

        class _Svc(SolanaPaymentService):
            @property
            def mode(self) -> str:
                return "solana"

            @property
            def network(self) -> str:
                return "devnet"

        svc = object.__new__(_Svc)

        def fake_get_transaction(signature):
            return {
                "mode": "solana",
                "network": "devnet",
                "signature": signature,
                "found": True,
                "confirmed": True,
                "err": None,
                "slot": 42,
                "amount": 1_500_000,
                "mint": "USDC_MINT",
                "source": "FROM_ATA",
                "destination": "ESCROW_ATA",
            }

        monkeypatch.setattr(svc, "get_transaction", fake_get_transaction)
        out = svc.verify_transaction("sig-abc")

        assert out["verified"] is True
        assert out["amount"] == 1_500_000
        assert out["mint"] == "USDC_MINT"
        assert out["destination"] == "ESCROW_ATA"