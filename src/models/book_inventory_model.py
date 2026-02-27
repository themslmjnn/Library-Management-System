from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column,relationship

from typing import Annotated
from datetime import datetime

from db.database import Base


int_pk = Annotated[int, mapped_column(primary_key=True, index=True)]


class BookInventory(Base):
    __tablename__ = "book_inventory"

    id: Mapped[int_pk]

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())
    quantity_added: Mapped[int] = mapped_column(nullable=False)

    book = relationship("Book", back_populates="inventory_records")
    creator = relationship("User", back_populates="inventory_records_creator")