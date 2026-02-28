from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from starlette import status
from typing import Annotated

from db.database import get_db
from schemas.loan_book_schemas import BookLoaningCreate, BookLoaningResponse
from services.loane_book_services import LoaningBookService


router = APIRouter(
    prefix="/loaned_books",
    tags=["Loan books"]
)

db_dependency = Annotated[Session, Depends(get_db)]


@router.post("", response_model=BookLoaningResponse, status_code=status.HTTP_200_OK)
def loan_book(db: db_dependency, loan_request: BookLoaningCreate):
    return LoaningBookService.loan_book(db, loan_request)


@router.get("", response_model=list[BookLoaningResponse], status_code=status.HTTP_200_OK)
def get_loaned_books(db: db_dependency):
    return LoaningBookService.get_loaned_books(db)


@router.get("/{loaned_book_id}", response_model=BookLoaningResponse, status_code=status.HTTP_200_OK)
def get_loaned_book_by_id(db: db_dependency, loaned_book_id: Annotated[int, Path(ge=1)]):
    return LoaningBookService.get_loaned_book_by_id(db, loaned_book_id)


@router.delete("/{loaned_book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loaned_books_by_id(db: db_dependency, loaned_book_id: Annotated[int, Path(ge=1)]):
    LoaningBookService.delete_loaned_book_id(db, loaned_book_id)