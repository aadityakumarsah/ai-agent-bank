from typing import Dict, Any
import json
import logging
from datetime import datetime
from app.db.models import Agent, TransactionRequest
from app.services.policy_engine import PolicyEngine
from app.services.payment_service import payment_service
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)


def search_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Simulate a search tool.
    For demo, we return hardcoded results based on the query.
    """
    query = arguments.get("query", "")
    logger.info(f"Agent {agent_id} performing search: {query}")

    # Hardcoded demo results
    if "solana rpc" in query.lower() or "best solana rpc" in query.lower():
        results = [
            {
                "name": "FastRPC",
                "url": "https://fastrpc.example.com",
                "cost_per_request": 0.001,
                "description": "Low-latency RPC provider with global coverage.",
            },
            {
                "name": "RocketRPC",
                "url": "https://rocketrpc.example.com",
                "cost_per_request": 0.002,
                "description": "High-throughput RPC provider.",
            },
        ]
    else:
        results = [
            {
                "title": "Demo search result",
                "snippet": f"This is a demo result for query: {query}",
                "url": "https://example.com",
            }
        ]

    return {"type": "search_results", "results": results}


def http_request_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Simulate an HTTP request.
    For demo, we return hardcoded responses based on the URL.
    """
    url = arguments.get("url", "")
    method = arguments.get("method", "GET")
    logger.info(f"Agent {agent_id} making {method} request to {url}")

    # Hardcoded demo responses
    if "fastrpc" in url.lower():
        return {
            "type": "http_response",
            "status_code": 200,
            "body": {
                "provider": "FastRPC",
                "latency": "12ms",
                "uptime": "99.9%",
                "cost": "0.001 USDC per request",
            },
        }
    elif "rocketrpc" in url.lower():
        return {
            "type": "http_response",
            "status_code": 200,
            "body": {
                "provider": "RocketRPC",
                "latency": "18ms",
                "uptime": "99.5%",
                "cost": "0.002 USDC per request",
            },
        }
    else:
        return {
            "type": "http_response",
            "status_code": 404,
            "body": {"error": "Not found"},
        }


def fetch_api_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Similar to http_request but specifically for APIs.
    We'll reuse the http_request tool for simplicity.
    """
    return http_request_tool(agent_id, arguments, db)


def get_balance_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Get the agent's current balance from the database.
    """
    logger.info(f"Agent {agent_id} requesting balance")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"type": "error", "message": "Agent not found"}

    return {"type": "balance", "balance": agent.balance, "currency": "USDC"}


def request_payment_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Handle a payment request from the agent.
    This tool will:
      1. Validate the arguments.
      2. Create a TransactionRequest.
      3. Send it to the PolicyEngine.
      4. If DENY, return the rejection.
      5. If REQUIRE_APPROVAL, return a indication that approval is needed (and we should pause the task).
      6. If ALLOW, reserve the spending (by creating a pending transaction request and then executing the payment via the payment service).
      7. Record the transaction and return the result.
    """
    logger.info(f"Agent {agent_id} requesting payment: {arguments}")

    # Validate required arguments
    required_fields = ["amount", "currency", "recipient", "category", "reason"]
    for field in required_fields:
        if field not in arguments:
            return {"type": "error", "message": f"Missing required field: {field}"}

    amount = arguments["amount"]
    currency = arguments["currency"]
    recipient = arguments["recipient"]
    category = arguments["category"]
    reason = arguments["reason"]
    metadata = arguments.get("metadata", {})

    # Create a transaction request object
    tx_request = TransactionRequest(
        agent_id=agent_id,
        amount=amount,
        currency=currency,
        recipient=recipient,
        category=category,
        reason=reason,
        metadata=json.dumps(metadata),
        status="pending",  # We'll set the status based on policy engine decision
    )
    db.add(tx_request)
    db.commit()
    db.refresh(tx_request)

    # Evaluate with policy engine
    policy_engine = PolicyEngine(db)
    decision = policy_engine.evaluate_transaction(tx_request)

    # Update the transaction request with the policy result and status
    tx_request.policy_result = json.dumps(decision)
    if decision["decision"] == "ALLOW":
        tx_request.status = "approved"
    elif decision["decision"] == "DENY":
        tx_request.status = "rejected"
        tx_request.rejection_reason = decision["reason"]
    elif decision["decision"] == "REQUIRE_APPROVAL":
        tx_request.status = "requires_approval"

    db.add(tx_request)
    db.commit()

    # If denied, return the denial
    if decision["decision"] == "DENY":
        return {
            "type": "payment_rejected",
            "request_id": tx_request.id,
            "reason": decision["reason"],
            "decision": decision["decision"],
        }

    # If requires approval, we return that and the task should pause
    if decision["decision"] == "REQUIRE_APPROVAL":
        return {
            "type": "payment_requires_approval",
            "request_id": tx_request.id,
            "reason": decision["reason"],
            "decision": decision["decision"],
        }

    # If allowed, we proceed to execute the payment
    # We'll use the payment service to transfer USDC
    # We need the sender address: we'll use the agent's wallet address (we assume the agent has a wallet address in the Agent model)
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or not agent.wallet_address:
        # If we don't have a wallet address, we cannot send money.
        tx_request.status = "failed"
        tx_request.rejection_reason = "Agent wallet address not found"
        db.add(tx_request)
        db.commit()
        return {
            "type": "payment_failed",
            "request_id": tx_request.id,
            "reason": "Agent wallet address not found",
            "decision": "FAILED",
        }

    # We'll simulate the payment for now (since we are using a mock payment service in development)
    # In production, we would use the real Solana payment service.
    payment_result = payment_service.transfer_usdc(
        from_address=agent.wallet_address, to_address=recipient, amount=amount
    )

    if not payment_result.get("success"):
        tx_request.status = "failed"
        tx_request.rejection_reason = payment_result.get("message", "Payment failed")
        db.add(tx_request)
        db.commit()
        return {
            "type": "payment_failed",
            "request_id": tx_request.id,
            "reason": tx_request.rejection_reason,
            "decision": "FAILED",
        }

    # Payment succeeded, update the transaction request and create a transaction record
    tx_request.status = "completed"
    tx_request.processed_at = datetime.utcnow()

    # Create a transaction record
    transaction = Transaction(
        request_id=tx_request.id,
        agent_id=agent_id,
        signature=payment_result.get("tx_hash"),
        network="solana-devnet",  # We'll hardcode for demo, but should come from settings
        amount=amount,
        currency=currency,
        recipient=recipient,
        sender=agent.wallet_address,
        status="executed",
        fee=0.0001,  # Example fee, in reality we would get from the payment result
    )
    db.add(transaction)

    # Update the agent's balance (subtract the amount and fee)
    agent.balance -= amount + transaction.fee
    agent.total_spent += amount + transaction.fee
    agent.last_active_at = datetime.utcnow()

    # Update daily spending
    today = datetime.utcnow().date()
    daily_spending = (
        db.query(DailySpending)
        .filter(
            and_(
                DailySpending.agent_id == agent_id,
                DailySpending.date >= today,
                DailySpending.date < today + datetime.timedelta(days=1),
            )
        )
        .first()
    )
    if not daily_spending:
        daily_spending = DailySpending(
            agent_id=agent_id, date=today, spent_amount=0, transaction_count=0
        )
        db.add(daily_spending)
    daily_spending.spent_amount += amount
    daily_spending.transaction_count += 1

    db.add(agent)
    db.add(daily_spending)
    db.commit()

    return {
        "type": "payment_completed",
        "request_id": tx_request.id,
        "transaction_id": transaction.id,
        "tx_hash": transaction.signature,
        "amount": amount,
        "fee": transaction.fee,
        "total_deducted": amount + transaction.fee,
        "new_balance": agent.balance,
        "decision": "ALLOW",
    }


def get_transaction_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Get a transaction by ID.
    """
    tx_id = arguments.get("transaction_id")
    if not tx_id:
        return {"type": "error", "message": "Missing transaction_id"}

    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx_id, Transaction.agent_id == agent_id)
        .first()
    )
    if not tx:
        return {"type": "error", "message": "Transaction not found"}

    return {
        "type": "transaction",
        "id": tx.id,
        "amount": tx.amount,
        "currency": tx.currency,
        "recipient": tx.recipient,
        "sender": tx.sender,
        "status": tx.status,
        "tx_hash": tx.signature,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }


def ask_user_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Simulate asking the user for input.
    For demo, we return a hardcoded response.
    """
    prompt = arguments.get("prompt", "Please provide input:")
    logger.info(f"Agent {agent_id} asking user: {prompt}")

    # In a real implementation, we would wait for user input.
    # For demo, we return a fixed response.
    return {"type": "user_response", "response": "Demo user response: " + prompt}


def complete_task_tool(
    agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Mark the task as complete.
    """
    result = arguments.get("result", "Task completed.")
    logger.info(f"Agent {agent_id} completing task with result: {result}")

    # We would update the task run in the database, but for now we just return success.
    return {"type": "task_completed", "result": result}


# Tool registry: maps tool names to functions
TOOL_REGISTRY = {
    "search": search_tool,
    "http_request": http_request_tool,
    "fetch_api": fetch_api_tool,
    "get_balance": get_balance_tool,
    "request_payment": request_payment_tool,
    "get_transaction": get_transaction_tool,
    "ask_user": ask_user_tool,
    "complete_task": complete_task_tool,
}


def execute_tool(
    tool_name: str, agent_id: int, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    Execute a tool by name.
    """
    if tool_name not in TOOL_REGISTRY:
        return {"type": "error", "message": f"Unknown tool: {tool_name}"}

    tool_func = TOOL_REGISTRY[tool_name]
    return tool_func(agent_id, arguments, db)
