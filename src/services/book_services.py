from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.models.book_model import Book
from src.models.book_inventory_model import BookInventory
from src.repositories.book_repositories import BookRepository
from src.utils.helpers import require_admin_or_member, require_admin, ensure_exists, update_object
from src.utils.constants import MESSAGE_409_DUPLICATE, MESSAGE_404_INVENTORY, MESSAGE_404_BOOK
from src.utils.exceptions import check_added_by_fkey_error, check_book_id_fkey_error


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
        book = BookRepository.get_book_by_id(db, book_id)

        ensure_exists(book, MESSAGE_404_BOOK)

        return book
    

    @staticmethod
    def search_book(db, search_book_request):
        return BookRepository.search_book(db, search_book_request)
    

    @staticmethod
    def update_book_info_by_id(db, current_user, book_request, book_id):
        require_admin(current_user)

        book = BookRepository.get_book_by_id(db, book_id)

        ensure_exists(book, MESSAGE_404_BOOK)

        try:
            update_object(book, book_request)

            db.commit()

            return book
        
        except IntegrityError:
            db.rollback()
            
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_DUPLICATE)
        
    
    @staticmethod
    def add_book_inventory(db, current_user, book_inventory_request):
        require_admin_or_member(current_user)

        new_book_inventory = BookInventory(
            book_id=book_inventory_request.book_id,
            added_by=current_user["id"],
            quantity_added=book_inventory_request.quantity_added
        )

        try:
            BookRepository.add_book_inventory(db, new_book_inventory)

            db.commit()
            db.refresh(new_book_inventory)

            return new_book_inventory
        
        except IntegrityError as e:
            db.rollback()

            check_book_id_fkey_error(e)

            check_added_by_fkey_error(e)

            raise

    
    @staticmethod
    def get_all_books_inventory(db, current_user):
        require_admin_or_member(current_user)
        
        return BookRepository.get_all_book_inventory(db)
    

    @staticmethod
    def get_book_inventory_by_id(db, current_user, book_inventory_id):
        require_admin_or_member(current_user)

        book_inventory = BookRepository.get_book_inventory_by_id(db, book_inventory_id)

        ensure_exists(book_inventory, MESSAGE_404_INVENTORY)
        
        return book_inventory
    

    @staticmethod
    def search_books_inventory(db, current_user, search_book_inventory_request):
        require_admin_or_member(current_user)    

        return BookRepository.search_book_inventory(db, search_book_inventory_request)
    
    
    @staticmethod
    def update_book_inventory_quantity_by_id(db, current_user, quantity, book_inventory_id):
        require_admin(current_user)

        book_inventory = BookRepository.get_book_inventory_by_id(db, book_inventory_id)

        ensure_exists(book_inventory, MESSAGE_404_INVENTORY)
        
        book_inventory.quantity_added = quantity

        db.commit()

        return book_inventory