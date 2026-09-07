"""
One-click demo scenarios for live hackathon demos.

Each scenario auto-provisions a deterministic demo user + "ResearchBot" agent
(no wallet connection needed), configures the agent's policy for the specific
control we want to demonstrate, funds it with $100, runs the REAL policy engine
and payment path (mock USDC when not configured), and returns a full execution
trace the frontend renders as a timeline.

When ``DEMO_MODE`` is off, these endpoints refuse to run so a live deployment is
never accidentally exercised by demo data.

Every transaction produced here is explicitly labelled ``simulated=True`` /
``mode="mock"`` in mock mode and carries an ``idempotency_key`` so a repeated
POST (double-click) returns the existing result instead of paying twice.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Agent,
    AgentStatus,
    Policy,
    PolicyCategory,
    ServiceDirectory,
    Transaction,
    TransactionStatus,
    User,
)
from app.services.errors import AIBankError
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

DEMO_WALLET = "DemoWallet11111111111111111111111111111111"
RESEARCH_BOT_NAME = "ResearchBot"
STARTING_BALANCE = 100.0

# Each scenario is a full circle of the agent -> bank -> policy -> USDC -> API
# flow, configured so a specific control is what decides the outcome.
SCENARIOS: Dict[str, Dict[str, Any]] = {
    "success": {
        "title": "Autonomous purchase",
        "badge": "AUTO-APPROVED",
        "task": "Find the fastest Solana RPC provider and buy 100 requests.",
        "service": "Solana RPC API",
        "amount": 0.02,
        # below per-tx limit AND below the approval threshold -> auto-approved
        "max_per_transaction": 20.0,
        "require_approval_above": 20.0,
        "outcome": "completed",
        "summary": (
            "RECOMMENDATION: Solana RPC API. The agent negotiated, paid "
            "($0.02 USDC, simulated) and received a working endpoint — approved "
            "by the policy engine in under a second, no human needed."
        ),
    },
    "blocked-spend": {
        "title": "Per-transaction limit",
        "badge": "POLICY BLOCK",
        "task": "Purchase $50 of premium market data to price a token.",
        "service": "Premium Data API",
        "amount": 50.0,
        # $50 busts the $20 per-tx cap -> blocked before any money moves
        "max_per_transaction": 20.0,
        "require_approval_above": 20.0,
        "outcome": "blocked",
        "suggestion": (
            "The agent could keep searching for a cheaper provider inside its "
            "$20 per-transaction budget instead of forcing the payment."
        ),
    },
    "blocked-transfer": {
        "title": "Human transfer blocked",
        "badge": "NO HUMAN TRANSFERS",
        "task": "Transfer $15 to the agent's owner to cover coffee.",
        "service": "My personal wallet",
        "amount": 15.0,
        "recipient_address": "unknown_human_wallet_9f3k2m1q",
        "recipient_name": "Suspicious human wallet",
        # amount is fine ($15 < $20) but the recipient is unknown -> blocked
        "max_per_transaction": 20.0,
        "require_approval_above": 20.0,
        "outcome": "blocked",
        "suggestion": (
            "Agents cannot move money to arbitrary human wallets. The agent "
            "should only pay whitelisted providers."
        ),
    },
    "approval": {
        "title": "Human approval",
        "badge": "APPROVAL REQUIRED",
        "task": "Buy a $75 deep-research report from the Web Search API.",
        "service": "Web Search API",
        "amount": 75.0,
        # within the $100 per-tx budget BUT above the $20 approval threshold
        "max_per_transaction": 100.0,
        "require_approval_above": 20.0,
        "outcome": "approval_required",
        "suggestion": (
            "Click 'Approve payment' to authorise it as the human. The bank "
            "then executes the USDC payment the agent proposed."
        ),
    },
}


def scenario_spec(scenario_id: str) -> Dict[str, Any]:
    spec = SCENARIOS.get(scenario_id)
    if spec is None:
        raise AIBankError(
            detail=(
                f"Unknown demo scenario '{scenario_id}'. "
                f"Available: {', '.join(sorted(SCENARIOS))}."
            )
        )
    return spec


def scenario_enabled() -> bool:
    return settings.DEMO_MODE


def ensure_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.wallet_address == DEMO_WALLET).first()
    if user is None:
        user = User(wallet_address=DEMO_WALLET)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def reset_research_bot(
    db: Session, spec: Dict[str, Any], *, wipe_history: bool = True
) -> Agent:
    """
    Find or create the demo agent and reset its funds + policy deterministically
    so every run behaves identically for the audience.

    ``wipe_history`` removes the demo agent's previous demo transactions so the
    daily-limit counter starts clean and the trace tells one clear story. The
    agent is an auto-provisioned demo entity, so this never touches real data.
    """
    user = ensure_demo_user(db)
    agent = db.query(Agent).filter(Agent.name == RESEARCH_BOT_NAME).first()
    if agent is None:
        agent = Agent(
            name=RESEARCH_BOT_NAME,
            description=(
                "Auto-provisioned demo agent that pays real (mock) USDC for "
                "marketplace services within policy limits."
            ),
            user_id=user.id,
            balance=Decimal(str(STARTING_BALANCE)),
            total_spent=Decimal("0"),
            status=AgentStatus.active,
            violation_count=0,
        )
        db.add(agent)
        db.flush()
        policy = Policy(
            agent_id=agent.id,
            user_id=user.id,
            max_per_transaction=Decimal(str(spec["max_per_transaction"])),
            max_per_day=Decimal("100.00"),
            max_per_month=Decimal("1000.00"),
            allowed_categories="[\"api\", \"compute\", \"data\", \"agent\"]",
            blocked_human_transfers=True,
            blocked_withdrawals=True,
            blocked_arbitrary_contracts=True,
            require_approval_above=Decimal(str(spec["require_approval_above"])),
            allowed_recipient_addresses="[]",  # trusted providers resolve via registry
        )
        db.add(policy)
        db.commit()
        db.refresh(agent)
        return agent

    if wipe_history and agent.transactions:
        for tx in list(agent.transactions):
            db.delete(tx)
        db.flush()

    # Reset funds + policy for determinism on re-runs.
    agent.balance = Decimal(str(STARTING_BALANCE))
    agent.total_spent = Decimal("0")
    agent.status = AgentStatus.active
    policy = agent.policies
    if policy is None:
        policy = Policy(agent_id=agent.id, user_id=user.id)
        db.add(policy)
    policy.max_per_transaction = Decimal(str(spec["max_per_transaction"]))
    policy.max_per_day = Decimal("100.00")
    policy.max_per_month = Decimal("1000.00")
    policy.allowed_categories = '["api", "compute", "data", "agent"]'
    policy.blocked_human_transfers = True
    policy.blocked_withdrawals = True
    policy.blocked_arbitrary_contracts = True
    policy.require_approval_above = Decimal(str(spec["require_approval_above"]))
    policy.allowed_recipient_addresses = "[]"
    db.commit()
    db.refresh(agent)
    return agent


def _find_service(db: Session, spec: Dict[str, Any]) -> Optional[ServiceDirectory]:
    name = spec.get("service")
    if name == "My personal wallet":
        return None
    service = db.query(ServiceDirectory).filter(ServiceDirectory.name == name).first()
    if service is None:
        service = (
            db.query(ServiceDirectory)
            .filter(ServiceDirectory.is_demo == True)  # noqa: E712
            .first()
        )
    return service


def _recipient_for(
    db: Session, agent: Agent, spec: Dict[str, Any]
):
    service = _find_service(db, spec)
    if service is not None:
        return (
            service,
            service.wallet_address,
            service.name,
            service_category_to_policy(service.category),
        )
    return (
        None,
        spec.get("recipient_address", "unknown_human_wallet"),
        spec.get("recipient_name", "Unknown human wallet"),
        PolicyCategory.data,
    )


def _tx_idempotency_key(scenario_id: str, client_request_id: Optional[str]) -> str:
    tag = client_request_id or "default"
    return f"demo:{scenario_id}:{tag}"


def _tx_to_result(
    db: Session,
    scenario_id: str,
    spec: Dict[str, Any],
    agent: Agent,
    tx: Transaction,
) -> Dict[str, Any]:
    """Build the full DemoResult-shaped response from a persisted transaction."""
    now = datetime.now(timezone.utc).isoformat()
    task = spec["task"]
    amount = float(tx.amount)
    service = _find_service(db, spec)
    service_name = service.name if service else tx.recipient_name or tx.recipient_address

    def step(key, label, detail, state):
        return {"key": key, "label": label, "detail": detail, "t": now, "state": state}

    trace = [
        step("task", "TASK STARTED", task, "done"),
        step("discover", "API DISCOVERED", f"{service_name}", "done"),
        step("required", "PAYMENT REQUIRED", f"402 · USDC {amount:.2f}", "active"),
    ]

    outcome = "completed"
    if tx.status == TransactionStatus.rejected:
        outcome = "blocked"
    elif tx.status == TransactionStatus.approved:
        outcome = "approval_required"
    elif tx.status == TransactionStatus.failed:
        outcome = "failed"
    elif tx.status != TransactionStatus.executed:
        outcome = "pending"

    reason = tx.rejection_reason

    if outcome in ("blocked", "failed"):
        trace.append(
            step("policy", "POLICY CHECK", f"{amount:.2f} USDC requested", "active")
        )
        trace.append(
            step("blocked", "BLOCKED", reason or "Refused by policy engine", "error")
        )
    elif outcome == "approval_required":
        trace.append(
            step("policy", "POLICY CHECK", "Requires human approval", "error")
        )
        trace.append(
            step(
                "approval",
                "WAITING FOR APPROVAL",
                f"{amount:.2f} USDC paused for human sign-off",
                "error",
            )
        )
    else:  # executed / completed / pending
        trace.append(
            step("policy", "POLICY CHECK", "All checks passed", "done")
        )
        trace.append(
            step("approved", "APPROVED", f"{amount:.2f} USDC within policy", "success")
        )
        if tx.status == TransactionStatus.executed:
            trace.append(
                step(
                    "payment",
                    "USDC PAYMENT",
                    f"{amount:.2f} USDC · {tx.tx_hash}",
                    "done",
                )
            )
            trace.append(
                step(
                    "confirmed",
                    "SOLANA CONFIRMED",
                    "Confirmed (simulated)" if payment_service.is_mock else "Confirmed on-chain",
                    "success",
                )
            )
            trace.append(
                step("response", "API RESPONSE", f"{service_name} returned data", "done")
            )
            trace.append(
                step("complete", "TASK COMPLETED", "Recommendation produced", "success")
            )
        else:
            trace.append(step("pending", "AWAITING EXECUTION", "No money moved yet", "active"))

    result: Dict[str, Any] = {
        "scenario": scenario_id,
        "scenario_title": spec["title"],
        "scenario_badge": spec["badge"],
        "task": task,
        "flow": outcome,
        "approved": outcome == "completed",
        "trace": trace,
        "checks": [],  # filled below when we re-evaluate deterministically
        "transaction": transaction_to_dict(tx),
        "agent": {"id": agent.id, "name": agent.name, "balance": float(agent.balance)},
        "demo_wallet": DEMO_WALLET,
        "can_approve": outcome == "approval_required",
        "suggestion": spec.get("suggestion"),
        "summary": spec.get("summary") if outcome == "completed" else None,
    }
    if service is not None:
        result["service"] = {
            "id": service.id,
            "name": service.name,
            "category": service.category.value,
            "price": float(service.price),
            "is_demo": service.is_demo,
        }

    # Re-run the deterministic engine for a consistent "checks" panel.
    policy_result = evaluate_payment(
        db,
        agent,
        amount=amount,
        category=tx.category or PolicyCategory.api,
        recipient_address=tx.recipient_address,
        recipient_name=tx.recipient_name,
        transaction_id=tx.id,
    )
    result["checks"] = policy_result.checks
    if reason is None and outcome in ("blocked", "failed"):
        result["reason"] = policy_result.reason or reason
    elif reason:
        result["reason"] = reason

    if outcome == "completed" and tx.tx_hash:
        result["proof"] = {
            "tx_hash": tx.tx_hash,
            "mode": "mock" if payment_service.is_mock else "solana",
            "simulated": payment_service.is_mock,
            "explorer_url": None,
        }
    return result


def run_scenario(
    db: Session, scenario_id: str, client_request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run one demo scenario to completion (or to its natural hold point) and return
    a full trace. Idempotent per ``client_request_id``.
    """
    spec = scenario_spec(scenario_id)
    if not scenario_enabled():
        raise AIBankError(
            status_code=403,
            code="demo_mode_disabled",
            detail=(
                "DEMO_MODE is off. Set DEMO_MODE=true (or leave it blank) to run "
                "the one-click demo scenarios."
            ),
        )

    agent = reset_research_bot(db, spec)
    service, recipient_address, recipient_name, category = _recipient_for(db, agent, spec)
    amount = float(spec["amount"])
    idem_key = _tx_idempotency_key(scenario_id, client_request_id)

    tx, created = create_or_get_tx(
        db,
        agent,
        amount=amount,
        category=category,
        recipient_address=recipient_address,
        recipient_name=recipient_name,
        description=spec["task"],
        idempotency_key=idem_key,
    )
    if not created:
        return _tx_to_result(db, scenario_id, spec, agent, tx)

    decision = evaluate_payment(
        db,
        agent,
        amount=amount,
        category=category,
        recipient_address=recipient_address,
        recipient_name=recipient_name,
        transaction_id=tx.id,
    )

    if not decision.allowed and not decision.requires_approval:
        mark_rejected(db, tx, decision.reason)
        return _tx_to_result(db, scenario_id, spec, agent, tx)

    if decision.requires_approval:
        mark_approval_required(db, tx)
        return _tx_to_result(db, scenario_id, spec, agent, tx)

    # Auto-approved: execute immediately.
    executed = attempt_execution(
        db, agent, tx, to_name=recipient_name, memo=f"Demo: {spec['task']}"
    )
    return _tx_to_result(db, scenario_id, spec, agent, executed["transaction"])


def approve_pending_scenario(
    db: Session, scenario_id: str, client_request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Approve + execute the payment that a scenario paused for human approval.
    Idempotent: if the transaction is already executed this simply returns it.
    """
    spec = scenario_spec(scenario_id)
    if not scenario_enabled():
        raise AIBankError(
            status_code=403,
            code="demo_mode_disabled",
            detail="DEMO_MODE is off; demo approvals are unavailable.",
        )

    idem_key = _tx_idempotency_key(scenario_id, client_request_id)
    tx = db.query(Transaction).filter(Transaction.idempotency_key == idem_key).first()
    if tx is None or tx.agent is None:
        raise AIBankError(
            code="scenario_not_run",
            detail=(
                f"No pending transaction for scenario '{scenario_id}'. Run the "
                "scenario first, then approve."
            ),
        )

    agent = reset_research_bot(db, spec, wipe_history=False)
    agent.balance = Decimal(str(STARTING_BALANCE))
    agent.total_spent = Decimal("0")
    db.commit()

    if tx.status in (TransactionStatus.executed, TransactionStatus.failed):
        # Already settled (double-click approve) — never double-pay.
        return _tx_to_result(db, scenario_id, spec, agent, tx)

    if tx.status == TransactionStatus.rejected:
        raise AIBankError(
            code="already_rejected",
            detail="This payment was blocked by policy and can no longer be approved.",
        )

    executed = attempt_execution(
        db, agent, tx, to_name=tx.recipient_name, memo=f"Approved demo: {spec['task']}"
    )
    return _tx_to_result(db, scenario_id, spec, agent, executed["transaction"])