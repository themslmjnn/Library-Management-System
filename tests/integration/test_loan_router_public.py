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


class TestLoanBookMe:
    async def test_member_creates_own_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        member = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.post("/loans/me", json={
            "book_id": book.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == member.id

    async def test_guest_creates_own_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)
        guest = await make_guest(test_db)
        headers = make_auth_header(guest)

        response = await client.post("/loans/me", json={
            "book_id": book.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 201

    async def test_unauthenticated_cannot_loan(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=3, added_by=system_admin.id)

        response = await client.post("/loans/me", json={
            "book_id": book.id,
            "due_at": due_date(),
        })

        assert response.status_code == 401

    async def test_fails_when_book_unavailable(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await make_inventory(test_db, book_id=book.id, quantity=0, added_by=system_admin.id)
        member = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.post("/loans/me", json={
            "book_id": book.id,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 409

    async def test_fails_unknown_book(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        member = await make_member(test_db)
        headers = make_auth_header(member)

        response = await client.post("/loans/me", json={
            "book_id": book.id + 999999,
            "due_at": due_date(),
        }, headers=headers)

        assert response.status_code == 404