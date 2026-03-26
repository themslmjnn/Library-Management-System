from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.models.book_model import Book
from src.repositories.book_repositories import BookRepository
from src.utils.helpers import require_admin_or_member, require_admin, ensure_exists, update_object
from src.utils.constants import MESSAGE_409_DUPLICATE


class BookService:
    @staticmethod
    def add_book(db, current_user, book_request):
        require_admin_or_member(current_user)

        new_book = Book(**book_request.model_dump(), created_by=current_user["id"])

        try:
            BookRepository.add_book(db, new_book)

            db.commit()
            db.refresh(new_book)

            return new_book
        
        except IntegrityError:
            db.rollback()
                
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_DUPLICATE)
        

    @staticmethod
    def get_all_books(db):
        return BookRepository.get_all_books(db)
    

    @staticmethod
    def get_book_by_id(db, book_id):
        return BookRepository.get_book_by_id(db, book_id)
    

    @staticmethod
    def search_book(db, search_book_request):
        return BookRepository.search_book(db, search_book_request)
    

    @staticmethod
    def update_book_info_by_id(db, current_user, book_request, book_id):
        require_admin(current_user)

        book = BookRepository.get_book_by_id(db, book_id)

        ensure_exists(book)

        try:
            update_object(book, book_request)

            db.commit()

            return book
        
        except IntegrityError:
            db.rollback()
            
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_DUPLICATE)