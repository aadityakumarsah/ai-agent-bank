from typing import Any

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    wallet_address: str = Field(..., description="Solana wallet public key")


class UserOut(BaseModel):
    id: int
    wallet_address: str

    class Config:
        from_attributes = True


class AuthNonceRequest(BaseModel):
    wallet_address: str = Field(..., description="Solana wallet public key to authenticate")


class AuthNonceOut(BaseModel):
    wallet_address: str
    nonce: str
    message: str
    expires_minutes: int = 10


class AuthVerifyRequest(BaseModel):
    wallet_address: str
    message: str
    signature: str = Field(..., description="Wallet signature over the challenge message")


class AuthVerifyOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    wallet_address: str
    expires_minutes: int = 0


class PolicyCreate(BaseModel):
    max_per_transaction: float = Field(..., gt=0)
    max_per_day: float = Field(..., gt=0)
    max_per_month: float | None = Field(default=None, gt=0)
    allowed_categories: list[str] = []
    blocked_human_transfers: bool = True
    blocked_withdrawals: bool = True
    blocked_arbitrary_contracts: bool = True
    require_approval_above: float | None = None
    allowed_recipient_addresses: list[str] = []


class PolicyUpdate(BaseModel):
    max_per_transaction: float | None = Field(default=None, gt=0)
    max_per_day: float | None = Field(default=None, gt=0)
    max_per_month: float | None = Field(default=None, gt=0)
    allowed_categories: list[str] | None = None
    blocked_human_transfers: bool | None = None
    blocked_withdrawals: bool | None = None
    blocked_arbitrary_contracts: bool | None = None
    require_approval_above: float | None = None
    allowed_recipient_addresses: list[str] | None = None


class PolicyOut(BaseModel):
    id: int
    agent_id: int
    max_per_transaction: float
    max_per_day: float
    max_per_month: float | None = None
    allowed_categories: list[str]
    blocked_human_transfers: bool
    blocked_withdrawals: bool
    blocked_arbitrary_contracts: bool
    require_approval_above: float | None
    allowed_recipient_addresses: list[str]

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None


class AgentFund(BaseModel):
    amount: float = Field(..., gt=0)


class FundConfirm(BaseModel):
    amount: float = Field(..., gt=0)
    signature: str = Field(..., min_length=1)


class AgentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended|killed)$")


class AgentOut(BaseModel):
    id: int
    name: str
    description: str | None
    balance: float
    total_spent: float
    status: str
    escrow_address: str | None
    policies: PolicyOut | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    agent_id: int
    amount: float
    currency: str
    transaction_type: str
    status: str
    recipient_address: str
    recipient_name: str | None
    category: str | None
    description: str | None
    tx_hash: str | None
    rejection_reason: str | None
    created_at: str | None


class TaskCreate(BaseModel):
    task: str = Field(..., min_length=1)


class TaskOut(BaseModel):
    run_id: int
    status: str
    result: str | None = None
    blocked: bool = False
    decision: Any | None = None
    transaction: TransactionOut | None = None
    error: str | None = None
    steps: list[Any] | None = None


class MessageOut(BaseModel):
    message: str


class LLMKeyInput(BaseModel):
    api_key: str = Field(..., min_length=8, max_length=512)


class LLMKeyStatusOut(BaseModel):
    provider: str
    has_key: bool = False  # user has supplied a key
    source: str  # "user" | "server" | "mock"


class LLMKeySavedOut(BaseModel):
    provider: str
    message: str


class ServiceOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str
    endpoint: str
    wallet_address: str
    price: float
    currency: str
    requires_payment: bool
    active: bool
    risk_level: str
    is_demo: bool

    class Config:
        from_attributes = True


class ServiceRequestIn(BaseModel):
    agent_id: int
    payload: Any | None = None


class ServicePaymentIn(BaseModel):
    agent_id: int
    requested_amount: float | None = None


class ServiceRunIn(BaseModel):
    agent_id: int
    proof: Any | None = None  # optional payment proof {tx_hash: ...}


class ConfigStatusOut(BaseModel):
    payment_mode: str
    payment_configured: bool
    solana_configured: bool
    solana_network: str
    solana_usdc_mint: str | None = None
    rpc_configured: bool = False
    redis_configured: bool
    llm_provider: str
    llm_configured: bool
    use_real_payment: bool
    missing_config: list[str]


# ---------------------------------------------------------------------------
# Real provider marketplace (the "agent buys things" loop)
# ---------------------------------------------------------------------------
class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    adapter: str = Field(..., min_length=1, max_length=64)  # e.g. "mymemory"
    api_base_url: str = Field(..., min_length=5, max_length=512)
    category: str = "api"  # ServiceCategory value
    wallet_address: str = Field(..., min_length=20, max_length=60)
    owner_wallet: str | None = Field(
        default=None,
        description="Explicit wallet identity (demo/staging only; ignored when a Bearer token is present)",
    )
    supports: list[str] = []


class ProviderOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    adapter: str
    api_base_url: str
    category: str
    wallet_address: str
    supports: list[str]
    status: str
    verified: bool
    created_at: str | None = None

    class Config:
        from_attributes = True


class ProviderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|active|suspended)$")


class ListingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = None
    category: str = "api"
    price: float = Field(..., ge=0)
    parameters: Any = {}
    requires_payment: bool = True


class ListingStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|inactive)$")


class ListingOut(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    name: str
    description: str | None = None
    category: str
    price: float
    currency: str
    parameters: Any
    requires_payment: bool
    status: str
    created_at: str | None = None


class QuoteRequest(BaseModel):
    agent_id: int
    payload: Any = {}


class QuoteOut(BaseModel):
    intent_id: int
    status: str
    listing_id: int
    listing_name: str
    provider_id: int
    provider_name: str
    amount: float
    currency: str
    expires_at: str | None = None
    notes: list[str] = []
    quote: Any = None


class PurchaseSubmit(BaseModel):
    intent_id: int


class PurchaseOut(BaseModel):
    id: int
    agent_id: int
    task_run_id: int | None = None
    listing_id: int
    listing_name: str
    provider_id: int
    provider_name: str
    provider_wallet_address: str
    status: str
    request_payload: Any = None
    quote: Any = None
    amount: float | None = None
    transaction_id: int | None = None
    error: str | None = None
    result: Any = None
    created_at: str | None = None
    completed_at: str | None = None


class DcaPlanCreate(BaseModel):
    agent_id: int = Field(..., gt=0)
    token_mint: str = Field(..., min_length=1)
    token_symbol: str | None = None
    token_decimals: int | None = Field(default=9, ge=0, le=36)
    amount_per_cycle: float = Field(..., gt=0)
    frequency: str = Field(..., pattern="^(hourly|daily|weekly)$")
    starts_at: str | None = None
    ends_at: str | None = None


class DcaPlanStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|paused|completed|cancelled)$")


class DcaExecutionOut(BaseModel):
    id: int
    plan_id: int
    agent_id: int
    amount: float | None = None
    status: str
    error: str | None = None
    token_mint: str | None = None
    token_symbol: str | None = None
    out_amount: float | None = None
    out_unit: str | None = None
    quote_price: float | None = None
    transaction_id: int | None = None
    tx_signature: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

    class Config:
        from_attributes = True


class DcaPlanOut(BaseModel):
    id: int
    agent_id: int
    token_mint: str
    token_symbol: str
    token_decimals: int
    amount_per_cycle: float
    frequency: str
    status: str
    runs_completed: int
    total_invested: float
    starts_at: str | None = None
    ends_at: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str | None = None
    executions: list | None = None

    class Config:
        from_attributes = True
