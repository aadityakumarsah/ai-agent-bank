from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_wallet_ownership
from app.db.session import get_db
from app.db.models import User
from app.schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_wallet_ownership)])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_or_get_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a user by wallet address, or return the existing user if present."""
    existing = db.query(User).filter(User.wallet_address == payload.wallet_address).first()
    if existing:
        return existing

    user = User(wallet_address=payload.wallet_address)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{wallet_address}", response_model=UserOut)
def get_user(wallet_address: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
