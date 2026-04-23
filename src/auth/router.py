from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.schemas import (
    ActivateAccountWithCode,
    ActivateAccountWithToken,
    LoginResponse,
)
from src.auth.service import AuthService
from src.core.dependencies import async_db_dependency, current_user_dependency
from src.core.limiter import ip_limiter
from src.utils.exception_constants import HTTP401

router = APIRouter(
    prefix="/auth", 
    tags=["Auth"],
)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@ip_limiter.limit("10/minute")
async def login(
    request: Request,
    db: async_db_dependency,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    return await AuthService.login(db, response, form_data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    db: async_db_dependency,
    response: Response,
    current_user: current_user_dependency,
):
    await AuthService.logout(db, response, current_user)


@router.post("/activate_with_token", status_code=status.HTTP_204_NO_CONTENT)
@ip_limiter.limit("5/minute")
async def activate_with_token(
    request: Request,
    db: async_db_dependency,
    activation_request: ActivateAccountWithToken,
):
    await AuthService.activate_account_with_token(db, activation_request)


@router.post("/activate_with_code", status_code=status.HTTP_204_NO_CONTENT)
@ip_limiter.limit("5/minute")
async def activate_with_code(
    request: Request,
    db: async_db_dependency,
    activation_request: ActivateAccountWithCode,
):
    await AuthService.activate_account_with_code(db, activation_request)


@router.post("/refresh_token", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@ip_limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: async_db_dependency,
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=HTTP401.INVALID_REFRESH_TOKEN,
        )
    
    return await AuthService.refresh_token(db, response, refresh_token)