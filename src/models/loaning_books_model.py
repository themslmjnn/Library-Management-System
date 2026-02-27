from sqlalchemy import Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from datetime import datetime, date
from typing import Annotated

from db.database import Base
from models.user_model import UserRole


int_pk = Annotated[int, mapped_column(primary_key=True, index=True)]


class LoanedBook(Base):
    __tablename__ = "loaned_books"

    id: Mapped[int_pk]
    book_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    created_by: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    due_at: Mapped[date] = mapped_column(nullable=False)
    is_returned: Mapped[bool] = mapped_column(False)

    __table_args__ = (
        UniqueConstraint("book_id", "user_id", "created_at", name="uix_loaned_book_constraint"),
    )
