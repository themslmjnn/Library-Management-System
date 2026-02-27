from sqlalchemy import Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum

from typing import Annotated
from datetime import date, datetime

from db.database import Base


int_pk = Annotated[int, mapped_column(primary_key=True, index=True)]
model_str_type = Annotated[str, mapped_column(unique=True, nullable=False)]


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int_pk]
    username: Mapped[model_str_type]
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    email_address: Mapped[model_str_type]
    hash_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int]
    created_at: Mapped[datetime]