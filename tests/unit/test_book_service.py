from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User
from src.book.schemas import CreateBook, UpdateBook
from src.book.service import BookService
import pytest
from src.utils.exceptions import BookAlreadyExistsError, BookNotFoundError

class TestCreateBook:
    async def test_create_book_successfully(self, test_db: AsyncSession, system_admin: User):
        book_request = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        new_book = await BookService.add_book(test_db, book_request, system_admin.id)
        
        assert new_book.title == "Book_1"
        assert new_book.author == "Author_1"
        assert new_book.category == "science"
        assert new_book.created_by == system_admin.id


    async def test_reject_duplicate_books(self, test_db: AsyncSession, system_admin: User):
        book_1 = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        await BookService.add_book(test_db, book_1, system_admin.id)

        book_2 = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
        )

        with pytest.raises(BookAlreadyExistsError):
            await BookService.add_book(test_db, book_2, system_admin.id)


class TestGetBookByID:
    async def test_return_valid_book_info(self, test_db: AsyncSession, system_admin: User):
        book_request = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        book = await BookService.add_book(test_db, book_request, system_admin.id)

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
    async def test_update_book_successfully(self, test_db: AsyncSession, system_admin: User):
        book_request = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        book = await BookService.add_book(test_db, book_request, system_admin.id)

        update_request = UpdateBook(
            title="NewBook_1",
            author="NewAuthor_1",
        )

        result = await BookService.update_book(test_db, system_admin.id, update_request, book.id)

        assert result.title == update_request.title
        assert result.author == update_request.author


    async def test_reject_duplicate_fields(self, test_db: AsyncSession, system_admin: User):
        system_admin_id = system_admin.id
        book_1 = CreateBook(
            title="Book_1",
            author="Author_1",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        book_1 = await BookService.add_book(test_db, book_1, system_admin_id)

        book_2 = CreateBook(
            title="Book_2",
            author="Author_2",
            category="science",
            description="Awesome book",
            publishing_date="2020-10-10",
        )

        book_2 = await BookService.add_book(test_db, book_2, system_admin_id)

        update_request = UpdateBook(
            title="Book_1",
            author="Author_1",
        )

        with pytest.raises(BookAlreadyExistsError):
            await BookService.update_book(test_db, system_admin_id, update_request, book_2.id)


    async def test_raise_404_for_unknown_books(self, test_db: AsyncSession, system_admin: User):
        with pytest.raises(BookNotFoundError):
            await BookService.update_book(test_db, system_admin.id, None, 999999)