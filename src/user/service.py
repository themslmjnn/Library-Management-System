from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import delete_cache, get_cache, set_cache
from src.core.logging import get_logger
from src.core.security import (
    generate_account_activation_code,
    generate_invite_token,
    hash_password,
    verify_password,
)
from src.pagination import PaginatedResponse
from src.user.models import User, UserRole
from src.user.repository import (
    UserRepositoryAdmin,
    UserRepositoryBase,
    UserRepositoryStaff,
)
from src.user.schemas import (
    CreateUserAdmin,
    CreateUserBase,
    CreateUserPublic,
    SearchUserAdmin,
    SearchUserBase,
    UpdateUserAdmin,
    UpdateUserBase,
    UpdateUserPasswordAdmin,
    UpdateUserPasswordPublic,
    UserResponseAdmin,
    UserResponseBase,
    UserResponseStaff,
)
from src.utils.cache_keys import user_detail_key
from src.utils.email import send_account_activation_code, send_invite_email
from src.utils.exception_constants import HTTP400, HTTP404
from src.utils.exceptions import (
    IncorrectPasswordError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
    handle_user_integrity_error,
)
from src.utils.helpers import ensure_exists, update_object

logger = get_logger(__name__)


class UserServiceAdmin:
    @staticmethod
    async def create_account_admin(db: AsyncSession, user_request: CreateUserAdmin, current_user_id: int) -> User:
        if user_request.role == UserRole.system_admin:
            logger.warning(
                "create_user_denied",
                reason="cannot_create_system_admin",
                requested_by=current_user_id,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create system_admin accounts through the API",
            ) 
        
        raw_invite_token, hashed_invite_token = generate_invite_token()
        invite_token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        new_user = User(
            **user_request.model_dump(),
            is_active=False,
            invite_token_hash=hashed_invite_token,
            invite_token_expires_at=invite_token_expires_at,
            created_by=current_user_id,
        )

        try:
            UserRepositoryBase.add_user(db, new_user)

            await db.commit()
            await db.refresh(new_user)
            
            send_invite_email(new_user.email, raw_invite_token)

            logger.info(
                "user_created",
                new_user_id=new_user.id,
                role=user_request.role,
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
    async def get_users_admin(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserAdmin,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        users, total = await UserRepositoryAdmin.get_users_admin(db, skip, limit, filters, sort_by, order)

        return PaginatedResponse(
            items=users,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    

    @staticmethod
    async def get_user_by_id_admin(db: AsyncSession, user_id: int) -> UserResponseAdmin:
        key = user_detail_key(user_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached
        
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        serialized = UserResponseAdmin.model_validate(user).model_dump(mode="json")
        await set_cache(key, serialized, 600)

        return serialized
    

    @staticmethod
    async def deactivate_user_admin(db: AsyncSession, user_id: int, current_user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
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
        user.access_token_version += 1
        user.refresh_token_hash = None
        user.refresh_token_family = None
        user.refresh_token_expires_at = None

        await db.commit()

        key = user_detail_key(user_id)
        await delete_cache(key)

        logger.info(
            "user_deactivated",
            target_user_id=user_id,
            deactivated_by=current_user_id,
        )


    @staticmethod
    async def activate_user_admin(db: AsyncSession, user_id: int, current_user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
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

        key = user_detail_key(user_id)
        await delete_cache(key)

        logger.info(
            "user_activated",
            target_user_id=user_id,
            activated_by=current_user_id,
        )


    @staticmethod
    async def update_user_admin(db: AsyncSession, user_id: int, update_request: UpdateUserAdmin, current_user_id: int) -> User:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        if update_request.role is not None:
            if update_request.role == UserRole.system_admin:
                logger.error(
                    "update_user_denied",
                    reason="cannot_update_role_to_system_admin",
                    requested_by=current_user_id,
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update role to system_admin through the API",
                ) 

            if user.role in (UserRole.guest, UserRole.member) and update_request.role not in (UserRole.guest, UserRole.member):
                logger.error(
                    "update_user_denied",
                    target_user_id=user_id,
                    requested_by=current_user_id,
                    reason="can_not_assign_regular_user_role_a_system_role",
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Can not assign regular users a system role",
                )

        try:
            update_object(user, update_request)

            await db.commit()
            await db.refresh(user)

            key = user_detail_key(user_id)
            await delete_cache(key)

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
    async def update_password_admin(db: AsyncSession, user_id: int, password_request: UpdateUserPasswordAdmin, current_user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        user.password_hash = hash_password(password_request.new_password)
        user.access_token_version += 1
        user.refresh_token_hash = None
        user.refresh_token_family = None
        user.refresh_token_expires_at = None

        await db.commit()

        key = user_detail_key(user_id)
        await delete_cache(key)
        
        logger.info(
            "password_changed",
            target_user_id=user_id,
            changed_by=current_user_id,
            method="admin_reset",
        )


class UserServiceStaff:
    @staticmethod
    async def create_account_staff(db: AsyncSession, user_request: CreateUserBase, current_user_id: int) -> User:
        raw_invite_token, invite_token_hash = generate_invite_token()
        invite_token_expires_at = datetime.now(timezone.utc) + timedelta(days=2)

        new_user = User(
            **user_request.model_dump(),
            role=UserRole.guest,
            is_active=False,
            invite_token_hash=invite_token_hash,
            invite_token_expires_at=invite_token_expires_at,
            created_by=current_user_id,
        )

        try:
            UserRepositoryBase.add_user(db, new_user)

            await db.commit()
            await db.refresh(new_user)

            send_invite_email(new_user.email, raw_invite_token)

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
                "user_creation_failed",
                reason="integrity_error",
                error=str(e.orig),
                created_by=current_user_id,
            )

            handle_user_integrity_error(e)
            raise


    @staticmethod
    async def get_users_staff(db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserBase,
        current_user: User,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        if current_user.role == UserRole.library_admin:
            users, total = await UserRepositoryStaff.get_users_library_admin(db, skip, limit, filters, sort_by, order)
        elif current_user.role == UserRole.receptionist:
            users, total = await UserRepositoryStaff.get_users_receptionist(db, skip, limit, filters, sort_by, order)

        return PaginatedResponse(
            items=users,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    

    @staticmethod
    async def get_user_by_id_staff(db: AsyncSession, user_id: int, current_user: User) -> UserResponseStaff:
        if current_user.role == UserRole.library_admin:
            user = await UserRepositoryStaff.get_user_by_id_library_admin(db, user_id)
        elif current_user.role == UserRole.receptionist:
            user = await UserRepositoryStaff.get_user_by_id_receptionist(db, user_id)

        key = user_detail_key(user_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached
        
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        serialized = UserResponseStaff.model_validate(user).model_dump(mode="json")
        await set_cache(key, serialized, 600)

        return serialized


class UserServicePublic:
    @staticmethod
    async def create_account_public(db: AsyncSession, user_request: CreateUserPublic) -> User:
        raw_activation_code, hashed_activation_code = generate_account_activation_code()
        account_activation_code_expires_at = datetime.now(timezone.utc) + timedelta(days=1)

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
            account_activation_code_hash=hashed_activation_code,
            account_activation_code_expires_at=account_activation_code_expires_at
        )

        try:
            UserRepositoryBase.add_user(db, new_user)

            await db.commit()
            await db.refresh(new_user)

            send_account_activation_code(new_user.email, raw_activation_code)

            logger.info(
                "user_registered", 
                user_id=new_user.id,
                method="self-registered",
            )

            return new_user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "user_registration_failed",
                reason="integrity_error",
                error=str(e.orig),
            )

            handle_user_integrity_error(e)
            raise


    @staticmethod
    async def get_me(db: AsyncSession, user_id: int) -> UserResponseBase:
        key = user_detail_key(user_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached
        
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))

        serialized = UserResponseBase.model_validate(user).model_dump(mode="json")
        await set_cache(key, serialized, 600)

        return serialized
    

    @staticmethod
    async def update_me(db: AsyncSession, update_request: UpdateUserBase, user_id: int) -> User:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        try:
            update_object(user, update_request)

            await db.commit()
            await db.refresh(user)

            key = user_detail_key(user_id)
            await delete_cache(key)

            logger.info(
                "user_updated",
                target_user_id=user.id,
                method="self_update",
            )

            return user
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "update_user_denied",
                target_user_id=user.id,
                reason=str(e.orig),
            )

            handle_user_integrity_error(e)
            raise


    @staticmethod
    async def update_my_password(db: AsyncSession, password_request: UpdateUserPasswordPublic, user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        if not verify_password(password_request.old_password, user.password_hash):
            raise IncorrectPasswordError(HTTP400.INCORRECT_PASSWORD)
        
        user.password_hash = hash_password(password_request.new_password)
        user.access_token_version += 1
        user.refresh_token_hash = None
        user.refresh_token_family = None
        user.refresh_token_expires_at = None

        await db.commit()

        key = user_detail_key(user_id)
        await delete_cache(key)

        logger.info(
            "password_changed",
            user_id=user.id,
            method="self_update",
        )