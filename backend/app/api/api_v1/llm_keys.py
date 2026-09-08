from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.api.deps import require_wallet_ownership
from app.db.models import User, UserAPIKey
from app.schemas import LLMKeyInput, LLMKeySavedOut, LLMKeyStatusOut
from app.services.secrets import encrypt_secret

router = APIRouter(
    prefix="/users/{wallet_address}/llm-keys",
    tags=["llm-keys"],
    dependencies=[Depends(require_wallet_ownership)],
)

PROVIDERS = ["openai", "anthropic", "google"]

_SERVER_SOURCE = {
    "openai": bool(settings.OPENAI_API_KEY),
    "anthropic": bool(settings.ANTHROPIC_API_KEY),
    "google": bool(settings.GOOGLE_AI_API_KEY),
}


def _get_user(wallet_address: str, db: Session) -> User:
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _require_provider(provider: str) -> str:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    return provider


@router.get("", response_model=List[LLMKeyStatusOut])
def list_llm_keys(
    wallet_address: str, db: Session = Depends(get_db)
) -> List[LLMKeyStatusOut]:
    """Report which providers the wallet has configured. Never returns a raw key."""
    user = _get_user(wallet_address, db)
    set_providers = {
        k.provider
        for k in db.query(UserAPIKey).filter(UserAPIKey.user_id == user.id).all()
    }
    return [
        LLMKeyStatusOut(
            provider=p,
            has_key=p in set_providers,
            source="user" if p in set_providers else ("server" if _SERVER_SOURCE[p] else "mock"),
        )
        for p in PROVIDERS
    ]


@router.put("/{provider}", response_model=LLMKeySavedOut)
def set_llm_key(
    wallet_address: str,
    provider: str,
    payload: LLMKeyInput,
    db: Session = Depends(get_db),
) -> LLMKeySavedOut:
    """Encrypt and store an end-user API key for a provider (upsert)."""
    provider = _require_provider(provider)
    user = _get_user(wallet_address, db)

    row = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == user.id, UserAPIKey.provider == provider)
        .first()
    )
    if row is None:
        row = UserAPIKey(user_id=user.id, provider=provider, encrypted_key="")
        db.add(row)
    row.encrypted_key = encrypt_secret(payload.api_key)
    db.commit()
    return LLMKeySavedOut(provider=provider, message=f"{provider} API key saved")


@router.delete("/{provider}", response_model=LLMKeySavedOut)
def delete_llm_key(
    wallet_address: str,
    provider: str,
    db: Session = Depends(get_db),
) -> LLMKeySavedOut:
    """Remove a wallet's stored key for a provider."""
    provider = _require_provider(provider)
    user = _get_user(wallet_address, db)

    row = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == user.id, UserAPIKey.provider == provider)
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return LLMKeySavedOut(provider=provider, message=f"{provider} API key removed")