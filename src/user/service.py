from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    generate_account_activation_code,
    generate_invite_token,
    hash_password,
    verify_password,
)
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
    SearchUser,
    UpdateUserAdmin,
    UpdateUserBase,
    UpdateUserPasswordAdmin,
    UpdateUserPasswordPublic,
)
from src.utils.email import send_account_activation_code, send_invite_email
from src.utils.exception_constants import HTTP400, HTTP404
from src.utils.exceptions import handle_user_integrity_error
from src.utils.helpers import ensure_exists, update_object


class UserServiceAdmin:
    @staticmethod
    async def create_account_admin(db: AsyncSession, user_request: CreateUserAdmin, current_user: User) -> User:
        if user_request.role == UserRole.system_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create system_admin accounts through the API",
            ) 
        
        raw_invite_token, hashed_invite_token = generate_invite_token()
        invite_token_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=2)
        )

        new_user = User(\
            username=user_request.username,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            date_of_birth=user_request.date_of_birth,
            email=user_request.email,
            phone_number=user_request.phone_number,
            role=user_request.role,
            is_active=False,
            invite_token_hash=hashed_invite_token,
            invite_token_expires_at=invite_token_expires_at,
            created_by=current_user.id,
        )

        try:
            UserRepositoryBase.add_user(db, new_user)

            await db.commit()
            await db.refresh(new_user)

            send_invite_email(new_user.email, raw_invite_token)

            return new_user
        
        except IntegrityError as e:
            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def get_users_admin(db: AsyncSession) -> list[User]:
        users = await UserRepositoryAdmin.get_users_admin(db)

        return users
    
    @staticmethod
    async def search_users_admin(db: AsyncSession, search_request: SearchUser) -> list[User]:
        users = await UserRepositoryAdmin.search_users_admin(db, search_request)

        return users
    
    @staticmethod
    async def get_user_by_id_admin(db: AsyncSession, user_id: int) -> User:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        ensure_exists(user, HTTP404.USER)

        return user
    
    @staticmethod
    async def deactivate_user_admin(db: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        ensure_exists(user, HTTP404.USER)

        user.is_active = False
        user.access_token_version += 1
        user.refresh_token_hash = None
        user.refresh_token_family = None
        user.refresh_token_expires_at = None

        await db.commit()

    @staticmethod
    async def activate_user_admin(db: AsyncSession, user_id: int) -> None:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        ensure_exists(user, HTTP404.USER)

        user.is_active = True

        await db.commit()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, update_request: UpdateUserAdmin) -> User:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        ensure_exists(user, HTTP404.USER)

        try:
            update_object(user, update_request)

            await db.commit()
            await db.refresh(user)

            return user
        
        except IntegrityError as e:
            handle_user_integrity_error(e)   
            raise


    @staticmethod
    async def update_password(db: AsyncSession, user_id: int, password_request: UpdateUserPasswordAdmin):
        user = await UserRepositoryBase.get_user_by_id(db, user_id)

        ensure_exists(user, HTTP404.USER)

        user.password_hash = hash_password(password_request.new_password)

        await db.commit()



class UserServiceStaff:
    @staticmethod
    async def create_account_staff(db: AsyncSession, user_request: CreateUserBase, current_user: User) -> User:
        raw_invite_token, invite_token_hash = generate_invite_token()
        invite_token_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=2)
        )

        new_user = User(\
            username=user_request.username,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            date_of_birth=user_request.date_of_birth,
            email=user_request.email,
            phone_number=user_request.phone_number,
            role=UserRole.guest,
            is_active=False,
            invite_token_hash=invite_token_hash,
            invite_token_expires_at=invite_token_expires_at,
            created_by=current_user.id,
        )

        try:
            UserRepositoryBase.add_user(db, new_user)

            await db.commit()
            await db.refresh(new_user)

            send_invite_email(new_user.email, raw_invite_token)

            return new_user
        
        except IntegrityError as e:
            handle_user_integrity_error(e)
            raise

    @staticmethod
    async def get_users_staff(db: AsyncSession, current_user: User) -> list[User]:
        if current_user.role == UserRole.library_admin:
            users = await UserRepositoryStaff.get_users_library_admin(db)
        elif current_user.role == UserRole.receptionist:
            users = await UserRepositoryStaff.get_users_receptionist(db)

        return users
    
    @staticmethod
    async def search_users_staff(db: AsyncSession, search_request: SearchUser, current_user: User) -> list[User]:
        if current_user.role == UserRole.library_admin:
            users = await UserRepositoryStaff.search_users_library_admin(db, search_request)
        elif current_user.role == UserRole.receptionist:
            users = await UserRepositoryStaff.search_users_receptionist(db, search_request)

        return users
    
    @staticmethod
    async def get_user_by_id_staff(db: AsyncSession, user_id: int, current_user: User) -> User:
        if current_user.role == UserRole.library_admin:
            user = await UserRepositoryStaff.get_user_by_id_library_admin(db, user_id)
        elif current_user.role == UserRole.receptionist:
            user = await UserRepositoryStaff.get_user_by_id_receptionist(db, user_id)

        ensure_exists(user, HTTP404.USER)

        return user


class UserServicePublic:
    @staticmethod
    async def create_account_public(db: AsyncSession, user_request: CreateUserPublic) -> User:
        raw_activation_code, hashed_activation_code = generate_account_activation_code()
        account_activation_code_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=1)
        )

        new_user = User(\
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

            return new_user
        
        except IntegrityError as e:
            handle_user_integrity_error(e)
            raise


    @staticmethod
    async def update_me(db: AsyncSession, update_request: UpdateUserBase, current_user: User) -> User:
        try:
            update_object(current_user, update_request)

            await db.commit()
            await db.refresh(current_user)

            return current_user
        except IntegrityError as e:
            handle_user_integrity_error(e)
                
            raise


    @staticmethod
    async def update_my_password(db: AsyncSession, password_request: UpdateUserPasswordPublic, current_user: User) -> None:
        verify_password(password_request.old_password, current_user.password_hash, HTTP400.INCORRECT_PASSWORD)
        
        current_user.password_hash = hash_password(password_request.new_password)

        await db.commit()