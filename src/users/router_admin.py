from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_system_admin,
    require_system_and_library_admin,
)
from src.core.enums import OrderBy
from src.core.limiter import user_limiter
from src.pagination import PaginatedResponse
from src.users.models import User
from src.users.schemas import (
    CreateUserAdmin,
    SearchUserAdmin,
    UpdateUser,
    UpdateUserEmail,
    UserResponseAdmin,
)
from src.users.service import UserServiceAdmin
from src.utils.enums import UserSortField

router = APIRouter(
    prefix="/users",
    tags=["Users - Admin"],
)


@router.post("", response_model=UserResponseAdmin, status_code=status.HTTP_201_CREATED)
@user_limiter.limit("5/minute")
async def create_account(
    request: Request,
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    create_request: CreateUserAdmin,
):
    return await UserServiceAdmin.create_account(db, current_user.id, create_request)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponseAdmin],
    status_code=status.HTTP_200_OK,
)
@user_limiter.limit("15/minute")
async def get_users(
    request: Request,
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    pagination: pagination_dependency,
    filters: Annotated[SearchUserAdmin, Depends()],
    sort_by: str = UserSortField.created_at,
    order: str = OrderBy.desc,
):
    return await UserServiceAdmin.get_users(
        db,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponseAdmin | dict,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.get_user_by_id(db, user_id)


@router.patch("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.deactivate_user(db, current_user.id, user_id)


@router.patch("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.activate_user(db, current_user.id, user_id)


@router.patch(
    "/{user_id}", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK
)
async def update_user(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
    update_request: UpdateUser,
):
    return await UserServiceAdmin.update_user(
        db, current_user.id, user_id, update_request
    )


@router.patch(
    "/{user_id}/email",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user_email(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
    update_request: UpdateUserEmail,
):
    await UserServiceAdmin.update_user_email(
        db, current_user.id, user_id, update_request
    )


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
@user_limiter.limit("5/minute")
async def create_reset_password_request(
    request: Request,
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_and_library_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    await UserServiceAdmin.create_reset_password_request(db, current_user, user_id)
