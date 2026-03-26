from sqlalchemy.exc import IntegrityError

from src.models.book_model import Book
from src.models.book_inventory_model import BookInventory
from src.repositories.book_repositories import BookRepository
from src.utils.helpers import require_admin_or_member, ensure_exists, update_object
from src.utils.constants import MESSAGE_404_INVENTORY, MESSAGE_404_BOOK
from src.utils.exceptions import check_added_by_fkey_error, check_book_id_fkey_error, check_unique_title_and_author


class BookService:
    @staticmethod
    def add_book(db, current_user, book_request):
        require_admin_or_member(current_user)

        new_book = Book(**book_request.model_dump(), created_by=current_user["id"])

        try:
            BookRepository.add_item(db, new_book)

            db.commit()
            db.refresh(new_book)

            return new_book
        
        except IntegrityError as error:
            db.rollback()
                
            check_unique_title_and_author(error)

            raise
        

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
    def update_book_by_id(db, current_user, update_request, book_id):
        require_admin_or_member(current_user)

        book = BookRepository.get_book_by_id(db, book_id)

        ensure_exists(book, MESSAGE_404_BOOK)

        try:
            update_object(book, update_request)

            db.commit()

            return book
        
        except IntegrityError as error:
            db.rollback()
            
            check_unique_title_and_author(error)

            raise
        
    
    @staticmethod
    def add_inventory(db, current_user, inventory_request):
        require_admin_or_member(current_user)

        new_inventory = BookInventory(
            book_id=inventory_request.book_id,
            added_by=current_user["id"],
            quantity_added=inventory_request.quantity_added
        )

        try:
            BookRepository.add_item(db, new_inventory)

            db.commit()
            db.refresh(new_inventory)

            return new_inventory
        
        except IntegrityError as e:
            db.rollback()

            check_book_id_fkey_error(e)

            check_added_by_fkey_error(e)

            raise

    
    @staticmethod
    def get_all_inventories(db, current_user):
        require_admin_or_member(current_user)
        
        return BookRepository.get_all_inventories(db)
    

    @staticmethod
    def get_inventory_by_id(db, current_user, inventory_id):
        require_admin_or_member(current_user)

        inventory = BookRepository.get_inventory_by_id(db, inventory_id)

        ensure_exists(inventory, MESSAGE_404_INVENTORY)
        
        return inventory
    

    @staticmethod
    def search_inventories(db, current_user, search_request):
        require_admin_or_member(current_user)    

        return BookRepository.search_inventories(db, search_request)
    
    
    @staticmethod
    def update_inventory_quantity_by_id(db, current_user, quantity, inventory_id):
        require_admin_or_member(current_user)

        inventory = BookRepository.get_inventory_by_id(db, inventory_id)

        ensure_exists(inventory, MESSAGE_404_INVENTORY)
        
        inventory.quantity_added = quantity

        db.commit()

        return inventory