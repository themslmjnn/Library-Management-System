from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.core.enums import OrderBy
from src.users.models import User, UserActivation, UserSession
from src.users.schemas import (
    SearchUserAdmin,
    SearchUserBase,
)
from src.utils.enums import UserRole, UserSortField

LIBRARY_ADMIN_VISIBLE_ROLES = frozenset(
    {UserRole.receptionist, UserRole.member, UserRole.guest}
)
RECEPTIONIST_VISIBLE_ROLES = frozenset({UserRole.member, UserRole.guest})


class UserRepositoryBase:
    @staticmethod
    def add_entity(
        db: AsyncSession, new_user: User | UserSession | UserActivation
    ) -> None:
        db.add(new_user)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        query = select(User).filter(User.id == user_id)

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id_with_session(
        db: AsyncSession, user_id: int
    ) -> User | None:
        query = (
            select(User).options(joinedload(User.session)).filter(User.id == user_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id_with_activation(
        db: AsyncSession, user_id: int
    ) -> User | None:
        query = (
            select(User).options(joinedload(User.activation)).filter(User.id == user_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    def apply_base_filters(
        base_query: Select, filters: SearchUserBase | SearchUserAdmin | None
    ) -> Select:
        if filters is None:
            return base_query

        if filters.first_name:
            base_query = base_query.filter(
                User.first_name.ilike(f"%{filters.first_name}%")
            )
        if filters.last_name:
            base_query = base_query.filter(
                User.last_name.ilike(f"%{filters.last_name}%")
            )
        if filters.date_of_birth:
            base_query = base_query.filter(User.date_of_birth == filters.date_of_birth)
        if filters.email:
            base_query = base_query.filter(User.email.ilike(f"%{filters.email}%"))
        if filters.phone_number:
            base_query = base_query.filter(
                User.phone_number.ilike(f"%{filters.phone_number}%")
            )

        return base_query

    @staticmethod
    def apply_sorting(base_query: Select, sort_by: str, order: str) -> Select:
        if sort_by not in UserSortField:
            sort_by = UserSortField.created_at

        sort_column = getattr(User, sort_by)

        if order == OrderBy.desc:
            return base_query.order_by(sort_column.desc())

        return base_query.order_by(sort_column.asc())

    @staticmethod
    async def paginate(
        db: AsyncSession,
        query: Select,
        skip: int,
        limit: int,
    ) -> tuple[list[User], int]:

        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )

        total = count_result.scalar_one()

        result = await db.execute(query.offset(skip).limit(limit))

        return result.scalars().all(), total


class UserRepositoryAdmin:
    @staticmethod
    def _apply_admin_filters(base_query, filters: SearchUserAdmin) -> Select:
        base_query = UserRepositoryBase.apply_base_filters(base_query, filters)

        if filters.username:
            base_query = base_query.filter(User.username.ilike(f"%{filters.username}%"))
        if filters.role:
            base_query = base_query.filter(User.role == filters.role)
        if filters.is_active is not None:
            base_query = base_query.filter(User.is_active == filters.is_active)

        return base_query

    @staticmethod
    async def get_users_admin(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserAdmin | None = None,
        sort_by: str = UserSortField.created_at,
        order: str = OrderBy.desc,
    ) -> tuple[list[User], int]:

        base_query = select(User).filter(User.role != UserRole.system_admin)

        query = UserRepositoryAdmin._apply_admin_filters(base_query, filters)

        query = UserRepositoryBase.apply_sorting(query, sort_by, order)

        return await UserRepositoryBase.paginate(
            db=db,
            query=query,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    async def get_user_by_id_admin(db: AsyncSession, user_id: int) -> User | None:
        query = select(User).filter(
            and_(
                User.role != UserRole.system_admin,
                User.id == user_id,
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id_with_session_admin(
        db: AsyncSession, user_id: int
    ) -> User | None:
        query = (
            select(User)
            .options(joinedload(User.session))
            .filter(
                and_(
                    User.role != UserRole.system_admin,
                    User.id == user_id,
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()


class UserRepositoryStaff:
    @staticmethod
    async def get_users_library_admin(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserBase | None = None,
        sort_by: str = UserSortField.created_at,
        order: str = OrderBy.desc,
    ) -> tuple[list[User], int]:

        base_query = select(User).filter(User.role.in_(LIBRARY_ADMIN_VISIBLE_ROLES))

        query = UserRepositoryBase.apply_base_filters(base_query, filters)

        query = UserRepositoryBase.apply_sorting(query, sort_by, order)

        return await UserRepositoryBase.paginate(
            db=db,
            query=query,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    async def get_user_by_id_with_session_library_admin(
        db: AsyncSession, user_id: int
    ) -> User | None:
        query = (
            select(User)
            .options(joinedload(User.session))
            .filter(
                and_(
                    User.id == user_id,
                    User.role.in_(LIBRARY_ADMIN_VISIBLE_ROLES),
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_users_receptionist(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserBase | None = None,
        sort_by: str = UserSortField.created_at,
        order: str = OrderBy.desc,
    ) -> tuple[list[User], int]:

        base_query = select(User).filter(User.role.in_(RECEPTIONIST_VISIBLE_ROLES))

        query = UserRepositoryBase.apply_base_filters(base_query, filters)

        query = UserRepositoryBase.apply_sorting(query, sort_by, order)

        return await UserRepositoryBase.paginate(
            db=db,
            query=query,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    async def get_user_by_id_receptionist(
        db: AsyncSession, user_id: int
    ) -> User | None:
        query = select(User).filter(
            and_(
                User.id == user_id,
                User.role.in_(RECEPTIONIST_VISIBLE_ROLES),
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
