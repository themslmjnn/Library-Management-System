from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from passlib.context import CryptContext

from starlette import status
from typing import Annotated

from core.security import get_current_user
from db.database import get_db
from schemas import user_schemas
from src.schemas import book_schemas, book_inventory_schemas, loan_book_schemas
from src.services import admin_services


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

db_dependency = Annotated[Session, Depends(get_db)]

user_dependency = Annotated[dict, Depends(get_current_user)]

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

path_param_int_ge1 = Annotated[int, Path(ge=1)]



@router.get("/loaned_books", response_model=list[loan_book_schemas.LoanBookResponse], status_code=status.HTTP_200_OK)
def get_all_loaned_books(
        db: db_dependency,
        user: user_dependency):

    return admin_services.AdminLoanBookService.get_loaned_books(db, user)


@router.get("/loaned_books/by-id/{loaned_book_id}", response_model=loan_book_schemas.LoanBookResponse, status_code=status.HTTP_200_OK)
def get_loaned_book_by_id(
        db: db_dependency, 
        user: user_dependency,
        loaned_book_id: path_param_int_ge1):

    return admin_services.AdminLoanBookService.get_loaned_book_by_id(db, user, loaned_book_id)


@router.get("/search/loaned_books", response_model=list[loan_book_schemas.LoanBookResponse], status_code=status.HTTP_200_OK)
def search_loaned_books(
        db: db_dependency, 
        user: user_dependency,
        search_loaned_book_request: Annotated[loan_book_schemas.LoanBookSearch, Depends()]):

    return admin_services.AdminLoanBookService.search_loaned_books(db, user, search_loaned_book_request)


@router.get("/loaned_books/by-book/{book_id}", response_model=list[loan_book_schemas.LoanBookResponse], status_code=status.HTTP_200_OK)
def get_loaned_books_by_book_id(
        db: db_dependency,
        user: user_dependency,
        book_id: path_param_int_ge1):
    
    return admin_services.AdminLoanBookService.get_loaned_books_by_book_id(db, user, book_id)