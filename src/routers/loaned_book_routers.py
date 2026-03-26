from fastapi import APIRouter, status, Depends

from typing import Annotated

from db.database import db_dependency
from src.core.security import user_dependency
from src.schemas.loan_book_schemas import LoanedBookResponse, LoanedBookCreate, LoanedBookSearch, ReturnLoanResponse
from src.services.loaned_book_services import LoanedBookService
from src.utils.constants import path_param_int_ge1


router = APIRouter(
    prefix="/books",
    tags=["Loans"]
)


@router.get("/loaned", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_all_loaned_books(
        db: db_dependency,
        current_user: user_dependency):

    return LoanedBookService.get_loaned_books(db, current_user)


@router.get("/loaned/by-id/{loaned_book_id}", response_model=LoanedBookResponse, status_code=status.HTTP_200_OK)
def get_loaned_book_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        loaned_book_id: path_param_int_ge1):

    return LoanedBookService.get_loaned_book_by_id(db, current_user, loaned_book_id)


@router.get("/loaned/search", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def search_loaned_books(
        db: db_dependency, 
        current_user: user_dependency,
        search_loaned_book_request: Annotated[LoanedBookSearch, Depends()]):

    return LoanedBookService.search_loaned_book(db, current_user, search_loaned_book_request)


@router.get("/loaned/by_book_id/{book_id}", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_loaned_books_by_book_id(
        db: db_dependency,
        current_user: user_dependency,
        book_id: path_param_int_ge1):
    
    return LoanedBookService.get_loaned_books_by_book_id(db, current_user, book_id)


@router.post("/loan", response_model=LoanedBookResponse, status_code=status.HTTP_201_CREATED)
def loan_book(
        db: db_dependency, 
        current_user: user_dependency,
        loan_book_request: LoanedBookCreate):

    return LoanedBookService.loan_book(db, current_user, loan_book_request)


@router.get("/loaned/by_user_id/{user_id}", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_loaned_books_by_user_id(
        db: db_dependency,
        current_user: user_dependency,
        user_id: path_param_int_ge1):
    
    return LoanedBookService.get_loaned_books_by_user_id(db, current_user, user_id)


@router.put("loaned/{loan_id}/return", response_model=ReturnLoanResponse, status_code=status.HTTP_200_OK)
def return_loan(
        db: db_dependency, 
        current_user: user_dependency,
        loan_id: path_param_int_ge1,
        user_id: path_param_int_ge1):
    
    return LoanedBookService.return_loan(db, current_user, user_id, loan_id)