from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.books.models import Book
from src.books.repository import BookRepository
from src.books.schemas import BookResponse, BookResponsePublic, CreateBook, UpdateBook
from src.core.cache import delete_cache, get_cache, set_cache
from src.core.enums import OrderBy
from src.core.logging import get_logger
from src.pagination import PaginatedResponse
from src.utils.cache_keys import BookCacheKey
from src.utils.custom_exceptions import BookNotFoundError, check_unique_title_and_author
from src.utils.enums import BookCategory
from src.utils.exception_constants import HTTP404
from src.utils.helpers import ensure_exists, update_object

logger = get_logger(__name__)


class BookService:
    @staticmethod
    async def add_book(
        db: AsyncSession, book_request: CreateBook, current_user_id: int
    ) -> Book:
        new_book = Book(
            **book_request.model_dump(),
            created_by=current_user_id,
        )

        try:
            BookRepository.add_book(db, new_book)

            await db.commit()
            await db.refresh(new_book)

            logger.info(
                "book_created",
                book_id=new_book.id,
                created_by=current_user_id,
            )

            return new_book
        except IntegrityError as error:
            await db.rollback()

            logger.error(
                "create_book_failed",
                requested_by=current_user_id,
                error=str(error.orig),
            )

            check_unique_title_and_author(error)
            raise

    @staticmethod
    async def get_books(
        db: AsyncSession,
        skip: int,
        limit: int,
        title: str | None,
        author: str | None,
        category: BookCategory | None,
        sort_by: str,
        order: OrderBy,
    ) -> PaginatedResponse:

        books, total = await BookRepository.get_books(
            db,
            skip=skip,
            limit=limit,
            title=title,
            author=author,
            category=category,
            sort_by=sort_by,
            order=order,
        )

        return PaginatedResponse(
            items=books,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> dict:
        key = BookCacheKey.book_detail_key(book_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached

        book = await BookRepository.get_book_by_id(db, book_id)
        ensure_exists(book, BookNotFoundError(HTTP404.BOOK))

        serialized = BookResponse.model_validate(book).model_dump(mode="json")
        await set_cache(key, serialized, 600)

        return serialized

    @staticmethod
    async def get_book_by_id_public(db: AsyncSession, book_id: int) -> dict:
        key = BookCacheKey.book_detail_key_public(book_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached

        book = await BookRepository.get_book_by_id(db, book_id)
        ensure_exists(book, BookNotFoundError(HTTP404.BOOK))

        serialized = BookResponsePublic.model_validate(book).model_dump(mode="json")
        await set_cache(key, serialized, 600)

        return serialized

    @staticmethod
    async def update_book(
        db: AsyncSession, user_id: int, update_request: UpdateBook, book_id: int
    ) -> Book:
        book = await BookRepository.get_book_by_id(db, book_id)
        ensure_exists(book, BookNotFoundError(HTTP404.BOOK))

        try:
            update_object(book, update_request)

            await db.commit()
            await db.refresh(book)

            logger.info(
                "book_updated",
                book_id=book.id,
                updated_by=user_id,
            )

            await delete_cache(BookCacheKey.book_detail_key(book_id))

            return book
        except IntegrityError as error:
            await db.rollback()

            logger.error(
                "update_book_failed",
                book_id=book_id,
                requested_by=user_id,
                error=str(error.orig),
            )

            check_unique_title_and_author(error)
            raise
