from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.user.schemas import SearchUser


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
        filters: SearchUser | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[User], int]:
        base_query = select(User)

        if filters:
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

        ALLOWED_SORT_FIELDS_USER = {"created_at", "first_name", "last_name", "username", "role"}

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
    async def search_users_admin(db: AsyncSession, search_request: SearchUser) -> list[User]:
        query = select(User)

        if search_request.username:
            query = query.filter(User.username.ilike('%' + search_request.username + '%'))

        if search_request.first_name:
            query = query.filter(User.first_name.ilike('%' + search_request.first_name + '%'))

        if search_request.last_name:
            query = query.filter(User.last_name.ilike('%' + search_request.last_name + '%'))

        if search_request.date_of_birth:
            query = query.filter(User.date_of_birth == search_request.date_of_birth)

        if search_request.email:
            query = query.filter(User.email.ilike('%' + search_request.email + '%'))

        if search_request.phone_number:
            query = query.filter(User.phone_number.ilike('%' + search_request.phone_number + '%'))

        if search_request.role:
            query = query.filter(User.role == search_request.role)

        if search_request.is_active is not None:
            query = query.filter(User.is_active == search_request.is_active)

        result = await db.execute(query)

        return result.scalars().all()
    
    

class UserRepositoryStaff:
    @staticmethod
    async def get_users_library_admin(db: AsyncSession) -> list[User]:
        query = (
            select(User)
            .filter(
                User.role.in_(UserRole.receptionist, UserRole.member, UserRole.guest)
            )
        )

        result = await db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    async def search_users_library_admin(db: AsyncSession, search_request: SearchUser) -> list[User]:
        query = (
            select(User)
            .filter(
                User.role.not_in(UserRole.system_admin, UserRole.library_admin)
            )
        )

        if search_request.username:
            query = query.filter(User.username.ilike('%' + search_request.username + '%'))

        if search_request.first_name:
            query = query.filter(User.first_name.ilike('%' + search_request.first_name + '%'))

        if search_request.last_name:
            query = query.filter(User.last_name.ilike('%' + search_request.last_name + '%'))

        if search_request.date_of_birth:
            query = query.filter(User.date_of_birth == search_request.date_of_birth)

        if search_request.email:
            query = query.filter(User.email.ilike('%' + search_request.email + '%'))

        if search_request.phone_number:
            query = query.filter(User.phone_number.ilike('%' + search_request.phone_number + '%'))

        if search_request.role:
            query = query.filter(User.role == search_request.role)

        if search_request.is_active is not None:
            query = query.filter(User.is_active == search_request.is_active)

        result = await db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    async def get_user_by_id_library_admin(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.role.not_in(UserRole.system_admin, UserRole.library_admin)
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
    

    @staticmethod
    async def get_users_receptionist(db: AsyncSession) -> list[User]:
        query = (
            select(User)
            .filter(
                User.role.in_(UserRole.member, UserRole.guest)
            )
        )

        result = await db.execute(query)

        return result.scalars().all()

    @staticmethod
    async def search_users_receptionist(db: AsyncSession, search_request: SearchUser) -> list[User]:
        query = (
            select(User)
            .filter(
                User.role.not_in(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist)
            )
        )

        if search_request.username:
            query = query.filter(User.username.ilike('%' + search_request.username + '%'))

        if search_request.first_name:
            query = query.filter(User.first_name.ilike('%' + search_request.first_name + '%'))

        if search_request.last_name:
            query = query.filter(User.last_name.ilike('%' + search_request.last_name + '%'))

        if search_request.date_of_birth:
            query = query.filter(User.date_of_birth == search_request.date_of_birth)

        if search_request.email:
            query = query.filter(User.email.ilike('%' + search_request.email + '%'))

        if search_request.phone_number:
            query = query.filter(User.phone_number.ilike('%' + search_request.phone_number + '%'))

        if search_request.role:
            query = query.filter(User.role == search_request.role)

        if search_request.is_active is not None:
            query = query.filter(User.is_active == search_request.is_active)

        result = await db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    async def get_user_by_id_receptionist(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.role.not_in(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist)
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()