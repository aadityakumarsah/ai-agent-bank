"""
Shared payment-flow helpers for marketplace + demo scenarios + approvals.

This is the single place that:
* creates transaction records (with idempotency-key dedupe so a double-submit
  never double-pays),
* evaluates policy (re-using the deterministic policy engine),
* checks the agent has enough balance BEFORE executing,
* executes the USDC transfer and updates the ledger,
* emits structured logs + audit events.

``marketplace.py`` and ``demo_scenarios.py`` both rely on it so the money paths
behave identically everywhere.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import (
    Agent,
    PolicyCategory,
    ServiceCategory,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.services.audit_service import (
    TRANSACTION_EXECUTED,
    audit_service,
)
from app.services.payment_service import payment_service
from app.services.policy_engine import PolicyEvaluationResult, policy_engine

logger = get_logger("app.payment-flow")


# Map the service-directory categories onto the policy categories the engine
# understands. Additional directory categories (ai_model, storage) fold into
# the closest policy bucket so the existing deterministic policy engine applies.
def service_category_to_policy(category: ServiceCategory) -> PolicyCategory:
    return {
        ServiceCategory.api: PolicyCategory.api,
        ServiceCategory.compute: PolicyCategory.compute,
        ServiceCategory.data: PolicyCategory.data,
        ServiceCategory.ai_model: PolicyCategory.api,
        ServiceCategory.storage: PolicyCategory.data,
        ServiceCategory.other_agent: PolicyCategory.agent,
    }.get(category, PolicyCategory.api)


def find_tx_by_idempotency_key(db: Session, idempotency_key: str) -> Optional[Transaction]:
    if not idempotency_key:
        return None
    return (
        db.query(Transaction)
        .filter(Transaction.idempotency_key == idempotency_key)
        .first()
    )


def transaction_to_dict(tx: Transaction) -> Dict[str, Any]:
    return {
        "id": tx.id,
        "agent_id": tx.agent_id,
        "amount": float(tx.amount),
        "currency": tx.currency,
        "transaction_type": tx.transaction_type.value,
        "recipient_address": tx.recipient_address,
        "recipient_name": tx.recipient_name,
        "category": tx.category.value if tx.category else None,
        "status": tx.status.value,
        "rejection_reason": tx.rejection_reason,
        "tx_hash": tx.tx_hash,
        "description": tx.description,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }


def create_or_get_tx(
    db: Session,
    agent: Agent,
    *,
    amount: float,
    category: PolicyCategory,
    recipient_address: str,
    recipient_name: Optional[str],
    description: str,
    idempotency_key: Optional[str] = None,
    transaction_type: TransactionType = TransactionType.payment,
) -> Tuple[Transaction, bool]:
    """
    Create a pending transaction record, or return the existing one when
    ``idempotency_key`` matches an already-recorded attempt. ``created`` is
    False in the dedupe case — callers must NOT execute the payment twice.
    """
    if idempotency_key:
        existing = find_tx_by_idempotency_key(db, idempotency_key)
        if existing is not None:
            logger.info(
                "idempotency hit for key %s -> tx %s (status=%s)",
                idempotency_key,
                existing.id,
                existing.status.value,
            )
            return existing, False

    tx = Transaction(
        agent_id=agent.id,
        user_id=agent.user_id,
        amount=Decimal(str(amount)),
        transaction_type=transaction_type,
        status=TransactionStatus.pending,
        recipient_address=recipient_address,
        recipient_name=recipient_name,
        category=category,
        description=description,
        idempotency_key=idempotency_key,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx, True


def evaluate_payment(
    db: Session,
    agent: Agent,
    *,
    amount: float,
    category: PolicyCategory,
    recipient_address: str,
    recipient_name: Optional[str],
    transaction_id: int,
) -> PolicyEvaluationResult:
    return policy_engine.evaluate_transaction(
        agent=agent,
        policy=agent.policies,
        amount=amount,
        category=category.value,
        recipient_address=recipient_address,
        recipient_name=recipient_name,
        db=db,
        transaction_id=transaction_id,
    )


def mark_rejected(db: Session, tx: Transaction, reason: str) -> None:
    tx.status = TransactionStatus.rejected
    tx.rejection_reason = reason
    db.commit()
    db.refresh(tx)


def mark_approval_required(db: Session, tx: Transaction) -> None:
    tx.status = TransactionStatus.approved
    db.commit()
    db.refresh(tx)


def _executed_since(db: Session, agent_id: int, since: datetime) -> Decimal:
    """Sum of already-executed amounts for ``agent`` since ``since`` (excludes the
    pending/approved transaction being settled, so it cannot double-count itself)."""
    rows = (
        db.query(Transaction.amount)
        .filter(
            Transaction.agent_id == agent_id,
            Transaction.status == TransactionStatus.executed,
            Transaction.created_at >= since,
        )
        .all()
    )
    return sum((Decimal(str(r.amount)) for r in rows), Decimal("0"))


def recheck_limits_at_execution(
    db: Session, agent: Agent, tx: Transaction
) -> Optional[str]:
    """
    Re-run the daily/monthly caps a second time at the moment of execution.

    The policy engine evaluates a payment when the transaction is *requested*;
    a concurrent burst of approvals could each pass their own evaluation and then
    push the agent past the daily cap together. Re-checking the caps here, under
    the same request as the money movement, closes that window. Returns a failure
    reason when a cap would be exceeded, else None.
    """
    policy = agent.policies
    if policy is None:
        return None
    amount = Decimal(str(tx.amount))
    now = datetime.now(timezone.utc)
    daily = Decimal(str(policy.max_per_day))
    daily_spent = _executed_since(db, agent.id, now - timedelta(hours=24))
    if daily_spent + amount > daily:
        return (
            f"Daily limit exceeded at execution time. Spent ${daily_spent} today; "
            f"this payment would bring it to ${daily_spent + amount}, exceeding the ${daily} limit."
        )
    if policy.max_per_month is not None:
        monthly = Decimal(str(policy.max_per_month))
        monthly_spent = _executed_since(db, agent.id, now - timedelta(days=30))
        if monthly_spent + amount > monthly:
            return (
                f"Monthly limit exceeded at execution time. Spent ${monthly_spent} in the last "
                f"30 days; this payment would exceed the ${monthly} limit."
            )
    return None


def attempt_execution(
    db: Session,
    agent: Agent,
    tx: Transaction,
    *,
    to_address: Optional[str] = None,
    to_name: Optional[str] = None,
    memo: Optional[str] = None,
    execution_label: str = "Payment",
) -> Dict[str, Any]:
    """
    Execute a policy-approved payment.

    Responsibilities:
    * balance check FIRST (never let an underfunded agent pay),
    * actually transfer USDC via the payment service,
    * persist executed/failed state + ledger + audit + tx hash.

    Returns ``{"executed": bool, "transaction": tx, "reason": str|None,
    "proof": dict|None}``. Never raises for business conditions.
    """
    amount = float(tx.amount)
    dest_address = to_address or tx.recipient_address
    dest_name = to_name or tx.recipient_name or dest_address
    memo_value = memo or tx.description or f"{execution_label} {amount} USDC"

    balance = float(agent.balance or 0)
    if balance < amount:
        logger.warning(
            "insufficient balance: agent=%s tx=%s has=%.6f needs=%.6f",
            agent.id,
            tx.id,
            balance,
            amount,
        )
        tx.status = TransactionStatus.failed
        tx.rejection_reason = (
            f"Insufficient balance: the agent only has ${balance:.2f} but the "
            f"payment needs ${amount:.2f}. Fund the agent and approve again."
        )
        db.commit()
        db.refresh(tx)
        return {
            "executed": False,
            "transaction": tx,
            "reason": tx.rejection_reason,
            "proof": None,
        }

    # Final enforcement re-check: the policy engine already approved this payment,
    # but daily/monthly caps are re-verified here so a concurrent batch of
    # approvals can never sneak the agent past its configured limits together.
    limit_failure = recheck_limits_at_execution(db, agent, tx)
    if limit_failure is not None:
        logger.warning(
            "execution guard blocked agent=%s tx=%s amount=%.6f: %s",
            agent.id,
            tx.id,
            amount,
            limit_failure,
        )
        tx.status = TransactionStatus.failed
        tx.rejection_reason = limit_failure
        db.commit()
        db.refresh(tx)
        return {
            "executed": False,
            "transaction": tx,
            "reason": limit_failure,
            "proof": None,
        }

    source = agent.escrow_address or agent.user.wallet_address
    try:
        exec_result = payment_service.execute_payment(
            from_address=source,
            to_address=dest_address,
            amount=amount,
            memo=memo_value,
            signer_context={
                "owner_wallet": agent.user.wallet_address,
                "agent_id": agent.id,
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            "payment execution raised agent=%s tx=%s amount=%.6f: %s",
            agent.id,
            tx.id,
            amount,
            e,
        )
        tx.status = TransactionStatus.failed
        tx.rejection_reason = "Payment execution failed. The provider could not complete the transfer."
        db.commit()
        db.refresh(tx)
        return {
            "executed": False,
            "transaction": tx,
            "reason": tx.rejection_reason,
            "proof": None,
        }

    if not exec_result.get("success"):
        tx.status = TransactionStatus.failed
        tx.rejection_reason = exec_result.get("message", "Payment execution failed")
        db.commit()
        db.refresh(tx)
        return {
            "executed": False,
            "transaction": tx,
            "reason": tx.rejection_reason,
            "proof": None,
        }

    # Success: settle in the ledger + audit trail.
    tx.status = TransactionStatus.executed
    tx.tx_hash = exec_result.get("tx_hash")
    tx.executed_at = datetime.now(timezone.utc)
    agent.balance = Decimal(str(agent.balance)) - Decimal(str(amount))
    agent.total_spent = Decimal(str(agent.total_spent)) + Decimal(str(amount))
    audit_service.log(
        db,
        user_id=agent.user_id,
        agent_id=agent.id,
        event=TRANSACTION_EXECUTED,
        actor="system",
        detail={
            "transaction_id": tx.id,
            "amount": amount,
            "recipient": dest_name,
            "recipient_address": dest_address,
            "tx_hash": tx.tx_hash,
            "mode": "mock" if payment_service.is_mock else "solana",
            "simulated": payment_service.is_mock,
        },
    )
    db.commit()
    db.refresh(tx)

    proof = {
        "tx_hash": tx.tx_hash,
        "mode": "mock" if payment_service.is_mock else "solana",
        "simulated": payment_service.is_mock,
        "explorer_url": exec_result.get("explorer_url"),
    }
    logger.info(
        "payment executed agent=%s tx=%s amount=%.6f -> %s",
        agent.id,
        tx.id,
        amount,
        dest_name,
    )
    return {
        "executed": True,
        "transaction": tx,
        "reason": None,
        "proof": proof,
    }