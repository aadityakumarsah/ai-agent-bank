"""
Dollar-cost-averaging service for AI Agent Bank.

A DCA plan periodically spends a fixed USDC amount from an agent's balance to
buy a token via Jupiter. Each trade is policy-governed (per-transaction cap,
rolling daily/monthly caps, balance check), recorded as a ``swap`` Transaction
in the ledger with a stable ``idempotency_key``, and audited — so a scheduler
re-run can never double-spend.

Security: swaps are quoted and signed by the backend-managed per-agent escrow
via :class:`SwapService`; no user-supplied program IDs or raw transactions are
ever accepted (see ``swap_service.py``).
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Agent,
    DcaExecution,
    DcaExecutionStatus,
    DcaFrequency,
    DcaPlan,
    DcaStatus,
    PolicyCategory,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.services.audit_service import (
    DCA_EXECUTED,
    DCA_SKIPPED,
    audit_service,
)
from app.services.payment_flow import find_tx_by_idempotency_key
from app.services.swap_service import resolved_swap_usdc_mint, swap_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for ``DateTime(timezone=True)``
    columns; normalise to tz-aware UTC so comparisons always work (dev+prod)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _frequency_seconds(frequency: DcaFrequency) -> int:
    return {"hourly": 3600, "daily": 86400, "weekly": 604800}[frequency.value]


def compute_next_run(plan: DcaPlan, freq: DcaFrequency | None = None) -> datetime:
    f = freq or plan.frequency
    base = plan.last_run_at or plan.starts_at or plan.created_at or _now()
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    return base + timedelta(seconds=_frequency_seconds(f))


def _execution_idempotency_key(plan_id: int, run_number: int) -> str:
    return f"dca:{plan_id}:{run_number}"


class DCAService:
    # ------------------------------------------------------------------ plans
    def create_plan(
        self,
        db: Session,
        agent: Agent,
        user: User,
        *,
        token_mint: str,
        token_symbol: str | None,
        token_decimals: int | None,
        amount_per_cycle: float,
        frequency: str,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
    ) -> DcaPlan:
        if amount_per_cycle <= 0:
            raise ValueError("amount_per_cycle must be positive.")
        if not token_mint:
            raise ValueError("token_mint is required.")
        try:
            freq = DcaFrequency(frequency)
        except ValueError:
            raise ValueError(f"Unknown frequency: {frequency}") from None
        if frequency == "daily" and settings.DCA_SCAN_INTERVAL_S > 3600:
            raise ValueError("Daily plans require a scheduler interval <= 1 hour.")

        plan = DcaPlan(
            agent_id=agent.id,
            user_id=user.id,
            token_mint=token_mint,
            token_symbol=token_symbol or token_mint[:8],
            token_decimals=token_decimals or 9,
            amount_per_cycle=Decimal(str(amount_per_cycle)),
            frequency=freq,
            status=DcaStatus.active,
            runs_completed=0,
            total_invested=Decimal(0),
            starts_at=starts_at,
            ends_at=ends_at,
        )
        plan.next_run_at = compute_next_run(plan)
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    def list_plans(self, db: Session, user_id: int) -> list[DcaPlan]:
        return (
            db.query(DcaPlan)
            .filter(DcaPlan.user_id == user_id)
            .order_by(DcaPlan.created_at.desc())
            .all()
        )

    def get_plan(self, db: Session, plan_id: int) -> DcaPlan | None:
        return db.query(DcaPlan).filter(DcaPlan.id == plan_id).first()

    def set_status(self, db: Session, plan: DcaPlan, status: str) -> DcaPlan:
        try:
            new_status = DcaStatus(status)
        except ValueError:
            raise ValueError(f"Unknown status: {status}") from None
        plan.status = new_status
        if new_status == DcaStatus.active and plan.next_run_at is None:
            plan.next_run_at = compute_next_run(plan)
        db.commit()
        db.refresh(plan)
        return plan

    # --------------------------------------------------------------- execution
    def execute_due_plans(self, db: Session) -> dict[str, Any]:
        """Scheduler entry point. Returns a summary of what ran/skipped/failed."""
        now = _now()
        due = (
            db.query(DcaPlan)
            .filter(DcaPlan.status == DcaStatus.active)
            .all()
        )
        # Python-side timezone-safe comparison (works across SQLite/Postgres).
        summary = {"executed": 0, "skipped": 0, "failed": 0, "plans_checked": 0}
        for plan in due:
            if plan.next_run_at is None or _aware(plan.next_run_at) > now:
                continue
            summary["plans_checked"] += 1
            outcome = self._execute_once(db, plan)
            status = outcome.get("status")
            if status == "completed":
                summary["executed"] += 1
            elif status == "skipped":
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
        return summary

    def _execute_once(self, db: Session, plan: DcaPlan) -> dict[str, Any]:
        agent = plan.agent
        if agent is None:
            return {"status": "failed", "error": "agent missing"}

        if plan.ends_at is not None and _now() > _aware(plan.ends_at):
            plan.status = DcaStatus.completed
            db.commit()
            return {"status": "skipped", "error": "plan ended"}

        run_number = (plan.runs_completed or 0) + 1
        idempotency_key = _execution_idempotency_key(plan.id, run_number)

        existing_tx = find_tx_by_idempotency_key(db, idempotency_key)
        if existing_tx is not None and existing_tx.status == TransactionStatus.executed:
            # Already paid this cycle; treat as previously completed.
            return {"status": "completed", "reused": True}

        amount = float(plan.amount_per_cycle or 0)
        balance = float(agent.balance or 0)

        # 1. Balance guard — never let an underfunded agent trade.
        if balance < amount:
            self._record_failure(db, plan, run_number, idempotency_key,
                                 amount, "skipped",
                                 f"Insufficient balance: has ${balance:.2f}, needs ${amount:.2f}.",
                                 tx=existing_tx)
            return {"status": "skipped", "error": "insufficient balance"}

        # 2. Policy gate — per-transaction + rolling daily/monthly caps.
        policy = plan.agent.policies if plan.agent.policies else None
        if policy is None:
            return self._record_failure(db, plan, run_number, idempotency_key,
                                        amount, "failed",
                                        "No policy configured on this agent.",
                                        tx=existing_tx)
        if amount > float(policy.max_per_transaction or 0):
            return self._record_failure(db, plan, run_number, idempotency_key,
                                        amount, "failed",
                                        f"Amount ${amount:.2f} exceeds per-transaction cap ${float(policy.max_per_transaction)}.",
                                        tx=existing_tx)
        if policy.require_approval_above is not None and amount > float(policy.require_approval_above):
            return self._record_failure(db, plan, run_number, idempotency_key,
                                        amount, "failed",
                                        f"Amount ${amount:.2f} exceeds the auto-approval threshold ${float(policy.require_approval_above)}; DCA requires auto-approved trades.",
                                        tx=existing_tx)

        # 3. Execute the swap via the swap service (quoted + signed server-side).
        tx = self._create_swap_tx(db, agent, plan, amount, existing_tx)

        # Rolling 24h + 30d caps, re-checked at execution (same guard the
        # payment path uses) so a burst of trades can't exceed configured caps.
        from app.services.payment_flow import recheck_limits_at_execution
        limit_failure = recheck_limits_at_execution(db, agent, tx)
        if limit_failure:
            return self._record_failure(db, plan, run_number, idempotency_key,
                                        amount, "failed", limit_failure, tx=tx)

        escrow = agent.escrow_address or agent.user.wallet_address
        try:
            result = swap_service.execute_swap(
                owner_wallet=agent.user.wallet_address,
                agent_id=agent.id,
                escrow_address=escrow,
                input_mint=resolved_swap_usdc_mint(),
                output_mint=plan.token_mint,
                amount=amount,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("dca swap raised agent=%s plan=%s: %s", agent.id, plan.id, e)
            result = {"success": False, "error": str(e)}

        if not result.get("success"):
            tx.status = TransactionStatus.failed
            tx.rejection_reason = result.get("error") or result.get("message", "Swap failed")
            self._record_failure(db, plan, run_number, idempotency_key, amount,
                                 "failed", tx.rejection_reason, tx=tx)
            return {"status": "failed", "error": tx.rejection_reason}

        # 4. Settle the ledger + execution.
        tx.status = TransactionStatus.executed
        tx.tx_hash = result.get("tx_signature") or result.get("signature")
        tx.executed_at = _now()
        agent.balance = Decimal(str(agent.balance)) - Decimal(str(amount))
        agent.total_spent = Decimal(str(agent.total_spent)) + Decimal(str(amount))
        plan.runs_completed = (plan.runs_completed or 0) + 1
        plan.total_invested = Decimal(str(plan.total_invested or 0)) + Decimal(str(amount))
        plan.last_run_at = _now()
        plan.next_run_at = compute_next_run(plan)

        execution = db.query(DcaExecution).filter(
            DcaExecution.plan_id == plan.id,
            DcaExecution.agent_id == agent.id,
            DcaExecution.scheduled_at.is_(None),
        ).order_by(DcaExecution.id.desc()).first()
        if execution is None:
            execution = DcaExecution(
                plan_id=plan.id,
                agent_id=agent.id,
                user_id=agent.user_id,
                status=DcaExecutionStatus.executing,
                amount=Decimal(str(amount)),
                transaction_id=tx.id,
                token_mint=plan.token_mint,
                token_symbol=plan.token_symbol,
            )
            db.add(execution)
        else:
            execution.transaction_id = tx.id
        execution.status = DcaExecutionStatus.completed
        execution.out_amount = Decimal(str(result.get("out_amount") or 0))
        execution.out_unit = "token"
        execution.quote_price = Decimal(str(result.get("quote_price") or 0))
        execution.tx_signature = tx.tx_hash
        execution.completed_at = _now()

        audit_service.log(
            db,
            user_id=agent.user_id,
            agent_id=agent.id,
            event=DCA_EXECUTED,
            actor="system",
            detail={
                "plan_id": plan.id,
                "execution_number": run_number,
                "amount": amount,
                "token_mint": plan.token_mint,
                "token_symbol": plan.token_symbol,
                "out_amount": result.get("out_amount"),
                "tx_hash": tx.tx_hash,
                "mode": swap_service.mode,
                "simulated": swap_service.simulated,
            },
        )
        db.commit()
        for obj in (tx, plan, execution, agent):
            try:
                db.refresh(obj)
            except Exception as e:  # noqa: BLE001
                logger.debug("refresh failed for %s: %s", obj, e)
        return {"status": "completed", "tx": tx.id, "execution": execution.id}

    def _create_swap_tx(
        self, db: Session, agent: Agent, plan: DcaPlan, amount: float,
        existing_tx: Transaction | None,
    ) -> Transaction:
        if existing_tx is not None:
            return existing_tx
        tx = Transaction(
            agent_id=agent.id,
            user_id=agent.user_id,
            amount=Decimal(str(amount)),
            currency="USDC",
            transaction_type=TransactionType.swap,
            status=TransactionStatus.pending,
            recipient_address=plan.token_mint,
            recipient_name=f"DCA -> {plan.token_symbol}",
            category=PolicyCategory.agent,
            description=f"DCA {plan.frequency.value} buy of {plan.token_symbol} (plan {plan.id})",
            idempotency_key=_execution_idempotency_key(plan.id, (plan.runs_completed or 0) + 1),
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    def _record_failure(
        self, db: Session, plan: DcaPlan, run_number: int, idempotency_key: str,
        amount: float, status: str, error: str, tx: Transaction | None,
    ) -> dict[str, Any]:
        if tx is None:
            tx = self._create_swap_tx(db, plan.agent, plan, amount, None)
            tx.idempotency_key = idempotency_key
        execution = DcaExecution(
            plan_id=plan.id,
            agent_id=plan.agent_id,
            user_id=plan.user_id,
            status=DcaExecutionStatus(status),
            amount=Decimal(str(amount)),
            transaction_id=tx.id if tx.id else None,
            token_mint=plan.token_mint,
            token_symbol=plan.token_symbol,
            error=error,
            completed_at=_now(),
        )
        db.add(execution)
        if status == "skipped":
            audit_service.log(
                db, user_id=plan.user_id, agent_id=plan.agent_id,
                event=DCA_SKIPPED, actor="system",
                detail={"plan_id": plan.id, "amount": amount, "reason": error},
            )
        # Advance the plan regardless so the scheduler doesn't spin on failure.
        plan.last_run_at = _now()
        plan.next_run_at = compute_next_run(plan)
        db.commit()
        try:
            db.refresh(plan)
        except Exception as e:  # noqa: BLE001
            logger.debug("plan refresh failed: %s", e)
        return {"status": status, "error": error, "tx": tx.id if tx.id else None}

    def list_executions(self, db: Session, plan_id: int) -> list[DcaExecution]:
        return (
            db.query(DcaExecution)
            .filter(DcaExecution.plan_id == plan_id)
            .order_by(DcaExecution.created_at.desc())
            .all()
        )


dca_service = DCAService()