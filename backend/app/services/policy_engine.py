import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Agent,
    AgentStatus,
    Policy,
    ProviderProfile,
    ProviderStatus,
    Transaction,
    TransactionLog,
    TransactionStatus,
)
from app.services.risk_engine import risk_engine
from app.services.trust_registry import trust_registry

logger = logging.getLogger(__name__)


class PolicyEvaluationResult:
    def __init__(
        self,
        allowed: bool,
        reason: str = "",
        checks: Optional[List[Dict[str, Any]]] = None,
        requires_approval: bool = False,
        risk_score: Optional[int] = None,
        risk_level: Optional[str] = None,
        risk_factors: Optional[List[Dict[str, Any]]] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.checks = checks or []
        self.requires_approval = requires_approval
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.risk_factors = risk_factors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "checks": self.checks,
            "risk": {
                "score": self.risk_score,
                "level": self.risk_level,
                "factors": self.risk_factors,
            },
        }


class PolicyEngine:
    """
    Deterministic policy enforcement engine.

    The AI proposes actions (payment requests). This engine decides whether each
    action is permitted based solely on the agent's configuration and current
    state. It never consults an LLM — only deterministic rules.
    """

    TRUSTED_RECIPIENTS = {
        # Mock demo merchants / providers — DEMO_MODE only. These are aliases
        # with no real on-chain address; in real mode they are never treated as
        # trusted (a recipient must be a real address on the policy whitelist).
        "rpcProvider": {
            "name": "Solana RPC Provider",
            "category": "compute",
        },
        "apiProvider": {
            "name": "API Provider",
            "category": "api",
        },
        "dataProvider": {
            "name": "Data Provider",
            "category": "data",
        },
        "agentPeer": {
            "name": "Agent Peer",
            "category": "agent",
        },
        "computeProvider": {
            "name": "Compute Provider",
            "category": "compute",
        },
        "storageProvider": {
            "name": "Storage Provider",
            "category": "data",
        },
        "trustedMerchant": {
            "name": "Trusted Merchant",
            "category": "api",
        },
    }

    def _registered_provider(self, db: Session, address: str) -> Optional[dict]:
        """A wallet registered in the marketplace as an active, verified
        provider is a vetted merchant — safe to pay within policy limits."""
        provider = (
            db.query(ProviderProfile)
            .filter(
                ProviderProfile.wallet_address == address,
                ProviderProfile.status == ProviderStatus.active,
                ProviderProfile.verified.is_(True),
            )
            .first()
        )
        if provider is None:
            return None
        return {"name": provider.name, "category": provider.category.value}

    def _parse_json(self, value: str, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse JSON field")
            return default

    def _sum_executed(self, db: Session, agent_id: int, since: datetime) -> Decimal:
        """Sum of executed transactions for this agent since ``since``."""
        total = (
            db.query(Transaction)
            .filter(
                Transaction.agent_id == agent_id,
                Transaction.status == TransactionStatus.executed,
                Transaction.created_at >= since,
            )
            .with_entities(Transaction.amount)
            .all()
        )
        return sum((Decimal(str(t.amount)) for t in total), Decimal("0"))

    def _get_daily_spend(self, db: Session, agent_id: int) -> Decimal:
        """Sum of executed transactions for this agent over the last 24h window."""
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        return self._sum_executed(db, agent_id, since)

    def _get_monthly_spend(self, db: Session, agent_id: int) -> Decimal:
        """Sum of executed transactions for this agent over the last 30 days."""
        since = datetime.now(timezone.utc) - timedelta(days=30)
        return self._sum_executed(db, agent_id, since)

    def _agent_age_hours(self, agent: Agent) -> float:
        if agent.created_at is None:
            return 24 * 365
        created = agent.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 3600.0)

    def _velocity(self, db: Session, agent_id: int) -> int:
        """Number of transactions submitted by this agent in the last hour."""
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        return int(
            db.query(Transaction)
            .filter(
                Transaction.agent_id == agent_id,
                Transaction.created_at >= since,
            )
            .count()
        )

    def _log(
        self, db: Session, transaction_id: int, level: str, message: str
    ) -> None:
        log = TransactionLog(
            transaction_id=transaction_id,
            log_level=level,
            message=message,
        )
        db.add(log)

    def evaluate_transaction(
        self,
        agent: Agent,
        policy: Optional[Policy],
        amount: float,
        category: str,
        recipient_address: str,
        recipient_name: Optional[str],
        db: Session,
        transaction_id: Optional[int] = None,
    ) -> PolicyEvaluationResult:
        """
        Deterministically evaluate whether a transaction should be allowed.

        Returns (allowed, reason, checks).
        """
        amount_dec = Decimal(str(amount))

        def _fail(reason: str, check: Dict[str, Any]) -> PolicyEvaluationResult:
            if transaction_id:
                self._log(db, transaction_id, "error", f"BLOCKED: {reason}")
            return PolicyEvaluationResult(
                allowed=False,
                reason=reason,
                checks=[check],
            )

        # --- Check 1: Policy exists ---
        if policy is None:
            return _fail(
                "No policy configured for agent. Add policies before enabling transactions.",
                {"name": "Policy configured", "passed": False, "detail": "No policy found"},
            )

        # --- Check 2: Agent active ---
        if agent.status != AgentStatus.active:
            return _fail(
                f"Agent is {agent.status.value} and cannot transact.",
                {"name": "Agent active", "passed": False, "detail": f"status={agent.status.value}"},
            )

        checks = []
        checks.append({"name": "Agent active", "passed": True, "detail": agent.status.value})

        # --- Check 3: Amount valid ---
        if amount_dec <= 0:
            return _fail(
                "Transaction amount must be greater than zero.",
                {"name": "Valid amount", "passed": False, "detail": amount},
            )
        checks.append({"name": "Valid amount", "passed": True, "detail": str(amount_dec)})

        # --- Check 4: Per-transaction limit ---
        max_per_tx = Decimal(str(policy.max_per_transaction))
        if amount_dec > max_per_tx:
            return _fail(
                f"Transaction exceeds per-transaction limit. Requested ${amount} but allowed ${max_per_tx}.",
                {
                    "name": "Per-transaction limit",
                    "passed": False,
                    "requested": str(amount_dec),
                    "allowed": str(max_per_tx),
                },
            )
        checks.append(
            {
                "name": "Per-transaction limit",
                "passed": True,
                "requested": str(amount_dec),
                "allowed": str(max_per_tx),
            }
        )

        # --- Check 5: Daily limit ---
        max_per_day = Decimal(str(policy.max_per_day))
        daily_spent = self._get_daily_spend(db, agent.id)
        projected_daily = daily_spent + amount_dec
        if projected_daily > max_per_day:
            return _fail(
                f"Daily limit exceeded. Spent ${daily_spent} today; this would bring it to ${projected_daily}, exceeding the ${max_per_day} limit.",
                {
                    "name": "Daily limit",
                    "passed": False,
                    "daily_spent": str(daily_spent),
                    "requested": str(amount_dec),
                    "allowed": str(max_per_day),
                },
            )
        checks.append(
            {
                "name": "Daily limit",
                "passed": True,
                "daily_spent": str(daily_spent),
                "projected": str(projected_daily),
                "allowed": str(max_per_day),
            }
        )

        # --- Check 6: Monthly limit ---
        # Hard cap over a rolling 30-day window. None (unset) = unlimited.
        monthly_allowed = policy.max_per_month
        if monthly_allowed is not None:
            max_per_month = Decimal(str(monthly_allowed))
            monthly_spent = self._get_monthly_spend(db, agent.id)
            projected_monthly = monthly_spent + amount_dec
            if projected_monthly > max_per_month:
                return _fail(
                    f"Monthly limit exceeded. Spent ${monthly_spent} in the last 30 days; "
                    f"this would bring it to ${projected_monthly}, exceeding the ${max_per_month} limit.",
                    {
                        "name": "Monthly limit",
                        "passed": False,
                        "monthly_spent": str(monthly_spent),
                        "projected": str(projected_monthly),
                        "allowed": str(max_per_month),
                    },
                )
            checks.append(
                {
                    "name": "Monthly limit",
                    "passed": True,
                    "monthly_spent": str(monthly_spent),
                    "projected": str(projected_monthly),
                    "allowed": str(max_per_month),
                }
            )
        else:
            checks.append(
                {"name": "Monthly limit", "passed": True, "detail": "No monthly cap"}
            )

        # --- Check 7: Category allowed ---
        allowed_categories = self._parse_json(policy.allowed_categories, [])
        if category not in allowed_categories:
            return _fail(
                f"Category '{category}' is not allowed. Allowed: {allowed_categories}.",
                {
                    "name": "Category allowed",
                    "passed": False,
                    "requested": category,
                    "allowed": allowed_categories,
                },
            )
        checks.append(
            {
                "name": "Category allowed",
                "passed": True,
                "requested": category,
                "allowed": allowed_categories,
            }
        )

        # --- Check 8: Recipient trusted / whitelisted ---
        # A recipient is trusted if it is on the policy's explicit whitelist
        # (a real address), OR — DEMO_MODE only — it is a known demo
        # provider/merchant alias. In real mode there are no pseudo-trusted
        # aliases: only the addresses the owner whitelisted count.
        whitelist = self._parse_json(policy.allowed_recipient_addresses, [])

        known_provider = None
        if settings.DEMO_MODE:
            for key, info in self.TRUSTED_RECIPIENTS.items():
                if recipient_address == key:
                    known_provider = info
                    break

        recipient_trusted = (known_provider is not None) or (recipient_address in whitelist)
        registry_entry = trust_registry.lookup(recipient_address)
        registered_provider = self._registered_provider(db, recipient_address)
        merchant_known = bool(registry_entry.get("trusted")) or recipient_trusted or (registered_provider is not None)

        # For demo/real: addresses are pseudonymous; we can't cryptographically
        # determine 'human' vs 'agent' yet, so we enforce:
        #   - blocked_human_transfers: if the recipient is NOT a known merchant
        #     (registered marketplace provider, official demo provider, or the
        #     owner's explicit whitelist) and human transfers are blocked, deny.
        if not merchant_known:
            if policy.blocked_human_transfers:
                return _fail(
                    f"Recipient '{recipient_name or recipient_address}' is unknown. Human transfers are disabled.",
                    {
                        "name": "Recipient trusted",
                        "passed": False,
                        "recipient": recipient_name or recipient_address,
                        "detail": "Human/untrusted transfers are disabled",
                    },
                )
            checks.append(
                {
                    "name": "Recipient trusted",
                    "passed": True,
                    "recipient": recipient_address,
                    "detail": "Recipient in allowed whitelist",
                }
            )
        else:
            if registered_provider is not None:
                detail = f"Registered marketplace provider: {registered_provider['name']}"
            elif recipient_trusted:
                detail = "Known provider or whitelisted"
            else:
                detail = "Trusted recipient (registry)"
            checks.append(
                {
                    "name": "Recipient trusted",
                    "passed": True,
                    "recipient": recipient_name or recipient_address,
                    "detail": detail,
                }
            )

        # --- Check 9: Human approval threshold ---
        requires_approval = False
        require_above = policy.require_approval_above
        if require_above is not None:
            require_above_dec = Decimal(str(require_above))
            if amount_dec > require_above_dec:
                requires_approval = True
                checks.append(
                    {
                        "name": "Human approval threshold",
                        "passed": False,
                        "requested": str(amount_dec),
                        "threshold": str(require_above_dec),
                        "detail": "Requires human approval",
                    }
                )
                return PolicyEvaluationResult(
                    allowed=False,
                    reason=f"Transaction above ${require_above_dec} requires human approval.",
                    checks=checks,
                    requires_approval=True,
                )
            else:
                checks.append(
                    {
                        "name": "Human approval threshold",
                        "passed": True,
                        "requested": str(amount_dec),
                        "threshold": str(require_above_dec),
                    }
                )

        # --- Check 10: Deterministic risk score ---
        # The policy engine gates, and the risk engine scores. A HIGH risk
        # transaction is pushed into human-approval rather than auto-executed.
        risk = risk_engine.compute(
            amount=float(amount_dec),
            recipient_known=recipient_trusted,
            merchant_known=merchant_known,
            category_allowed=True,
            contract_allowed=not bool(policy.blocked_arbitrary_contracts),
            agent_age_hours=self._agent_age_hours(agent),
            daily_limit=float(max_per_day),
            spent_today=float(daily_spent),
            velocity=self._velocity(db, agent.id),
            policy_violation_count=int(getattr(agent, "violation_count", 0) or 0),
        )
        risk_dict = risk.to_dict()
        risk_checks = {
            "name": "Risk score",
            "passed": risk.level != "high",
            "score": risk.score,
            "level": risk.level,
            "factors": risk_dict["factors"],
        }
        checks.append(risk_checks)

        if risk.level == "high" and not requires_approval:
            requires_approval = True
            checks.append(
                {
                    "name": "Risk approval threshold",
                    "passed": False,
                    "score": risk.score,
                    "detail": "High-risk transaction requires human approval",
                }
            )

        if transaction_id:
            self._log(db, transaction_id, "info", "APPROVED: All policy checks passed")

        return PolicyEvaluationResult(
            allowed=requires_approval is False,
            reason="All policy checks passed." if not requires_approval else "Transaction requires human approval (policy or risk threshold).",
            checks=checks,
            requires_approval=requires_approval,
            risk_score=risk.score,
            risk_level=risk.level,
            risk_factors=risk_dict["factors"],
        )


# Singleton instance
policy_engine = PolicyEngine()
