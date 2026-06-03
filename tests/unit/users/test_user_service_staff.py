import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import OrderBy
from src.email.repository import PendingEmailRepository
from src.users.models import User, UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import CreateUserBase
from src.users.service import UserServiceStaff
from src.utils.cache_keys import UserCacheKey
from src.utils.custom_exceptions import (
    AccessDeniedError,
    UserNotFoundError,
)
from src.utils.enums import UserSortField
from tests.factories import (
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
)


class TestCreateAccountStaff:
    async def test_create_user_successfully(
        self,
        test_db: AsyncSession,
        library_admin: User,
        valid_create_user_request_staff: CreateUserBase,
    ):
        user = await UserServiceStaff.create_account(
            test_db, library_admin.id, valid_create_user_request_staff
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )
        pending_email = await PendingEmailRepository.get_pending_email_by_triggered_by(test_db, library_admin.id)


        assert user.id is not None
        assert user.email == "test_email@gmail.com"
        assert user.role == UserRole.guest
        assert user.is_active is False
        assert user.password_hash is None
        assert user.created_by == library_admin.id
        assert user_session is not None
        assert user_activation is not None
        assert pending_email is not None
        assert len(pending_email) == 1



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
            limit=10,
            filters=None,
            current_user=library_admin,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
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
            limit=10,
            filters=None,
            current_user=receptionist,
            sort_by=UserSortField.created_at,
            order=OrderBy.desc,
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
                current_user=system_admin,
                skip=0,
                limit=10,
                filters=None,
                sort_by=UserSortField.created_at,
                order=OrderBy.desc,
            )


class TestGetUserByIDStaff:
    async def test_library_admin_can_not_view_library_and_system_admins(
        self, test_db: AsyncSession, library_admin: User
    ):
        user1 = await make_library_admin(test_db)
        user2 = await make_system_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(
                test_db, library_admin, user1.id
            )

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(
                test_db, library_admin, user2.id
            )

    async def test_get_user_by_id_staff_return_valid_info_for_library_admin(
        self, test_db: AsyncSession, library_admin: User
    ):
        user = await make_receptionist(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(
            test_db, library_admin, user.id
        )

        assert result["id"] == user.id
        assert result["role"] == UserRole.receptionist

    async def test_receptionist_can_not_view_higher_roles(
        self, test_db: AsyncSession, receptionist: User
    ):
        user1 = await make_receptionist(test_db)
        user2 = await make_library_admin(test_db)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, receptionist, user1.id)

        with pytest.raises(UserNotFoundError):
            await UserServiceStaff.get_user_by_id_staff(test_db, receptionist, user2.id)

    async def test_get_user_by_id_staff_return_valid_info_for_receptionist(
        self, test_db: AsyncSession, receptionist: User
    ):
        user = await make_member(test_db)

        result = await UserServiceStaff.get_user_by_id_staff(
            test_db, receptionist, user.id
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
                current_user=system_admin,
                user_id=non_existant_id,
            )

    async def test_get_user_by_id_staff_populates_cache_after_db_hit(
        self, test_db: AsyncSession, library_admin: User, mocker
    ):
        user = await make_member(test_db)

        mock_set_cache = mocker.patch("src.users.service.set_cache")

        await UserServiceStaff.get_user_by_id_staff(test_db, library_admin, user.id)

        mock_set_cache.assert_called_once_with(
            UserCacheKey.user_detail_key_staff(user.id),
            mocker.ANY,
            900,
        )
