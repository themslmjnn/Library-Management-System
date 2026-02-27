from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import Annotated
from datetime import datetime, date

from db.database import Base


int_pk = Annotated[int, mapped_column(primary_key=True)]


class Books(Base):
    __tablename__ = "books"

    id: Mapped[int_pk]
    title: Mapped[str]
    author: Mapped[str]
    category: Mapped[str]
    description: Mapped[str]
    rating: Mapped[float]
    publishing_date: Mapped[date]
    created_at: Mapped[datetime]
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    book = relationship("Users", back_populates="books")

    __table_args__ = (
        UniqueConstraint('title', 'author', name="uix_title_author"),
    )
