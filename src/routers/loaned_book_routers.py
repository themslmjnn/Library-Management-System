from fastapi import APIRouter, status, Depends

from typing import Annotated

from db.database import db_dependency
from src.core.security import user_dependency
from src.schemas.loan_book_schemas import LoanedBookResponse, LoanedBookCreate, LoanedBookSearch, ReturnLoanResponse
from src.services.loaned_book_services import LoanedBookService
from src.utils.constants import path_param_int_ge1


router = APIRouter(
    prefix="/loans",
    tags=["Loans"]
)


@router.get("", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_all_loans(
        db: db_dependency,
        current_user: user_dependency):

    return LoanedBookService.get_all_loans(db, current_user)


@router.get("/public", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_all_loans_public(
        db: db_dependency,
        current_user: user_dependency):

    return LoanedBookService.get_all_loans(db, current_user)


@router.get("/{loan_id}", response_model=LoanedBookResponse, status_code=status.HTTP_200_OK)
def get_loan_by_id_admin(
        db: db_dependency, 
        current_user: user_dependency,
        loan_id: path_param_int_ge1):

    return LoanedBookService.get_loan_by_id_admin(db, current_user, loan_id)


@router.get("/{loan_id}/public", response_model=LoanedBookResponse, status_code=status.HTTP_200_OK)
def get_loan_by_id_public(
        db: db_dependency, 
        current_user: user_dependency,
        loan_id: path_param_int_ge1):

    return LoanedBookService.get_loan_by_id_public(db, current_user, loan_id)


@router.get("/search", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def search_loans_admin(
        db: db_dependency, 
        current_user: user_dependency,
        search_request: Annotated[LoanedBookSearch, Depends()]):

    return LoanedBookService.search_loans_admin(db, current_user, search_request)


@router.get("/search/public", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def search_loans_public(
        db: db_dependency, 
        current_user: user_dependency,
        search_request: Annotated[LoanedBookSearch, Depends()]):

    return LoanedBookService.search_loans_public(db, current_user, search_request)


@router.get("/by_book_id/{book_id}", response_model=list[LoanedBookResponse], status_code=status.HTTP_200_OK)
def get_loans_by_book_id(
        db: db_dependency,
        current_user: user_dependency,
        book_id: path_param_int_ge1):
    
    return LoanedBookService.get_loans_by_book_id(db, current_user, book_id)


@router.post("/add", response_model=LoanedBookResponse, status_code=status.HTTP_201_CREATED)
def loan_book(
        db: db_dependency, 
        current_user: user_dependency,
        loan_request: LoanedBookCreate):

    return LoanedBookService.loan_book(db, current_user, loan_request)


@router.put("/{loan_id}/return", response_model=ReturnLoanResponse, status_code=status.HTTP_200_OK)
def return_loan(
        db: db_dependency, 
        current_user: user_dependency,
        loan_id: path_param_int_ge1):
    
    return LoanedBookService.return_loan(db, current_user, loan_id)