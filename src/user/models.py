from datetime import date, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils.model_constants import (
    created_at_constant,
    int_pk,
    str30_ix_non_null,
    updated_at_constant,
)


class UserRole(str, Enum):
    system_admin = "system_admin"
    library_admin = "library_admin"
    receptionist = "receptionist"
    member = "member"
    guest = "guest"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int_pk]

    username: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    first_name: Mapped[str30_ix_non_null]
    last_name: Mapped[str30_ix_non_null]

    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, default=UserRole.guest)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    invite_token_hash: Mapped[str | None] = mapped_column(nullable=True)
    invite_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account_activation_code_hash: Mapped[str | None] = mapped_column(nullable=True)
    account_activation_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    access_token_version: Mapped[int] = mapped_column(nullable=False, default=1)

    refresh_token_hash: Mapped[str | None] = mapped_column(nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_token_family: Mapped[str | None] = mapped_column(String(64), nullable=True)

    failed_login_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[created_at_constant]
    updated_at: Mapped[updated_at_constant]

    creator: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys="[User.created_by]",
        back_populates="created_users"
    )

    created_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="[User.created_by]",
        back_populates="creator"
    )

    created_books: Mapped[list["Book"]] = relationship(
        "Book", 
        back_populates="book_creator",
    )

    loaned_records: Mapped[list["Loan"]] = relationship(
        "Loan", 
        foreign_keys="[Loan.user_id]", 
        back_populates="user",
    )

    loan_creator: Mapped[list["Loan"]] = relationship(
        "Loan", 
        foreign_keys="[Loan.created_by]", 
        back_populates="creator",
    )

    inventory_records_creator: Mapped[list["Inventory"]] = relationship(
        "Inventory", 
        foreign_keys="[Inventory.added_by]", 
        back_populates="creator",
    )