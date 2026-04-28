from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.models import Book
from src.book.repository import BookRepository
from src.book.schemas import BookResponse, CreateBook, SearchBook, UpdateBook
from src.core.cache import get_cache, set_cache
from src.core.logging import get_logger
from src.pagination import PaginatedResponse
from src.user.models import User
from src.utils.cache_keys import book_detail_key
from src.utils.exception_constants import HTTP404
from src.utils.exceptions import check_unique_title_and_author
from src.utils.helpers import ensure_exists, update_object

logger = get_logger(__name__)


class BookService:
    @staticmethod
    async def add_book(db: AsyncSession, book_request: CreateBook, current_user: User):
        new_book = Book(**book_request.model_dump(), created_by=current_user.id)

        try:
            BookRepository.add_book(db, new_book)

            await db.commit()
            await db.refresh(new_book)

            logger.info(
                "book_created",
                book_id=new_book.id,
                created_by=current_user.id,
            )

            return new_book
        
        except IntegrityError as error:
            await db.rollback()

            logger.error(
                "create_book_failed",
                requested_by=current_user.id,
                error=str(error.orig),
            )

            check_unique_title_and_author(error)
            raise
        

    @staticmethod
    async def get_books(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchBook,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        books, total = await BookRepository.get_books(db, skip, limit, filters, sort_by, order)
        
        return PaginatedResponse(
            items=books,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> Book:
        cached = await get_cache(book_detail_key(book_id))
        if cached is not None:
            return cached
        

        book = await BookRepository.get_book_by_id(db, book_id)
        ensure_exists(book, HTTP404.BOOK)

        serialized = BookResponse.model_validate(book).model_dump(mode="json")
        await set_cache(book_detail_key(book_id), serialized, 600)

        return serialized
    

    @staticmethod
    async def update_book(db: AsyncSession, user_id: int, update_request: UpdateBook, book_id: int) -> Book:
        book = await BookRepository.get_book_by_id(db, book_id)

        ensure_exists(book, HTTP404.BOOK)

        try:
            update_object(book, update_request)

            await db.commit()

            logger.info(
                "book_updated",
                book_id=book.id,
                updated_by=user_id,
            )

            return book
        
        except IntegrityError as error:
            await db.rollback()

            logger.error(
                "update_book_failed",
                book_id=book.id,
                requested_by=user_id,
                error=str(error.orig),
            )
            
            check_unique_title_and_author(error)
            raise