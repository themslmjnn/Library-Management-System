from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.models.book_inventory_model import BookInventory

class BookInventoryRepository:
    @staticmethod
    def add_book_inventory(db: Session, book_inventory_request):
        db.add(book_inventory_request)

    @staticmethod
    def get_all_book_inventory(db: Session):
        query = select(BookInventory)

        result = db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    def get_book_inventory_by_id(db: Session, book_inventory_id: int):
        query = (
            select(BookInventory)
            .filter(BookInventory.id == book_inventory_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    
    @staticmethod
    def search_book_inventory(db: Session, search_book_inventory_request):
        query = select(BookInventory)

        if search_book_inventory_request.book_id is not None:
            query = query.filter(BookInventory.book_id == search_book_inventory_request.book_id)

        if search_book_inventory_request.added_by is not None:
            query = query.filter(BookInventory.added_by == search_book_inventory_request.added_by)

        if search_book_inventory_request.added_at is not None:
            query = query.filter(BookInventory.added_at == search_book_inventory_request.added_at)

        if search_book_inventory_request.quantity_added is not None:
            query = query.filter(BookInventory.quantity_added == search_book_inventory_request.quantity_added)

        result = db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    def get_quantity_added(db: Session, book_id: int):
        # query = (
        #     select(func.sum(BookInventory.quantity_added))
        #     .select_from(BookInventory)
        #     .group_by(BookInventory.book_id)
        #     .having(BookInventory.book_id == book_id)
        # )

        query = (
            select(func.sum(BookInventory.quantity_added))
            .select_from(BookInventory)
            .filter(BookInventory.book_id == book_id)
        )

        result = db.execute(query)

        return result.scalar()