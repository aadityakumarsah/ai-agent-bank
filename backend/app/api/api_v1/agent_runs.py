import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_wallet_ownership
from app.db.models import User, Agent, AgentStatus, Transaction, TaskRun
from app.schemas import TaskCreate, TaskOut, TransactionOut
from app.services.agent_runtime import agent_runtime
from app.services.ai_service import NoLLMConfiguredError
from app.services.redis_service import redis_client

router = APIRouter(
    prefix="/users/{wallet_address}/agents/{agent_id}/runs",
    tags=["agent-runtime"],
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


def _get_agent(wallet_address: str, agent_id: int, db: Session) -> Agent:
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=TaskOut)
def run_task(
    wallet_address: str, agent_id: int, payload: TaskCreate, db: Session = Depends(get_db)
):
    """Give the agent a task. It proposes an action; the policy engine decides."""
    agent = _get_agent(wallet_address, agent_id, db)

    if agent.status != AgentStatus.active:
        raise HTTPException(status_code=400, detail=f"Agent is {agent.status.value}")

    # Rate limit: max 10 task runs per minute per agent
    if not redis_client.rate_limit_check(f"ratelimit:run:{agent_id}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many task runs. Slow down.")

    run = agent_runtime.create_task(db, agent, payload.task)
    try:
        result = agent_runtime.execute_task(db, agent, run)
    except NoLLMConfiguredError as e:
        # Real mode + no LLM key: surface a helpful 400 instead of a 500, and
        # never let the run pretend it reasoned when it couldn't.
        run.status = "failed"
        run.error = str(e)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    return TaskOut(
        run_id=result["run_id"],
        status=result["status"],
        result=result.get("result"),
        blocked=result.get("blocked", False),
        decision=result.get("decision"),
        transaction=result.get("transaction"),
        error=result.get("error"),
        steps=result.get("steps"),
    )


@router.get("", response_model=list[TaskOut])
def list_runs(wallet_address: str, agent_id: int, db: Session = Depends(get_db)):
    agent = _get_agent(wallet_address, agent_id, db)
    runs = db.query(TaskRun).filter(TaskRun.agent_id == agent.id).order_by(TaskRun.created_at.desc()).all()
    return [
        TaskOut(
            run_id=r.id,
            status=r.status,
            result=r.result,
            error=r.error,
            steps=json.loads(r.steps or "[]"),
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=TaskOut)
def get_run(wallet_address: str, agent_id: int, run_id: int, db: Session = Depends(get_db)):
    agent = _get_agent(wallet_address, agent_id, db)
    run = db.query(TaskRun).filter(TaskRun.id == run_id, TaskRun.agent_id == agent.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    tx = (
        db.query(Transaction)
        .filter(Transaction.agent_id == agent.id, Transaction.created_at >= run.created_at)
        .order_by(Transaction.created_at.desc())
        .first()
    )
    return TaskOut(
        run_id=run.id,
        status=run.status,
        result=run.result,
        error=run.error,
        blocked=bool(run.result and "BLOCKED" in run.result),
        transaction=_tx_to_out(tx) if tx else None,
        steps=json.loads(run.steps or "[]"),
    )