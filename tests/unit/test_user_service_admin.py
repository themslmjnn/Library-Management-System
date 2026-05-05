import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.service import UserServiceAdmin
from src.user.schemas import CreateUserAdmin, UpdateUserPasswordAdmin, UpdateUserAdmin
from src.user.models import User, UserRole
from src.utils.exceptions import (
    CannotCreateSystemAdminError,
    CannotAssignSystemRoleError,
    EmailAlreadyTakenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UserNotFoundError,
    PhonenumberAlreadyTakenError,
    UsernameAlreadyTakenError,
)
from tests.factories import make_library_admin, make_member, make_user


class TestCreateAccountAdmin:
    async def test_creates_user_successfully(self, test_db: AsyncSession, system_admin: User):
        request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.library_admin,
        )

        user = await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.library_admin
        assert user.is_active is False
        assert user.invite_token_hash is not None
        assert user.password_hash is None


    async def test_blocks_system_admin_creation(self, test_db: AsyncSession, system_admin: User):
        request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotCreateSystemAdminError):
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)


    async def test_rejects_duplicate_email(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            email="taken@gmail.com",
        )

        request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="taken@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

        
    async def test_rejects_duplicate_username(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            username="taken_username",
            email="test_email@gmail.com"
        )

        request = CreateUserAdmin(
            username="taken_username",
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)

    
    async def test_rejects_duplicate_phone_number(self, test_db: AsyncSession, system_admin: User):
        await make_user(
            test_db, 
            email="test_email@gmail.com",
            phone_number="+992 000 000 000",
        )

        request = CreateUserAdmin(
            first_name="Test_fname",
            last_name="Test_lname",
            email="just_email@gmail.com",
            phone_number="+992 000 000 000",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServiceAdmin.create_account_admin(test_db, request, system_admin.id)


class TestDeactivateUserAdmin:
    async def test_deactivates_active_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(test_db)

        assert user.is_active is True

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is False
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None


    async def test_increments_token_version_on_deactivation(self, test_db:AsyncSession, system_admin: User):
        user = await make_member(test_db)

        original_version = user.access_token_version

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.access_token_version == original_version + 1


    async def test_raises_if_already_inactive(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=False,
        )

        with pytest.raises(UserAlreadyInactiveError):
            await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)


    async def test_raises_if_user_not_found(self, test_db: AsyncSession, system_admin: User):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.deactivate_user_admin(test_db, 99999, system_admin.id)


class TestActivateUserAdmin:
    async def test_activates_inactive_user(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=False,
        )

        await UserServiceAdmin.activate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is True


    async def test_raises_if_already_active(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(
            test_db, 
            is_active=True,
        )

        with pytest.raises(UserAlreadyActiveError):
            await UserServiceAdmin.activate_user_admin(test_db, user.id, system_admin.id)


    async def test_raises_if_user_not_found(self, test_db: AsyncSession, system_admin: User):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.activate_user_admin(test_db, 99999, system_admin.id)


class TestUpdateAdmin:
    async def test_updates_user_successfully(self, test_db: AsyncSession, system_admin: User):
        user = await make_library_admin(test_db)

        request = UpdateUserAdmin(
            first_name="User_name",
            last_name="User_surname",
        )


        await UserServiceAdmin.update_user_admin(test_db, user.id, request, system_admin.id)

        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"


    async def test_cannot_create_system_admin(self, test_db: AsyncSession, system_admin: User):
        user = await make_library_admin(test_db)

        request = UpdateUserAdmin(
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotCreateSystemAdminError):
            await UserServiceAdmin.update_user_admin(test_db, user.id, request, system_admin.id)


    async def test_cannot_assign_system_role(self, test_db: AsyncSession, system_admin: User):
        user = await make_member(test_db)

        request = UpdateUserAdmin(
            role=UserRole.library_admin,
        )

        with pytest.raises(CannotAssignSystemRoleError):
            await UserServiceAdmin.update_user_admin(test_db, user.id, request, system_admin.id)

        
    async def test_update_user_not_found(self, test_db: AsyncSession, system_admin: User):
        await make_member(test_db)

        request = UpdateUserAdmin(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_admin(test_db, 9999999, request, system_admin.id)

    
    async def test_update_email_taken(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            email="taken@gmail.com",
        )

        user2 = await make_member(
            test_db,
            email="other@gmail.com",
        )

        request = UpdateUserAdmin(
            email="taken@gmail.com",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user2.id, request, system_admin.id)


    async def test_update_username_taken(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            username="test_user",
        )

        user2 = await make_member(
            test_db,
            username="test_user2",
        )

        request = UpdateUserAdmin(
           username="test_user",
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user2.id, request, system_admin.id)

    
    async def test_update_phone_number_taken(self, test_db: AsyncSession, system_admin: User):
        await make_member(
            test_db,
            phone_number="+992 000 111 222",
        )

        user2 = await make_member(
            test_db,
            phone_number="+992 000 111 333",
        )

        request = UpdateUserAdmin(
           phone_number="+992 000 111 222",
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServiceAdmin.update_user_admin(test_db, user2.id, request, system_admin.id)


class TestUpdatePasswordAdmin:
    async def test_changes_password_and_invalidates_tokens(self, test_db, system_admin):
        user = await make_member(test_db, password="OldPass123!")
        user.refresh_token_hash = "some_token"
        user.refresh_token_family = "some_family"
        await test_db.commit()

        original_version = user.access_token_version
        request = UpdateUserPasswordAdmin(new_password="NewPass456!")

        await UserServiceAdmin.update_password_admin(test_db, user.id, request, system_admin.id)

        await test_db.refresh(user)
        assert user.access_token_version == original_version + 1
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None