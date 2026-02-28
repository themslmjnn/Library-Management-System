from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from passlib.context import CryptContext

from starlette import status
from typing import Annotated

from db.database import get_db
from src.schemas import auth_schemas, book_schemas, book_inventory_schemas, loan_book_schemas
from src.services import admin_services

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

db_dependency = Annotated[Session, Depends(get_db)]

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

path_param_int_ge1 = Annotated[int, Path(ge=1)]


@router.get("/users", response_model=list[auth_schemas.UserResponse], status_code=status.HTTP_200_OK)
def get_all_users(db: db_dependency):
    return admin_services.AdminAuthService.get_all_users(db)


@router.get("/users/{user_id}", response_model=auth_schemas.UserResponse, status_code=status.HTTP_200_OK)
def get_user_by_id(db: db_dependency, user_id: path_param_int_ge1):
    return admin_services.AdminAuthService.get_user_by_id(db, user_id)


@router.get("/search/users", response_model=list[auth_schemas.UserResponse], status_code=status.HTTP_200_OK)
def search_users(db: db_dependency, user_search_request: Annotated[auth_schemas.UserSearch, Depends()]):
    return admin_services.AdminAuthService.search_users(db, user_search_request)


@router.get("/books", response_model=list[book_schemas.BookResponse], status_code=status.HTTP_200_OK)
def get_all_books(db: db_dependency):
    return admin_services.AdminBookService.get_all_books(db)


@router.get("/books/{book_id}", response_model=book_schemas.BookResponse, status_code=status.HTTP_200_OK)
def get_book_by_id(db: db_dependency, book_id: path_param_int_ge1):
    return admin_services.AdminBookService.get_book_by_id(db, book_id)


@router.get("/search/books")
def search_books(db: db_dependency, search_book_request: Annotated[book_schemas.BookSearch, Depends()]):
    return admin_services.AdminBookService.search_books(db, search_book_request)


@router.get("/loaned_books", response_model=list[loan_book_schemas.LoanBookRepsonse], status_code=status.HTTP_200_OK)
def get_all_loaned_books(db: db_dependency):
    return admin_services.AdminLoanBookService.get_loaned_books(db)


@router.get("/loaned_books/{loaned_book_id}", response_model=loan_book_schemas.LoanBookRepsonse, status_code=status.HTTP_200_OK)
def get_loaned_book_by_id(db: db_dependency, loaned_book_id: path_param_int_ge1):
    return admin_services.AdminLoanBookService.get_loaned_book_by_id(db, loaned_book_id)


@router.get("/search/loaned_books", response_model=list[loan_book_schemas.LoanBookRepsonse], status_code=status.HTTP_200_OK)
def search_loaned_books(db: db_dependency, search_loaned_book_request: Annotated[loan_book_schemas.LoanBookSearch, Depends()]):
    return admin_services.AdminLoanBookService.search_loaned_books(db, search_loaned_book_request)


@router.get("/book_inventory", response_model=list[book_inventory_schemas.BookInventoryResponse], status_code=status.HTTP_200_OK)
def get_all_book_inventory(db: db_dependency):
    return admin_services.AdminBookInventoryService.get_all_book_inventory(db)
    

@router.get("/books_inventory/{book_inventory_id}")
def get_book_inverntory_by_id(db: db_dependency, book_inventory_id: path_param_int_ge1):
    return admin_services.AdminBookInventoryService.get_book_inventory_by_id(db, book_inventory_id)


@router.get("/search/books_inventory", response_model=list[book_inventory_schemas.BookInventoryResponse], status_code=status.HTTP_200_OK)
def search_books_inventory(db: db_dependency, search_book_inventory_request: Annotated[book_inventory_schemas.BookInventorySearch, Depends()]):
    return admin_services.AdminBookInventoryService.search_book_inventory(db, search_book_inventory_request)


@router.post("/user_registration", response_model=auth_schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user_admin(db: db_dependency, user_request: auth_schemas.UserCreateAdmin):
    return admin_services.AdminAuthService.register_user(db, user_request, bcrypt_context)


@router.post("/book_addition", response_model=book_schemas.BookResponse, status_code=status.HTTP_201_CREATED)
def add_book(db: db_dependency, book_request: book_schemas.BookCreateAdmin):
    return admin_services.AdminBookService.add_book(db, book_request)


@router.post("/book_inventory", response_model=book_inventory_schemas.BookInventoryResponse, status_code=status.HTTP_201_CREATED)
def add_book_inventory(db: db_dependency, book_inventory_request: book_inventory_schemas.BookInventoryCreate):
    return admin_services.AdminBookInventoryService.add_book_inventory(db, book_inventory_request)


@router.post("/loaning_book", response_model=loan_book_schemas.LoanBookRepsonse, status_code=status.HTTP_201_CREATED)
def loan_book(db: db_dependency, loan_book_request: loan_book_schemas.LoanBookCreateAdmin):
    return admin_services.AdminLoanBookService.loan_book(db, loan_book_request, loan_book_request.created_by)


@router.put("/returning_loan", response_model=loan_book_schemas.ReturnLoanResponse, status_code=status.HTTP_200_OK)
def return_loan(db: db_dependency, return_loan_request: loan_book_schemas.ReturnLoanRequest):
    return admin_services.AdminLoanBookService.return_loan(db, return_loan_request)