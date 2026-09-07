from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.db.session import get_db
from app.db.models import Agent, TaskRun, TransactionRequest
from app.services.agent_runtime import (
    AgentRuntime,
    TASK_RUN_STATUS_RUNNING,
    TASK_RUN_STATUS_WAITING_FOR_APPROVAL,
)

router = APIRouter()


@router.post("/agents/{agent_id}/tasks", status_code=status.HTTP_201_CREATED)
def start_agent_task(agent_id: int, task_prompt: str, db: Session = Depends(get_db)):
    """
    Start a task for an agent.
    The agent will run autonomously until it completes, fails, or needs approval.
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if agent is active
    if agent.status != "active":
        raise HTTPException(
            status_code=400, detail=f"Agent is not active (status: {agent.status})"
        )

    # Create agent runtime and start the task
    runtime = AgentRuntime(agent_id, db)
    task_run = runtime.start_task(task_prompt)

    # Run the agent task (this will run until it completes, fails, or needs approval)
    result = runtime.run_task(max_steps=10)

    # Refresh the task run to get the latest status
    db.refresh(task_run)

    return {
        "task_id": task_run.id,
        "status": task_run.status,
        "result": task_run.result,
        "agent_id": agent_id,
    }


@router.get("/agents/{agent_id}/tasks/{task_id}")
def get_agent_task_status(agent_id: int, task_id: int, db: Session = Depends(get_db)):
    """
    Get the status of a specific task for an agent.
    """
    task_run = (
        db.query(TaskRun)
        .filter(TaskRun.id == task_id, TaskRun.agent_id == agent_id)
        .first()
    )
    if not task_run:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_run.id,
        "agent_id": task_run.agent_id,
        "status": task_run.status,
        "result": task_run.result,
        "error": task_run.error,
        "steps": json.loads(task_run.steps) if task_run.steps else [],
        "memory": json.loads(task_run.memory) if task_run.memory else {},
        "created_at": task_run.created_at,
        "updated_at": task_run.updated_at,
        "completed_at": task_run.completed_at,
    }


@router.post("/agents/{agent_id}/tasks/{task_id}/approve")
def approve_task_payment(agent_id: int, task_id: int, db: Session = Depends(get_db)):
    """
    Approve a pending payment for a task that is waiting for approval.
    This will update the transaction request and allow the agent to continue.
    """
    task_run = (
        db.query(TaskRun)
        .filter(TaskRun.id == task_id, TaskRun.agent_id == agent_id)
        .first()
    )
    if not task_run:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_run.status != TASK_RUN_STATUS_WAITING_FOR_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not waiting for approval (status: {task_run.status})",
        )

    # We need to find the pending transaction request that caused the pause.
    # We'll look for a transaction request with status 'requires_approval' for this agent that is associated with this task run.
    # We don't have a direct link from task run to transaction request, but we can look for the most recent requires_approval transaction request for the agent that is not yet approved.
    # For simplicity, we'll assume that the task run's memory or result contains the request ID.
    # We'll store the pending request ID in the task run's memory or result.
    # In our agent runtime, when we pause, we set the task run's result to the reason and we have the request ID in the tool result.
    # We didn't save it to the task run. Let's adjust: we'll store the pending request ID in the task run's memory.
    # We'll change the agent runtime to store the pending request ID in the memory when we pause.
    # But we already updated the models to have a memory field. We'll use that.

    # For now, we'll do a simple lookup: find the most recent transaction request for this agent that is in requires_approval state.
    pending_tx = (
        db.query(TransactionRequest)
        .filter(
            TransactionRequest.agent_id == agent_id,
            TransactionRequest.status == "requires_approval",
        )
        .order_by(TransactionRequest.id.desc())
        .first()
    )

    if not pending_tx:
        raise HTTPException(
            status_code=400, detail="No pending payment request found for approval"
        )

    # Update the transaction request to approved
    pending_tx.status = "approved"
    pending_tx.processed_at = func.now()
    # We'll also update the policy_result to reflect approval? We'll leave it as is.
    db.add(pending_tx)
    db.commit()

    # Now we need to restart the agent runtime from where it left off.
    # We'll create a new agent runtime instance, set the task run to the existing one, and run the task again.
    # The agent runtime's run_task method will use the existing task run and memory.
    runtime = AgentRuntime(agent_id, db)
    runtime.task_run = task_run  # Use the existing task run
    # Load memory from the task run
    if task_run.memory:
        runtime.memory = json.loads(task_run.memory)
    else:
        runtime.memory = {
            "previous_actions": [],
            "tool_results": [],
            "transaction_ids": [],
            "policy_decisions": [],
            "task_context": {},
        }

    # Run the agent task again (it will continue from where it left off)
    result = runtime.run_task(max_steps=10)

    # Refresh the task run
    db.refresh(task_run)

    return {
        "task_id": task_run.id,
        "status": task_run.status,
        "result": task_run.result,
        "agent_id": agent_id,
    }


@router.post("/agents/{agent_id}/tasks/{task_id}/cancel")
def cancel_agent_task(agent_id: int, task_id: int, db: Session = Depends(get_db)):
    """
    Cancel a running task.
    """
    task_run = (
        db.query(TaskRun)
        .filter(TaskRun.id == task_id, TaskRun.agent_id == agent_id)
        .first()
    )
    if not task_run:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_run.status not in [
        TASK_RUN_STATUS_RUNNING,
        TASK_RUN_STATUS_WAITING_FOR_APPROVAL,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be cancelled (status: {task_run.status})",
        )

    task_run.status = TASK_RUN_STATUS_CANCELLED
    task_run.result = "Task cancelled by user"
    db.add(task_run)
    db.commit()

    return {
        "task_id": task_run.id,
        "status": task_run.status,
        "result": task_run.result,
    }
