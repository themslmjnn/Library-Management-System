import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import AuthRepository
from src.auth.schemas import (
    ActivateAccountWithCode,
    ActivateAccountWithToken,
    CreateAccessTokenRequest,
    CreateRefreshTokenRequest,
    LoginResponse,
)
from src.core.cache import delete_cache
from src.core.config import settings
from src.core.logging import get_logger
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
from src.utils.cache_keys import access_token_version_key
from src.utils.exception_constants import HTTP400, HTTP401, HTTP403
from src.utils.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    EmptyCredentialsError,
    ExpiredActivationCodeError,
    ExpiredInviteTokenError,
    ExpiredRefreshTokenError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    InvalidInviteTokenError,
    InvalidRefreshTokenError,
    RefreshTokenFamilyError,
)

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
    async def _invalidate_all_tokens(db: AsyncSession, current_user_id: int) -> None:
        user = await UserRepositoryBase.get_user_with_session(db, current_user_id)
        if user is None:
            return

        user.session.access_token_version += 1
        user.session.refresh_token_hash = None
        user.session.refresh_token_family = None
        user.session.refresh_token_expires_at = None

        await db.commit()

        await delete_cache(access_token_version_key(current_user_id))

        logger.info(
            "tokens_invalidated",
            user_id=current_user_id,
            reason="explicit_invalidation",
        )

    @staticmethod
    async def login(
        db: AsyncSession, response: Response, form_data: OAuth2PasswordRequestForm
    ) -> LoginResponse:
        if form_data.username is None or form_data.password is None:
            raise EmptyCredentialsError("Username and password is required")

        user = await AuthRepository.get_user_by_login_identifier_with_session(
            db, form_data.username
        )

        if user is None:
            logger.warning(
                "login_failed",
                reason="user_not_found",
                identifier=form_data.username,
            )

            raise InvalidCredentialsError(HTTP401.INVALID_CREDENTIALS)

        if (
            user.session.locked_until
            and datetime.now(timezone.utc) < user.session.locked_until
        ):
            logger.warning(
                "login_blocked",
                reason="account_locked",
                user_id=user.id,
                locked_until=user.session.locked_until.isoformat(),
            )

            raise AccountLockedError(
                f"Account locked. Try again after {user.session.locked_until.strftime('%H:%M UTC')}"
            )

        if user.password_hash is None:
            logger.warning(
                "login_failed",
                reason="no_password_set",
                user_id=user.id,
            )

            raise InvalidCredentialsError(HTTP401.INVALID_CREDENTIALS)

        if not verify_password(form_data.password, user.password_hash):
            user.session.failed_login_attempts += 1

            if user.session.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.session.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_MINUTES
                )

                logger.warning(
                    "account_locked",
                    user_id=user.id,
                    failed_attempts=user.session.failed_login_attempts,
                    locked_until=user.session.locked_until.isoformat(),
                )
            else:
                logger.warning(
                    "login_failed",
                    reason="wrong_password",
                    user_id=user.id,
                    failed_attempts=user.session.failed_login_attempts,
                )

            await db.commit()

            raise InvalidCredentialsError(HTTP401.INVALID_CREDENTIALS)

        if not user.is_active:
            logger.warning(
                "login_failed",
                reason="account_inactive",
                user_id=user.id,
            )

            raise AccountInactiveError(HTTP403.ACCOUNT_DEACTIVATED)

        user.session.failed_login_attempts = 0
        user.session.locked_until = None

        new_family = secrets.token_urlsafe(32)
        user.session.refresh_token_family = new_family

        access_token = create_access_token(
            CreateAccessTokenRequest(
                user_id=user.id,
                role=user.role,
                access_token_version=user.session.access_token_version,
            )
        )
        raw_refresh_token, hashed_refresh_token = create_refresh_token(
            CreateRefreshTokenRequest(
                user_id=user.id,
                family=new_family,
            )
        )

        user.session.refresh_token_hash = hashed_refresh_token
        user.session.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRES_DAYS
        )

        await db.commit()
        await db.refresh(user)

        logger.info(
            "login_success",
            user_id=user.id,
            role=user.role,
        )

        AuthService._set_refresh_cookie(response, raw_refresh_token)

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    @staticmethod
    async def logout(db: AsyncSession, response: Response, current_user: User) -> None:
        await AuthService._invalidate_all_tokens(db, current_user.id)

        AuthService._clear_refresh_cookie(response)

        logger.info(
            "logout",
            user_id=current_user.id,
        )

    @staticmethod
    async def activate_account_with_token(
        db: AsyncSession, activation_request: ActivateAccountWithToken
    ) -> None:
        user = await AuthRepository.get_user_by_login_identifier_with_activation(
            db, activation_request.email
        )

        if user is None or user.activation.invite_token_hash is None:
            logger.warning(
                "activation_failed",
                reason="invalid_invite_token",
                email=activation_request.email,
            )

            raise InvalidInviteTokenError(HTTP400.INVALID_INVITE_TOKEN)

        if (
            user.activation.invite_token_expires_at is None
            or datetime.now(timezone.utc) > user.activation.invite_token_expires_at
        ):
            logger.warning(
                "activation_failed",
                reason="invite_token_expired",
                user_id=user.id,
            )

            raise ExpiredInviteTokenError(HTTP400.EXPIRED_INVITE_TOKEN)

        if not verify_invite_token(
            activation_request.invite_token, user.activation.invite_token_hash
        ):
            logger.warning(
                "activation_failed",
                reason="invite_token_mismatch",
                user_id=user.id,
            )

            raise InvalidInviteTokenError(HTTP400.INVALID_INVITE_TOKEN)

        user.password_hash = hash_password(activation_request.password)
        user.is_active = True
        user.activation.invite_token_hash = None
        user.activation.invite_token_expires_at = None

        await db.commit()
        await db.refresh(user)

        logger.info(
            "account_activated",
            user_id=user.id,
            method="invite_token",
        )

    @staticmethod
    async def activate_account_with_code(
        db: AsyncSession, activation_request: ActivateAccountWithCode
    ) -> None:
        user = await AuthRepository.get_by_login_identifier(
            db, activation_request.email
        )

        if user is None or user.activation.account_activation_code_hash is None:
            logger.warning(
                "activation_failed",
                reason="invalid_activation_code",
                email=activation_request.email,
            )

            raise InvalidActivationCodeError(HTTP400.INVALID_ACTIVATION_CODE)

        if (
            user.activation.account_activation_code_expires_at is None
            or datetime.now(timezone.utc)
            > user.activation.account_activation_code_expires_at
        ):
            logger.warning(
                "activation_failed",
                reason="activation_code_expired",
                user_id=user.id,
            )

            raise ExpiredActivationCodeError(HTTP400.EXPIRED_ACTIVATION_CODE)

        if not verify_account_activation_code(
            activation_request.code,
            user.activation.account_activation_code_hash,
        ):
            logger.warning(
                "activation_failed",
                reason="activation_code_mismatch",
                user_id=user.id,
            )

            raise InvalidActivationCodeError(HTTP400.INVALID_ACTIVATION_CODE)

        user.is_active = True
        user.activation.account_activation_code_hash = None
        user.activation.account_activation_code_expires_at = None

        await db.commit()
        await db.refresh(user)

        logger.info(
            "account_activated",
            user_id=user.id,
            method="activation_code",
        )

    @staticmethod
    async def refresh_token(
        db: AsyncSession, response: Response, raw_refresh_token: str
    ) -> LoginResponse:
        try:
            payload = decode_refresh_token(raw_refresh_token)
            user_id = int(payload.get("sub"))
            refresh_token_family = payload.get("family")

        except ExpiredSignatureError:
            logger.warning(
                "refresh_token_rotation_failed",
                reason="token_expired",
            )
            raise ExpiredRefreshTokenError(HTTP401.EXPIRED_REFRESH_TOKEN)

        except (ValueError, TypeError) as e:
            logger.warning(
                "invalid_jwt",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            raise InvalidRefreshTokenError(HTTP401.INVALID_REFRESH_TOKEN)

        user = await UserRepositoryBase.get_user_with_session(db, user_id)

        if user is None or user.session.refresh_token_hash is None:
            logger.warning(
                "refresh_token_rotation_failed",
                reason="invalid_refresh_token",
                user_id=user_id,
            )

            raise InvalidRefreshTokenError(HTTP401.INVALID_REFRESH_TOKEN)

        if refresh_token_family != user.session.refresh_token_family:
            await AuthService._invalidate_all_tokens(db, user.id)

            logger.warning(
                "refresh_token_reuse_detected",
                user_id=user.id,
                action="all_tokens_invalidated",
            )

            raise RefreshTokenFamilyError(
                "Security violation detected. Please log in again"
            )

        if datetime.now(timezone.utc) > user.session.refresh_token_expires_at:
            logger.warning(
                "refresh_token_rotation_failed",
                reason="refresh_token_expired",
                user_id=user.id,
            )

            raise ExpiredRefreshTokenError(HTTP401.EXPIRED_REFRESH_TOKEN)

        if not verify_refresh_token(raw_refresh_token, user.session.refresh_token_hash):
            logger.warning(
                "refresh_token_rotation_failed",
                reason="refresh_token_mismatch",
                user_id=user.id,
            )

            raise InvalidRefreshTokenError(HTTP401.INVALID_REFRESH_TOKEN)

        new_family = secrets.token_urlsafe(32)
        user.session.refresh_token_family = new_family

        access_token = create_access_token(
            CreateAccessTokenRequest(
                user_id=user.id,
                role=user.role,
                access_token_version=user.session.access_token_version,
            )
        )
        raw_refresh_token, hashed_refresh_token = create_refresh_token(
            CreateRefreshTokenRequest(
                user_id=user.id,
                family=new_family,
            )
        )

        user.session.refresh_token_hash = hashed_refresh_token
        user.session.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRES_DAYS
        )

        await db.commit()
        await db.refresh(user)

        logger.info(
            "refresh_token_rotated",
            user_id=user.id,
            method="refresh_token",
        )

        AuthService._set_refresh_cookie(response, raw_refresh_token)

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
