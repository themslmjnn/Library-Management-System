from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Loan(Base):
    __tablename__ = "loans"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id"), nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    due_at: Mapped[date] = mapped_column(nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
