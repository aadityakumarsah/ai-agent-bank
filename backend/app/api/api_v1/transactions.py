from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_wallet_ownership
from app.db.models import (
    User,
    Agent,
    AgentStatus,
    Transaction,
    TransactionStatus,
)
from app.schemas import TransactionOut
from app.services.audit_service import (
    TRANSACTION_APPROVED,
    TRANSACTION_REJECTED,
    audit_service,
)
from app.services.payment_flow import attempt_execution, transaction_to_dict

router = APIRouter(
    prefix="/users/{wallet_address}/transactions",
    tags=["transactions"],
    dependencies=[Depends(require_wallet_ownership)],
)


def _tx_to_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id,
        agent_id=tx.agent_id,
        amount=float(tx.amount),
        currency=tx.currency,
        transaction_type=tx.transaction_type.value,
        status=tx.status.value,
        recipient_address=tx.recipient_address,
        recipient_name=tx.recipient_name,
        category=tx.category.value if tx.category else None,
        description=tx.description,
        tx_hash=tx.tx_hash,
        rejection_reason=tx.rejection_reason,
        created_at=tx.created_at.isoformat() if tx.created_at else None,
    )


@router.get("", response_model=list[TransactionOut])
def list_transactions(wallet_address: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return [_tx_to_out(t) for t in txs]


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    wallet_address: str, transaction_id: int, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _tx_to_out(tx)


@router.post("/{transaction_id}/approve")
def approve_transaction(
    wallet_address: str, transaction_id: int, db: Session = Depends(get_db)
):
    """
    Human approval of a pending transaction (a payment that was above the
    approval threshold, or otherwise paused). Approving executes the USDC
    payment through the same guarded path used everywhere else: balance check
    first, idempotent, audited.

    * Already executed  -> 200 with the same transaction (never double-pays).
    * Blocked/failed    -> 409 (cannot approve a dead transaction).
    * Pending/approved  -> executes and returns the settled transaction.
    """
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    agent = db.query(Agent).filter(Agent.id == tx.agent_id).first()
    if agent is None or agent.status != AgentStatus.active:
        raise HTTPException(
            status_code=403,
            detail="The agent is no longer active and cannot execute this payment.",
        )

    if tx.status in (TransactionStatus.rejected, TransactionStatus.failed):
        raise HTTPException(
            status_code=409,
            detail="This transaction was already blocked or failed and can no longer be approved.",
        )

    if tx.status == TransactionStatus.executed:
        # Idempotent: approving an already-executed payment is a no-op.
        return {
            "approved": True,
            "executed": True,
            "already_processed": True,
            "transaction": _tx_to_out(tx),
        }

    audit_service.log(
        db,
        user_id=user.id,
        agent_id=agent.id,
        event=TRANSACTION_APPROVED,
        actor="human",
        detail={"transaction_id": tx.id, "amount": float(tx.amount)},
    )

    executed = attempt_execution(
        db,
        agent,
        tx,
        to_name=tx.recipient_name,
        memo=f"Approved payment {tx.id}",
    )
    settled = executed["transaction"]

    return {
        "approved": True,
        "executed": executed["executed"],
        "reason": executed["reason"],
        "transaction": _tx_to_out(settled),
        "tx_detail": transaction_to_dict(settled),
    }


@router.post("/{transaction_id}/reject")
def reject_transaction(
    wallet_address: str, transaction_id: int, db: Session = Depends(get_db)
):
    """
    Human rejection of a pending transaction. Refuses money movement without
    executing anything — the payment is marked rejected and audited for the
    trail. Idempotent: already-rejected/failed payments just return the current
    state; an executed payment can never be unwound (no double-processing).
    """
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status == TransactionStatus.executed:
        raise HTTPException(
            status_code=409,
            detail="This payment already executed and cannot be rejected.",
        )

    if tx.status in (TransactionStatus.rejected, TransactionStatus.failed):
        # Already decided (double-click) — report the stable outcome.
        return {
            "rejected": True,
            "already_processed": True,
            "transaction": _tx_to_out(tx),
        }

    agent = db.query(Agent).filter(Agent.id == tx.agent_id).first()
    tx.status = TransactionStatus.rejected
    tx.rejection_reason = "Rejected by the human. No money moved."
    if agent is not None:
        audit_service.log(
            db,
            user_id=user.id,
            agent_id=agent.id,
            event=TRANSACTION_REJECTED,
            actor="human",
            detail={"transaction_id": tx.id, "amount": float(tx.amount)},
        )
    db.commit()
    db.refresh(tx)
    return {
        "rejected": True,
        "already_processed": False,
        "transaction": _tx_to_out(tx),
    }