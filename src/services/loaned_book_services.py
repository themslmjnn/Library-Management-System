from datetime import datetime

from fastapi import HTTPException, status

from sqlalchemy.exc import IntegrityError

from models.loaned_book_model import LoanedBook
from repositories.book_repositories import BookRepository
from repositories.user_repositories import UserRepository
from src.repositories.loan_book_repositories import LoanedBookRepository
from src.utils.helpers import require_admin_or_member, ensure_exists, require_user
from src.utils.constants import MESSAGE_404_BOOK, MESSAGE_404_BOOK_NOT_AVAILABLE, MESSAGE_404_LOAN, MESSAGE_404_USER
from src.utils.constants import MESSAGE_409_DUPLICATE, MESSAGE_400_BOOK


class LoanedBookService:
    @staticmethod
    def get_all_loans(db, current_user):
        require_admin_or_member(current_user)
        
        return LoanedBookRepository.get_all_loans(db)
    

    @staticmethod
    def get_all_loans_public(db, current_user):
        loan = LoanedBookRepository.get_loans_by_user_id(db, current_user["id"])

        return loan
    
    
    @staticmethod
    def get_loan_by_id_admin(db, current_user, loan_id):
        require_admin_or_member(current_user)
        
        loan = LoanedBookRepository.get_loan_by_id(db, loan_id)

        ensure_exists(loan, MESSAGE_404_BOOK)
        
        return loan
    
    @staticmethod
    def get_loan_by_id_public(db, current_user, loan_id):
        require_user(current_user)
        
        loan = LoanedBookRepository.get_loan_by_id_public(db, loan_id, current_user["id"])

        ensure_exists(loan, MESSAGE_404_BOOK)
        
        return loan
    
    
    @staticmethod
    def search_loans_admin(db, current_user, search_request):
        require_admin_or_member(current_user)
        
        return LoanedBookRepository.search_loans_admin(db, search_request)
    

    @staticmethod
    def search_loans_public(db, current_user, search_request):
        require_user(current_user)
        
        return LoanedBookRepository.search_loans_public(db, search_request, current_user["id"])


    @staticmethod
    def get_loans_by_book_id(db, current_user, book_id):
        require_admin_or_member(current_user)
        
        loans = LoanedBookRepository.get_loans_by_book_id(db, book_id)

        return loans


    @staticmethod
    def get_loaned_books_by_user_id(db, current_user, user_id):
        require_admin_or_member(current_user)
        
        loaned_books = LoanedBookRepository.get_loaned_books_by_user_id(db, user_id)

        return loaned_books
    
    
    @staticmethod
    def loan_book(db, current_user, loan_request):
        new_loan = LoanedBook(
            book_id=loan_request.book_id,
            user_id=loan_request.user_id,
            created_by=current_user["id"],
            due_at=loan_request.due_at
        )

        user = UserRepository.get_user_by_id(db, loan_request.user_id)

        ensure_exists(user, MESSAGE_404_USER)
            
        book = BookRepository.get_book_by_id(db, new_loan.book_id)

        ensure_exists(book, MESSAGE_404_BOOK)
            
        quantity = BookRepository.get_quantity_added(db, new_loan.book_id) or 0
            
        book_available = quantity - LoanedBookRepository.get_not_returned_loans(db, new_loan.book_id)

        if book_available <= 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MESSAGE_404_BOOK_NOT_AVAILABLE)
        

        try:
            LoanedBookRepository.loan_book(db, new_loan)

            db.commit()
            db.refresh(new_loan)

            return new_loan
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_DUPLICATE)
    

    @staticmethod
    def return_loan(db, current_user, loan_id):
        require_admin_or_member(current_user)
         
        loan = LoanedBookRepository.get_loan_by_id_admin(db, loan_id)

        ensure_exists(loan, MESSAGE_404_LOAN)
            
        if loan.returned_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MESSAGE_400_BOOK)
            
        loan.returned_at = datetime.now()

        db.commit()

        return loan