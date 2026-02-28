from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from src.models import user_model, book_model, book_inventory_model, loan_book_model
from src.repositories.auth_repositories import UserRepository
from src.repositories.book_repositories import BookRepository
from src.repositories.book_inventory_repositories import BookInventoryRepository
from src.repositories.loan_book_repositories import LoanBookRepository
from core import core_methods


MESSAGE_404_1 = "User not found"
MESSAGE_404_2 = "Book not found"
MESSAGE_404_3 = "Book inventory not found"
MESSAGE_404_4 = "Loaned book not found"
MESSAGE_409 = "Duplicate values are not accepted"


class AdminAuthService:
    # Finished
    @staticmethod
    def register_user(db, user_request, bcrypt_context):
        new_user = user_model.User(\
            username=user_request.username,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            date_of_birth=user_request.date_of_birth,
            email_address=user_request.email_address,
            hash_password=bcrypt_context.hash(user_request.password),
            role=user_request.role,
            is_active=user_request.is_active
        )

        try:
            UserRepository.register_user(db, new_user)

            db.commit()
            db.refresh(new_user)
            
            return new_user
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
    
    # Finished
    @staticmethod 
    def get_all_users(db):
        return UserRepository.get_all_users(db)
    
    # Finished
    @staticmethod
    def get_user_by_id(db, user_id):
        user = UserRepository.get_user_by_id(db, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        return user
    
    @staticmethod
    def search_users(db, search_user_request):
        return UserRepository.search_users(db, search_user_request)

class AdminBookService:
    # Finished
    @staticmethod
    def add_book(db, book_request):
        new_book = book_model.Book(\
            title=book_request.title,
            author=book_request.author,
            category=book_request.category,
            description=book_request.description,
            rating=book_request.rating,
            publishing_date=book_request.publishing_date,
            created_by=book_request.created_by
        )

        try:
            BookRepository.add_book(db, new_book)

            db.commit()
            db.refresh(new_book)

            return new_book
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
    
    # Finished
    @staticmethod 
    def get_all_books(db):
        return BookRepository.get_all_books(db)
    
    # Finished
    @staticmethod
    def get_book_by_id(db, book_id):
        book = BookRepository.get_book_by_id(db, book_id)

        if book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_2)
        
        return book
    

    @staticmethod
    def search_books(db, search_book_request):
        return BookRepository.search_books(db, search_book_request)
    

class AdminBookInventoryService:
    # Finished
    @staticmethod
    def add_book_inventory(db, book_inventory_request):
        new_book_inventory = book_inventory_model.BookInventory(\
            book_id=book_inventory_request.book_id,
            added_by=book_inventory_request.added_by,
            quantity_added=book_inventory_request.quantity_added
        )

        try:
            BookInventoryRepository.add_book_inventory(db, new_book_inventory)

            db.commit()
            db.refresh(new_book_inventory)

            return new_book_inventory
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
        

    # Finished
    @staticmethod
    def get_all_book_inventory(db):
        return BookInventoryRepository.get_all_book_inventory(db)
    

    # Finished
    @staticmethod
    def get_book_inventory_by_id(db, book_inventory_id):
        book_inventory = BookInventoryRepository.get_book_inventory_by_id(db, book_inventory_id)

        if book_inventory is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_3)
        
        return book_inventory
    
    @staticmethod
    def search_book_inventory(db, search_book_inventory_request):
        return BookInventoryRepository.search_book_inventory(db, search_book_inventory_request)
    

class AdminLoanBookService:
    # Finished
    @staticmethod
    def loan_book(db, loan_book_request, created_by: int):
        new_loan = core_methods.LoanBookLogic.loan_book(db, loan_book_request, created_by)

        db.commit()
        db.refresh(new_loan)

        return new_loan
    
    # Finished
    @staticmethod
    def return_loan(db, return_loan_request):
        returned_loan = core_methods.ReturnLoanLogic.return_loan(db, return_loan_request.book_id, return_loan_request.user_id)

        db.commit()

        return returned_loan
    
    # Finished
    @staticmethod
    def get_loaned_books(db):
        return LoanBookRepository.get_loaned_books(db)
    
    # Finished
    @staticmethod
    def get_loaned_book_by_id(db, loaned_book_id):
        loaned_book = LoanBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        if loaned_book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_4)
        
        return loaned_book
    

    @staticmethod
    def search_loaned_books(db, search_loaned_book_request):
        return LoanBookRepository.search_loaned_books(db, search_loaned_book_request)