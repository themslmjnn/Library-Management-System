import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import delete_cache, get_cache, set_cache
from src.core.config import settings
from src.core.dependencies import CurrentUser
from src.core.logging import get_logger
from src.core.security import (
    generate_account_activation_code,
    generate_email_change_code,
    generate_invite_token,
    generate_reset_password_token,
    hash_password,
    verify_email_change_code,
    verify_password,
)
from src.email.enums import EmailType
from src.email.repository import PendingEmailRepository
from src.pagination import PaginatedResponse
from src.users import schemas as user_schemas
from src.users.models import User, UserActivation, UserSession
from src.users.repository import (
    UserRepositoryAdmin,
    UserRepositoryBase,
)
from src.utils import email as email_sender
from src.utils.cache_keys import (
    SessionCacheKey,
    UserCacheKey,
)
from src.utils.custom_exceptions import (
    AccessDeniedError,
    CannotCreateSystemAdminError,
    ExpiredEmailChangeCodeError,
    IncorrectPasswordError,
    InvalidEmailChangeCodeError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
    handle_user_integrity_error,
)
from src.utils.enums import UserRole
from src.utils.exception_constants import HTTP400, HTTP403, HTTP404
from src.utils.helpers import ensure_exists, update_object
from src.utils.response_messages import PublicMessages
from src.utils.response_schemas import MessageResponse

logger = get_logger(__name__)

SYSTEM_ADMIN_INVISIBLE_ROLES = frozenset({UserRole.system_admin})
LIBRARY_ADMIN_INVISIBLE_ROLES = frozenset(
    {UserRole.system_admin, UserRole.library_admin}
)
RECEPTIONIST_VISIBLE_ROLES = frozenset({UserRole.member, UserRole.guest})


class UserServiceAdmin:
    @staticmethod
    async def create_account(
        db: AsyncSession,
        current_user_id: int,
        user_request: user_schemas.CreateUserAdmin,
    ) -> User:
        if user_request.role == UserRole.system_admin:
            logger.warning(
                "create_user_denied",
                reason="cannot_create_system_admin_through_the_api",
                requested_by=current_user_id,
            )

            raise CannotCreateSystemAdminError(
                "Cannot create system admin through the API"
            )

        raw_invite_token, hashed_invite_token = generate_invite_token()
        invite_token_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITE_TOKEN_EXPIRES_HOURS
        )

        try:
            new_user = User(
                username=user_request.username,
                first_name=user_request.first_name,
                last_name=user_request.last_name,
                date_of_birth=user_request.date_of_birth,
                email=user_request.email,
                phone_number=user_request.phone_number,
                role=user_request.role,
                is_active=False,
                created_by=current_user_id,
            )

            UserRepositoryBase.add_entity(db, new_user)

            await db.flush()

            new_user_activation = UserActivation(
                user_id=new_user.id,
                invite_token_hash=hashed_invite_token,
                invite_token_expires_at=invite_token_expires_at,
            )

            new_user_session = UserSession(
                user_id=new_user.id,
            )

            UserRepositoryBase.add_entity(db, new_user_activation)
            UserRepositoryBase.add_entity(db, new_user_session)

            subject, html_body, text_body = email_sender.build_invite_email(
                raw_invite_token, new_user.email
            )

            PendingEmailRepository.create(
                db,
                recipient=new_user.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                email_type=EmailType.invite,
                triggered_by=current_user_id,
                recipient_user_id=new_user.id,
            )

            await db.commit()
            await db.refresh(new_user)

            logger.info(
                "user_created",
                new_user_id=new_user.id,
                role=new_user.role,
                created_by=current_user_id,
            )

            return new_user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "create_user_failed",
                reason="integrity_error",
                error=str(e.orig),
                requested_by=current_user_id,
            )

            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def get_users(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: user_schemas.SearchUserAdmin,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:

        users, total = await UserRepositoryAdmin.get_users_admin(
            db, skip, limit, filters, sort_by, order
        )

        return PaginatedResponse(
            items=users,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession, user_id: int
    ) -> user_schemas.UserResponseAdmin | dict:
        cache_key = UserCacheKey.user_detail_key_admin(user_id)
        cached = await get_cache(cache_key)
        if cached is not None:
            return cached

        user = await UserRepositoryBase.get_user_by_id(
            db, user_id, excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES
        )
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        result = user_schemas.UserResponseAdmin.model_validate(user)
        await set_cache(
            cache_key,
            result.model_dump(mode="json"),
            900,
        )

        return result

    @staticmethod
    async def deactivate_user(
        db: AsyncSession, current_user_id: int, user_id: int
    ) -> None:
        user = await UserRepositoryBase.get_user_by_id(
            db, user_id, load_session=True, excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES
        )
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        if not user.is_active:
            logger.error(
                "deactivate_user_failed",
                target_user_id=user_id,
                requested_by=current_user_id,
                reason="user_is_already_deactivated",
            )

            raise UserAlreadyInactiveError("User is already deactivated")

        user.is_active = False
        user.session.access_token_version += 1
        user.session.refresh_token_hash = None
        user.session.refresh_token_family = None
        user.session.refresh_token_expires_at = None

        await db.commit()

        asyncio.create_task(
            email_sender.send_safe(
                email_sender.send_account_deactivation_email(user.email),
                email_type="account_deactivation",
            )
        )

        await delete_cache(
            UserCacheKey.user_detail_key_admin(user_id),
            SessionCacheKey.access_token_version_key(user_id),
        )

        logger.info(
            "user_deactivated",
            target_user_id=user_id,
            deactivated_by=current_user_id,
        )

    @staticmethod
    async def activate_user(
        db: AsyncSession, current_user_id: int, user_id: int
    ) -> None:
        user = await UserRepositoryBase.get_user_by_id(
            db, user_id, excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES
        )
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        if user.is_active:
            logger.error(
                "activate_user_failed",
                target_user_id=user_id,
                requested_by=current_user_id,
                reason="user_is_already_activated",
            )

            raise UserAlreadyActiveError("User is already activated")

        user.is_active = True

        await db.commit()

        asyncio.create_task(
            email_sender.send_safe(
                email_sender.send_account_activation_email(user.email),
                email_type="account_activation",
            )
        )

        await delete_cache(UserCacheKey.user_detail_key_admin(user_id))

        logger.info(
            "user_activated",
            target_user_id=user_id,
            activated_by=current_user_id,
        )

    @staticmethod
    async def update_user(
        db: AsyncSession,
        current_user_id: int,
        user_id: int,
        update_request: user_schemas.UpdateUser,
    ) -> User:
        user = await UserRepositoryBase.get_user_by_id(
            db, user_id, excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES
        )
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        try:
            update_object(user, update_request)

            await db.commit()
            await db.refresh(user)

            await delete_cache(
                UserCacheKey.user_detail_key_admin(user_id),
                UserCacheKey.user_detail_key_staff(user_id),
                UserCacheKey.user_detail_key_self(user_id),
            )

            logger.info(
                "user_updated",
                target_user_id=user_id,
                updated_by=current_user_id,
                method="admin_update",
            )

            return user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "update_user_denied",
                target_user_id=user_id,
                requested_by=current_user_id,
                reason=str(e.orig),
            )

            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def update_user_email(
        db: AsyncSession,
        current_user_id: int,
        user_id: int,
        update_request: user_schemas.UpdateUserEmail,
    ) -> None:
        user = await UserRepositoryBase.get_user_by_id(
            db, user_id, excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES, load_session=True
        )
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        try:
            old_email = user.email
            user.email = update_request.new_email

            user.session.access_token_version += 1
            user.session.refresh_token_hash = None
            user.session.refresh_token_family = None
            user.session.refresh_token_expires_at = None

            user.session.pending_new_email = None
            user.session.email_change_code_hash = None
            user.session.email_change_code_expires_at = None

            await db.commit()

            asyncio.create_task(
                email_sender.send_safe(
                    email_sender.send_admin_email_override_notification(old_email),
                    email_type=EmailType.admin_email_override,
                )
            )

            await delete_cache(
                UserCacheKey.user_detail_key_admin(user_id),
                UserCacheKey.user_detail_key_staff(user_id),
                UserCacheKey.user_detail_key_self(user_id),
                SessionCacheKey.access_token_version_key(user_id),
            )

            logger.info(
                "admin_email_override",
                target_user_id=user_id,
                updated_by=current_user_id,
            )

        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "admin_email_override_failed",
                target_user_id=user_id,
                requested_by=current_user_id,
                reason=str(e.orig),
            )

            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def create_reset_password_request(
        db: AsyncSession,
        current_user: CurrentUser,
        user_id: int,
    ) -> None:

        match current_user.role:
            case UserRole.system_admin:
                user = await UserRepositoryBase.get_user_by_id(
                    db,
                    user_id,
                    excluded_roles=SYSTEM_ADMIN_INVISIBLE_ROLES,
                    load_session=True,
                )
            case UserRole.library_admin:
                user = await UserRepositoryBase.get_user_by_id(
                    db,
                    user_id,
                    excluded_roles=LIBRARY_ADMIN_INVISIBLE_ROLES,
                    load_session=True,
                )
            case _:
                raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        raw_reset_token, hashed_reset_token = generate_reset_password_token()

        user.session.reset_password_token_hash = hashed_reset_token
        user.session.reset_password_token_expires_at = datetime.now(
            timezone.utc
        ) + timedelta(minutes=settings.RESET_PASSWORD_EXPIRES_MINUTES)

        subject, html_body, text_body = email_sender.build_reset_password_email(
            raw_reset_token
        )

        PendingEmailRepository.create(
            db,
            recipient=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=EmailType.password_reset_admin,
            triggered_by=current_user.id,
            recipient_user_id=user.id,
        )

        await db.commit()

        logger.info(
            "reset_password_request_created",
            user_id=user.id,
        )


class UserServiceStaff:
    @staticmethod
    async def create_account(
        db: AsyncSession,
        current_user_id: int,
        user_request: user_schemas.CreateUserBase,
    ) -> User:
        raw_invite_token, invite_token_hash = generate_invite_token()
        invite_token_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.INVITE_TOKEN_EXPIRES_HOURS
        )

        try:
            new_user = User(
                username=user_request.username,
                first_name=user_request.first_name,
                last_name=user_request.last_name,
                date_of_birth=user_request.date_of_birth,
                email=user_request.email,
                phone_number=user_request.phone_number,
                role=UserRole.guest,
                is_active=False,
                created_by=current_user_id,
            )

            UserRepositoryBase.add_entity(db, new_user)

            await db.flush()

            new_user_activation = UserActivation(
                user_id=new_user.id,
                invite_token_hash=invite_token_hash,
                invite_token_expires_at=invite_token_expires_at,
            )

            new_user_session = UserSession(
                user_id=new_user.id,
            )

            UserRepositoryBase.add_entity(db, new_user_activation)
            UserRepositoryBase.add_entity(db, new_user_session)

            subject, html_body, text_body = email_sender.build_invite_email(
                raw_invite_token, new_user.email
            )

            PendingEmailRepository.create(
                db,
                recipient=new_user.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                email_type=EmailType.invite,
                triggered_by=current_user_id,
                recipient_user_id=new_user.id,
            )

            await db.commit()
            await db.refresh(new_user)

            logger.info(
                "user_created",
                new_user_id=new_user.id,
                role=UserRole.guest,
                created_by=current_user_id,
            )

            return new_user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "user_creation_failed",
                reason="integrity_error",
                error=str(e.orig),
                created_by=current_user_id,
            )

            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def get_users(
        db: AsyncSession,
        current_user: CurrentUser,
        skip: int,
        limit: int,
        filters: user_schemas.SearchUserBase,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:

        match current_user.role:
            case UserRole.library_admin:
                users, total = await UserRepositoryBase.get_users(
                    db,
                    excluded_roles=LIBRARY_ADMIN_INVISIBLE_ROLES,
                    skip=skip,
                    limit=limit,
                    filters=filters,
                    sort_by=sort_by,
                    order=order,
                )
            case UserRole.receptionist:
                users, total = await UserRepositoryBase.get_users(
                    db,
                    allowed_roles=RECEPTIONIST_VISIBLE_ROLES,
                    skip=skip,
                    limit=limit,
                    filters=filters,
                    sort_by=sort_by,
                    order=order,
                )
            case _:
                raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        return PaginatedResponse(
            items=users,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession, current_user: CurrentUser, user_id: int
    ) -> user_schemas.UserResponseStaff | dict:
        cache_key = UserCacheKey.user_detail_key_staff(user_id)
        cached = await get_cache(cache_key)
        if cached is not None:
            return cached

        match current_user.role:
            case UserRole.library_admin:
                user = await UserRepositoryBase.get_user_by_id(
                    db, user_id, excluded_roles=LIBRARY_ADMIN_INVISIBLE_ROLES
                )
            case UserRole.receptionist:
                user = await UserRepositoryBase.get_user_by_id(
                    db, user_id, allowed_roles=RECEPTIONIST_VISIBLE_ROLES
                )
            case _:
                raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        result = user_schemas.UserResponseStaff.model_validate(user)
        await set_cache(
            cache_key,
            result.model_dump(mode="json"),
            900,
        )

        return result


class UserServicePublic:
    @staticmethod
    async def create_account(
        db: AsyncSession, user_request: user_schemas.CreateUserPublic
    ) -> MessageResponse:
        raw_activation_code, hashed_activation_code = generate_account_activation_code()
        account_activation_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACTIVATION_CODE_EXPIRES_MINUTES
        )

        try:
            new_user = User(
                username=user_request.username,
                first_name=user_request.first_name,
                last_name=user_request.last_name,
                date_of_birth=user_request.date_of_birth,
                email=user_request.email,
                phone_number=user_request.phone_number,
                password_hash=hash_password(user_request.password),
                role=UserRole.guest,
                is_active=False,
            )

            UserRepositoryBase.add_entity(db, new_user)

            await db.flush()

            new_user_activation = UserActivation(
                user_id=new_user.id,
                account_activation_code_hash=hashed_activation_code,
                account_activation_code_expires_at=account_activation_code_expires_at,
            )

            new_user_session = UserSession(
                user_id=new_user.id,
            )

            UserRepositoryBase.add_entity(db, new_user_activation)
            UserRepositoryBase.add_entity(db, new_user_session)

            subject, html_body, text_body = email_sender.build_activation_code_email(
                raw_activation_code
            )

            PendingEmailRepository.create(
                db,
                recipient=new_user.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                email_type=EmailType.activation_with_code,
                triggered_by=None,
                recipient_user_id=new_user.id,
            )

            await db.commit()

            logger.info(
                "user_registered",
                user_id=new_user.id,
                method="self_registered",
            )
        except IntegrityError as e:
            await db.rollback()

            if "users_email_key" in str(e.orig):
                logger.info("registration_attempted_with_existing_email")

                asyncio.create_task(
                    email_sender.send_safe(
                        email_sender.send_already_registered_email(user_request.email),
                        email_type="already_registered_notice",
                    )
                )
            else:
                logger.error(
                    "user_registration_failed",
                    reason="integrity_error",
                    error=str(e.orig),
                )

                handle_user_integrity_error(e)
                raise

        return MessageResponse(detail=PublicMessages.REGISTRATION)

    @staticmethod
    async def get_me(db: AsyncSession, user_id: int) -> user_schemas.UserResponseBase:
        cache_key = UserCacheKey.user_detail_key_self(user_id)
        cached = await get_cache(cache_key)
        if cached is not None:
            return user_schemas.UserResponseBase.model_validate(cached)

        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        result = user_schemas.UserResponseBase.model_validate(user)
        await set_cache(
            cache_key,
            result.model_dump(mode="json"),
            900,
        )

        return result

    @staticmethod
    async def update_me(
        db: AsyncSession, user_id: int, update_request: user_schemas.UpdateUser
    ) -> User:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        try:
            update_object(user, update_request)

            await db.commit()
            await db.refresh(user)

            await delete_cache(
                UserCacheKey.user_detail_key_admin(user_id),
                UserCacheKey.user_detail_key_staff(user_id),
                UserCacheKey.user_detail_key_self(user_id),
            )

            logger.info(
                "user_updated",
                target_user_id=user_id,
                method="self_update",
            )

            return user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "update_user_denied",
                target_user_id=user_id,
                reason=str(e.orig),
            )

            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def update_my_password(
        db: AsyncSession,
        user_id: int,
        password_request: user_schemas.UpdateUserPasswordPublic,
    ) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id, load_session=True)

        if not user.password_hash:
            raise IncorrectPasswordError(HTTP400.INCORRECT_PASSWORD)

        if not verify_password(password_request.old_password, user.password_hash):
            raise IncorrectPasswordError(HTTP400.INCORRECT_PASSWORD)

        user.password_hash = hash_password(password_request.new_password)
        user.session.access_token_version += 1
        user.session.refresh_token_hash = None
        user.session.refresh_token_family = None
        user.session.refresh_token_expires_at = None

        await db.commit()

        await delete_cache(SessionCacheKey.access_token_version_key(user_id))

        asyncio.create_task(
            email_sender.send_safe(
                email_sender.send_password_changed_confirmation(user.email),
                email_type="password_changed_confirmation",
                user_id=user_id,
            )
        )

        logger.info(
            "password_changed",
            user_id=user_id,
            method="self_update",
        )

    @staticmethod
    async def request_email_change(
        db: AsyncSession,
        user_id: int,
        request: user_schemas.EmailChangeRequest,
    ) -> dict:
        user = await UserRepositoryBase.get_user_by_id(db, user_id, load_session=True)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        raw_email_change_code, hashed_email_change_code = generate_email_change_code()
        email_change_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_CHANGE_CODE_EXPIRES_MINUTES
        )

        user.session.pending_new_email = request.new_email
        user.session.email_change_code_hash = hashed_email_change_code
        user.session.email_change_code_expires_at = email_change_code_expires_at

        await db.commit()

        asyncio.create_task(
            email_sender.send_safe(
                email_sender.send_email_change_verification(
                    request.new_email, raw_email_change_code
                ),
                email_type="email_change_verification",
                user_id=user_id,
            )
        )

        logger.info(
            "email_change_requested",
            user_id=user_id,
        )

        return MessageResponse(detail=PublicMessages.EMAIL_CHANGE_REQUESTED)

    @staticmethod
    async def confirm_email_change(
        db: AsyncSession,
        user_id: int,
        code: str,
    ) -> dict:
        user = await UserRepositoryBase.get_user_by_id(db, user_id, load_session=True)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        if (
            user.session.pending_new_email is None
            or user.session.email_change_code_hash is None
        ):
            raise InvalidEmailChangeCodeError(HTTP400.INVALID_EMAIL_CHANGE_CODE)

        if (
            user.session.email_change_code_expires_at is None
            or datetime.now(timezone.utc) > user.session.email_change_code_expires_at
        ):
            raise ExpiredEmailChangeCodeError(HTTP400.EXPIRED_EMAIL_CHANGE_CODE)

        if not verify_email_change_code(code, user.session.email_change_code_hash):
            raise InvalidEmailChangeCodeError(HTTP400.INVALID_EMAIL_CHANGE_CODE)

        user.email = user.session.pending_new_email

        user.session.pending_new_email = None
        user.session.email_change_code_hash = None
        user.session.email_change_code_expires_at = None

        user.session.access_token_version += 1
        user.session.refresh_token_hash = None
        user.session.refresh_token_family = None
        user.session.refresh_token_expires_at = None

        await db.commit()

        await delete_cache(
            UserCacheKey.user_detail_key_admin(user_id),
            UserCacheKey.user_detail_key_staff(user_id),
            UserCacheKey.user_detail_key_self(user_id),
            SessionCacheKey.access_token_version_key(user_id),
        )

        logger.info(
            "email_changed",
            user_id=user_id,
        )

        return MessageResponse(detail=PublicMessages.EMAIL_CHANGE_CONFIRMED)
