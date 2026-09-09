"""
Tool registry for the agent's native tool-calling loop.

The LLM may only call these tools. Each tool maps to the real purchase pipeline
(real marketplace listings + purchase intents) — the model can search, quote,
buy and poll, but it can never move money outside the policy engine or
fabricate a provider result.
"""

import json
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import Agent, PurchaseIntent
from app.services.ai_service import ToolSpec
from app.services.provider_adapters import (
    ProviderAdapterError,
    build_adapter,
)
from app.services.purchase_service import purchase_service

logger = logging.getLogger(__name__)

_SEARCH = ToolSpec(
    name="search_services",
    description=(
        "Search the marketplace of real, payable provider services. Returns "
        "candidate listings with their id, price, category and provider. Use "
        "this first."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional free-text filter"},
            "category": {"type": "string", "description": "api | compute | data | ai_model | storage | other_agent"},
        },
    },
)

_QUOTE = ToolSpec(
    name="get_quote",
    description=(
        "Get a real price quote for a listing before buying. Returns an "
        "intent_id and the quoted USDC amount. Call this for each candidate "
        "you are considering."
    ),
    parameters={
        "type": "object",
        "properties": {
            "listing_id": {"type": "integer", "description": "id from search_services"},
            "payload": {
                "type": "object",
                "description": "The service request, e.g. {text, langpair} for translation",
            },
        },
        "required": ["listing_id", "payload"],
    },
)

_SUBMIT = ToolSpec(
    name="submit_purchase",
    description=(
        "Buy a quoted service at its quoted price. The policy engine decides: "
        "approving executes a real USDC payment then the provider fulfils it. "
        "Call at most once per intent_id. If the result says approval_required, "
        "the human must approve — do NOT call this tool again for that intent."
    ),
    parameters={
        "type": "object",
        "properties": {
            "intent_id": {"type": "integer", "description": "id returned by get_quote"},
        },
        "required": ["intent_id"],
    },
)

_STATUS = ToolSpec(
    name="purchase_status",
    description="Check the current status/result of a purchase by intent_id.",
    parameters={
        "type": "object",
        "properties": {"intent_id": {"type": "integer"}},
        "required": ["intent_id"],
    },
)

TOOLS: List[ToolSpec] = [_SEARCH, _QUOTE, _SUBMIT, _STATUS]


def _quote_field(intent: PurchaseIntent, key: str, default: Any = None) -> Any:
    if not intent.quote:
        return default
    try:
        value = json.loads(intent.quote)
    except (json.JSONDecodeError, TypeError):
        return default
    return value.get(key, default) if isinstance(value, dict) else default


def list_tool_specs() -> List[ToolSpec]:
    return list(TOOLS)


def run_tool(
    db: Session,
    agent: Agent,
    task_run_id: int,
    name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute one tool call inside an agent run. Always returns a dict the
    model can read; failures come back as ``{"error": ...}``, never exceptions."""
    try:
        return _dispatch(db, agent, task_run_id, name, args)
    except ProviderAdapterError as e:
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.error("tool %s raised for agent=%s run=%s: %s", name, agent.id, task_run_id, e)
        return {"error": f"Internal tool error: {e}"}


def _dispatch(
    db: Session,
    agent: Agent,
    task_run_id: int,
    name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    if name == "search_services":
        listings = purchase_service.search(
            db, category=args.get("category"), query=args.get("query")
        )
        return {
            "listings": listings,
            "count": len(listings),
            "note": "Call get_quote with a listing_id and a payload to see the real price.",
        }

    if name == "get_quote":
        listing_id = int(args["listing_id"])
        payload = args.get("payload") or {}
        listing = purchase_service.get_listing(db, listing_id)
        adapter = build_adapter(listing.provider.adapter)
        # Surface incompatible payloads (translation needs text/langpair) before
        # persisting anything.
        adapter.quote(listing, payload, api_base_url=listing.provider.api_base_url)
        intent = purchase_service.create_quote(
            db, agent, listing, payload, task_run_id=task_run_id
        )
        return {
            "intent_id": intent.id,
            "status": intent.status.value,
            "listing_id": listing.id,
            "listing_name": listing.name,
            "provider_name": listing.provider.name,
            "provider_wallet_address": listing.provider.wallet_address,
            "amount": float(intent.amount or 0),
            "currency": _quote_field(intent, "currency", "USDC"),
            "quote_notes": _quote_field(intent, "notes"),
            "suggestion": "Call submit_purchase with this intent_id to buy at this quoted price.",
        }

    if name == "submit_purchase":
        result = purchase_service.submit(db, agent, int(args["intent_id"]))
        intent = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.id == result["intent_id"])
            .first()
        )
        if intent is not None:
            purchase_service.finalize_run(db, intent)
        return result

    if name == "purchase_status":
        return purchase_service.status(db, int(args["intent_id"]))

    return {"error": f"Unknown tool: {name}"}