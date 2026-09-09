"""
Append-only audit logging for AI Agent Bank.

Every important event (agent created / funded, policy changed, transaction
requested / approved / denied / executed, agent paused / resumed / revoked)
must generate an AuditLog record. The API surface is read + insert only; there
is deliberately no update or delete path, and the UI never mutates these rows.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


# Canonical event names
AGENT_CREATED = "agent_created"
AGENT_FUNDED = "agent_funded"
AGENT_PAUSED = "agent_paused"
AGENT_RESUMED = "agent_resumed"
AGENT_REVOKED = "agent_revoked"
AGENT_AUTO_SUSPENDED = "agent_auto_suspended"
POLICY_CHANGED = "policy_changed"
TRANSACTION_REQUESTED = "transaction_requested"
TRANSACTION_APPROVED = "transaction_approved"
TRANSACTION_DENIED = "transaction_denied"
TRANSACTION_EXECUTED = "transaction_executed"
TRANSACTION_REJECTED = "transaction_rejected"
TRANSACTION_CANCELLED = "transaction_cancelled"
DCA_EXECUTED = "dca_executed"
DCA_SKIPPED = "dca_skipped"


class AuditService:
    def log(
        self,
        db: Session,
        *,
        user_id: int,
        event: str,
        actor: str = "human",
        agent_id: int | None = None,
        detail: dict | None = None,
    ) -> AuditLog:
        record = AuditLog(
            user_id=user_id,
            agent_id=agent_id,
            event=event,
            actor=actor,
            detail=json.dumps(detail or {}),
        )
        db.add(record)
        return record


audit_service = AuditService()