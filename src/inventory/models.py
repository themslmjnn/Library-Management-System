from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.utils.model_constants import created_at_constant, int_pk, updated_at_constant


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int_pk]

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(nullable=False)

    added_at: Mapped[created_at_constant]
    updated_at: Mapped[updated_at_constant]

    book: Mapped["Book"] = relationship(
        "Book", 
        back_populates="inventory_records",
    )

    loan_records: Mapped[list["Loan"]] = relationship(
        "Loan",
        back_populates="inventory",
    )
    
    creator: Mapped["User"] = relationship(
        "User", 
        back_populates="inventory_records_creator",
    )