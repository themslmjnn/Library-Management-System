# Imports
from fastapi import HTTPException

from datetime import datetime

from src.models.loan_book_model import LoanBook
from src.schemas.loan_book_schemas import LoanBookCreatePublic
from src.repositories.auth_repositories import UserRepository
from src.repositories.book_repositories import BookRepository
from src.repositories.loan_book_repositories import LoanBookRepository
from src.repositories.book_inventory_repositories import BookInventoryRepository


# Constants
MESSAGE_404_1 = "User not found"
MESSAGE_404_2 = "Book not found"
MESSAGE_404_3 = "Loan not found"

MESSAGE_400 = "Loan already returned"

class LoanBookLogic:
    @staticmethod
    def loan_book(db, loan_book_request: LoanBookCreatePublic, created_by: int):
        new_loan_book_request = LoanBook(\
            book_id=loan_book_request.book_id,
            user_id=loan_book_request.user_id,
            created_by=created_by,
            due_at=loan_book_request.due_at
        )

        user = UserRepository.get_user_by_id(db, new_loan_book_request.user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        book = BookRepository.get_book_by_id(db, new_loan_book_request.book_id)

        if book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_2)
        
        book_available = BookInventoryRepository.get_quantity_added(db, new_loan_book_request.book_id) - LoanBookRepository.get_not_returned_loans(db, new_loan_book_request.book_id)

        if book_available <= 0:
            raise HTTPException(status_code=404, detail="Book not available")
        
        LoanBookRepository.loan_book(db, new_loan_book_request)

        return new_loan_book_request
    
class ReturnLoanLogic:
    @staticmethod
    def return_loan(db, book_id, user_id):
        loan = LoanBookRepository.get_loan_by_user_and_book_id(db, book_id, user_id)

        if loan is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_3)
        
        if loan.returned_at is not None:
            raise HTTPException(status_code=400, detail=MESSAGE_400)
        
        loan.returned_at = datetime.now()

        return loan