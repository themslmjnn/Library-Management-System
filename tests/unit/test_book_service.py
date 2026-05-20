from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import SortOrder
from src.book.schemas import BookResponse, CreateBook, SearchBook, UpdateBook
from src.book.service import BookService
from src.core.dependencies import BookQueryParams
from src.user.models import User
from src.utils.exceptions import BookAlreadyExistsError, BookNotFoundError
from tests.factories import make_book
from utils.cache_keys import book_detail_key
from utils.enums import BookCategory


class TestCreateBook:
    async def test_reject_duplicate_books(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        book_to_be_created = CreateBook(
            title=book.title,
            author=book.author,
            category="science",
        )

        with pytest.raises(BookAlreadyExistsError):
            await BookService.add_book(test_db, book_to_be_created, system_admin.id)

    async def test_same_title_different_author_is_allowed(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            title="Book_1",
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
        assert result.title == book.title
        assert result.author == "Author_2"
        assert result.category == "science"

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
            **BookQueryParams().model_dump(),
        )

        result_dict = result.model_dump()

        assert "items" in result_dict
        assert "total" in result_dict
        assert "has_more" in result_dict
        assert result.total == 3

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
            **BookQueryParams(skip=3).model_dump(),
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
            **BookQueryParams(limit=2).model_dump(),
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
            **BookQueryParams().model_dump(),
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
            **BookQueryParams(category=BookCategory.fiction).model_dump(),
        )

        assert result.total == 2
        assert all(book.category == "fiction" for book in result.items)

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
            **BookQueryParams(title="python").model_dump(),
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
            **BookQueryParams(author="fowler").model_dump(),
        )

        assert result.total == 1
        assert result.items[0].author == "Martin Fowler"

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
            **BookQueryParams(sort_by="title", order=SortOrder.asc).model_dump(),
        )

        titles = sorted(["Zebra Book", "Apple Book", "Mango Book"])
        results = [book.title for book in result.items]

        assert titles == results

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
            **BookQueryParams(sort_by="title").model_dump(),
        )

        titles = sorted(["Zebra Book", "Apple Book", "Mango Book"], reverse=True)
        results = [book.title for book in result.items]

        assert results == titles

    async def test_invalid_sort_field_falls_back_to_created_at(
        self, test_db: AsyncSession, system_admin: User
    ):
        await make_book(
            test_db,
            created_by=system_admin.id,
        )

        result = await BookService.get_books(
            test_db,
            **BookQueryParams(sort_by="invalid_field").model_dump(),
        )

        assert result.total == 1

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
            **BookQueryParams(title="invalid_title").model_dump(),
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

    async def test_get_book_by_id_populates_cache_after_db_hit(
        self, test_db: AsyncSession, system_admin: User, mocker
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        mock_set_cache = mocker.patch("src.book.service.set_cache")

        await BookService.get_book_by_id(test_db, book.id)

        mock_set_cache.assert_called_once_with(
            book_detail_key(book.id),
            mocker.ANY,
            600,
        )


class TestGetBookByID:
    async def test_return_valid_book_info(
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
        assert result["category"] == book.category
        assert result["created_by"] == system_admin.id

    async def test_raise_404_for_unknown_books(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        with pytest.raises(BookNotFoundError):
            await BookService.get_book_by_id(test_db, book.id + 999999)


class TestUpdateBook:
    async def test_raise_404_for_unknown_books(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        with pytest.raises(BookNotFoundError):
            await BookService.update_book(
                test_db, system_admin.id, UpdateBook(title="Anything"), book.id + 999999
            )

    async def test_reject_duplicate_fields(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        book_to_be_updated = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        update_request = UpdateBook(
            title=book.title,
            author=book.author,
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
