from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.book_model import Book

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
    def add_book(db: Session, book_request):
        db.add(book_request)

        return book_request
    
    @staticmethod
    def search_books(db: Session, search_book_request):
        query = select(Book)

        if search_book_request.title:
            query = query.filter(Book.title.ilike(search_book_request.title))

        if search_book_request.author:
            query = query.filter(Book.author.ilike(search_book_request.author))

        if search_book_request.category:
            query = query.filter(Book.category.ilike(search_book_request.category))

        if search_book_request.rating is not None:
            query = query.filter(Book.rating == search_book_request.rating)

        if search_book_request.publishing_date:
            query = query.filter(Book.publishing_date == search_book_request.publishing_date)

        results = db.execute(query)

        return results.scalars().all()
