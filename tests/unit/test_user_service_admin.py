import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.repository import UserRepositoryBase
from src.user.schemas import CreateUserAdmin, UpdateUser, UpdateUserPasswordAdmin
from src.user.service import UserServiceAdmin
from src.utils.exceptions import (
    CannotAssignSystemRoleError,
    CannotCreateSystemAdminError,
    EmailAlreadyTakenError,
    PhonenumberAlreadyTakenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from tests.constants import NEW_PASSWORD, OLD_PASSWORD
from tests.factories import make_library_admin, make_member, make_user
from utils.cache_keys import user_detail_key_admin


class TestCreateAccountAdmin:
    async def test_block_system_admin_creation(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request: CreateUserAdmin,
    ):
        valid_create_user_request.role = UserRole.system_admin

        with pytest.raises(CannotCreateSystemAdminError):
            await UserServiceAdmin.create_account_admin(
                test_db, valid_create_user_request, system_admin.id
            )

    @pytest.mark.parametrize(
        ("existing_user_data", "request_override", "expected_exception"),
        [
            (
                {"email": "taken@gmail.com"},
                {"email": "taken@gmail.com"},
                EmailAlreadyTakenError,
            ),
            (
                {"username": "taken_username"},
                {"username": "taken_username"},
                UsernameAlreadyTakenError,
            ),
            (
                {"phone_number": "+992 000 000 000"},
                {"phone_number": "+992 000 000 000"},
                PhonenumberAlreadyTakenError,
            ),
        ],
    )
    async def test_reject_duplicate_fields(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request: CreateUserAdmin,
        existing_user_data: dict,
        request_override: dict,
        expected_exception,
    ):
        await make_user(
            test_db,
            **existing_user_data,
        )

        for field, value in request_override.items():
            setattr(valid_create_user_request, field, value)

        with pytest.raises(expected_exception):
            await UserServiceAdmin.create_account_admin(
                test_db, valid_create_user_request, system_admin.id
            )

    async def test_create_user_session_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, valid_create_user_request, system_admin.id
        )

        await test_db.refresh(user)

        user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)
        session = user_session.session

        assert session.id is not None
        assert session.user_id == user.id
        assert session.access_token_version == 1
        assert session.refresh_token_hash is None
        assert session.refresh_token_expires_at is None
        assert session.refresh_token_family is None
        assert session.failed_login_attempts == 0
        assert session.locked_until is None

    async def test_create_user_activation_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, valid_create_user_request, system_admin.id
        )

        await test_db.refresh(user)

        user_activation = await UserRepositoryBase.get_user_with_activation(
            test_db, user.id
        )
        activation = user_activation.activation

        assert activation.id is not None
        assert activation.user_id == user.id
        assert activation.invite_token_hash is not None
        assert activation.invite_token_expires_at is not None
        assert activation.account_activation_code_hash is None
        assert activation.account_activation_code_expires_at is None

    async def test_create_user_successfully(
        self, test_db: AsyncSession, system_admin: User, valid_create_user_request: CreateUserAdmin
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, valid_create_user_request, system_admin.id
        )

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is None
        assert user.created_by == system_admin.id


class TestGetUserByIDAdmin:
    async def test_get_user_by_id_admin_raises_not_found(self, test_db: AsyncSession):
        user = await make_user(test_db)
        non_existent_id = user.id + 9999999

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.get_user_by_id_admin(test_db, non_existent_id)

    async def test_get_user_by_id_admin_returns_correct_data(self, test_db: AsyncSession):
        user = await make_member(
            test_db,
            email="test_email@gmail.com",
            phone_number="+1 000 0000",
        )

        result = await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        assert result["id"] == user.id
        assert result["email"] == "test_email@gmail.com"
        assert result["phone_number"] == "+1 000 0000"
        assert result["role"] == UserRole.member
        assert result["is_active"] == user.is_active

    async def test_get_user_by_id_admin_populates_cache_after_db_hit(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        mock_set_cache = mocker.patch("src.user.service.set_cache")

        await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        mock_set_cache.assert_called_once_with(
            user_detail_key_admin(user.id),
            mocker.ANY,
            600,
        )

    async def test_get_user_by_id_admin_returns_cached_data(self, test_db: AsyncSession):
        user = await make_member(test_db)

        first_result = await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        second_result = await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        assert second_result == first_result

    async def test_get_user_by_id_admin_does_not_hit_db_on_cache_hit(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        mock_get_user = mocker.patch.object(UserRepositoryBase, "get_user_by_id")

        await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        mock_get_user.assert_not_called()


class TestDeactivateUserAdmin:
    async def test_does_not_deactivate_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.deactivate_user_admin(
                test_db, 999999, system_admin.id
            )

    async def test_does_not_deactivate_already_inactive_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=False,
        )

        with pytest.raises(UserAlreadyInactiveError):
            await UserServiceAdmin.deactivate_user_admin(
                test_db, user.id, system_admin.id
            )

    async def test_deactivate_active_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is False
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
        assert user.refresh_token_expires_at is None

    async def test_increment_access_token_version_on_deactivation(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)

        original_version = user.access_token_version

        await UserServiceAdmin.deactivate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.access_token_version == original_version + 1


class TestActivateUserAdmin:
    async def test_does_not_activate_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.activate_user_admin(test_db, 999999, system_admin.id)

    async def test_does_not_activate_already_active_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=True,
        )

        with pytest.raises(UserAlreadyActiveError):
            await UserServiceAdmin.activate_user_admin(
                test_db, user.id, system_admin.id
            )

    async def test_activate_inactive_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=False,
        )

        await UserServiceAdmin.activate_user_admin(test_db, user.id, system_admin.id)

        await test_db.refresh(user)

        assert user.is_active is True


class TestUpdateUserAdmin:
    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        update_request = UpdateUserAdmin(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_admin(
                test_db, 999999, update_request, system_admin.id
            )

    async def test_cannot_assign_system_admin_role(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_library_admin(test_db)

        update_request = UpdateUserAdmin(
            role=UserRole.system_admin,
        )

        with pytest.raises(CannotAssignSystemAdminRoleError):
            await UserServiceAdmin.update_user_admin(
                test_db, user.id, update_request, system_admin.id
            )

    async def test_cannot_assign_system_role(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)

        request = UpdateUserAdmin(
            role=UserRole.library_admin,
        )

        with pytest.raises(CannotAssignSystemRoleError):
            await UserServiceAdmin.update_user_admin(
                test_db, user.id, request, system_admin.id
            )

    async def test_reject_duplicate_email(
        self, test_db: AsyncSession, system_admin: User
    ):
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
            await UserServiceAdmin.update_user_admin(
                test_db, user_to_be_updated.id, update_request, system_admin.id
            )

    async def test_reject_duplicate_username(
        self, test_db: AsyncSession, system_admin: User
    ):
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
            await UserServiceAdmin.update_user_admin(
                test_db, user_to_be_updated.id, update_request, system_admin.id
            )

    async def test_reject_duplicate_phone_number(
        self, test_db: AsyncSession, system_admin: User
    ):
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
            await UserServiceAdmin.update_user_admin(
                test_db, user_to_be_updated.id, update_request, system_admin.id
            )

    async def test_update_user_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_library_admin(test_db)

        update_request = UpdateUserAdmin(
            first_name="User_name",
            last_name="User_surname",
        )

        await UserServiceAdmin.update_user_admin(
            test_db, user.id, update_request, system_admin.id
        )

        await test_db.refresh(user)

        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"


class TestUpdateUserPasswordAdmin:
    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        update_request = UpdateUserAdmin(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_password_admin(
                test_db, 999999, update_request, system_admin.id
            )

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

        await UserServiceAdmin.update_user_password_admin(
            test_db, user.id, update_request, system_admin.id
        )

        await test_db.refresh(user)

        assert old_password_hash != user.password_hash
        assert user.access_token_version == original_version + 1
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
