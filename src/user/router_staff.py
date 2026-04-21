from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import async_db_dependency, require_roles
from src.user.models import User, UserRole
from src.user.schemas import CreateUserBase, SearchUser, UserResponseBase
from src.user.service import UserServiceStaff
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/users",
    tags=["Users - Staff"],
)

@router.post("/staff", response_model=UserResponseBase, status_code=status.HTTP_201_CREATED)
async def create_account_staff(
    db: async_db_dependency,
    user_request: CreateUserBase,
    current_user: Annotated[User, Depends(require_roles(UserRole.library_admin, UserRole.receptionist))],
):
    return await UserServiceStaff.create_account_staff(db, user_request, current_user)


@router.get("/staff", response_model=list[UserResponseBase], status_code=status.HTTP_200_OK)
async def get_users_staff(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_roles(UserRole.library_admin, UserRole.receptionist))],
):
    return await UserServiceStaff.get_users_staff(db, current_user)


@router.get("/search/staff", response_model=list[UserResponseBase], status_code=status.HTTP_200_OK)
async def search_users_staff(
    db: async_db_dependency,
    search_request: Annotated[SearchUser, Depends()],
    current_user: Annotated[User, Depends(require_roles(UserRole.library_admin, UserRole.receptionist))],
):
    return await UserServiceStaff.search_users_staff(db, search_request, current_user)


@router.get("/{user_id}/for_staff", response_model=UserResponseBase, status_code=status.HTTP_200_OK)
async def get_user_by_id_staff(
    db: async_db_dependency,
    user_id: path_param_int_ge1,
    current_user: Annotated[User, Depends(require_roles(UserRole.library_admin, UserRole.receptionist))],
):
    return await UserServiceStaff.get_user_by_id_staff(db, user_id, current_user)