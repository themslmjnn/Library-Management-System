from typing import Annotated, Union

from fastapi import APIRouter, Depends, Path, status

from src.books.schemas import BookResponse, BookResponsePublic, CreateBook, UpdateBook
from src.books.service import BookService
from src.core.dependencies import (
    BookQueryParams,
    CurrentUser,
    async_db_dependency,
    require_system_admin_and_staff,
    require_system_and_library_admin,
)
from src.pagination import PaginatedResponse
from src.users.models import User

router = APIRouter(
    prefix="/books",
    tags=["Books"],
)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def add_book(
    db: async_db_dependency,
    book_request: CreateBook,
    current_user: Annotated[User, Depends(require_system_and_library_admin)],
):
    return await BookService.add_book(db, book_request, current_user.id)


@router.get(
    "", response_model=PaginatedResponse[BookResponse], status_code=status.HTTP_200_OK
)
async def get_books(
    db: async_db_dependency,
    query_params: Annotated[BookQueryParams, Depends()],
    _: Annotated[User, Depends(require_system_admin_and_staff)],
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


@router.get(
    "/public",
    response_model=PaginatedResponse[BookResponsePublic],
    status_code=status.HTTP_200_OK,
)
async def get_books_public(
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


@router.get(
    "/{book_id}",
    response_model=Union[BookResponse, dict],
    status_code=status.HTTP_200_OK,
)
async def get_book_by_id(
    db: async_db_dependency,
    book_id: Annotated[int, Path(ge=1)],
    _: Annotated[User, Depends(require_system_admin_and_staff)],
):
    return await BookService.get_book_by_id(db, book_id)


@router.get(
    "/{book_id}/public",
    response_model=Union[BookResponsePublic, dict],
    status_code=status.HTTP_200_OK,
)
async def get_book_by_id_public(
    db: async_db_dependency,
    book_id: Annotated[int, Path(ge=1)],
):
    return await BookService.get_book_by_id_public(db, book_id)


@router.patch("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
async def update_book(
    db: async_db_dependency,
    current_user: Annotated[User, Depends(require_system_and_library_admin)],
    update_request: UpdateBook,
    book_id: Annotated[int, Path(ge=1)],
):
    return await BookService.update_book(db, current_user.id, update_request, book_id)
