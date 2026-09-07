from pydantic import BaseModel, Field
from typing import Optional, List, Any


class UserCreate(BaseModel):
    wallet_address: str = Field(..., description="Solana wallet public key")


class UserOut(BaseModel):
    id: int
    wallet_address: str

    class Config:
        from_attributes = True


class PolicyCreate(BaseModel):
    max_per_transaction: float = Field(..., gt=0)
    max_per_day: float = Field(..., gt=0)
    max_per_month: Optional[float] = Field(default=None, gt=0)
    allowed_categories: List[str] = []
    blocked_human_transfers: bool = True
    blocked_withdrawals: bool = True
    blocked_arbitrary_contracts: bool = True
    require_approval_above: Optional[float] = None
    allowed_recipient_addresses: List[str] = []


class PolicyUpdate(BaseModel):
    max_per_transaction: Optional[float] = Field(default=None, gt=0)
    max_per_day: Optional[float] = Field(default=None, gt=0)
    max_per_month: Optional[float] = Field(default=None, gt=0)
    allowed_categories: Optional[List[str]] = None
    blocked_human_transfers: Optional[bool] = None
    blocked_withdrawals: Optional[bool] = None
    blocked_arbitrary_contracts: Optional[bool] = None
    require_approval_above: Optional[float] = None
    allowed_recipient_addresses: Optional[List[str]] = None


class PolicyOut(BaseModel):
    id: int
    agent_id: int
    max_per_transaction: float
    max_per_day: float
    max_per_month: Optional[float] = None
    allowed_categories: List[str]
    blocked_human_transfers: bool
    blocked_withdrawals: bool
    blocked_arbitrary_contracts: bool
    require_approval_above: Optional[float]
    allowed_recipient_addresses: List[str]

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


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
    description: Optional[str]
    balance: float
    total_spent: float
    status: str
    escrow_address: Optional[str]
    policies: Optional[PolicyOut] = None
    created_at: Optional[str] = None

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
    recipient_name: Optional[str]
    category: Optional[str]
    description: Optional[str]
    tx_hash: Optional[str]
    rejection_reason: Optional[str]
    created_at: Optional[str]


class TaskCreate(BaseModel):
    task: str = Field(..., min_length=1)


class TaskOut(BaseModel):
    run_id: int
    status: str
    result: Optional[str] = None
    blocked: bool = False
    decision: Optional[Any] = None
    transaction: Optional[TransactionOut] = None
    error: Optional[str] = None
    steps: Optional[List[Any]] = None


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
    description: Optional[str] = None
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
    payload: Optional[Any] = None


class ServicePaymentIn(BaseModel):
    agent_id: int
    requested_amount: Optional[float] = None


class ServiceRunIn(BaseModel):
    agent_id: int
    proof: Optional[Any] = None  # optional payment proof {tx_hash: ...}


class ConfigStatusOut(BaseModel):
    payment_mode: str
    payment_configured: bool
    solana_configured: bool
    solana_network: str
    solana_usdc_mint: Optional[str] = None
    rpc_configured: bool = False
    redis_configured: bool
    llm_provider: str
    llm_configured: bool
    use_real_payment: bool
    missing_config: List[str]
