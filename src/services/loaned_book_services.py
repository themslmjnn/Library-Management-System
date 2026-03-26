from datetime import datetime

from fastapi import HTTPException, status

from sqlalchemy.exc import IntegrityError

from models.loaned_book_model import LoanedBook
from repositories.book_repositories import BookRepository
from repositories.user_repositories import UserRepository
from schemas.loan_book_schemas import LoanedBookCreate
from src.repositories.loan_book_repositories import LoanedBookRepository
from src.utils.helpers import require_admin_or_member, ensure_exists, loan_book, return_loan
from src.utils.constants import MESSAGE_404_BOOK, MESSAGE_404_LOAN, MESSAGE_404_USER, MESSAGE_409_DUPLICATE


class LoanedBookService:
    @staticmethod
    def get_loaned_books(db, current_user):
        require_admin_or_member(current_user)
        
        return LoanedBookRepository.get_loaned_books(db)
    
    
    @staticmethod
    def get_loaned_book_by_id(db, current_user, loaned_book_id):
        require_admin_or_member(current_user)
        
        loaned_book = LoanedBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        ensure_exists(loaned_book, MESSAGE_404_BOOK)
        
        return loaned_book
    
    
    @staticmethod
    def search_loaned_book(db, current_user, search_loaned_book_request):
        require_admin_or_member(current_user)
        
        return LoanedBookRepository.search_loaned_book(db, search_loaned_book_request)


    @staticmethod
    def get_loaned_books_by_book_id(db, current_user, book_id):
        require_admin_or_member(current_user)
        
        loaned_books = LoanedBookRepository.get_loaned_books_by_book_id(db, book_id)

        return loaned_books
    

    @staticmethod
    def loan_book(db, current_user, loan_book_request):
        require_admin_or_member(current_user)
        
        new_loan = loan_book(db, loan_book_request, current_user["id"])

        try:
            LoanedBookRepository.loan_book(new_loan)

            db.commit()
            db.refresh(new_loan)

            return new_loan
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_DUPLICATE)
    

    @staticmethod
    def return_loan(db, current_user, loan_id):
        require_admin_or_member(current_user)
         
        returned_loan = return_loan(db, loan_id)

        db.commit()

        return returned_loan


    @staticmethod
    def get_loaned_books_by_user_id(db, current_user, user_id):
        require_admin_or_member(current_user)
        
        loaned_books = LoanedBookRepository.get_loaned_books_by_user_id(db, user_id)

        return loaned_books
    
    @staticmethod
    def loan_book(db, loan_book_request: LoanedBookCreate, created_by: int):
        new_loan_book_request = LoanedBook(
            book_id=loan_book_request.book_id,
            user_id=loan_book_request.user_id,
            created_by=created_by,
            due_at=loan_book_request.due_at
        )

        user = UserRepository.get_user_by_id(db, new_loan_book_request.user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_USER)
            
        book = BookRepository.get_book_by_id(db, new_loan_book_request.book_id)

        if book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_BOOK)
            
        quantity = BookRepository.get_quantity_added(db, new_loan_book_request.book_id) or 0
            
        book_available = quantity - LoanedBookRepository.get_not_returned_loans(db, new_loan_book_request.book_id)

        if book_available <= 0:
            raise HTTPException(status_code=404, detail="Book not available")
        
        LoanedBookRepository.loan_book(db, new_loan_book_request)

        return new_loan_book_request

    @staticmethod
    def return_loan(db, loan_id):
        loan = LoanedBookRepository.get_loaned_book_by_id(db, loan_id)

        if loan is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_LOAN)
            
        if loan.returned_at is not None:
            raise HTTPException(status_code=400, detail="Book is returned")
            
        loan.returned_at = datetime.now()

        return loan