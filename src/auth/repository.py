from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User


class AuthRepository:
    @staticmethod
    async def get_by_login_identifier(db: AsyncSession, identifier: str) -> User | None:
        query = (
            select(User)
            .filter(or_(
                User.username == identifier,
                User.phone_number == identifier,
                User.email == identifier
            ))
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()