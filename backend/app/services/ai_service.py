import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    """OpenAI-shaped function tool the model may call in the purchase loop."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # JSON schema

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMChatResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


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

    @property
    def supports_tools(self) -> bool:
        """True when the provider can natively call tools (function calling)."""
        return False

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant text."""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
    ) -> LLMChatResult:
        """Tool-capable providers override this. ``messages`` use an OpenAI-shaped
        multi-turn format: system/user/assistant(with tool_calls)/tool roles.
        Returns text plus any tool calls the model requested."""
        raise NotImplementedError("This provider does not support tool calling.")


def _unpack_tool_arguments(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _openai_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.OPENAI_API_KEY

    @property
    def name(self) -> str:
        return "openai"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_tools(self) -> bool:
        return True

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

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
    ) -> LLMChatResult:
        import openai

        client = openai.OpenAI(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = _openai_tools(tools)
            kwargs["tool_choice"] = "auto"
        resp = client.chat.completions.create(model="gpt-4o-mini", **kwargs)
        msg = resp.choices[0].message
        text = msg.content or ""
        tool_calls = []
        for tc in msg.tool_calls or []:
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, arguments=_unpack_tool_arguments(tc.function.arguments))
            )
        return LLMChatResult(text=text, tool_calls=tool_calls)


class OpenRouterProvider(LLMProvider):
    """OpenAI-compatible gateway (OpenRouter) to hundreds of models.

    Uses the OpenAI SDK pointed at OpenRouter's base URL. The model id follows
    OpenRouter's "vendor/model" convention and is configurable via
    ``OPENROUTER_MODEL``. Tool calling works identically to OpenAI.
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.OPENROUTER_API_KEY

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_tools(self) -> bool:
        return True

    def _client(self):
        import openai

        return openai.OpenAI(
            api_key=self._api_key, base_url=settings.OPENROUTER_BASE_URL
        )

    def complete(self, system: str, user: str) -> str:
        resp = self._client().chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
    ) -> LLMChatResult:
        kwargs: dict[str, Any] = {
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = _openai_tools(tools)
            kwargs["tool_choice"] = "auto"
        resp = self._client().chat.completions.create(
            model=settings.OPENROUTER_MODEL, **kwargs
        )
        msg = resp.choices[0].message
        text = msg.content or ""
        tool_calls = []
        for tc in msg.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=_unpack_tool_arguments(tc.function.arguments),
                )
            )
        return LLMChatResult(text=text, tool_calls=tool_calls)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.ANTHROPIC_API_KEY

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_tools(self) -> bool:
        return True

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

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
    ) -> LLMChatResult:
        import anthropic

        system = "\n\n".join(
            m["content"] for m in messages if m.get("role") == "system" and m.get("content")
        )
        conv: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            if role == "assistant":
                blocks: list[dict[str, Any]] = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []) or []:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc.get("arguments") or {},
                        }
                    )
                conv.append({"role": "assistant", "content": blocks or m.get("content")})
            elif role == "tool":
                conv.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.get("tool_call_id", ""),
                                "content": m.get("content", ""),
                            }
                        ],
                    }
                )
            else:
                conv.append({"role": "user", "content": m.get("content", "")})

        tool_specs = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in (tools or [])
        ]
        client = anthropic.Anthropic(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 2048,
            "system": system,
            "messages": conv,
        }
        if tool_specs:
            kwargs["tools"] = tool_specs
            kwargs["tool_choice"] = {"type": "auto"}
        msg = client.messages.create(**kwargs)

        text = ""
        tool_calls: list[ToolCall] = []
        for block in msg.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
                )
        return LLMChatResult(text=text, tool_calls=tool_calls)


class GoogleProvider(LLMProvider):
    """Gemini via the stateful Interactions API.

    ``generateContent`` no longer round-trips tool calls for current Gemini
    models (they require opaque ``thought_signature`` echo which that endpoint
    cannot even parse). The Interactions API in stateful mode (``store: true``
    + ``previous_interaction_id``) makes the server own all signature/thought
    state, so we only ever send the next user input or ``function_result``
    blocks.

    Sessions are keyed by the identity of the ``messages`` list object: the
    agent loop passes the SAME list it mutates on every iteration, so a single
    run maps to one server-side interaction, and concurrent runs (distinct list
    objects) stay isolated.
    """

    _INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
    _MAX_SESSIONS = 64

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.GOOGLE_AI_API_KEY
        self._sessions: dict[int, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "google"

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_tools(self) -> bool:
        return True

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                resp = httpx.post(
                    self._INTERACTIONS_URL,
                    headers={"x-goog-api-key": self._api_key},
                    json=payload,
                    timeout=120.0,
                )
                if resp.status_code >= 500 or resp.status_code == 429:
                    last_error = httpx.HTTPStatusError(
                        f"{resp.status_code} {resp.text[:200]}",
                        request=resp.request,
                        response=resp,
                    )
                    time.sleep((2 ** attempt) * 1.5)  # 1.5s, 3s, 6s
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep((2 ** attempt) * 1.5)
        raise last_error  # type: ignore[misc]

    def complete(self, system: str, user: str) -> str:
        data = self._post(
            {
                "model": settings.GOOGLE_AI_MODEL,
                "system_instruction": system,
                "input": user,
            }
        )
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                content = step.get("content") or []
                if content and content[0].get("text"):
                    return "".join(p.get("text", "") for p in content if p.get("text"))
        return ""

    @staticmethod
    def _tool_specs(tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters or {"type": "object", "properties": {}},
            }
            for t in tools
        ]

    @staticmethod
    def _tool_name_by_id(messages: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for m in messages:
            for tc in m.get("tool_calls", []) or []:
                if "function" in tc:
                    mapping[tc.get("id", "")] = tc["function"].get("name", "")
                else:
                    mapping[tc.get("id", "")] = tc.get("name", "")
        return mapping

    def _parse(self, data: dict[str, Any]) -> LLMChatResult:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for part in step.get("content") or []:
                    if part.get("text"):
                        text_parts.append(part["text"])
            elif step.get("type") == "function_call":
                arguments = step.get("arguments") or {}
                tool_calls.append(
                    ToolCall(
                        id=step.get("id") or f"{step.get('name', 'tool')}-{len(tool_calls)}",
                        name=step.get("name", ""),
                        arguments=dict(arguments) if isinstance(arguments, dict) else {},
                    )
                )
        return LLMChatResult(text="".join(text_parts), tool_calls=tool_calls)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec] | None = None,
    ) -> LLMChatResult:
        key = id(messages)
        session = self._sessions.get(key)
        tool_names = self._tool_name_by_id(messages)

        if session is None:
            system_text = "\n\n".join(
                m["content"] for m in messages if m.get("role") == "system" and m.get("content")
            )
            user_text = next(
                (m["content"] for m in messages if m.get("role") == "user" and m.get("content")),
                "",
            )
            payload: dict[str, Any] = {
                "model": settings.GOOGLE_AI_MODEL,
                "system_instruction": system_text,
                "input": user_text,
                "store": True,
            }
            if tools:
                payload["tools"] = self._tool_specs(tools)
            data = self._post(payload)
            interaction_id = data.get("id")
            if not interaction_id:
                raise RuntimeError(f"Gemini interaction returned no session id: {data}")
            self._sessions[key] = {"id": interaction_id, "next": 2}
            if len(self._sessions) > self._MAX_SESSIONS:
                self._sessions.pop(next(iter(self._sessions)))
        else:
            results = []
            idx = max(session["next"], 0)
            msgs = messages[idx:]
            for m in msgs:
                if m.get("role") == "tool":
                    results.append(
                        {
                            "type": "function_result",
                            "name": tool_names.get(m.get("tool_call_id", ""), "unknown"),
                            "call_id": m.get("tool_call_id", ""),
                            "result": [{"type": "text", "text": m.get("content") or ""}],
                        }
                    )
            session["next"] = len(messages)
            if results:
                data = self._post(
                    {
                        "model": settings.GOOGLE_AI_MODEL,
                        "previous_interaction_id": session["id"],
                        "input": results,
                    }
                )
                new_id = data.get("id")
                if new_id:
                    session["id"] = new_id
            else:
                data = {"steps": []}
        return self._parse(data)


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


def build_provider(name: str | None, api_key: str | None) -> LLMProvider:
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
        self.providers: list[LLMProvider] = []
        if settings.DEMO_MODE:
            self.providers.append(MockLLMProvider())
        # Appends real providers whose keys are configured on the server.
        for provider in (
            OpenRouterProvider(),
            OpenAIProvider(),
            AnthropicProvider(),
            GoogleProvider(),
        ):
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
            "Settings (or set OPENROUTER_API_KEY/OPENAI_API_KEY/"
            "ANTHROPIC_API_KEY/GOOGLE_AI_API_KEY on the server) to run real "
            "agent tasks."
        )

    def resolve_provider(
        self,
        provider_name: str | None = None,
        api_key: str | None = None,
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
        provider_name: str | None = None,
        api_key: str | None = None,
    ) -> str:
        provider = self.resolve_provider(provider_name, api_key)
        logger.info("Using LLM provider: %s", provider.name)
        return provider.complete(system, user)


llm_service = LLMService()
_PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "openrouter": OpenRouterProvider,
}