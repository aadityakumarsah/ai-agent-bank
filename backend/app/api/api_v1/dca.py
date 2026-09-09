"""DCA (dollar-cost averaging) API router.

Plans are scoped to ``/users/{wallet_address}/dca`` and gated by the same
wallet-ownership dependency used across the agent API. Serialization mirrors
the ``AgentOut`` conventions.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.api_v1.providers import _get_agent, _get_user
from app.api.deps import require_wallet_ownership
from app.db.models import DcaPlan
from app.db.session import get_db
from app.schemas import (
    DcaPlanCreate,
    DcaPlanStatusUpdate,
)
from app.services.dca_service import dca_service

router = APIRouter(
    prefix="/users/{wallet_address}/dca",
    dependencies=[Depends(require_wallet_ownership)],
)


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _plan_out(plan: DcaPlan, db: Session, include_executions: bool = False) -> dict:
    out = {
        "id": plan.id,
        "agent_id": plan.agent_id,
        "token_mint": plan.token_mint,
        "token_symbol": plan.token_symbol,
        "token_decimals": plan.token_decimals,
        "amount_per_cycle": float(plan.amount_per_cycle or 0),
        "frequency": plan.frequency.value if plan.frequency else None,
        "status": plan.status.value if plan.status else None,
        "runs_completed": plan.runs_completed or 0,
        "total_invested": float(plan.total_invested or 0),
        "starts_at": _iso(plan.starts_at),
        "ends_at": _iso(plan.ends_at),
        "last_run_at": _iso(plan.last_run_at),
        "next_run_at": _iso(plan.next_run_at),
        "created_at": _iso(plan.created_at),
    }
    if include_executions:
        out["executions"] = []
        for x in dca_service.list_executions(db, plan.id):
            out["executions"].append({
                "id": x.id,
                "plan_id": x.plan_id,
                "agent_id": x.agent_id,
                "amount": float(x.amount or 0) if x.amount is not None else None,
                "status": x.status.value if x.status else None,
                "error": x.error,
                "token_mint": x.token_mint,
                "token_symbol": x.token_symbol,
                "out_amount": float(x.out_amount or 0) if x.out_amount is not None else None,
                "out_unit": x.out_unit,
                "quote_price": float(x.quote_price or 0) if x.quote_price is not None else None,
                "transaction_id": x.transaction_id,
                "tx_signature": x.tx_signature,
                "created_at": _iso(x.created_at),
                "completed_at": _iso(x.completed_at),
            })
    return out


def _resolve_plan(db: Session, wallet_address: str, plan_id: int) -> DcaPlan:
    user = _get_user(db, wallet_address)
    plan = dca_service.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="DCA plan not found")
    if plan.agent is None or plan.agent.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="This DCA plan does not belong to the wallet.",
        )
    return plan


def _parse_iso(value: str | None):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ISO-8601 timestamp: {value!r}",
        ) from None


@router.get("", response_model=list[dict])
def list_plans(
    wallet_address: str,
    agent_id: int | None = None,
    db: Session = Depends(get_db),
) -> list:
    user = _get_user(db, wallet_address)
    plans = dca_service.list_plans(db, user.id)
    if agent_id is not None:
        plans = [p for p in plans if p.agent_id == agent_id]
    return [_plan_out(p, db) for p in plans]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_plan(
    wallet_address: str,
    payload: DcaPlanCreate,
    db: Session = Depends(get_db),
) -> dict:
    user = _get_user(db, wallet_address)
    agent = _get_agent(db, payload.agent_id, wallet_address)
    try:
        plan = dca_service.create_plan(
            db,
            agent,
            user,
            token_mint=payload.token_mint,
            token_symbol=payload.token_symbol,
            token_decimals=payload.token_decimals,
            amount_per_cycle=payload.amount_per_cycle,
            frequency=payload.frequency,
            starts_at=_parse_iso(payload.starts_at),
            ends_at=_parse_iso(payload.ends_at),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return _plan_out(plan, db)


@router.get("/{plan_id}")
def get_plan(
    wallet_address: str,
    plan_id: int,
    include_executions: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    plan = _resolve_plan(db, wallet_address, plan_id)
    return _plan_out(plan, db, include_executions=include_executions)


@router.patch("/{plan_id}/status")
def update_plan_status(
    wallet_address: str,
    plan_id: int,
    payload: DcaPlanStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    plan = _resolve_plan(db, wallet_address, plan_id)
    try:
        plan = dca_service.set_status(db, plan, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return _plan_out(plan, db)


@router.get("/{plan_id}/executions")
def list_executions(
    wallet_address: str,
    plan_id: int,
    db: Session = Depends(get_db),
) -> list:
    plan = _resolve_plan(db, wallet_address, plan_id)
    executions = dca_service.list_executions(db, plan.id)
    return [{
        "id": x.id,
        "plan_id": x.plan_id,
        "agent_id": x.agent_id,
        "amount": float(x.amount or 0) if x.amount is not None else None,
        "status": x.status.value if x.status else None,
        "error": x.error,
        "token_mint": x.token_mint,
        "token_symbol": x.token_symbol,
        "out_amount": float(x.out_amount or 0) if x.out_amount is not None else None,
        "out_unit": x.out_unit,
        "quote_price": float(x.quote_price or 0) if x.quote_price is not None else None,
        "transaction_id": x.transaction_id,
        "tx_signature": x.tx_signature,
        "created_at": _iso(x.created_at),
        "completed_at": _iso(x.completed_at),
    } for x in executions]