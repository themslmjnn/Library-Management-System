from sqlalchemy import Enum as SQLEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum

from typing import Annotated
from datetime import date, datetime

from db.database import Base


int_pk = Annotated[int, mapped_column(primary_key=True, index=True)]
str_unique = Annotated[str, mapped_column(unique=True, nullable=False)]


class UserRole(str, Enum):
    admin = "admin"
    member = "member"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int_pk]
    username: Mapped[str_unique]
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    email_address: Mapped[str_unique]
    hash_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    creator = relationship(
        "User",
        remote_side="User.id",
        back_populates="created_users"
    )

    created_users = relationship(
        "User",
        back_populates="creator"
    )

    loaned_records = relationship("LoanBook", foreign_keys="LoanBook.user_id", back_populates="user")
    loaned_book_creator = relationship("LoanBook", foreign_keys="LoanBook.created_by", back_populates="creator")

    inventory_records_creator = relationship("BookInventory", foreign_keys="BookInventory.added_by", back_populates="creator")

    created_books = relationship("Book", back_populates="user")
