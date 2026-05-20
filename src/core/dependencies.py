from dataclasses import dataclass
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import get_cache, set_cache
from src.core.enums import SortOrder
from src.core.security import decode_access_token
from src.database import AsyncSessionLocal
from src.user.repository import UserRepositoryBase
from src.utils.cache_keys import access_token_version_key
from src.utils.enums import BookCategory, UserRole
from src.utils.exception_constants import HTTP401, HTTP403
from src.utils.exceptions import (
    AccessDeniedError,
    AccountInactiveError,
    InvalidAccessTokenError,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async_db_dependency = Annotated[AsyncSession, Depends(get_db)]


@dataclass
class CurrentUser:
    id: int
    role: UserRole


async def get_current_user(
    db: async_db_dependency, token: str = Depends(oauth2_scheme)
) -> CurrentUser:
    try:
        payload = decode_access_token(token)

        user_id = int(payload.get("sub"))
        token_version = int(payload.get("version"))

    except (ValueError, TypeError):
        raise InvalidAccessTokenError(HTTP401.INVALID_ACCESS_TOKEN)

    user_access_token_version_key = access_token_version_key(user_id)

    cached_version = await get_cache(user_access_token_version_key)
    if cached_version is not None:
        if int(cached_version) != token_version:
            raise InvalidAccessTokenError(HTTP401.INVALID_ACCESS_TOKEN)

        return CurrentUser(
            id=user_id,
            role=UserRole(payload.get("role")),
        )

    user = await UserRepositoryBase.get_user_with_session(db, user_id)

    if user is None:
        raise InvalidAccessTokenError(HTTP401.INVALID_ACCESS_TOKEN)

    if user.session.access_token_version != token_version:
        raise InvalidAccessTokenError(HTTP401.INVALID_ACCESS_TOKEN)

    if not user.is_active:
        raise AccountInactiveError(HTTP403.ACCOUNT_DEACTIVATED)

    await set_cache(
        user_access_token_version_key,
        user.session.access_token_version,
        ttl_seconds=300,
    )

    return CurrentUser(
        id=user_id,
        role=UserRole(payload.get("role")),
    )


current_user_dependency = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def guard(current_user: current_user_dependency) -> CurrentUser:
        if current_user.role not in roles:
            raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        return current_user

    return guard


require_system_admin = require_roles(UserRole.system_admin)
require_system_and_library_admin = require_roles(
    UserRole.system_admin,
    UserRole.library_admin,
)
require_staff = require_roles(UserRole.library_admin, UserRole.receptionist)
require_system_admin_and_staff = require_roles(
    UserRole.system_admin,
    UserRole.library_admin,
    UserRole.receptionist,
)


class PaginationParams(BaseModel):
    skip: int = Query(ge=0, default=0)
    limit: int = Query(ge=1, le=100, default=20)


pagination_dependency = Annotated[PaginationParams, Depends(PaginationParams)]


class BookQueryParams(PaginationParams):
    title: str | None = Query(default=None)
    author: str | None = Query(default=None)
    category: BookCategory | None = Query(default=None)
    sort_by: str = Query(default="created_at")
    order: SortOrder = Query(default=SortOrder.desc)
