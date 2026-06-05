import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import generate_email_change_code
from src.email.enums import EmailType
from src.email.repository import PendingEmailRepository
from src.users.models import User, UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import (
    CreateUserPublic,
    EmailChangeRequest,
    UpdateUser,
    UpdateUserPasswordPublic,
)
from src.users.service import UserServicePublic
from src.utils.cache_keys import SessionCacheKey, UserCacheKey
from src.utils.custom_exceptions import (
    ExpiredEmailChangeCodeError,
    IncorrectPasswordError,
    InvalidEmailChangeCodeError,
    PhonenumberAlreadyTakenError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from src.utils.response_messages import PublicMessages
from src.utils.response_schemas import MessageResponse
from tests.constants import NEW_PASSWORD, OLD_PASSWORD, WRONG_PASSWORD
from tests.factories import make_member, make_user


class TestCreateAccountPublic:
    async def test_create_user_activation_table_successfully(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
    ):
        await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        user = await UserRepositoryBase.get_user_by_email(
            test_db, valid_create_user_request_public.email
        )
        created_user = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_activation=True
        )
        activation = created_user.activation

        assert activation.id is not None
        assert activation.user_id == user.id
        assert activation.invite_token_hash is None
        assert activation.invite_token_expires_at is None
        assert activation.account_activation_code_hash is not None
        assert activation.account_activation_code_expires_at is not None

    async def test_create_user_successfully(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
    ):
        result = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        user = await UserRepositoryBase.get_user_by_email(
            test_db, valid_create_user_request_public.email
        )
        created_user = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        pending_emails = await PendingEmailRepository.get_pending(test_db)

        assert result.detail == PublicMessages.REGISTRATION
        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is not None
        assert user.created_by is None
        assert created_user.session is not None
        assert len(pending_emails) == 1
        assert pending_emails[0].email_type == EmailType.activation_with_code

    async def test_returns_same_response_for_duplicate_email(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
        mock_send_already_registered_email,
    ):
        valid_create_user_request_public.email = "user_email@gmail.com"

        response1 = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        valid_create_user_request_public.email = "user_email@gmail.com"
        valid_create_user_request_public.username = "new_username"
        valid_create_user_request_public.phone_number = "992000000000"

        response2 = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        assert response1.detail == response2.detail

    async def test_already_registered_email_is_sent_to_the_correct_email(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
        mock_send_already_registered_email,
    ):
        await make_member(
            test_db,
            email="new_user_email@gmail.com",
        )

        valid_create_user_request_public.email = "new_user_email@gmail.com"

        result = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        assert result.detail == PublicMessages.REGISTRATION
        mock_send_already_registered_email.assert_called_once_with(
            "new_user_email@gmail.com"
        )

    async def test_email_is_not_sent_for_other_integrity_errors(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
        mock_send_already_registered_email,
    ):
        await make_member(
            test_db,
            username="test_username",
        )

        valid_create_user_request_public.username = "test_username"

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServicePublic.create_account_public(
                test_db, valid_create_user_request_public
            )

        mock_send_already_registered_email.assert_not_called()


class TestGetMe:
    async def test_get_me_returns_correct_data(self, test_db: AsyncSession):
        user = await make_member(test_db)

        result = await UserServicePublic.get_me(test_db, user.id)

        assert result["id"] is not None
        assert result["username"] is not None
        assert result["first_name"] == "test_fname"
        assert result["last_name"] == "test_lname"
        assert result["date_of_birth"] == "2000-01-01"

    async def test_get_me_populates_cache_after_db_hit(
        self, test_db: AsyncSession, mock_set_cache_users, mocker
    ):
        user = await make_member(test_db)

        await UserServicePublic.get_me(test_db, user.id)

        mock_set_cache_users.assert_called_once_with(
            UserCacheKey.user_detail_key_self(user.id),
            mocker.ANY,
            900,
        )

    async def test_request_doesnot_hit_db_on_second_call(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        await UserServicePublic.get_me(test_db, user.id)

        mock_get_me = mocker.patch.object(UserRepositoryBase, "get_user_by_id")

        await UserServicePublic.get_me(test_db, user.id)

        mock_get_me.assert_not_called()


class TestUpdateMe:
    async def test_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        update_request = UpdateUser(
            username="username_test",
            first_name="User_name",
            last_name="User_surname",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, user.id, update_request)

        await test_db.refresh(user)

        assert user.username == "username_test"
        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"
        assert user.phone_number == "+992 101 101 101"

    async def test_partially_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        update_request = UpdateUser(
            username="username_test",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, user.id, update_request)

        await test_db.refresh(user)

        assert user.username == "username_test"
        assert user.phone_number == "+992 101 101 101"

    async def test_cache_is_invalidated_after_update(
        self, test_db: AsyncSession, mock_delete_cache_users
    ):
        user = await make_member(test_db)

        await UserServicePublic.update_me(test_db, user.id, UpdateUser())

        assert mock_delete_cache_users.call_count == 1
        mock_delete_cache_users.assert_called_once_with(
            UserCacheKey.user_detail_key_admin(user.id),
            UserCacheKey.user_detail_key_staff(user.id),
            UserCacheKey.user_detail_key_self(user.id),
        )

    async def test_raise_404_for_unknown_user(self, test_db: AsyncSession):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServicePublic.update_me(test_db, non_existant_id, UpdateUser())

    @pytest.mark.parametrize(
        ("existing_user_data", "request_override", "expected_exception"),
        [
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
    async def test_reject_duplicate_values(
        self,
        test_db: AsyncSession,
        existing_user_data: dict,
        request_override: dict,
        expected_exception,
    ):

        await make_member(
            test_db,
            **existing_user_data,
        )

        user_to_be_updated = await make_member(test_db)

        update_request = UpdateUser()

        for field, value in request_override.items():
            setattr(update_request, field, value)

        with pytest.raises(expected_exception):
            await UserServicePublic.update_me(
                test_db, user_to_be_updated.id, update_request
            )


class TestUpdateMyPassword:
    async def test_updates_password_successfully(
        self, test_db: AsyncSession, mock_send_password_changed_confirmation
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )
        user_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_session.session

        old_password_hash = user.password_hash
        old_access_token_version = session.access_token_version

        update_request = UpdateUserPasswordPublic(
            old_password=OLD_PASSWORD,
            new_password=NEW_PASSWORD,
        )

        await UserServicePublic.update_my_password(test_db, user.id, update_request)

        await test_db.refresh(user)
        user_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_session.session

        assert old_password_hash != user.password_hash
        assert session.access_token_version == old_access_token_version + 1
        assert session.refresh_token_hash is None
        assert session.refresh_token_family is None
        assert session.refresh_token_expires_at is None

    async def test_incorrect_old_password(self, test_db: AsyncSession):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        update_request = UpdateUserPasswordPublic(
            old_password=WRONG_PASSWORD,
            new_password=NEW_PASSWORD,
        )

        with pytest.raises(IncorrectPasswordError):
            await UserServicePublic.update_my_password(test_db, user.id, update_request)

    async def test_password_change_confirmation_is_sent_correctly(
        self, test_db: AsyncSession, mock_send_password_changed_confirmation
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        update_request = UpdateUserPasswordPublic(
            old_password=OLD_PASSWORD,
            new_password=NEW_PASSWORD,
        )

        await UserServicePublic.update_my_password(test_db, user.id, update_request)

        mock_send_password_changed_confirmation.assert_called_once_with(user.email)


class TestRequestEmailChange:
    async def test_returns_message_response(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)

        result = await UserServicePublic.request_email_change(
            test_db, user.id, EmailChangeRequest(new_email="new_email@gmail.com")
        )

        assert isinstance(result, MessageResponse)
        assert result.detail == PublicMessages.EMAIL_CHANGE_REQUESTED

    async def test_pending_email_written_to_session(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)

        await UserServicePublic.request_email_change(
            test_db, user.id, EmailChangeRequest(new_email="new_email@gmail.com")
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.pending_new_email == "new_email@gmail.com"
        assert session.email_change_code_hash is not None
        assert session.email_change_code_expires_at is not None
        assert session.email_change_code_expires_at > datetime.now(timezone.utc)

    async def test_overwrites_existing_pending_change(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)

        await UserServicePublic.request_email_change(
            test_db, user.id, EmailChangeRequest(new_email="first_new_email@gmail.com")
        )

        await UserServicePublic.request_email_change(
            test_db, user.id, EmailChangeRequest(new_email="second_new_email@gmail.com")
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.pending_new_email == "second_new_email@gmail.com"

    async def test_verification_email_sent_to_new_address(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)

        await UserServicePublic.request_email_change(
            test_db,
            user.id,
            EmailChangeRequest(new_email="new_email_address@gmail.com"),
        )

        await asyncio.sleep(0)

        mock_send_email_change_verification.assert_called_once()
        assert (
            mock_send_email_change_verification.call_args.args[0]
            == "new_email_address@gmail.com"
        )

    async def test_raises_404_for_unknown_user(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)
        non_existent_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServicePublic.request_email_change(
                test_db,
                non_existent_id,
                EmailChangeRequest(new_email="new_email_address@gmail.com"),
            )

    async def test_current_email_not_changed_yet(
        self, test_db: AsyncSession, mock_send_email_change_verification
    ):
        user = await make_member(test_db)
        original_email = user.email

        await UserServicePublic.request_email_change(
            test_db,
            user.id,
            EmailChangeRequest(new_email="new_email_address@gmail.com"),
        )

        await test_db.refresh(user)

        assert user.email == original_email


class TestConfirmEmailChange:
    async def _setup_pending_change(
        self,
        test_db: AsyncSession,
        user: User,
        new_email: str = "new_email@gmail.com",
        expired: bool = False,
    ) -> str:
        raw_email_change_code, hashed_email_change_code = generate_email_change_code()

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        session.pending_new_email = new_email
        session.email_change_code_hash = hashed_email_change_code
        session.email_change_code_expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
            if expired
            else datetime.now(timezone.utc)
            + timedelta(minutes=settings.EMAIL_CHANGE_CODE_EXPIRES_MINUTES)
        )

        await test_db.commit()

        return raw_email_change_code

    async def test_email_updated_successfully(self, test_db: AsyncSession):
        user = await make_member(test_db)

        new_email = "new_email@gmail.com"
        raw_email_change_code = await self._setup_pending_change(
            test_db, user, new_email
        )

        result = await UserServicePublic.confirm_email_change(
            test_db, user.id, raw_email_change_code
        )

        await test_db.refresh(user)

        assert user.email == new_email
        assert isinstance(result, MessageResponse)
        assert result.detail == PublicMessages.EMAIL_CHANGE_CONFIRMED

    async def test_pending_email_fields_cleared_after_confirmation(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)
        raw_email_change_code = await self._setup_pending_change(test_db, user)

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        original_version = user_with_session.session.access_token_version

        await UserServicePublic.confirm_email_change(
            test_db, user.id, raw_email_change_code
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.pending_new_email is None
        assert session.email_change_code_hash is None
        assert session.email_change_code_expires_at is None
        assert session.access_token_version == original_version + 1

    async def test_refresh_token_fields_cleared_after_confirmation(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)

        raw_email_change_code = await self._setup_pending_change(test_db, user)

        await UserServicePublic.confirm_email_change(
            test_db, user.id, raw_email_change_code
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.refresh_token_hash is None
        assert session.refresh_token_family is None
        assert session.refresh_token_expires_at is None

    async def test_all_cache_keys_invalidated_after_confirmation(
        self, test_db: AsyncSession, mock_delete_cache_users
    ):
        user = await make_member(test_db)
        raw_email_change_code = await self._setup_pending_change(test_db, user)

        await UserServicePublic.confirm_email_change(
            test_db, user.id, raw_email_change_code
        )

        assert mock_delete_cache_users.call_count == 1
        mock_delete_cache_users.assert_called_once_with(
            UserCacheKey.user_detail_key_admin(user.id),
            UserCacheKey.user_detail_key_staff(user.id),
            UserCacheKey.user_detail_key_self(user.id),
            SessionCacheKey.access_token_version_key(user.id),
        )

    async def test_raises_invalid_code_error_when_no_pending_change(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)

        with pytest.raises(InvalidEmailChangeCodeError):
            await UserServicePublic.confirm_email_change(test_db, user.id, "123456")

    async def test_raises_invalid_code_error_when_code_is_wrong(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)

        await self._setup_pending_change(test_db, user)

        with pytest.raises(InvalidEmailChangeCodeError):
            await UserServicePublic.confirm_email_change(test_db, user.id, "000000")

    async def test_raises_expired_code_error_when_code_is_expired(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)

        raw_email_change_code = await self._setup_pending_change(
            test_db, user, expired=True
        )

        with pytest.raises(ExpiredEmailChangeCodeError):
            await UserServicePublic.confirm_email_change(
                test_db, user.id, raw_email_change_code
            )

    async def test_raises_404_for_unknown_user(self, test_db: AsyncSession):
        user = await make_member(test_db)
        non_existent_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServicePublic.confirm_email_change(
                test_db, non_existent_id, "123456"
            )

    async def test_email_not_changed_on_wrong_code(self, test_db: AsyncSession):
        user = await make_member(test_db)

        original_email = user.email
        await self._setup_pending_change(test_db, user)

        with pytest.raises(InvalidEmailChangeCodeError):
            await UserServicePublic.confirm_email_change(test_db, user.id, "000000")

        await test_db.refresh(user)

        assert user.email == original_email

    async def test_email_not_changed_on_expired_code(self, test_db: AsyncSession):
        user = await make_member(test_db)

        original_email = user.email
        raw_email_change_code = await self._setup_pending_change(
            test_db, user, expired=True
        )

        with pytest.raises(ExpiredEmailChangeCodeError):
            await UserServicePublic.confirm_email_change(
                test_db, user.id, raw_email_change_code
            )

        await test_db.refresh(user)

        assert user.email == original_email
