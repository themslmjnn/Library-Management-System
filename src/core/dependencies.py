from dataclasses import dataclass
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_access_token
from src.database import AsyncSessionLocal
from src.user.models import User, UserRole
from src.user.repository import UserRepositoryBase
from src.utils.exception_constants import HTTP401, HTTP403

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async_db_dependency = Annotated[AsyncSession, Depends(get_db)]


@dataclass
class CurrentUser:
    id: int
    role: UserRole
    is_active: bool

async def get_current_user(db: async_db_dependency, token: str = Depends(oauth2_scheme)) -> CurrentUser:
    try:
        payload = decode_access_token(token)

        user_id = int(payload.get("sub"))
        token_version = int(payload.get("version"))

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=HTTP401.INVALID_ACCESS_TOKEN
        )
    
    user = await UserRepositoryBase.get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=HTTP401.INVALID_ACCESS_TOKEN
        )
    
    if user.access_token_version != token_version:      
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=HTTP401.INVALID_ACCESS_TOKEN
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=HTTP403.ACCOUNT_DEACTIVATED
        )
    
    return CurrentUser(id=user.id, role=user.role, is_active=user.is_active)

current_user_dependency = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def guard(current_user: current_user_dependency) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=HTTP403.ACCESS_DENIED,
            )
        
        return current_user
    return guard


class PaginationParams(BaseModel):
    skip: int = Query(ge=0, default=0)
    limit: int = Query(ge=1, le=100, default=20)

pagination_dependency = Annotated[PaginationParams, Depends(PaginationParams)]