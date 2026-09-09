"""End-user LLM API key management (Part: per-user keys)."""
from fastapi.testclient import TestClient

from app.db.models import User, UserAPIKey
from app.services.ai_service import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OpenRouterProvider,
    MockLLMProvider,
    llm_service,
)


def _create_user(client: TestClient, wallet: str):
    r = client.post("/api/v1/users", json={"wallet_address": wallet})
    assert r.status_code == 201, r.text
    return wallet


def test_llm_key_round_trip(client, db):
    wallet = _create_user(client, "KeyWallet11111111111111111111111111111111")
    base = f"/api/v1/users/{wallet}/llm-keys"

    r = client.get(base)
    assert r.status_code == 200, r.text
    empty = {k["provider"]: k for k in r.json()}
    assert set(empty) == {"openai", "anthropic", "google", "openrouter"}
    assert all(
        entry["has_key"] is False and entry["source"] == "mock"
        for entry in empty.values()
    )

    r = client.put(f"{base}/openai", json={"api_key": "sk-test-super-secret-value"})
    assert r.status_code == 200, r.text

    r = client.get(base)
    openai = next(k for k in r.json() if k["provider"] == "openai")
    assert openai["has_key"] is True
    assert openai["source"] == "user"
    assert "secret" not in r.text.lower()

    user = db.query(User).filter(User.wallet_address == wallet).one()
    row = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == user.id, UserAPIKey.provider == "openai")
        .one()
    )
    assert row.encrypted_key != "sk-test-super-secret-value"

    r = client.delete(f"{base}/openai")
    assert r.status_code == 200, r.text
    r = client.get(base)
    assert all(
        k["provider"] != "openai" or k["has_key"] is False for k in r.json()
    )


def test_llm_key_unknown_provider_404(client):
    wallet = _create_user(client, "KeyWallet22222222222222222222222222222222")
    base = f"/api/v1/users/{wallet}/llm-keys"
    assert client.put(f"{base}/no-such-provider", json={"api_key": "x" * 12}).status_code == 404
    assert client.delete(f"{base}/no-such-provider").status_code == 404


def test_llm_key_upsert_overwrites(client, db):
    wallet = _create_user(client, "KeyWallet33333333333333333333333333333333")
    base = f"/api/v1/users/{wallet}/llm-keys"
    client.put(f"{base}/anthropic", json={"api_key": "sk-ant-first"})
    client.put(f"{base}/anthropic", json={"api_key": "sk-ant-second"})
    user = db.query(User).filter(User.wallet_address == wallet).one()
    rows = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == user.id, UserAPIKey.provider == "anthropic")
        .all()
    )
    assert len(rows) == 1


def test_resolve_provider_prefers_user_key_over_server_and_mock():
    user_openai = llm_service.resolve_provider("openai", "sk-user-provided")
    assert isinstance(user_openai, OpenAIProvider)

    user_anthropic = llm_service.resolve_provider("anthropic", "sk-ant-user")
    assert isinstance(user_anthropic, AnthropicProvider)

    user_google = llm_service.resolve_provider("google", "ai-user-provided")
    assert isinstance(user_google, GoogleProvider)

    user_openrouter = llm_service.resolve_provider("openrouter", "sk-or-v1-user")
    assert isinstance(user_openrouter, OpenRouterProvider)

    # With no keys at all (test env strips server keys) we fall back to mock.
    assert isinstance(llm_service.active_provider, MockLLMProvider)
    assert isinstance(llm_service.resolve_provider(), MockLLMProvider)
    # Unknown name falls back to the default (mock here).
    assert isinstance(llm_service.resolve_provider("nope", "some-key"), MockLLMProvider)


def test_real_mode_never_falls_back_to_mock(monkeypatch):
    """Real mode excludes the mock provider, so a task with no LLM key raises
    instead of silently simulating an agent's reasoning."""
    from app.core.config import settings
    from app.services.ai_service import (
        LLMService,
        MockLLMProvider,
        NoLLMConfiguredError,
    )

    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(settings, "GOOGLE_AI_API_KEY", "")

    real_service = LLMService()
    assert not any(isinstance(p, MockLLMProvider) for p in real_service.providers)

    try:
        real_service.active_provider
    except NoLLMConfiguredError:
        pass  # expected
    else:
        raise AssertionError("expected NoLLMConfiguredError in real mode without a key")


def test_parse_proposal_tolerates_code_fences(client):
    from app.services.agent_runtime import agent_runtime

    assert agent_runtime.parse_proposal('{"action":"respond","text":"ok"}') == {
        "action": "respond",
        "text": "ok",
    }
    assert agent_runtime.parse_proposal(
        '```json\n{"action":"payment","amount":1}\n```'
    ) == {"action": "payment", "amount": 1}
    assert agent_runtime.parse_proposal(
        'Sure! Here is the plan:\n```\n{"action":"respond","text":"done"}\n```'
    ) == {"action": "respond", "text": "done"}
    assert agent_runtime.parse_proposal("no json here") == {
        "action": "respond",
        "text": "no json here",
    }