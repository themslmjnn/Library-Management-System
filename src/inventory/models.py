from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Inventory(Base):
    __tablename__ = "inventories"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    added_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
    )
