import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.service import UserServiceAdmin
from src.user.schemas import CreateUserAdmin
from src.user.models import UserRole
from src.utils.exceptions import (
    CannotCreateSystemAdminError,
    UserAlreadyInactiveError,
    UserNotFoundError,
)
from tests.factories import make_member, make_user


class TestCreateAccountAdmin:
    async def test_creates_user_successfully(self, test_db: AsyncSession, system_admin):
        request = CreateUserAdmin(
            first_name="New",
            last_name="User",
            email="newuser@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.library_admin,
        )

        user = await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

        assert user.id is not None
        assert user.email == "newuser@gmail.com"
        assert user.role == UserRole.library_admin
        assert user.is_active is False          # must activate via invite
        assert user.invite_token_hash is not None
        assert user.password_hash is None       # no password until activation

    async def test_blocks_system_admin_creation(self, test_db: AsyncSession, system_admin):
        request = CreateUserAdmin(
            first_name="Evil",
            last_name="Admin",
            email="evil@gmail.com",
            phone_number="+15550000002",
            date_of_birth="1990-01-01",
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotCreateSystemAdminError):
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

        

    async def test_rejects_duplicate_email(self, test_db: AsyncSession, system_admin):
        await make_user(test_db, email="taken@gmail.com")
        request = CreateUserAdmin(
            first_name="Another",
            last_name="User",
            email="taken@gmail.com",  # same email
            phone_number="+15550000003",
            date_of_birth="1990-01-01",
            role=UserRole.member,
        )

        # handle_user_integrity_error raises AppException
        with pytest.raises(Exception) as exc_info:
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

        assert "email" in str(exc_info.value.detail).lower()

class TestDeactivateUserAdmin:
    async def test_deactivates_active_user(self, test_db: AsyncSession, system_admin):
        user = await make_member(test_db)
        assert user.is_active is True

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)
        assert user.is_active is False
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None

    async def test_increments_token_version_on_deactivation(self, test_db, system_admin):
        user = await make_member(test_db)
        original_version = user.access_token_version

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)
        assert user.access_token_version == original_version + 1

    async def test_raises_if_already_inactive(self, test_db, system_admin):
        user = await make_member(test_db, is_active=False)

        with pytest.raises(UserAlreadyInactiveError):
            await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

    async def test_raises_if_user_not_found(self, test_db, system_admin):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.deactivate_user_admin(test_db, 99999, system_admin.id)