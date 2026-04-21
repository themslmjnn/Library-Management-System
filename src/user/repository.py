from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User


class UserRepositoryBase:
    @staticmethod
    def add_user(db: AsyncSession, new_user: User) -> None:
        db.add(new_user)

class UserRepository:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        query = (
            select(User)
            .filter(User.id == user_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
    

