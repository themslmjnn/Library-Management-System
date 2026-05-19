from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.models import Book
from src.core.enums import SortOrder
from src.utils.enums import BookCategory

ALLOWED_SORT_FIELDS_BOOK: frozenset[str] = frozenset({"created_at", "title", "author"})


class BookRepository:
    @staticmethod
    async def get_books(
        db: AsyncSession,
        skip: int,
        limit: int,
        title: str | None = None,
        author: str | None = None,
        category: BookCategory | None = None,
        sort_by: str = "created_at",
        order: SortOrder = SortOrder.desc,
    ) -> tuple[list[Book], int]:
        base_query = select(Book)

        if title:
            base_query = base_query.filter(Book.title.ilike(f"%{title}%"))
        if author:
            base_query = base_query.filter(Book.author.ilike(f"%{author}%"))
        if category:
            base_query = base_query.filter(Book.category == category)

        if sort_by not in ALLOWED_SORT_FIELDS_BOOK:
            sort_by = "created_at"

        sort_column = getattr(Book, sort_by)
        base_query = base_query.order_by(
            sort_column.desc() if order == SortOrder.desc else sort_column.asc()
        )

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await db.execute(base_query.offset(skip).limit(limit))

        return result.scalars().all(), total

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> Book | None:
        query = select(Book).filter(Book.id == book_id)

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    def add_book(db: AsyncSession, new_book: Book) -> None:
        db.add(new_book)
