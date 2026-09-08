from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from app.api.api_v1.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db as get_db_session

# Re-export the database session dependency
get_db = get_db_session

# OAuth2 scheme kept for compatibility; real auth lives in app.api.api_v1.auth
oauth2_scheme = None  # type: ignore


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    lowered = authorization.strip()
    if lowered.lower().startswith("bearer "):
        return lowered[len("bearer ") :].strip()
    return None


def get_authenticated_wallet(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Return the authenticated wallet from ``Authorization: Bearer``.

    * ``REQUIRE_AUTH`` off (MOCK/demo): returns ``None`` so legacy wallet-scoped
      routes keep working.
    * ``REQUIRE_AUTH`` on: requires a valid token, else 401.
    """
    if not settings.REQUIRE_AUTH:
        return None
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user(f"Bearer {token}")


def require_wallet_ownership(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Router-level guard for ``/users/{wallet_address}/...`` routers.

    When ``REQUIRE_AUTH`` is on, verifies the authenticated wallet equals the
    wallet named in the request path (403 otherwise). Off in demo mode.
    """
    if not settings.REQUIRE_AUTH:
        return None
    auth_wallet = get_authenticated_wallet(authorization)
    path_wallet = request.path_params.get("wallet_address")
    if path_wallet and path_wallet != auth_wallet:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated wallet does not match the requested wallet.",
        )
    return auth_wallet


# Re-export for routes that want the identity explicitly typed.
def get_current_wallet(
    wallet: Optional[str] = Depends(get_authenticated_wallet),
) -> Optional[str]:
    return wallet