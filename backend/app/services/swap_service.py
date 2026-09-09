"""
Token swap layer for AI Agent Bank (DCA trading).

Two interchangeable implementations of :class:`SwapService`:

* ``MockSwapService`` — MOCK MODE. Simulates a swap with a deterministic
  ``mock_``-prefixed signature and ``simulated=True``.
* ``JupiterSwapService`` — REAL MODE. Quotes a route on Jupiter's swap API and
  builds, signs and submits the swap transaction, then waits for confirmation.

Security invariants (mirroring ``payment_service``):
* The LLM / frontend can never inject arbitrary program IDs, instruction bytes
  or serialized transactions — the swap transaction is fetched FROM Jupiter for
  a fixed input/output mint + amount, and signed ONLY with the backend-derived
  per-agent escrow keypair.
* Secret keys live only on the backend and are never exposed.
"""

import base64
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Jupiter's USDC mint by network. The payment layer may use a different
# SPL-token faucet mint; swaps use the mint Jupiter actually has liquidity for.
DEVNET_SWAP_USDC_MINT = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
MAINNET_SWAP_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def resolved_network() -> str:
    net = (settings.SOLANA_NETWORK or "devnet").strip().lower()
    if net in ("mainnet", "mainnet-beta"):
        return "mainnet-beta"
    return "devnet"


def resolved_swap_usdc_mint() -> str:
    if settings.SWAP_USDC_MINT:
        return settings.SWAP_USDC_MINT.strip()
    return (
        MAINNET_SWAP_USDC_MINT
        if resolved_network() == "mainnet-beta"
        else DEVNET_SWAP_USDC_MINT
    )


class SwapService(ABC):
    """Unified swap interface."""

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """True when this service simulates swaps (MOCK MODE)."""

    @property
    def mode(self) -> str:
        return "mock" if self.is_mock else "jupiter"

    @property
    def simulated(self) -> bool:
        return self.is_mock

    @property
    def usdc_mint(self) -> str:
        return resolved_swap_usdc_mint()

    @abstractmethod
    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        """Return a best-route quote for swapping ``amount`` USDC -> token."""

    @abstractmethod
    def execute_swap(
        self,
        *,
        owner_wallet: str,
        agent_id: int,
        escrow_address: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        """Execute a swap, signed by the agent's escrow. Returns ``{success,
        signature, out_amount, quote_price, ...}``. Never raises for business
        conditions."""


class MockSwapService(SwapService):
    """DEMO-only simulated swap. Clearly labelled ``simulated=True``."""

    @property
    def is_mock(self) -> bool:
        return True

    def _rand(self) -> str:
        import uuid

        return "mock_" + uuid.uuid4().hex

    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        # Deterministic-but-plausible mock: 1 USDC -> 1 output unit at par, so a
        # $amount swap yields ``amount`` units. Asymmetric mints (SOL) use a
        # fixed demo price so downstream code paths exercise decimals/price.
        price = 1.0
        if output_mint in ("So11111111111111111111111111111111111111112",):
            price = 0.002
        dec = 9 if output_mint in ("So11111111111111111111111111111111111111112",) else 6
        out_amount = round(amount / price, dec)
        return {
            "success": True,
            "input_mint": input_mint,
            "output_mint": output_mint,
            "in_amount": amount,
            "out_amount": out_amount,
            "quote_price": price,
            "slippage_bps": slippage_bps or settings.JUPITER_DEFAULT_SLIPPAGE_BPS,
            "price_impact_pct": 0.0,
            "simulated": True,
            "mode": "mock",
        }

    def execute_swap(
        self,
        *,
        owner_wallet: str,
        agent_id: int,
        escrow_address: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        q = self.quote(input_mint, output_mint, amount, slippage_bps)
        sig = self._rand()
        return {
            "success": True,
            "signature": sig,
            "tx_hash": sig,
            "out_amount": q["out_amount"],
            "quote_price": q["quote_price"],
            "input_mint": input_mint,
            "output_mint": output_mint,
            "amount": amount,
            "from_address": escrow_address,
            "confirmed": True,
            "simulated": True,
            "mode": "mock",
            "explorer_url": None,
            "message": "Mock swap executed (simulated — no real tokens moved).",
        }


class JupiterSwapService(SwapService):
    """REAL Jupiter DEX swaps. Requires SOLANA_RPC_URL + SOLANA_PRIVATE_KEY."""

    def __init__(self, rpc_url: str, private_key: str):
        self.rpc_url = rpc_url
        self.private_key = private_key
        self._master_keypair = None

    @property
    def is_mock(self) -> bool:
        return False

    def _sdk(self):
        from solana.rpc.api import Client

        return Client(self.rpc_url)

    def _master(self):
        if self._master_keypair is None:
            from solders.keypair import Keypair

            if not self.private_key:
                raise ValueError("SOLANA_PRIVATE_KEY is not configured for real swaps.")
            self._master_keypair = Keypair.from_base58_string(self.private_key)
        return self._master_keypair

    def _resolve_escrow(self, owner_wallet: str, agent_id: int):
        """Deterministic per-agent escrow keypair (same scheme as payments)."""
        import hashlib

        from solders.keypair import Keypair

        seed = hashlib.sha256(
            f"aibank-escrow:{owner_wallet}:{agent_id}".encode()
            + bytes(self._master().secret())
        ).digest()
        return Keypair.from_seed(seed)

    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        slippage = slippage_bps or settings.JUPITER_DEFAULT_SLIPPAGE_BPS
        in_amount = round(amount * (10**6))
        if in_amount <= 0:
            raise ValueError("Swap amount must be positive.")
        resp = httpx.get(
            settings.JUPITER_QUOTE_URL,
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": in_amount,
                "slippageBps": slippage,
                "onlyDirectRoutes": "false",
                "maxAccounts": 20,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise ValueError(data.get("error"))
        out_amount = float(int(data.get("outAmount") or 0)) / (10**6)
        price = (
            (float(data.get("inAmount") or 0) / (10**6)) / out_amount
            if out_amount
            else 0.0
        )
        return {
            "success": True,
            "input_mint": input_mint,
            "output_mint": output_mint,
            "in_amount": amount,
            "out_amount": out_amount,
            "quote_price": price,
            "slippage_bps": slippage,
            "price_impact_pct": data.get("priceImpactPct"),
            "route_plan": data.get("routePlan"),
            "other_amount_threshold": data.get("otherAmountThreshold"),
            "quote_response": data,
            "simulated": False,
            "mode": "jupiter",
        }

    def execute_swap(
        self,
        *,
        owner_wallet: str,
        agent_id: int,
        escrow_address: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None = None,
    ) -> dict[str, Any]:
        try:
            return self._do_swap(
                owner_wallet=owner_wallet,
                agent_id=agent_id,
                escrow_address=escrow_address,
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage_bps,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("real swap failed: %s", e)
            return {"success": False, "error": str(e)}

    def _do_swap(
        self,
        *,
        owner_wallet: str,
        agent_id: int,
        escrow_address: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int | None,
    ) -> dict[str, Any]:
        from solders.transaction import VersionedTransaction

        quote = self.quote(input_mint, output_mint, amount, slippage_bps)
        quote_response = quote["quote_response"]

        signer = self._resolve_escrow(owner_wallet, agent_id)
        if str(signer.pubkey()) != escrow_address:
            raise ValueError(
                "Refusing to swap: escrow does not match the backend-managed "
                "keypair for this agent."
            )

        swap_resp = httpx.post(
            settings.JUPITER_SWAP_URL,
            json={
                "quoteResponse": quote_response,
                "userPublicKey": escrow_address,
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": 0,
            },
            timeout=30.0,
        )
        swap_resp.raise_for_status()
        swap_data = swap_resp.json()
        if swap_data.get("error"):
            raise ValueError(swap_data.get("error"))
        swap_b64 = swap_data.get("swapTransaction") or swap_data.get("tx")
        if not swap_b64:
            raise ValueError("Jupiter returned no swap transaction.")
        raw = base64.b64decode(swap_b64)
        tx = VersionedTransaction.deserialize(raw)

        # Build a fully-signed versioned transaction: Jupiter returns a
        # versioned message with the user listed as a signer; we supply the
        # escrow signature. The whole signed tx is then sent raw.
        signed = VersionedTransaction(tx.message, [signer])
        raw_signed = bytes(signed)

        client = self._sdk()
        resp = client.send_raw_transaction(raw_signed)
        sig = str(resp.value)
        logger.info("[JUPITER] submitted swap %s: %s USDC -> %s", sig, amount, output_mint)

        # wait for confirmation
        deadline = time.monotonic() + 40
        confirmed = False
        err = None
        slot = None
        while time.monotonic() < deadline:
            try:
                sresp = client.get_signature_statuses([sig])
            except Exception:  # noqa: BLE001
                time.sleep(1)
                continue
            value = (sresp.value or [None])[0]
            if value is None:
                time.sleep(0.8)
                continue
            slot = getattr(value, "slot", None)
            err = str(getattr(value, "err", None)) if getattr(value, "err", None) else None
            if err is None:
                confirmed = True
                break
        return {
            "success": confirmed,
            "signature": sig,
            "tx_hash": sig,
            "out_amount": quote["out_amount"],
            "quote_price": quote["quote_price"],
            "input_mint": input_mint,
            "output_mint": output_mint,
            "amount": amount,
            "from_address": escrow_address,
            "confirmed": confirmed,
            "slot": slot,
            "err": err,
            "simulated": False,
            "mode": "jupiter",
            "explorer_url": (
                f"https://explorer.solana.com/tx/{sig}?cluster={resolved_network()}"
            ),
            "message": "Swap confirmed on Solana" if confirmed else "Swap submitted",
        }


def get_swap_service() -> SwapService:
    """Factory. Returns a real Jupiter swap when real payment creds are set and
    the network is live; otherwise a clearly-labelled mock."""
    if (
        settings.USE_REAL_PAYMENT
        and settings.SOLANA_RPC_URL
        and settings.SOLANA_PRIVATE_KEY
    ):
        try:
            # Probe reachability so a dead RPC doesn't silently fall to mock.
            jup = JupiterSwapService(settings.SOLANA_RPC_URL, settings.SOLANA_PRIVATE_KEY)
            if not jup._sdk().is_connected():
                raise RuntimeError("Solana RPC is not reachable for swaps")
            return jup
        except Exception as e:  # noqa: BLE001
            logger.warning("Jupiter swap unavailable, falling back to mock: %s", e)
    return MockSwapService()


swap_service = get_swap_service()