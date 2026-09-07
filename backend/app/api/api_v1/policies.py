from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.db.models import Policy, Agent
from app.api import deps
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# Pydantic models for request/response
class PolicyBase(BaseModel):
    max_per_transaction: float
    max_per_day: float
    allowed_categories: List[str] = []
    blocked_human_transfers: bool = True
    blocked_withdrawals: bool = True
    blocked_arbitrary_contracts: bool = True
    require_approval_above: float = None


class PolicyCreate(PolicyBase):
    agent_id: int


class PolicyUpdate(BaseModel):
    max_per_transaction: float = None
    max_per_day: float = None
    allowed_categories: List[str] = None
    blocked_human_transfers: bool = None
    blocked_withdrawals: bool = None
    blocked_arbitrary_contracts: bool = None
    require_approval_above: float = None


class PolicyResponse(PolicyBase):
    id: int
    agent_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime = None

    class Config:
        orm_mode = True


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_in: PolicyCreate,
    db: Session = Depends(deps.get_db),
    # TODO: Add current user dependency
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new policy for an agent.
    """
    # For now, we'll hardcode a user_id until we have authentication
    user_id = 1  # Placeholder

    # Check if agent exists and belongs to the user
    agent = (
        db.query(Agent)
        .filter(Agent.id == policy_in.agent_id, Agent.user_id == user_id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not authorized")

    # Convert allowed_categories list to JSON string for storage
    policy_data = policy_in.dict()
    allowed_categories_json = json.dumps(policy_data.pop("allowed_categories"))

    policy = Policy(
        **policy_data, allowed_categories=allowed_categories_json, user_id=user_id
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/", response_model=List[PolicyResponse])
def read_policies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    # TODO: Add current user dependency
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve policies.
    """
    # For now, we'll hardcode a user_id until we have authentication
    user_id = 1  # Placeholder
    policies = (
        db.query(Policy)
        .filter(Policy.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Convert allowed_categories JSON string back to list for response
    for policy in policies:
        if policy.allowed_categories:
            policy.allowed_categories = json.loads(policy.allowed_categories)
        else:
            policy.allowed_categories = []
    return policies


@router.get("/{policy_id}", response_model=PolicyResponse)
def read_policy(
    policy_id: int,
    db: Session = Depends(deps.get_db),
    # TODO: Add current user dependency
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific policy by ID.
    """
    # For now, we'll hardcode a user_id until we have authentication
    user_id = 1  # Placeholder
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user_id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy.allowed_categories:
        policy.allowed_categories = json.loads(policy.allowed_categories)
    else:
        policy.allowed_categories = []
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    policy_in: PolicyUpdate,
    db: Session = Depends(deps.get_db),
    # TODO: Add current user dependency
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update a policy.
    """
    # For now, we'll hardcode a user_id until we have authentication
    user_id = 1  # Placeholder
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user_id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = policy_in.dict(exclude_unset=True)
    # Handle allowed_categories separately
    if "allowed_categories" in update_data:
        allowed_categories_json = json.dumps(update_data.pop("allowed_categories"))
        update_data["allowed_categories"] = allowed_categories_json

    for field, value in update_data.items():
        setattr(policy, field, value)

    db.add(policy)
    db.commit()
    db.refresh(policy)
    if policy.allowed_categories:
        policy.allowed_categories = json.loads(policy.allowed_categories)
    else:
        policy.allowed_categories = []
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(deps.get_db),
    # TODO: Add current user dependency
    # current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a policy.
    """
    # For now, we'll hardcode a user_id until we have authentication
    user_id = 1  # Placeholder
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user_id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()
    return None
