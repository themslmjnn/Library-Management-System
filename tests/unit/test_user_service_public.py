import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import UserRole
from src.user.schemas import CreateUserPublic, UpdateUserBase, UpdateUserPasswordPublic
from src.user.service import UserServicePublic
from src.utils.exceptions import (
    EmailAlreadyTakenError,
    IncorrectPasswordError,
    PhonenumberAlreadyTakenError,
    UsernameAlreadyTakenError,
)
from tests.factories import make_member, make_user

DEFAULT_PASSWORD = "Valid123!"
OLD_PASSWORD = "OldPassword123!"
NEW_PASSWORD = "NewPassword123!"
WRONG_PASSWORD = "Wrong123!"


class TestCreateAccountPublic:    
    async def test_reject_duplicate_email(self, test_db: AsyncSession):
        await make_user(
            test_db, 
            email="taken@gmail.com",
        )

        request = CreateUserPublic(
            first_name="Test_fname",
            last_name="Test_lname",
            email="taken@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            password=DEFAULT_PASSWORD,
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)

        
    async def test_reject_duplicate_username(self, test_db: AsyncSession):
        await make_user(
            test_db, 
            username="taken_username",
        )

        request = CreateUserPublic(
            username="taken_username",
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            password=DEFAULT_PASSWORD,
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)

    
    async def test_reject_duplicate_phone_number(self, test_db: AsyncSession):
        await make_user(
            test_db, 
            phone_number="+992 000 000 000",
        )

        request = CreateUserPublic(
            first_name="Test_fname",
            last_name="Test_lname",
            email="just_email@gmail.com",
            phone_number="+992 000 000 000",
            date_of_birth="1990-01-01",
            password=DEFAULT_PASSWORD,
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)


    async def test_creates_user_successfully(self, test_db: AsyncSession):
        request = CreateUserPublic(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            password=DEFAULT_PASSWORD,
        )

        user = await UserServicePublic.create_account_public(test_db, request)

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.account_activation_code_hash is not None
        assert user.password_hash is not None


class TestUpdateMe:
    async def test_reject_duplicate_email(self, test_db: AsyncSession):
        await make_user(
            test_db,
            email="taken@gmail.com",
        )

        user_to_be_updated = await make_user(
            test_db,
            email="other@gmail.com",
        )

        update_request = UpdateUserBase(
            email="taken@gmail.com",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServicePublic.update_me(test_db, update_request, user_to_be_updated.id)


    async def test_reject_duplicate_username(self, test_db: AsyncSession):
        await make_member(
            test_db,
            username="test_user",
        )

        user_to_be_updated = await make_member(
            test_db,
            username="test_user2",
        )

        update_request = UpdateUserBase(
           username="test_user",
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServicePublic.update_me(test_db, update_request, user_to_be_updated.id)


    async def test_reject_duplicate_phone_number(self, test_db: AsyncSession):
        await make_member(
            test_db,
            phone_number="+992 000 111 222",
        )

        user_to_be_updated = await make_member(
            test_db,
            phone_number="+992 000 111 333",
        )

        update_request = UpdateUserBase(
           phone_number="+992 000 111 222",
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServicePublic.update_me(test_db, update_request, user_to_be_updated.id)


    async def test_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        update_request = UpdateUserBase(
            username="username_test",
            first_name="User_name",
            last_name="User_surname",
            email="new_email@gmail.com",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, update_request, user.id)

        await test_db.refresh(user)

        assert user.username == "username_test"
        assert user.first_name == "User_name"
        assert user.last_name == "User_surname"
        assert user.email == "new_email@gmail.com"
        assert user.phone_number == "+992 101 101 101"


    async def test_partially_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        request = UpdateUserBase(
            username="username_test",
            email="new_email@gmail.com",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, request, user.id)

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

        old_password_hash = user.password_hash
        old_access_token_version = user.access_token_version

        update_request = UpdateUserPasswordPublic(
            old_password=OLD_PASSWORD,
            new_password=NEW_PASSWORD,
        )

        await UserServicePublic.update_my_password(test_db, update_request, user.id)

        await test_db.refresh(user)

        assert old_password_hash != user.password_hash
        assert user.access_token_version == old_access_token_version + 1
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
        assert user.refresh_token_expires_at is None


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
            await UserServicePublic.update_my_password(test_db, update_request, user.id)