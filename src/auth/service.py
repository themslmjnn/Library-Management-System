import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import AuthRepository
from src.auth.schemas import (
    ActivateAccountWithCode,
    ActivateAccountWithToken,
    CreateAccessTokenRequest,
    CreateRefreshTokenRequest,
    LoginResponse,
)
from src.core.config import settings
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_account_activation_code,
    verify_invite_token,
    verify_password,
    verify_refresh_token,
)
from src.user.models import User
from src.user.repository import UserRepositoryBase
from src.utils.exception_constants import HTTP400, HTTP401, HTTP403
from src.core.logging import get_logger

logger = get_logger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
COOKIE_MAX_AGE = 60 * 60 * 24 * 7


class AuthService:
    @staticmethod
    def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
        response.set_cookie(
            key="refresh_token",
            value=raw_refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=COOKIE_MAX_AGE,
            path="/auth/refresh_token",
        )

    @staticmethod
    def _clear_refresh_cookie(response: Response) -> None:
        response.delete_cookie(
            key="refresh_token",
            path="/auth/refresh_token",
        )

    @staticmethod
    async def _invalidate_all_tokens(db: AsyncSession, user: User) -> None:
        user.access_token_version += 1
        user.refresh_token_hash = None
        user.refresh_token_family = None
        user.refresh_token_expires_at = None

        await db.commit()

        logger.info(
            "tokens_invalidated",
            user_id=user.id,
            reason="explicit_invalidation",
        )

    @staticmethod
    async def login(db: AsyncSession, response: Response, form_data: OAuth2PasswordRequestForm) -> LoginResponse:
        if form_data.username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username can not be empty",
            )
        
        user = await AuthRepository.get_by_login_identifier(db, form_data.username)

        if user is None:
            logger.warning(
                "login_failed",
                reason="user_not_found",
                identifier=form_data.username,
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_CREDENTIALS,
            )

        if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
            logger.warning(
                "login_blocked",
                reason="account_locked",
                user_id=user.id,
                locked_until=user.locked_until.isoformat(),
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked. Try again after {user.locked_until.strftime('%H:%M UTC')}",
            )

        if user.password_hash is None:
            logger.warning(
                "login_failed",
                reason="no_password_set",
                user_id=user.id,
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_CREDENTIALS,
            )

        if not verify_password(form_data.password, user.password_hash):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                await db.commit()
                logger.warning(
                    "account_locked",
                    user_id=user.id,
                    failed_attempts=user.failed_login_attempts,
                    locked_until=user.locked_until.isoformat(),
                )
            else:
                await db.commit()
                logger.warning(
                    "login_failed",
                    reason="wrong_password",
                    user_id=user.id,
                    failed_attempts=user.failed_login_attempts,
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_CREDENTIALS,
            )

        if not user.is_active:
            logger.warning(
                "login_failed",
                reason="account_inactive",
                user_id=user.id,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=HTTP403.ACCOUNT_DEACTIVATED,
            )

        user.failed_login_attempts = 0
        user.locked_until = None

        new_family = secrets.token_urlsafe(32)
        user.refresh_token_family = new_family

        access_token = create_access_token(
            CreateAccessTokenRequest(
                user_id=user.id,
                role=user.role,
                access_token_version=user.access_token_version,
            )
        )

        raw_refresh_token, hashed_refresh_token = create_refresh_token(
            CreateRefreshTokenRequest(
                user_id=user.id,
                family=new_family,
            )
        )

        user.refresh_token_hash = hashed_refresh_token
        user.refresh_token_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        )

        await db.commit()

        logger.info(
            "login_success",
            user_id=user.id,
            role=user.role,
        )

        AuthService._set_refresh_cookie(response, raw_refresh_token)

        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod
    async def activate_account_with_token(db: AsyncSession, request: ActivateAccountWithToken) -> None:
        user = await AuthRepository.get_by_login_identifier(db, request.email)

        if user is None or user.invite_token_hash is None:
            logger.warning(
                "activation_failed",
                reason="invalid_token",
                email=request.email,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.INVALID_INVITE_TOKEN,
            )

        if datetime.now(timezone.utc) > user.invite_token_expires_at:
            logger.warning(
                "activation_failed",
                reason="token_expired",
                user_id=user.id,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.EXPIRED_INVITE_TOKEN,
            )

        if not verify_invite_token(request.invite_token, user.invite_token_hash):
            logger.warning(
                "activation_failed",
                reason="token_mismatch",
                user_id=user.id,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.INVALID_INVITE_TOKEN,
            )

        user.password_hash = hash_password(request.password)
        user.is_active = True
        user.invite_token_hash = None
        user.invite_token_expires_at = None

        await db.commit()

        logger.info("account_activated", user_id=user.id, method="invite_token")


    @staticmethod
    async def activate_account_with_code(db: AsyncSession, request: ActivateAccountWithCode) -> None:
        user = await AuthRepository.get_by_login_identifier(db, request.email)

        if user is None or user.account_activation_code_hash is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.INVALID_ACTIVATION_CODE,
            )

        if datetime.now(timezone.utc) > user.account_activation_code_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.EXPIRED_ACTIVATION_CODE,
            )

        if not verify_account_activation_code(request.code, user.account_activation_code_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=HTTP400.INVALID_ACTIVATION_CODE,
            )

        user.is_active = True
        user.account_activation_code_hash = None
        user.account_activation_code_expires_at = None

        await db.commit()


    @staticmethod
    async def refresh_token(db: AsyncSession, response: Response, raw_refresh_token: str) -> LoginResponse:
        try:
            payload = decode_refresh_token(raw_refresh_token)
            user_id = int(payload.get("sub"))
            token_family = payload.get("family")

        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_REFRESH_TOKEN,
            )

        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        if user is None or user.refresh_token_hash is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_REFRESH_TOKEN,
            )

        if token_family != user.refresh_token_family:
            await AuthService._invalidate_all_tokens(db, user)

            logger.warning(
                "refresh_token_reuse_detected",
                user_id=user.id,
                action="all_tokens_invalidated",
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security violation detected. Please log in again",
            )

        if datetime.now(timezone.utc) > user.refresh_token_expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.EXPIRED_REFRESH_TOKEN,
            )

        if not verify_refresh_token(raw_refresh_token, user.refresh_token_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=HTTP401.INVALID_REFRESH_TOKEN,
            )

        new_family = secrets.token_urlsafe(32)
        user.refresh_token_family = new_family

        access_token = create_access_token(
            CreateAccessTokenRequest(
                user_id=user.id,
                role=user.role,
                access_token_version=user.access_token_version,
            )
        )

        raw_refresh_token, hashed_refresh_token = create_refresh_token(
            CreateRefreshTokenRequest(
                user_id=user.id,
                family=new_family,
            )
        )

        user.refresh_token_hash = hashed_refresh_token
        user.refresh_token_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        )

        await db.commit()

        AuthService._set_refresh_cookie(response, raw_refresh_token)

        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod
    async def logout(db: AsyncSession, response: Response, current_user: User) -> None:
        await AuthService._invalidate_all_tokens(db, current_user)

        AuthService._clear_refresh_cookie(response)

        logger.info("logout", user_id=current_user.id)