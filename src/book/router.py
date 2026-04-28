from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.book.schemas import BookResponse, CreateBook, SearchBook, UpdateBook
from src.book.service import BookService
from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_roles,
)
from src.pagination import PaginatedResponse
from src.user.models import User, UserRole
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/books",
    tags=["Books"]
)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def add_book(
    db: async_db_dependency,
    book_request: CreateBook,
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
):
    return await BookService.add_book(db, book_request, current_user)


@router.get("", response_model=PaginatedResponse[BookResponse], status_code=status.HTTP_200_OK)
async def get_books(
    db: async_db_dependency,
    pagination: pagination_dependency,
    filters: Annotated[SearchBook, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await BookService.get_books(
        db,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order
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
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
    update_request: UpdateBook, 
    book_id: path_param_int_ge1
):
    return await BookService.update_book(db, current_user.id, update_request, book_id)