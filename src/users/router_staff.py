from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_staff,
)
from src.pagination import PaginatedResponse
from src.users.models import User
from src.users.schemas import CreateUserBase, SearchUserBase, UserResponseStaff
from src.users.service import UserServiceStaff
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/users",
    tags=["Users - Staff"],
)


@router.post(
    "/staff", response_model=UserResponseStaff, status_code=status.HTTP_201_CREATED
)
async def create_account_staff(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_staff)],
    user_request: CreateUserBase,
):
    return await UserServiceStaff.create_account_staff(
        db, current_user.id, user_request
    )


@router.get(
    "/staff",
    response_model=PaginatedResponse[UserResponseStaff],
    status_code=status.HTTP_200_OK,
)
async def get_users_staff(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_staff)],
    pagination: pagination_dependency,
    filters: Annotated[SearchUserBase, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await UserServiceStaff.get_users_staff(
        db,
        current_user,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order,
    )


@router.get(
    "/{user_id}/staff", response_model=UserResponseStaff, status_code=status.HTTP_200_OK
)
async def get_user_by_id_staff(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_staff)],
    user_id: path_param_int_ge1,
):
    return await UserServiceStaff.get_user_by_id_staff(db, current_user, user_id)
