from fastapi import APIRouter, Depends, HTTPException, Path, Query

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import Annotated, Optional
from starlette import status
from datetime import date

from db.database import get_db
from src.schemas.book_schemas import BookCreatePublic, BookResponse, BookUpdate, BookSearch
from src.services.book_services import BookService


router = APIRouter(
    prefix="/books",
    tags=["Books"]
)

db_dependency = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[BookResponse], status_code=status.HTTP_200_OK)
def get_all_books(db: db_dependency): 
    return BookService.get_all_books(db)


@router.get("/search", response_model=list[BookResponse], status_code=status.HTTP_200_OK)
def search_books(
    db: db_dependency, 
    search_book: Annotated[BookSearch, Depends()]
):

    return BookService.search_book(db, search_book)


@router.get("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
def get_book_by_id(db: db_dependency, book_id: Annotated[int, Path(ge=1)]):
    return BookService.get_book_by_id(db, book_id)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_books_by_id(db: db_dependency, book_id: Annotated[int, Path(ge=1)]):
    BookService.delete_book_by_id(db, book_id)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def add_book(db: db_dependency, book_request: BookCreatePublic):
    return BookService.add_book(db, book_request)
    

@router.put("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
def update_books(db: db_dependency, book_request: BookUpdate, book_id: int = Path(ge=1)):
    return BookService.update_book_by_id(db, book_request, book_id)