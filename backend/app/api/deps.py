from fastapi.security import OAuth2PasswordBearer
from app.db.session import get_db as get_db_session
from app.core.config import settings

# Re-export the database session dependency
get_db = get_db_session

# OAuth2 scheme for token authentication (we'll implement later if needed)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

# TODO: Implement get_current_user dependency
# async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     # Decode token and fetch user from db
#     pass
