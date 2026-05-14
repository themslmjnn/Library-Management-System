from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils.enums import UserRole


class User(Base):
    __tablename__ = "users"

    username: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), index=True, nullable=False)

    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), nullable=False, default=UserRole.guest
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    creator: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys="[User.created_by]",
        back_populates="created_users",
    )

    created_users: Mapped[list["User"]] = relationship(
        "User", foreign_keys="[User.created_by]", back_populates="creator"
    )


class UserSession:
    __tablename__ = "users_sessions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    access_token_version: Mapped[int] = mapped_column(nullable=False, default=1)

    refresh_token_hash: Mapped[str | None] = mapped_column(nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_token_family: Mapped[str | None] = mapped_column(String(64), nullable=True)

    failed_login_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserActivation:
    __tablename__ = "users_activation"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    invite_token_hash: Mapped[str | None] = mapped_column(nullable=True)
    invite_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    account_activation_code_hash: Mapped[str | None] = mapped_column(nullable=True)
    account_activation_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
