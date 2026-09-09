"""
Marketplace registry + purchase API for the real provider marketplace.

These are the HTTP endpoints the frontend uses to see providers/listings,
register a real provider, and inspect/interact with purchases. The agent's
tool loop drives the same business logic through ``PurchaseService``.
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps as auth_deps
from app.core.config import settings
from app.db.models import (
    Agent,
    ListingStatus,
    ProviderProfile,
    ProviderStatus,
    PurchaseIntent,
    ServiceCategory,
    ServiceListing,
    User,
)
from app.db.session import get_db
from app.schemas import (
    ListingCreate,
    ListingOut,
    ListingStatusUpdate,
    ProviderCreate,
    ProviderOut,
    ProviderStatusUpdate,
    PurchaseOut,
    PurchaseSubmit,
    QuoteOut,
    QuoteRequest,
)
from app.services.provider_adapters import (
    ProviderAdapterError,
    build_adapter,
)
from app.services.purchase_service import purchase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

BASE58_ALPHABET = set(
    "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
)


def _provider_status_safe(provider: ProviderProfile) -> str:
    return provider.status.value if provider.status else "pending"


def _provider_to_out(provider: ProviderProfile) -> ProviderOut:
    try:
        supports = json.loads(provider.supports or "[]")
    except (json.JSONDecodeError, TypeError):
        supports = []
    return ProviderOut(
        id=provider.id,
        name=provider.name,
        description=provider.description,
        adapter=provider.adapter,
        api_base_url=provider.api_base_url,
        category=provider.category.value,
        wallet_address=provider.wallet_address,
        supports=supports,
        status=_provider_status_safe(provider),
        verified=bool(provider.verified),
        created_at=provider.created_at.isoformat() if provider.created_at else None,
    )


def _listing_to_out(listing: ServiceListing) -> ListingOut:
    try:
        parameters = json.loads(listing.parameters or "{}")
    except (json.JSONDecodeError, TypeError):
        parameters = {}
    return ListingOut(
        id=listing.id,
        provider_id=listing.provider_id,
        provider_name=listing.provider.name,
        name=listing.name,
        description=listing.description,
        category=listing.category.value,
        price=float(listing.price),
        currency=listing.currency,
        parameters=parameters,
        requires_payment=listing.requires_payment,
        status=listing.status.value,
        created_at=listing.created_at.isoformat() if listing.created_at else None,
    )


def _resolve_owner(
    authorization: Optional[str],
    override_wallet: Optional[str] = None,
) -> Optional[str]:
    """Authenticated wallet, or an explicit override wallet in demo (auth-off)
    mode (matching how ``require_wallet_ownership`` behaves elsewhere: identity
    is only enforced when REQUIRE_AUTH is on)."""
    owner = auth_deps.get_authenticated_wallet(authorization)
    if settings.REQUIRE_AUTH:
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide a Bearer token.",
            )
        if override_wallet and override_wallet != owner:
            raise HTTPException(
                status_code=403,
                detail="owner_wallet does not match the authenticated wallet.",
            )
        return owner
    return owner or override_wallet


def _get_user(db: Session, wallet: str) -> User:
    user = db.query(User).filter(User.wallet_address == wallet).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_agent(db: Session, agent_id: int, wallet: Optional[str]) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if wallet is not None:
        user = _get_user(db, wallet)
        if agent.user_id != user.id:
            raise HTTPException(status_code=403, detail="This agent does not belong to the wallet.")
    return agent


def _get_provider_for_owner(db: Session, provider_id: int, wallet: Optional[str]) -> ProviderProfile:
    provider = db.query(ProviderProfile).filter(ProviderProfile.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if wallet is not None:
        user = _get_user(db, wallet)
        if provider.owner_user_id != user.id:
            raise HTTPException(status_code=403, detail="This provider does not belong to the wallet.")
    return provider


def _validate_solana_address(address: str) -> str:
    if len(address) < 32 or len(address) > 44:
        raise HTTPException(status_code=400, detail="wallet_address must be a base58 Solana address.")
    if not all(c in BASE58_ALPHABET for c in address):
        raise HTTPException(status_code=400, detail="wallet_address is not valid base58.")
    return address


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
@router.post("/providers", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def register_provider(
    payload: ProviderCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Register a real, payable provider integration. The adapter is health-
    checked against the advertised base URL; only reachable integrations are
    marked verified and active."""
    owner = _resolve_owner(authorization, getattr(payload, "owner_wallet", None))
    user = _get_user(db, owner)

    try:
        adapter = build_adapter(payload.adapter)
    except ProviderAdapterError as e:
        raise HTTPException(status_code=400, detail=str(e))

    category_values = [c.value for c in ServiceCategory]
    if payload.category not in category_values:
        raise HTTPException(status_code=400, detail=f"Unknown category: {payload.category}")

    if db.query(ProviderProfile).filter(ProviderProfile.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A provider with this name already exists.")

    _validate_solana_address(payload.wallet_address)

    known = adapter.capability_names()
    for cap in payload.supports:
        if cap not in known:
            raise HTTPException(
                status_code=400,
                detail=f"Adapter '{payload.adapter}' does not support '{cap}'. Supported: {known}",
            )

    ok, message = adapter.health_check(payload.api_base_url)
    provider = ProviderProfile(
        owner_user_id=user.id,
        name=payload.name,
        description=payload.description,
        adapter=payload.adapter,
        api_base_url=payload.api_base_url.strip(),
        category=ServiceCategory(payload.category),
        wallet_address=payload.wallet_address,
        supports=json.dumps(payload.supports or known),
        status=ProviderStatus.active if ok else ProviderStatus.pending,
        verified=ok,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    if not ok:
        logger.warning("provider %s registered but health check failed: %s", provider.name, message)
    return _provider_to_out(provider)


@router.get("/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db)):
    providers = db.query(ProviderProfile).order_by(ProviderProfile.name).all()
    return [_provider_to_out(p) for p in providers]


@router.get("/providers/{provider_id}", response_model=ProviderOut)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(ProviderProfile).filter(ProviderProfile.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _provider_to_out(provider)


@router.patch("/providers/{provider_id}/status", response_model=ProviderOut)
def update_provider_status(
    provider_id: int,
    payload: ProviderStatusUpdate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    provider = _get_provider_for_owner(db, provider_id, owner)
    provider.status = ProviderStatus(payload.status)
    db.commit()
    db.refresh(provider)
    return _provider_to_out(provider)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------
@router.post("/providers/{provider_id}/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    provider_id: int,
    payload: ListingCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    provider = _get_provider_for_owner(db, provider_id, owner)

    category_values = [c.value for c in ServiceCategory]
    if payload.category not in category_values:
        raise HTTPException(status_code=400, detail=f"Unknown category: {payload.category}")

    if (
        db.query(ServiceListing)
        .filter(ServiceListing.provider_id == provider.id, ServiceListing.name == payload.name)
        .first()
    ):
        raise HTTPException(status_code=400, detail="This provider already has a listing with that name.")

    listing = ServiceListing(
        provider_id=provider.id,
        name=payload.name,
        description=payload.description,
        category=ServiceCategory(payload.category),
        price=payload.price,
        requires_payment=payload.requires_payment,
        parameters=json.dumps(payload.parameters or {}),
    )
    adapter = build_adapter(provider.adapter)
    issues = adapter.validate_listing(listing)
    if issues:
        raise HTTPException(status_code=400, detail="Listing incompatible with adapter: " + "; ".join(issues))

    db.add(listing)
    db.commit()
    db.refresh(listing)
    return _listing_to_out(listing)


@router.patch("/listings/{listing_id}/status", response_model=ListingOut)
def update_listing_status(
    listing_id: int,
    payload: ListingStatusUpdate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _get_provider_for_owner(db, listing.provider_id, owner)
    listing.status = ListingStatus(payload.status)
    db.commit()
    db.refresh(listing)
    return _listing_to_out(listing)


@router.get("/listings", response_model=List[ListingOut])
def list_listings(db: Session = Depends(get_db)):
    listings = (
        db.query(ServiceListing)
        .filter(ServiceListing.status == ListingStatus.active)
        .order_by(ServiceListing.name)
        .all()
    )
    return [_listing_to_out(l) for l in listings]


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_to_out(listing)


# ---------------------------------------------------------------------------
# Quotes + purchases
# ---------------------------------------------------------------------------
@router.post("/listings/{listing_id}/quote", response_model=QuoteOut)
def quote_listing(
    listing_id: int,
    payload: QuoteRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    agent = _get_agent(db, payload.agent_id, owner)
    try:
        listing = purchase_service.get_listing(db, listing_id)
        intent = purchase_service.create_quote(
            db, agent, listing, payload.payload or {}, task_run_id=None
        )
    except ProviderAdapterError as e:
        raise HTTPException(status_code=400, detail=str(e))
    quote = json.loads(intent.quote or "{}")
    return QuoteOut(
        intent_id=intent.id,
        status=intent.status.value,
        listing_id=listing.id,
        listing_name=listing.name,
        provider_id=listing.provider_id,
        provider_name=listing.provider.name,
        amount=float(intent.amount or 0),
        currency=quote.get("currency", "USDC"),
        expires_at=quote.get("expires_at"),
        notes=quote.get("notes", []),
        quote=quote,
    )


@router.post("/purchases")
def submit_purchase(
    payload: PurchaseSubmit,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    intent = db.query(PurchaseIntent).filter(PurchaseIntent.id == payload.intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")
    agent = _get_agent(db, intent.agent_id, owner)
    return purchase_service.submit(db, agent, intent.id)


@router.get("/purchases", response_model=List[PurchaseOut])
def list_purchases(
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    owner = _resolve_owner(authorization)
    if agent_id is None:
        if owner is None:
            raise HTTPException(status_code=400, detail="agent_id is required in demo mode.")
        user = _get_user(db, owner)
        intents = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.user_id == user.id)
            .order_by(PurchaseIntent.created_at.desc())
            .all()
        )
    else:
        agent = _get_agent(db, agent_id, owner)
        intents = (
            db.query(PurchaseIntent)
            .filter(PurchaseIntent.agent_id == agent.id)
            .order_by(PurchaseIntent.created_at.desc())
            .all()
        )
    return [_purchase_to_out(i) for i in intents]


@router.get("/purchases/{intent_id}", response_model=PurchaseOut)
def get_purchase(
    intent_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    owner = _resolve_owner(authorization)
    intent = db.query(PurchaseIntent).filter(PurchaseIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")
    if owner is not None:
        user = _get_user(db, owner)
        if intent.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not your purchase.")
    return _purchase_to_out(intent)


def _purchase_to_out(intent: PurchaseIntent) -> PurchaseOut:
    def _read(text: str, default=None):
        if not text:
            return default
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return default

    return PurchaseOut(
        id=intent.id,
        agent_id=intent.agent_id,
        task_run_id=intent.task_run_id,
        listing_id=intent.listing_id,
        listing_name=intent.listing.name if intent.listing else None,
        provider_id=intent.provider_id,
        provider_name=intent.provider.name if intent.provider else None,
        provider_wallet_address=intent.provider.wallet_address if intent.provider else None,
        status=intent.status.value,
        request_payload=_read(intent.request_payload, {}),
        quote=_read(intent.quote),
        amount=float(intent.amount) if intent.amount is not None else None,
        transaction_id=intent.transaction_id,
        error=intent.error,
        result=_read(intent.result),
        created_at=intent.created_at.isoformat() if intent.created_at else None,
        completed_at=intent.completed_at.isoformat() if intent.completed_at else None,
    )