from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from passlib.context import CryptContext

from starlette import status
from typing import Annotated

from core.security import get_current_user
from db.database import get_db
from src.schemas import auth_schemas, loan_book_schemas
from src.services import core_services


router = APIRouter(
    prefix="/core",
    tags=["Core"]
)

db_dependency = Annotated[Session, Depends(get_db)]

user_dependency = Annotated[dict, Depends(get_current_user)]

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

path_param_int_ge1 = Annotated[int, Path(ge=1)]


@router.post("/users_registration_public", response_model=auth_schemas.UserResponse, status_code=status.HTTP_200_OK)
def register_user_public(
        db: db_dependency,
        user_request: auth_schemas.UserCreatePublic):
    
    return core_services.CoreService.register_user_public(db, user_request, bcrypt_context)


@router.get("/users/{user_id}", response_model=auth_schemas.UserResponse, status_code=status.HTTP_200_OK)
def get_user_by_id(
        db: db_dependency, 
        user: user_dependency,
        user_id: path_param_int_ge1):

    return core_services.CoreService.get_user_by_id(db, user, user_id)


@router.put("/users_account_deletion/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_id(
        db: db_dependency, 
        user: user_dependency,
        user_id: path_param_int_ge1):

    core_services.CoreService.delete_user_by_id(db, user, user_id)


@router.put("/update_users_info/{user_id}", response_model=auth_schemas.UserResponse, status_code=status.HTTP_200_OK)
def update_user_info_by_user_id(
        db: db_dependency, 
        user: user_dependency,
        user_request: auth_schemas.UserUpdate, 
        user_id: path_param_int_ge1):

    return core_services.CoreService.update_user_info_by_user_id(db, user, user_request, user_id)


@router.put("/update_users_password/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_user_password_by_user_id(
        db: db_dependency, 
        user: user_dependency,
        user_password_request: auth_schemas.UserUpdatePassword, 
        user_id: path_param_int_ge1):

    core_services.CoreService.update_user_password_by_user_id(db, user, user_password_request, user_id, bcrypt_context)


@router.post("/loaning_books", response_model=loan_book_schemas.LoanBookResponse, status_code=status.HTTP_201_CREATED)
def loan_book(
        db: db_dependency, 
        user: user_dependency,
        loan_book_request: loan_book_schemas.LoanBookCreate):

    return core_services.CoreService.loan_book(db, user, loan_book_request)


@router.get("/loaned_books/{user_id}", response_model=list[loan_book_schemas.LoanBookResponse], status_code=status.HTTP_200_OK)
def get_loaned_books_by_user_id(
        db: db_dependency,
        user: user_dependency,
        user_id: path_param_int_ge1):
    
    return core_services.CoreService.get_loaned_books_by_user_id(db, user, user_id)


@router.put("/users/{user_id}/returning_loans/{loan_id}", response_model=loan_book_schemas.ReturnLoanResponse, status_code=status.HTTP_200_OK)
def return_loan(
        db: db_dependency, 
        user: user_dependency,
        loan_id: path_param_int_ge1,
        user_id: path_param_int_ge1):
    
    return core_services.CoreService.return_loan(db, user, user_id, loan_id)