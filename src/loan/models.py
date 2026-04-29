from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils.model_constants import int_pk


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int_pk]

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    due_at: Mapped[date] = mapped_column(nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    loaned_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    book: Mapped["Book"] = relationship(
        "Book", 
        back_populates="loaned_records",
    )

    user: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[user_id], 
        back_populates="loaned_records",
    )

    creator = relationship(
        "User", 
        foreign_keys=[created_by], 
        back_populates="loan_creator",
    )