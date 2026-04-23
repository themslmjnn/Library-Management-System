from fastapi import APIRouter, Request, status

from src.core.dependencies import async_db_dependency, current_user_dependency
from src.core.limiter import ip_limiter
from src.user.schemas import (
    CreateUserPublic,
    UpdateUserBase,
    UpdateUserPasswordPublic,
    UserResponseBase,
)
from src.user.service import UserServicePublic

router = APIRouter(
    prefix="/users",
    tags=["Users - Public"],
)


@router.post("/me", response_model=UserResponseBase, status_code=status.HTTP_201_CREATED)
@ip_limiter.limit("3/minute")
async def create_account_public(
    request: Request,
    db: async_db_dependency,
    user_request: CreateUserPublic,
):
    return await UserServicePublic.create_account_public(db, user_request)


@router.get("/me", response_model=UserResponseBase, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: current_user_dependency,
):
    return current_user


@router.patch("/me", response_model=UserResponseBase, status_code=status.HTTP_200_OK)
async def update_me(
    db: async_db_dependency,
    update_request: UpdateUserBase,
    current_user: current_user_dependency,
):
    return await UserServicePublic.update_me(db, update_request, current_user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_password(
    db: async_db_dependency,
    password_request: UpdateUserPasswordPublic,
    current_user: current_user_dependency,
):
    await UserServicePublic.update_my_password(db, password_request, current_user)