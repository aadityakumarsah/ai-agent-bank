"""Encryption helpers for storing end-user-supplied secrets (e.g. LLM keys).

We never store a raw API key. Values are encrypted with Fernet using a key
from ``settings.LLM_KEY_ENCRYPTION_KEY`` (a urlsafe base64 of 32 bytes). When
no key is configured we derive a stable value from ``SECRET_KEY`` so the
feature keeps working out of the box; production should set an explicit key.
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    configured = settings.LLM_KEY_ENCRYPTION_KEY
    if configured:
        try:
            return Fernet(configured.encode("utf-8"))
        except (ValueError, TypeError):
            logger.warning(
                "LLM_KEY_ENCRYPTION_KEY is not a valid Fernet key; deriving from SECRET_KEY"
            )
    digest = hashlib.sha256((settings.SECRET_KEY or "aibank").encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    """Return an encrypted (Fernet token) string for storage."""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Return the decrypted plaintext, or "" if the token can't be decrypted."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):  # pragma: no cover - defensive
        return ""