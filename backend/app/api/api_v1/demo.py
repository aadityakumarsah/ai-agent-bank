import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Agent, Transaction, TransactionStatus, TransactionType, PolicyCategory
from app.schemas import TransactionOut
from app.services.policy_engine import policy_engine
from decimal import Decimal


router = APIRouter(prefix="/demo", tags=["demo"])


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


@router.post("/check")
def demo_blocked_transaction(payload: dict, db: Session = Depends(get_db)):
    """
    Demo endpoint to construct and evaluate a synthetic transaction against an
    agent's policy. Used by the frontend to show the blocked-transaction screen.
    """
    agent_id = payload.get("agent_id")
    amount = float(payload.get("amount", 0))
    recipient = payload.get("recipient", "unknownWallet")
    recipient_name = payload.get("recipient_name", "Unknown Human Wallet")
    category = payload.get("category", "api")

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = agent.policies

    # Record a rejected transaction for audit
    tx = Transaction(
        agent_id=agent.id,
        user_id=agent.user_id,
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.payment,
        status=TransactionStatus.pending,
        recipient_address=recipient,
        recipient_name=recipient_name,
        category=PolicyCategory(category) if category in [c.value for c in PolicyCategory] else PolicyCategory.api,
        description=payload.get("description", "Synthetic demo transaction"),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    result = policy_engine.evaluate_transaction(
        agent=agent,
        policy=policy,
        amount=amount,
        category=category,
        recipient_address=recipient,
        recipient_name=recipient_name,
        db=db,
        transaction_id=tx.id,
    )

    if not result.allowed:
        tx.status = TransactionStatus.rejected
        tx.rejection_reason = result.reason
        db.commit()
        db.refresh(tx)

    return {
        "decision": result.to_dict(),
        "transaction": _tx_to_out(tx),
        "summary": {
            "requested": amount,
            "per_transaction_limit": float(policy.max_per_transaction) if policy else None,
            "daily_limit": float(policy.max_per_day) if policy else None,
            "monthly_limit": (
                float(policy.max_per_month) if policy and policy.max_per_month is not None else None
            ),
            "recipient": recipient_name,
            "recipient_trusted": policy and recipient not in json.loads(policy.allowed_recipient_addresses or "[]"),
        },
    }