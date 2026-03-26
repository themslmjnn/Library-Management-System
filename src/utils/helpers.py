from datetime import datetime

from fastapi import HTTPException, status

from src.models.user_model import UserRole
from src.models.loaned_book_model import LoanedBook
from src.repositories.user_repositories import UserRepository
from src.repositories.book_repositories import BookRepository
from src.repositories.loan_book_repositories import LoanedBookRepository
from src.schemas.loan_book_schemas import LoanedBookCreate
from src.utils.constants import MESSAGE_403, MESSAGE_404_BOOK, MESSAGE_404_USER, MESSAGE_404_LOAN


def require_admin(user) -> None:
    if user["role"] != UserRole.admin:
        raise HTTPException(status_code=403, detail=MESSAGE_403)


def require_user(user, owner_id) -> None:
    if user["id"] != owner_id:
        raise HTTPException(status_code=403, detail=MESSAGE_403)


def require_admin_or_owner(user, owner_id) -> None:
    if user["role"] != UserRole.admin and user["id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403)
    

def require_admin_or_member(user) -> None:
    if user["role"] not in (UserRole.admin, UserRole.member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403)


def ensure_exists(object, message) -> None:
    if object is None or not object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
     

def update_object(instance, request) -> None:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)


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


def return_loan(db, loan_id):
    loan = LoanedBookRepository.get_loaned_book_by_id(db, loan_id)

    if loan is None:
        raise HTTPException(status_code=404, detail=MESSAGE_404_LOAN)
        
    if loan.returned_at is not None:
        raise HTTPException(status_code=400, detail="Book is returned")
        
    loan.returned_at = datetime.now()

    return loan