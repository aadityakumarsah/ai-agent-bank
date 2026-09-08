from fastapi import APIRouter

from app.core.config import settings
from app.services.payment_service import payment_service
from app.services.ai_service import NoLLMConfiguredError, llm_service
from app.services.redis_service import redis_client

router = APIRouter(tags=["config"])


def _llm_status() -> tuple[str, bool]:
    """Resolve the active LLM provider without crashing /status in real mode
    when no key is configured yet (the UI needs to show that state)."""
    try:
        provider = llm_service.active_provider
        return provider.name, provider.name != "mock"
    except NoLLMConfiguredError:
        return "none", False


@router.get("/status")
def config_status():
    """Report runtime configuration so the UI can surface missing keys gracefully."""
    missing = []
    for key in ("DATABASE_URL", "SOLANA_RPC_URL", "REDIS_URL"):
        if key == "DATABASE_URL":
            if not settings.resolved_database_url:
                missing.append(key)
        elif key == "REDIS_URL":
            if not settings.REDIS_URL:
                missing.append(key)
        else:
            if not getattr(settings, key, ""):
                missing.append(key)

    if not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY and not settings.GOOGLE_AI_API_KEY:
        missing.append("AI_API_KEY (OPENAI/ANTHROPIC/GOOGLE)")

    llm_provider, llm_configured = _llm_status()

    return {
        "demo_mode": settings.DEMO_MODE,
        "payment_mode": "real" if payment_service.is_mock is False else "mock",
        "payment_configured": payment_service.is_mock is False,
        "solana_configured": bool(settings.SOLANA_RPC_URL and settings.SOLANA_PRIVATE_KEY),
        "solana_network": payment_service.network,
        "solana_usdc_mint": payment_service.usdc_mint,
        "rpc_configured": bool(settings.SOLANA_RPC_URL),
        "redis_configured": redis_client.enabled,
        "llm_provider": llm_provider,
        "llm_configured": llm_configured,
        "use_real_payment": settings.USE_REAL_PAYMENT,
        "missing_config": missing,
        "demo_scenarios": settings.DEMO_MODE,
    }