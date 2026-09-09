import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class LLMProviderName(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    google = "google"
    openrouter = "openrouter"


class ServiceCategory(str, enum.Enum):
    api = "api"
    compute = "compute"
    data = "data"
    ai_model = "ai_model"
    storage = "storage"
    other_agent = "other_agent"


class ProviderStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class ListingStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class PurchaseIntentStatus(str, enum.Enum):
    """Lifecycle of a real purchase (agent buys a provider service).

    Only one of ``quoting``/``pending_approval``/``paying`` runs at a time; the
    intent never skips forward without the prior stage completing.
    """

    quoting = "quoting"  # quote requested; amount agreed
    pending_approval = "pending_approval"  # human must approve (policy/risk)
    paying = "paying"  # USDC transfer in flight
    awaiting_provider = "awaiting_provider"  # paid; waiting on provider result
    completed = "completed"  # provider returned the real result
    failed = "failed"  # policy block / payment failure / provider error
    cancelled = "cancelled"  # abandoned by the human/agent


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
    purchases = relationship(
        "PurchaseIntent", back_populates="agent", cascade="all, delete-orphan"
    )
    dca_plans = relationship(
        "DcaPlan", back_populates="agent", cascade="all, delete-orphan"
    )
    dca_executions = relationship(
        "DcaExecution", back_populates="agent", cascade="all, delete-orphan"
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
    swap = "swap"


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


class ProviderProfile(Base):
    """
    A real marketplace provider registered by a wallet owner.

    ``api_base_url`` is the integration endpoint the agent bank calls to quote
    and execute the advertised service (e.g. a machine-readable translation
    API). ``wallet_address`` is the USDC recipient the agent pays on devnet
    (pseudo-random placeholder until a real merchant wallet is provided).
    ``supports`` declares the capabilities a listing relies on, so the agent
    bank can route tool calls to providers that actually offer them.
    """

    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text)
    adapter = Column(String, nullable=False)  # e.g. "mymemory"
    api_base_url = Column(String(512), nullable=False)
    category = Column(Enum(ServiceCategory), default=ServiceCategory.api)
    wallet_address = Column(String, nullable=False)  # USDC recipient for payments
    supports = Column(Text, default="[]")  # JSON list of capability strings
    status = Column(Enum(ProviderStatus), default=ProviderStatus.pending)
    verified = Column(Boolean, default=False)  # registry connectivity check passed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", backref="providers")
    listings = relationship(
        "ServiceListing", back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProviderProfile {self.name} ({self.adapter})>"


class ServiceListing(Base):
    """
    A payable service a provider offers, advertised to agents (e.g. "translate
    an English paragraph to Spanish"). ``price`` is the flat USDC amount per
    request; ``parameters`` holds a JSON schema the adapter validates request
    payloads against before quoting.
    """

    __tablename__ = "service_listings"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(Enum(ServiceCategory), nullable=False)
    price = Column(Numeric(20, 6), nullable=False, default=0)  # USDC
    currency = Column(String, default="USDC")
    parameters = Column(Text, default="{}")  # JSON schema of accepted params
    requires_payment = Column(Boolean, default=True)
    status = Column(Enum(ListingStatus), default=ListingStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    provider = relationship("ProviderProfile", back_populates="listings")
    purchases = relationship("PurchaseIntent", back_populates="listing")

    __table_args__ = (
        # A provider can't publish two listings with the same name.
        UniqueConstraint("provider_id", "name", name="uq_listing_provider_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ServiceListing {self.name} ({self.category.value})>"


class PurchaseIntent(Base):
    """
    A purchase an agent intent to make against a specific listing at a quoted
    price — the canonical record of "the agent buys things". Tracks every stage
    from quote to verified provider result and links the ledger payment row
    (``transaction_id``), so the purchase, its money movement and its result are
    one auditable unit.
    """

    __tablename__ = "purchase_intents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_run_id = Column(Integer, ForeignKey("task_runs.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("service_listings.id"), nullable=False)
    status = Column(Enum(PurchaseIntentStatus), default=PurchaseIntentStatus.quoting)
    request_payload = Column(Text, default="{}")  # JSON params sent to the provider
    quote = Column(Text, nullable=True)  # JSON quote from the provider
    amount = Column(Numeric(20, 6), nullable=True)  # agreed USDC amount
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    idempotency_key = Column(String, nullable=True, unique=True, index=True)
    provider_ref = Column(String(512), nullable=True)  # provider-side reference
    result = Column(Text, nullable=True)  # JSON final result / provider payload
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="purchases")
    user = relationship("User", backref="purchases")
    run = relationship("TaskRun", backref="purchases")
    provider = relationship("ProviderProfile", backref="purchases")
    listing = relationship("ServiceListing", back_populates="purchases")
    transaction = relationship("Transaction", backref="purchase")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PurchaseIntent {self.id} {self.status.value}>"


class DcaFrequency(str, enum.Enum):
    """How often a DCA plan places a trade."""

    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"


class DcaStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class DcaExecutionStatus(str, enum.Enum):
    """Lifecycle of a single scheduled DCA trade."""

    due = "due"  # scheduled, not yet attempted
    executing = "executing"  # swap in flight
    completed = "completed"  # swap executed successfully
    failed = "failed"  # policy block / payment / swap error
    skipped = "skipped"  # not enough balance this cycle


class DcaPlan(Base):
    """
    A dollar-cost-averaging plan: periodically spend a fixed USDC amount from an
    agent's balance to buy a token via Jupiter.

    The plan is policy-governed — each trade runs through the same balance
    check, daily/monthly caps and approval threshold as any other movement, and
    is recorded as a ``swap`` Transaction with a stable ``idempotency_key`` so a
    scheduler re-run can never double-pay.
    """

    __tablename__ = "dca_plans"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_mint = Column(String, nullable=False)  # SPL token mint to buy
    token_symbol = Column(String, nullable=True)  # human label, e.g. "SOL"
    token_decimals = Column(Integer, default=9)
    amount_per_cycle = Column(Numeric(20, 6), nullable=False)  # USDC per trade
    frequency = Column(Enum(DcaFrequency), nullable=False)
    status = Column(Enum(DcaStatus), default=DcaStatus.active)
    runs_completed = Column(Integer, default=0)
    total_invested = Column(Numeric(20, 6), default=0)  # summed USDC spent
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agent = relationship("Agent", back_populates="dca_plans")
    user = relationship("User", backref="dca_plans")
    executions = relationship(
        "DcaExecution", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DcaPlan {self.id} {self.token_symbol} {self.frequency.value}>"


class DcaExecution(Base):
    """One scheduled trade attempted by a DCA plan."""

    __tablename__ = "dca_executions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("dca_plans.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(DcaExecutionStatus), default=DcaExecutionStatus.due)
    amount = Column(Numeric(20, 6), nullable=False)  # USDC spent
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    out_amount = Column(Numeric(30, 10), nullable=True)  # token received (sat)
    out_unit = Column(String(24), nullable=True)  # "sat" or token ui amount
    token_mint = Column(String, nullable=True)
    token_symbol = Column(String, nullable=True)
    quote_price = Column(Numeric(30, 12), nullable=True)  # price per token (USDC)
    tx_signature = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("DcaPlan", back_populates="executions")
    agent = relationship("Agent", back_populates="dca_executions")
    user = relationship("User", backref="dca_executions")
    transaction = relationship("Transaction", backref="dca_execution")
