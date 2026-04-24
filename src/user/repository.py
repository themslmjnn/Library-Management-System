from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.schemas import SearchUserAdmin, SearchUserBase

ALLOWED_SORT_FIELDS_USER = {"created_at", "first_name", "last_name"}


class UserRepositoryBase:
    @staticmethod
    def add_user(db: AsyncSession, new_user: User) -> None:
        db.add(new_user)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(User.id == user_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
    

class UserRepositoryAdmin:
    @staticmethod
    async def get_users_admin(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserAdmin | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[User], int]:
        
        base_query = (
            select(User)
            .filter(User.role != UserRole.system_admin)
        )

        base_query = UserRepositoryAdmin._apply_admin_filters(base_query, filters)

        if sort_by not in ALLOWED_SORT_FIELDS_USER:
            sort_by = "created_at"

        sort_column = getattr(User, sort_by, User.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total

    @staticmethod
    def _apply_admin_filters(
        base_query,
        filters: SearchUserAdmin | None,
    ):
        if not filters:
            return base_query

        if filters.username:
            base_query = base_query.filter(User.username.ilike('%' + filters.username + '%'))

        if filters.first_name:
            base_query = base_query.filter(User.first_name.ilike('%' + filters.first_name + '%'))

        if filters.last_name:
            base_query = base_query.filter(User.last_name.ilike('%' + filters.last_name + '%'))

        if filters.date_of_birth:
            base_query = base_query.filter(User.date_of_birth == filters.date_of_birth)

        if filters.email:
            base_query = base_query.filter(User.email.ilike('%' + filters.email + '%'))

        if filters.phone_number:
            base_query = base_query.filter(User.phone_number.ilike('%' + filters.phone_number + '%'))

        if filters.role:
            base_query = base_query.filter(User.role == filters.role)

        if filters.is_active is not None:
            base_query = base_query.filter(User.is_active == filters.is_active)

        return base_query
    

class UserRepositoryStaff:
    @staticmethod
    async def get_users_library_admin(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchUserBase | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[User], int]:
        
        base_query = (
            select(User)
            .filter(
                User.role.not_in([UserRole.library_admin, UserRole.system_admin])
            )
        )

        if filters:
            if filters.first_name:
                base_query = base_query.filter(User.first_name.ilike('%' + filters.first_name + '%'))

            if filters.last_name:
                base_query = base_query.filter(User.last_name.ilike('%' + filters.last_name + '%'))

            if filters.date_of_birth:
                base_query = base_query.filter(User.date_of_birth == filters.date_of_birth)

            if filters.email:
                base_query = base_query.filter(User.email.ilike('%' + filters.email + '%'))

            if filters.phone_number:
                base_query = base_query.filter(User.phone_number.ilike('%' + filters.phone_number + '%'))

        if sort_by not in ALLOWED_SORT_FIELDS_USER:
            sort_by = "created_at"

        sort_column = getattr(User, sort_by, User.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total
    
    @staticmethod
    async def get_user_by_id_library_admin(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.role.not_in([UserRole.system_admin, UserRole.library_admin])
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
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[User], int]:
        
        base_query = (
            select(User)
            .filter(
                User.role.in_(UserRole.member, UserRole.guest)
            )
        )

        if filters:
            if filters.first_name:
                base_query = base_query.filter(User.first_name.ilike('%' + filters.first_name + '%'))

            if filters.last_name:
                base_query = base_query.filter(User.last_name.ilike('%' + filters.last_name + '%'))

            if filters.date_of_birth:
                base_query = base_query.filter(User.date_of_birth == filters.date_of_birth)

            if filters.email:
                base_query = base_query.filter(User.email.ilike('%' + filters.email + '%'))

            if filters.phone_number:
                base_query = base_query.filter(User.phone_number.ilike('%' + filters.phone_number + '%'))

        if sort_by not in ALLOWED_SORT_FIELDS_USER:
            sort_by = "created_at"

        sort_column = getattr(User, sort_by, User.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total


    @staticmethod
    async def get_user_by_id_receptionist(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.role.in_(UserRole.member, UserRole.guest)
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()