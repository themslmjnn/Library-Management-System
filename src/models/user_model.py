from sqlalchemy import ForeignKey, func, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum

from typing import Annotated
from datetime import date, datetime

from db.database import Base
from src.utils.model_constants import int_pk, str_ix_30, str_uix_50


str_unique = Annotated[str, mapped_column(unique=True, nullable=False)]


class UserRole(str, Enum):
    admin = "admin"
    member = "member"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int_pk]

    username: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    first_name: Mapped[str_ix_30]
    last_name: Mapped[str_ix_30]

    date_of_birth: Mapped[date] = mapped_column(nullable=False)

    email_address: Mapped[str_uix_50]

    password_hash: Mapped[str] = mapped_column(nullable=False)

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), index=True, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship(
        "User",
        remote_side="User.id",
        back_populates="created_users"
    )

    created_users = relationship(
        "User",
        back_populates="creator"
    )

    loaned_records = relationship("LoanedBook", foreign_keys="LoanedBook.user_id", back_populates="user")
    loaned_book_creator = relationship("LoanedBook", foreign_keys="LoanedBook.created_by", back_populates="creator")

    inventory_records_creator = relationship("BookInventory", foreign_keys="BookInventory.added_by", back_populates="creator")

    created_books = relationship("Book", back_populates="user")
