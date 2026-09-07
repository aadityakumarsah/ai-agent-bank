"""
One-click demo scenarios router.

Four scripted missions run the REAL agent-bank-policy-payment path and render a
full execution trace:
    1. success          — auto-approved autonomous purchase
    2. blocked-spend    — per-transaction limit stops a $50 payment
    3. blocked-transfer — human transfers are disabled
    4. approval         — payment pauses for human approval, then executes

Every scenario auto-provisions a deterministic demo agent, so the button just
works in front of a live audience.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.limiter import RateLimiter
from app.db.session import get_db
from app.services.demo_scenarios import (
    SCENARIOS,
    approve_pending_scenario,
    run_scenario,
    scenario_enabled,
)

router = APIRouter(prefix="/demo/scenarios", tags=["demo-scenarios"])

scenario_limiter = RateLimiter(limit=30, window_seconds=60, prefix="demo-scenarios")


class _ScenarioPayload(BaseModel):
    client_request_id: Optional[str] = None


@router.get("")
def list_scenarios():
    """List the one-click demo scenarios with their metadata."""
    return {
        "demo_mode": scenario_enabled(),
        "scenarios": [
            {
                "id": sid,
                "title": spec["title"],
                "badge": spec["badge"],
                "task": spec["task"],
                "amount": float(spec["amount"]),
                "outcome": spec["outcome"],
            }
            for sid, spec in SCENARIOS.items()
        ],
    }


@router.post("/{scenario_id}/run")
def run(
    scenario_id: str,
    payload: _ScenarioPayload,
    db: Session = Depends(get_db),
    _: None = Depends(scenario_limiter),
):
    """Run one demo scenario. Returns a full DemoResult-shaped response."""
    return run_scenario(db, scenario_id, payload.client_request_id)


@router.post("/{scenario_id}/approve")
def approve(
    scenario_id: str,
    payload: _ScenarioPayload,
    db: Session = Depends(get_db),
    _: None = Depends(scenario_limiter),
):
    """Approve + execute the payment a scenario paused for human approval."""
    return approve_pending_scenario(db, scenario_id, payload.client_request_id)