import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Agent, AgentStatus, Policy
from app.schemas import (
    AgentCreate,
    AgentFund,
    AgentStatusUpdate,
    AgentOut,
    PolicyCreate,
    PolicyOut,
    MessageOut,
    FundConfirm,
)
from app.services.payment_service import payment_service

router = APIRouter(prefix="/users/{wallet_address}/agents", tags=["agents"])


def _get_user(wallet_address: str, db: Session) -> User:
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _agent_to_out(agent: Agent) -> AgentOut:
    policy = agent.policies
    policy_out = None
    if policy:
        policy_out = PolicyOut(
            id=policy.id,
            agent_id=policy.agent_id,
            max_per_transaction=float(policy.max_per_transaction),
            max_per_day=float(policy.max_per_day),
            max_per_month=(
                float(policy.max_per_month) if policy.max_per_month is not None else None
            ),
            allowed_categories=json.loads(policy.allowed_categories or "[]"),
            blocked_human_transfers=policy.blocked_human_transfers,
            blocked_withdrawals=policy.blocked_withdrawals,
            blocked_arbitrary_contracts=policy.blocked_arbitrary_contracts,
            require_approval_above=(
                float(policy.require_approval_above) if policy.require_approval_above is not None else None
            ),
            allowed_recipient_addresses=json.loads(policy.allowed_recipient_addresses or "[]"),
        )
    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        balance=float(agent.balance),
        total_spent=float(agent.total_spent),
        status=agent.status.value,
        escrow_address=agent.escrow_address,
        policies=policy_out,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
    )


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    wallet_address: str, payload: AgentCreate, db: Session = Depends(get_db)
):
    user = _get_user(wallet_address, db)
    agent = Agent(
        name=payload.name,
        description=payload.description,
        user_id=user.id,
        balance=0,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    # Give the agent a deterministic escrow address derived server-side. The
    # secret key for this address never leaves the backend.
    agent.escrow_address = payment_service.derive_escrow_address(
        user.wallet_address, agent.id
    )
    db.commit()
    db.refresh(agent)
    return _agent_to_out(agent)


@router.get("", response_model=list[AgentOut])
def list_agents(wallet_address: str, db: Session = Depends(get_db)):
    user = _get_user(wallet_address, db)
    return [_agent_to_out(a) for a in user.agents]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(wallet_address: str, agent_id: int, db: Session = Depends(get_db)):
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_out(agent)


@router.post("/{agent_id}/fund")
def fund_agent(
    wallet_address: str, agent_id: int, payload: AgentFund, db: Session = Depends(get_db)
):
    """
    Fund an agent's escrow.

    MOCK MODE: credits the simulated balance immediately (no on-chain tx).
    REAL MODE: returns a reviewable payment request for the user's wallet to
    sign; the escrow balance only updates after ``/fund/confirm``.
    """
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if payment_service.is_mock:
        # Simulated funding — credit balance, clearly MOCK MODE.
        agent.balance = float(agent.balance) + payload.amount
        db.commit()
        db.refresh(agent)
        return {
            "mode": "mock",
            "simulated": True,
            "tx_hash": payment_service.create_payment_request(
                user.wallet_address,
                agent.escrow_address or user.wallet_address,
                payload.amount,
                memo=f"Fund {agent.name}",
            )["signature"],
            "agent": _agent_to_out(agent),
        }

    # REAL MODE — build a signed-by-user request; do NOT credit yet.
    payment_request = payment_service.create_payment_request(
        from_address=user.wallet_address,
        to_address=agent.escrow_address or user.wallet_address,
        amount=payload.amount,
        memo=f"Fund {agent.name}",
    )
    return {
        "mode": "solana",
        "simulated": False,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "payment_request": payment_request,
    }


@router.post("/{agent_id}/fund/confirm", response_model=AgentOut)
def confirm_fund(
    wallet_address: str, agent_id: int, payload: FundConfirm, db: Session = Depends(get_db)
):
    """
    Verify a user-signed funding transaction on-chain, then credit the escrow.

    Used in REAL MODE after the user approves the transfer in their wallet.
    """
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    verification = payment_service.verify_transaction(payload.signature)
    if not verification.get("verified"):
        raise HTTPException(
            status_code=400,
            detail=verification.get("err", "Funding transaction could not be verified"),
        )

    agent.balance = float(agent.balance) + payload.amount
    db.commit()
    db.refresh(agent)
    return _agent_to_out(agent)


@router.post("/{agent_id}/policy", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def set_policy(
    wallet_address: str, agent_id: int, payload: PolicyCreate, db: Session = Depends(get_db)
):
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    existing = db.query(Policy).filter(Policy.agent_id == agent_id).first()
    if existing:
        existing.max_per_transaction = payload.max_per_transaction
        existing.max_per_day = payload.max_per_day
        existing.max_per_month = payload.max_per_month
        existing.allowed_categories = json.dumps(payload.allowed_categories)
        existing.blocked_human_transfers = payload.blocked_human_transfers
        existing.blocked_withdrawals = payload.blocked_withdrawals
        existing.blocked_arbitrary_contracts = payload.blocked_arbitrary_contracts
        existing.require_approval_above = payload.require_approval_above
        existing.allowed_recipient_addresses = json.dumps(payload.allowed_recipient_addresses)
        db.commit()
        db.refresh(existing)
        return PolicyOut(
            id=existing.id,
            agent_id=existing.agent_id,
            max_per_transaction=float(existing.max_per_transaction),
            max_per_day=float(existing.max_per_day),
            max_per_month=(
                float(existing.max_per_month)
                if existing.max_per_month is not None
                else None
            ),
            allowed_categories=payload.allowed_categories,
            blocked_human_transfers=existing.blocked_human_transfers,
            blocked_withdrawals=existing.blocked_withdrawals,
            blocked_arbitrary_contracts=existing.blocked_arbitrary_contracts,
            require_approval_above=(
                float(existing.require_approval_above)
                if existing.require_approval_above is not None
                else None
            ),
            allowed_recipient_addresses=payload.allowed_recipient_addresses,
        )

    policy = Policy(
        agent_id=agent.id,
        user_id=user.id,
        max_per_transaction=payload.max_per_transaction,
        max_per_day=payload.max_per_day,
        max_per_month=payload.max_per_month,
        allowed_categories=json.dumps(payload.allowed_categories),
        blocked_human_transfers=payload.blocked_human_transfers,
        blocked_withdrawals=payload.blocked_withdrawals,
        blocked_arbitrary_contracts=payload.blocked_arbitrary_contracts,
        require_approval_above=payload.require_approval_above,
        allowed_recipient_addresses=json.dumps(payload.allowed_recipient_addresses),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return PolicyOut(
        id=policy.id,
        agent_id=policy.agent_id,
        max_per_transaction=float(policy.max_per_transaction),
        max_per_day=float(policy.max_per_day),
        max_per_month=(
            float(policy.max_per_month) if policy.max_per_month is not None else None
        ),
        allowed_categories=payload.allowed_categories,
        blocked_human_transfers=policy.blocked_human_transfers,
        blocked_withdrawals=policy.blocked_withdrawals,
        blocked_arbitrary_contracts=policy.blocked_arbitrary_contracts,
        require_approval_above=(
            float(policy.require_approval_above)
            if policy.require_approval_above is not None
            else None
        ),
        allowed_recipient_addresses=payload.allowed_recipient_addresses,
    )


@router.patch("/{agent_id}/status", response_model=AgentOut)
def update_agent_status(
    wallet_address: str, agent_id: int, payload: AgentStatusUpdate, db: Session = Depends(get_db)
):
    """Control the agent lifecycle: active / suspended / killed."""
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        agent.status = AgentStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    db.commit()
    db.refresh(agent)
    return _agent_to_out(agent)


@router.delete("/{agent_id}", response_model=MessageOut)
def kill_agent(wallet_address: str, agent_id: int, db: Session = Depends(get_db)):
    """Instantly kill/revoke an agent (human ultimate authority)."""
    user = _get_user(wallet_address, db)
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = AgentStatus.killed
    db.commit()
    return {"message": f"Agent '{agent.name}' has been killed and can no longer transact."}
