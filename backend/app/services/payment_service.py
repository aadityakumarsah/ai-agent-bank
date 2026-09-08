"""
Solana payment layer for AI Agent Bank.

Provides two interchangeable implementations of :class:`PaymentService`:

* ``MockPaymentService`` — MOCK MODE. Simulates blockchain transactions for
  demos. Every result is explicitly labelled ``simulated=True`` / ``mode="mock"``
  and never pretends to be an on-chain transaction.
* ``SolanaPaymentService`` — REAL MODE. Builds, signs and submits real SPL USDC
  transfers on Solana, then waits for confirmation and can re-verify them.

The policy engine MUST be evaluated before ``execute_payment`` is ever called —
the runtime enforces that ordering (see ``agent_runtime.py``).

Security invariants
-------------------
* The LLM / frontend can never supply private keys, raw instruction bytes,
  program IDs, or serialized transactions. Only validated amounts and
  base58 addresses are accepted.
* Secret keys live only on the backend (``SOLANA_PRIVATE_KEY``) and are never
  exposed through the API.
* Per-agent escrow keypairs are derived deterministically from the master
  keypair on the backend; a derived public key (``escrow_address``) is what gets
  returned to clients.
"""

import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (configurable via environment, not hidden in business logic)
# ---------------------------------------------------------------------------
DEVNET_USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
MAINNET_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDC_DECIMALS = 6
SOL_EXPLORER = "https://explorer.solana.com"


def explorer_tx_url(signature: str, network: str = "devnet") -> str:
    return f"{SOL_EXPLORER}/tx/{signature}?cluster={network}"


def explorer_address_url(address: str, network: str = "devnet") -> str:
    return f"{SOL_EXPLORER}/address/{address}?cluster={network}"


def resolved_network() -> str:
    net = (settings.SOLANA_NETWORK or "devnet").strip().lower()
    if net in ("mainnet", "mainnet-beta"):
        return "mainnet-beta"
    return "devnet"


def resolved_usdc_mint() -> str:
    if settings.SOLANA_USDC_MINT:
        return settings.SOLANA_USDC_MINT.strip()
    if resolved_network() == "mainnet-beta":
        return MAINNET_USDC_MINT
    return DEVNET_USDC_MINT


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------
class PaymentService(ABC):
    """Unified interface used by the rest of the backend."""

    # -- metadata ----------------------------------------------------------
    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """True when this service simulates transactions (MOCK MODE)."""

    @property
    def mode(self) -> str:
        return "mock" if self.is_mock else "solana"

    @property
    def network(self) -> str:
        return resolved_network()

    @property
    def usdc_mint(self) -> str:
        return resolved_usdc_mint()

    @property
    def simulated(self) -> bool:
        return self.is_mock

    # -- spec methods (camelCase aliases) -----------------------------------
    def getBalance(self, address: str) -> Dict[str, Any]:
        return self.get_balance(address)

    def createPaymentRequest(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.create_payment_request(from_address, to_address, amount, memo)

    def estimateFee(
        self,
        from_address: str,
        to_address: str,
        amount: float,
    ) -> Dict[str, Any]:
        return self.estimate_fee(from_address, to_address, amount)

    def executePayment(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
        signer_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.execute_payment(from_address, to_address, amount, memo, signer_context)

    def getTransaction(self, signature: str) -> Dict[str, Any]:
        return self.get_transaction(signature)

    def verifyTransaction(self, signature: str) -> Dict[str, Any]:
        return self.verify_transaction(signature)

    # -- compatibility ------------------------------------------------------
    def transfer_usdc(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Legacy alias. Policy engine must have approved before calling this."""
        return self.execute_payment(from_address, to_address, amount, memo)

    # -- core abstract business methods -------------------------------------
    @abstractmethod
    def get_balance(self, address: str) -> Dict[str, Any]:
        """USDC balance of the SPL-token account(s) owned by ``address``."""

    @abstractmethod
    def create_payment_request(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare a reviewable payment request (what the user confirms)."""

    @abstractmethod
    def estimate_fee(
        self,
        from_address: str,
        to_address: str,
        amount: float,
    ) -> Dict[str, Any]:
        """Estimate network fee in SOL lamports for the transfer."""

    @abstractmethod
    def execute_payment(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
        signer_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a previously policy-allowed payment. Returns + confirms tx."""

    @abstractmethod
    def get_transaction(self, signature: str) -> Dict[str, Any]:
        """Fetch a transaction by on-chain signature."""

    @abstractmethod
    def verify_transaction(self, signature: str) -> Dict[str, Any]:
        """Check confirmation status of a signature."""

    def derive_escrow_address(self, owner_wallet: str, agent_id: int) -> str:
        """Public escrow account for an agent. Secret key never leaves backend."""
        raise NotImplementedError("derive_escrow_address not implemented")

    def _base_result(self, **extra: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "mode": self.mode,
            "network": self.network,
            "simulated": self.simulated,
        }
        out.update(extra)
        return out


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58(data: bytes) -> str:
    """Minimal base58 encoder used only for mock/demo addresses."""
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = BASE58_ALPHABET[r] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + (out or "")


def _mock_address(material: str) -> str:
    return _b58(hashlib.sha256(material.encode()).digest())


# ---------------------------------------------------------------------------
# MOCK MODE
# ---------------------------------------------------------------------------
class MockPaymentService(PaymentService):
    """
    Simulated payment service for demos. Transactions are labelled ``mock_``,
    ``mode="mock"`` and ``simulated=True`` so consumers can never confuse them
    with real on-chain activity. No explorer links are produced.
    """

    @property
    def is_mock(self) -> bool:
        return True

    @property
    def usdc_mint(self) -> str:
        return "mock-usdc"

    def get_balance(self, address: str) -> Dict[str, Any]:
        return self._base_result(
            balance=0.0,
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            ata=None,
            note="MOCK MODE — no on-chain balance is read.",
        )

    def get_sol_balance(self, address: str) -> Dict[str, Any]:
        return self._base_result(balance_sol=0.0)

    def estimate_fee(
        self, from_address: str, to_address: str, amount: float
    ) -> Dict[str, Any]:
        return self._base_result(
            fee_sol=0.000005,
            fee_lamports=5000,
            currency="SOL",
            estimated=True,
            note="MOCK MODE — simulated fee.",
        )

    def create_payment_request(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        signature = "mock_" + hashlib.sha256(
            f"{from_address}{to_address}{amount}{time.time()}".encode()
        ).hexdigest()[:64]
        return self._base_result(
            request_id=str(uuid.uuid4()),
            from_address=from_address,
            to_address=to_address,
            amount=round(float(amount), USDC_DECIMALS),
            currency="USDC",
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            fee=self.estimate_fee(from_address, to_address, amount),
            signature=signature,
            explorer_url=None,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=15)).isoformat(),
            note="MOCK MODE — simulated payment request, no transaction will be broadcast.",
        )

    def execute_payment(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
        signer_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        time.sleep(0.3)  # simulate network latency
        signature = "mock_" + hashlib.sha256(
            f"{from_address}{to_address}{amount}{time.time()}".encode()
        ).hexdigest()[:64]
        logger.info("[MOCK] payment: %s USDC %s -> %s", amount, from_address, to_address)
        return self._base_result(
            success=True,
            tx_hash=signature,
            signature=signature,
            amount=round(float(amount), USDC_DECIMALS),
            from_address=from_address,
            to_address=to_address,
            currency="USDC",
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            confirmed=True,
            slot=None,
            blockhash=None,
            explorer_url=None,
            message="MOCK MODE — simulated payment confirmed",
        )

    def get_transaction(self, signature: str) -> Dict[str, Any]:
        if signature.startswith("mock_"):
            return self._base_result(
                signature=signature,
                confirmed=True,
                slot=None,
                err=None,
                simulated=True,
                transaction=None,
            )
        raise ValueError(f"Unknown mock signature: {signature}")

    def verify_transaction(self, signature: str) -> Dict[str, Any]:
        if signature.startswith("mock_"):
            return self._base_result(
                signature=signature,
                verified=True,
                status="confirmed",
                confirmations=1,
                err=None,
                note="MOCK MODE — simulated confirmation.",
            )
        return self._base_result(
            signature=signature,
            verified=False,
            status="unknown",
            confirmations=None,
            err="Not a mock signature",
        )

    def derive_escrow_address(self, owner_wallet: str, agent_id: int) -> str:
        return _mock_address(f"escrow:{owner_wallet}:{agent_id}")


# ---------------------------------------------------------------------------
# REAL MODE (Solana)
# ---------------------------------------------------------------------------
class SolanaPaymentService(PaymentService):
    """
    Real USDC transfer engine. Requires ``SOLANA_RPC_URL`` + ``SOLANA_PRIVATE_KEY``.

    * Per-agent escrow keypairs are derived deterministically from the master
      keypair (``SOLANA_PRIVATE_KEY``) — never exposed.
    * All inputs are validated (amount > 0, base58 pubkeys).
    * Program ID is fixed server-side to the SPL Token program. No caller
      supplied program IDs, instruction bytes or serialized transactions.
    """

    CONFIRMATION_TIMEOUT_S = 40

    @property
    def is_mock(self) -> bool:
        return False

    def __init__(self) -> None:
        if not settings.SOLANA_RPC_URL:
            raise ValueError(
                "SOLANA_RPC_URL is not configured. Leave blank for MOCK MODE."
            )
        if not settings.SOLANA_PRIVATE_KEY:
            raise ValueError(
                "SOLANA_PRIVATE_KEY is not configured. Leave blank for MOCK MODE."
            )
        self.rpc_url = settings.SOLANA_RPC_URL

        try:
            from solders.keypair import Keypair

            self._master_keypair = Keypair.from_base58_string(settings.SOLANA_PRIVATE_KEY)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Invalid SOLANA_PRIVATE_KEY: {e}") from e

    # -- sdk access ----------------------------------------------------------
    def _sdk(self):
        try:
            from solana.rpc.api import Client
            from solders.pubkey import Pubkey
            from solana.rpc.commitment import Confirmed  # noqa: F401
            return Client(self.rpc_url), Pubkey
        except ImportError as e:
            raise RuntimeError(
                "Solana Python SDK not installed. Run: pip install solana solders "
                "to enable REAL MODE."
            ) from e

    # -- validation ----------------------------------------------------------
    def _validate_amount(self, amount: float) -> Decimal:
        try:
            amount_dec = Decimal(str(amount))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid amount: {amount}") from e
        if not amount_dec.is_finite() or amount_dec <= 0:
            raise ValueError("Amount must be a positive number")
        max_amount = Decimal("100000000")
        if amount_dec > max_amount:
            raise ValueError("Amount exceeds maximum supported transfer size")
        return amount_dec.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

    def _validate_address(self, address: str, label: str = "address") -> str:
        if not address or not isinstance(address, str):
            raise ValueError(f"Invalid {label}")
        address = address.strip()
        if len(address) not in range(32, 45):
            raise ValueError(f"Invalid {label} (bad length)")
        _, Pubkey = self._sdk()
        try:
            Pubkey.from_string(address)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Invalid {label}: {address}") from e
        return address

    # -- key management ------------------------------------------------------
    def _derive_escrow_keypair(self, owner_wallet: str, agent_id: int):
        from solders.keypair import Keypair

        seed = hashlib.sha256(
            f"aibank-escrow:{owner_wallet}:{agent_id}".encode()
            + bytes(self._master_keypair.secret())
        ).digest()
        return Keypair.from_seed(seed)

    def derive_escrow_address(self, owner_wallet: str, agent_id: int) -> str:
        kp = self._derive_escrow_keypair(owner_wallet, agent_id)
        return str(kp.pubkey())

    def _resolver_for(
        self, from_address: str, signer_context: Optional[Dict[str, Any]]
    ) -> Any:
        """
        Returns the keypair we are allowed to sign ``from_address`` with.

        Only two cases are accepted:
          1. The master payer itself (managed by the backend).
          2. An escrow derived from the provided (owner_wallet, agent_id) context.
        Anything else is refused — the AI can't make us sign for wallets we
        don't control.
        """
        if signer_context and signer_context.get("owner_wallet") and signer_context.get("agent_id"):
            kp = self._derive_escrow_keypair(
                str(signer_context["owner_wallet"]), int(signer_context["agent_id"])
            )
            if str(kp.pubkey()) == from_address:
                return kp
        if str(self._master_keypair.pubkey()) == from_address:
            return self._master_keypair
        raise ValueError(
            "Refusing to sign: source address is not a backend-managed escrow "
            "or payer. The AI cannot direct arbitrary signing."
        )

    # -- balances ------------------------------------------------------------
    def get_balance(self, address: str) -> Dict[str, Any]:
        client, Pubkey = self._sdk()
        owner = Pubkey.from_string(self._validate_address(address))
        mint = Pubkey.from_string(self.usdc_mint)
        resp = client.get_token_accounts_by_owner_json_parsed(owner, mint=mint)
        ata_list = resp.value or []
        total = Decimal("0")
        ata = None
        for acct in ata_list:
            try:
                amt = Decimal(
                    str(acct.account.data.parsed["info"]["token_amount"].get("uiAmount") or 0)
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            total += amt
            ata = str(acct.pubkey) if ata is None else ata
        return self._base_result(
            balance=float(total),
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            ata=ata,
            owner=address,
            explorer_url=explorer_address_url(address, self.network) if ata else None,
        )

    def get_sol_balance(self, address: str) -> Dict[str, Any]:
        client, _ = self._sdk()
        lamports = client.get_balance(self._validate_address(address)).value
        return self._base_result(
            balance_sol=float(Decimal(str(lamports)) / Decimal("1000000000")),
            lamports=int(lamports),
        )

    # -- fee ----------------------------------------------------------------
    def estimate_fee(
        self, from_address: str, to_address: str, amount: float
    ) -> Dict[str, Any]:
        lamports = self._estimate_lamports()
        return self._base_result(
            fee_sol=float(Decimal(str(lamports)) / Decimal("1000000000")),
            fee_lamports=int(lamports),
            currency="SOL",
            estimated=True,
        )

    def _estimate_lamports(self) -> int:
        try:
            from solana.rpc.api import Client
            from solders.transaction import Transaction
            from solders.pubkey import Pubkey
            from spl.token.constants import TOKEN_PROGRAM_ID
            from spl.token import models
            from spl.token.instructions import (
                transfer_checked,
                get_associated_token_address,
            )

            client = Client(self.rpc_url)
            client.get_latest_blockhash()  # confirms RPC reachability for quoting
            mint = Pubkey.from_string(self.usdc_mint)
            payer = self._master_keypair
            # ATA addresses can be computed for any owner; fee only depends on
            # message size, so a stand-in recipient is fine for estimation.
            source_ata = get_associated_token_address(payer.pubkey(), mint)
            dest_ata = get_associated_token_address(
                Pubkey.from_string("So11111111111111111111111111111111111111112"), mint
            )
            ix = transfer_checked(
                models.TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source_ata,
                    dest=dest_ata,
                    owner=payer.pubkey(),
                    amount=1,
                    decimals=USDC_DECIMALS,
                    mint=mint,
                )
            )
            tx = Transaction.new_with_payer([ix], payer.pubkey())
            fee = client.get_fee_for_message(tx.message).value
            return int(fee) if fee else 5000
        except Exception as e:  # noqa: BLE001
            logger.warning("Fee estimation failed, using default: %s", e)
            return 5000

    # -- payment request -----------------------------------------------------
    def create_payment_request(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        from_address = self._validate_address(from_address, "from_address")
        to_address = self._validate_address(to_address, "to_address")
        amount_dec = self._validate_amount(amount)
        _, Pubkey = self._sdk()
        from spl.token.constants import TOKEN_PROGRAM_ID
        from spl.token.instructions import get_associated_token_address

        mint = Pubkey.from_string(self.usdc_mint)
        dest_ata = get_associated_token_address(Pubkey.from_string(to_address), mint)
        now = datetime.now(timezone.utc)
        return self._base_result(
            request_id=str(uuid.uuid4()),
            from_address=from_address,
            to_address=to_address,
            to_ata=str(dest_ata),
            amount=float(amount_dec),
            currency="USDC",
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            program_id=str(TOKEN_PROGRAM_ID),
            fee=self.estimate_fee(from_address, to_address, float(amount_dec)),
            signature=None,
            explorer_url=None,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=15)).isoformat(),
        )

    # -- execution -----------------------------------------------------------
    def _pubkey(self, value: str):
        _, Pubkey = self._sdk()
        return Pubkey.from_string(value)

    def execute_payment(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        memo: Optional[str] = None,
        signer_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from_address = self._validate_address(from_address, "from_address")
        to_address = self._validate_address(to_address, "to_address")
        amount_dec = self._validate_amount(amount)
        signer = self._resolver_for(from_address, signer_context)

        from solana.rpc.api import Client
        from solders.transaction import Transaction
        from solders.pubkey import Pubkey
        from spl.token.constants import TOKEN_PROGRAM_ID
        from spl.token import models
        from spl.token.instructions import (
            transfer_checked,
            get_associated_token_address,
        )

        client = Client(self.rpc_url)
        mint = Pubkey.from_string(self.usdc_mint)
        source_ata = get_associated_token_address(signer.pubkey(), mint)
        dest_ata = get_associated_token_address(Pubkey.from_string(to_address), mint)

        transfer_ix = transfer_checked(
            models.TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=source_ata,
                dest=dest_ata,
                owner=signer.pubkey(),
                amount=int(amount_dec * (10**USDC_DECIMALS)),
                decimals=USDC_DECIMALS,
                mint=mint,
            )
        )

        blockhash = client.get_latest_blockhash().value.blockhash
        tx = Transaction.new_with_payer([transfer_ix], signer.pubkey())
        tx.sign([signer], blockhash)

        signature = str(client.send_raw_transaction(bytes(tx)).value)
        logger.info("[SOLANA] submitted %s: %s USDC -> %s", signature, amount, to_address)

        confirmed = self._wait_for_confirmation(client, signature)
        slot = confirmed.get("slot")

        return self._base_result(
            success=True,
            tx_hash=signature,
            signature=signature,
            amount=float(amount_dec),
            from_address=from_address,
            to_address=to_address,
            from_ata=str(source_ata),
            to_ata=str(dest_ata),
            currency="USDC",
            mint=self.usdc_mint,
            decimals=USDC_DECIMALS,
            confirmed=confirmed.get("confirmed", True),
            slot=slot,
            blockhash=blockhash,
            explorer_url=explorer_tx_url(signature, self.network),
            message="USDC transfer submitted and confirmed on Solana",
        )

    def _wait_for_confirmation(self, client, signature: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Poll signature status until confirmed/finalized or timeout."""
        deadline = time.monotonic() + (timeout or self.CONFIRMATION_TIMEOUT_S)
        last: Dict[str, Any] = {"confirmed": False}
        while time.monotonic() < deadline:
            try:
                resp = client.get_signature_statuses([signature])
            except Exception as e:  # noqa: BLE001
                logger.warning("confirmation poll error: %s", e)
                time.sleep(1)
                continue
            value = (resp.value or [None])[0]
            if value is None:
                time.sleep(0.8)
                continue
            err = getattr(value, "err", None)
            last = {
                "confirmed": True,
                "slot": getattr(value, "slot", None),
                "err": str(err) if err else None,
                "confirmation_status": (
                    getattr(value, "confirmation_status", "confirmed") or "confirmed"
                ),
            }
            if err is None:
                return last
            break
        return last

    def get_transaction(self, signature: str) -> Dict[str, Any]:
        client, _ = self._sdk()
        resp = client.get_transaction(
            signature,
            commitment="confirmed",
            encoding="jsonParsed",
            max_supported_transaction_version=0,
        )
        value = getattr(resp, "value", None)
        if value is None:
            raise ValueError(f"Transaction not found: {signature}")
        meta = getattr(value, "meta", None) or {}
        return self._base_result(
            signature=signature,
            found=True,
            confirmed=meta.get("err") is None,
            slot=getattr(value, "slot", None),
            err=meta.get("err"),
            block_time=getattr(value, "block_time", None),
            fee=meta.get("fee"),
            explorer_url=explorer_tx_url(signature, self.network),
        )

    def verify_transaction(self, signature: str) -> Dict[str, Any]:
        try:
            tx = self.get_transaction(signature)
        except ValueError as e:
            return self._base_result(
                signature=signature,
                verified=False,
                status="not_found",
                confirmations=None,
                err=str(e),
            )
        verified = bool(tx.get("confirmed"))
        return self._base_result(
            signature=signature,
            verified=verified,
            status="confirmed" if verified else "failed",
            confirmations=None,
            err=tx.get("err"),
            slot=tx.get("slot"),
            explorer_url=tx.get("explorer_url"),
        )


# ---------------------------------------------------------------------------
# Factory + singleton
# ---------------------------------------------------------------------------
def get_payment_service() -> PaymentService:
    if (
        settings.USE_REAL_PAYMENT
        and settings.SOLANA_RPC_URL
        and settings.SOLANA_PRIVATE_KEY
    ):
        try:
            return SolanaPaymentService()
        except ValueError as e:
            logger.warning("Real payment requested but not configured: %s", e)
            if settings.is_production:
                # Never silently downgrade real money to mock in production.
                raise RuntimeError(
                    "USE_REAL_PAYMENT=true but Solana payment is misconfigured. "
                    f"{e}"
                ) from e
            logger.warning("Falling back to MOCK MODE.")
    elif settings.USE_REAL_PAYMENT and settings.is_production:
        raise RuntimeError(
            "USE_REAL_PAYMENT=true in production requires SOLANA_RPC_URL and "
            "SOLANA_PRIVATE_KEY. Set them or turn USE_REAL_PAYMENT off."
        )
    return MockPaymentService()


payment_service = get_payment_service()