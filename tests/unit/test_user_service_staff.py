import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.schemas import CreateUserBase
from src.user.service import UserServiceStaff
from src.utils.exceptions import (
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


class TestCreateAccountStaff:
    async def test_reject_duplicate_email(self, test_db: AsyncSession, library_admin: User):
        await make_user(
            test_db, 
            email="taken@gmail.com",
        )

        update_request = CreateUserBase(
            first_name="Test_fname",
            last_name="Test_lname",
            email="taken@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
        )

        with pytest.raises(EmailAlreadyTakenError):
            await UserServiceStaff.create_account_staff(test_db, update_request, library_admin.id)

        
    async def test_reject_duplicate_username(self, test_db: AsyncSession, library_admin: User):
        await make_user(
            test_db, 
            username="taken_username",
        )

        update_request = CreateUserBase(
            username="taken_username",
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+15550000001",
            date_of_birth="1990-01-01",
        )

        with pytest.raises(UsernameAlreadyTakenError):
            await UserServiceStaff.create_account_staff(test_db, update_request, library_admin.id)

    
    async def test_reject_duplicate_phone_number(self, test_db: AsyncSession, library_admin: User):
        await make_user(
            test_db, 
            phone_number="+992 000 000 000",
        )

        update_request = CreateUserBase(
            first_name="Test_fname",
            last_name="Test_lname",
            email="test_email@gmail.com",
            phone_number="+992 000 000 000",
            date_of_birth="1990-01-01",
            role=UserRole.receptionist,
        )

        with pytest.raises(PhonenumberAlreadyTakenError):
            await UserServiceStaff.create_account_staff(test_db, update_request, library_admin.id)


class TestGetUsersStaff:
    async def test_get_users_staff_return_valid_info_for_library_admin(self, test_db: AsyncSession, library_admin: User):
        await make_system_admin(test_db)
        await make_library_admin(test_db)
        visible_user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_users_staff(
            test_db, skip=0, limit=20, filters=None,
            current_user=library_admin, sort_by="created_at", order="desc"
        )

        roles = [i.role for i in result.items]

        assert UserRole.system_admin not in roles
        assert UserRole.library_admin not in roles
        assert visible_user.id in [i.id for i in result.items]
        assert len(result.items) >= 1


    async def test_get_users_staff_return_valid_info_for_receptionist(self, test_db: AsyncSession, receptionist: User):
        await make_system_admin(test_db)
        await make_library_admin(test_db)
        await make_receptionist(test_db)
        visible_user = await make_member(test_db)

        result = await UserServiceStaff.get_users_staff(
            test_db, skip=0, limit=20, filters=None,
            current_user=receptionist, sort_by="created_at", order="desc"
        )

        roles = [i.role for i in result.items]

        assert UserRole.system_admin not in roles
        assert UserRole.library_admin not in roles
        assert UserRole.receptionist not in roles
        assert visible_user.id in [i.id for i in result.items]
        assert len(result.items) >= 1


class TestGetUserByIDStaff:
    async def test_get_user_by_id_staff_return_404_for_library_admin(self, test_db: AsyncSession, library_admin: User):
        user1 = await make_library_admin(test_db)
        user2 = await make_system_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user1.id, library_admin)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user2.id, library_admin)


    async def test_get_user_by_id_staff_return_valid_info_for_library_admin(self, test_db: AsyncSession, library_admin: User):
        user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(test_db, user.id, library_admin)

        assert result["role"] == UserRole.receptionist


    async def test_get_user_by_id_staff_return_404_for_receptionist(self, test_db: AsyncSession, receptionist: User):
        user1 = await make_receptionist(test_db)
        user2 = await make_library_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user1.id, receptionist)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user2.id, receptionist)


    async def test_get_user_by_id_staff_return_valid_info_for_receptionist(self, test_db: AsyncSession, receptionist: User):
        user = await make_member(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(test_db, user.id, receptionist)

        assert result["role"] == UserRole.member