from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import datetime, date

from db.database import Base
from src.utils.model_constants import int_pk


class LoanedBook(Base):
    __tablename__ = "loaned_books"

    id: Mapped[int_pk]

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_at: Mapped[date] = mapped_column(nullable=False)
    returned_at: Mapped[datetime | None]

    loaned_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    book = relationship("Book", back_populates="loaned_records")
    user = relationship("User", foreign_keys=[user_id], back_populates="loaned_records")
    creator = relationship("User", foreign_keys=[created_by], back_populates="loaned_book_creator")
