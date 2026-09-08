"""
Marketplace / Service Directory router.

Implements the simplified, self-labelled x402-style payment flow for
autonomous commerce:

    HTTP request
        -> 402 Payment Required (service says "payment_required")
        -> payment info
        -> Agent Bank executes policy check
        -> USDC payment
        -> retry request with payment proof
        -> API response

This is a *** simplified demo implementation ***. It mirrors the shape of the
x402 protocol (402 status + payment requirement + proof-of-payment retry) but
it is NOT wire-compatible with the real x402 standard. It is labelled as such
so we never claim compliance we don't have.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api import deps as auth_deps
from sqlalchemy.orm import Session

from app.api.dependencies.limiter import RateLimiter
from app.core.config import settings
from app.db.session import get_db
from app.db.models import (
    Agent,
    AgentStatus,
    Transaction,
    TransactionStatus,
    ServiceDirectory,
    ServiceCategory,
)
from app.schemas import ServiceOut, ServiceRequestIn, ServicePaymentIn, ServiceRunIn
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["marketplace"])

payment_limiter = RateLimiter(limit=30, window_seconds=60, prefix="service-payment")
demo_limiter = RateLimiter(limit=20, window_seconds=60, prefix="service-demo")


def _service_to_out(s: ServiceDirectory) -> ServiceOut:
    return ServiceOut(
        id=s.id,
        name=s.name,
        description=s.description,
        category=s.category.value,
        endpoint=s.endpoint,
        wallet_address=s.wallet_address,
        price=float(s.price),
        currency=s.currency,
        requires_payment=s.requires_payment,
        active=s.active,
        risk_level=s.risk_level.value,
        is_demo=s.is_demo,
    )


def _get_agent(db: Session, agent_id: int) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != AgentStatus.active:
        raise HTTPException(status_code=400, detail=f"Agent is {agent.status.value}")
    return agent


def _require_agent_owner(
    authorization: Optional[str],
    db: Session,
    agent_id: int,
) -> str:
    """Bind a marketplace agent-spend call to the agent's authenticated owner.

    Closes the cross-tenant IDOR (was: any caller who knew an ``agent_id`` could
    drain an agent that only had to be ``active``). When ``REQUIRE_AUTH`` is on,
    the caller must present a Bearer token for the wallet that owns the agent.
    The ``_get_agent`` active + owner-active checks still apply for the policy
    gate; this is the authorization gate.
    """
    owner_wallet = auth_deps.get_authenticated_wallet(authorization)
    if not owner_wallet:
        return ""  # auth off (staging/demo)
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    owner = agent.user
    if owner is None or owner.wallet_address != owner_wallet:
        raise HTTPException(
            status_code=403,
            detail="This agent does not belong to the authenticated wallet.",
        )
    return owner_wallet


def _get_service(db: Session, service_id: int) -> ServiceDirectory:
    service = db.query(ServiceDirectory).filter(ServiceDirectory.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if not service.active:
        raise HTTPException(status_code=400, detail="Service is inactive")
    if service.is_demo and not settings.DEMO_MODE:
        # Demo listings carry fake wallet addresses; never offer them in real mode.
        raise HTTPException(status_code=404, detail="Service not found")
    return service


def _create_pending_tx(
    db: Session,
    agent: Agent,
    service: ServiceDirectory,
    amount: float,
    description: str,
    idempotency_key: Optional[str] = None,
) -> tuple[Transaction, bool]:
    """Create a pending purchase tx (or return the deduplicated existing one)."""
    key = idempotency_key or f"mkt:{agent.id}:{service.id}:{amount:.6f}"
    return create_or_get_tx(
        db,
        agent,
        amount=amount,
        category=service_category_to_policy(service.category),
        recipient_address=service.wallet_address,
        recipient_name=service.name,
        description=description,
        idempotency_key=key,
    )


def _tx_to_dict(tx: Transaction):
    return transaction_to_dict(tx)


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    """List the service directory.

    Includes demo services, clearly flagged, in DEMO_MODE. In real mode the
    demo listings (fake wallet addresses) are excluded so a real agent can
    never be offered a pay route that doesn't exist on-chain.
    """
    query = db.query(ServiceDirectory)
    if not settings.DEMO_MODE:
        query = query.filter(ServiceDirectory.is_demo.is_(False))
    services = query.order_by(ServiceDirectory.category, ServiceDirectory.id).all()
    return [_service_to_out(s) for s in services]


@router.get("/categories")
def list_categories():
    return {"categories": [c.value for c in ServiceCategory]}


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = _get_service(db, service_id)
    return _service_to_out(service)


# ---------------------------------------------------------------------------
# x402-style request flow
# ---------------------------------------------------------------------------
@router.post("/{service_id}/request")
def request_service(
    service_id: int,
    payload: ServiceRequestIn,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    Agent requests a service. This is step 1 of the x402-style flow.

    * If the service requires payment, we respond with status ``payment_required``
      and the payment information the Agent Bank needs to settle it
      (an HTTP 402 Payment Required in spirit — see note below).
    * If the service is free, we respond with a result directly.

    NOTE: real x402 returns literal HTTP status 402 with specific headers. This
    demo returns a JSON body with ``payment_required=true`` instead, and is NOT
    wire-compatible with x402. See the module docstring.
    """
    _require_agent_owner(authorization, db, payload.agent_id)
    _get_agent(db, payload.agent_id)  # ensure agent exists + is active
    service = _get_service(db, service_id)

    # Free service path — no payment needed.
    if not service.requires_payment or float(service.price) == 0:
        return {
            "status": "ok",
            "service_id": service.id,
            "service_name": service.name,
            "payment_required": False,
            "demo": service.is_demo,
            "result": {
                "ok": True,
                "data": {
                    "source": "demo" if service.is_demo else "live",
                    "note": (
                        "DEMO SERVICE — simulated response."
                        if service.is_demo
                        else "Live response."
                    ),
                },
            },
        }

    # Paid service path — return the payment requirement so the Agent Bank can
    # evaluate policy and execute the USDC payment.
    return {
        "status": "payment_required",
        "http_status_hint": 402,  # the semantic of HTTP 402 Payment Required
        "x402_note": (
            "Simplified x402-style demo. Not wire-compatible with the real "
            "x402 standard."
        ),
        "service_id": service.id,
        "service_name": service.name,
        "payment_required": True,
        "demo": service.is_demo,
        "payment_info": {
            "amount": float(service.price),
            "currency": service.currency,
            "recipient_address": service.wallet_address,
            "recipient_name": service.name,
            "category": service.category.value,
            "endpoint": service.endpoint,
        },
    }


@router.post("/{service_id}/payment")
def pay_for_service(
    service_id: int,
    payload: ServicePaymentIn,
    db: Session = Depends(get_db),
    _: None = Depends(payment_limiter),
    authorization: Optional[str] = Header(None),
):
    """
    Agent Bank settles the payment for a paid service request.

    The policy engine evaluates the amount against the agent's policy first.
    Only if it passes do we actually execute the USDC payment. This is the
    "can the agent spend this?" gate — autonomous but never uncontrolled.

    Idempotent: repeating the same (agent, service, amount) payment returns the
    existing result and NEVER double-pays.
    """
    _require_agent_owner(authorization, db, payload.agent_id)
    agent = _get_agent(db, payload.agent_id)
    service = _get_service(db, service_id)

    amount = float(payload.requested_amount or service.price)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    tx, created = _create_pending_tx(
        db,
        agent,
        service,
        amount,
        description=f"Purchase {service.name} ({service.category.value})",
    )

    if not created:
        # Dedupe hit (double-submit): re-evaluate for the checks panel, but
        # never move money again — return the outcome the tx already has.
        return _outcome_for_existing_tx(db, agent, service, tx)

    policy_category = service_category_to_policy(service.category)
    result = evaluate_payment(
        db,
        agent,
        amount=amount,
        category=policy_category,
        recipient_address=service.wallet_address,
        recipient_name=service.name,
        transaction_id=tx.id,
    )

    checks = [c for c in result.checks]

    # Persist the deterministic risk score onto the ledger row so the
    # UI/history exposes exactly how risky a payment was judged to be.
    if result.risk_score is not None:
        tx.risk_score = result.risk_score
        tx.risk_level = result.risk_level or "low"

    # Approval required (human in the loop) takes precedence over the generic
    # blocked branch — the policy engine reports requires_approval with allowed=False.
    if result.requires_approval:
        mark_approval_required(db, tx)
        return {
            "status": "approval_required",
            "approved": False,
            "requires_approval": True,
            "checks": checks,
            "transaction": _tx_to_dict(tx),
        }

    # Blocked by policy — the agent cannot pay uncontrolled amounts.
    if not result.allowed:
        mark_rejected(db, tx, result.reason)
        return {
            "status": "blocked",
            "payment_required": True,
            "approved": False,
            "blocked": True,
            "reason": result.reason,
            "checks": checks,
            "transaction": _tx_to_dict(tx),
            "suggestion": (
                "The agent could continue searching for another, cheaper service "
                "within its spending limits."
            ),
        }

    # Approved — execute the USDC payment (with a balance check first).
    executed = attempt_execution(
        db, agent, tx, to_name=service.name, memo=f"Purchase {service.name}"
    )

    if not executed["executed"]:
        return {
            "status": "failed",
            "approved": True,
            "blocked": False,
            "reason": executed["reason"],
            "checks": checks,
            "transaction": _tx_to_dict(executed["transaction"]),
        }

    return {
        "status": "paid",
        "approved": True,
        "payment_required": True,
        "checks": checks,
        "proof": executed["proof"],
        "transaction": _tx_to_dict(executed["transaction"]),
        "service": _service_to_out(service),
        "retry_with_proof": True,
    }


def _outcome_for_existing_tx(
    db: Session, agent: Agent, service: ServiceDirectory, tx: Transaction
):
    """Build the API response for a previously-created transaction (dedupe path)."""
    policy_category = service_category_to_policy(service.category)
    result = evaluate_payment(
        db,
        agent,
        amount=float(tx.amount),
        category=policy_category,
        recipient_address=tx.recipient_address,
        recipient_name=tx.recipient_name,
        transaction_id=tx.id,
    )
    checks = [c for c in result.checks]

    if tx.status == TransactionStatus.executed:
        return {
            "status": "paid",
            "approved": True,
            "payment_required": True,
            "checks": checks,
            "already_processed": True,
            "proof": {
                "tx_hash": tx.tx_hash,
                "mode": "mock" if payment_service.is_mock else "solana",
                "simulated": payment_service.is_mock,
                "explorer_url": None,
            },
            "transaction": _tx_to_dict(tx),
            "service": _service_to_out(service),
            "retry_with_proof": True,
        }
    if tx.status in (TransactionStatus.rejected, TransactionStatus.failed):
        return {
            "status": "blocked",
            "payment_required": True,
            "approved": False,
            "blocked": True,
            "already_processed": True,
            "reason": tx.rejection_reason or result.reason,
            "checks": checks,
            "transaction": _tx_to_dict(tx),
        }
    # still awaiting human approval (or a pending pre-policy tx)
    return {
        "status": "approval_required",
        "approved": False,
        "requires_approval": True,
        "already_processed": True,
        "checks": checks,
        "transaction": _tx_to_dict(tx),
    }


# ---------------------------------------------------------------------------
# API response after payment proof (retry with proof)
# ---------------------------------------------------------------------------
@router.post("/{service_id}/result")
def get_service_result(
    service_id: int,
    payload: ServiceRunIn,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Agent retries a paid service with its payment proof and gets the result."""
    _require_agent_owner(authorization, db, payload.agent_id)
    agent = _get_agent(db, payload.agent_id)
    service = _get_service(db, service_id)

    # Find the most recent executed payment to this service as the proof.
    proof_tx = (
        db.query(Transaction)
        .filter(
            Transaction.agent_id == agent.id,
            Transaction.recipient_address == service.wallet_address,
            Transaction.status == TransactionStatus.executed,
        )
        .order_by(Transaction.created_at.desc())
        .first()
    )

    if not proof_tx:
        raise HTTPException(
            status_code=402,
            detail="Payment Required — no on-record payment to this service was found.",
        )

    # Payload may carry an explicit proof signature; validate if present.
    explicit = payload.proof or {}
    provided_hash = explicit.get("tx_hash") if isinstance(explicit, dict) else None
    if provided_hash and proof_tx.tx_hash != provided_hash:
        raise HTTPException(status_code=402, detail="Invalid payment proof.")

    return {
        "status": "ok",
        "payment_required": False,
        "demo": service.is_demo,
        "service_id": service.id,
        "service_name": service.name,
        "proof": {
            "tx_hash": proof_tx.tx_hash,
            "verified": True,
        },
        "result": {
            "ok": True,
            "paid": True,
            "amount_paid": float(proof_tx.amount),
            "data": {
                "source": "demo" if service.is_demo else "live",
                "note": (
                    "DEMO SERVICE — simulated response returned after a USDC "
                    "payment."
                    if service.is_demo
                    else "Live service response."
                ),
            },
        },
    }


# ---------------------------------------------------------------------------
# Killer demo + failed-payment demo (single-call orchestration)
# ---------------------------------------------------------------------------
def _run_payment_flow(
    db: Session,
    agent: Agent,
    service: ServiceDirectory,
    requested_amount: float,
    task: str,
):
    """
    Run the full x402-style flow for a service and return a step-by-step trace
    the frontend renders as a beautiful execution timeline.
    """
    trace = []
    now = datetime.now(timezone.utc).isoformat()

    trace.append({"key": "task", "label": "TASK STARTED", "detail": task, "t": now, "state": "done"})
    trace.append(
        {
            "key": "discover",
            "label": "API DISCOVERED",
            "detail": f"{service.name} ({service.category.value})",
            "t": now,
            "state": "done",
        }
    )
    trace.append(
        {
            "key": "required",
            "label": "PAYMENT REQUIRED",
            "detail": f"402 · {service.currency} {requested_amount:.2f}",
            "t": now,
            "state": "active",
        }
    )

    # Policy evaluation (reuse the deterministic engine).
    policy_category = service_category_to_policy(service.category)
    tx, _created = _create_pending_tx(
        db,
        agent,
        service,
        requested_amount,
        description=f"Purchase {service.name} ({service.category.value})",
    )
    result = evaluate_payment(
        db,
        agent,
        amount=requested_amount,
        category=policy_category,
        recipient_address=service.wallet_address,
        recipient_name=service.name,
        transaction_id=tx.id,
    )

    if result.requires_approval:
        mark_approval_required(db, tx)
        trace.append(
            {
                "key": "policy",
                "label": "POLICY CHECK",
                "detail": "Requires human approval",
                "t": now,
                "state": "error",
            }
        )
        return {
            "flow": "approval_required",
            "approved": False,
            "trace": trace,
            "checks": result.checks,
            "reason": result.reason,
            "transaction": _tx_to_dict(tx),
        }

    if not result.allowed:
        mark_rejected(db, tx, result.reason)
        trace.append(
            {
                "key": "policy",
                "label": "POLICY CHECK",
                "detail": f"{requested_amount:.2f} USDC requested",
                "t": now,
                "state": "active",
            }
        )
        trace.append(
            {
                "key": "blocked",
                "label": "BLOCKED",
                "detail": result.reason,
                "t": now,
                "state": "error",
            }
        )
        return {
            "flow": "blocked",
            "approved": False,
            "trace": trace,
            "checks": result.checks,
            "reason": result.reason,
            "transaction": _tx_to_dict(tx),
            "suggestion": (
                "The agent could continue searching for another service within "
                "its spending limits instead of forcing this payment."
            ),
        }

    if result.requires_approval:
        mark_approval_required(db, tx)
        trace.append(
            {
                "key": "policy",
                "label": "POLICY CHECK",
                "detail": "Requires human approval",
                "t": now,
                "state": "error",
            }
        )
        return {
            "flow": "approval_required",
            "approved": False,
            "trace": trace,
            "checks": result.checks,
            "reason": result.reason,
            "transaction": _tx_to_dict(tx),
        }

    trace.append(
        {
            "key": "policy",
            "label": "POLICY CHECK",
            "detail": "All checks passed",
            "t": now,
            "state": "done",
        }
    )
    trace.append(
        {
            "key": "approved",
            "label": "APPROVED",
            "detail": f"{requested_amount:.2f} USDC within policy",
            "t": now,
            "state": "success",
        }
    )

    # Execute the USDC payment (balance-checked, idempotent per key).
    executed = attempt_execution(
        db, agent, tx, to_name=service.name, memo=f"Purchase {service.name}"
    )

    if not executed["executed"]:
        trace.append(
            {
                "key": "payment",
                "label": "USDC PAYMENT",
                "detail": "Execution failed",
                "t": now,
                "state": "error",
            }
        )
        return {
            "flow": "failed",
            "approved": True,
            "trace": trace,
            "checks": result.checks,
            "reason": executed["reason"],
            "transaction": _tx_to_dict(executed["transaction"]),
        }

    tx = executed["transaction"]
    trace.append(
        {
            "key": "payment",
            "label": "USDC PAYMENT",
            "detail": f"{requested_amount:.2f} USDC · {tx.tx_hash}",
            "t": now,
            "state": "done",
        }
    )
    trace.append(
        {
            "key": "confirmed",
            "label": "SOLANA CONFIRMED",
            "detail": "Confirmed (simulated)" if payment_service.is_mock else "Confirmed on-chain",
            "t": now,
            "state": "success",
        }
    )
    trace.append(
        {
            "key": "response",
            "label": "API RESPONSE",
            "detail": f"{service.name} returned data",
            "t": now,
            "state": "done",
        }
    )
    trace.append(
        {
            "key": "complete",
            "label": "TASK COMPLETED",
            "detail": "Recommendation produced",
            "t": now,
            "state": "success",
        }
    )

    return {
        "flow": "completed",
        "approved": True,
        "trace": trace,
        "checks": result.checks,
        "transaction": _tx_to_dict(tx),
        "proof": executed["proof"],
    }


@router.post("/demo/killer")
def killer_demo(
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(demo_limiter),
):
    """
    KILLER DEMO: "Find the best Solana RPC provider and return the recommendation."

    The agent requests the Solana RPC API service, the API requires $0.02, the
    agent asks the bank, the policy engine approves ($0.02 < $20, daily limit
    OK), USDC payment executes, the API responds, and the agent summarizes.

    DEMO_MODE only — a real deployment has no scripted scenarios.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Demo scenarios are disabled.")
    agent_id = payload.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    agent = _get_agent(db, int(agent_id))

    # Locate the Solana RPC API demo service.
    service = (
        db.query(ServiceDirectory)
        .filter(ServiceDirectory.name.ilike("%RPC%"))
        .first()
    )
    if not service:
        service = (
            db.query(ServiceDirectory)
            .filter(ServiceDirectory.category == ServiceCategory.api)
            .first()
        )
    if not service:
        raise HTTPException(status_code=404, detail="No demo RPC service found")

    requested = float(payload.get("requested_amount", 0.02))
    task = (
        "Find the best Solana RPC provider and return the recommendation."
    )

    result = _run_payment_flow(db, agent, service, requested, task)

    if result["flow"] == "completed":
        result["summary"] = (
            "RECOMMENDATION: Solana RPC API. Paid $0.02 USDC (simulated) for a "
            "live endpoint; the provider responds with consistent slot latency "
            "and 99.9% uptime. Recommended for low-cost agent infrastructure."
        )

    result["agent_name"] = agent.name
    result["service"] = _service_to_out(service)
    return result


@router.post("/demo/failed")
def failed_payment_demo(
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(demo_limiter),
):
    """
    FAILED PAYMENT DEMO: agent tries a $50 API payment. The policy engine blocks
    it because max per-transaction is $20. The agent can then continue searching
    for another service — autonomous economic reasoning without uncontrolled
    spending.

    DEMO_MODE only — a real deployment has no scripted scenarios.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Demo scenarios are disabled.")
    agent_id = payload.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    agent = _get_agent(db, int(agent_id))

    service = (
        db.query(ServiceDirectory)
        .filter(ServiceDirectory.name.ilike("%Premium Data%"))
        .first()
    )
    if not service:
        service = (
            db.query(ServiceDirectory)
            .filter(ServiceDirectory.requires_payment == True)  # noqa: E712
            .first()
        )
    if not service:
        raise HTTPException(status_code=404, detail="No demo paid service found")

    requested = float(payload.get("requested_amount", 50.0))
    task = "Purchase premium market data for $50 to price a token."

    result = _run_payment_flow(db, agent, service, requested, task)
    result["agent_name"] = agent.name
    result["service"] = _service_to_out(service)
    result["demo_task"] = task
    return result

