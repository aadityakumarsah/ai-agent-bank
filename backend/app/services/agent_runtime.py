import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import (
    Agent,
    PolicyCategory,
    TaskRun,
    Transaction,
    TransactionStatus,
    TransactionType,
    UserAPIKey,
)
from app.services.agent_tools import list_tool_specs, run_tool
from app.services.ai_service import NoLLMConfiguredError, llm_service
from app.services.payment_flow import attempt_execution
from app.services.payment_service import payment_service
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

SYSTEM_PROMPT_TOOLS = """You are an AI agent operating inside AI Agent Bank — a programmable financial permission layer.
You can buy real services from registered providers with a real budget, but you never control money directly: every purchase is gated by a deterministic policy engine and a real USDC ledger.

To buy something you MUST use the tools in order:
1. search_services — find candidate listings (category, price, provider, id).
2. get_quote — for any candidate you intend to buy, with a valid request payload
   (translation listings require {"text": "...", "langpair": "en|es"} or
   {"text": "...", "source": "en", "target": "es"}).
3. submit_purchase — buy a quoted intent_id at its quoted price, calling it at
   most once per intent_id.
4. purchase_status — poll a purchase's status/result if needed.

Rules:
- Never invent or guess listing ids, prices, quotes, tx hashes or provider results. Only report what the tools return.
- If a purchase is approval_required, say so plainly and stop attempting that purchase.
- If a purchase is blocked, look for another candidate service within budget rather than forcing payment.
- Prefer the cheapest verified option that satisfies the user's request.
- When you have a completed purchase, answer the user with a concise summary of what was bought, the amount paid, and the provider's returned result.
- If you have final text to say without any tool needed, just respond with text (no tool call).
"""


class AgentRuntime:
    """
    Executes an AI agent task. Coordinates:
      LLM reasoning (native tool calls when available)
        -> tool registry -> purchase pipeline (quote/policy/payment/provider)
    Providers without native tool-calling (demo mock) fall back to the legacy
    single-propose flow so demo mode keeps working.
    """

    MAX_TOOL_ITERATIONS = 8

    # Deterministic preference order so a wallet with multiple keys has a
    # stable provider.
    PROVIDER_PREFERENCE = ["openrouter", "openai", "anthropic", "google"]

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
            memory="{}",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    # ------------------------------------------------------------------ entry
    def execute_task(self, db: Session, agent: Agent, run: TaskRun) -> Dict[str, Any]:
        """Run the task loop. Returns a result dict appropriate for the API."""
        provider_name, api_key = self._user_llm_key(db, agent.user_id)
        provider = llm_service.resolve_provider(provider_name, api_key)

        if not provider.supports_tools:
            return self._legacy_execute(db, agent, run, provider_name, api_key)
        return self._tool_loop(db, agent, run, provider)

    # ------------------------------------------------ native tool-calling path
    def _tool_loop(self, db: Session, agent: Agent, run: TaskRun, provider) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = json.loads(run.steps or "[]")
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT_TOOLS},
            {"role": "user", "content": run.task_prompt},
        ]
        tools = list_tool_specs()
        final_text: Optional[str] = None

        self._record_step(
            db,
            run,
            steps,
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "type": "llm",
                "stage": "start",
                "provider": provider.name,
                "tools": [t.name for t in tools],
            },
        )

        for iteration in range(1, self.MAX_TOOL_ITERATIONS + 1):
            try:
                resp = provider.chat(messages, tools)
            except NoLLMConfiguredError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("provider.chat failed run=%s iter=%s: %s", run.id, iteration, e)
                run.status = "failed"
                run.error = f"The LLM provider call failed: {e}"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return {
                    "run_id": run.id,
                    "status": "failed",
                    "error": run.error,
                    "steps": steps,
                }

            self._record_step(
                db,
                run,
                steps,
                {
                    "t": datetime.now(timezone.utc).isoformat(),
                    "type": "llm",
                    "stage": f"iteration-{iteration}",
                    "provider": provider.name,
                    "tool_calls": [tc.name for tc in resp.tool_calls] or None,
                    "text": (resp.text or "")[:2000],
                },
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": resp.text or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, default=str),
                            },
                        }
                        for tc in resp.tool_calls
                    ],
                }
            )

            if not resp.tool_calls:
                final_text = resp.text or "Task complete."
                break

            for tc in resp.tool_calls:
                outcome = run_tool(db, agent, run.id, tc.name, tc.arguments)
                self._record_step(
                    db,
                    run,
                    steps,
                    {
                        "t": datetime.now(timezone.utc).isoformat(),
                        "type": "tool",
                        "name": tc.name,
                        "args": tc.arguments,
                        "outcome": outcome,
                    },
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(outcome, default=str),
                    }
                )

                # Human-approval pause: the run waits for the owner; the Approvals
                # page resumes it (payment + provider fulfilment) on approve.
                if tc.name == "submit_purchase" and outcome.get("outcome") == "approval_required":
                    memory = self._load_memory(run)
                    memory.setdefault("purchases", []).append(
                        {
                            "intent_id": outcome["intent_id"],
                            "status": "pending_approval",
                        }
                    )
                    run.memory = json.dumps(memory)
                    run.status = "waiting_for_approval"
                    run.result = (
                        f"APPROVAL REQUIRED\n{outcome.get('reason') or 'Purchase needs human approval.'}\n"
                        f"Purchase intent {outcome['intent_id']} is awaiting approval on the Approvals page."
                    )
                    db.commit()
                    return {
                        "run_id": run.id,
                        "status": "waiting_for_approval",
                        "approval_required": True,
                        "result": run.result,
                        "decision": outcome,
                        "steps": steps,
                    }

        if final_text is None:
            final_text = (
                "Reached the maximum number of tool iterations without a "
                "final answer. Last tool results are in the run history."
            )
        run.memory = json.dumps(self._load_memory(run))
        run.result = final_text
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "run_id": run.id,
            "status": "completed",
            "result": run.result,
            "steps": steps,
        }

    @staticmethod
    def _load_memory(run: TaskRun) -> Dict[str, Any]:
        try:
            memory = json.loads(run.memory or "{}")
        except (json.JSONDecodeError, TypeError):
            memory = {}
        return memory if isinstance(memory, dict) else {}

    # ----------------------------------------------- legacy (non-tool) providers
    def _legacy_execute(
        self,
        db: Session,
        agent: Agent,
        run: TaskRun,
        provider_name: Optional[str],
        api_key: Optional[str],
    ) -> Dict[str, Any]:
        """Single-shot propose->policy->pay flow for providers without native
        tool calling (the DEMO mock provider)."""
        steps: List[Dict[str, Any]] = json.loads(run.steps or "[]")

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

        if result.risk_score is not None:
            tx.risk_score = result.risk_score
            tx.risk_level = result.risk_level or "low"

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

        # 5. Execute the payment through the guarded pipeline.
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
                    "explorer_url": None,
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