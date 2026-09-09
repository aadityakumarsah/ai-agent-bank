"""
Real provider adapters for the "agent buys things" loop.

An adapter turns a registered ``ProviderProfile`` (a base URL + a wallet that
collects USDC) into something the agent bank can actually buy from:

    quote   -> validate the request payload + return the real price
    execute -> perform the real service and return the real result

Only *real*, machine-readable integrations live here. There is deliberately
no simulated provider: in real mode an agent can only buy from a provider
whose endpoint answers a live quote/health check.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.db.models import ServiceListing

logger = logging.getLogger(__name__)


class ProviderAdapterError(RuntimeError):
    """A provider integration refused the request (validation/network/format)."""


class QuoteResult:
    """The provider's real quote for a request payload."""

    def __init__(
        self,
        amount: float,
        currency: str = "USDC",
        expires_at: Optional[str] = None,
        notes: Optional[List[str]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.amount = amount
        self.currency = currency
        self.expires_at = expires_at
        self.notes = notes or []
        self.raw = raw or {}

    def to_dict(self) -> dict:
        return {
            "amount": round(float(self.amount), 6),
            "currency": self.currency,
            "expires_at": self.expires_at,
            "notes": self.notes,
            "raw": self.raw,
        }


class ProviderResult:
    """Outcome of executing a paid purchase against a provider."""

    def __init__(
        self,
        ok: bool,
        data: Optional[Dict[str, Any]] = None,
        provider_ref: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.ok = ok
        self.data = data or {}
        self.provider_ref = provider_ref
        self.raw = raw or {}
        self.error = error

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": self.data,
            "provider_ref": self.provider_ref,
            "raw": self.raw,
            "error": self.error,
        }


class ProviderAdapter(ABC):
    """Contract every real provider integration must satisfy."""

    @property
    @abstractmethod
    def key(self) -> str:
        """Adapter identifier used in ProviderProfile.adapter (e.g. "mymemory")."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable adapter name shown in the UI."""

    @abstractmethod
    def capability_names(self) -> list[str]:
        """Capabilities this adapter can fulfil (e.g. ["translate"])."""

    @abstractmethod
    def health_check(self, api_base_url: str) -> Tuple[bool, str]:
        """Call the provider's endpoint to prove it is reachable. Returns
        ``(ok, message)``. Used at registration to mark the provider verified."""

    @abstractmethod
    def validate_listing(self, listing: ServiceListing) -> list[str]:
        """Return a list of problems (empty = acceptable) if the listing's
        parameter schema is incompatible with this adapter."""

    @abstractmethod
    def quote(
        self,
        listing: ServiceListing,
        payload: Dict[str, Any],
        api_base_url: Optional[str] = None,
    ) -> QuoteResult:
        """Validate the request payload and return the real price. Never moves
        money and never charges the caller."""

    @abstractmethod
    def execute(
        self,
        listing: ServiceListing,
        payload: Dict[str, Any],
        payment_proof: Dict[str, Any],
        api_base_url: Optional[str] = None,
    ) -> ProviderResult:
        """Perform the paid service. ``payment_proof`` carries the executed
        ledger tx hash so the provider can settle/audit. Never fakes a result."""


# ---------------------------------------------------------------------------
# MyMemory — public machine-readable translation API (no key required)
# ---------------------------------------------------------------------------
class MyMemoryTranslationAdapter(ProviderAdapter):
    """
    Real translation via the public MyMemory API (api.mymemory.translated.net).

     * ``quote`` validates text + langpair and prices the request deterministically
       from character count against the provider's public pricing table.
     * ``execute`` performs the actual translation server-side and returns the
       real translated text (plus MyMemory's match/quality metadata).

    MyMemory itself is a free public translation endpoint; the USDC settlement
    is the Agent Bank paying the registered provider's wallet (devnet) through
    the policy engine, and is labelled as such in quotes — we never claim
    MyMemory bills the buyer.
    """

    key = "mymemory"
    label = "MyMemory (public translation API)"
    DEFAULT_BASE_URL = "https://api.mymemory.translated.net"
    PRICE_PER_1000_CHARS = Decimal("0.010000")  # $0.01 / 1k chars (public table)
    FLOOR_PRICE = Decimal("0.020000")  # minimum quote (devnet parity floor)
    MAX_TEXT_CHARS = 8000  # provider limit for a single translation request

    def capability_names(self) -> list[str]:
        return ["translate"]

    # -- validation --------------------------------------------------------
    def _split_langpair(self, payload: Dict[str, Any]) -> str:
        langpair = payload.get("langpair")
        if langpair and isinstance(langpair, str) and "|" in langpair:
            return langpair
        source = payload.get("source")
        target = payload.get("target")
        if source and target:
            return f"{source}|{target}"
        raise ProviderAdapterError(
            "payload must include 'langpair' (e.g. 'en|es') or 'source' + 'target'."
        )

    def _extract_text(self, listing: ServiceListing, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ProviderAdapterError("Request payload must be a JSON object.")
        text = payload.get("text") or payload.get("q")
        if not isinstance(text, str) or not text.strip():
            raise ProviderAdapterError("payload requires a non-empty 'text' string.")
        text = text.strip()
        if len(text) > self.MAX_TEXT_CHARS:
            raise ProviderAdapterError(
                f"text too long ({len(text)} chars); maximum is {self.MAX_TEXT_CHARS}."
            )
        return text

    def validate_listing(self, listing: ServiceListing) -> list[str]:
        issues: list[str] = []
        try:
            schema = json.loads(listing.parameters or "{}")
        except (json.JSONDecodeError, TypeError):
            return ["parameters must be valid JSON"]
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if schema.get("type") != "object":
            issues.append("parameters schema must be a JSON object schema")
        if "text" not in props and "q" not in props:
            issues.append("parameters must declare a required string field 'text'")
        has_langpair = "langpair" in props
        has_src_tgt = "source" in props and "target" in props
        if not has_langpair and not has_src_tgt:
            issues.append("parameters must declare 'langpair' or 'source'+'target'")
        return issues

    # -- network -----------------------------------------------------------
    def _base(self, api_base_url: Optional[str]) -> str:
        base = (api_base_url or self.DEFAULT_BASE_URL).rstrip("/")
        if not base.startswith("http"):
            raise ProviderAdapterError("api_base_url must be an http(s) URL.")
        return base

    def _fetch_translation(self, base: str, text: str, langpair: str) -> Dict[str, Any]:
        """GET for short texts, POST (form) for longer ones — both documented
        MyMemory request forms."""
        params = {"q": text, "langpair": langpair, "mt": "1"}
        try:
            resp = httpx.get(f"{base}/get", params=params, timeout=20)
            if resp.status_code >= 400:
                return {"ok": False, "error": f"HTTP {resp.status_code}", "raw": {}}
            body = resp.json()
            if body.get("responseStatus") not in (200, 201):
                return {
                    "ok": False,
                    "error": body.get("responseDetails") or "MyMemory API error",
                    "raw": body,
                }
            translated = (
                (body.get("responseData") or {}).get("translatedText")
                if body.get("responseData")
                else None
            )
            if not isinstance(translated, str):
                return {"ok": False, "error": "No translated text in response.", "raw": body}
            return {"ok": True, "data": {"translated_text": translated}, "raw": body}
        except ProviderAdapterError:
            raise
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"Provider request failed: {e}", "raw": {}}

    # -- interface ---------------------------------------------------------
    def health_check(self, api_base_url: str) -> Tuple[bool, str]:
        base = self._base(api_base_url)
        resp = self._fetch_translation(base, "hello", "en|es")
        if resp["ok"]:
            return True, "reachable (translation API responded)"
        return False, resp["error"]

    def quote(
        self,
        listing: ServiceListing,
        payload: Dict[str, Any],
        api_base_url: Optional[str] = None,
    ) -> QuoteResult:
        text = self._extract_text(listing, payload)
        langpair = self._split_langpair(payload)
        chars = len(text)
        by_chars = (Decimal(chars) / Decimal("1000")) * self.PRICE_PER_1000_CHARS
        amount = max(self.FLOOR_PRICE, Decimal(str(listing.price)), by_chars)
        expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        return QuoteResult(
            amount=float(amount),
            expires_at=expires,
            notes=[
                f"Estimated {amount:.4f} USDC from {chars} characters @ "
                f"{self.PRICE_PER_1000_CHARS:.2f}/1k chars.",
                "USDC settles to the provider wallet on devnet through the "
                "Agent Bank policy engine (quote != MyMemory billing).",
                f"Translating {langpair}. Result returned after payment confirms.",
            ],
            raw={
                "adapter": self.key,
                "langpair": langpair,
                "characters": chars,
                "pricing": "per-1000-chars public table",
            },
        )

    def execute(
        self,
        listing: ServiceListing,
        payload: Dict[str, Any],
        payment_proof: Dict[str, Any],
        api_base_url: Optional[str] = None,
    ) -> ProviderResult:
        base = self._base(api_base_url)
        text = self._extract_text(listing, payload)
        langpair = self._split_langpair(payload)
        resp = self._fetch_translation(base, text, langpair)
        if not resp["ok"]:
            return ProviderResult(ok=False, error=resp["error"], raw=resp["raw"])
        data = dict(resp["data"])
        data["langpair"] = langpair
        data["payment"] = {
            "signature": payment_proof.get("tx_hash"),
            "mode": payment_proof.get("mode", "unknown"),
            "simulated": payment_proof.get("simulated", False),
        }
        return ProviderResult(
            ok=True,
            data=data,
            raw=resp["raw"],
            provider_ref=None,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
ADAPTER_CLASSES: Dict[str, type] = {
    MyMemoryTranslationAdapter.key: MyMemoryTranslationAdapter,
}


def get_adapter_class(key: str) -> type:
    if key not in ADAPTER_CLASSES:
        raise ProviderAdapterError(
            f"Unknown provider adapter '{key}'. Known adapters: {sorted(ADAPTER_CLASSES)}"
        )
    return ADAPTER_CLASSES[key]


def build_adapter(adapter_key: str) -> ProviderAdapter:
    return get_adapter_class(adapter_key)()