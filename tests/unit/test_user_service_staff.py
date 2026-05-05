import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import UserRole, User
from src.user.service import UserServiceStaff
from tests.factories import make_library_admin, make_member, make_receptionist, make_system_admin
from src.utils.exceptions import UserNotFoundError


class TestGetUsersStaff:
    async def test_library_admin_get_users_returns_valid_info(self, test_db: AsyncSession):
        user = await make_library_admin(test_db)

        result = await UserServiceStaff.get_users_staff(test_db, skip=0, limit=20, filters=None, current_user=user, sort_by="created_at", order="desc")

        system_admin_true = any(i.role == UserRole.system_admin for i in result.items)
        library_admin_true = any(i.role == UserRole.library_admin for i in result.items)

        assert not system_admin_true
        assert not library_admin_true
        assert all(
            i.role in (UserRole.receptionist, UserRole.member, UserRole.guest) 
            for i in result.items
        )


    async def test_receptionist_get_users_returns_valid_info(self, test_db: AsyncSession):
        user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_users_staff(test_db, skip=0, limit=20, filters=None, current_user=user, sort_by="created_at", order="desc")

        system_admin_true = any(i.role == UserRole.system_admin for i in result.items)
        library_admin_true = any(i.role == UserRole.library_admin for i in result.items)
        receptionist_true = any(i.role == UserRole.receptionist for i in result.items)


        assert not system_admin_true
        assert not library_admin_true
        assert not receptionist_true
        assert all(
            i.role in (UserRole.member, UserRole.guest) 
            for i in result.items
        )


class TestGetUserByIDStaff:
    async def test_library_admin_get_user_by_id_user_not_found(self, test_db: AsyncSession, library_admin: User):
        user1 = await make_library_admin(test_db)
        user2 = await make_system_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user1.id, library_admin)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user2.id, library_admin)


    async def test_library_admin_get_user_by_id_returns_valid_info(self, test_db: AsyncSession, library_admin: User):
        user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(test_db, user.id, library_admin)

        assert result["role"] == UserRole.receptionist

    async def test_receptionist_get_user_by_id_user_not_found(self, test_db: AsyncSession, receptionist: User):
        user1 = await make_receptionist(test_db)
        user2 = await make_library_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user1.id, receptionist)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, user2.id, receptionist)


    async def test_receptionist_get_user_by_id_returns_valid_info(self, test_db: AsyncSession, receptionist: User):
        user = await make_member(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(test_db, user.id, receptionist)

        assert result["role"] == UserRole.member
