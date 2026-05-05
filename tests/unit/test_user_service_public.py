import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.user.service import UserServicePublic
from src.user.schemas import CreateUserPublic, UpdateUserBase, UpdateUserPasswordPublic
from src.user.models import UserRole
from tests.factories import make_user
from src.utils.exceptions import EmailAlreadyTakenError, PhonenumberAlreadyTakenError, UsernameAlreadyTakenError

class TestCreateAccountPublic:
    async def test_creates_user_successfully(self, test_db: AsyncSession):
        request = CreateUserPublic(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            password="Valid123!",
        )

        user = await UserServicePublic.create_account_public(test_db, request)

        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.account_activation_code_hash is not None
        assert user.password_hash is not None

    
    async def test_rejects_duplicate_email(self, test_db: AsyncSession):
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
            password="Valid123!",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)

        
    async def test_rejects_duplicate_username(self, test_db: AsyncSession):
        await make_user(
            test_db, 
            username="taken_username",
            email="test_email@gmail.com"
        )

        request = CreateUserPublic(
            username="taken_username",
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
            password="Valid123!",
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)

    
    async def test_rejects_duplicate_phone_number(self, test_db: AsyncSession):
        await make_user(
            test_db, 
            email="test_email@gmail.com",
            phone_number="+992 000 000 000",
        )

        request = CreateUserPublic(
            first_name="Test_fname",
            last_name="Test_lname",
            email="just_email@gmail.com",
            phone_number="+992 000 000 000",
            date_of_birth="1990-01-01",
            password="Valid123!",
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServicePublic.create_account_public(test_db, request)


class TestUpdateMe:
    async def test_updates_user_successfully(self, test_db: AsyncSession):
        user = await make_user(test_db)

        request = UpdateUserBase(
            username="username_test",
            first_name="User_name",
            last_name="User_surname",
            date_of_birth="2008-01-01",
            email="new_email@gmail.com",
            phone_number="+992 101 101 101",
        )

        await UserServicePublic.update_me(test_db, request, user.id)

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

        assert user.username == "username_test"
        assert user.email == "new_email@gmail.com"
        assert user.phone_number == "+992 101 101 101"

    
    async def test_update_email_taken(self, test_db: AsyncSession):
        await make_user(
            test_db,
            email="taken@gmail.com",
        )

        user2 = await make_user(
            test_db,
            email="other@gmail.com",
        )

        request = UpdateUserBase(
            email="taken@gmail.com",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServicePublic.update_me(test_db, request, user2.id)