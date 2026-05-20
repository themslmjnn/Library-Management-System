from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_guest,
    make_inventory,
    make_member,
)


def due_date(days: int = 14) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


class TestLoanBookMe:
    async def test_member_creates_own_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        response = await client.post(
            "/loans/me",
            json={
                "book_id": book.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == member.id

    async def test_guest_creates_own_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        guest = await make_guest(test_db)
        headers = await make_auth_header(test_db, guest)

        response = await client.post(
            "/loans/me",
            json={
                "book_id": book.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 201

    async def test_unauthenticated_cannot_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )

        response = await client.post(
            "/loans/me",
            json={
                "book_id": book.id,
                "due_at": due_date(),
            },
        )

        assert response.status_code == 401

    async def test_fails_when_book_unavailable(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=0, added_by=system_admin.id
        )
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        response = await client.post(
            "/loans/me",
            json={
                "book_id": book.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 409

    async def test_fails_unknown_book(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        response = await client.post(
            "/loans/me",
            json={
                "book_id": book.id + 999999,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 404


class TestGetLoansMe:
    async def test_member_sees_own_loans(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        await client.post(
            "/loans/me",
            json={"book_id": book.id, "due_at": due_date()},
            headers=headers,
        )

        response = await client.get("/loans/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == member.id

    async def test_member_cannot_see_other_users_loans(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )

        member1 = await make_member(test_db)
        member2 = await make_member(test_db)

        await client.post(
            "/loans/me",
            json={"book_id": book.id, "due_at": due_date()},
            headers=await make_auth_header(test_db, member1),
        )

        # member2 fetches their own loans — must not see member1's loan
        response = await client.get(
            "/loans/me", headers=await make_auth_header(test_db, member2)
        )

        data = response.json()
        ids = [loan["user_id"] for loan in data["items"]]
        assert member1.id not in ids

    async def test_unauthenticated_cannot_get_loans_me(self, client: AsyncClient):
        response = await client.get("/loans/me")
        assert response.status_code == 401

    async def test_member_gets_own_loan_by_id(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        loan_response = await client.post(
            "/loans/me",
            json={"book_id": book.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.get(f"/loans/{loan_id}/me", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == loan_id

    async def test_member_cannot_get_other_users_loan_by_id(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )

        member1 = await make_member(test_db)
        member2 = await make_member(test_db)

        loan_response = await client.post(
            "/loans/me",
            json={"book_id": book.id, "due_at": due_date()},
            headers=await make_auth_header(test_db, member1),
        )
        loan_id = loan_response.json()["id"]

        # member2 tries to access member1's loan — must get 404, not 403
        # 404 prevents confirming the loan exists at all
        response = await client.get(
            f"/loans/{loan_id}/me", headers=await make_auth_header(test_db, member2)
        )

        assert response.status_code == 404
