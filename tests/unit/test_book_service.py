from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.schemas import CreateBook, SearchBook, UpdateBook
from src.book.service import BookService
from src.user.models import User
from src.utils.exceptions import BookAlreadyExistsError, BookNotFoundError
from tests.factories import make_book


class TestCreateBook:
    async def test_reject_duplicate_books(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        book_to_be_created = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
        )

        with pytest.raises(BookAlreadyExistsError):
            await BookService.add_book(test_db, book_to_be_created, system_admin.id)

    async def test_same_title_different_author_is_allowed(self, test_db, system_admin):
        await make_book(
            test_db,
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        book_to_be_created = CreateBook(
            title="Book_1",
            author="Author_2",
            category="science",
        )

        result = await BookService.add_book(
            test_db, book_to_be_created, system_admin.id
        )

        assert result.id is not None

    async def test_create_book_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        book_request = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
        )

        new_book = await BookService.add_book(test_db, book_request, system_admin.id)

        assert new_book.title == "Book_1"
        assert new_book.author == "Author_1"
        assert new_book.category == "science"
        assert new_book.created_by == system_admin.id


class TestGetBookByID:
    async def test_return_valid_book_info(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        result = await BookService.get_book_by_id(test_db, book.id)

        assert result["id"] == book.id
        assert result["title"] == book.title
        assert result["author"] == book.author
        assert result["category"] == book.category
        assert result["created_by"] == system_admin.id

    async def test_raise_404_for_unknown_books(self, test_db: AsyncSession):
        with pytest.raises(BookNotFoundError):
            await BookService.get_book_by_id(test_db, 999999)


class TestUpdateBook:
    async def test_raise_404_for_unknown_books(
        self, test_db: AsyncSession, system_admin: User
    ):
        with pytest.raises(BookNotFoundError):
            await BookService.update_book(
                test_db, system_admin.id, UpdateBook(title="Anything"), 999999
            )

    async def test_reject_duplicate_fields(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        book_to_be_updated = await make_book(
            test_db,
            title="Book_2",
            author="Author_2",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        update_request = UpdateBook(
            title="Book_1",
            author="Author_1",
        )

        with pytest.raises(BookAlreadyExistsError):
            await BookService.update_book(
                test_db, system_admin.id, update_request, book_to_be_updated.id
            )

    async def test_update_book_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date=date(2000, 2, 4),
            created_by=system_admin.id,
        )

        update_request = UpdateBook(
            title="NewBook_1",
            author="NewAuthor_1",
        )

        result = await BookService.update_book(
            test_db, system_admin.id, update_request, book.id
        )

        await test_db.refresh(result)

        assert result.title == update_request.title
        assert result.author == update_request.author


class TestGetBooks:
    async def test_returns_paginated_response(
        self, test_db: AsyncSession, system_admin: User
    ):
        for _ in range(3):
            await make_book(
                test_db,
                created_by=system_admin.id,
            )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(),
            sort_by="created_at",
            order="desc",
        )

        result_dict = result.model_dump()

        assert "items" in result_dict
        assert "total" in result_dict
        assert "has_more" in result_dict
        assert result.total >= 3

    async def test_pagination_skip_works(
        self, test_db: AsyncSession, system_admin: User
    ):
        for _ in range(5):
            await make_book(
                test_db,
                created_by=system_admin.id,
            )

        result = await BookService.get_books(
            test_db,
            skip=3,
            limit=20,
            filters=SearchBook(),
            sort_by="created_at",
            order="desc",
        )

        assert len(result.items) == 2

    async def test_pagination_limit_works(
        self, test_db: AsyncSession, system_admin: User
    ):
        for _ in range(5):
            await make_book(
                test_db,
                created_by=system_admin.id,
            )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=2,
            filters=SearchBook(),
            sort_by="created_at",
            order="desc",
        )

        assert len(result.items) == 2
        assert result.has_more is True

    async def test_has_more_is_false_when_no_more_pages(
        self, test_db: AsyncSession, system_admin: User
    ):
        for _ in range(3):
            await make_book(
                test_db,
                created_by=system_admin.id,
            )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(),
            sort_by="created_at",
            order="desc",
        )

        assert result.has_more is False

    async def test_filters_by_category(self, test_db: AsyncSession, system_admin: User):
        for _ in range(2):
            await make_book(
                test_db,
                category="fiction",
                created_by=system_admin.id,
            )

        await make_book(
            test_db,
            category="science",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(category="fiction"),
            sort_by="created_at",
            order="desc",
        )

        assert result.total == 2
        assert all(b.category == "fiction" for b in result.items)

    async def test_filters_by_title(self, test_db: AsyncSession, system_admin: User):
        await make_book(
            test_db,
            title="Python Cookbook",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            title="Clean Code",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(title="python"),
            sort_by="created_at",
            order="desc",
        )

        assert result.total == 1
        assert result.items[0].title == "Python Cookbook"

    async def test_filters_by_author(self, test_db: AsyncSession, system_admin: User):
        await make_book(
            test_db,
            author="Martin Fowler",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            author="Robert Martin",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(author="fowler"),
            sort_by="created_at",
            order="desc",
        )

        assert result.total == 1
        assert result.items[0].author == "Martin Fowler"

    async def test_title_filter_is_case_insensitive(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="The Great Gatsby",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(title="great gatsby"),
            sort_by="created_at",
            order="desc",
        )

        assert result.total == 1

    async def test_sort_by_title_ascending(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="Zebra Book",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            title="Apple Book",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            title="Mango Book",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(),
            sort_by="title",
            order="asc",
        )

        titles = [b.title for b in result.items]
        assert titles == sorted(titles)

    async def test_sort_by_title_descending(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="Zebra Book",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            title="Apple Book",
            created_by=system_admin.id,
        )

        await make_book(
            test_db,
            title="Mango Book",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(),
            sort_by="title",
            order="desc",
        )

        titles = [b.title for b in result.items]
        assert titles == sorted(titles, reverse=True)

    async def test_invalid_sort_field_falls_back_to_created_at(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(),
            sort_by="nonexistent_field",
            order="desc",
        )

        assert result.total >= 1

    async def test_empty_result_when_no_match(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            title="Real Book",
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            skip=0,
            limit=20,
            filters=SearchBook(title="zzz_no_match_zzz"),
            sort_by="created_at",
            order="desc",
        )

        assert result.total == 0
        assert result.items == []
        assert result.has_more is False


class TestGetBookByIDCache:
    async def test_returns_correct_data(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        result = await BookService.get_book_by_id(test_db, book.id)

        assert result["id"] == book.id
        assert result["title"] == book.title
        assert result["author"] == book.author

    async def test_second_call_returns_same_result(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        result1 = await BookService.get_book_by_id(test_db, book.id)
        result2 = await BookService.get_book_by_id(test_db, book.id)

        assert result1 == result2

    async def test_cache_invalidated_after_update(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        await BookService.get_book_by_id(test_db, book.id)

        await BookService.update_book(
            test_db,
            system_admin.id,
            UpdateBook(title="Updated Title"),
            book.id,
        )

        result = await BookService.get_book_by_id(test_db, book.id)

        assert result["title"] == "Updated Title"

    async def test_not_found_raises_after_cache_miss(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        non_existent_id = book.id + 999999

        with pytest.raises(BookNotFoundError):
            await BookService.get_book_by_id(test_db, non_existent_id)
