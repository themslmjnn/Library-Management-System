from datetime import date

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils.enums import BookCategory


class Book(Base):
    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(50), nullable=False)
    author: Mapped[str] = mapped_column(String(30), nullable=False)

    category: Mapped[BookCategory] = mapped_column(SQLEnum(BookCategory), nullable=False, default=BookCategory.others)
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)
    publishing_date: Mapped[date | None]

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    book_creator: Mapped["User"] = relationship(
        "User", 
        back_populates="created_books",
    )

    inventory_records: Mapped[list["Inventory"]] = relationship(
        "Inventory", 
        back_populates="book",
    )

    loaned_records: Mapped[list["Loan"]] = relationship(
        "Loan", 
        back_populates="book",
    )

    __table_args__ = (
        UniqueConstraint('title', 'author', name="uix_title_author"),
    )