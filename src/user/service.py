from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    generate_account_activation_code,
    generate_invite_token,
    hash_password,
)
from src.user.models import User, UserRole
from src.user.repository import UserRepositoryBase
from src.user.schemas import CreateUserAdmin, CreateUserBase, CreateUserPublic
from src.utils.email import send_account_activation_code, send_invite_email
from src.utils.exceptions import handle_user_integrity_error


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