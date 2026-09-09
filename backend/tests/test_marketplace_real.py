"""Real-provider marketplace: registration, listings, quoting, and the full
agent-buys-something loop exercised with an injectable fake adapter only —
never the network (matches the repo rule that tests use canned adapters)."""

import pytest

from app.db.models import ServiceListing
from app.services import provider_adapters
from app.services.provider_adapters import (
    ProviderAdapter,
    ProviderAdapterError,
    ProviderResult,
    QuoteResult,
)

PROVIDER_WALLET = "11111111111111111111111111111111"


class FakeTranslationAdapter(ProviderAdapter):
    key = "faketrans"
    label = "Fake (test) translation API"

    def capability_names(self) -> list[str]:
        return ["translate"]

    def health_check(self, api_base_url: str):
        return True, "test adapter reachable"

    def validate_listing(self, listing: ServiceListing) -> list[str]:
        return []

    def quote(self, listing, payload, api_base_url=None) -> QuoteResult:
        text = payload.get("text") or payload.get("q") or ""
        if not isinstance(text, str) or not text.strip():
            raise ProviderAdapterError("payload requires a non-empty 'text' string.")
        if "langpair" not in payload and "source" not in payload:
            raise ProviderAdapterError("payload requires 'langpair' or 'source'+'target'.")
        return QuoteResult(
            amount=0.02,
            notes=[f"Fake quote for {len(text)} chars."],
        )

    def execute(self, listing, payload, payment_proof, api_base_url=None) -> ProviderResult:
        return ProviderResult(
            ok=True,
            data={
                "translated_text": "HOLA TEST",
                "text_chars": len(payload.get("text") or ""),
                "langpair": payload.get("langpair") or "en|es",
            },
            provider_ref=f"fake-ref-{payment_proof.get('tx_hash')}",
        )


@pytest.fixture(autouse=True)
def _fake_adapter():
    provider_adapters.ADAPTER_CLASSES[FakeTranslationAdapter.key] = FakeTranslationAdapter
    yield
    provider_adapters.ADAPTER_CLASSES.pop(FakeTranslationAdapter.key, None)


def _register_provider_and_listing(client, wallet, name=None):
    client.post("/api/v1/users", json={"wallet_address": wallet})
    name = name or f"Fake Trans {wallet}"
    r = client.post(
        "/api/v1/marketplace/providers",
        json={
            "name": name,
            "description": "test provider",
            "adapter": "faketrans",
            "api_base_url": "https://fake.example.test",
            "category": "api",
            "wallet_address": PROVIDER_WALLET,
            "owner_wallet": wallet,
            "supports": ["translate"],
        },
    )
    assert r.status_code == 201, r.text
    provider = r.json()
    assert provider["status"] == "active"
    assert provider["verified"] is True

    r = client.post(
        f"/api/v1/marketplace/providers/{provider['id']}/listings",
        json={
            "name": "Translate 1k",
            "description": "Translate up to 1k characters.",
            "category": "api",
            "price": 0.02,
            "requires_payment": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "langpair": {"type": "string"},
                },
            },
        },
    )
    assert r.status_code == 201, r.text
    listing = r.json()
    assert listing["status"] == "active"
    return provider, listing


def test_register_provider_validation(client, agent_factory):
    wallet = "wallet_prov_validate"
    client.post("/api/v1/users", json={"wallet_address": wallet})

    # unknown adapter key -> 400 with a useful message
    r = client.post(
        "/api/v1/marketplace/providers",
        json={
            "name": "Bad Adapter",
            "adapter": "not_a_real_adapter",
            "api_base_url": "https://x.test",
            "category": "api",
            "wallet_address": PROVIDER_WALLET,
            "owner_wallet": wallet,
            "supports": ["translate"],
        },
    )
    assert r.status_code == 400
    assert "Unknown provider adapter" in r.json()["detail"]

    # unsupported capability -> 400
    r = client.post(
        "/api/v1/marketplace/providers",
        json={
            "name": "Bad Capability",
            "adapter": "faketrans",
            "api_base_url": "https://x.test",
            "category": "api",
            "wallet_address": PROVIDER_WALLET,
            "owner_wallet": wallet,
            "supports": ["fly"],
        },
    )
    assert r.status_code == 400
    assert "does not support" in r.json()["detail"]

    # invalid provider wallet -> 400 (valid length but not base58)
    r = client.post(
        "/api/v1/marketplace/providers",
        json={
            "name": "Bad Wallet",
            "adapter": "faketrans",
            "api_base_url": "https://x.test",
            "category": "api",
            "wallet_address": "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO",
            "owner_wallet": wallet,
            "supports": ["translate"],
        },
    )
    assert r.status_code == 400


def test_marketplace_listings_empty(client):
    r = client.get("/api/v1/marketplace/listings")
    assert r.status_code == 200
    assert r.json() == []


def test_full_auto_pay_loop(client, agent_factory):
    wallet = "wallet_buys"
    agent = agent_factory(client, wallet)
    _provider, listing = _register_provider_and_listing(client, wallet)

    # quote (never moves money)
    r = client.post(
        f"/api/v1/marketplace/listings/{listing['id']}/quote",
        json={
            "agent_id": agent["id"],
            "payload": {"text": "Hola", "langpair": "en|es"},
        },
    )
    assert r.status_code == 200, r.text
    quote = r.json()
    assert quote["status"] == "quoting"
    assert float(quote["amount"]) == 0.02
    assert quote["currency"] == "USDC"

    # submit -> policy passes (< approval threshold) -> mock payment -> provider
    r = client.post(
        "/api/v1/marketplace/purchases",
        json={"intent_id": quote["intent_id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "completed"
    assert body["approved"] is True
    assert body["transaction"]["status"] == "executed"
    intent = body["intent"]
    assert intent["status"] == "completed"
    assert intent["result"]["data"]["translated_text"] == "HOLA TEST"
    assert intent["result"]["provider_ref"].startswith("fake-ref-")

    # ledger actually debited
    after = client.get(f"/api/v1/users/{wallet}/agents/{agent['id']}").json()
    assert abs(float(after["balance"]) - 99.98) < 1e-6

    # idempotent re-submit: same result, no second payment
    r2 = client.post(
        "/api/v1/marketplace/purchases",
        json={"intent_id": quote["intent_id"]},
    )
    assert r2.status_code == 200
    assert r2.json()["outcome"] == "completed"
    txs = client.get(f"/api/v1/users/{wallet}/transactions").json()
    executed = [t for t in txs if t["status"] == "executed"]
    assert len(executed) == 1


def test_approval_required_then_resume(client, agent_factory):
    wallet = "wallet_approval_real"
    agent = agent_factory(client, wallet, approval=0.01)  # 0.02 exceeds threshold
    _provider, listing = _register_provider_and_listing(client, wallet)

    r = client.post(
        f"/api/v1/marketplace/listings/{listing['id']}/quote",
        json={"agent_id": agent["id"], "payload": {"text": "Hola", "langpair": "en|es"}},
    )
    intent_id = r.json()["intent_id"]

    r = client.post("/api/v1/marketplace/purchases", json={"intent_id": intent_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "approval_required"
    assert body["approved"] is False
    tx_id = body["transaction"]["id"]

    # still quoting->pending: nothing paid, no provider executed yet
    state = client.get(f"/api/v1/marketplace/purchases/{intent_id}").json()
    assert state["status"] == "pending_approval"
    assert state["result"] is None

    # human approves through the canonical payments endpoint -> resume fulfilment
    r = client.post(f"/api/v1/users/{wallet}/transactions/{tx_id}/approve")
    assert r.status_code == 200, r.text
    approve = r.json()
    assert approve["executed"] is True
    assert approve["purchase"]["id"] == intent_id
    assert approve["purchase"]["status"] == "completed"

    after = client.get(f"/api/v1/marketplace/purchases/{intent_id}").json()
    assert after["status"] == "completed"
    assert after["result"]["data"]["translated_text"] == "HOLA TEST"

    ledger = client.get(f"/api/v1/users/{wallet}/transactions").json()
    assert len([t for t in ledger if t["status"] == "executed"]) == 1


def test_inactive_listing_cannot_be_purchased(client, agent_factory):
    wallet = "wallet_inactive"
    agent = agent_factory(client, wallet)
    _provider, listing = _register_provider_and_listing(client, wallet)

    r = client.patch(
        f"/api/v1/marketplace/listings/{listing['id']}/status",
        json={"status": "inactive"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"

    r = client.post(
        f"/api/v1/marketplace/listings/{listing['id']}/quote",
        json={"agent_id": agent["id"], "payload": {"text": "Hola", "langpair": "en|es"}},
    )
    assert r.status_code == 400
    assert "not active" in r.json()["detail"]