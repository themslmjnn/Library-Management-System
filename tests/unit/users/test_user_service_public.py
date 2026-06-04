from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailType
from src.email.repository import PendingEmailRepository
from src.users.models import UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import CreateUserPublic, UpdateUser, UpdateUserPasswordPublic
from src.users.service import UserServicePublic
from src.utils.cache_keys import UserCacheKey
from src.utils.custom_exceptions import (
    IncorrectPasswordError,
    PhonenumberAlreadyTakenError,
    UserNotFoundError,
    UsernameAlreadyTakenError,
)
from src.utils.response_messages import PublicMessages
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
        created_user = await UserRepositoryBase.get_user_by_id(test_db, user.id, load_activation=True)
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
        created_user = await UserRepositoryBase.get_user_by_id(test_db, user.id, load_session=True)
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
        self, test_db: AsyncSession, valid_create_user_request_public: CreateUserPublic, mocker
    ):
        valid_create_user_request_public.email = "user_email@gmail.com"

        response1 = await UserServicePublic.create_account_public(test_db, valid_create_user_request_public)

        valid_create_user_request_public.email = "user_email@gmail.com"
        valid_create_user_request_public.username = "new_username"
        valid_create_user_request_public.phone_number = "992000000000"

        mocker.patch(
            "src.users.service.email_sender.send_already_registered_email",
            new_callable=AsyncMock,
        )

        response2 = await UserServicePublic.create_account_public(test_db, valid_create_user_request_public)

        assert response1.detail == response2.detail

    async def test_already_registered_email_is_sent_to_the_correct_email(
        self, test_db: AsyncSession, valid_create_user_request_public: CreateUserPublic, mocker
    ):
        await make_member(
            test_db,
            email="new_user_email@gmail.com",
        )

        mock_send = mocker.patch(
            "src.users.service.email_sender.send_already_registered_email",
            new_callable=AsyncMock,
        )

        valid_create_user_request_public.email = "new_user_email@gmail.com"

        result = await UserServicePublic.create_account_public(test_db, valid_create_user_request_public)

        assert result.detail == PublicMessages.REGISTRATION
        mock_send.assert_called_once_with("new_user_email@gmail.com")

    async def test_email_is_not_sent_for_other_integrity_errors(
        self, test_db: AsyncSession, valid_create_user_request_public: CreateUserPublic, mocker
    ):
        await make_member(
            test_db,
            username="test_username",
        )

        valid_create_user_request_public.username = "test_username"

        mock_send = mocker.patch(
            "src.users.service.email_sender.send_already_registered_email",
            new_callable=   AsyncMock,
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, valid_create_user_request_public)

        mock_send.assert_not_called()



class TestGetMe:
    async def test_get_me_returns_correct_data(self, test_db: AsyncSession, mocker):
        user = await make_member(test_db)

        result = await UserServicePublic.get_me(test_db, user.id)

        assert result.id is not None
        assert result.username is not None
        assert result.first_name == "test_fname"
        assert result.last_name == "last_lname"
        assert result.date_of_birth == date(2000, 1, 1)

        
    async def test_get_me_populates_cache_after_db_hit(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        mock_set_cache = mocker.patch("src.users.service.set_cache")

        await UserServicePublic.get_me(test_db, user.id)

        mock_set_cache.assert_called_once_with(
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
            email="new_email@gmail.com",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, user.id, update_request)

        await test_db.refresh(user)

        assert user.username == "username_test"
        assert user.email == "new_email@gmail.com"
        assert user.phone_number == "+992 101 101 101"

    async def test_cache_is_invalidated_after_update(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        mock_delete_cache = mocker.patch("src.users.service.delete_cache")

        await UserServicePublic.update_me(test_db, user.id, UpdateUser())

        assert mock_delete_cache.call_count == 1
        mock_delete_cache.assert_called_once_with(
            UserCacheKey.user_detail_key_admin(user.id),
            UserCacheKey.user_detail_key_staff(user.id),
            UserCacheKey.user_detail_key_self(user.id),
        )

    async def test_raise_404_for_unknown_user(self, test_db: AsyncSession):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        with pytest.raises(UserNotFoundError):
            await UserServicePublic.update_me(test_db, user.id, UpdateUser())

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
    async def test_reject_duplicate_values(self, test_db: AsyncSession,
        existing_user_data: dict,
        request_override: dict,
        expected_exception):

        user = await make_member(test_db, **existing_user_data)

        update_request = UpdateUser()

        for field, value in request_override.items():
            setattr(update_request, field, value)

        with pytest.raises(expected_exception):
            await UserServicePublic.update_me(
                test_db, user.id, update_request
            )

class TestUpdateMyPassword:
    async def test_updates_password_successfully(self, test_db: AsyncSession):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
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
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
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

    async def test_password_change_confirmation_is_sent_correctly(self, test_db: AsyncSession, mocker):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        update_request = UpdateUserPasswordPublic(
            old_password=WRONG_PASSWORD,
            new_password=NEW_PASSWORD,
        )

        mock_send = mocker.patch(
            "src.users.service.email_sender.send_password_changed_confirmation",
            new_callable=AsyncMock,
        )

        await UserServicePublic.update_my_password(test_db, user.id, update_request)

        mock_send.assert_called_once_with(user.email)