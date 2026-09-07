"""
Domain errors for AI Agent Bank.

Each error carries a stable ``code`` and a user-facing ``detail`` that is safe to
show in the UI. Technical details (stack traces, exception chaining) are logged
server-side by the exception handlers and never returned to clients.
"""

from typing import Optional


class AIBankError(Exception):
    """Base class for all expected, user-facing application errors."""

    status_code = 400
    code = "error"

    def __init__(
        self,
        detail: str = "Something went wrong.",
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class AgentRevokedError(AIBankError):
    status_code = 403
    code = "agent_revoked"

    def __init__(self, detail: str = "Agent is revoked and can no longer transact."):
        super().__init__(detail)


class AgentSuspendedError(AIBankError):
    status_code = 403
    code = "agent_suspended"

    def __init__(self, detail: str = "Agent is suspended and cannot transact right now."):
        super().__init__(detail)


class InsufficientBalanceError(AIBankError):
    status_code = 400
    code = "insufficient_balance"

    def __init__(self, requested: float, balance: float):
        super().__init__(
            f"Insufficient balance. Requested ${requested:.6f} but the agent only has ${balance:.6f}."
        )
        self.requested = requested
        self.balance = balance


class InvalidAmountError(AIBankError):
    status_code = 400
    code = "invalid_amount"

    def __init__(self, detail: str = "Amount must be a positive number."):
        super().__init__(detail)


class InvalidRecipientError(AIBankError):
    status_code = 400
    code = "invalid_recipient"

    def __init__(self, detail: str = "Recipient address is missing or malformed."):
        super().__init__(detail)


class ProviderUnavailableError(AIBankError):
    status_code = 503
    code = "provider_unavailable"

    def __init__(self, detail: str = "The external provider is unavailable. Try again shortly."):
        super().__init__(detail)


class DatabaseUnavailableError(AIBankError):
    status_code = 503
    code = "database_unavailable"

    def __init__(self, detail: str = "The database is unavailable. Try again shortly."):
        super().__init__(detail)


class TransactionTimeoutError(AIBankError):
    status_code = 504
    code = "transaction_timeout"

    def __init__(self, detail: str = "The payment timed out before confirmation. No money moved without a signature."):
        super().__init__(detail)


class ApprovalExpiredError(AIBankError):
    status_code = 410
    code = "approval_expired"

    def __init__(self, detail: str = "This approval has expired and can no longer be acted on."):
        super().__init__(detail)


class DuplicatePaymentError(AIBankError):
    status_code = 409
    code = "duplicate_request"

    def __init__(self, detail: str = "This payment request was already processed."):
        super().__init__(detail)


class RateLimitedError(AIBankError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, detail: str = "Too many requests. Please slow down and try again."):
        super().__init__(detail)


class WalletDisconnectedError(AIBankError):
    status_code = 401
    code = "wallet_disconnected"

    def __init__(self, detail: str = "No wallet is connected for this request."):
        super().__init__(detail)