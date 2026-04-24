from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.models import Book
from src.book.schemas import CreateBook, SearchBook

ALLOWED_SORT_FIELDS_BOOK = {"created_at", "title", "author", "publishing_date"}


class BookRepository:
    @staticmethod
    async def get_books(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchBook | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Book], int]:
        
        base_query = select(Book)

        if filters:
            if filters.title:
                base_query = base_query.filter(Book.title.ilike('%' + filters.title + '%'))

            if filters.author:
                base_query = base_query.filter(Book.author.ilike('%' + filters.author + '%'))

            if filters.category:
                base_query = base_query.filter(Book.category == filters.category)

            if filters.publishing_date:
                base_query = base_query.filter(Book.publishing_date == filters.publishing_date)

        if sort_by not in ALLOWED_SORT_FIELDS_BOOK:
            sort_by = "created_at"

        sort_column = getattr(Book, sort_by, Book.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> Book | None:
        query = (
            select(Book)
            .filter(Book.id == book_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()


    @staticmethod
    def add_book(db: AsyncSession, new_book: CreateBook) -> None:
        db.add(new_book)