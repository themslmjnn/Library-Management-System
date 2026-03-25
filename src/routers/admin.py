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


@router.post("/users_registration", response_model=user_schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user_admin(
        db: db_dependency, 
        user: user_dependency,
        user_request: user_schemas.UserCreateAdmin):

    return admin_services.AdminAuthService.register_user(db, user, user_request, bcrypt_context)


@router.get("/users", response_model=list[user_schemas.UserResponse], status_code=status.HTTP_200_OK)
def get_all_users(
        db: db_dependency,
        user: user_dependency):

    return admin_services.AdminAuthService.get_all_users(db, user)


@router.get("/search/users", response_model=list[user_schemas.UserResponse], status_code=status.HTTP_200_OK)
def search_users(
        db: db_dependency, 
        user: user_dependency,
        user_search_request: Annotated[user_schemas.UserSearch, Depends()]):

    return admin_services.AdminAuthService.search_users(db, user, user_search_request)


@router.post("/book_addition", response_model=book_schemas.BookResponse, status_code=status.HTTP_201_CREATED)
def add_book(
        db: db_dependency, 
        user: user_dependency,
        book_request: book_schemas.BookCreateAdmin):

    return admin_services.AdminBookService.add_book(db, user, book_request)


@router.get("/books", response_model=list[book_schemas.BookResponse], status_code=status.HTTP_200_OK)
def get_all_books(
        db: db_dependency,
        user: user_dependency):

    return admin_services.AdminBookService.get_all_books(db, user)


@router.get("/books/{book_id}", response_model=book_schemas.BookResponse, status_code=status.HTTP_200_OK)
def get_book_by_id(
        db: db_dependency, 
        user: user_dependency,
        book_id: path_param_int_ge1):
    
    return admin_services.AdminBookService.get_book_by_id(db, user, book_id)


@router.get("/search/books", response_model=list[book_schemas.BookResponse], status_code=status.HTTP_200_OK)
def search_books(
        db: db_dependency, 
        user: user_dependency,
        search_book_request: Annotated[book_schemas.BookSearch, Depends()]):

    return admin_services.AdminBookService.search_books(db, user, search_book_request)


@router.put("/books/update_book_info/{book_id}", response_model=book_schemas.BookResponse, status_code=status.HTTP_200_OK)
def update_book_info_by_book_id(
        db: db_dependency, 
        user: user_dependency,
        book_request: book_schemas.BookUpdate, 
        book_id: path_param_int_ge1):

    return admin_services.AdminBookService.update_book_info_by_book_id(db, user, book_request, book_id)


@router.post("/book_inventory", response_model=book_inventory_schemas.BookInventoryResponse, status_code=status.HTTP_201_CREATED)
def add_book_inventory(
        db: db_dependency, 
        user: user_dependency,
        book_inventory_request: book_inventory_schemas.BookInventoryCreate):

    return admin_services.AdminBookInventoryService.add_book_inventory(db, user, book_inventory_request)


@router.get("/books_inventory", response_model=list[book_inventory_schemas.BookInventoryResponse], status_code=status.HTTP_200_OK)
def get_all_book_inventory(
        db: db_dependency,
        user: user_dependency):

    return admin_services.AdminBookInventoryService.get_all_books_inventory(db, user)
    

@router.get("/books_inventory/{book_inventory_id}", response_model=book_inventory_schemas.BookInventoryResponse, status_code=status.HTTP_200_OK)
def get_book_inventory_by_id(
        db: db_dependency, 
        user: user_dependency,
        book_inventory_id: 
        path_param_int_ge1):

    return admin_services.AdminBookInventoryService.get_book_inventory_by_id(db, user, book_inventory_id)


@router.get("/search/books_inventory", response_model=list[book_inventory_schemas.BookInventoryResponse], status_code=status.HTTP_200_OK)
def search_books_inventory(
        db: db_dependency, 
        user: user_dependency,
        search_book_inventory_request: Annotated[book_inventory_schemas.BookInventorySearch, Depends()]):

    return admin_services.AdminBookInventoryService.search_books_inventory(db, user, search_book_inventory_request)


@router.put("/books_inventory/update_quantity_added/{book_inventory_id}", response_model=book_inventory_schemas.BookInventoryResponse, status_code=status.HTTP_200_OK)
def update_book_inventory_quantity_by_id(
        db: db_dependency, 
        user: user_dependency,
        quantity: int, 
        book_inventory_id: path_param_int_ge1):

    return admin_services.AdminBookInventoryService.update_book_inventory_quantity_by_id(db, user, quantity, book_inventory_id)


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