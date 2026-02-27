from sqlalchemy import UniqueConstraint, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum
from typing import Annotated
from datetime import datetime, date

from db.database import Base


int_pk = Annotated[int, mapped_column(primary_key=True)]


class Category(str, Enum):
    self_improvement = "self improvement"
    fiction = "fiction"
    stories = "stories"
    history = "history"
    science = "science"
    others = "others"

class Book(Base):
    __tablename__ = "books"

    id: Mapped[int_pk]
    title: Mapped[str]
    author: Mapped[str]
    category: Mapped[Category] = mapped_column(SQLEnum(Category))
    description: Mapped[str | None]
    rating: Mapped[float | None]
    publishing_date: Mapped[date | None]

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="created_books")
    inventory_records = relationship("BookInventory", back_populates="book")
    loaned_records = relationship("LoanedBook", back_populates="book")

    __table_args__ = (
        UniqueConstraint('title', 'author', name="uix_title_author"),
    )
