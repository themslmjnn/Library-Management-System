test_loan_router.py:
from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_inventory,
    make_member,
)


def due_date(days: int = 14) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ── STAFF LOAN CREATION ────────────────────────────────────────────────────────


class TestLoanBook:
    async def test_system_admin_creates_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == book.id
        assert data["user_id"] == borrower.id

    async def test_library_admin_creates_loan(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        library_admin: User,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(library_admin)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 201

    async def test_receptionist_creates_loan(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        receptionist: User,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(receptionist)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 201

    async def test_member_cannot_create_staff_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        member = await make_member(test_db)
        borrower = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
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
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 409

    async def test_fails_unknown_book(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id + 999999,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 404

    async def test_fails_unknown_user(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id + 999999,
                "due_at": due_date(),
            },
            headers=headers,
        )

        assert response.status_code == 404

    async def test_inventory_decremented_after_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        await client.post(
            "/loans",
            json={
                "book_id": book.id,
                "user_id": borrower.id,
                "due_at": due_date(),
            },
            headers=headers,
        )

        await test_db.refresh(inventory)
        assert inventory.quantity == 4


class TestGetLoans:
    async def test_staff_gets_all_loans(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=5, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )

        response = await client.get("/loans", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_member_cannot_get_all_loans(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        member = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.get("/loans", headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_get_loans(self, client: AsyncClient):
        response = await client.get("/loans")
        assert response.status_code == 401

    async def test_get_loan_by_id_returns_correct_data(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.get(f"/loans/{loan_id}", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == loan_id

    async def test_get_loan_by_id_returns_404_for_unknown(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.get(f"/loans/{loan_id + 999999}", headers=headers)

        assert response.status_code == 404

    async def test_member_cannot_get_loan_by_id_via_staff_endpoint(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        member = await make_member(test_db)
        admin_headers = make_auth_header(system_admin)
        member_headers = make_auth_header(member)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": member.id, "due_at": due_date()},
            headers=admin_headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.get(f"/loans/{loan_id}", headers=member_headers)

        assert response.status_code == 403


class TestReturnLoan:
    async def test_staff_returns_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.put(f"/loans/{loan_id}/return", headers=headers)

        assert response.status_code == 200

    async def test_return_increments_inventory(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        await test_db.refresh(inventory)
        qty_after_loan = inventory.quantity

        await client.put(f"/loans/{loan_id}/return", headers=headers)

        await test_db.refresh(inventory)
        assert inventory.quantity == qty_after_loan + 1

    async def test_returns_400_if_already_returned(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        await client.put(f"/loans/{loan_id}/return", headers=headers)
        response = await client.put(f"/loans/{loan_id}/return", headers=headers)

        assert response.status_code == 400

    async def test_returns_404_for_unknown_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.put(
            f"/loans/{loan_id + 999999}/return", headers=headers
        )

        assert response.status_code == 404

    async def test_member_cannot_return_via_staff_endpoint(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        member = await make_member(test_db)
        admin_headers = make_auth_header(system_admin)
        member_headers = make_auth_header(member)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": member.id, "due_at": due_date()},
            headers=admin_headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.put(f"/loans/{loan_id}/return", headers=member_headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_return_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(
            test_db, book_id=book.id, quantity=3, added_by=system_admin.id
        )
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        loan_response = await client.post(
            "/loans",
            json={"book_id": book.id, "user_id": borrower.id, "due_at": due_date()},
            headers=headers,
        )
        loan_id = loan_response.json()["id"]

        response = await client.put(f"/loans/{loan_id}/return")

        assert response.status_code == 401


test_loan_public_router.py:
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
        headers = make_auth_header(member)

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
        headers = make_auth_header(guest)

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
        headers = make_auth_header(member)

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
        headers = make_auth_header(member)

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
        headers = make_auth_header(member)

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
            headers=make_auth_header(member1),
        )

        # member2 fetches their own loans — must not see member1's loan
        response = await client.get("/loans/me", headers=make_auth_header(member2))

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
        headers = make_auth_header(member)

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
            headers=make_auth_header(member1),
        )
        loan_id = loan_response.json()["id"]

        # member2 tries to access member1's loan — must get 404, not 403
        # 404 prevents confirming the loan exists at all
        response = await client.get(
            f"/loans/{loan_id}/me", headers=make_auth_header(member2)
        )

        assert response.status_code == 404
