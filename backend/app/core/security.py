"""
JWT + signature primitives for AI Agent Bank.

Two token types (both JWT signed with ``SECRET_KEY``):

* ``auth_challenge`` — short-lived nonce the client signs with their Solana
  wallet to prove ownership of an address. Stateless (no DB writes) and
  single-use by construction (expires in minutes).
* ``access`` — issued after a signature is verified; carries ``wallet`` and
  is what the browser holds for subsequent authenticated requests.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expires(minutes: int) -> datetime:
    return _now() + timedelta(minutes=minutes)


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> str:
    """Signed JWT with an ``exp`` claim. ``subject`` is the wallet address."""
    expire = _expires(expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_auth_challenge(wallet_address: str) -> Dict[str, str]:
    """Return a message + nonce the wallet must sign to authenticate."""
    nonce = create_access_token(
        wallet_address,
        expires_minutes=10,
        extra={"purpose": "auth_challenge"},
    )
    issued = _now()
    expires = _now() + timedelta(minutes=10)
    message = (
        "Sign this message to authenticate with AI Agent Bank.\n"
        f"\nWallet: {wallet_address}"
        f"\nNonce: {nonce}"
        f"\nIssued (UTC): {issued.isoformat()}"
        f"\nExpires (UTC): {expires.isoformat()}"
    )
    return {"nonce": nonce, "message": message}


def decode_token(token: str, *, purpose: Optional[str] = None) -> Dict[str, Any]:
    """Decode + validate a JWT. Raises ``ValueError`` when invalid/expired/wrong purpose."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e
    if purpose and payload.get("purpose") != purpose:
        raise ValueError("Token has the wrong purpose")
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise ValueError("Token is missing a subject")
    return payload


def normalize_signature_from_request(signature: str) -> bytes:
    """Accept a Solana signature as base58 (Phantom/Solflare default), base64,
    or hex and return the raw 64 bytes."""
    s = signature.strip()
    if not s:
        raise ValueError("Empty signature")
    try:
        from solders.signature import Signature

        return bytes(Signature.from_string(s))
    except Exception:  # noqa: BLE001
        pass
    for coder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            decoded = coder(s)
            if len(decoded) == 64:
                return decoded
        except Exception:  # noqa: BLE001
            continue
    try:
        decoded = bytes.fromhex(s)
        if len(decoded) == 64:
            return decoded
    except (ValueError, TypeError):
        pass
    raise ValueError("Signature must be base58, base64, or hex (64 bytes)")