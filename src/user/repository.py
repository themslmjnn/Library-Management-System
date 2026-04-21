from sqlalchemy import and_, select
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
    async def get_users_admin(db: AsyncSession) -> list[User]:
        query = select(User)

        result = await db.execute(query)

        return result.scalars().all()
    
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