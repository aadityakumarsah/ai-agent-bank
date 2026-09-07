import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import (
    Agent,
    Transaction,
    TransactionStatus,
    TransactionType,
    PolicyCategory,
    TaskRun,
    UserAPIKey,
)
from app.services.ai_service import llm_service
from app.services.payment_service import payment_service
from app.services.payment_flow import attempt_execution
from app.services.policy_engine import policy_engine
from app.services.secrets import decrypt_secret

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI agent operating inside AI Agent Bank — a programmable financial permission layer.
You DO NOT control money directly. You PROPOSE actions, and the policy engine decides.
Follow rules:
- Only propose payments with a JSON object: {"action":"payment","recipient":...,"recipient_name":...,"amount":...,"category":...,"description":...}
- category must be one of: api, compute, data, agent
- Only propose amounts you judge necessary. Never propose transfers to human wallets.
- If no payment is needed, respond with {"action":"respond","text":"..."}.
Respond only with a single JSON object.
"""


class AgentRuntime:
    """
    Executes an AI agent task. Coordinates:
      LLM proposal  ->  policy engine decision  ->  payment service execution
    """

    # Deterministic preference order so a wallet with multiple keys has a
    # stable provider.
    PROVIDER_PREFERENCE = ["openai", "anthropic", "google"]

    def _user_llm_key(self, db: Session, user_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Return (provider, api_key) for an agent's owner, if they set one."""
        rows = {
            k.provider: k.encrypted_key
            for k in db.query(UserAPIKey).filter(UserAPIKey.user_id == user_id).all()
        }
        for provider in self.PROVIDER_PREFERENCE:
            if provider in rows:
                api_key = decrypt_secret(rows[provider])
                if api_key:
                    return provider, api_key
        return None, None

    def parse_proposal(self, raw: str) -> Dict[str, Any]:
        """Parse the LLM's proposed plan. Tolerates code fences, prose and
        malformed JSON that real models sometimes return."""
        if not raw:
            return {"action": "respond", "text": ""}
        text = raw.strip()
        # Strip a ``` ... ``` code fence (with or without a language tag).
        if text.startswith("```"):
            inner = text[3:].rpartition("```")[0].strip()
            lines = inner.splitlines()
            # Drop a language tag line ("json", "python", ...) that precedes JSON.
            if lines and not lines[0].lstrip().startswith("{"):
                lines = lines[1:]
            text = "\n".join(lines).strip()
        # Prefer an embedded JSON object even if the model added prose around it.
        if "{" in text:
            candidate = text[text.find("{") : text.rfind("}") + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"action": "respond", "text": raw}
        except json.JSONDecodeError:
            return {"action": "respond", "text": raw}

    def _record_step(
        self, db: Session, run: TaskRun, steps: List[Dict[str, Any]], step: Dict[str, Any]
    ) -> None:
        steps.append(step)
        run.steps = json.dumps(steps)
        db.commit()
        db.refresh(run)

    def create_task(self, db: Session, agent: Agent, task_prompt: str) -> TaskRun:
        run = TaskRun(
            agent_id=agent.id,
            task_prompt=task_prompt,
            status="running",
            steps="[]",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def execute_task(self, db: Session, agent: Agent, run: TaskRun) -> Dict[str, Any]:
        """Run the task loop. Returns a result dict appropriate for the API."""
        steps = json.loads(run.steps or "[]")

        # 1. Ask the LLM (or mock) to propose an action. End-user supplied keys
        #    (encrypted, per wallet) override any server-configured key.
        provider_name, api_key = self._user_llm_key(db, agent.user_id)
        self._record_step(
            db,
            run,
            steps,
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "type": "llm",
                "stage": "propose",
                "provider": provider_name or "default",
            },
        )

        raw = llm_service.complete(
            SYSTEM_PROMPT,
            run.task_prompt,
            provider_name=provider_name,
            api_key=api_key,
        )
        proposal = self.parse_proposal(raw)

        self._record_step(
            db,
            run,
            steps,
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "type": "proposal",
                "stage": "analysis",
                "proposal": proposal,
            },
        )

        # 2. If the LLM just wants to respond (no payment), finish.
        if proposal.get("action") != "payment":
            run.result = proposal.get("text", raw)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "run_id": run.id,
                "status": "completed",
                "result": run.result,
                "steps": steps,
            }

        # 3. Proceed with the payment proposal through the policy engine.
        amount = float(proposal.get("amount", 0))
        recipient = proposal.get("recipient", "")
        recipient_name = proposal.get("recipient_name")
        category = proposal.get("category", "api")
        description = proposal.get("description", "")

        # Build the transaction record (pending).
        tx = Transaction(
            agent_id=agent.id,
            user_id=agent.user_id,
            amount=Decimal(str(amount)),
            transaction_type=TransactionType.payment,
            status=TransactionStatus.pending,
            recipient_address=recipient,
            recipient_name=recipient_name,
            category=category if category in [c.value for c in PolicyCategory] else PolicyCategory.api,
            description=description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        policy = agent.policies
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

        self._record_step(
            db,
            run,
            steps,
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "type": "policy",
                "stage": "evaluation",
                "requested": {
                    "amount": amount,
                    "recipient": recipient,
                    "recipient_name": recipient_name,
                    "category": category,
                },
                "decision": result.to_dict(),
            },
        )

        # 4. Handle the decision.
        if result.requires_approval:
            # Above the human-approval threshold: pause the payment, do NOT move
            # money. The human decides in the Approvals page (approve or reject).
            tx.status = TransactionStatus.approved
            db.commit()
            db.refresh(tx)

            run.result = (
                f"APPROVAL REQUIRED\nRequested: ${amount}\n"
                f"Policy: {result.reason}"
            )
            run.status = "waiting_for_approval"
            db.commit()
            return {
                "run_id": run.id,
                "status": "waiting_for_approval",
                "approval_required": True,
                "result": run.result,
                "transaction": self._tx_to_dict(tx),
                "decision": result.to_dict(),
                "steps": steps,
            }

        if not result.allowed:
            tx.status = TransactionStatus.rejected
            tx.rejection_reason = result.reason
            db.commit()
            db.refresh(tx)

            run.result = (
                f"TRANSACTION BLOCKED\nRequested: ${amount}\n"
                f"Reason: {result.reason}"
            )
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "run_id": run.id,
                "status": "completed",
                "blocked": True,
                "result": run.result,
                "transaction": self._tx_to_dict(tx),
                "decision": result.to_dict(),
                "steps": steps,
            }

        # 5. Execute the payment. Policy already approved; sign only for this
        #    agent's backend-managed escrow. Never let the LLM direct signing
        #    for arbitrary addresses. Balance is checked before money moves.
        executed = attempt_execution(
            db,
            agent,
            tx,
            to_name=recipient_name or recipient,
            memo=description or None,
        )

        if executed["executed"]:
            tx = executed["transaction"]
            run.result = (
                f"Payment executed: ${amount} to {recipient_name or recipient} ({category}). "
                f"Tx: {tx.tx_hash}"
            )
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

            self._record_step(
                db,
                run,
                steps,
                {
                    "t": datetime.now(timezone.utc).isoformat(),
                    "type": "payment",
                    "stage": "execution",
                    "tx_hash": tx.tx_hash,
                    "mode": "mock" if payment_service.is_mock else "solana",
                    "simulated": payment_service.is_mock,
                    "explorer_url": executed["proof"].get("explorer_url")
                    if executed["proof"]
                    else None,
                },
            )

            return {
                "run_id": run.id,
                "status": "completed",
                "blocked": False,
                "transaction": self._tx_to_dict(tx),
                "decision": result.to_dict(),
                "steps": steps,
            }
        else:
            tx = executed["transaction"]
            run.status = "failed"
            run.error = executed["reason"]
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "run_id": run.id,
                "status": "failed",
                "error": run.error,
                "transaction": self._tx_to_dict(tx),
                "steps": steps,
            }

    def _tx_to_dict(self, tx: Transaction) -> Dict[str, Any]:
        return {
            "id": tx.id,
            "agent_id": tx.agent_id,
            "user_id": tx.user_id,
            "amount": str(tx.amount),
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


agent_runtime = AgentRuntime()
