from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.models.book_model import Book
from src.models.book_inventory_model import BookInventory


class BookRepository:
    @staticmethod
    def get_all_books(db: Session):
        query = select(Book)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_book_by_id(db: Session, book_id: int):
        query = (
            select(Book)
            .filter(Book.id == book_id)
        )

        result = db.execute(query)

        return result.scalars().first()


    @staticmethod
    def add_item(db: Session, item_request):
        db.add(item_request)
    
    
    @staticmethod
    def search_book(db: Session, search_book_request):
        query = select(Book)

        if search_book_request.title:
            query = query.filter(Book.title.ilike('%' + search_book_request.title + '%'))

        if search_book_request.author:
            query = query.filter(Book.author.ilike('%' + search_book_request.author + '%'))

        if search_book_request.category:
            query = query.filter(Book.category == search_book_request.category)

        if search_book_request.rating is not None:
            query = query.filter(Book.rating == search_book_request.rating)

        if search_book_request.publishing_date:
            query = query.filter(Book.publishing_date == search_book_request.publishing_date)

        results = db.execute(query)

        return results.scalars().all()


    @staticmethod
    def get_all_inventories(db: Session):
        query = select(BookInventory)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_inventory_by_id(db: Session, inventory_id: int):
        query = (
            select(BookInventory)
            .filter(BookInventory.id == inventory_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    

    @staticmethod
    def search_inventories(db: Session, search_request):
        query = select(BookInventory)

        if search_request.book_id is not None:
            query = query.filter(BookInventory.book_id == search_request.book_id)

        if search_request.added_by is not None:
            query = query.filter(BookInventory.added_by == search_request.added_by)

        if search_request.quantity_added is not None:
            query = query.filter(BookInventory.quantity_added == search_request.quantity_added)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_quantity_added(db: Session, book_id: int):
        query = (
            select(func.sum(BookInventory.quantity_added))
            .select_from(BookInventory)
            .filter(BookInventory.book_id == book_id)
        )

        result = db.execute(query)

        return result.scalar()