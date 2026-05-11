from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Inventory(Base):
    __tablename__ = "inventories"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    book: Mapped["Book"] = relationship(
        "Book", 
        back_populates="inventory_records",
    )
    
    creator: Mapped["User"] = relationship(
        "User", 
        back_populates="inventory_records_creator",
    )