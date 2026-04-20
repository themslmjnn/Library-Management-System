from typing import AsyncGenerator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import AsyncSessionLocal
from src.user.models import User, UserRole
from src.core.security import decode_access_token
from src.user.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async_db_dependency = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: async_db_dependency,
    token: str = Depends(oauth2_scheme),
) -> User:
    try:
        payload = decode_access_token(token)

        user_id = int(payload.get("sub"))
        token_version = int(payload.get("version"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = await UserRepository.get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if user.access_token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated"
        )
    
    return user

current_user_dependency = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def guard(current_user: current_user_dependency) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        return current_user
    return guard