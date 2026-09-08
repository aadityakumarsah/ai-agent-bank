import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Provider abstraction for AI services. Never hardcode a single AI vendor."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def configured(self) -> bool:
        pass

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant text."""
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY

    @property
    def name(self) -> str:
        return "openai"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def complete(self, system: str, user: str) -> str:
        import openai

        client = openai.OpenAI(api_key=self._api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.ANTHROPIC_API_KEY

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def complete(self, system: str, user: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        msg = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


class GoogleProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.GOOGLE_AI_API_KEY

    @property
    def name(self) -> str:
        return "google"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def complete(self, system: str, user: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(f"{system}\n\n{user}")
        return resp.text or ""


class NoLLMConfiguredError(RuntimeError):
    """Raised in real mode when an agent task needs reasoning but no LLM key
    is configured (neither a per-wallet key nor a server-level key).

    Real agents reason with a genuine model — a hardcoded fake is never an
    acceptable substitute. The user adds their key in Settings (stored
    encrypted, per wallet) or the deployment sets OPENAI/ANTHROPIC/GOOGLE key.
    """


class MockLLMProvider(LLMProvider):
    """
    DEMO-only provider. Simulates an AI agent deciding to make a
    policy-compliant payment without requiring any external API key.

    Guardrail: even if an instance is constructed, ``complete()`` refuses to
    answer when DEMO_MODE is off. Real agents must never read scripted output.
    """

    @property
    def name(self) -> str:
        return "mock"

    @property
    def configured(self) -> bool:
        return True

    def complete(self, system: str, user: str) -> str:
        if not settings.DEMO_MODE:
            logger.error(
                "MockLLMProvider.complete called with DEMO_MODE off — refusing to "
                "simulate an agent's reasoning in real mode."
            )
            raise NoLLMConfiguredError(
                "No LLM is configured. Add an API key for your agent in Settings "
                "(or set OPENAI_API_KEY/ANTHROPIC_API_KEY/GOOGLE_AI_API_KEY on the "
                "server) before running a real task."
            )
        lower = user.lower()

        # --- Attack vector: agent tries to sweep funds to an unknown human wallet.
        if "300" in user and ("unknown" in user or "wallet" in user):
            return (
                '{"action":"payment","recipient":"unknownWallet",'
                '"recipient_name":"Unknown Human Wallet","amount":300,"category":"api",'
                '"description":"Transfer $300 to an unknown wallet"}'
            )

        # --- >-threshold purchase: e.g. "Buy a $75 deep-research report".
        if "75" in user:
            return (
                '{"action":"payment","recipient":"apiProvider",'
                '"recipient_name":"API Provider","amount":75,"category":"api",'
                '"description":"Purchase deep-research report from Web Search API"}'
            )

        # --- Story task: research + test a Solana RPC provider.
        if "rpc" in lower and ("research" in lower or "test" in lower or "provider" in lower):
            return (
                '{"action":"payment","recipient":"rpcProvider",'
                '"recipient_name":"RPC Compute Provider","amount":0.02,"category":"compute",'
                '"description":"Purchase Solana RPC access to test their API"}'
            )

        # --- Light API/RPC work below the auto-approval threshold.
        if "rpc" in lower or ("api" in lower and "provider" in lower):
            return (
                '{"action":"payment","recipient":"rpcProvider",'
                '"recipient_name":"RPC Compute Provider","amount":0.02,"category":"compute",'
                '"description":"Purchase Solana RPC access"}'
            )

        if "data" in lower:
            return (
                '{"action":"payment","recipient":"dataProvider",'
                '"recipient_name":"Data Provider","amount":5,"category":"data",'
                '"description":"Purchase market data"}'
            )
        return (
            '{"action":"respond","text":"I researched the task. No payment was required to complete it."}'
        )


def build_provider(name: Optional[str], api_key: Optional[str]) -> LLMProvider:
    """Instantiate a provider by name, falling back to env/mock resolution."""
    if name:
        cls = _PROVIDER_CLASSES.get(name)
        if cls is not None:
            return cls(api_key=api_key) if api_key else cls()
    return llm_service.active_provider


class LLMService:
    """Routes to the appropriate provider based on available API keys.

    In DEMO_MODE the mock provider is part of the chain so the UX works with
    zero keys. In real mode mock is excluded entirely: a task without a genuine
    LLM raises :class:`NoLLMConfiguredError` instead of silently simulating.
    """

    def __init__(self):
        self.providers: List[LLMProvider] = []
        if settings.DEMO_MODE:
            self.providers.append(MockLLMProvider())
        # Appends real providers whose keys are configured on the server.
        for provider in (OpenAIProvider(), AnthropicProvider(), GoogleProvider()):
            if provider.configured:
                self.providers.append(provider)

    @property
    def active_provider(self) -> LLMProvider:
        # Prefer real providers over mock when configured.
        for p in self.providers:
            if p.name != "mock":
                return p
        if self.providers:
            return self.providers[0]
        raise NoLLMConfiguredError(
            "No LLM provider is configured. Add an API key for your agent in "
            "Settings (or set OPENAI_API_KEY/ANTHROPIC_API_KEY/GOOGLE_AI_API_KEY "
            "on the server) to run real agent tasks."
        )

    def resolve_provider(
        self,
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> LLMProvider:
        """Pick the provider for a call. An explicitly passed key wins over the
        server env key. Falls back to any configured server provider, then mock
        (demo only). Never silently simulates in real mode."""
        if provider_name and api_key:
            cls = _PROVIDER_CLASSES.get(provider_name)
            if cls is not None:
                return cls(api_key=api_key)
            logger.warning("Unknown per-user provider %s; falling back", provider_name)
        if provider_name:
            cls = _PROVIDER_CLASSES.get(provider_name)
            if cls is not None and cls().configured:
                return cls()
        return self.active_provider

    def complete(
        self,
        system: str,
        user: str,
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> str:
        provider = self.resolve_provider(provider_name, api_key)
        logger.info("Using LLM provider: %s", provider.name)
        return provider.complete(system, user)


llm_service = LLMService()
_PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
}
