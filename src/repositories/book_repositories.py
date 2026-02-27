from sqlalchemy import select
from sqlalchemy.orm import Session

from models.book_model import Books

class BookRepository:
    @staticmethod
    def get_all_books(db: Session):
        query = select(Books)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_book_by_id(db: Session, book_id: int):
        query = (
            select(Books)
            .filter(Books.id == book_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    

    @staticmethod
    def delete_book_by_id(db: Session, book):
        db.delete(book)


    @staticmethod
    def add_book(db: Session, book_request):
        db.add(book_request)

        return book_request
    
    @staticmethod
    def search_book(db: Session, search_book_request):
        query = select(Books)

        if search_book_request.title:
            query = query.filter(Books.title.ilike(search_book_request.title))

        if search_book_request.author:
            query = query = query.filter(Books.author.ilike(search_book_request.author))

        if search_book_request.category:
            query = query = query.filter(Books.category.ilike(search_book_request.category))

        if search_book_request.rating is not None:
            query = query.filter(Books.rating == search_book_request.rating)

        if search_book_request.publishing_date:
            query = query.filter(Books.publishing_date == search_book_request.publishing_date)

        results = db.execute(query)

        return results.scalars().all()
