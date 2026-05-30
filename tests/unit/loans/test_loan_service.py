from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.loan.schemas import LoanBase, SearchLoan
from src.loan.service import LoanService
from src.users.models import User
from utils.custom_exceptions import (
    BookNotAvailableError,
    BookNotFoundError,
    LoanAlreadyReturnedError,
    LoanNotFoundError,
    UserNotFoundError,
)
from tests.factories import (
    make_book,
    make_inventory,
    make_member,
)


def due_date(days: int = 14) -> date:
    return date.today() + timedelta(days=days)


class TestLoanBook:
    async def test_creates_loan_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        await make_inventory(
            test_db,
            book_id=book.id,
            quantity=3,
            added_by=system_admin.id,
        )

        borrower = await make_member(test_db)

        request = LoanBase(
            book_id=book.id,
            user_id=borrower.id,
            due_at=due_date(),
        )

        loan = await LoanService.loan_book(test_db, system_admin.id, request)

        assert loan.id is not None
        assert loan.book_id == book.id
        assert loan.user_id == borrower.id
        assert loan.created_by == system_admin.id
        assert loan.returned_at is None

    async def test_loan_sets_inventory_id(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        inventory = await make_inventory(
            test_db,
            book_id=book.id,
            quantity=5,
            added_by=system_admin.id,
        )

        borrower = await make_member(test_db)

        request = LoanBase(
            book_id=book.id,
            user_id=borrower.id,
            due_at=due_date(),
        )

        loan = await LoanService.loan_book(test_db, system_admin.id, request)

        assert loan.inventory_id == inventory.id

    async def test_loan_decrements_inventory(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        inventory = await make_inventory(
            test_db,
            book_id=book.id,
            quantity=5,
            added_by=system_admin.id,
        )

        borrower = await make_member(test_db)

        request = LoanBase(
            book_id=book.id,
            user_id=borrower.id,
            due_at=due_date(),
        )

        await LoanService.loan_book(test_db, system_admin.id, request)

        await test_db.refresh(inventory)

        assert inventory.quantity == 4

    async def test_loan_fails_book_not_found(
        self, test_db: AsyncSession, system_admin: User
    ):
        borrower = await make_member(test_db)
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        request = LoanBase(
            book_id=book.id + 999999,
            user_id=borrower.id,
            due_at=due_date(),
        )

        with pytest.raises(BookNotFoundError):
            await LoanService.loan_book(test_db, system_admin.id, request)

    async def test_loan_fails_user_not_found(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        await make_inventory(
            test_db,
            book_id=book.id,
            quantity=3,
            added_by=system_admin.id,
        )

        borrower = await make_member(test_db)

        request = LoanBase(
            book_id=book.id,
            user_id=borrower.id + 999999,
            due_at=due_date(),
        )

        with pytest.raises(UserNotFoundError):
            await LoanService.loan_book(test_db, system_admin.id, request)

    async def test_loan_fails_book_not_available(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(
            test_db,
            created_by=system_admin.id,
        )

        await make_inventory(
            test_db,
            book_id=book.id,
            quantity=0,
            added_by=system_admin.id,
        )

        borrower = await make_member(test_db)

        request = LoanBase(
            book_id=book.id,
            user_id=borrower.id,
            due_at=due_date(),
        )

        with pytest.raises(BookNotAvailableError):
            await LoanService.loan_book(test_db, system_admin.id, request)

    async def test_loan_fails_no_inventory_record(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        borrower = await make_member(test_db)

        request = LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date())

        with pytest.raises(BookNotAvailableError):
            await LoanService.loan_book(test_db, system_admin.id, request)

    async def test_multiple_loans_decrement_correctly(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )

        borrower1 = await make_member(test_db)
        borrower2 = await make_member(test_db)
        borrower3 = await make_member(test_db)

        for borrower in [borrower1, borrower2, borrower3]:
            await LoanService.loan_book(
                test_db,
                system_admin.id,
                LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
            )

        await test_db.refresh(inventory)
        assert inventory.quantity == 0

    async def test_fourth_loan_fails_when_stock_exhausted(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=2, added_by=system_admin.id
        )

        borrower1 = await make_member(test_db)
        borrower2 = await make_member(test_db)
        borrower3 = await make_member(test_db)

        await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower1.id, due_at=due_date()),
        )
        await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower2.id, due_at=due_date()),
        )

        with pytest.raises(BookNotAvailableError):
            await LoanService.loan_book(
                test_db,
                system_admin.id,
                LoanBase(book_id=book.id, user_id=borrower3.id, due_at=due_date()),
            )


class TestReturnLoan:
    async def test_staff_returns_loan_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        await LoanService.return_loan(test_db, system_admin.id, loan.id)

        await test_db.refresh(loan)

        assert loan.returned_at is not None

    async def test_return_increments_inventory(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        await test_db.refresh(inventory)

        qty_after_loan = inventory.quantity

        await LoanService.return_loan(test_db, system_admin.id, loan.id)

        await test_db.refresh(inventory)

        assert inventory.quantity == qty_after_loan + 1

    async def test_return_sets_timezone_aware_datetime(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        await LoanService.return_loan(test_db, system_admin.id, loan.id)

        await test_db.refresh(loan)
        assert loan.returned_at.tzinfo is not None

    async def test_raises_if_already_returned(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        await LoanService.return_loan(test_db, system_admin.id, loan.id)

        with pytest.raises(LoanAlreadyReturnedError):
            await LoanService.return_loan(test_db, system_admin.id, loan.id)

    async def test_raises_loan_not_found(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        with pytest.raises(LoanNotFoundError):
            await LoanService.return_loan(test_db, system_admin.id, loan.id + 999999)


class TestGetLoans:
    async def test_staff_sees_all_loans(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )

        borrower1 = await make_member(test_db)
        borrower2 = await make_member(test_db)

        await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower1.id, due_at=due_date()),
        )
        await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower2.id, due_at=due_date()),
        )

        result = await LoanService.get_loans(
            test_db,
            skip=0,
            limit=20,
            filters=SearchLoan(),
            sort_by="created_at",
            order="desc",
        )

        assert result.total >= 2

    async def test_get_loan_by_id_returns_correct_loan(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        result = await LoanService.get_loan_by_id(test_db, loan.id)

        assert result["id"] == loan.id
        assert result["book_id"] == book.id
        assert result["user_id"] == borrower.id

    async def test_get_loan_by_id_raises_not_found(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        loan = await LoanService.loan_book(
            test_db,
            system_admin.id,
            LoanBase(book_id=book.id, user_id=borrower.id, due_at=due_date()),
        )

        with pytest.raises(LoanNotFoundError):
            await LoanService.get_loan_by_id(test_db, loan.id + 999999)
