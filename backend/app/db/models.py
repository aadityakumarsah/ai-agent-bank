from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Enum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class LLMProviderName(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    google = "google"


class ServiceCategory(str, enum.Enum):
    api = "api"
    compute = "compute"
    data = "data"
    ai_model = "ai_model"
    storage = "storage"
    other_agent = "other_agent"


class ServiceRiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ServiceDirectory(Base):
    """
    A marketplace listing of external, payable services an agent can purchase.

    Each entry describes an endpoint an agent may call. If ``requires_payment``
    is true, the agent must first obtain policy-engine approval and execute a
    USDC payment before the service will return its result.

    Demo services are explicitly flagged via ``is_demo`` and should be labelled
    "DEMO SERVICE" in the UI — they never represent a real payable endpoint.
    """

    __tablename__ = "service_directory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(Enum(ServiceCategory), nullable=False)
    endpoint = Column(String, nullable=False)  # conceptual endpoint path
    wallet_address = Column(String, nullable=False)  # recipient for payment
    price = Column(Numeric(20, 6), nullable=False, default=0)  # USDC
    currency = Column(String, default="USDC")
    requires_payment = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    risk_level = Column(Enum(ServiceRiskLevel), default=ServiceRiskLevel.low)
    is_demo = Column(Boolean, default=True)  # explicitly a mock/demo service
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ServiceDirectory {self.name} ({self.category.value})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    policies = relationship(
        "Policy", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )


class AgentStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    killed = "killed"  # legacy alias — treated identically to revoked
    revoked = "revoked"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Numeric(20, 6), default=0)  # 6 decimal places for USDC
    total_spent = Column(Numeric(20, 6), default=0)
    escrow_address = Column(
        String, nullable=True
    )  # Solana escrow account for the agent
    status = Column(Enum(AgentStatus), default=AgentStatus.active)
    violation_count = Column(Integer, default=0)  # policy violations (deterministic risk input)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="agents")
    policies = relationship(
        "Policy", back_populates="agent", uselist=False, cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="agent", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="agent", cascade="all, delete-orphan"
    )


class PolicyCategory(str, enum.Enum):
    api = "api"
    compute = "compute"
    data = "data"
    agent = "agent"


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, unique=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # For direct access
    max_per_transaction = Column(
        Numeric(20, 6), nullable=False, default=0
    )  # e.g., 20.00
    max_per_day = Column(Numeric(20, 6), nullable=False, default=0)  # e.g., 100.00
    max_per_month = Column(
        Numeric(20, 6), nullable=True, default=None
    )  # e.g., 1000.00; None = unlimited
    allowed_categories = Column(Text, default="[]")  # JSON list of allowed categories
    blocked_human_transfers = Column(Boolean, default=True)
    blocked_withdrawals = Column(Boolean, default=True)
    blocked_arbitrary_contracts = Column(Boolean, default=True)
    require_approval_above = Column(Numeric(20, 6), nullable=True, default=None)
    allowed_recipient_addresses = Column(
        Text, default="[]"
    )  # JSON whitelist of allowed merchant/agent addresses
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agent = relationship("Agent", back_populates="policies")
    user = relationship("User", back_populates="policies")


class TransactionType(str, enum.Enum):
    payment = "payment"
    withdrawal = "withdrawal"
    approval = "approval"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    failed = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(20, 6), nullable=False)
    currency = Column(String, default="USDC")
    transaction_type = Column(Enum(TransactionType), default=TransactionType.payment)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    recipient_address = Column(String, nullable=False)
    recipient_name = Column(String, nullable=True)
    category = Column(Enum(PolicyCategory), nullable=True)
    description = Column(Text)
    idempotency_key = Column(
        String, nullable=True, unique=True, index=True
    )  # dedupe double-submits; never double-pay
    tx_hash = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    risk_score = Column(Integer, default=0)  # deterministic rule-based risk score 0-100
    risk_level = Column(String(16), default="low")  # low | medium | high
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="transactions")
    user = relationship("User", back_populates="transactions")
    logs = relationship(
        "TransactionLog", back_populates="transaction", cascade="all, delete-orphan"
    )


class TransactionLog(Base):
    __tablename__ = "transaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    log_level = Column(String)  # info, warning, error
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="logs")


class TaskRun(Base):
    """Tracks an agent task execution / run."""

    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    task_prompt = Column(Text, nullable=False)
    status = Column(
        String, default="running"
    )  # running, completed, failed, cancelled, waiting_for_approval
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    steps = Column(Text, default="[]")  # JSON list of execution steps
    memory = Column(Text, default="{}")  # JSON string for agent memory
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent")


class AuditLog(Base):
    """
    Immutable audit trail for every important financial / control event.

    Records are append-only: the API exposes reads and inserts only, never
    update or delete. Nothing in the UI can edit or remove an audit record.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    event = Column(String(64), index=True, nullable=False)
    actor = Column(String(32), default="human")  # human | system | policy_engine
    detail = Column(Text, default="{}")  # JSON metadata snapshot
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="audit_logs")
    agent = relationship("Agent", back_populates="audit_logs")


class UserAPIKey(Base):
    """
    An end-user supplied API key for a real LLM provider.

    Keys are scoped to a wallet (user) and encrypted at rest with Fernet
    (see ``app.services.secrets``). The raw key is never returned by the API —
    the UI only reports whether a key is set.
    """

    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(16), nullable=False)  # openai | anthropic | google
    encrypted_key = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="api_keys")


# We'll add a relationship from Agent to TaskRun if needed, but not necessary for now.
