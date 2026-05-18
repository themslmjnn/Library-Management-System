import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.schemas import CreateUserBase
from src.user.service import UserServiceStaff
from src.utils.exceptions import (
    AccessDeniedError,
    EmailAlreadyTakenError,
    PhonenumberAlreadyTakenError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from tests.factories import (
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
    make_user,
)
from user.repository import UserRepositoryBase


class TestCreateAccountStaff:
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
        valid_create_user_request_staff: CreateUserBase,
        existing_user_data: dict,
        request_override: dict,
        expected_exception,
    ):
        await make_user(
            test_db,
            **existing_user_data,
        )

        for field, value in request_override.items():
            setattr(valid_create_user_request_staff, field, value)

        with pytest.raises(expected_exception):
            await UserServiceStaff.create_account_staff(
                test_db, valid_create_user_request_staff, system_admin.id
            )

    async def test_create_user_session_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_staff: CreateUserBase,
    ):
        user = await UserServiceStaff.create_account_staff(
            test_db, valid_create_user_request_staff, system_admin.id
        )

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
        valid_create_user_request_staff: CreateUserBase,
    ):
        user = await UserServiceStaff.create_account_staff(
            test_db, valid_create_user_request_staff, system_admin.id
        )

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
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_staff: CreateUserBase,
    ):
        user = await UserServiceStaff.create_account_staff(
            test_db, valid_create_user_request_staff, system_admin.id
        )

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is None
        assert user.created_by == system_admin.id


class TestGetUsersStaff:
    async def test_get_users_staff_return_valid_info_for_library_admin(
        self, test_db: AsyncSession, library_admin: User
    ):
        await make_system_admin(test_db)
        await make_library_admin(test_db)
        visible_user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_users_staff(
            test_db,
            skip=0,
            limit=20,
            filters=None,
            current_user=library_admin,
            sort_by="created_at",
            order="desc",
        )

        roles = [user.role for user in result.items]

        assert UserRole.system_admin not in roles
        assert UserRole.library_admin not in roles
        assert visible_user.id in [user.id for user in result.items]

    async def test_get_users_staff_return_valid_info_for_receptionist(
        self, test_db: AsyncSession, receptionist: User
    ):
        await make_system_admin(test_db)
        await make_library_admin(test_db)
        await make_receptionist(test_db)
        visible_user = await make_member(test_db)

        result = await UserServiceStaff.get_users_staff(
            test_db,
            skip=0,
            limit=20,
            filters=None,
            current_user=receptionist,
            sort_by="created_at",
            order="desc",
        )

        roles = [user.role for user in result.items]

        assert UserRole.system_admin not in roles
        assert UserRole.library_admin not in roles
        assert UserRole.receptionist not in roles
        assert visible_user.id in [user.id for user in result.items]

    async def test_get_users_staff_raises_for_unauthorized_role(
        self, test_db: AsyncSession, system_admin: User
    ):
        with pytest.raises(AccessDeniedError):
            await UserServiceStaff.get_users_staff(
                test_db,
                skip=0,
                limit=20,
                filters=None,
                current_user=system_admin,
                sort_by="created_at",
                order="desc",
            )


class TestGetUserByIDStaff:
    async def test_library_admin_can_not_view_library_and_system_admins(
        self, test_db: AsyncSession, library_admin: User
    ):
        user1 = await make_library_admin(test_db)
        user2 = await make_system_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(
                test_db, user1.id, library_admin
            )

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(
                test_db, user2.id, library_admin
            )

    async def test_get_user_by_id_staff_return_valid_info_for_library_admin(
        self, test_db: AsyncSession, library_admin: User
    ):
        user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(
            test_db, user.id, library_admin
        )

        assert result["id"] == user.id
        assert result["role"] == UserRole.receptionist

    async def test_receptionist_can_not_view_higher_roles(
        self, test_db: AsyncSession, receptionist: User
    ):
        user1 = await make_receptionist(test_db)
        user2 = await make_library_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user1.id, receptionist)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user2.id, receptionist)

    async def test_get_user_by_id_staff_return_valid_info_for_receptionist(
        self, test_db: AsyncSession, receptionist: User
    ):
        user = await make_member(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(
            test_db, user.id, receptionist
        )

        assert result["id"] == user.id
        assert result["role"] == UserRole.member

    async def test_get_user_by_id_staff_raises_for_unauthorized_role(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        with pytest.raises(AccessDeniedError):
            await UserServiceStaff.get_user_by_id_staff(
                test_db,
                user_id=non_existant_id,
                current_user=system_admin,
            )
