"""
Purchase orchestration — the canonical "agent buys things" path.

A purchase is backed by a real provider (``ProviderProfile`` + adapter) and a
payable listing (``ServiceListing``). The lifecycle:

    quote (no money)
      -> submit: policy engine gate
          -> blocked                          (intent = failed)
          -> human approval required          (intent = pending_approval)
          -> USDC payment via attempt_execution
              -> provider.execute (real service)  (intent = completed | failed)
      -> resume_after_payment (approvals endpoint)

Every stage is idempotent: a repeated submit for the same intent returns the
existing outcome and never pays twice (same unique ``idempotency_key`` on both
the ledger row and the intent drives double-submit protection).
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    Agent,
    ProviderProfile,
    PurchaseIntent,
    PurchaseIntentStatus,
    ServiceListing,
    ListingStatus,
    TaskRun,
    Transaction,
    TransactionStatus,
)
from app.services.payment_flow import (
    attempt_execution,
    create_or_get_tx,
    evaluate_payment,
    mark_approval_required,
    mark_rejected,
    service_category_to_policy,
    transaction_to_dict,
)
from app.services.payment_service import payment_service
from app.services.provider_adapters import (
    ProviderAdapterError,
    build_adapter,
)

logger = logging.getLogger(__name__)


def _load_json(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


class PurchaseService:
    # ------------------------------------------------------------------ utils
    def get_listing(self, db: Session, listing_id: int) -> ServiceListing:
        listing = (
            db.query(ServiceListing)
            .filter(ServiceListing.id == listing_id)
            .first()
        )
        if listing is None:
            raise ProviderAdapterError(f"Listing {listing_id} not found.")
        provider = listing.provider
        if listing.status != ListingStatus.active:
            raise ProviderAdapterError(f"Listing '{listing.name}' is not active.")
        if provider is None or provider.status.value != "active":
            raise ProviderAdapterError("The provider of this listing is not active.")
        return listing

    def search(
        self,
        db: Session,
        category: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict]:
        rows = (
            db.query(ServiceListing)
            .join(ServiceListing.provider)
            .filter(
                ServiceListing.status == ListingStatus.active,
                ProviderProfile.status == "active",
            )
            .order_by(ServiceListing.category, ServiceListing.name)
            .all()
        )
        out = []
        for l in rows:
            if category and l.category.value != category:
                continue
            if query and query.lower() not in (
                f"{l.name} {l.description or ''}".lower()
            ):
                continue
            out.append(self.listing_summary(l))
        return out

    def listing_summary(self, listing: ServiceListing) -> dict:
        return {
            "listing_id": listing.id,
            "name": listing.name,
            "description": listing.description,
            "category": listing.category.value,
            "price": float(listing.price),
            "currency": listing.currency,
            "requires_payment": listing.requires_payment,
            "provider_id": listing.provider.id,
            "provider_name": listing.provider.name,
            "provider_wallet_address": listing.provider.wallet_address,
            "parameters": _load_json(listing.parameters, {}),
        }

    # ---------------------------------------------------------------- quoting
    def create_quote(
        self,
        db: Session,
        agent: Agent,
        listing: ServiceListing,
        payload: Dict[str, Any],
        task_run_id: Optional[int] = None,
    ) -> PurchaseIntent:
        """Validate the payload against the listing's adapter and store the
        provider's real quote on a fresh purchase intent. No money moves."""
        adapter = build_adapter(listing.provider.adapter)
        quote = adapter.quote(listing, payload, api_base_url=listing.provider.api_base_url)

        intent = PurchaseIntent(
            agent_id=agent.id,
            user_id=agent.user_id,
            task_run_id=task_run_id,
            provider_id=listing.provider_id,
            listing_id=listing.id,
            status=PurchaseIntentStatus.quoting,
            request_payload=json.dumps(payload, default=str),
            quote=json.dumps(quote.to_dict(), default=str),
            amount=Decimal(str(quote.amount)),
            idempotency_key=f"purchase:{agent.id}:{listing.id}:{task_run_id or 'task'}",
        )
        db.add(intent)
        db.commit()
        db.refresh(intent)
        logger.info("quote created intent=%s agent=%s listing=%s", intent.id, agent.id, listing.id)
        return intent

    # --------------------------------------------------------------- submit
    def submit(self, db: Session, agent: Agent, intent_id: int) -> dict:
        """Advance a quoted intent through policy -> payment -> provider result.
        Idempotent per intent: repeating after completion returns the result."""
        intent = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.id == intent_id, PurchaseIntent.agent_id == agent.id)
            .with_for_update()
            .first()
        )
        if intent is None:
            raise ProviderAdapterError("Purchase intent not found for this agent.")

        if intent.status != PurchaseIntentStatus.quoting:
            # Already advanced (approval-paused / done / failed) — report as-is,
            # never re-pay.
            return self._outcome_for_intent(db, agent, intent)

        listing = self.get_listing(db, intent.listing_id)
        amount = float(intent.amount or listing.price)
        if amount <= 0:
            raise ProviderAdapterError("Invalid purchase amount.")

        tx, _created = create_or_get_tx(
            db,
            agent,
            amount=amount,
            category=service_category_to_policy(listing.category),
            recipient_address=listing.provider.wallet_address,
            recipient_name=f"{listing.provider.name} — {listing.name}",
            description=f"Purchase {listing.name} ({listing.category.value})",
            idempotency_key=f"purchase-tx:{intent.id}",
        )

        result = evaluate_payment(
            db,
            agent,
            amount=amount,
            category=service_category_to_policy(listing.category),
            recipient_address=listing.provider.wallet_address,
            recipient_name=f"{listing.provider.name} — {listing.name}",
            transaction_id=tx.id,
        )
        checks = [c for c in result.checks]
        if result.risk_score is not None:
            tx.risk_score = result.risk_score
            tx.risk_level = result.risk_level or "low"

        if result.requires_approval:
            mark_approval_required(db, tx)
            intent.transaction_id = tx.id
            intent.status = PurchaseIntentStatus.pending_approval
            db.commit()
            return {
                "outcome": "approval_required",
                "approved": False,
                "blocked": False,
                "intent_id": intent.id,
                "reason": result.reason,
                "checks": checks,
                "transaction": transaction_to_dict(tx),
            }

        if not result.allowed:
            mark_rejected(db, tx, result.reason)
            intent.transaction_id = tx.id
            intent.status = PurchaseIntentStatus.failed
            intent.error = result.reason
            db.commit()
            return {
                "outcome": "blocked",
                "approved": False,
                "blocked": True,
                "intent_id": intent.id,
                "reason": result.reason,
                "checks": checks,
                "transaction": transaction_to_dict(tx),
            }

        # Policy approved — auto-pay through the canonical pipeline.
        executed = attempt_execution(
            db,
            agent,
            tx,
            to_name=f"{listing.provider.name} — {listing.name}",
            memo=f"Agent purchase {listing.name}",
        )
        intent.transaction_id = tx.id
        self._finish_after_payment(db, intent, executed["transaction"])
        return {
            "outcome": "completed" if executed["executed"] else "failed",
            "approved": True,
            "blocked": False,
            "intent_id": intent.id,
            "reason": executed["reason"],
            "checks": checks,
            "transaction": transaction_to_dict(executed["transaction"]),
            "intent": self._intent_dict(intent),
        }

    def _finish_after_payment(
        self, db: Session, intent: PurchaseIntent, tx: Transaction
    ) -> None:
        """After the ledger payment executes, call the real provider and persist
        the verified result. If the payment did not execute, the intent fails
        honestly (never a fake result)."""
        if tx.status != TransactionStatus.executed:
            intent.status = PurchaseIntentStatus.failed
            intent.error = tx.rejection_reason or "Payment did not execute."
            intent.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(intent)
            return

        intent.status = PurchaseIntentStatus.awaiting_provider
        db.commit()

        provider = intent.provider
        listing = intent.listing
        try:
            adapter = build_adapter(provider.adapter)
            payload = _load_json(intent.request_payload, {})
            proof = {
                "tx_hash": tx.tx_hash,
                "mode": "mock" if payment_service.is_mock else "solana",
                "simulated": payment_service.is_mock,
                "explorer_url": None,
            }
            pr = adapter.execute(
                listing,
                payload,
                proof,
                api_base_url=provider.api_base_url,
            )
        except ProviderAdapterError as e:
            pr = None
            intent.status = PurchaseIntentStatus.failed
            intent.error = f"Provider refused the purchase: {e}"
        except Exception as e:  # noqa: BLE001
            logger.error("provider execute raised intent=%s: %s", intent.id, e)
            intent.status = PurchaseIntentStatus.failed
            intent.error = "Provider execution failed unexpectedly."

        if pr is not None and pr.ok:
            intent.result = json.dumps(pr.to_dict(), default=str)
            intent.provider_ref = pr.provider_ref
            intent.status = PurchaseIntentStatus.completed
        elif pr is not None:
            intent.result = json.dumps(pr.to_dict(), default=str)
            intent.status = PurchaseIntentStatus.failed
            intent.error = pr.error or "Provider execution failed."
        intent.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(intent)

    # ------------------------------------------------------------- approvals
    def resume_after_payment(
        self, db: Session, tx: Transaction
    ) -> Optional[PurchaseIntent]:
        """Called by the human-approval endpoint after the payment executes.
        Finds the linked purchase and completes provider fulfilment."""
        intent = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.transaction_id == tx.id)
            .with_for_update()
            .first()
        )
        if intent is None:
            return None
        if intent.status in (
            PurchaseIntentStatus.completed,
            PurchaseIntentStatus.failed,
            PurchaseIntentStatus.cancelled,
        ):
            return intent
        if intent.status == PurchaseIntentStatus.pending_approval:
            self._finish_after_payment(db, intent, tx)
        self.finalize_run(db, intent)
        return intent

    # -------------------------------------------------------------------- run
    def finalize_run(self, db: Session, intent: PurchaseIntent) -> None:
        """Reflect a purchase's terminal outcome onto its agent run."""
        if not intent.task_run_id:
            return
        run = db.query(TaskRun).filter(TaskRun.id == intent.task_run_id).first()
        if run is None:
            return
        memory = _load_json(run.memory, {})
        memory.setdefault("purchases", []).append(
            {
                "intent_id": intent.id,
                "listing": intent.listing.name if intent.listing else None,
                "status": intent.status.value,
                "amount": float(intent.amount or 0),
            }
        )
        run.memory = json.dumps(memory)
        if run.status == "waiting_for_approval":
            if intent.status == PurchaseIntentStatus.completed:
                run.status = "completed"
                run.result = self._completion_summary(intent)
                run.completed_at = datetime.now(timezone.utc)
            elif intent.status == PurchaseIntentStatus.failed:
                run.status = "failed"
                run.error = intent.error
                run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    @staticmethod
    def _completion_summary(intent: PurchaseIntent) -> str:
        result = _load_json(intent.result, {})
        data = result.get("data", {}) if isinstance(result, dict) else {}
        translated = data.get("translated_text")
        run_id = f" run #{intent.task_run_id}" if intent.task_run_id else ""
        if translated:
            return (
                f"PURCHASE COMPLETED{run_id}: paid {float(intent.amount or 0):.4f} USDC "
                f"to {intent.provider.name} for '{intent.listing.name}'. "
                f"Result: {translated}"
            )
        return (
            f"PURCHASE COMPLETED{run_id}: paid {float(intent.amount or 0):.4f} USDC "
            f"to {intent.provider.name} for '{intent.listing.name}'."
        )

    # ---------------------------------------------------------------- status
    def status(self, db: Session, intent_id: int) -> dict:
        intent = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.id == intent_id)
            .first()
        )
        if intent is None:
            raise ProviderAdapterError("Purchase intent not found.")
        return self._intent_dict(intent)

    def _intent_dict(self, intent: PurchaseIntent) -> dict:
        return {
            "id": intent.id,
            "agent_id": intent.agent_id,
            "task_run_id": intent.task_run_id,
            "listing_id": intent.listing_id,
            "listing_name": intent.listing.name if intent.listing else None,
            "provider_id": intent.provider_id,
            "provider_name": intent.provider.name if intent.provider else None,
            "status": intent.status.value,
            "amount": float(intent.amount or 0),
            "transaction_id": intent.transaction_id,
            "request_payload": _load_json(intent.request_payload, {}),
            "quote": _load_json(intent.quote, {}),
            "result": _load_json(intent.result, None),
            "error": intent.error,
            "created_at": intent.created_at.isoformat() if intent.created_at else None,
            "completed_at": intent.completed_at.isoformat() if intent.completed_at else None,
        }

    def _outcome_for_intent(self, db: Session, agent: Agent, intent: PurchaseIntent) -> dict:
        """Idempotent re-report of an intent that already left ``quoting``."""
        base = {"intent_id": intent.id, "approved": False, "blocked": False}
        if intent.status == PurchaseIntentStatus.pending_approval:
            return {**base, "outcome": "approval_required", "reason": "Awaiting human approval."}
        if intent.status == PurchaseIntentStatus.completed:
            return {
                **base,
                "outcome": "completed",
                "approved": True,
                "intent": self._intent_dict(intent),
            }
        if intent.status == PurchaseIntentStatus.failed:
            return {**base, "outcome": "failed", "reason": intent.error}
        return {**base, "outcome": intent.status.value}


purchase_service = PurchaseService()