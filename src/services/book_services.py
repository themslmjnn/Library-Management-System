from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from src.models.book_model import Book
from src.repositories.book_repositories import BookRepository


MESSAGE_404 = "Book not found"
MESSAGE_409 = "Duplicate values are not accepted"


class BookService:
    @staticmethod
    def get_all_books(db):
        return BookRepository.get_all_books(db)
    

    @staticmethod
    def get_book_by_id(db, book_id):
        book_model = BookRepository.get_book_by_id(db, book_id)

        if not book_model:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
    
        return book_model


    @staticmethod
    def add_book(db, book_request):
        new_book = Book(**book_request.model_dump())

        try:
            BookRepository.add_book(db, new_book)

            db.commit()
            db.refresh(new_book)
            
            return new_book
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
        

    @staticmethod
    def search_book(db, search_book_request):
        return BookRepository.search_book(db, search_book_request)
    
    @staticmethod
    def update_book_by_id(db, book_request, book_id):
        query_result = BookRepository.get_book_by_id(db, book_id)

        if query_result is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404)

        try:
            for field, value in book_request.model_dump(exclude_unset=True).items():
                setattr(query_result, field, value)

            db.commit()
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)

        return query_result