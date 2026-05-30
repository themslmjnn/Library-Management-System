import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.models import UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import CreateUserPublic, UpdateUser, UpdateUserPasswordPublic
from src.users.service import UserServicePublic
from src.utils.cache_keys import user_detail_key_self
from utils.custom_exceptions import IncorrectPasswordError
from tests.constants import NEW_PASSWORD, OLD_PASSWORD, WRONG_PASSWORD
from tests.factories import make_member, make_user


class TestCreateAccountPublic:
    async def test_create_user_activation_table_successfully(
        self,
        test_db: AsyncSession,
        valid_create_user_request_public: CreateUserPublic,
    ):
        user = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )
        activation = user_activation.activation

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
        user = await UserServicePublic.create_account_public(
            test_db, valid_create_user_request_public
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is not None
        assert user.created_by is None
        assert user_session is not None


class TestGetMe:
    async def test_get_user_by_id_staff_populates_cache_after_db_hit(
        self, test_db: AsyncSession, mocker
    ):
        user = await make_member(test_db)

        mock_set_cache = mocker.patch("src.users.service.set_cache")

        await UserServicePublic.get_me(test_db, user.id)

        mock_set_cache.assert_called_once_with(
            user_detail_key_self(user.id),
            mocker.ANY,
            900,
        )


class TestUpdateMe:
    async def test_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        update_request = UpdateUser(
            username="username_test",
            first_name="User_name",
            last_name="User_surname",
            email="new_email@gmail.com",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, user.id, update_request)

        await test_db.refresh(user)

        assert user.username == "username_test"
        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"
        assert user.email == "new_email@gmail.com"
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
