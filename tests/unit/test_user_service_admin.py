import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.schemas import CreateUserAdmin, UpdateUserAdmin, UpdateUserPasswordAdmin
from src.user.service import UserServiceAdmin
from src.utils.exceptions import (
    CannotAssignSystemAdminRoleError,
    CannotAssignSystemRoleError,
    EmailAlreadyTakenError,
    PhonenumberAlreadyTakenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from tests.factories import make_library_admin, make_member, make_user

OLD_PASSWORD = "OldPassword123!"
NEW_PASSWORD = "NewPassword123!"


class TestCreateAccountAdmin:
    async def test_block_system_admin_creation(self, test_db: AsyncSession, system_admin: User):
        create_request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotAssignSystemAdminRoleError):
            await UserServiceAdmin.create_account_admin(test_db, create_request, system_admin.id)


    async def test_reject_duplicate_email(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            email="taken@gmail.com",
        )

        update_request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="taken@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, update_request, system_admin.id)

        
    async def test_reject_duplicate_username(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            username="taken_username",
        )

        update_request = CreateUserAdmin(
            username="taken_username",
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, update_request, system_admin.id)

    
    async def test_reject_duplicate_phone_number(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            phone_number="+992 000 000 000",
        )

        update_request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+992 000 000 000",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, update_request, system_admin.id)


    async def test_create_user_successfully(self, test_db: AsyncSession, system_admin: User):
        create_request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.library_admin,
        )

        user = await UserServiceAdmin.create_account_admin(test_db, create_request, system_admin.id)

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.library_admin
        assert user.is_active is False
        assert user.invite_token_hash is not None
        assert user.password_hash is None


class TestDeactivateUserAdmin:
    async def test_does_not_deactivate_unknown_user(self, test_db: AsyncSession, system_admin: User):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.deactivate_user_admin(test_db, 999999, system_admin.id)


    async def test_does_not_deactivate_already_inactive_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=False,
        )

        with pytest.raises(UserAlreadyInactiveError):
            await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)


    async def test_deactivate_active_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(test_db)

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is False
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
        assert user.refresh_token_expires_at is None


    async def test_increment_access_token_version_on_deactivation(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(test_db)

        original_version = user.access_token_version

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.access_token_version == original_version + 1


class TestActivateUserAdmin:
    async def test_does_not_activate_unknown_user(self, test_db: AsyncSession, system_admin: User):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.activate_user_admin(test_db, 999999, system_admin.id)


    async def test_does_not_activate_already_active_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=True,
        )

        with pytest.raises(UserAlreadyActiveError):
            await UserServiceAdmin.activate_user_admin(test_db, user.id, system_admin.id)


    async def test_activate_inactive_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=False,
        )

        await UserServiceAdmin.activate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is True


class TestUpdateUserAdmin:
    async def test_does_not_update_unknown_user(self, test_db: AsyncSession, system_admin: User):
        update_request = UpdateUserAdmin(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_admin(test_db, 999999, update_request, system_admin.id)


    async def test_cannot_assign_system_admin_role(self, test_db: AsyncSession, system_admin: User):
        user = await make_library_admin(test_db)

        update_request = UpdateUserAdmin(
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotAssignSystemAdminRoleError):
            await UserServiceAdmin.update_user_admin(test_db, user.id, update_request, system_admin.id)


    async def test_cannot_assign_system_role(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(test_db)

        request = UpdateUserAdmin(
            role=UserRole.library_admin,
        )

        with pytest.raises(CannotAssignSystemRoleError):
            await UserServiceAdmin.update_user_admin(test_db, user.id, request, system_admin.id)

    
    async def test_reject_duplicate_email(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            email="taken@gmail.com",
        )

        user_to_be_updated = await make_member(
            test_db,
            email="other@gmail.com",
        )

        update_request = UpdateUserAdmin(
            email="taken@gmail.com",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user_to_be_updated.id, update_request, system_admin.id)


    async def test_reject_duplicate_username(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            username="test_user",
        )

        user_to_be_updated = await make_member(
            test_db,
            username="test_user2",
        )

        update_request = UpdateUserAdmin(
           username="test_user",
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user_to_be_updated.id, update_request, system_admin.id)

    
    async def test_reject_duplicate_phone_number(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            phone_number="+992 000 111 222",
        )

        user_to_be_updated = await make_member(
            test_db,
            phone_number="+992 000 111 333",
        )

        update_request = UpdateUserAdmin(
           phone_number="+992 000 111 222",
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user_to_be_updated.id, update_request, system_admin.id)


    async def test_update_user_successfully(self, test_db: AsyncSession, system_admin: User):
        user = await make_library_admin(test_db)

        update_request = UpdateUserAdmin(
            first_name="User_name",
            last_name="User_surname",
        )

        await UserServiceAdmin.update_user_admin(test_db, user.id, update_request, system_admin.id)

        await test_db.refresh(user)

        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"


class TestUpdateUserPasswordAdmin:
    async def test_does_not_update_unknown_user(self, test_db: AsyncSession, system_admin: User):
        update_request = UpdateUserAdmin(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_password_admin(test_db, 999999, update_request, system_admin.id)


    async def test_update_password_and_invalidates_tokens(self, test_db, system_admin):
        user = await make_member(
            test_db, 
            password=OLD_PASSWORD,
        )
        
        user.refresh_token_hash = "some_token"
        user.refresh_token_family = "some_family"

        await test_db.commit()

        original_version = user.access_token_version
        old_password_hash = user.password_hash

        update_request = UpdateUserPasswordAdmin(
            new_password=NEW_PASSWORD,
        )

        await UserServiceAdmin.update_user_password_admin(test_db, user.id, update_request, system_admin.id)

        await test_db.refresh(user)

        assert old_password_hash != user.password_hash
        assert user.access_token_version == original_version + 1
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None