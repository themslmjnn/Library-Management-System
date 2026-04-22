from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    require_roles,
    pagination_dependency,
)
from src.user.models import User, UserRole
from src.user.schemas import (
    CreateUserAdmin,
    SearchUser,
    UpdateUserAdmin,
    UpdateUserPasswordAdmin,
    UserResponseAdmin,
)
from src.user.service import UserServiceAdmin
from src.utils.exception_constants import path_param_int_ge1
from src.pagination import PaginatedResponse

router = APIRouter(
    prefix="/users",
    tags=["Users - Admin"],
)

@router.post("", response_model=UserResponseAdmin, status_code=status.HTTP_201_CREATED)
async def create_account_admin(
    db: async_db_dependency,
    user_request: CreateUserAdmin,
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.create_account_admin(db, user_request, current_user)


@router.get("", response_model=PaginatedResponse[UserResponseAdmin], status_code=status.HTTP_200_OK)
async def get_users_admin(
    db: async_db_dependency,
    pagination: pagination_dependency,
    filters: Annotated[SearchUser, Depends()],
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
    sort_by: str = "created_at",
    order_by: str = "desc",
):
    return await UserServiceAdmin.get_users_admin(
        db,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order_by,
    )


@router.get("/search", response_model=list[UserResponseAdmin], status_code=status.HTTP_200_OK)
async def search_users_admin(
    db: async_db_dependency,
    search_request: Annotated[SearchUser, Depends()],
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.search_users_admin(db, search_request)

@router.get("/{user_id}", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK)
async def get_user_by_id_admin(
    db: async_db_dependency,
    user_id: path_param_int_ge1,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.get_user_by_id_admin(db, user_id)

@router.put("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user_admin(
    db: async_db_dependency,
    user_id: path_param_int_ge1,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.deactivate_user_admin(db, user_id)

@router.put("/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_user_admin(
    db: async_db_dependency,
    user_id: path_param_int_ge1,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.activate_user_admin(db, user_id)

@router.patch("", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK)
async def update_user_admin(
    db: async_db_dependency,
    user_id: path_param_int_ge1,
    update_request: UpdateUserAdmin,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.update_user_admin(db, user_id, update_request)

@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password_admin(
    db: async_db_dependency,
    user_id: int,
    password_request: UpdateUserPasswordAdmin,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    await UserServiceAdmin.update_password(db, user_id, password_request)