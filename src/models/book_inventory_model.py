from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column,relationship

from datetime import datetime

from db.database import Base
from src.utils.model_constants import int_pk


class BookInventory(Base):
    __tablename__ = "book_inventories"

    id: Mapped[int_pk]

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    quantity_added: Mapped[int] = mapped_column(nullable=False)

    added_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    book = relationship("Book", back_populates="inventory_records")
    creator = relationship("User", back_populates="inventory_records_creator")