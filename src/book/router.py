from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.book.schemas import BookResponse, CreateBook, UpdateBook
from src.book.service import BookService
from src.core.dependencies import (
    BookQueryParams,
    async_db_dependency,
    require_system_admin_and_staff,
)
from src.pagination import PaginatedResponse
from src.user.models import User
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/books",
    tags=["Books"],
)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def add_book(
    db: async_db_dependency,
    book_request: CreateBook,
    current_user: Annotated[User, Depends(require_system_admin_and_staff)],
):
    return await BookService.add_book(db, book_request, current_user.id)


@router.get(
    "", response_model=PaginatedResponse[BookResponse], status_code=status.HTTP_200_OK
)
async def get_books(
    db: async_db_dependency,
    query_params: Annotated[BookQueryParams, Depends()],
):
    return await BookService.get_books(
        db,
        skip=query_params.skip,
        limit=query_params.limit,
        title=query_params.title,
        author=query_params.author,
        category=query_params.category,
        sort_by=query_params.sort_by,
        order=query_params.order,
    )


@router.get("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
async def get_book_by_id(
    db: async_db_dependency,
    book_id: path_param_int_ge1,
):
    return await BookService.get_book_by_id(db, book_id)


@router.put("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
async def update_book(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_admin_and_staff)],
    update_request: UpdateBook,
    book_id: path_param_int_ge1,
):
    return await BookService.update_book(db, current_user.id, update_request, book_id)
