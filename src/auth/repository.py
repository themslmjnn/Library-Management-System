from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.user.models import User


class AuthRepository:
    @staticmethod
    async def get_user_by_login_identifier_with_session(
        db: AsyncSession, identifier: str
    ) -> User | None:
        query = (
            select(User)
            .options(joinedload(User.session))
            .filter(
                or_(
                    User.username == identifier,
                    User.phone_number == identifier,
                    User.email == identifier,
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_login_identifier_with_activation(
        db: AsyncSession, identifier: str
    ) -> User | None:
        query = (
            select(User)
            .options(joinedload(User.activation))
            .filter(
                or_(
                    User.username == identifier,
                    User.phone_number == identifier,
                    User.email == identifier,
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
