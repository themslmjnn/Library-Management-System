from sqlalchemy import String, UniqueConstraint, ForeignKey, func
from sqlalchemy import Enum as SQLEnum

from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum
from datetime import datetime, date

from db.database import Base
from src.utils.model_constants import int_pk


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

    title: Mapped[str] = mapped_column(String(50), nullable=False)
    author: Mapped[str] = mapped_column(String(30), nullable=False)

    category: Mapped[Category] = mapped_column(SQLEnum(Category), nullable=False)
    description: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[float | None]
    publishing_date: Mapped[date | None]

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="created_books")

    inventory_records = relationship("BookInventory", back_populates="book")
    loaned_records = relationship("LoanedBook", back_populates="book")

    __table_args__ = (
        UniqueConstraint('title', 'author', name="uix_title_author"),
    )
