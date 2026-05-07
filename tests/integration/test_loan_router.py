from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_guest,
    make_inventory,
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
)


def due_date(days: int = 14) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ── STAFF LOAN CREATION ────────────────────────────────────────────────────────

class TestLoanBook:
    async def test_system_admin_creates_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == book.id
        assert data["user_id"] == borrower.id

    async def test_library_admin_creates_loan(
        self, client: AsyncClient, test_db: AsyncSession,
        library_admin: User, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(library_admin)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 201

    async def test_receptionist_creates_loan(
        self, client: AsyncClient, test_db: AsyncSession,
        receptionist: User, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(receptionist)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 201

    async def test_member_cannot_create_staff_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        member = await make_member(test_db)
        borrower = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        borrower = await make_member(test_db)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        })

        assert response.status_code == 401

    async def test_fails_when_book_unavailable(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=0, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 409

    async def test_fails_unknown_book(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post("/loans", json={
            "book_id": book.id + 999999,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 404

    async def test_fails_unknown_user(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id + 999999,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 404

    async def test_inventory_decremented_after_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await make_inventory(test_db, book_id=book.id, quantity=5, added_by=system_admin.id)
        borrower = await make_member(test_db)
        headers = make_auth_header(system_admin)

        await client.post("/loans", json={
            "book_id": book.id,
            "user_id": borrower.id,
            "due_at": due_date(),
        }, headers=headers)

        await test_db.refresh(inventory)
        assert inventory.quantity == 4