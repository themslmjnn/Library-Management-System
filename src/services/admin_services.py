from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from src.models import user_model, book_model, book_inventory_model
from repositories.user_repositories import UserRepository
from src.repositories.book_repositories import BookRepository
from src.repositories.book_inventory_repositories import BookInventoryRepository
from src.repositories.loan_book_repositories import LoanBookRepository


MESSAGE_403 = "Accessing denied"
MESSAGE_404_1 = "User not found"
MESSAGE_404_2 = "Book not found"
MESSAGE_404_3 = "Book inventory not found"
MESSAGE_404_4 = "Loaned book not found"
MESSAGE_409 = "Duplicate values are not accepted"



class AdminBookInventoryService:
    
    

class AdminLoanBookService:
    @staticmethod
    def get_loaned_books(db, user):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return LoanBookRepository.get_loaned_books(db)
    
    
    @staticmethod
    def get_loaned_book_by_id(db, user, loaned_book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        loaned_book = LoanBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        if loaned_book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_4)
        
        return loaned_book
    
    
    @staticmethod
    def search_loaned_books(db, user, search_loaned_book_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return LoanBookRepository.search_loaned_books(db, search_loaned_book_request)


    @staticmethod
    def get_loaned_books_by_book_id(db, user, book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        loaned_books = LoanBookRepository.get_loaned_books_by_book_id(db, book_id)

        return loaned_books