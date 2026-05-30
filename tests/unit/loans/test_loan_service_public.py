import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.loan.schemas import CreateLoanPublic
from src.loan.service import LoanServicePublic
from src.users.models import User
from utils.custom_exceptions import (
    BookNotAvailableError,
    BookNotFoundError,
    LoanNotFoundError,
)
from tests.factories import (
    make_book,
    make_guest,
    make_inventory,
    make_member,
)
from tests.unit.loans.test_loan_service import due_date


class TestLoanBookMe:
    async def test_creates_loan_successfully(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        request = CreateLoanPublic(book_id=book.id, due_at=due_date())
        loan = await LoanServicePublic.loan_book_me(test_db, request, borrower.id)

        assert loan.id is not None
        assert loan.book_id == book.id
        assert loan.user_id == borrower.id

    async def test_self_service_loan_has_null_created_by(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        request = CreateLoanPublic(book_id=book.id, due_at=due_date())
        loan = await LoanServicePublic.loan_book_me(test_db, request, borrower.id)

        # self-service loans have no staff issuer
        assert loan.created_by is None

    async def test_decrements_inventory(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        request = CreateLoanPublic(book_id=book.id, due_at=due_date())
        await LoanServicePublic.loan_book_me(test_db, request, borrower.id)

        await test_db.refresh(inventory)
        assert inventory.quantity == 4

    async def test_fails_book_not_found(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        borrower = await make_member(test_db)

        request = CreateLoanPublic(book_id=book.id + 999999, due_at=due_date())

        with pytest.raises(BookNotFoundError):
            await LoanServicePublic.loan_book_me(test_db, request, borrower.id)

    async def test_fails_book_not_available(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=0, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        request = CreateLoanPublic(book_id=book.id, due_at=due_date())

        with pytest.raises(BookNotAvailableError):
            await LoanServicePublic.loan_book_me(test_db, request, borrower.id)

    async def test_guest_can_loan(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        guest = await make_guest(test_db)

        request = CreateLoanPublic(book_id=book.id, due_at=due_date())
        loan = await LoanServicePublic.loan_book_me(test_db, request, guest.id)

        assert loan.user_id == guest.id


class TestGetLoansMe:
    async def test_member_cannot_see_other_users_loan_by_id(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )

        borrower1 = await make_member(test_db)
        borrower2 = await make_member(test_db)

        loan = await LoanServicePublic.loan_book_me(
            test_db, CreateLoanPublic(book_id=book.id, due_at=due_date()), borrower1.id
        )

        # borrower2 tries to access borrower1's loan
        with pytest.raises(LoanNotFoundError):
            await LoanServicePublic.get_loan_by_id_me(test_db, borrower2.id, loan.id)
