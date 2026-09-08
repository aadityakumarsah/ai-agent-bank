"""
Wallet-ownership authentication.

Proves a client owns a Solana address BEFORE it is allowed to act on that
address's agents/accounts:

* ``POST /auth/nonce``  — returns a message the wallet must sign.
* ``POST /auth/verify`` — verifies the Ed25519 signature over that message and
  returns a short-lived JWT (``sub`` = wallet address).
* ``GET  /auth/me``     — returns the wallet for a valid ``Bearer`` token.

This replaces trusting a bare ``wallet_address`` path/body param as identity.
In MOCK/demo deployments routes still accept a passed wallet for convenience;
in PRODUCTION the ``get_current_user`` dependency (with ``REQUIRE_AUTH=true``)
enforces that the claimed wallet equals the authenticated one.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_auth_challenge,
    decode_token,
    normalize_signature_from_request,
)
from app.db.session import get_db
from app.db.models import User
from app.schemas import (
    AuthNonceOut,
    AuthNonceRequest,
    AuthVerifyOut,
    AuthVerifyRequest,
)

logger = logging.getLogger("app.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


def _verify_wallet_signature(wallet_address: str, message: str, signature: str) -> None:
    try:
        from solders.pubkey import Pubkey
        from solders.signature import Signature
    except ImportError as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Signature verification is unavailable.",
        ) from e

    try:
        pubkey = Pubkey.from_string(wallet_address)
        sig = Signature.from_bytes(normalize_signature_from_request(signature))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid wallet address or signature encoding.",
        ) from e

    if not sig.verify(pubkey, message.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature does not prove ownership of this wallet.",
        )


@router.post("/nonce", response_model=AuthNonceOut)
def get_auth_nonce(payload: AuthNonceRequest) -> AuthNonceOut:
    """Return a message the wallet must sign to prove ownership."""
    challenge = create_auth_challenge(payload.wallet_address)
    return AuthNonceOut(
        wallet_address=payload.wallet_address,
        nonce=challenge["nonce"],
        message=challenge["message"],
        expires_minutes=10,
    )


@router.post("/verify", response_model=AuthVerifyOut)
def verify_signature(payload: AuthVerifyRequest, db: Session = Depends(get_db)) -> AuthVerifyOut:
    """Verify the wallet's signature over the nonce message; issue a JWT."""
    # The message must contain a nonce that decodes as a challenge for this
    # wallet — prevents replaying a signature against another operation.
    lines = payload.message.splitlines()
    nonce_line = next((ln for ln in lines if ln.startswith("Nonce: ")), None)
    if not nonce_line:
        raise HTTPException(status_code=400, detail="Message is missing its Nonce line.")
    nonce = nonce_line.removeprefix("Nonce: ").strip()
    try:
        claims = decode_token(nonce, purpose="auth_challenge")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    if claims.get("sub") != payload.wallet_address:
        raise HTTPException(status_code=401, detail="Nonce belongs to a different wallet.")

    _verify_wallet_signature(payload.wallet_address, payload.message, payload.signature)

    # Ensure a User row exists so downstream wallet-scoped routes work.
    user = db.query(User).filter(User.wallet_address == payload.wallet_address).first()
    if not user:
        user = User(wallet_address=payload.wallet_address)
        db.add(user)
        db.commit()

    token = create_access_token(payload.wallet_address, extra={"purpose": "access"})
    return AuthVerifyOut(
        access_token=token,
        wallet_address=payload.wallet_address,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


def get_current_user(authorization: str | None = Header(None)) -> str:
    """FastAPI dependency: read ``Authorization: Bearer <jwt>`` and return the
    authenticated wallet address. Raises 401 when missing/invalid."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = decode_token(token, purpose="access")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return claims["sub"]


@router.get("/me")
def auth_me(current_wallet: str = Depends(get_current_user)) -> dict:
    """Return the wallet that owns the presented token."""
    return {"wallet_address": current_wallet, "authenticated": True}