from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OrderBy
from src.email.enums import EmailType
from src.email.repository import PendingEmailRepository
from src.users.models import User, UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import (
    CreateUserAdmin,
    SearchUserAdmin,
    UpdateUser,
)
from src.users.service import UserServiceAdmin
from src.utils.cache_keys import UserCacheKey
from src.utils.custom_exceptions import (
    CannotCreateSystemAdminError,
    EmailAlreadyTakenError,
    PhonenumberAlreadyTakenError,
    UserAlreadyActiveError,
    UserAlreadyInactiveError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from tests.constants import NEW_PASSWORD, OLD_PASSWORD
from tests.factories import (
    make_library_admin,
    make_member,
    make_receptionist,
    make_user,
)
from utils.enums import BookSortField, UserSortField


class TestCreateAccountAdmin:
    async def test_block_system_admin_creation(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        valid_create_user_request_admin.role = UserRole.system_admin

        with pytest.raises(CannotCreateSystemAdminError):
            await UserServiceAdmin.create_account_admin(
                test_db, system_admin.id, valid_create_user_request_admin
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
        valid_create_user_request_admin: CreateUserAdmin,
        existing_user_data: dict,
        request_override: dict,
        expected_exception,
    ):
        await make_user(
            test_db,
            **existing_user_data,
        )

        for field, value in request_override.items():
            setattr(valid_create_user_request_admin, field, value)

        with pytest.raises(expected_exception):
            await UserServiceAdmin.create_account_admin(
                test_db, system_admin.id, valid_create_user_request_admin
            )

    async def test_create_user_session_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, system_admin.id, valid_create_user_request_admin
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session.session

        assert session.id is not None
        assert session.user_id == user.id
        assert session.access_token_version == 1
        assert session.refresh_token_hash is None
        assert session.refresh_token_expires_at is None
        assert session.refresh_token_family is None
        assert session.failed_login_attempts == 0
        assert session.locked_until is None
        assert session.reset_password_token_hash is None
        assert session.reset_password_token_expires_at is None
        assert session.pending_new_email is None
        assert session.email_change_code_hash is None
        assert session.email_change_code_expires_at is None

    async def test_create_user_activation_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, system_admin.id, valid_create_user_request_admin
        )

        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )
        activation = user_activation.activation

        assert activation.id is not None
        assert activation.user_id == user.id
        assert activation.invite_token_hash is not None
        assert activation.invite_token_expires_at is not None
        assert activation.account_activation_code_hash is None
        assert activation.account_activation_code_expires_at is None
        assert activation.invite_token_expires_at > datetime.now(timezone.utc)

    async def test_create_pending_email_table_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, system_admin.id, valid_create_user_request_admin
        )

        pending_email = await PendingEmailRepository.get_pending_email_by_triggered_by(
            test_db, system_admin.id
        )

        email = pending_email[0]

        assert len(pending_email) == 1
        assert email.recipient == user.email
        assert email.subject is not None
        assert email.html_body is not None
        assert email.text_body is not None
        assert email.email_type == EmailType.invite
        assert email.triggered_by == system_admin.id
        assert email.recipient_user_id == user.id

    async def test_create_user_successfully(
        self,
        test_db: AsyncSession,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        user = await UserServiceAdmin.create_account_admin(
            test_db, system_admin.id, valid_create_user_request_admin
        )

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is None
        assert user.created_by == system_admin.id


class TestGetUsersAdmin:
    async def test_returns_empty_when_no_users(self, test_db: AsyncSession):
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert result.items == []
        assert result.total == 0
        assert result.has_more is False

    async def test_excludes_system_admin_from_results(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_member(test_db)

        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        returned_ids = [user.id for user in result.items]

        assert system_admin.id not in returned_ids

    async def test_returns_all_non_system_admin_users(
        self, test_db: AsyncSession, system_admin: User
    ):
        member = await make_member(test_db)
        library_admin = await make_library_admin(test_db)
        receptionist = await make_receptionist(test_db)

        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        returned_ids = [user.id for user in result.items]

        assert member.id in returned_ids
        assert library_admin.id in returned_ids
        assert receptionist.id in returned_ids
        assert system_admin.id not in returned_ids

    async def test_has_more_is_true_when_results_exceed_page(
        self, test_db: AsyncSession
    ):
        await make_member(test_db)
        await make_member(
            test_db,
            email="second@gmail.com",
            phone_number="+15550000002",
        )
        await make_member(
            test_db,
            email="third@gmail.com",
            phone_number="+15550000003",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=2,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert result.has_more is True
        assert len(result.items) == 2

    async def test_has_more_is_false_when_results_fit_in_page(
        self, test_db: AsyncSession
    ):
        await make_member(test_db)
        await make_member(
            test_db,
            email="second@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=BookSortField.created_at,
            order=OrderBy.desc,
        )
        
        assert result.total == 2
        assert result.has_more is False

    async def test_skip_and_limit_return_correct_slice(self, test_db: AsyncSession):
        await make_member(test_db)
        await make_member(
            test_db,
            email="second@gmail.com",
            phone_number="+15550000002",
        )
        await make_member(
            test_db,
            email="third@gmail.com",
            phone_number="+15550000003",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=1,
            limit=1,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert len(result.items) == 1
        assert result.total == 3

    async def test_filter_by_email(self, test_db: AsyncSession):
        target = await make_member(
            test_db,
            email="target@gmail.com",
        )
        await make_member(
            test_db,
            email="other@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(email="target")

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert len(result.items) == 1
        assert result.items[0].id == target.id

    async def test_filter_by_first_name(self, test_db: AsyncSession):
        target = await make_member(
            test_db,
            first_name="Unique",
        )
        await make_member(
            test_db,
            first_name="Other",
            email="other@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(first_name="Unique")

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert len(result.items) == 1
        assert result.items[0].id == target.id

    async def test_filter_by_last_name(self, test_db: AsyncSession):
        target = await make_member(
            test_db,
            last_name="Targetlast",
        )
        await make_member(
            test_db,
            last_name="Otherlast",
            email="other@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(last_name="Targetlast")

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert len(result.items) == 1
        assert result.items[0].id == target.id

    async def test_filter_by_phone_number(self, test_db: AsyncSession):
        target = await make_member(
            test_db,
            phone_number="+15550000099",
        )
        await make_member(
            test_db,
            email="other@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(phone_number="+15550000099")

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        assert len(result.items) == 1
        assert result.items[0].id == target.id

    async def test_filter_by_role(self, test_db: AsyncSession):
        member = await make_member(test_db)
        await make_library_admin(test_db)

        filters = SearchUserAdmin(role=UserRole.member)

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        returned_ids = [user.id for user in result.items]

        assert member.id in returned_ids
        assert all(user.role == UserRole.member for user in result.items)

    async def test_filter_by_is_active_true(self, test_db: AsyncSession):
        active_user = await make_member(
            test_db,
            is_active=True,
        )
        await make_member(
            test_db,
            is_active=False,
            email="inactive@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(is_active=True)

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        returned_ids = [user.id for user in result.items]

        assert active_user.id in returned_ids
        assert all(user.is_active is True for user in result.items)

    async def test_filter_by_is_active_false(self, test_db: AsyncSession):
        await make_member(
            test_db,
            is_active=True,
        )
        inactive_user = await make_member(
            test_db,
            is_active=False,
            email="inactive@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin(is_active=False)

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
        )

        returned_ids = [user.id for user in result.items]

        assert inactive_user.id in returned_ids
        assert all(user.is_active is False for user in result.items)

    async def test_sort_by_first_name_asc(self, test_db: AsyncSession):
        await make_member(
            test_db,
            first_name="Charlie",
        )
        await make_member(
            test_db,
            first_name="Alice",
            email="alice@gmail.com",
            phone_number="+15550000002",
        )
        await make_member(
            test_db,
            first_name="Bob",
            email="bob@gmail.com",
            phone_number="+15550000003",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.first_name,
            order=OrderBy.asc,
        )

        first_names = [user.first_name for user in result.items]

        assert first_names == sorted(first_names)

    async def test_sort_by_first_name_desc(self, test_db: AsyncSession):
        await make_member(
            test_db,
            first_name="Charlie",
        )
        await make_member(
            test_db,
            first_name="Alice",
            email="alice@gmail.com",
            phone_number="+15550000002",
        )
        await make_member(
            test_db,
            first_name="Bob",
            email="bob@gmail.com",
            phone_number="+15550000003",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by=UserSortField.first_name,
            order=OrderBy.desc,
        )

        first_names = [user.first_name for user in result.items]

        assert first_names == sorted(first_names, reverse=True)

    async def test_invalid_sort_field_falls_back_to_created_at(
        self, test_db: AsyncSession
    ):
        await make_member(test_db)
        await make_member(
            test_db,
            email="second@gmail.com",
            phone_number="+15550000002",
        )
        filters = SearchUserAdmin()

        result = await UserServiceAdmin.get_users_admin(
            test_db,
            skip=0,
            limit=10,
            filters=filters,
            sort_by="invalid_field",
            order=OrderBy.desc,
        )

        assert result.total == 2


class TestGetUserByIDAdmin:
    async def test_get_user_by_id_admin_raises_not_found(self, test_db: AsyncSession):
        user = await make_user(test_db)
        non_existent_id = user.id + 9999999

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.get_user_by_id_admin(test_db, non_existent_id)

    async def test_get_user_by_id_admin_returns_correct_data(
        self, test_db: AsyncSession
    ):
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

        mock_set_cache = mocker.patch("src.users.service.set_cache")

        await UserServiceAdmin.get_user_by_id_admin(test_db, user.id)

        mock_set_cache.assert_called_once_with(
            UserCacheKey.user_detail_key_admin(user.id),
            mocker.ANY,
            900,
        )

    async def test_get_user_by_id_admin_returns_cached_data(
        self, test_db: AsyncSession
    ):
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
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.deactivate_user_admin(
                test_db, system_admin.id, non_existant_id
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
                test_db, system_admin.id, user.id
            )

    async def test_deactivate_active_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)

        await UserServiceAdmin.deactivate_user_admin(test_db, system_admin.id, user.id)

        await test_db.refresh(user)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session.session

        assert user.is_active is False
        assert session.refresh_token_hash is None
        assert session.refresh_token_family is None
        assert session.refresh_token_expires_at is None

    async def test_increment_access_token_version_on_deactivation(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session.session

        original_version = session.access_token_version

        await UserServiceAdmin.deactivate_user_admin(test_db, system_admin.id, user.id)

        user_session_updated = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session_updated.session

        assert session.access_token_version == original_version + 1


class TestActivateUserAdmin:
    async def test_does_not_activate_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.activate_user_admin(
                test_db, system_admin.id, non_existant_id
            )

    async def test_does_not_activate_already_active_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=True,
        )

        with pytest.raises(UserAlreadyActiveError):
            await UserServiceAdmin.activate_user_admin(
                test_db, system_admin.id, user.id
            )

    async def test_activate_inactive_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=False,
        )

        await UserServiceAdmin.activate_user_admin(test_db, system_admin.id, user.id)

        await test_db.refresh(user)

        assert user.is_active is True


class TestUpdateUserAdmin:
    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        update_request = UpdateUser(
            email="user_email@gmail.com",
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user(
                test_db, system_admin.id, non_existant_id, update_request
            )

    @pytest.mark.parametrize(
        (
            "existing_user_data",
            "user_to_be_updated_data",
            "request_override",
            "expected_exception",
        ),
        [
            (
                {"username": "taken_username"},
                {"username": "other_username"},
                {"username": "taken_username"},
                UsernameAlreadyTakenError,
            ),
            (
                {"phone_number": "+992 000 000 000"},
                {"phone_number": "+992 111 111 111"},
                {"phone_number": "+992 000 000 000"},
                PhonenumberAlreadyTakenError,
            ),
        ],
    )
    async def test_reject_duplicate_fields(
        self,
        test_db: AsyncSession,
        system_admin: User,
        existing_user_data: dict,
        user_to_be_updated_data: dict,
        request_override: dict,
        expected_exception,
    ):
        await make_member(
            test_db,
            **existing_user_data,
        )

        user_to_be_updated = await make_member(
            test_db,
            **user_to_be_updated_data,
        )

        update_request = UpdateUser()

        for field, value in request_override.items():
            setattr(update_request, field, value)

        with pytest.raises(expected_exception):
            await UserServiceAdmin.update_user(
                test_db, system_admin.id, user_to_be_updated.id, update_request
            )

    async def test_update_user_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_library_admin(test_db)

        update_request = UpdateUser(
            first_name="User_name",
            last_name="User_surname",
        )

        await UserServiceAdmin.update_user(
            test_db, system_admin.id, user.id, update_request
        )

        await test_db.refresh(user)

        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"


class TestUpdateUserPasswordAdmin:
    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        update_request = UpdateUserPasswordAdmin(
            new_password=NEW_PASSWORD,
        )

        with pytest.raises(UserNotFoundError):
            await UserServiceAdmin.update_user_password_admin(
                test_db, system_admin.id, non_existant_id, update_request
            )

    async def test_update_password_and_invalidates_tokens(self, test_db, system_admin):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session.session

        session.refresh_token_hash = "some_token"
        session.refresh_token_family = "some_family"
        session.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=1
        )
        original_version = session.access_token_version
        old_password_hash = user.password_hash

        await test_db.commit()

        update_request = UpdateUserPasswordAdmin(
            new_password=NEW_PASSWORD,
        )

        await UserServiceAdmin.update_user_password_admin(
            test_db, system_admin.id, user.id, update_request
        )

        await test_db.refresh(user)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_session.session

        assert old_password_hash != user.password_hash
        assert session.access_token_version == original_version + 1
        assert session.refresh_token_hash is None
        assert session.refresh_token_family is None
        assert session.refresh_token_expires_at is None
