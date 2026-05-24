from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_system_admin,
)
from src.pagination import PaginatedResponse
from src.users.models import User
from src.users.schemas import (
    CreateUserAdmin,
    SearchUserAdmin,
    UpdateUser,
    UpdateUserPasswordAdmin,
    UserResponseAdmin,
)
from src.users.service import UserServiceAdmin

router = APIRouter(
    prefix="/users",
    tags=["Users - Admin"],
)


@router.post("", response_model=UserResponseAdmin, status_code=status.HTTP_201_CREATED)
async def create_account_admin(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_request: CreateUserAdmin,
):
    return await UserServiceAdmin.create_account_admin(
        db, current_user.id, user_request
    )


@router.get(
    "",
    response_model=PaginatedResponse[UserResponseAdmin],
    status_code=status.HTTP_200_OK,
)
async def get_users_admin(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    pagination: pagination_dependency,
    filters: Annotated[SearchUserAdmin, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await UserServiceAdmin.get_users_admin(
        db,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order,
    )


@router.get(
    "/{user_id}", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK
)
async def get_user_by_id_admin(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.get_user_by_id_admin(db, user_id)


@router.patch("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user_admin(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.deactivate_user_admin(db, current_user.id, user_id)


@router.patch("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user_admin(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
):
    return await UserServiceAdmin.activate_user_admin(db, current_user.id, user_id)


@router.patch(
    "/{user_id}", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK
)
async def update_user_admin(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: Annotated[int, Path(ge=1)],
    update_request: UpdateUser,
):
    return await UserServiceAdmin.update_user_admin(
        db, current_user.id, user_id, update_request
    )


@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_password_admin(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin)],
    user_id: int,
    password_request: UpdateUserPasswordAdmin,
):
    await UserServiceAdmin.update_user_password_admin(
        db, current_user.id, user_id, password_request
    )
