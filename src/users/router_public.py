from fastapi import APIRouter, Request, status

from src.core.dependencies import async_db_dependency, current_user_dependency
from src.core.limiter import ip_limiter, user_limiter
from src.users.schemas import (
    ConfirmEmailChange,
    CreateUserPublic,
    EmailChangeRequest,
    ForgotPasswordPublicRequest,
    UpdateUser,
    UpdateUserPasswordPublic,
    UserResponseBase,
)
from src.users.service import UserServicePublic
from src.utils.response_schemas import MessageResponse

router = APIRouter(
    prefix="/users",
    tags=["Users - Public"],
)


@router.post(
    "/register", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
@ip_limiter.limit("5/minute")
async def create_account_public(
    request: Request,
    db: async_db_dependency,
    user_request: CreateUserPublic,
):
    return await UserServicePublic.create_account_public(db, user_request)


@router.post(
    "/forgot_password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
@ip_limiter.limit("5/minute")
async def create_forgot_password_request(
    request: Request,
    db: async_db_dependency,
    forgot_password_request: ForgotPasswordPublicRequest,
):
    return await UserServicePublic.create_forgot_passsword_request_public(
        db, forgot_password_request
    )


@router.get("/me", response_model=UserResponseBase, status_code=status.HTTP_200_OK)
async def get_me(
    db: async_db_dependency,
    current_user: current_user_dependency,
):
    return await UserServicePublic.get_me(db, current_user.id)


@router.patch("/me", response_model=UserResponseBase, status_code=status.HTTP_200_OK)
async def update_me(
    db: async_db_dependency,
    current_user: current_user_dependency,
    update_request: UpdateUser,
):
    return await UserServicePublic.update_me(db, current_user.id, update_request)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
@user_limiter.limit("5/minute")
async def update_my_password(
    request: Request,
    db: async_db_dependency,
    current_user: current_user_dependency,
    password_request: UpdateUserPasswordPublic,
):
    await UserServicePublic.update_my_password(db, current_user.id, password_request)


@router.post(
    "/me/email",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def request_email_change(
    db: async_db_dependency,
    current_user: current_user_dependency,
    update_request: EmailChangeRequest,
):
    return await UserServicePublic.request_email_change(
        db, current_user.id, update_request.new_email
    )


@router.post(
    "/me/email/confirm",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def confirm_email_change(
    db: async_db_dependency,
    current_user: current_user_dependency,
    body: ConfirmEmailChange,
):
    return await UserServicePublic.confirm_email_change(db, current_user.id, body.code)
